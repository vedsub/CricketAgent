from __future__ import annotations

from graph.state import CricketState


def run(state: CricketState) -> dict:
    squad = state.get("request", {}).get("squad", [])
    playing_xi = squad[:11]
    bench = squad[11:]
    return {
        "xi_selection": {
            "summary": "Initial playing XI scaffolded from the supplied squad order.",
            "key_points": [
                "Swap order-based selection for role-balance and condition-aware rules.",
                "Use this node to produce captaincy, wicketkeeper, and impact-player decisions.",
            ],
            "playing_xi": playing_xi,
            "bench": bench,
        }
    }
