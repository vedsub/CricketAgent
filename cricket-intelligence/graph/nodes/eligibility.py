from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from config import get_llm
from graph.nodes._shared import append_error, coerce_player_profile, normalize_text
from graph.state import CricketState
from schemas.models import EligibilityOutput, PlayerProfile

SYSTEM_PROMPT = """
You are an IPL squad eligibility validator. Your job is to:
1. Identify overseas (non-Indian) players. IPL allows max 4
   overseas players in a Playing XI.
2. Resolve shortened or ambiguous player names to full names.
3. Classify each player's primary role: batter, bowler,
   all-rounder, or wicket-keeper.
4. Flag any issues: duplicate names, unrecognized players,
   role ambiguity.

Use your cricket knowledge. Be precise with nationalities.
Return structured output only.
""".strip()

USER_PROMPT_TEMPLATE = """
Validate and clean these two IPL squads:

Team 1 ({team1_name}): {team1_squad_raw}
Team 2 ({team2_name}): {team2_squad_raw}

Return validated player profiles for both teams.
""".strip()


def _fallback_validate_team(players: list[dict[str, Any]]) -> tuple[list[PlayerProfile], list[str]]:
    validated: list[PlayerProfile] = []
    seen: set[str] = set()
    flagged: list[str] = []

    for player in players:
        profile = coerce_player_profile(player)
        normalized_name = normalize_text(profile.name).lower()
        if normalized_name == "unknown player":
            flagged.append("Unrecognized player entry encountered in squad data.")
            continue
        if normalized_name in seen:
            flagged.append(f"Duplicate player detected: {profile.name}")
            continue
        seen.add(normalized_name)
        validated.append(profile)

    overseas = sum(player.is_overseas for player in validated)
    if overseas > 4:
        flagged.append(
            f"Squad contains {overseas} overseas players; only 4 can be used in the playing XI."
        )

    return validated, flagged


def run(state: CricketState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(EligibilityOutput)

    team1_name = state.get("team1_name", "Team 1")
    team2_name = state.get("team2_name", "Team 2")
    team1_squad_raw = state.get("team1_squad_raw", [])
    team2_squad_raw = state.get("team2_squad_raw", [])

    user_prompt = USER_PROMPT_TEMPLATE.format(
        team1_name=team1_name,
        team2_name=team2_name,
        team1_squad_raw=team1_squad_raw,
        team2_squad_raw=team2_squad_raw,
    )

    try:
        response = structured_llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
        )
        output = EligibilityOutput.model_validate(response)
        return {"eligibility": output}
    except Exception as exc:
        team1_validated, team1_issues = _fallback_validate_team(team1_squad_raw)
        team2_validated, team2_issues = _fallback_validate_team(team2_squad_raw)
        output = EligibilityOutput(
            team1_validated=team1_validated,
            team2_validated=team2_validated,
            overseas_count={
                team1_name: sum(player.is_overseas for player in team1_validated),
                team2_name: sum(player.is_overseas for player in team2_validated),
            },
            flagged_issues=team1_issues + team2_issues,
        )
        return {
            "eligibility": output,
            "errors": append_error(state, f"Eligibility node fell back to rules-based validation: {exc}"),
        }
