"""D2 — CROSS_BOOK_DIVERGENCE: one book priced away from the consensus.

Compares each book's latest implied probability against the median across
books at the most recent poll. Stale books (no data at the latest poll) are
excluded so suspended/lagging lines can't fake a divergence.
Max contribution: 15 points.
"""
from __future__ import annotations

import statistics

from ..models import DetectorResult, FeatureCtx

MAX_POINTS = 15.0


class DivergenceDetector:
    name = "divergence"

    def detect(self, ctx: FeatureCtx) -> DetectorResult:
        th = ctx.segment.thresholds.get("divergence", {})
        divergence_min = float(th.get("divergence_min", 0.04))

        if not ctx.consensus_series:
            return DetectorResult(self.name, False, 0.0, {"reason": "no data"})
        latest_ts = ctx.consensus_series[-1][0]

        current: dict[str, float] = {
            book: series[-1][1]
            for book, series in ctx.book_series.items()
            if series and series[-1][0] == latest_ts
        }
        if len(current) < 3:
            return DetectorResult(
                self.name, False, 0.0, {"reason": f"only {len(current)} fresh books"}
            )

        median_p = statistics.median(current.values())
        book, p = max(current.items(), key=lambda kv: abs(kv[1] - median_p))
        div = p - median_p
        if abs(div) < divergence_min:
            return DetectorResult(
                self.name, False, 0.0, {"max_divergence": round(div, 5), "book": book}
            )

        # A diverging sharp book is the interesting case — it may be leading.
        is_sharp = book in ctx.segment.sharp_bookmaker_keys
        scale = min((abs(div) - divergence_min) / max(divergence_min, 1e-9), 1.0)
        points = MAX_POINTS * (0.5 + 0.5 * scale)
        if not is_sharp:
            points *= 0.7  # retail outliers are more often stale/soft lines

        return DetectorResult(
            self.name,
            True,
            round(points, 1),
            {
                "book": book,
                "book_p": round(p, 5),
                "consensus_p": round(median_p, 5),
                "divergence": round(div, 5),
                "book_is_sharp": is_sharp,
                "fresh_books": len(current),
                "direction": "shortening" if div > 0 else "drifting",
            },
        )
