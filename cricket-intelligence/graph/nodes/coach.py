from __future__ import annotations

from graph.state import CricketState
from schemas.models import (
    AnalysisRequest,
    BowlingPlan,
    CricketIntelligenceResponse,
    NodeSection,
    PlayingXIRecommendation,
    TossPlan,
)


def run(state: CricketState) -> dict:
    request = AnalysisRequest.model_validate(state.get("request", {}))

    section_titles = {
        "eligibility": "Eligibility",
        "venue": "Venue",
        "form": "Form",
        "batter": "Batter",
        "bowler": "Bowler",
        "matchup": "Matchup",
        "toss": "Toss",
        "bowling_rotation": "Bowling Rotation",
        "xi_selection": "XI Selection",
        "own_strategy": "Own Strategy",
        "opposition_strategy": "Opposition Strategy",
    }

    sections = [
        NodeSection(
            title=title,
            summary=state[key].get("summary", ""),
            key_points=state[key].get("key_points", []),
        )
        for key, title in section_titles.items()
        if key in state
    ]

    xi_data = state.get("xi_selection", {})
    bowling_data = state.get("bowling_rotation", {})
    toss_data = state.get("toss", {})
    coach_summary = (
        "Scaffolded coaching summary generated from the current graph nodes. "
        "Connect live data, richer heuristics, or an LLM call in this final node to turn the placeholders into actionable recommendations."
    )

    response = CricketIntelligenceResponse(
        match_context=request,
        sections=sections,
        xi_selection=PlayingXIRecommendation(
            playing_xi=xi_data.get("playing_xi", request.squad[:11]),
            bench=xi_data.get("bench", request.squad[11:]),
            rationale=xi_data.get("summary", "Initial XI derived from the submitted squad."),
        ),
        bowling_rotation=BowlingPlan(
            opening_pair=bowling_data.get("opening_pair", request.squad[:2]),
            middle_overs=bowling_data.get("middle_overs", request.squad[2:5]),
            death_overs=bowling_data.get("death_overs", request.squad[5:7]),
            rationale=bowling_data.get(
                "summary", "Initial bowling rotation derived from the submitted squad."
            ),
        ),
        toss_plan=TossPlan(
            decision_if_win_toss=toss_data.get(
                "decision_if_win_toss", "Assess conditions before deciding"
            ),
            rationale=toss_data.get("summary", "Toss guidance pending more detailed inputs."),
        ),
        coach_summary=coach_summary,
    )

    return {
        "coach": {
            "summary": coach_summary,
            "key_points": [
                "The scaffold is wired end-to-end from API request to final response.",
                "Replace placeholder node logic with data-backed or model-backed reasoning as you iterate.",
            ],
        },
        "final_response": response.model_dump(),
    }
