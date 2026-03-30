from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from config import get_llm
from graph.nodes._shared import append_error, get_validated_teams
from graph.state import CricketState
from schemas.models import FormOutput
from tools.cricket_tools import get_player_stats

SYSTEM_PROMPT = """
You are a cricket form analyst. Evaluate each player's recent
form using their last 5 performances.

Form Index (0-100):
- 80-100: Exceptional recent form (e.g., 3 consecutive 40+ scores)
- 60-79: Good form
- 40-59: Average / inconsistent
- 20-39: Poor form (scores under 15 in most recent matches)
- 0-19: Out of form or returning from injury

For bowlers, use wickets and economy:
- 80-100: 2+ wickets per game or economy < 7
- Below 40: Economy > 10 or no wickets in last 3 games

Be realistic with current IPL player form. Flag anyone
returning from injury as 30 form index by default.
""".strip()


def _stats_for_team(players: list[Any]) -> list[dict[str, Any]]:
    results = []
    for player in players:
        stats = get_player_stats.invoke({"player_name": player.name})
        results.append({"name": player.name, **stats})
    return results


def _form_index_from_stats(stats: dict[str, Any]) -> int:
    last_5_scores = stats.get("last_5_scores", [])
    strike_rate = float(stats.get("strike_rate", 0.0))
    economy = stats.get("economy")
    recent_wickets = int(stats.get("recent_wickets", 0))

    batting_score = 0
    if isinstance(last_5_scores, list) and last_5_scores:
        batting_score = min(100, int((sum(last_5_scores) / len(last_5_scores)) * 1.6))
        if sum(score >= 40 for score in last_5_scores) >= 3:
            batting_score = max(batting_score, 85)
        if sum(score < 15 for score in last_5_scores) >= 3:
            batting_score = min(batting_score, 35)

    bowling_score = 0
    if economy is not None:
        bowling_score = min(100, max(15, int((12.5 - float(economy)) * 14 + (recent_wickets * 4))))
        if recent_wickets >= 10:
            bowling_score = max(bowling_score, 85)
        if float(economy) > 10 and recent_wickets <= 1:
            bowling_score = min(bowling_score, 35)

    combined = max(batting_score, bowling_score, int(strike_rate / 2))
    return max(0, min(100, combined))


def _fallback_rankings(team_stats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rankings = []
    for stats in team_stats:
        rankings.append({"name": stats["name"], "form_index": _form_index_from_stats(stats)})
    rankings.sort(key=lambda item: item["form_index"], reverse=True)
    return rankings


def run(state: CricketState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(FormOutput)

    team1_name = state.get("team1_name", "Team 1")
    team2_name = state.get("team2_name", "Team 2")
    team1_players, team2_players = get_validated_teams(state)
    team1_stats = _stats_for_team(team1_players)
    team2_stats = _stats_for_team(team2_players)

    try:
        response = structured_llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"Evaluate recent form for these IPL squads.\n\n"
                        f"{team1_name} player stats: {team1_stats}\n\n"
                        f"{team2_name} player stats: {team2_stats}\n\n"
                        "Return structured output only."
                    )
                ),
            ]
        )
        output = FormOutput.model_validate(response)
        return {"form": output}
    except Exception as exc:
        team1_rankings = _fallback_rankings(team1_stats)
        team2_rankings = _fallback_rankings(team2_stats)
        combined = team1_rankings + team2_rankings
        output = FormOutput(
            team1_form_rankings=team1_rankings,
            team2_form_rankings=team2_rankings,
            in_form_players=[item["name"] for item in combined if item["form_index"] >= 80],
            out_of_form_players=[item["name"] for item in combined if item["form_index"] < 40],
        )
        return {
            "form": output,
            "errors": append_error(state, f"Form node fell back to rules-based scoring: {exc}"),
        }
