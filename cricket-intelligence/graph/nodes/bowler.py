from __future__ import annotations

from graph.state import CricketState


def run(state: CricketState) -> dict:
    request = state.get("request", {})
    bowling_pool = request.get("squad", [])[4:9]
    return {
        "bowler": {
            "summary": "Bowling unit analysis placeholder created for phase-based role allocation.",
            "key_points": [
                f"Initial bowling pool: {', '.join(bowling_pool) if bowling_pool else 'not supplied'}",
                "Add economy, wicket mode, and matchup filters here.",
            ],
        }
    }
