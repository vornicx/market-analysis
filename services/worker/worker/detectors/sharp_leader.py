"""D4 — SHARP_LEADER: a sharp book moves first, retail books follow.

The strongest free proxy for informed money. Two patterns:
- lead-follow (full points): sharp moved >= sharp_dp_min in the PREVIOUS
  interval, and >= follower_count_min retail books moved the same direction in
  the LATEST interval.
- simultaneous (60% points): sharp + followers all moved in the latest
  interval. Weaker — public news can explain simultaneous moves.
Max contribution: 30 points.
"""
from __future__ import annotations

from ..models import DetectorResult, FeatureCtx

MAX_POINTS = 30.0
FOLLOW_DP_MIN = 0.008  # a retail "follow" must be non-trivial


class SharpLeaderDetector:
    name = "sharp_leader"

    def detect(self, ctx: FeatureCtx) -> DetectorResult:
        th = ctx.segment.thresholds.get("sharp_leader", {})
        sharp_dp_min = float(th.get("sharp_dp_min", 0.025))
        follower_min = int(th.get("follower_count_min", 2))

        sharps = [b for b in ctx.segment.sharp_bookmaker_keys if b in ctx.book_series]
        if not sharps:
            return DetectorResult(self.name, False, 0.0, {"reason": "no sharp book data"})

        for sharp in sharps:
            series = ctx.book_series[sharp]

            # Pattern A: sharp led in the previous interval.
            if len(series) >= 3:
                sharp_dp = series[-2][1] - series[-3][1]
                if abs(sharp_dp) >= sharp_dp_min:
                    sign = 1 if sharp_dp > 0 else -1
                    followers = self._followers(ctx, sharp, sign, interval=-1)
                    if len(followers) >= follower_min:
                        return DetectorResult(
                            self.name, True, MAX_POINTS,
                            {
                                "pattern": "lead_follow",
                                "sharp_book": sharp,
                                "sharp_dp": round(sharp_dp, 5),
                                "followers": sorted(followers),
                                "direction": "shortening" if sign > 0 else "drifting",
                            },
                        )

            # Pattern B: simultaneous sharp + retail move in the latest interval.
            if len(series) >= 2:
                sharp_dp = series[-1][1] - series[-2][1]
                if abs(sharp_dp) >= sharp_dp_min:
                    sign = 1 if sharp_dp > 0 else -1
                    followers = self._followers(ctx, sharp, sign, interval=-1)
                    if len(followers) >= follower_min:
                        return DetectorResult(
                            self.name, True, round(MAX_POINTS * 0.6, 1),
                            {
                                "pattern": "simultaneous",
                                "sharp_book": sharp,
                                "sharp_dp": round(sharp_dp, 5),
                                "followers": sorted(followers),
                                "direction": "shortening" if sign > 0 else "drifting",
                            },
                        )

        return DetectorResult(self.name, False, 0.0, {"reason": "no sharp-led pattern"})

    @staticmethod
    def _followers(ctx: FeatureCtx, sharp: str, sign: int, interval: int) -> set[str]:
        followers: set[str] = set()
        for book, series in ctx.book_series.items():
            if book == sharp or book in ctx.segment.sharp_bookmaker_keys:
                continue
            if len(series) < 2:
                continue
            d = series[interval][1] - series[interval - 1][1]
            if d * sign >= FOLLOW_DP_MIN:
                followers.add(book)
        return followers
