from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from config import get_llm
from graph.nodes._shared import append_error, get_validated_teams, normalize_text
from graph.state import CricketState
from schemas.models import BatterOutput, BatterProfile
from tools.cricket_tools import get_player_stats

SYSTEM_PROMPT = """
You are a batting analyst for T20 cricket. Profile each batter:

Venue SR Index: How does their strike rate at this specific venue
compare to their overall T20 SR? Above 110% = high venue SR.

Type vulnerability: Is this batter vulnerable to:
- Left-arm pace (front foot weakness)
- Off-spin (struggles against turn from off)
- Short-pitch pace (poor against bouncers)
- Wrist spin (struggles against googly)

Use known player tendencies from IPL history.
Be specific — not every batter is vulnerable.
Known examples: Many right-handers struggle vs left-arm pace.
Some aggressive batters have poor records against wrist spin.
""".strip()

KNOWN_VULNERABILITIES = {
    "rohit sharma": "left-arm pace",
    "sanju samson": "wrist spin",
    "shivam dube": "short-pitch pace",
    "kl rahul": "wrist spin",
    "ruturaj gaikwad": "left-arm pace",
    "suryakumar yadav": "wrist spin",
    "jos buttler": "off-spin",
    "phil salt": "short-pitch pace",
}

VENUE_MODIFIERS = {
    "chinnaswamy": 12,
    "wankhede": 8,
    "eden gardens": 6,
    "narendra modi": 4,
    "arun jaitley": 7,
    "rajiv gandhi": 5,
    "chepauk": -10,
    "chidambaram": -10,
    "ekana": -12,
    "sawai mansingh": -6,
}


def _venue_index(venue_name: str, strike_rate: float) -> float:
    key = normalize_text(venue_name).lower()
    modifier = 0
    for venue_key, value in VENUE_MODIFIERS.items():
        if venue_key in key:
            modifier = value
            break
    base = 100 + modifier + ((strike_rate - 140) * 0.18)
    return round(max(80, min(130, base)), 1)


def _vulnerability_for_player(player_name: str, batting_style: str) -> str | None:
    name_key = normalize_text(player_name).lower()
    if name_key in KNOWN_VULNERABILITIES:
        return KNOWN_VULNERABILITIES[name_key]
    if batting_style.lower().startswith("right"):
        return "left-arm pace"
    if batting_style.lower().startswith("left"):
        return "off-spin"
    return None


def _collect_batters(state: CricketState) -> list[dict[str, Any]]:
    team1_players, team2_players = get_validated_teams(state)
    players = []
    for player in team1_players + team2_players:
        if player.role in {"batter", "all-rounder", "wicket-keeper"}:
            stats = get_player_stats.invoke({"player_name": player.name})
            players.append(
                {
                    "name": player.name,
                    "role": player.role,
                    "batting_style": player.batting_style,
                    "stats": stats,
                }
            )
    return players


def _fallback_output(venue_name: str, players: list[dict[str, Any]]) -> BatterOutput:
    profiles: dict[str, BatterProfile] = {}
    high_venue_sr: list[str] = []
    type_vulnerable: list[str] = []

    for player in players:
        stats = player["stats"]
        venue_sr = _venue_index(venue_name, float(stats.get("strike_rate", 130.0)))
        vulnerability_type = _vulnerability_for_player(player["name"], player["batting_style"])
        profile = BatterProfile(
            name=player["name"],
            venue_sr=venue_sr,
            is_type_vulnerable=vulnerability_type is not None,
            vulnerability_type=vulnerability_type,
            recent_avg=float(stats.get("average", 0.0)),
        )
        profiles[player["name"]] = profile
        if venue_sr > 110:
            high_venue_sr.append(player["name"])
        if vulnerability_type:
            type_vulnerable.append(player["name"])

    return BatterOutput(
        batters_profiled=len(profiles),
        type_vulnerable=type_vulnerable,
        high_venue_sr=high_venue_sr,
        batter_profiles=profiles,
    )


def run(state: CricketState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(BatterOutput)

    venue_name = state.get("venue", "Unknown venue")
    players = _collect_batters(state)

    try:
        response = structured_llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"Venue: {venue_name}\n"
                        f"Batter candidate data: {players}\n\n"
                        "Return a BatterOutput object only."
                    )
                ),
            ]
        )
        output = BatterOutput.model_validate(response)
        return {"batter_data": output}
    except Exception as exc:
        return {
            "batter_data": _fallback_output(venue_name, players),
            "errors": append_error(state, f"Batter node fell back to heuristics: {exc}"),
        }
