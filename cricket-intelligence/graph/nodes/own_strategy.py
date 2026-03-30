from __future__ import annotations

from graph.state import CricketState


def run(state: CricketState) -> dict:
    request = state.get("request", {})
    own_team = request.get("own_team", "Our side")
    return {
        "own_strategy": {
            "summary": f"{own_team} strategy scaffolded across powerplay, middle overs, and endgame phases.",
            "key_points": [
                "Add batting tempo targets, bowling matchups, and field templates here.",
                "This node should turn upstream analysis into an executable game plan.",
            ],
        }
    }
