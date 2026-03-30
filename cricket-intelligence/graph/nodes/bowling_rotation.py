from __future__ import annotations

from graph.state import CricketState


def run(state: CricketState) -> dict:
    squad = state.get("request", {}).get("squad", [])
    opening_pair = squad[:2]
    middle_overs = squad[2:5]
    death_overs = squad[5:7]
    return {
        "bowling_rotation": {
            "summary": "Bowling rotation placeholder mapped into opening, middle, and death overs.",
            "key_points": [
                "Replace squad-order assumptions with role-aware bowler selection.",
                "Model matchup and workload constraints before locking the final rotation.",
            ],
            "opening_pair": opening_pair,
            "middle_overs": middle_overs,
            "death_overs": death_overs,
        }
    }
