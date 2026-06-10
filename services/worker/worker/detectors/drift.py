"""D3 — SUSTAINED_DRIFT: same-direction consensus movement across N polls.

Slow steam: each individual move may be small, but 3+ consecutive polls in the
same direction with meaningful cumulative magnitude is a directional market.
Max contribution: 20 points.
"""
from __future__ import annotations

from ..models import DetectorResult, FeatureCtx

MAX_POINTS = 20.0


class DriftDetector:
    name = "drift"

    def detect(self, ctx: FeatureCtx) -> DetectorResult:
        th = ctx.segment.thresholds.get("drift", {})
        polls_min = int(th.get("drift_polls_min", 3))
        cum_min = float(th.get("drift_cum_min", 0.04))

        series = ctx.consensus_series
        if len(series) < polls_min + 1:
            return DetectorResult(self.name, False, 0.0, {"reason": "insufficient history"})

        # Count consecutive same-sign deltas walking back from the latest poll.
        deltas = [series[i][1] - series[i - 1][1] for i in range(1, len(series))]
        last = deltas[-1]
        if abs(last) < 1e-6:
            return DetectorResult(self.name, False, 0.0, {"reason": "flat latest poll"})
        sign = 1 if last > 0 else -1

        streak = 0
        cum = 0.0
        for d in reversed(deltas):
            if d * sign <= 0:
                break
            streak += 1
            cum += d

        if streak < polls_min or abs(cum) < cum_min:
            return DetectorResult(
                self.name, False, 0.0,
                {"streak": streak, "cum_dp": round(cum, 5)},
            )

        scale = min((abs(cum) - cum_min) / max(cum_min, 1e-9), 1.0)
        points = MAX_POINTS * (0.6 + 0.4 * scale)
        return DetectorResult(
            self.name,
            True,
            round(points, 1),
            {
                "streak": streak,
                "cum_dp": round(cum, 5),
                "direction": "shortening" if sign > 0 else "drifting",
                "from_p": round(series[-1 - streak][1], 5),
                "to_p": round(series[-1][1], 5),
            },
        )
