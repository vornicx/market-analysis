"""D5 — RAPID_PERSISTENT: a big move that held through the next poll.

Confirms a D1-size move one poll later: if the market kept >= 70% of the move,
it was real demand, not a blip. This amplifier costs one poll of latency and
strictly reduces noise. Max contribution: 15 points.
"""
from __future__ import annotations

from ..models import DetectorResult, FeatureCtx

MAX_POINTS = 15.0


class PersistenceAmpDetector:
    name = "persistence_amp"

    def detect(self, ctx: FeatureCtx) -> DetectorResult:
        th = ctx.segment.thresholds.get("persistence", {})
        ratio_min = float(th.get("persistence_ratio_min", 0.7))
        move_min = float(
            ctx.segment.thresholds.get("price_move", {}).get("abs_dp_min", 0.03)
        )

        series = ctx.consensus_series
        if len(series) < 3:
            return DetectorResult(self.name, False, 0.0, {"reason": "insufficient history"})

        p_before, p_mid, p_now = series[-3][1], series[-2][1], series[-1][1]
        move = p_mid - p_before
        if abs(move) < move_min:
            return DetectorResult(self.name, False, 0.0, {"reason": "no qualifying prior move"})

        retained = (p_now - p_before) / move  # 1.0 = fully held, <0 = reversed past origin
        if retained < ratio_min:
            return DetectorResult(
                self.name, False, 0.0,
                {"prior_move": round(move, 5), "retained_ratio": round(retained, 3)},
            )

        points = MAX_POINTS * min(retained, 1.0)
        return DetectorResult(
            self.name,
            True,
            round(points, 1),
            {
                "prior_move": round(move, 5),
                "retained_ratio": round(retained, 3),
                "direction": "shortening" if move > 0 else "drifting",
            },
        )
