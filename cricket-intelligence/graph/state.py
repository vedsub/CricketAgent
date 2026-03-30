from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict


class CricketState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes."""

    request: dict[str, Any]
    raw_data: dict[str, Any]
    eligibility: dict[str, Any]
    venue: dict[str, Any]
    form: dict[str, Any]
    batter: dict[str, Any]
    bowler: dict[str, Any]
    matchup: dict[str, Any]
    toss: dict[str, Any]
    bowling_rotation: dict[str, Any]
    xi_selection: dict[str, Any]
    own_strategy: dict[str, Any]
    opposition_strategy: dict[str, Any]
    coach: dict[str, Any]
    final_response: dict[str, Any]
