"""Fire / no-fire scenarios for every detector with synthetic series."""
from worker.detectors.divergence import DivergenceDetector
from worker.detectors.drift import DriftDetector
from worker.detectors.persistence_amp import PersistenceAmpDetector
from worker.detectors.price_move import PriceMoveDetector
from worker.detectors.rarity import RarityDetector
from worker.detectors.reversal import ReversalDetector
from worker.detectors.sharp_leader import SharpLeaderDetector

from .conftest import make_ctx


# ── D1 price_move ──────────────────────────────────────────────────────────
def test_price_move_fires_on_big_consensus_move():
    ctx = make_ctx(
        consensus=[0.50, 0.55],
        books={"pinnacle": [0.50, 0.55], "bet365": [0.50, 0.54]},
    )
    r = PriceMoveDetector().detect(ctx)
    assert r.fired and r.points > 0
    assert r.evidence["direction"] == "shortening"


def test_price_move_quiet_market_does_not_fire():
    ctx = make_ctx(consensus=[0.50, 0.505])
    assert not PriceMoveDetector().detect(ctx).fired


def test_price_move_lone_retail_book_discounted():
    full = PriceMoveDetector().detect(
        make_ctx(consensus=[0.50, 0.55],
                 books={"pinnacle": [0.50, 0.55], "bet365": [0.50, 0.54]})
    )
    lone = PriceMoveDetector().detect(
        make_ctx(consensus=[0.50, 0.55], books={"bet365": [0.50, 0.55]})
    )
    assert lone.fired and lone.points < full.points


# ── D2 divergence ──────────────────────────────────────────────────────────
def test_divergence_fires_on_outlier_book():
    ctx = make_ctx(
        consensus=[0.50, 0.50],
        books={
            "pinnacle": [0.50, 0.56],
            "bet365": [0.50, 0.50],
            "unibet": [0.50, 0.50],
            "williamhill": [0.50, 0.50],
        },
    )
    r = DivergenceDetector().detect(ctx)
    assert r.fired and r.evidence["book"] == "pinnacle"


def test_divergence_needs_three_fresh_books():
    ctx = make_ctx(consensus=[0.50, 0.50], books={"pinnacle": [0.50, 0.58]})
    assert not DivergenceDetector().detect(ctx).fired


# ── D3 drift ───────────────────────────────────────────────────────────────
def test_drift_fires_on_sustained_directional_move():
    ctx = make_ctx(consensus=[0.50, 0.515, 0.53, 0.55])
    r = DriftDetector().detect(ctx)
    assert r.fired and r.evidence["streak"] >= 3


def test_drift_broken_streak_does_not_fire():
    ctx = make_ctx(consensus=[0.50, 0.52, 0.51, 0.53])
    assert not DriftDetector().detect(ctx).fired


# ── D4 sharp_leader ────────────────────────────────────────────────────────
def test_sharp_leader_lead_follow_full_points():
    ctx = make_ctx(
        consensus=[0.50, 0.53, 0.54],
        books={
            "pinnacle": [0.50, 0.55, 0.55],   # sharp moved first
            "bet365": [0.50, 0.50, 0.53],     # retail followed next poll
            "unibet": [0.50, 0.50, 0.52],
        },
    )
    r = SharpLeaderDetector().detect(ctx)
    assert r.fired and r.evidence["pattern"] == "lead_follow"
    assert r.points == 30.0


def test_sharp_leader_simultaneous_discounted():
    ctx = make_ctx(
        consensus=[0.50, 0.54],
        books={
            "pinnacle": [0.50, 0.54],
            "bet365": [0.50, 0.53],
            "unibet": [0.50, 0.52],
        },
    )
    r = SharpLeaderDetector().detect(ctx)
    assert r.fired and r.evidence["pattern"] == "simultaneous"
    assert r.points < 30.0


def test_sharp_leader_no_followers_no_fire():
    ctx = make_ctx(
        consensus=[0.50, 0.53],
        books={"pinnacle": [0.50, 0.55], "bet365": [0.50, 0.50]},
    )
    assert not SharpLeaderDetector().detect(ctx).fired


# ── D5 persistence ─────────────────────────────────────────────────────────
def test_persistence_fires_when_move_holds():
    ctx = make_ctx(consensus=[0.50, 0.55, 0.548])
    r = PersistenceAmpDetector().detect(ctx)
    assert r.fired and r.evidence["retained_ratio"] > 0.9


def test_persistence_does_not_fire_when_move_fades():
    ctx = make_ctx(consensus=[0.50, 0.55, 0.515])
    assert not PersistenceAmpDetector().detect(ctx).fired


# ── D6 reversal (suppressor) ───────────────────────────────────────────────
def test_reversal_penalizes_retraced_move():
    ctx = make_ctx(consensus=[0.50, 0.55, 0.51])
    r = ReversalDetector().detect(ctx)
    assert r.fired and r.points == -20.0


def test_reversal_ignores_held_move():
    ctx = make_ctx(consensus=[0.50, 0.55, 0.55])
    assert not ReversalDetector().detect(ctx).fired


# ── D7 rarity ──────────────────────────────────────────────────────────────
def test_rarity_fires_on_extreme_move_with_baseline():
    baseline = [0.002] * 50  # normal moves are tiny
    ctx = make_ctx(consensus=[0.50, 0.55], baseline_dps=baseline)
    r = RarityDetector().detect(ctx)
    assert r.fired and r.evidence["pctile"] >= 97


def test_rarity_inert_on_thin_baseline():
    ctx = make_ctx(consensus=[0.50, 0.55], baseline_dps=[0.002] * 5)
    r = RarityDetector().detect(ctx)
    assert not r.fired and "baseline too thin" in r.evidence["reason"]
