from __future__ import annotations

from graph.state import CricketState


def run(state: CricketState) -> dict:
    request = state.get("request", {})
    opponent = request.get("opposition_team") or request.get("opponent", "the opposition")
    return {
        "matchup": {
            "summary": f"Matchup planning has been scaffolded against {opponent}.",
            "key_points": [
                "Add batter-vs-bowler and handedness matchup edges in this node.",
                "Use opponent recent XI patterns to improve pre-match targeting.",
            ],
        }
    }
