from __future__ import annotations

from graph.state import CricketState


def run(state: CricketState) -> dict:
    request = state.get("request", {})
    squad = request.get("squad", [])
    highlighted = ", ".join(squad[:3]) if squad else "squad members"
    return {
        "form": {
            "summary": f"Recent-form analysis is scaffolded and ready to evaluate players like {highlighted}.",
            "key_points": [
                "Attach batting and bowling trend windows from the data layer.",
                "Prioritize role-specific form rather than generic aggregate averages.",
            ],
        }
    }
