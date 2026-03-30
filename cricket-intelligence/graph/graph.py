from __future__ import annotations

from langgraph.graph import END, START, StateGraph

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


def build_graph():
    workflow = StateGraph(CricketState)

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

    workflow.add_edge(START, "eligibility")
    workflow.add_edge("eligibility", "venue")
    workflow.add_edge("venue", "form")
    workflow.add_edge("form", "batter")
    workflow.add_edge("batter", "bowler")
    workflow.add_edge("bowler", "matchup")
    workflow.add_edge("matchup", "toss")
    workflow.add_edge("toss", "bowling_rotation")
    workflow.add_edge("bowling_rotation", "xi_selection")
    workflow.add_edge("xi_selection", "own_strategy")
    workflow.add_edge("own_strategy", "opposition_strategy")
    workflow.add_edge("opposition_strategy", "coach")
    workflow.add_edge("coach", END)

    return workflow.compile()


intelligence_graph = build_graph()
