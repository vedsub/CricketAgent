from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from config import get_llm
from graph.nodes._shared import append_error, get_validated_teams, normalize_text
from graph.state import CricketState
from schemas.models import BowlerProfile, BowlingRotationOutput

SYSTEM_PROMPT = """
You are an IPL bowling coach planning the 20-over bowling rotation.

Hard constraints:
- Each bowler maximum 4 overs
- Must use at least 5 different bowlers across 20 overs
- Part-time bowlers (batters who bowl) max 2 overs

Tactical principles:
- Powerplay (Overs 1-6): Use your best new-ball pace bowlers.
  Bring your most attacking spinner in over 5 or 6 if conditions suit.
- Middle overs (7-15): This is where economy matters most.
  Use cutters, variations bowlers. Protect your death bowler here.
- Death overs (16-20): Use your yorker specialists.
  Over 20 should always be your most trusted death bowler.

Return the over_plan as a dict mapping over numbers (as strings)
to bowler names. Example: {"1": "Bumrah", "2": "Bumrah", ...}

Also identify one "banker" bowler per team — the most reliable
option who should bowl the 20th over.
""".strip()


def _bowler_profile_map(state: CricketState) -> dict[str, BowlerProfile]:
    bowler_data = state.get("bowler_data")
    if not bowler_data:
        return {}

    payload = bowler_data.model_dump() if hasattr(bowler_data, "model_dump") else bowler_data
    profiles = payload.get("bowler_profiles", {})
    return {
        normalize_text(name).lower(): BowlerProfile.model_validate(profile)
        for name, profile in profiles.items()
    }


def _team_bowlers(team_players: list, profile_map: dict[str, BowlerProfile]) -> list[tuple[Any, BowlerProfile]]:
    bowlers: list[tuple[Any, BowlerProfile]] = []
    for player in team_players:
        key = normalize_text(player.name).lower()
        profile = profile_map.get(key)
        if profile:
            bowlers.append((player, profile))
    return bowlers


