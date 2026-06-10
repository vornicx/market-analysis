"""Alert creation: dedupe key, suppression window, anti-spam caps, band-upgrade
escalation, evidence persistence, optional LLM annotation, Telegram delivery."""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone

from supabase import Client

from . import llm, telegram
from .models import FeatureCtx, GlobalConfig, ScoredAnomaly, Segment

log = logging.getLogger(__name__)

BAND_ORDER = {"low": 0, "medium": 1, "high": 2}


def dedupe_key(ctx: FeatureCtx, scored: ScoredAnomaly, suppression_minutes: int) -> str:
    """Same (segment, event, market, selection, direction) can't alert twice
    inside one suppression bucket. DB unique constraint enforces it."""
    bucket = int(time.time() // (suppression_minutes * 60))
    raw = "|".join(
        [
            ctx.segment.segment_key,
            ctx.event_id,
            ctx.snapshot.market_key,
            ctx.selection_id,
            scored.direction,
            str(bucket),
        ]
    )
    return hashlib.sha1(raw.encode()).hexdigest()


def _event_alerts_today(db: Client, event_id: str) -> int:
    midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    res = (
        db.table("alerts")
        .select("id", count="exact", head=True)
        .eq("event_id", event_id)
        .gte("created_at", midnight.isoformat())
        .execute()
    )
    return res.count or 0


def _existing_band(db: Client, key: str) -> str | None:
    rows = db.table("alerts").select("confidence_band").eq("dedupe_key", key).execute().data
    return rows[0]["confidence_band"] if rows else None


def create_and_deliver(
    db: Client,
    config: GlobalConfig,
    segment: Segment,
    ctx: FeatureCtx,
    scored: ScoredAnomaly,
    cycle_alerts_sent: int = 0,
) -> str | None:
    """Returns alert id, or None if deduped. Never raises on Telegram failure."""
    key = dedupe_key(ctx, scored, config.alert_suppression_minutes)
    escalation = False

    existing = _existing_band(db, key)
    if existing is not None:
        # Suppression window active. The only bypass: the band UPGRADED.
        if BAND_ORDER[scored.band] > BAND_ORDER[existing]:
            key = f"{key}-esc-{scored.band}"
            escalation = True
            if _existing_band(db, key) is not None:
                return None  # already escalated at this band
        else:
            log.info("alert deduped (key=%s)", key[:10])
            return None

    over_event_cap = _event_alerts_today(db, ctx.event_id) >= config.max_alerts_per_event_per_day
    over_cycle_cap = cycle_alerts_sent >= config.max_alerts_per_cycle

    try:
        alert = (
            db.table("alerts")
            .insert(
                {
                    "segment_key": segment.segment_key,
                    "event_id": ctx.event_id,
                    "market_key": ctx.snapshot.market_key,
                    "selection_id": ctx.selection_id,
                    "alert_type": scored.alert_type,
                    "alert_score": scored.score,
                    "confidence_band": scored.band,
                    "reason_summary": scored.reason_summary,
                    "dedupe_key": key,
                }
            )
            .execute()
            .data[0]
        )
    except Exception:
        log.info("alert deduped at insert (key=%s)", key[:10])
        return None

    db.table("alert_evidence").insert(
        {"alert_id": alert["id"], "payload": _evidence_payload(ctx, scored)}
    ).execute()

    if config.llm_enabled:
        llm.annotate(db, config, ctx, scored, alert["id"])

    _deliver(
        db, config, segment, ctx, scored, alert["id"],
        escalation=escalation,
        suppress=over_event_cap or over_cycle_cap,
        suppress_reason="event daily cap" if over_event_cap else "cycle cap",
    )
    return alert["id"]


def _evidence_payload(ctx: FeatureCtx, scored: ScoredAnomaly) -> dict:
    return {
        "detectors": {
            r.detector: {"fired": r.fired, "points": r.points, "evidence": r.evidence}
            for r in scored.detector_results
        },
        "consensus_series": [
            {"polled_at": ts.isoformat(), "implied_prob": p} for ts, p in ctx.consensus_series
        ],
        "book_series": {
            book: [{"polled_at": ts.isoformat(), "implied_prob": p} for ts, p in series]
            for book, series in ctx.book_series.items()
        },
        "thresholds_used": ctx.segment.thresholds,
    }


def _fetch_llm_line(db: Client, alert_id: str) -> str | None:
    rows = (
        db.table("llm_analyses")
        .select("classification, summary, status")
        .eq("alert_id", alert_id)
        .eq("status", "ok")
        .execute()
        .data
    )
    if not rows:
        return None
    r = rows[0]
    return f"{r['classification'].replace('_', ' ')}: {r['summary']}"


def _deliver(
    db: Client,
    config: GlobalConfig,
    segment: Segment,
    ctx: FeatureCtx,
    scored: ScoredAnomaly,
    alert_id: str,
    escalation: bool,
    suppress: bool,
    suppress_reason: str,
) -> None:
    chat_id = segment.telegram_chat_id
    if not chat_id:
        log.warning("segment %s has no telegram_chat_id — skipping delivery", segment.segment_key)
        return

    if suppress:
        log.info("alert %s suppressed (%s)", alert_id[:8], suppress_reason)
        db.table("telegram_deliveries").insert(
            {"alert_id": alert_id, "chat_id": chat_id, "status": "suppressed",
             "error": suppress_reason}
        ).execute()
        return

    if config.dry_run:
        db.table("telegram_deliveries").insert(
            {"alert_id": alert_id, "chat_id": chat_id, "status": "dry_run"}
        ).execute()
        return

    s = ctx.snapshot
    text = telegram.format_alert_message(
        display_label=segment.display_label,
        segment_key=segment.segment_key,
        home_team=s.home_team,
        away_team=s.away_team,
        competition=s.sport_key,
        market_key=s.market_key,
        selection=s.selection_name + (f" {s.line:+g}" if s.line is not None else ""),
        alert_type=scored.alert_type,
        score=scored.score,
        band=scored.band,
        reason=scored.reason_summary,
        kickoff=s.commence_time,
        alert_id=alert_id,
        escalation=escalation,
        llm_line=_fetch_llm_line(db, alert_id),
        detector_results=scored.detector_results if scored.band == "high" else None,
        consensus_series=ctx.consensus_series if scored.band == "high" else None,
    )
    message_id, error = telegram.send_message(chat_id, text)
    db.table("telegram_deliveries").insert(
        {
            "alert_id": alert_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "status": "sent" if message_id else "failed",
            "error": error,
            "attempts": 1 if message_id else len(telegram.RETRY_DELAYS) + 1,
        }
    ).execute()
