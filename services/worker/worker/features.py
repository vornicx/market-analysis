"""Build FeatureCtx objects: per-book and consensus implied-prob series."""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime

from supabase import Client

from . import persistence
from .models import FeatureCtx, Segment, Snapshot


def build_ctx(
    db: Client, segment: Segment, snap: Snapshot, event_id: str, selection_id: str
) -> FeatureCtx:
    rows = persistence.fetch_series(db, selection_id)

    by_book: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    for r in rows:
        ts = datetime.fromisoformat(r["polled_at"].replace("Z", "+00:00"))
        by_book[r["bookmaker_key"]].append((ts, float(r["implied_prob"])))
    for series in by_book.values():
        series.sort(key=lambda x: x[0])  # oldest -> newest

    # Consensus = median implied prob across books per poll timestamp bucket.
    by_ts: dict[datetime, list[float]] = defaultdict(list)
    for series in by_book.values():
        for ts, p in series:
            by_ts[ts].append(p)
    consensus = [
        (ts, statistics.median(ps)) for ts, ps in sorted(by_ts.items(), key=lambda x: x[0])
    ]

    # Baseline |dp| samples from consensus history (cheap proxy; per-segment
    # market-wide baseline is the 14-day-plan upgrade).
    baseline = [
        abs(consensus[i][1] - consensus[i - 1][1]) for i in range(1, len(consensus))
    ]

    return FeatureCtx(
        segment=segment,
        snapshot=snap,
        selection_id=selection_id,
        event_id=event_id,
        book_series=dict(by_book),
        consensus_series=consensus,
        baseline_dps=baseline,
    )