def _fallback_rotation(state: CricketState) -> BowlingRotationOutput:
    team1_name = state.get("team1_name", "Team 1")
    team2_name = state.get("team2_name", "Team 2")
    team1_players, team2_players = get_validated_teams(state)
    profile_map = _bowler_profile_map(state)

    team1_bowlers = _team_bowlers(team1_players, profile_map)
    team2_bowlers = _team_bowlers(team2_players, profile_map)

    def rank_bowlers(entries: list[tuple[Any, BowlerProfile]], phase: str) -> list[str]:
        ranked = sorted(
            entries,
            key=lambda item: (
                1 if item[1].best_phase == phase else 0,
                -item[1].economy,
                item[1].wickets_per_match,
            ),
            reverse=True,
        )
        return [item[0].name for item in ranked]

    team1_powerplay = rank_bowlers(team1_bowlers, "powerplay")
    team1_middle = rank_bowlers(team1_bowlers, "middle")
    team1_death = rank_bowlers(team1_bowlers, "death")
    team2_death = rank_bowlers(team2_bowlers, "death")

    available_primary = team1_powerplay[:3]
    available_middle = [name for name in team1_middle if name not in available_primary][:3]
    available_death = [name for name in team1_death if name not in available_primary][:2]

    unique_bowlers = []
    for name in available_primary + available_middle + available_death:
        if name not in unique_bowlers:
            unique_bowlers.append(name)
    if len(unique_bowlers) < 5:
        for name in [entry[0].name for entry in team1_bowlers]:
            if name not in unique_bowlers:
                unique_bowlers.append(name)
            if len(unique_bowlers) >= 5:
                break

    bowler_limits: dict[str, int] = {}
    player_role_map = {player.name: player.role for player in team1_players}
    for name in unique_bowlers:
        bowler_limits[name] = 2 if player_role_map.get(name) == "batter" else 4

    death_banker_team1 = available_death[0] if available_death else (unique_bowlers[0] if unique_bowlers else "")
    death_banker_team2 = team2_death[0] if team2_death else ""

    plan_template = [
        available_primary[0] if available_primary else death_banker_team1,
        available_primary[1] if len(available_primary) > 1 else death_banker_team1,
        available_primary[0] if available_primary else death_banker_team1,
        available_primary[1] if len(available_primary) > 1 else death_banker_team1,
        available_middle[0] if available_middle else (available_primary[2] if len(available_primary) > 2 else death_banker_team1),
        available_primary[2] if len(available_primary) > 2 else (available_middle[0] if available_middle else death_banker_team1),
        available_middle[0] if available_middle else death_banker_team1,
        available_middle[1] if len(available_middle) > 1 else death_banker_team1,
        available_middle[0] if available_middle else death_banker_team1,
        available_middle[1] if len(available_middle) > 1 else death_banker_team1,
        available_middle[2] if len(available_middle) > 2 else death_banker_team1,
        available_middle[0] if available_middle else death_banker_team1,
        available_middle[2] if len(available_middle) > 2 else death_banker_team1,
        unique_bowlers[4] if len(unique_bowlers) > 4 else death_banker_team1,
        available_middle[1] if len(available_middle) > 1 else death_banker_team1,
        available_death[1] if len(available_death) > 1 else death_banker_team1,
        death_banker_team1,
        available_death[1] if len(available_death) > 1 else unique_bowlers[3] if len(unique_bowlers) > 3 else death_banker_team1,
        unique_bowlers[4] if len(unique_bowlers) > 4 else death_banker_team1,
        death_banker_team1,
    ]

    over_plan: dict[str, str] = {}
    overs_used = {name: 0 for name in bowler_limits}

    for over_number, preferred in enumerate(plan_template, start=1):
        candidates = [preferred] + [name for name in unique_bowlers if name != preferred]
        chosen = None
        for candidate in candidates:
            if not candidate:
                continue
            if overs_used.get(candidate, 0) < bowler_limits.get(candidate, 4):
                chosen = candidate
                break
        if chosen is None:
            chosen = unique_bowlers[0]
        overs_used[chosen] = overs_used.get(chosen, 0) + 1
        over_plan[str(over_number)] = chosen

    return BowlingRotationOutput(
        powerplay_bowlers=unique_bowlers[:3],
        middle_bowlers=[name for name in available_middle if name][:3],
        death_bowlers=[name for name in [death_banker_team1, death_banker_team2] + available_death if name][:4],
        over_plan=over_plan,
    )


def run(state: CricketState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(BowlingRotationOutput)

    team1_name = state.get("team1_name", "Team 1")
    team2_name = state.get("team2_name", "Team 2")
    team1_players, team2_players = get_validated_teams(state)
    bowler_data = state.get("bowler_data")
    matchups = state.get("matchups")
    venue_stats = state.get("venue_stats")

    bowler_payload = bowler_data.model_dump() if hasattr(bowler_data, "model_dump") else bowler_data
    matchup_payload = matchups.model_dump() if hasattr(matchups, "model_dump") else matchups
    venue_payload = venue_stats.model_dump() if hasattr(venue_stats, "model_dump") else venue_stats

    try:
        response = structured_llm.invoke(
            [
                SystemMessage(
                    content=(
                        SYSTEM_PROMPT
                        + "\nBecause the current schema supports only one over_plan, build the detailed 20-over plan for Team 1 while listing both teams' banker death bowlers first in death_bowlers."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Primary bowling plan needed for {team1_name} against {team2_name}.\n"
                        f"Team 1 squad roles: {[{'name': p.name, 'role': p.role, 'bowling_style': p.bowling_style} for p in team1_players]}\n"
                        f"Team 2 squad roles: {[{'name': p.name, 'role': p.role, 'bowling_style': p.bowling_style} for p in team2_players]}\n"
                        f"Bowler profiles: {bowler_payload}\n"
                        f"Matchup insights: {matchup_payload}\n"
                        f"Venue context: {venue_payload}\n"
                        "Return a BowlingRotationOutput object only."
                    )
                ),
            ]
        )
        output = BowlingRotationOutput.model_validate(response)
        return {"bowling_rotation": output}
    except Exception as exc:
        return {
            "bowling_rotation": _fallback_rotation(state),
            "errors": append_error(state, f"Bowling rotation node fell back to template scheduling: {exc}"),
        }
