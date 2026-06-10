"""Telegram delivery. parse_mode=HTML — escape every dynamic string."""
from __future__ import annotations

import html
import logging
import time
from datetime import datetime, timezone

import httpx

from .settings import settings

log = logging.getLogger(__name__)

API = "https://api.telegram.org"
RETRY_DELAYS = [2, 8, 30]


def escape(text: str) -> str:
    return html.escape(str(text), quote=False)


def format_alert_message(
    *,
    display_label: str,
    segment_key: str,
    home_team: str,
    away_team: str,
    competition: str,
    market_key: str,
    selection: str,
    alert_type: str,
    score: int,
    band: str,
    reason: str,
    kickoff: datetime,
    alert_id: str,
    escalation: bool = False,
    llm_line: str | None = None,
    detector_results: list | None = None,
    consensus_series: list[tuple[datetime, float]] | None = None,
) -> str:
    """Compact format by default; high-band alerts get the expanded evidence block."""
    emoji = "🏆" if segment_key == "world_cup" else "⚽"
    now = datetime.now(timezone.utc)
    ko_delta = kickoff - now
    hours, rem = divmod(max(int(ko_delta.total_seconds()), 0), 3600)

    lines = []
    if escalation:
        lines.append("⬆ <b>ESCALATION</b>")
    lines.append(
        f"{emoji} <b>{escape(display_label)}</b> · {escape(alert_type)} · "
        f"<b>{score}/100</b> ({band.upper()})"
    )
    lines.append(f"{escape(home_team)} vs {escape(away_team)} — {escape(competition)}")
    lines.append(f"{escape(market_key)} · {escape(selection)}")
    lines.append(escape(reason))

    # Expanded evidence block for high-confidence alerts.
    if consensus_series and len(consensus_series) >= 2:
        path = " → ".join(f"{p:.3f}" for _, p in consensus_series[-5:])
        lines.append(f"📈 consensus p: {escape(path)}")
    if detector_results:
        fired = [r for r in detector_results if r.fired]
        breakdown = " ".join(f"{r.detector}({r.points:+.0f})" for r in fired)
        lines.append(f"🧮 {escape(breakdown)}")

    if llm_line:
        lines.append(f"🤖 LLM (advisory): {escape(llm_line)}")

    lines.append(f"🕑 {now.strftime('%Y-%m-%d %H:%M')} UTC · ko in {hours}h {rem // 60}m")
    if settings.app_base_url:
        lines.append(f"🔗 {settings.app_base_url}/alerts/{alert_id}")
    return "\n".join(lines)


def send_notice(chat_id: str, text: str) -> None:
    """One-off operational notice (budget exhausted, worker events). Best-effort."""
    send_message(chat_id, f"ℹ️ {escape(text)}")


def send_message(chat_id: str, text: str) -> tuple[int | None, str | None]:
    """Send with retry. Returns (message_id, error)."""
    last_error: str | None = None
    for attempt, delay in enumerate([0, *RETRY_DELAYS]):
        if delay:
            time.sleep(delay)
        try:
            resp = httpx.post(
                f"{API}/bot{settings.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text[:4096],
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            body = resp.json()
            if body.get("ok"):
                return body["result"]["message_id"], None
            last_error = body.get("description", f"HTTP {resp.status_code}")
            if resp.status_code == 400:
                break  # formatting error — retrying won't help
        except httpx.HTTPError as exc:
            last_error = str(exc)
        log.warning("telegram send attempt %d failed: %s", attempt + 1, last_error)
    return None, last_error
