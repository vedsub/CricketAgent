from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from data.fetcher import CricAPIClient
from data.parser import summarize_matches


@tool
async def fetch_current_matches(offset: int = 0) -> list[dict[str, Any]]:
    """Fetch and normalize the current match list from the configured cricket data provider."""

    client = CricAPIClient()
    try:
        payload = await client.get_current_matches(offset=offset)
    finally:
        await client.aclose()
    return summarize_matches(payload)


@tool
def build_playing_xi_shortlist(players: list[str], preferred_team_size: int = 11) -> dict[str, list[str]]:
    """Split a squad into a starting XI and bench using the current ordering as a placeholder."""

    return {
        "playing_xi": players[:preferred_team_size],
        "bench": players[preferred_team_size:],
    }


@tool
def suggest_toss_plan(match_format: str, venue: str) -> dict[str, str]:
    """Return a simple toss recommendation that can be replaced with richer venue logic later."""

    normalized = match_format.upper()
    decision = "Bowl first" if normalized in {"T20", "T20I"} else "Assess conditions"
    return {
        "venue": venue,
        "match_format": normalized,
        "decision_if_win_toss": decision,
    }
