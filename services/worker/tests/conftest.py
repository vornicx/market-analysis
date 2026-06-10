"""Shared factories: synthetic configs, segments and feature contexts.

No network, no database — everything detectors/scoring need is constructed
in memory so the core logic is testable in milliseconds.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

# settings.py instantiates at import — give it harmless values before any
# worker module import.
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key")
os.environ.setdefault("ODDS_API_KEY", "test-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

import pytest

from worker.models import FeatureCtx, GlobalConfig, Segment, Snapshot

T0 = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)


def make_config(**overrides) -> GlobalConfig:
    base = dict(
        football_enabled=True,
        world_cup_enabled=False,
        world_cup_only_mode=False,
        global_pause=False,
        dry_run=True,
        llm_enabled=False,
        daily_credit_cap=16,
        monthly_credit_cap=450,
        odds_api_region="eu",
        worker_poll_floor_seconds=300,
        alert_suppression_minutes=90,
    )
    base.update(overrides)
    return GlobalConfig(**base)


def make_segment(segment_key: str = "world_cup", **overrides) -> Segment:
    base = dict(
        segment_key=segment_key,
        display_label="WORLD CUP" if segment_key == "world_cup" else "GENERAL FOOTBALL",
        sport_keys=["soccer_fifa_world_cup"],
        bookmaker_keys=["pinnacle", "bet365", "unibet", "williamhill"],
        sharp_bookmaker_keys=["pinnacle"],
        market_keys=["h2h", "spreads", "totals"],
        polling_profile={"gt48h": 0, "h48_24": 480, "h24_6": 180, "h6_1": 60, "lt1h": 30},
        min_alert_score=50,
        thresholds={
            "price_move": {"abs_dp_min": 0.03, "z_min": 3.0},
            "divergence": {"divergence_min": 0.04},
            "drift": {"drift_polls_min": 3, "drift_cum_min": 0.04},
            "sharp_leader": {"sharp_dp_min": 0.025, "follower_count_min": 2},
            "persistence": {"persistence_ratio_min": 0.7},
            "reversal": {"reversal_ratio": 0.6, "reversal_window_polls": 2},
            "rarity": {"rarity_pctile_min": 97, "rarity_min_samples": 30},
        },
        telegram_chat_id="-100123",
        enabled=True,
    )
    base.update(overrides)
    return Segment(**base)


def make_snapshot(**overrides) -> Snapshot:
    base = dict(
        provider_event_id="evt-1",
        sport_key="soccer_fifa_world_cup",
        segment_key="world_cup",
        home_team="Brazil",
        away_team="France",
        commence_time=T0 + timedelta(hours=5),
        bookmaker_key="pinnacle",
        market_key="h2h",
        selection_name="Brazil",
        line=None,
        price_decimal=1.95,
        implied_prob=0.5128,
        book_last_update=T0,
        poll_cycle_id="cycle-1",
    )
    base.update(overrides)
    return Snapshot(**base)


def series_from(probs: list[float], start: datetime = T0) -> list[tuple[datetime, float]]:
    """Build a time series at 1h intervals ending at start + len-1 hours."""
    return [(start + timedelta(hours=i), p) for i, p in enumerate(probs)]


def make_ctx(
    consensus: list[float],
    books: dict[str, list[float]] | None = None,
    baseline_dps: list[float] | None = None,
    segment: Segment | None = None,
) -> FeatureCtx:
    seg = segment or make_segment()
    book_probs = books or {}
    return FeatureCtx(
        segment=seg,
        snapshot=make_snapshot(),
        selection_id="sel-1",
        event_id="event-uuid-1",
        book_series={b: series_from(ps) for b, ps in book_probs.items()},
        consensus_series=series_from(consensus),
        baseline_dps=baseline_dps if baseline_dps is not None else [],
    )


@pytest.fixture
def segment() -> Segment:
    return make_segment()
