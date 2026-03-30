from __future__ import annotations

from typing import Any

import httpx

from config import CRICAPI_KEY


class CricAPIClient:
    """Minimal async client for CricAPI-style endpoints."""

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.cricapi.com/v1"):
        self.api_key = api_key or CRICAPI_KEY
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=20.0)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = {"apikey": self.api_key}
        if params:
            query.update(params)
        response = await self._client.get(f"{self.base_url}/{path.lstrip('/')}", params=query)
        response.raise_for_status()
        return response.json()

    async def get_current_matches(self, offset: int = 0) -> dict[str, Any]:
        return await self._get("currentMatches", {"offset": offset})

    async def get_match_scorecard(self, match_id: str) -> dict[str, Any]:
        return await self._get("match_scorecard", {"id": match_id})

    async def get_player_info(self, player_id: str) -> dict[str, Any]:
        return await self._get("players_info", {"id": player_id})

    async def aclose(self) -> None:
        await self._client.aclose()
