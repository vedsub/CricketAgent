from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from config import get_llm
from graph.nodes._shared import append_error, get_form_index_map, to_payload
from graph.state import CricketState
from schemas.models import StrategyOutput

SYSTEM_PROMPT = """
You are an aggressive T20 batting coach building a match-winning
game plan for team1.

Use the matchup data to build attacking plans:
- Which bowlers from the opposition should team1 target?
- Which partnerships should be preserved (don't lose wickets in
  powerplay vs dangerous bowlers)?
- What is a realistic powerplay target (6-over score)?
- Name specific batters who should attack specific bowlers based
  on their H2H danger matchup advantage.

Use the venue data to set a first innings target:
- High-scoring venues (SR index > 110): Target 180-200
- Average venues (SR 90-110): Target 160-175
- Low-scoring venues (SR < 90): Target 145-160

Be specific. Don't give generic advice. Name players and overs.
""".strip()


def _fallback_strategy(state: CricketState) -> StrategyOutput:
    xi_selection = to_payload(state.get("xi_selection") or {})
    matchups = to_payload(state.get("matchups") or {})
    venue = to_payload(state.get("venue_stats") or {})
    form_map = get_form_index_map(state)

    team1_xi = xi_selection.get("team1_xi", [])
    top_three = [player["name"] for player in team1_xi[:3]]
    middle = [player["name"] for player in team1_xi[3:7]]
    danger = matchups.get("danger_matchups", [])
    exploit = matchups.get("exploit_matchups", [])
    high_sr_index = float(venue.get("venue_sr_index", 100))

    if high_sr_index > 110:
        target = 188
    elif high_sr_index < 90:
        target = 154
    else:
        target = 168

    attack_lines = [
        f"{item['batter']} should line up {item['bowler']} from overs 7-10 if that matchup appears."
        for item in danger[:2]
    ]
    exploit_lines = [
        f"Respect {item['bowler']} early when {item['batter']} is exposed, especially in the first 10 balls."
        for item in exploit[:2]
    ]

    powerplay_target = 60 if high_sr_index > 110 else 51 if high_sr_index < 90 else 55
    anchor = max(top_three, key=lambda name: form_map.get(name.lower(), 50)) if top_three else "our anchor"

    return StrategyOutput(
        powerplay_target=powerplay_target,
        middle_overs_plan=" ".join(attack_lines) or "Use overs 7-10 to target the weakest fifth-bowler matchup and keep the left-right combination moving.",
        death_overs_plan=f"Hold wickets for overs 16-20 and funnel the finish through {', '.join(middle[:2]) if middle else 'your two best finishers'} once the death bowlers return.",
        key_partnerships=[
            f"Preserve the opening stand through over 3 before taking on the first change bowlers with {top_three[0] if top_three else 'the in-form opener'}.",
            f"Keep {anchor} batting into over 12 to anchor the total while the middle-order hitters launch around him.",
        ],
        bowling_plan="If defending, use the strongest matchup bowler immediately when the opposition's most explosive batter arrives.",
        restriction_plan="Avoid exposing new batters to exploit matchups in clusters; stagger acceleration around the safest matchup windows.",
        key_threats=[item["bowler"] for item in exploit[:3]] or ["Opposition new-ball pair"],
    )


def run(state: CricketState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(StrategyOutput)

    team1_name = state.get("team1_name", "Team 1")
    team2_name = state.get("team2_name", "Team 2")

    try:
        response = structured_llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT + "\nReturn a StrategyOutput object only."),
                HumanMessage(
                    content=(
                        f"Build the batting plan for {team1_name} against {team2_name}.\n"
                        f"Venue data: {to_payload(state.get('venue_stats'))}\n"
                        f"Matchup data: {to_payload(state.get('matchups'))}\n"
                        f"XI selection: {to_payload(state.get('xi_selection'))}\n"
                        f"Form data: {to_payload(state.get('form'))}\n"
                        "Be specific about players, bowlers, and overs."
                    )
                ),
            ]
        )
        output = StrategyOutput.model_validate(response)
        return {"own_strategy": output}
    except Exception as exc:
        return {
            "own_strategy": _fallback_strategy(state),
            "errors": append_error(state, f"Own strategy node fell back to matchup heuristics: {exc}"),
        }
