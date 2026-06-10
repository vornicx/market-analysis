"""Score assembly: bands, types, suppressors, no-fire."""
from worker.detectors import REGISTRY
from worker.models import DetectorResult
from worker.scoring import assemble, band_for

from .conftest import make_ctx


def dr(name: str, fired: bool, points: float) -> DetectorResult:
    return DetectorResult(name, fired, points, {"direction": "shortening"})


def test_band_boundaries():
    assert band_for(80) == "high"
    assert band_for(79) == "medium"
    assert band_for(60) == "medium"
    assert band_for(59) == "low"


def test_no_fired_detectors_returns_none():
    ctx = make_ctx(consensus=[0.5, 0.5])
    assert assemble([dr("price_move", False, 0)], ctx) is None


def test_sharp_leader_dominates_type():
    ctx = make_ctx(consensus=[0.5, 0.55])
    scored = assemble(
        [dr("sharp_leader", True, 30), dr("price_move", True, 20)], ctx
    )
    assert scored is not None
    assert scored.alert_type == "SHARP_MOVE"
    assert scored.score == 50


def test_reversal_suppresses_score():
    ctx = make_ctx(consensus=[0.5, 0.55, 0.51])
    with_penalty = assemble(
        [dr("price_move", True, 25), dr("reversal", True, -20)], ctx
    )
    without = assemble([dr("price_move", True, 25)], ctx)
    assert with_penalty is not None and without is not None
    assert with_penalty.score == without.score - 20


def test_score_clamped_to_100():
    ctx = make_ctx(consensus=[0.5, 0.55])
    scored = assemble(
        [
            dr("sharp_leader", True, 30),
            dr("price_move", True, 25),
            dr("drift", True, 20),
            dr("persistence_amp", True, 15),
            dr("divergence", True, 15),
            dr("rarity", True, 15),
        ],
        ctx,
    )
    assert scored is not None and scored.score == 100 and scored.band == "high"


def test_full_pipeline_steam_scenario_scores_high():
    """End-to-end: a sharp-led sustained move through the real registry.

    Pinnacle jumps in the second-to-last interval (lead), retail books follow
    in the latest interval, and the consensus has drifted up 3 polls in a row.
    """
    ctx = make_ctx(
        consensus=[0.50, 0.51, 0.53, 0.57],
        books={
            "pinnacle": [0.50, 0.52, 0.56, 0.57],
            "bet365": [0.50, 0.505, 0.52, 0.56],
            "unibet": [0.50, 0.505, 0.515, 0.55],
            "williamhill": [0.50, 0.50, 0.51, 0.54],
        },
    )
    results = [d.detect(ctx) for d in REGISTRY]
    scored = assemble(results, ctx)
    assert scored is not None
    assert scored.score >= ctx.segment.min_alert_score
    assert scored.alert_type == "SHARP_MOVE"
    fired = {r.detector for r in results if r.fired}
    assert {"sharp_leader", "drift", "price_move"} <= fired


def test_full_pipeline_quiet_market_no_alert():
    ctx = make_ctx(
        consensus=[0.50, 0.501, 0.499, 0.50],
        books={
            "pinnacle": [0.50, 0.50, 0.50, 0.50],
            "bet365": [0.50, 0.501, 0.499, 0.50],
            "unibet": [0.50, 0.50, 0.499, 0.501],
        },
    )
    results = [d.detect(ctx) for d in REGISTRY]
    assert assemble(results, ctx) is None
