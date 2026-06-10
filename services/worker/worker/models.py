"""Typed contracts. Mirrors packages/shared/src/types.ts — keep in sync by hand."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class GlobalConfig(BaseModel):
    football_enabled: bool
    world_cup_enabled: bool
    world_cup_only_mode: bool
    global_pause: bool
    dry_run: bool
    llm_enabled: bool
    daily_credit_cap: int
    monthly_credit_cap: int
    odds_api_region: str
    worker_poll_floor_seconds: int
    alert_suppression_minutes: int
    # v2 knobs — defaults keep older databases working before 0002 is applied
    max_alerts_per_cycle: int = 8
    max_alerts_per_event_per_day: int = 5
    llm_min_band: str = "medium"


class Segment(BaseModel):
    segment_key: str
    display_label: str
    sport_keys: list[str]
    bookmaker_keys: list[str]
    sharp_bookmaker_keys: list[str]
    market_keys: list[str]
    polling_profile: dict[str, int]
    min_alert_score: int
    thresholds: dict[str, dict[str, float]]
    telegram_chat_id: str | None
    enabled: bool


@dataclass(frozen=True)
class Snapshot:
    """One (event, bookmaker, market, selection) price observation."""

    provider_event_id: str
    sport_key: str
    segment_key: str
    home_team: str
    away_team: str
    commence_time: datetime
    bookmaker_key: str
    market_key: str
    selection_name: str
    line: float | None
    price_decimal: float
    implied_prob: float
    book_last_update: datetime | None
    poll_cycle_id: str


@dataclass
class FeatureCtx:
    """All inputs a detector needs for one selection at one point in time."""

    segment: Segment
    snapshot: Snapshot
    selection_id: str
    event_id: str
    # implied-prob series per book: {bookmaker_key: [(polled_at, implied_prob), ...]} newest last
    book_series: dict[str, list[tuple[datetime, float]]] = field(default_factory=dict)
    consensus_series: list[tuple[datetime, float]] = field(default_factory=list)
    # trailing |dp| samples for rarity baseline (same segment + market_key)
    baseline_dps: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class DetectorResult:
    detector: str
    fired: bool
    points: float  # negative for suppressors (reversal)
    evidence: dict[str, Any]


@dataclass(frozen=True)
class ScoredAnomaly:
    score: int
    band: str  # low | medium | high
    alert_type: str
    reason_summary: str
    direction: str  # shortening | drifting
    detector_results: list[DetectorResult]
