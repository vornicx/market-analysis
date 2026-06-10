"""Idempotent Supabase writes. Every upsert targets a natural unique key,
so a crashed-and-restarted cycle can never duplicate data."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from .models import Snapshot
from .settings import settings

log = logging.getLogger(__name__)


def get_db() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def start_run(db: Client, cycle_type: str, segments: list[str]) -> str:
    row = (
        db.table("worker_runs")
        .insert({"cycle_type": cycle_type, "segments": segments, "status": "running"})
        .execute()
        .data[0]
    )
    return row["id"]


def finish_run(db: Client, run_id: str, status: str, stats: dict[str, Any] | None = None,
               error: str | None = None) -> None:
    db.table("worker_runs").update(
        {
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "error": error,
            **(stats or {}),
        }
    ).eq("id", run_id).execute()


def upsert_event(db: Client, snap: Snapshot) -> str:
    """Returns events.id. Idempotent on (provider_event_id, sport_key)."""
    row = (
        db.table("events")
        .upsert(
            {
                "provider_event_id": snap.provider_event_id,
                "sport_key": snap.sport_key,
                "segment_key": snap.segment_key,
                "home_team": snap.home_team,
                "away_team": snap.away_team,
                "commence_time": snap.commence_time.isoformat(),
            },
            on_conflict="provider_event_id,sport_key",
        )
        .execute()
        .data[0]
    )
    return row["id"]


def upsert_selection(db: Client, event_id: str, snap: Snapshot) -> str:
    existing = (
        db.table("selections")
        .select("id")
        .eq("event_id", event_id)
        .eq("market_key", snap.market_key)
        .eq("name", snap.selection_name)
        .execute()
        .data
    )
    if existing:
        return existing[0]["id"]
    row = (
        db.table("selections")
        .insert(
            {
                "event_id": event_id,
                "market_key": snap.market_key,
                "name": snap.selection_name,
                "line": snap.line,
            }
        )
        .execute()
        .data[0]
    )
    return row["id"]


def insert_snapshot(db: Client, event_id: str, selection_id: str, snap: Snapshot) -> bool:
    """Append-only; unique (selection_id, bookmaker_key, poll_cycle_id) makes it idempotent."""
    try:
        db.table("odds_snapshots").upsert(
            {
                "event_id": event_id,
                "selection_id": selection_id,
                "bookmaker_key": snap.bookmaker_key,
                "market_key": snap.market_key,
                "price_decimal": snap.price_decimal,
                "implied_prob": snap.implied_prob,
                "book_last_update": snap.book_last_update.isoformat()
                if snap.book_last_update
                else None,
                "poll_cycle_id": snap.poll_cycle_id,
            },
            on_conflict="selection_id,bookmaker_key,poll_cycle_id",
            ignore_duplicates=True,
        ).execute()
        return True
    except Exception:
        log.exception("snapshot insert failed for selection %s", selection_id)
        return False


def fetch_series(
    db: Client, selection_id: str, limit_polls: int = 6
) -> list[dict[str, Any]]:
    """Recent snapshots for a selection across books, newest first."""
    return (
        db.table("odds_snapshots")
        .select("bookmaker_key, implied_prob, polled_at")
        .eq("selection_id", selection_id)
        .order("polled_at", desc=True)
        .limit(limit_polls * 8)  # ~books per poll
        .execute()
        .data
    )


def credits_used_today(db: Client) -> int:
    midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = (
        db.table("worker_runs")
        .select("credits_used")
        .gte("started_at", midnight.isoformat())
        .execute()
        .data
    )
    return sum(r["credits_used"] or 0 for r in rows)
