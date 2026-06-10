"""Manual replay: re-run detectors over STORED snapshots for an alert's
selection. Zero Odds API credits. Used for threshold tuning from the dashboard.

The dashboard inserts a replay_requests row; the worker consumes pending rows
each cycle. The replayed alert is persisted with status='replayed' and is never
delivered to Telegram.
"""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone

from supabase import Client

from . import features, scoring
from .detectors import REGISTRY
from .models import Segment, Snapshot

log = logging.getLogger(__name__)


def process_pending(db: Client, segments: dict[str, Segment]) -> int:
    rows = (
        db.table("replay_requests")
        .select("*")
        .eq("status", "pending")
        .limit(10)
        .execute()
        .data
    )
    done = 0
    for req in rows:
        try:
            result_id = _replay_one(db, segments, req["alert_id"])
            db.table("replay_requests").update(
                {
                    "status": "done",
                    "result_alert_id": result_id,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", req["id"]).execute()
            done += 1
        except Exception as exc:
            log.exception("replay %s failed", req["id"])
            db.table("replay_requests").update(
                {
                    "status": "failed",
                    "error": str(exc)[:500],
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", req["id"]).execute()
    return done


def _replay_one(db: Client, segments: dict[str, Segment], alert_id: str) -> str | None:
    alert = db.table("alerts").select("*").eq("id", alert_id).single().execute().data
    segment = segments.get(alert["segment_key"])
    if segment is None:
        raise RuntimeError(f"unknown segment {alert['segment_key']}")

    event = db.table("events").select("*").eq("id", alert["event_id"]).single().execute().data
    sel = (
        db.table("selections").select("*").eq("id", alert["selection_id"]).single().execute().data
    )

    # Minimal snapshot shell — features.build_ctx pulls the real series from DB.
    snap = Snapshot(
        provider_event_id=event["provider_event_id"],
        sport_key=event["sport_key"],
        segment_key=event["segment_key"],
        home_team=event["home_team"],
        away_team=event["away_team"],
        commence_time=datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00")),
        bookmaker_key="",
        market_key=sel["market_key"],
        selection_name=sel["name"],
        line=float(sel["line"]) if sel["line"] is not None else None,
        price_decimal=0.0,
        implied_prob=0.0,
        book_last_update=None,
        poll_cycle_id="replay",
    )
    ctx = features.build_ctx(db, segment, snap, alert["event_id"], alert["selection_id"])
    results = [d.detect(ctx) for d in REGISTRY]
    scored = scoring.assemble(results, ctx)
    if scored is None:
        return None  # current thresholds would not alert — useful signal itself

    key = hashlib.sha1(f"replay|{alert_id}|{time.time()}".encode()).hexdigest()
    new_alert = (
        db.table("alerts")
        .insert(
            {
                "segment_key": segment.segment_key,
                "event_id": alert["event_id"],
                "market_key": alert["market_key"],
                "selection_id": alert["selection_id"],
                "alert_type": scored.alert_type,
                "alert_score": scored.score,
                "confidence_band": scored.band,
                "reason_summary": f"[REPLAY of {alert_id[:8]}] {scored.reason_summary}",
                "status": "replayed",
                "dedupe_key": key,
            }
        )
        .execute()
        .data[0]
    )
    db.table("alert_evidence").insert(
        {
            "alert_id": new_alert["id"],
            "payload": {
                "replay_of": alert_id,
                "detectors": {
                    r.detector: {"fired": r.fired, "points": r.points, "evidence": r.evidence}
                    for r in results
                },
                "thresholds_used": segment.thresholds,
            },
        }
    ).execute()
    return new_alert["id"]
