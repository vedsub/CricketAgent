from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from config import get_llm
from graph.nodes._shared import append_error, to_payload
from graph.state import CricketState
from schemas.models import StrategyOutput

SYSTEM_PROMPT = """
You are a defensive T20 bowling coach analyzing how to restrict
the opposition.

Use the exploit matchups to plan:
- Which bowlers should bowl at which batters?
- When should the best bowlers be held back?
- Identify the opposition's danger batter (most likely match-winner)
  and design a specific containment plan for them.

Field placement suggestions (keep to 2-3 specific examples):
- E.g., "Set a deep square leg for [batter] against short ball
  from [bowler] — he top-edges frequently"

Death bowling plan:
- Name the over 18, 19, 20 bowlers and justify the choice based
  on the opposition's death-over batting lineup.

Identify one "X-factor" batter in the opposition who isn't
well-known but could be dangerous — plan for the unexpected.
""".strip()


def _fallback_strategy(state: CricketState) -> StrategyOutput:
    xi_selection = to_payload(state.get("xi_selection") or {})
    matchups = to_payload(state.get("matchups") or {})
    bowling_rotation = to_payload(state.get("bowling_rotation") or {})

    team2_xi = xi_selection.get("team2_xi", [])
    exploit = matchups.get("exploit_matchups", [])
    danger = matchups.get("danger_matchups", [])
    death_bowlers = bowling_rotation.get("death_bowlers", [])
    over_plan = bowling_rotation.get("over_plan", {})

    danger_batter = danger[0]["batter"] if danger else (team2_xi[0]["name"] if team2_xi else "the opposition opener")
    x_factor = team2_xi[4]["name"] if len(team2_xi) > 4 else "the opposition floater"

    return StrategyOutput(
        powerplay_target=47,
        middle_overs_plan=(
            f"Attack {exploit[0]['batter']} with {exploit[0]['bowler']} as soon as that matchup appears and keep a catching ring in place."
            if exploit
            else "Use the most economical middle-overs bowler from over 7 onward to choke boundary access."
        ),
        death_overs_plan=(
            f"Plan over 18 for {over_plan.get('18', death_bowlers[0] if death_bowlers else 'best death bowler')}, "
            f"over 19 for {over_plan.get('19', death_bowlers[1] if len(death_bowlers) > 1 else death_bowlers[0] if death_bowlers else 'secondary death bowler')}, "
            f"and over 20 for {over_plan.get('20', death_bowlers[0] if death_bowlers else 'banker bowler')}."
        ),
        key_partnerships=[
            f"Break the stand built around {danger_batter} before over 12 by holding one strike bowler back.",
            f"Use the strongest matchup bowler the moment {x_factor} arrives if the game is drifting.",
        ],
        bowling_plan=(
            f"Start with the bowlers most likely to reach {danger_batter}'s outside edge, then switch to pace-off once the ball softens."
        ),
        restriction_plan=(
            f"Set a deep square leg and fine leg back to {danger_batter} against short pace, and use a sweeper cover when the opposition's right-handers face left-arm spin."
        ),
        key_threats=[danger_batter, x_factor] + [item["batter"] for item in exploit[:2]],
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
                        f"Build the defensive bowling plan for {team1_name} against {team2_name}.\n"
                        f"XI selection: {to_payload(state.get('xi_selection'))}\n"
                        f"Matchups: {to_payload(state.get('matchups'))}\n"
                        f"Bowling rotation: {to_payload(state.get('bowling_rotation'))}\n"
                        f"Venue data: {to_payload(state.get('venue_stats'))}\n"
                        "Be specific about batters, bowlers, overs, and field settings."
                    )
                ),
            ]
        )
        output = StrategyOutput.model_validate(response)
        return {"opposition_strategy": output}
    except Exception as exc:
        return {
            "opposition_strategy": _fallback_strategy(state),
            "errors": append_error(state, f"Opposition strategy node fell back to defensive heuristics: {exc}"),
        }
