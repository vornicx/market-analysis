"""Alert creation: dedupe key, suppression window, evidence persistence,
Telegram delivery (dry-run aware)."""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import asdict

from supabase import Client

from . import telegram
from .models import FeatureCtx, GlobalConfig, ScoredAnomaly, Segment

log = logging.getLogger(__name__)


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


def create_and_deliver(
    db: Client,
    config: GlobalConfig,
    segment: Segment,
    ctx: FeatureCtx,
    scored: ScoredAnomaly,
) -> str | None:
    """Returns alert id, or None if deduped. Never raises on Telegram failure."""
    key = dedupe_key(ctx, scored, config.alert_suppression_minutes)

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
        log.info("alert deduped (key=%s)", key[:10])
        return None

    db.table("alert_evidence").insert(
        {
            "alert_id": alert["id"],
            "payload": {
                "detectors": {
                    r.detector: {"fired": r.fired, "points": r.points, "evidence": r.evidence}
                    for r in scored.detector_results
                },
                "consensus_series": [
                    {"polled_at": ts.isoformat(), "implied_prob": p}
                    for ts, p in ctx.consensus_series
                ],
                "book_series": {
                    book: [{"polled_at": ts.isoformat(), "implied_prob": p} for ts, p in series]
                    for book, series in ctx.book_series.items()
                },
                "thresholds_used": ctx.segment.thresholds,
            },
        }
    ).execute()

    _deliver(db, config, segment, ctx, scored, alert["id"])
    return alert["id"]


def _deliver(
    db: Client,
    config: GlobalConfig,
    segment: Segment,
    ctx: FeatureCtx,
    scored: ScoredAnomaly,
    alert_id: str,
) -> None:
    chat_id = segment.telegram_chat_id
    if not chat_id:
        log.warning("segment %s has no telegram_chat_id — skipping delivery", segment.segment_key)
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
