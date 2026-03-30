from __future__ import annotations

from graph.state import CricketState


def run(state: CricketState) -> dict:
    request = state.get("request", {})
    opponent = request.get("opposition_team") or request.get("opponent", "Opposition")
    return {
        "opposition_strategy": {
            "summary": f"Opposition tendencies for {opponent} can be analyzed and counter-planned here.",
            "key_points": [
                "Track likely opening combinations, spin usage, and death-over plans.",
                "Use opponent templates to stress-test your own XI and toss decisions.",
            ],
        }
    }
