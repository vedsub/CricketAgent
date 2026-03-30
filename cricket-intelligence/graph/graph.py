from __future__ import annotations

import json
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from graph.nodes._shared import append_error
from graph.nodes import (
    batter,
    bowler,
    bowling_rotation,
    coach,
    eligibility,
    form,
    matchup,
    opposition_strategy,
    own_strategy,
    toss,
    venue,
    xi_selection,
)
from graph.state import CricketState
from tools.cricket_tools import MOCK_SQUADS

try:
    from langgraph.graph.state import CompiledStateGraph as CompiledGraph
except Exception:
    CompiledGraph = Any


NODE_OUTPUT_KEYS = {
    "eligibility": "eligibility",
    "venue": "venue_stats",
    "form": "form",
    "batter": "batter_data",
    "bowler": "bowler_data",
    "matchup": "matchups",
    "toss": "toss",
    "bowling_rotation": "bowling_rotation",
    "xi_selection": "xi_selection",
    "own_strategy": "own_strategy",
    "opposition_strategy": "opposition_strategy",
    "coach": "final_report",
}


def build_run_config(team1: str, team2: str, match_date: str, thread_id: str | None = None) -> dict[str, Any]:
    return {
        "run_name": "cricket-intelligence",
        "metadata": {
            "match": f"{team1} vs {team2}",
            "date": match_date,
        },
        "configurable": {
            "thread_id": thread_id or f"{team1.lower().replace(' ', '-')}-{team2.lower().replace(' ', '-')}-{match_date}"
        },
    }


def _safe_node_runner(node_name: str, fn):
    output_key = NODE_OUTPUT_KEYS.get(node_name)

    def wrapped(state: CricketState) -> dict[str, Any]:
        try:
            return fn(state)
        except Exception as exc:
            update: dict[str, Any] = {
                "errors": append_error(state, f"{node_name} node failed: {exc}"),
            }
            if output_key:
                update[output_key] = state.get(output_key)
            return update

    return wrapped


def _mark_layer_complete(state: CricketState, layer_name: str) -> dict[str, list[str]]:
    completed_layers = list(state.get("completed_layers", []))
    if layer_name not in completed_layers:
        completed_layers.append(layer_name)
    return {"completed_layers": completed_layers}


def layer1_join(state: CricketState) -> dict[str, list[str]]:
    required = ["venue_stats", "form", "batter_data", "bowler_data"]
    if all(state.get(key) is not None for key in required):
        return _mark_layer_complete(state, "layer1")
    return {"completed_layers": list(state.get("completed_layers", []))}


def layer2_join(state: CricketState) -> dict[str, list[str]]:
    required = ["matchups", "toss", "bowling_rotation"]
    if all(state.get(key) is not None for key in required):
        return _mark_layer_complete(state, "layer2")
    return {"completed_layers": list(state.get("completed_layers", []))}


def layer3_join(state: CricketState) -> dict[str, list[str]]:
    required = ["own_strategy", "opposition_strategy"]
    if all(state.get(key) is not None for key in required):
        return _mark_layer_complete(state, "layer3")
    return {"completed_layers": list(state.get("completed_layers", []))}


def build_graph() -> CompiledGraph:
    workflow = StateGraph(CricketState)

    # Add all nodes
    workflow.add_node("eligibility", _safe_node_runner("eligibility", eligibility.run))
    workflow.add_node("venue", _safe_node_runner("venue", venue.run))
    workflow.add_node("form", _safe_node_runner("form", form.run))
    workflow.add_node("batter", _safe_node_runner("batter", batter.run))
    workflow.add_node("bowler", _safe_node_runner("bowler", bowler.run))
    workflow.add_node("matchup", _safe_node_runner("matchup", matchup.run))
    workflow.add_node("toss", _safe_node_runner("toss", toss.run))
    workflow.add_node("bowling_rotation", _safe_node_runner("bowling_rotation", bowling_rotation.run))
    workflow.add_node("xi_selection", _safe_node_runner("xi_selection", xi_selection.run))
    workflow.add_node("own_strategy", _safe_node_runner("own_strategy", own_strategy.run))
    workflow.add_node("opposition_strategy", _safe_node_runner("opposition_strategy", opposition_strategy.run))
    workflow.add_node("coach", _safe_node_runner("coach", coach.run))
    workflow.add_node("layer1_join", _safe_node_runner("layer1_join", layer1_join))
    workflow.add_node("layer2_join", _safe_node_runner("layer2_join", layer2_join))
    workflow.add_node("layer3_join", _safe_node_runner("layer3_join", layer3_join))

    # Entry point
    workflow.set_entry_point("eligibility")

    # Layer 0 -> Layer 1 (fan out in parallel)
    workflow.add_edge("eligibility", "venue")
    workflow.add_edge("eligibility", "form")
    workflow.add_edge("eligibility", "batter")
    workflow.add_edge("eligibility", "bowler")

    # Layer 1 -> Layer 2 (fan in)
    workflow.add_edge("venue", "layer1_join")
    workflow.add_edge("form", "layer1_join")
    workflow.add_edge("batter", "layer1_join")
    workflow.add_edge("bowler", "layer1_join")

    # Layer 2 (parallel)
    workflow.add_edge("layer1_join", "matchup")
    workflow.add_edge("layer1_join", "toss")
    workflow.add_edge("layer1_join", "bowling_rotation")

    # Layer 2 -> 2.5
    workflow.add_edge("matchup", "layer2_join")
    workflow.add_edge("toss", "layer2_join")
    workflow.add_edge("bowling_rotation", "layer2_join")
    workflow.add_edge("layer2_join", "xi_selection")

    # Layer 2.5 -> Layer 3 (parallel)
    workflow.add_edge("xi_selection", "own_strategy")
    workflow.add_edge("xi_selection", "opposition_strategy")

    # Layer 3 -> Layer 4
    workflow.add_edge("own_strategy", "layer3_join")
    workflow.add_edge("opposition_strategy", "layer3_join")
    workflow.add_edge("layer3_join", "coach")
    workflow.add_edge("coach", END)

    # Add checkpointing for state persistence
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


app_graph = build_graph()
intelligence_graph = app_graph


async def demo() -> None:
    state: CricketState = {
        "team1_name": "Chennai Super Kings",
        "team2_name": "Rajasthan Royals",
        "venue": "Chepauk",
        "match_date": "2026-03-30",
        "team1_squad_raw": MOCK_SQUADS["Chennai Super Kings"],
        "team2_squad_raw": MOCK_SQUADS["Rajasthan Royals"],
        "eligibility": None,
        "venue_stats": None,
        "form": None,
        "batter_data": None,
        "bowler_data": None,
        "matchups": None,
        "toss": None,
        "bowling_rotation": None,
        "xi_selection": None,
        "own_strategy": None,
        "opposition_strategy": None,
        "final_report": None,
        "errors": [],
        "completed_layers": [],
        "messages": [],
    }

    result = await app_graph.ainvoke(
        state,
        config=build_run_config("Chennai Super Kings", "Rajasthan Royals", "2026-03-30", "demo-csk-rr"),
    )
    print(json.dumps(result["final_report"].model_dump() if hasattr(result["final_report"], "model_dump") else result["final_report"], indent=2))
