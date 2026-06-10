"""LLM response parsing/validation — pure logic, no network."""
import pytest

from worker.llm import parse_response

VALID = (
    '{"classification": "possible_sharp_move", "summary": "Pinnacle led the move.", '
    '"confidence": "medium", "caveats": ["sparse polling"]}'
)


def test_parses_plain_json():
    payload = parse_response(VALID)
    assert payload["classification"] == "possible_sharp_move"


def test_strips_code_fences():
    payload = parse_response(f"```json\n{VALID}\n```")
    assert payload["confidence"] == "medium"


def test_rejects_unknown_classification():
    bad = VALID.replace("possible_sharp_move", "definitely_bet_now")
    with pytest.raises(Exception):
        parse_response(bad)


def test_rejects_extra_fields():
    bad = VALID[:-1] + ', "recommended_stake": 100}'
    with pytest.raises(Exception):
        parse_response(bad)


def test_rejects_overlong_summary():
    bad = VALID.replace("Pinnacle led the move.", "x" * 300)
    with pytest.raises(Exception):
        parse_response(bad)


def test_rejects_non_json():
    with pytest.raises(Exception):
        parse_response("I think this is a sharp move because...")
