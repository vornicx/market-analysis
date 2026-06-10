"""Optional LLM annotation layer. NEVER a detector, NEVER blocks delivery.

Annotates alerts at/above llm_min_band with a classification + short summary.
Any failure (missing key, timeout, invalid JSON) degrades to status
'failed'/'skipped' and the alert ships without annotation.
"""
from __future__ import annotations

import json
import logging

from jsonschema import validate as js_validate
from supabase import Client

from .models import FeatureCtx, GlobalConfig, ScoredAnomaly
from .settings import settings

log = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5"
TIMEOUT_SECONDS = 6
BAND_ORDER = {"low": 0, "medium": 1, "high": 2}

SYSTEM_PROMPT = (
    "You are an odds-market analyst assistant. You receive a pre-computed anomaly "
    "report from a deterministic detection system for a pre-match football betting "
    "market. Your job is ONLY to classify and summarize. You must not invent facts, "
    "news, injuries, or numbers not present in the input. If evidence is ambiguous, "
    'classify as "needs_human_review". Output ONLY valid JSON matching: '
    '{"classification": one of [possible_sharp_move, possible_market_correction, '
    "possible_news_driven_move, possible_noise, needs_human_review], "
    '"summary": string <= 280 chars, "confidence": low|medium|high, '
    '"caveats": array of <= 3 short strings}'
)

OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["classification", "summary", "confidence", "caveats"],
    "additionalProperties": False,
    "properties": {
        "classification": {
            "enum": [
                "possible_sharp_move",
                "possible_market_correction",
                "possible_news_driven_move",
                "possible_noise",
                "needs_human_review",
            ]
        },
        "summary": {"type": "string", "maxLength": 280},
        "confidence": {"enum": ["low", "medium", "high"]},
        "caveats": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
    },
}


def _digest(ctx: FeatureCtx, scored: ScoredAnomaly) -> str:
    s = ctx.snapshot
    fired = [r for r in scored.detector_results if r.fired]
    detector_summary = "; ".join(f"{r.detector}({r.points:+.0f}): {r.evidence}" for r in fired)
    consensus = " ".join(f"{p:.3f}@{ts.strftime('%H:%M')}" for ts, p in ctx.consensus_series[-6:])
    books_now = {
        book: round(series[-1][1], 3) for book, series in ctx.book_series.items() if series
    }
    return (
        f"ANOMALY REPORT\n"
        f"segment: {ctx.segment.display_label}\n"
        f"match: {s.home_team} vs {s.away_team} ({s.sport_key}, kickoff {s.commence_time:%Y-%m-%d %H:%M} UTC)\n"
        f"market: {s.market_key} / selection: {s.selection_name} {s.line if s.line is not None else ''}\n"
        f"detectors_fired: {detector_summary}\n"
        f"consensus_implied_prob_series: {consensus}\n"
        f"books_implied_prob_now: {books_now}\n"
        f"score: {scored.score}/100 band {scored.band}\n"
        f"Respond with JSON only."
    )


def annotate(
    db: Client,
    config: GlobalConfig,
    ctx: FeatureCtx,
    scored: ScoredAnomaly,
    alert_id: str,
) -> None:
    if BAND_ORDER[scored.band] < BAND_ORDER.get(config.llm_min_band, 1):
        _record(db, alert_id, status="skipped")
        return
    if not settings.anthropic_api_key:
        _record(db, alert_id, status="skipped")
        return

    try:
        import anthropic
    except ImportError:
        log.warning("anthropic package not installed — pip install '.[llm]'")
        _record(db, alert_id, status="skipped")
        return

    try:
        client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key, timeout=TIMEOUT_SECONDS
        )
        prompt = _digest(ctx, scored)
        msg = client.messages.create(
            model=MODEL,
            max_tokens=300,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()
        payload = json.loads(text)
        js_validate(payload, OUTPUT_SCHEMA)
        _record(
            db,
            alert_id,
            status="ok",
            classification=payload["classification"],
            summary=payload["summary"],
            confidence=payload["confidence"],
            raw=payload,
            tokens_in=msg.usage.input_tokens,
            tokens_out=msg.usage.output_tokens,
        )
    except Exception as exc:
        log.warning("LLM annotation failed for alert %s: %s", alert_id, exc)
        _record(db, alert_id, status="failed")


def _record(db: Client, alert_id: str, status: str, **fields: object) -> None:
    try:
        db.table("llm_analyses").upsert(
            {"alert_id": alert_id, "status": status, "model": MODEL, **fields},
            on_conflict="alert_id",
        ).execute()
    except Exception:
        log.exception("failed to record llm analysis for %s", alert_id)
