from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from config import get_llm
from graph.nodes._shared import append_error, get_validated_teams, message_content, normalize_text
from graph.state import CricketState
from schemas.models import Matchup, MatchupOutput, PlayerProfile
from tools.cricket_tools import get_h2h_stats

SYSTEM_PROMPT = """
You are a T20 cricket matchup specialist. Your job is to build
a head-to-head matchup matrix between the two teams.

Matchup classification rules:
- DANGER matchup (batter dominates): SR > 180, OR (SR > 140 AND W=0
  with 10+ balls faced)
- EXPLOIT matchup (bowler dominates): W >= 2 in under 20 balls,
  OR SR < 80 with 15+ balls
- NEUTRAL: Everything else

Type-based matchups (use when H2H data is sparse):
- Left-hand batter vs Left-arm pace: Generally dangerous for bowler
- Right-hand batter vs Left-arm orthodox spin: Historically bowler-friendly
- Aggressive batter vs wrist spinner: Volatile — could go either way

When printing matchup results, format exactly like:
  [Batter Name] vs [Bowler Name]    SR:[value] W:[value] ([balls]b)

Identify the top 3 danger matchups and top 3 exploit matchups.
These are critical for the XI selection and bowling rotation agents.
""".strip()


def _form_index_map(state: CricketState) -> dict[str, int]:
    form = state.get("form")
    if not form:
        return {}

    form_payload = form.model_dump() if hasattr(form, "model_dump") else form
    mapping: dict[str, int] = {}
    for item in form_payload.get("team1_form_rankings", []) + form_payload.get("team2_form_rankings", []):
        name = normalize_text(item.get("name")).lower()
        if name:
            mapping[name] = int(item.get("form_index", 50))
    return mapping


def _top_batters(players: list[PlayerProfile], form_map: dict[str, int]) -> list[PlayerProfile]:
    candidates = [player for player in players if player.role in {"batter", "all-rounder", "wicket-keeper"}]
    ranked = sorted(
        candidates,
        key=lambda player: (
            form_map.get(normalize_text(player.name).lower(), 50),
            1 if player.role == "wicket-keeper" else 0,
            1 if player.role == "batter" else 0,
        ),
        reverse=True,
    )
    return ranked[:6]


def _all_bowlers(players: list[PlayerProfile]) -> list[PlayerProfile]:
    return [
        player
        for player in players
        if player.role in {"bowler", "all-rounder"} and player.bowling_style.lower() not in {"none", "unknown"}
    ]


def _classify_matchup(strike_rate: float, wickets: int, balls: int) -> str:
    if strike_rate > 180 or (strike_rate > 140 and wickets == 0 and balls >= 10):
        return "danger"
    if (wickets >= 2 and balls < 20) or (strike_rate < 80 and balls >= 15):
        return "exploit"
    return "neutral"


def _type_matchup_insight(batter: PlayerProfile, bowler: PlayerProfile, form_map: dict[str, int]) -> dict[str, Any]:
    batter_style = batter.batting_style.lower()
    bowling_style = bowler.bowling_style.lower()
    batter_form = form_map.get(normalize_text(batter.name).lower(), 50)

    if batter_style.startswith("left") and "left-arm" in bowling_style and "fast" in bowling_style:
        insight = "Left-hand batter versus left-arm pace usually favors the batter's scoring zones."
        matchup_type = "danger"
    elif batter_style.startswith("right") and "left-arm orthodox" in bowling_style:
        insight = "Right-hand batter versus left-arm orthodox spin is often a control matchup for the bowler."
        matchup_type = "exploit"
    elif batter_form >= 75 and ("legbreak" in bowling_style or "wrist" in bowling_style or "googly" in bowling_style):
        insight = "Aggressive in-form batter versus wrist spin is volatile and can swing quickly."
        matchup_type = "neutral"
    else:
        insight = "No strong type-based edge beyond normal matchup variance."
        matchup_type = "neutral"

    return {
        "batter": batter.name,
        "bowler": bowler.name,
        "insight": insight,
        "matchup_type": matchup_type,
    }


