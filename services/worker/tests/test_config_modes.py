"""The mode truth table (blueprint §6) — all flag combinations."""
import pytest

from worker.config import resolve_active_segments

from .conftest import make_config, make_segment


def segments():
    return {
        "general_football": make_segment("general_football", sport_keys=["soccer_epl"]),
        "world_cup": make_segment("world_cup"),
    }


@pytest.mark.parametrize(
    "football,wc,wc_only,expected",
    [
        (True, True, False, ["general_football", "world_cup"]),
        (True, False, False, ["general_football"]),
        (False, True, False, ["world_cup"]),
        (False, False, False, []),
        (True, True, True, ["world_cup"]),   # only-mode suppresses general
        (False, True, True, ["world_cup"]),
        (True, False, True, []),             # misconfig: only-mode but WC off
        (False, False, True, []),
    ],
)
def test_truth_table(football, wc, wc_only, expected):
    cfg = make_config(
        football_enabled=football,
        world_cup_enabled=wc,
        world_cup_only_mode=wc_only,
    )
    active = resolve_active_segments(cfg, segments())
    assert [s.segment_key for s in active] == expected


def test_global_pause_overrides_everything():
    cfg = make_config(
        football_enabled=True, world_cup_enabled=True, global_pause=True
    )
    assert resolve_active_segments(cfg, segments()) == []


def test_segment_level_disable_gates_activation():
    cfg = make_config(world_cup_enabled=True, world_cup_only_mode=True)
    segs = segments()
    segs["world_cup"] = make_segment("world_cup", enabled=False)
    assert resolve_active_segments(cfg, segs) == []
