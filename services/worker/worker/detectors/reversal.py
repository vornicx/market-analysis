"""D6 — REVERSAL: a move that retraced. Acts as a SUPPRESSOR (negative points).

A qualifying move at poll T-1 that gave back >= reversal_ratio of its magnitude
by poll T was likely a fake/overreaction — subtract 20 points from whatever the
other detectors scored on this selection.
"""
from __future__ import annotations

from ..models import DetectorResult, FeatureCtx

PENALTY = -20.0


class ReversalDetector:
    name = "reversal"

    def detect(self, ctx: FeatureCtx) -> DetectorResult:
        th = ctx.segment.thresholds.get("reversal", {})
        reversal_ratio = float(th.get("reversal_ratio", 0.6))
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

        retraced = (p_mid - p_now) / move  # fraction of the move given back
        if retraced < reversal_ratio:
            return DetectorResult(
                self.name, False, 0.0, {"retraced_ratio": round(retraced, 3)}
            )

        return DetectorResult(
            self.name,
            True,
            PENALTY,
            {
                "prior_move": round(move, 5),
                "retraced_ratio": round(retraced, 3),
                "note": "move reversed — likely fake/overreaction",
            },
        )