def _build_pairs(
    team1_batters: list[PlayerProfile],
    team2_bowlers: list[PlayerProfile],
    team2_batters: list[PlayerProfile],
    team1_bowlers: list[PlayerProfile],
) -> list[tuple[PlayerProfile, PlayerProfile]]:
    pairs: list[tuple[PlayerProfile, PlayerProfile]] = []
    for batter in team1_batters:
        for bowler in team2_bowlers:
            pairs.append((batter, bowler))
    for batter in team2_batters:
        for bowler in team1_bowlers:
            pairs.append((batter, bowler))
    return pairs


def _fallback_output(state: CricketState) -> MatchupOutput:
    team1_players, team2_players = get_validated_teams(state)
    form_map = _form_index_map(state)

    team1_batters = _top_batters(team1_players, form_map)
    team2_batters = _top_batters(team2_players, form_map)
    team1_bowlers = _all_bowlers(team1_players)
    team2_bowlers = _all_bowlers(team2_players)

    danger: list[Matchup] = []
    exploit: list[Matchup] = []
    type_matchups: list[dict[str, Any]] = []
    bowl_hand_insights: list[str] = []

    for batter, bowler in _build_pairs(team1_batters, team2_bowlers, team2_batters, team1_bowlers):
        stats = get_h2h_stats.invoke({"batter": batter.name, "bowler": bowler.name})
        balls = int(stats.get("balls", 0))
        runs = int(stats.get("runs", 0))
        wickets = int(stats.get("wickets", 0))
        strike_rate = float(stats.get("strike_rate", 0.0))
        matchup_type = _classify_matchup(strike_rate, wickets, balls)
        matchup = Matchup(
            batter=batter.name,
            bowler=bowler.name,
            balls=balls,
            runs=runs,
            wickets=wickets,
            strike_rate=strike_rate,
            matchup_type=matchup_type,
        )

        if matchup_type == "danger":
            danger.append(matchup)
        elif matchup_type == "exploit":
            exploit.append(matchup)

        if balls < 20:
            insight = _type_matchup_insight(batter, bowler, form_map)
            type_matchups.append(insight)
            bowl_hand_insights.append(
                f"{batter.name} vs {bowler.name}: {insight['insight']}"
            )

    danger = sorted(danger, key=lambda item: (item.strike_rate, -item.wickets, item.balls), reverse=True)[:3]
    exploit = sorted(exploit, key=lambda item: (item.wickets, -item.strike_rate, -item.balls), reverse=True)[:3]

    return MatchupOutput(
        total_h2h=len(_build_pairs(team1_batters, team2_bowlers, team2_batters, team1_bowlers)),
        danger_matchups=danger,
        exploit_matchups=exploit,
        type_matchups=type_matchups[:8],
        bowl_hand_insights=bowl_hand_insights[:8],
    )


def run(state: CricketState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(MatchupOutput)

    team1_name = state.get("team1_name", "Team 1")
    team2_name = state.get("team2_name", "Team 2")
    team1_players, team2_players = get_validated_teams(state)
    form_map = _form_index_map(state)
    team1_batters = _top_batters(team1_players, form_map)
    team2_batters = _top_batters(team2_players, form_map)
    team1_bowlers = _all_bowlers(team1_players)
    team2_bowlers = _all_bowlers(team2_players)
    pairs = _build_pairs(team1_batters, team2_bowlers, team2_batters, team1_bowlers)

    agent = create_react_agent(llm, [get_h2h_stats])
    pair_lines = "\n".join(
        f"- {batter.name} vs {bowler.name}"
        for batter, bowler in pairs
    )

    try:
        agent_result = agent.invoke(
            {
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            f"Build the matchup matrix for {team1_name} vs {team2_name}.\n"
                            "Call get_h2h_stats for every pair listed below and then summarize the critical edges.\n"
                            f"{pair_lines}"
                        )
                    ),
                ]
            }
        )
        transcript = message_content(agent_result.get("messages", []))
        response = structured_llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT + "\nReturn a MatchupOutput object only."),
                HumanMessage(
                    content=(
                        f"Match context: {team1_name} vs {team2_name}\n"
                        f"Tool transcript:\n{transcript}\n\n"
                        "Use the rules exactly and keep only the top 3 danger and top 3 exploit matchups."
                    )
                ),
            ]
        )
        output = MatchupOutput.model_validate(response)
        return {"matchups": output}
    except Exception as exc:
        return {
            "matchups": _fallback_output(state),
            "errors": append_error(state, f"Matchup node fell back to direct H2H heuristics: {exc}"),
        }
