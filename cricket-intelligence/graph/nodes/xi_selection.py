from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from config import get_llm
from graph.nodes._shared import (
    append_error,
    get_form_index_map,
    get_validated_teams,
    normalize_text,
    overseas_count,
    to_payload,
)
from graph.state import CricketState
from schemas.models import XIPlayer, XISelectionOutput

SYSTEM_PROMPT = """
You are the head selector for an IPL franchise. Select the
optimal Playing XI from a 15-man squad.

Selection rules (non-negotiable):
1. Exactly 11 players in the XI
2. Maximum 4 overseas players
3. At least 1 designated wicket-keeper
4. Minimum 5 specialist batters (positions 1-7 must all bat)
5. Minimum 4 specialist bowlers who bowl their full 4 overs
6. At least 2 all-rounders or bowling options at 6, 7

Selection priority order:
1. Form (is the player performing right now?)
2. Venue fit (does their skill suit this ground?)
3. Matchup advantage (do they have good H2H vs the opposition?)
4. Team balance (do they fill a role gap?)

Impact Player rule (IPL 2025):
- One player from the bench (players 12-15) can be substituted
  in before the first over of either innings
- Choose your Impact Player based on match situation (batting or
  bowling impact needed)
- Recommend WHEN to use the Impact sub:
  "Use if chasing 180+, bring in [extra batter] for [tail bowler]"

Batting order philosophy:
- Position 1-2: Aggressive openers who can capitalize on powerplay
- Position 3: Most consistent run-scorer, anchor
- Position 4-5: Power-hitters who can accelerate in middle overs
- Position 6-7: All-rounders who can bat aggressively and bowl
- Position 8-9: Lower order who contribute quick runs
- Position 10-11: Tailenders (pure bowlers)

For EACH player selected, give a one-line reason for their
inclusion and their specific batting position.
""".strip()

VENUE_ROLE_BONUS = {
    "spin": {"bowler": 7, "all-rounder": 6, "batter": -1, "wicket-keeper": 0},
    "pace": {"bowler": 6, "all-rounder": 5, "batter": 1, "wicket-keeper": 1},
    "balanced": {"bowler": 3, "all-rounder": 4, "batter": 2, "wicket-keeper": 2},
}


def _matchup_advantage_map(state: CricketState) -> dict[str, int]:
    payload = to_payload(state.get("matchups") or {})
    scores: dict[str, int] = {}
    for item in payload.get("danger_matchups", []):
        batter = normalize_text(item.get("batter")).lower()
        bowler = normalize_text(item.get("bowler")).lower()
        scores[batter] = scores.get(batter, 0) + 8
        scores[bowler] = scores.get(bowler, 0) - 6
    for item in payload.get("exploit_matchups", []):
        batter = normalize_text(item.get("batter")).lower()
        bowler = normalize_text(item.get("bowler")).lower()
        scores[batter] = scores.get(batter, 0) - 8
        scores[bowler] = scores.get(bowler, 0) + 8
    return scores


def _player_score(player: Any, state: CricketState, form_map: dict[str, int], matchup_map: dict[str, int]) -> int:
    venue_payload = to_payload(state.get("venue_stats") or {})
    venue_type = venue_payload.get("pitch_type", "balanced")
    venue_bonus = VENUE_ROLE_BONUS.get(venue_type, VENUE_ROLE_BONUS["balanced"]).get(player.role, 0)
    role_bonus = {"wicket-keeper": 6, "all-rounder": 8, "batter": 5, "bowler": 5}.get(player.role, 0)
    overseas_penalty = -3 if player.is_overseas else 0
    return (
        form_map.get(normalize_text(player.name).lower(), 50)
        + venue_bonus
        + matchup_map.get(normalize_text(player.name).lower(), 0)
        + role_bonus
        + overseas_penalty
    )


