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
) -> str:
    emoji = "🏆" if segment_key == "world_cup" else "⚽"
    now = datetime.now(timezone.utc)
    ko_delta = kickoff - now
    hours, rem = divmod(max(int(ko_delta.total_seconds()), 0), 3600)
    link = f"\n🔗 {settings.app_base_url}/alerts/{alert_id}" if settings.app_base_url else ""
    return (
        f"{emoji} <b>{escape(display_label)}</b> · {escape(alert_type)} · "
        f"<b>{score}/100</b> ({band.upper()})\n"
        f"{escape(home_team)} vs {escape(away_team)} — {escape(competition)}\n"
        f"{escape(market_key)} · {escape(selection)}\n"
        f"{escape(reason)}\n"
        f"🕑 {now.strftime('%Y-%m-%d %H:%M')} UTC · ko in {hours}h {rem // 60}m"
        f"{link}"
    )


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
