from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

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

try:
    from langgraph.graph.state import CompiledStateGraph as CompiledGraph
except Exception:
    CompiledGraph = Any


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
    workflow.add_node("eligibility", eligibility.run)
    workflow.add_node("venue", venue.run)
    workflow.add_node("form", form.run)
    workflow.add_node("batter", batter.run)
    workflow.add_node("bowler", bowler.run)
    workflow.add_node("matchup", matchup.run)
    workflow.add_node("toss", toss.run)
    workflow.add_node("bowling_rotation", bowling_rotation.run)
    workflow.add_node("xi_selection", xi_selection.run)
    workflow.add_node("own_strategy", own_strategy.run)
    workflow.add_node("opposition_strategy", opposition_strategy.run)
    workflow.add_node("coach", coach.run)
    workflow.add_node("layer1_join", layer1_join)
    workflow.add_node("layer2_join", layer2_join)
    workflow.add_node("layer3_join", layer3_join)

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
