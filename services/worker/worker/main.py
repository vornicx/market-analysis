"""Worker entrypoint. Polls odds on a budget-governed adaptive schedule,
runs detectors, creates alerts, delivers to Telegram. NOT auto-betting.

Run: python -m worker.main
"""
from __future__ import annotations

import logging
import signal
import threading
import uuid
from datetime import datetime, timezone

from . import alerting, config as config_mod, features, normalize, persistence, scheduler, scoring
from .detectors import REGISTRY
from .odds_client import OddsApiClient

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
log = logging.getLogger("worker")

shutdown = threading.Event()
_last_polled: dict[str, datetime] = {}  # segment_key -> last poll time (process memory)
_last_event_refresh: datetime | None = None


def _handle_sigterm(signum: int, frame: object) -> None:
    log.info("shutdown signal received — finishing current cycle")
    shutdown.set()


def refresh_events(db, odds, segments) -> None:
    """Daily cheap event-list refresh keeps the schedule warm (0 credits)."""
    global _last_event_refresh
    now = datetime.now(timezone.utc)
    if _last_event_refresh and (now - _last_event_refresh).total_seconds() < 86400:
        return
    for seg in segments:
        for sport_key in seg.sport_keys:
            try:
                for ev in odds.fetch_events(sport_key):
                    db.table("events").upsert(
                        {
                            "provider_event_id": ev["id"],
                            "sport_key": sport_key,
                            "segment_key": seg.segment_key,
                            "home_team": ev["home_team"],
                            "away_team": ev["away_team"],
                            "commence_time": ev["commence_time"],
                        },
                        on_conflict="provider_event_id,sport_key",
                    ).execute()
            except Exception:
                log.exception("event refresh failed for %s", sport_key)
    _last_event_refresh = now


def poll_segment(db, odds, cfg, seg) -> tuple[int, int, int]:
    """Returns (credits_used, snapshots_written, alerts_created)."""
    poll_cycle_id = str(uuid.uuid4())
    snaps = []
    credits = 0
    for sport_key in seg.sport_keys:
        raw, used = odds.fetch_odds(
            sport_key=sport_key,
            region=cfg.odds_api_region,
            market_keys=seg.market_keys,
            bookmaker_keys=seg.bookmaker_keys,
        )
        credits += used
        snaps.extend(normalize.to_snapshots(raw, seg, poll_cycle_id))

    snapshots_written = 0
    alerts_created = 0
    seen_selections: set[str] = set()
    selection_snaps: dict[str, tuple[str, object]] = {}

    for snap in snaps:
        event_id = persistence.upsert_event(db, snap)
        selection_id = persistence.upsert_selection(db, event_id, snap)
        if persistence.insert_snapshot(db, event_id, selection_id, snap):
            snapshots_written += 1
        if selection_id not in seen_selections:
            seen_selections.add(selection_id)
            selection_snaps[selection_id] = (event_id, snap)

    # Detection pass: once per selection (consensus-level), after all books stored.
    for selection_id, (event_id, snap) in selection_snaps.items():
        ctx = features.build_ctx(db, seg, snap, event_id, selection_id)
        results = [d.detect(ctx) for d in REGISTRY]
        scored = scoring.assemble(results, ctx)
        if scored and scored.score >= seg.min_alert_score:
            if alerting.create_and_deliver(db, cfg, seg, ctx, scored):
                alerts_created += 1

    _last_polled[seg.segment_key] = datetime.now(timezone.utc)
    return credits, snapshots_written, alerts_created


def run() -> None:
    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)
    db = persistence.get_db()
    odds = OddsApiClient()
    log.info("worker started")

    while not shutdown.is_set():
        cfg, all_segments = config_mod.load_config(db)
        active = config_mod.resolve_active_segments(cfg, all_segments)

        if not active:
            run_id = persistence.start_run(db, "idle", [])
            persistence.finish_run(db, run_id, "ok")
            shutdown.wait(cfg.worker_poll_floor_seconds)
            continue

        refresh_events(db, odds, active)

        used_today = persistence.credits_used_today(db)
        due = [
            s for s in active
            if scheduler.is_due(db, s, _last_polled.get(s.segment_key))
        ]

        if not due or used_today >= cfg.daily_credit_cap:
            if due and used_today >= cfg.daily_credit_cap:
                log.warning("daily credit cap reached (%d) — polling paused", used_today)
            run_id = persistence.start_run(db, "idle", [s.segment_key for s in due])
            persistence.finish_run(db, run_id, "ok")
            shutdown.wait(cfg.worker_poll_floor_seconds)
            continue

        run_id = persistence.start_run(db, "poll", [s.segment_key for s in due])
        stats = {"credits_used": 0, "snapshots_written": 0, "alerts_created": 0}
        status, error = "ok", None
        try:
            for seg in due:
                if shutdown.is_set() or stats["credits_used"] + used_today >= cfg.daily_credit_cap:
                    status = "partial"
                    break
                credits, snaps_n, alerts_n = poll_segment(db, odds, cfg, seg)
                stats["credits_used"] += credits
                stats["snapshots_written"] += snaps_n
                stats["alerts_created"] += alerts_n
        except Exception as exc:
            log.exception("cycle failed")
            status, error = "error", str(exc)
        persistence.finish_run(db, run_id, status, stats, error)
        shutdown.wait(cfg.worker_poll_floor_seconds)

    odds.close()
    log.info("worker stopped cleanly")


if __name__ == "__main__":
    run()
