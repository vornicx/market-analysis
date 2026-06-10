"""Pure logic of alerting (dedupe key) and telegram formatting. No network."""
from datetime import datetime, timezone

from worker.alerting import dedupe_key
from worker.models import DetectorResult, ScoredAnomaly
from worker.telegram import escape, format_alert_message

from .conftest import make_ctx


def scored(direction="shortening", band="medium", score=65) -> ScoredAnomaly:
    return ScoredAnomaly(
        score=score,
        band=band,
        alert_type="PRICE_SPIKE",
        reason_summary="test reason",
        direction=direction,
        detector_results=[DetectorResult("price_move", True, 25, {})],
    )


def test_dedupe_key_stable_within_window():
    ctx = make_ctx(consensus=[0.5, 0.55])
    assert dedupe_key(ctx, scored(), 90) == dedupe_key(ctx, scored(), 90)


def test_dedupe_key_direction_sensitive():
    ctx = make_ctx(consensus=[0.5, 0.55])
    assert dedupe_key(ctx, scored("shortening"), 90) != dedupe_key(ctx, scored("drifting"), 90)


def test_escape_handles_html_entities():
    assert escape("Brighton & Hove <FC>") == "Brighton &amp; Hove &lt;FC&gt;"


def base_kwargs():
    return dict(
        display_label="WORLD CUP",
        segment_key="world_cup",
        home_team="Brazil",
        away_team="France",
        competition="soccer_fifa_world_cup",
        market_key="h2h",
        selection="Brazil",
        alert_type="SHARP_MOVE",
        score=82,
        band="high",
        reason="Pinnacle led, 3 books followed",
        kickoff=datetime(2026, 6, 11, 18, 0, tzinfo=timezone.utc),
        alert_id="abc-123",
    )


def test_message_carries_segment_label_and_score():
    msg = format_alert_message(**base_kwargs())
    assert "🏆" in msg and "WORLD CUP" in msg and "82/100" in msg


def test_message_escapes_team_names():
    kwargs = base_kwargs() | {"home_team": "Atlético <M>", "away_team": "B & C"}
    msg = format_alert_message(**kwargs)
    assert "<M>" not in msg and "&amp;" in msg


def test_escalation_prefix():
    msg = format_alert_message(**base_kwargs(), escalation=True)
    assert msg.startswith("⬆ <b>ESCALATION</b>")


def test_high_band_includes_expanded_evidence():
    msg = format_alert_message(
        **base_kwargs(),
        detector_results=[DetectorResult("sharp_leader", True, 30, {})],
        consensus_series=[
            (datetime(2026, 6, 10, h, 0, tzinfo=timezone.utc), 0.5 + h / 100)
            for h in range(5)
        ],
    )
    assert "🧮" in msg and "sharp_leader(+30)" in msg and "📈" in msg


def test_llm_line_labeled_advisory():
    msg = format_alert_message(**base_kwargs(), llm_line="possible sharp move: x")
    assert "🤖 LLM (advisory):" in msg


def test_message_under_telegram_limit():
    msg = format_alert_message(
        **base_kwargs(),
        detector_results=[DetectorResult(f"d{i}", True, 10, {}) for i in range(7)],
        consensus_series=[
            (datetime(2026, 6, 10, 0, i, tzinfo=timezone.utc), 0.5) for i in range(10)
        ],
        llm_line="x" * 280,
    )
    assert len(msg) < 4096
