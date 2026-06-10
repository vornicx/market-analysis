"""Normalization of raw Odds API payloads."""
from worker.normalize import to_snapshots

from .conftest import make_segment

SAMPLE = [
    {
        "id": "abc123",
        "sport_key": "soccer_fifa_world_cup",
        "commence_time": "2026-06-11T18:00:00Z",
        "home_team": "Brazil",
        "away_team": "France",
        "bookmakers": [
            {
                "key": "pinnacle",
                "last_update": "2026-06-10T12:00:00Z",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Brazil", "price": 2.10},
                            {"name": "France", "price": 3.40},
                            {"name": "Draw", "price": 3.30},
                        ],
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "price": 1.90, "point": 2.5},
                            {"name": "Under", "price": 1.92, "point": 2.5},
                        ],
                    },
                ],
            },
            {
                "key": "unlisted_book",
                "markets": [
                    {"key": "h2h", "outcomes": [{"name": "Brazil", "price": 2.0}]}
                ],
            },
        ],
    }
]


def test_converts_prices_to_implied_prob():
    snaps = to_snapshots(SAMPLE, make_segment(), "cycle-1")
    brazil = next(s for s in snaps if s.selection_name == "Brazil" and s.market_key == "h2h")
    assert abs(brazil.implied_prob - 1 / 2.10) < 1e-4
    assert brazil.segment_key == "world_cup"


def test_filters_unconfigured_bookmakers():
    snaps = to_snapshots(SAMPLE, make_segment(), "cycle-1")
    assert all(s.bookmaker_key != "unlisted_book" for s in snaps)


def test_totals_carry_the_line():
    snaps = to_snapshots(SAMPLE, make_segment(), "cycle-1")
    over = next(s for s in snaps if s.selection_name == "Over")
    assert over.line == 2.5


def test_malformed_price_skipped():
    bad = [dict(SAMPLE[0])]
    bad[0]["bookmakers"] = [
        {
            "key": "pinnacle",
            "markets": [{"key": "h2h", "outcomes": [{"name": "Brazil", "price": 1.0}]}],
        }
    ]
    assert to_snapshots(bad, make_segment(), "c") == []
