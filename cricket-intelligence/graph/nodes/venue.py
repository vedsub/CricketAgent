from __future__ import annotations

from graph.state import CricketState


def run(state: CricketState) -> dict:
    request = state.get("request", {})
    venue_name = request.get("venue", "Unknown venue")
    match_format = request.get("format", "T20")
    return {
        "venue": {
            "summary": f"{venue_name} has been set as the venue context for this {match_format} plan.",
            "key_points": [
                "Add pitch maps, boundary dimensions, and weather feeds here.",
                "Use venue trends to refine toss and phase strategy downstream.",
            ],
        }
    }
