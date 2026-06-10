"""D1 — PRICE_MOVE: unusual single-interval implied-probability move.

Fires when the consensus implied probability moved more than abs_dp_min (or the
z-score vs the segment baseline exceeds z_min) since the previous poll. Single
retail-book moves earn half points; multi-book or sharp-book moves earn full.
Max contribution: 25 points.
"""
from __future__ import annotations

import statistics

from ..models import DetectorResult, FeatureCtx

MAX_POINTS = 25.0


class PriceMoveDetector:
    name = "price_move"

    def detect(self, ctx: FeatureCtx) -> DetectorResult:
        th = ctx.segment.thresholds.get("price_move", {})
        abs_dp_min = float(th.get("abs_dp_min", 0.03))
        z_min = float(th.get("z_min", 3.0))

        if len(ctx.consensus_series) < 2:
            return DetectorResult(self.name, False, 0.0, {"reason": "insufficient history"})

        p_prev = ctx.consensus_series[-2][1]
        p_now = ctx.consensus_series[-1][1]
        dp = p_now - p_prev
        abs_dp = abs(dp)

        z = None
        if len(ctx.baseline_dps) >= 30:
            mu = statistics.fmean(ctx.baseline_dps)
            sd = statistics.pstdev(ctx.baseline_dps)
            if sd > 1e-9:
                z = (abs_dp - mu) / sd

        fired = abs_dp >= abs_dp_min or (z is not None and z >= z_min)
        if not fired:
            return DetectorResult(self.name, False, 0.0, {"dp": round(dp, 5), "z": z})

        # Scale points linearly from threshold to 2x threshold.
        scale = min((abs_dp - abs_dp_min) / max(abs_dp_min, 1e-9), 1.0)
        points = MAX_POINTS * (0.5 + 0.5 * scale)

        movers = self._books_that_moved(ctx, direction=1 if dp > 0 else -1)
        sharp_moved = any(b in ctx.segment.sharp_bookmaker_keys for b in movers)
        if len(movers) < 2 and not sharp_moved:
            points *= 0.5  # lone retail book — discount heavily

        return DetectorResult(
            self.name,
            True,
            round(points, 1),
            {
                "dp": round(dp, 5),
                "abs_dp": round(abs_dp, 5),
                "z": round(z, 2) if z is not None else None,
                "direction": "shortening" if dp > 0 else "drifting",
                "books_moved": sorted(movers),
                "sharp_moved": sharp_moved,
            },
        )

    @staticmethod
    def _books_that_moved(ctx: FeatureCtx, direction: int) -> set[str]:
        moved: set[str] = set()
        for book, series in ctx.book_series.items():
            if len(series) < 2:
                continue
            d = series[-1][1] - series[-2][1]
            if d * direction > 0.005:  # same direction, non-trivial
                moved.add(book)
        return moved