def _build_team_xi(
    players: list[Any],
    state: CricketState,
    form_map: dict[str, int],
    matchup_map: dict[str, int],
) -> tuple[list[XIPlayer], dict[str, Any], list[str]]:
    scored = sorted(
        players,
        key=lambda player: _player_score(player, state, form_map, matchup_map),
        reverse=True,
    )

    keepers = [player for player in scored if player.role == "wicket-keeper"]
    batters = [player for player in scored if player.role in {"batter", "wicket-keeper"}]
    all_rounders = [player for player in scored if player.role == "all-rounder"]
    bowlers = [player for player in scored if player.role == "bowler"]

    selected: list[Any] = []

    def add_player(candidate: Any) -> None:
        if candidate.name not in {player.name for player in selected}:
            if candidate.is_overseas and overseas_count(selected) >= 4:
                return
            selected.append(candidate)

    if keepers:
        add_player(keepers[0])

    for player in batters:
        if len(selected) >= 5:
            break
        add_player(player)

    for player in all_rounders:
        if len([p for p in selected if p.role == "all-rounder"]) >= 2:
            break
        add_player(player)

    for player in bowlers:
        if len([p for p in selected if p.role == "bowler"]) >= 4:
            break
        add_player(player)

    for player in scored:
        if len(selected) >= 11:
            break
        add_player(player)

    selected = selected[:11]

    top_order_pool = [player for player in selected if player.role in {"batter", "wicket-keeper"}]
    top_order_pool.sort(
        key=lambda player: (
            form_map.get(normalize_text(player.name).lower(), 50),
            matchup_map.get(normalize_text(player.name).lower(), 0),
        ),
        reverse=True,
    )
    lower_order_pool = [player for player in selected if player.role == "all-rounder"]
    lower_order_pool.sort(key=lambda player: form_map.get(normalize_text(player.name).lower(), 50), reverse=True)
    bowling_pool = [player for player in selected if player.role == "bowler"]
    bowling_pool.sort(key=lambda player: form_map.get(normalize_text(player.name).lower(), 50), reverse=True)

    batting_order = top_order_pool[:5] + lower_order_pool[:2]
    tail = [player for player in selected if player.name not in {p.name for p in batting_order}]
    tail.sort(key=lambda player: 0 if player.role == "all-rounder" else 1)
    ordered_players = (batting_order + tail)[:11]

    xi: list[XIPlayer] = []
    for index, player in enumerate(ordered_players, start=1):
        role_reason = {
            "wicket-keeper": "Keeps balance intact and offers top-seven batting security.",
            "all-rounder": "Adds two-dimensional value and keeps the XI tactically flexible.",
            "bowler": "Locks in four overs and strengthens the bowling phase plan.",
            "batter": "Selected for current run-making output and matchup relevance.",
        }[player.role]
        xi.append(
            XIPlayer(
                name=player.name,
                role=player.role,
                batting_position=index,
                reason=role_reason,
            )
        )

    bench = [player for player in scored if player.name not in {member.name for member in ordered_players}]
    impact = {
        "player": bench[0].name if bench else ordered_players[-1].name,
        "role": bench[0].role if bench else ordered_players[-1].role,
        "use_case": (
            f"Use if chasing 180+, bring in {bench[0].name if bench else ordered_players[-1].name} "
            f"for {ordered_players[-1].name} to deepen batting."
        ),
    }
    notes = [
        "Top seven were weighted toward current form before role balance.",
        "Overseas slots were preserved for the highest-impact ceiling players only.",
        "Selection leaned into venue fit and direct matchup edges where available.",
    ]
    return xi, impact, notes


def _fallback_selection(state: CricketState) -> XISelectionOutput:
    team1_players, team2_players = get_validated_teams(state)
    form_map = get_form_index_map(state)
    matchup_map = _matchup_advantage_map(state)

    team1_xi, team1_impact, notes1 = _build_team_xi(team1_players, state, form_map, matchup_map)
    team2_xi, team2_impact, notes2 = _build_team_xi(team2_players, state, form_map, matchup_map)

    return XISelectionOutput(
        team1_xi=team1_xi,
        team2_xi=team2_xi,
        team1_impact_player=team1_impact,
        team2_impact_player=team2_impact,
        selection_notes=notes1 + notes2[:2],
    )


def run(state: CricketState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(XISelectionOutput)

    team1_name = state.get("team1_name", "Team 1")
    team2_name = state.get("team2_name", "Team 2")
    team1_players, team2_players = get_validated_teams(state)

    try:
        response = structured_llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT + "\nReturn an XISelectionOutput object only."),
                HumanMessage(
                    content=(
                        f"Select the optimal XI for both teams in this IPL match.\n\n"
                        f"Team 1 ({team1_name}) validated squad: {to_payload(team1_players)}\n"
                        f"Team 2 ({team2_name}) validated squad: {to_payload(team2_players)}\n"
                        f"Form data: {to_payload(state.get('form'))}\n"
                        f"Venue data: {to_payload(state.get('venue_stats'))}\n"
                        f"Batter data: {to_payload(state.get('batter_data'))}\n"
                        f"Bowler data: {to_payload(state.get('bowler_data'))}\n"
                        f"Matchup data: {to_payload(state.get('matchups'))}\n"
                        f"Bowling rotation data: {to_payload(state.get('bowling_rotation'))}\n\n"
                        "Obey every non-negotiable selection rule and make the reasons specific."
                    )
                ),
            ]
        )
        output = XISelectionOutput.model_validate(response)
        return {"xi_selection": output}
    except Exception as exc:
        return {
            "xi_selection": _fallback_selection(state),
            "errors": append_error(state, f"XI selection node fell back to rules-based selection: {exc}"),
        }
