"""Combine detector results into a final scored anomaly (blueprint §5)."""
from __future__ import annotations

from .models import DetectorResult, FeatureCtx, ScoredAnomaly

# Which detector dominance maps to which alert_type, in priority order.
TYPE_PRIORITY = [
    ("sharp_leader", "SHARP_MOVE"),
    ("drift", "STEAM_MOVE"),
    ("persistence_amp", "STEAM_MOVE"),
    ("price_move", "PRICE_SPIKE"),
    ("divergence", "BOOK_DIVERGENCE"),
    ("rarity", "RARE_MOVE"),
]


def band_for(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 60:
        return "medium"
    return "low"


def assemble(results: list[DetectorResult], ctx: FeatureCtx) -> ScoredAnomaly | None:
    fired = [r for r in results if r.fired]
    if not fired:
        return None

    raw = sum(r.points for r in results)  # suppressors carry negative points
    score = max(0, min(100, round(raw)))
    if score == 0:
        return None

    dominant = max(fired, key=lambda r: r.points)
    alert_type = next(
        (t for name, t in TYPE_PRIORITY if name == dominant.detector), "PRICE_SPIKE"
    )

    direction = str(dominant.evidence.get("direction", "shortening"))
    s = ctx.snapshot
    line = f" {s.line:+g}" if s.line is not None else ""
    detector_bits = ", ".join(f"{r.detector}({r.points:+.0f})" for r in fired)
    reason = (
        f"{s.selection_name}{line} ({s.market_key}) {direction} in "
        f"{s.home_team} vs {s.away_team}: {detector_bits}"
    )

    return ScoredAnomaly(
        score=score,
        band=band_for(score),
        alert_type=alert_type,
        reason_summary=reason,
        direction=direction,
        detector_results=results,
    )
