from __future__ import annotations

from graph.state import CricketState


def run(state: CricketState) -> dict:
    request = state.get("request", {})
    match_format = request.get("format", "T20").upper()
    decision = "Bowl first" if match_format in {"T20", "T20I"} else "Assess conditions before deciding"
    return {
        "toss": {
            "summary": "Toss strategy scaffolded from the current match format and venue placeholder.",
            "key_points": [
                "Refine with dew, weather, and chasing bias once data feeds are connected.",
                f"Current format default suggests: {decision}.",
            ],
            "decision_if_win_toss": decision,
        }
    }
