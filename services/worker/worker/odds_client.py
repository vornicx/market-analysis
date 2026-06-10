"""The Odds API client with credit accounting and retries."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from .settings import settings

log = logging.getLogger(__name__)


class OddsApiClient:
    def __init__(self) -> None:
        self._http = httpx.Client(
            base_url=settings.odds_api_base_url,
            timeout=20,
            transport=httpx.HTTPTransport(retries=3),
        )
        self.last_remaining: int | None = None

    def fetch_events(self, sport_key: str) -> list[dict[str, Any]]:
        """Upcoming events for a sport. Costs 0 credits on The Odds API."""
        resp = self._http.get(
            f"/sports/{sport_key}/events", params={"apiKey": settings.odds_api_key}
        )
        resp.raise_for_status()
        self._track_quota(resp)
        return resp.json()

    def fetch_odds(
        self,
        sport_key: str,
        region: str,
        market_keys: list[str],
        bookmaker_keys: list[str],
        event_ids: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Fetch odds. Returns (raw events, credits charged ≈ markets × regions)."""
        params: dict[str, str] = {
            "apiKey": settings.odds_api_key,
            "regions": region,
            "markets": ",".join(market_keys),
            "bookmakers": ",".join(bookmaker_keys),
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
        if event_ids:
            params["eventIds"] = ",".join(event_ids)
        resp = self._http.get(f"/sports/{sport_key}/odds", params=params)
        if resp.status_code == 429:
            log.warning("Odds API rate limited — treating as budget signal")
            return [], 0
        resp.raise_for_status()
        self._track_quota(resp)
        credits = int(resp.headers.get("x-requests-last", len(market_keys)))
        return resp.json(), credits

    def _track_quota(self, resp: httpx.Response) -> None:
        remaining = resp.headers.get("x-requests-remaining")
        if remaining is not None:
            self.last_remaining = int(float(remaining))

    def close(self) -> None:
        self._http.close()
