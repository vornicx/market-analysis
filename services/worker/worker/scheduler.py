"""Adaptive cadence: decide which segments are due to poll this cycle,
based on time-to-kickoff of their nearest upcoming event and the budget."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from supabase import Client

from .models import Segment

log = logging.getLogger(__name__)

# polling_profile keys by hours-to-kickoff window
WINDOWS = [
    (1, "lt1h"),
    (6, "h6_1"),
    (24, "h24_6"),
    (48, "h48_24"),
]


def cadence_minutes(segment: Segment, hours_to_kickoff: float) -> int:
    """0 means: do not poll."""
    for max_hours, key in WINDOWS:
        if hours_to_kickoff <= max_hours:
            return int(segment.polling_profile.get(key, 0))
    return int(segment.polling_profile.get("gt48h", 0))


def nearest_kickoff_hours(db: Client, segment: Segment) -> float | None:
    now = datetime.now(timezone.utc)
    rows = (
        db.table("events")
        .select("commence_time")
        .eq("segment_key", segment.segment_key)
        .eq("status", "upcoming")
        .gte("commence_time", now.isoformat())
        .order("commence_time")
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        return None
    ko = datetime.fromisoformat(rows[0]["commence_time"].replace("Z", "+00:00"))
    return (ko - now).total_seconds() / 3600


def is_due(
    db: Client, segment: Segment, last_polled_at: datetime | None
) -> bool:
    hours = nearest_kickoff_hours(db, segment)
    if hours is None:
        return False
    minutes = cadence_minutes(segment, hours)
    if minutes <= 0:
        return False
    if last_polled_at is None:
        return True
    age_min = (datetime.now(timezone.utc) - last_polled_at).total_seconds() / 60
    return age_min >= minutes
