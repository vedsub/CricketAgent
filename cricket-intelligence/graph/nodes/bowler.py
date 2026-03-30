from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from config import get_llm
from graph.nodes._shared import append_error, get_validated_teams, normalize_text
from graph.state import CricketState
from schemas.models import BowlerOutput, BowlerProfile
from tools.cricket_tools import get_player_stats

SYSTEM_PROMPT = """
You are a bowling analyst for IPL T20 cricket. Profile each bowler:

Classify their best phase based on their bowling style and stats:
- Powerplay specialists: Swing bowlers, opening pacers with
  the new ball, aggressive spinners who can take early wickets
- Middle over specialists: Cutters, variations bowlers,
  off-spinners who dry up runs
- Death specialists: Bowlers with strong yorker skills,
  bowlers with low death economy (under 9 in death overs)

Economy benchmarks for IPL:
- Excellent: Under 7.5
- Good: 7.5 - 8.5
- Average: 8.5 - 9.5
- Poor: Over 9.5

Use real IPL 2024-25 stats where known.
""".strip()

POWERPLAY_NAMES = {"trent boult", "deepak chahar", "mohammed shami", "bhuvneshwar kumar", "khaleel ahmed"}
DEATH_NAMES = {"jasprit bumrah", "matheesha pathirana", "harshal patel", "t natarajan", "arshdeep singh", "kagiso rabada"}
MIDDLE_NAMES = {"ravindra jadeja", "ravichandran ashwin", "rashid khan", "kuldeep yadav", "varun chakaravarthy", "rahul chahar", "mitchell santner", "sai kishore"}


def _best_phase(player_name: str, bowling_style: str, economy: float, wickets_per_match: float) -> str:
    name_key = normalize_text(player_name).lower()
    style = bowling_style.lower()

    if name_key in DEATH_NAMES or ("yorker" in style) or (economy < 9 and wickets_per_match >= 1.8):
        return "death"
    if name_key in POWERPLAY_NAMES or ("left-arm fast" in style) or ("swing" in style):
        return "powerplay"
    if name_key in MIDDLE_NAMES or ("spin" in style) or ("offbreak" in style) or ("legbreak" in style):
        return "middle"
    return "powerplay" if economy <= 8.2 else "middle"


def _collect_bowlers(state: CricketState) -> list[dict[str, Any]]:
    team1_players, team2_players = get_validated_teams(state)
    players = []
    for player in team1_players + team2_players:
        if player.role in {"bowler", "all-rounder"} and player.bowling_style.lower() not in {"none", "unknown"}:
            stats = get_player_stats.invoke({"player_name": player.name})
            players.append(
                {
                    "name": player.name,
                    "bowling_style": player.bowling_style,
                    "stats": stats,
                }
            )
    return players


def _fallback_output(players: list[dict[str, Any]]) -> BowlerOutput:
    profiles: dict[str, BowlerProfile] = {}
    powerplay_specialists: list[str] = []
    death_specialists: list[str] = []
    middle_over_specialists: list[str] = []

    for player in players:
        stats = player["stats"]
        recent_wickets = int(stats.get("recent_wickets", 0))
        wickets_per_match = round(recent_wickets / 5, 2)
        economy = float(stats.get("economy", 8.5) or 8.5)
        phase = _best_phase(player["name"], player["bowling_style"], economy, wickets_per_match)
        profile = BowlerProfile(
            name=player["name"],
            bowling_type=player["bowling_style"],
            economy=economy,
            wickets_per_match=wickets_per_match,
            best_phase=phase,
        )
        profiles[player["name"]] = profile

        if phase == "powerplay":
            powerplay_specialists.append(player["name"])
        elif phase == "death":
            death_specialists.append(player["name"])
        else:
            middle_over_specialists.append(player["name"])

    return BowlerOutput(
        bowler_profiles=profiles,
        powerplay_specialists=powerplay_specialists,
        death_specialists=death_specialists,
        middle_over_specialists=middle_over_specialists,
    )


def run(state: CricketState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(BowlerOutput)

    players = _collect_bowlers(state)

    try:
        response = structured_llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"Bowler candidate data: {players}\n\n"
                        "Return a BowlerOutput object only."
                    )
                ),
            ]
        )
        output = BowlerOutput.model_validate(response)
        return {"bowler_data": output}
    except Exception as exc:
        return {
            "bowler_data": _fallback_output(players),
            "errors": append_error(state, f"Bowler node fell back to heuristics: {exc}"),
        }
