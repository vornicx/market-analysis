"""Normalize raw Odds API payloads into typed Snapshot rows (implied probability)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import Segment, Snapshot


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def to_snapshots(
    raw_events: list[dict[str, Any]], segment: Segment, poll_cycle_id: str
) -> list[Snapshot]:
    snaps: list[Snapshot] = []
    for ev in raw_events:
        commence = _parse_ts(ev["commence_time"])
        assert commence is not None
        for book in ev.get("bookmakers", []):
            if book["key"] not in segment.bookmaker_keys:
                continue
            book_update = _parse_ts(book.get("last_update"))
            for market in book.get("markets", []):
                if market["key"] not in segment.market_keys:
                    continue
                for outcome in market.get("outcomes", []):
                    price = float(outcome["price"])
                    if price <= 1.0:
                        continue  # malformed / suspended
                    snaps.append(
                        Snapshot(
                            provider_event_id=ev["id"],
                            sport_key=ev["sport_key"],
                            segment_key=segment.segment_key,
                            home_team=ev["home_team"],
                            away_team=ev["away_team"],
                            commence_time=commence,
                            bookmaker_key=book["key"],
                            market_key=market["key"],
                            selection_name=outcome["name"],
                            line=outcome.get("point"),
                            price_decimal=price,
                            implied_prob=round(1.0 / price, 5),
                            book_last_update=book_update,
                            poll_cycle_id=poll_cycle_id,
                        )
                    )
    return snaps
