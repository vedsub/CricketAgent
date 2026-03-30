from __future__ import annotations

from graph.state import CricketState


def run(state: CricketState) -> dict:
    request = state.get("request", {})
    squad = request.get("squad", [])
    summary = (
        f"{len(squad)} players were supplied for selection planning."
        if squad
        else "No squad list was provided yet, so eligibility is still a placeholder."
    )
    return {
        "eligibility": {
            "summary": summary,
            "key_points": [
                f"Own team: {request.get('own_team', 'Unknown')}",
                f"Opponent: {request.get('opponent', 'Unknown')}",
                "Integrate injuries, workload, and travel availability in this node next.",
            ],
            "available_players": squad,
        }
    }
