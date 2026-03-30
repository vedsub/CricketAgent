from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from config import get_llm
from graph.nodes._shared import append_error, get_validated_teams, normalize_text
from graph.state import CricketState
from schemas.models import TossOutput

SYSTEM_PROMPT = """
You are a T20 toss strategy expert. Recommend bat or bowl
based on these weighted factors:

1. Venue history (40% weight): What % of toss winners chose to bat
   and won at this ground?
2. Pitch + dew (30% weight): Evening matches at most IPL venues
   develop heavy dew after 25 overs — this strongly favors chasing.
3. Team batting depth (20% weight): A team with a stronger lower
   order may prefer setting a target.
4. Form (10% weight): In-form batting line-up → bat first.

IPL-specific knowledge:
- Wankhede (Mumbai), Chinnaswamy (Bengaluru): Historically chase-friendly
  due to dew. Usually bowl first.
- Chepauk (Chennai): Spin-friendly pitch. Bat first, post a total.
- Eden Gardens (Kolkata): Bat first in early tournament.
  Chase-friendly in playoffs due to dew.

Output confidence between 0.6 and 0.95.
Below 0.6 means genuinely coin-flip — still pick one.
Give exactly 2 sentences of reasoning.
""".strip()


def _form_index_map(state: CricketState) -> dict[str, int]:
    form = state.get("form")
    if not form:
        return {}

    payload = form.model_dump() if hasattr(form, "model_dump") else form
    mapping: dict[str, int] = {}
    for item in payload.get("team1_form_rankings", []) + payload.get("team2_form_rankings", []):
        name = normalize_text(item.get("name")).lower()
        if name:
            mapping[name] = int(item.get("form_index", 50))
    return mapping


def _team_batting_depth(players: list, form_map: dict[str, int]) -> int:
    depth = 0
    for player in players:
        if player.role in {"all-rounder", "wicket-keeper"}:
            depth += 2
        elif player.role == "batter":
            depth += 1
        depth += 1 if form_map.get(normalize_text(player.name).lower(), 50) >= 70 else 0
    return depth


def _fallback_decision(state: CricketState) -> TossOutput:
    venue_stats = state.get("venue_stats")
    venue_payload = venue_stats.model_dump() if hasattr(venue_stats, "model_dump") else (venue_stats or {})
    form_map = _form_index_map(state)
    team1_players, team2_players = get_validated_teams(state)
    venue_name = state.get("venue", "")

    team1_depth = _team_batting_depth(team1_players, form_map)
    team2_depth = _team_batting_depth(team2_players, form_map)
    avg_form = sum(form_map.values()) / len(form_map) if form_map else 55

    venue_score = 40 if venue_payload.get("toss_recommendation") == "bat" else -40
    key = normalize_text(venue_name).lower()
    if "wankhede" in key or "chinnaswamy" in key:
        venue_score -= 12
    elif "chepauk" in key or "chidambaram" in key:
        venue_score += 12
    elif "eden gardens" in key:
        venue_score += 4

    pitch_score = 0
    if venue_payload.get("pitch_type") == "spin":
        pitch_score += 10
    elif venue_payload.get("pitch_type") == "pace":
        pitch_score -= 6
    if venue_payload.get("avg_first_innings_score", 175) >= 185:
        pitch_score -= 12

    depth_score = 8 if max(team1_depth, team2_depth) - min(team1_depth, team2_depth) >= 3 else 2
    form_score = 5 if avg_form >= 72 else -4 if avg_form <= 48 else 0

    total_score = venue_score + pitch_score + depth_score + form_score
    decision = "bat" if total_score > 0 else "bowl"
    confidence = round(min(0.95, max(0.6, 0.6 + (abs(total_score) / 100))), 2)

    if decision == "bat":
        reasoning = (
            "Venue history and surface profile point toward scoreboard pressure being the cleaner path in this matchup. "
            "The batting depth signals are strong enough that setting a target looks slightly safer than exposing the chase to late spin or variation."
        )
    else:
        reasoning = (
            "The venue and innings profile lean toward chasing, so taking the ball first is the more practical toss move here. "
            "That route also protects both sides from late-innings uncertainty and makes better use of dew or a high-scoring outfield if conditions open up."
        )

    return TossOutput(decision=decision, confidence=confidence, reasoning=reasoning)


def run(state: CricketState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(TossOutput)

    team1_name = state.get("team1_name", "Team 1")
    team2_name = state.get("team2_name", "Team 2")
    venue_name = state.get("venue", "Unknown venue")
    venue_stats = state.get("venue_stats")
    form = state.get("form")
    team1_players, team2_players = get_validated_teams(state)

    venue_payload = venue_stats.model_dump() if hasattr(venue_stats, "model_dump") else venue_stats
    form_payload = form.model_dump() if hasattr(form, "model_dump") else form

    try:
        response = structured_llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        f"Match: {team1_name} vs {team2_name}\n"
                        f"Venue: {venue_name}\n"
                        f"Venue stats: {venue_payload}\n"
                        f"Form data: {form_payload}\n"
                        f"Team 1 squad roles: {[{'name': p.name, 'role': p.role} for p in team1_players]}\n"
                        f"Team 2 squad roles: {[{'name': p.name, 'role': p.role} for p in team2_players]}\n"
                        "Return a TossOutput object only with exactly 2 sentences of reasoning."
                    )
                ),
            ]
        )
        output = TossOutput.model_validate(response)
        return {"toss": output}
    except Exception as exc:
        return {
            "toss": _fallback_decision(state),
            "errors": append_error(state, f"Toss node fell back to weighted heuristics: {exc}"),
        }
