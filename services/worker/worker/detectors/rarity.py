"""D7 — RARITY: how unusual is this move vs the recent baseline?

Percentile of the latest |consensus move| within the trailing distribution of
moves. Deliberately inert until enough baseline samples exist (cold start).
Max contribution: 15 points.
"""
from __future__ import annotations

from ..models import DetectorResult, FeatureCtx

MAX_POINTS = 15.0


class RarityDetector:
    name = "rarity"

    def detect(self, ctx: FeatureCtx) -> DetectorResult:
        th = ctx.segment.thresholds.get("rarity", {})
        pctile_min = float(th.get("rarity_pctile_min", 97))
        min_samples = int(th.get("rarity_min_samples", 300))

        if len(ctx.consensus_series) < 2:
            return DetectorResult(self.name, False, 0.0, {"reason": "no current move"})
        if len(ctx.baseline_dps) < min_samples:
            return DetectorResult(
                self.name, False, 0.0,
                {"reason": f"baseline too thin ({len(ctx.baseline_dps)}/{min_samples})"},
            )

        current = abs(ctx.consensus_series[-1][1] - ctx.consensus_series[-2][1])
        below = sum(1 for d in ctx.baseline_dps if d < current)
        pctile = 100.0 * below / len(ctx.baseline_dps)

        if pctile < pctile_min:
            return DetectorResult(self.name, False, 0.0, {"pctile": round(pctile, 1)})

        scale = (pctile - pctile_min) / max(100.0 - pctile_min, 1e-9)
        points = MAX_POINTS * (0.6 + 0.4 * scale)
        return DetectorResult(
            self.name,
            True,
            round(points, 1),
            {
                "pctile": round(pctile, 1),
                "current_dp": round(current, 5),
                "baseline_n": len(ctx.baseline_dps),
            },
        )
