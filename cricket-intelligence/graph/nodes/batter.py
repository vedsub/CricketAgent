from __future__ import annotations

from graph.state import CricketState


def run(state: CricketState) -> dict:
    request = state.get("request", {})
    top_order = request.get("squad", [])[:4]
    return {
        "batter": {
            "summary": "Top-order batting analysis placeholder created for matchup-specific planning.",
            "key_points": [
                f"Provisional top-order pool: {', '.join(top_order) if top_order else 'not supplied'}",
                "Extend this node with strike-rate bands by phase and handedness splits.",
            ],
        }
    }
