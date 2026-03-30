from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from config import get_llm
from graph.nodes._shared import append_error, message_content, normalize_text
from graph.state import CricketState
from schemas.models import VenueOutput
from tools.cricket_tools import get_venue_stats, get_weather

SYSTEM_PROMPT = """
You are a cricket venue analyst specializing in IPL grounds.
Use the get_venue_stats tool to fetch pitch data.
Use the get_weather tool to get match-day conditions.

Analyze:
- Pitch type: Does the surface favor pace or spin?
- Historical averages: first innings score, powerplay score
- Toss decision: Based on pitch + dew factor + average scores,
  should the team winning the toss choose to bat or bowl?
- Venue SR Index: A score 80-120 measuring how batting-friendly
  this venue is relative to league average (100)

Chinnaswamy is always 115+. Chepauk is spin-friendly (below 95).
""".strip()


def _fallback_pitch_type(pace_wicket_pct: float, spin_wicket_pct: float) -> str:
    if pace_wicket_pct >= spin_wicket_pct + 6:
        return "pace"
    if spin_wicket_pct >= pace_wicket_pct + 6:
        return "spin"
    return "balanced"


def _fallback_sr_index(venue_name: str, avg_first_innings: int, avg_powerplay: int) -> float:
    key = normalize_text(venue_name).lower()
    base = 100 + ((avg_first_innings - 175) * 0.45) + ((avg_powerplay - 50) * 0.8)
    if "chinnaswamy" in key:
        base = max(base, 115)
    if "chepauk" in key or "chidambaram" in key:
        base = min(base, 94)
    return round(max(80, min(120, base)), 1)


def _fallback_toss_decision(
    pitch_type: str,
    avg_first_innings: int,
    toss_win_bat_pct: float,
    dew_factor: bool,
) -> str:
    if dew_factor or avg_first_innings >= 185:
        return "bowl"
    if pitch_type == "spin" and toss_win_bat_pct >= 50:
        return "bat"
    return "bowl" if toss_win_bat_pct < 45 else "bat"


def run(state: CricketState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(VenueOutput)

    venue_name = state.get("venue", "Unknown venue")
    match_date = state.get("match_date", "Unknown date")
    agent = create_react_agent(llm, [get_venue_stats, get_weather])

    user_prompt = (
        f"Analyze the IPL venue '{venue_name}' for a match on {match_date}. "
        "Use tools first, then provide enough reasoning context for a structured venue assessment."
    )

    try:
        agent_result = agent.invoke(
            {
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_prompt),
                ]
            }
        )
        tool_transcript = message_content(agent_result.get("messages", []))
        response = structured_llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT + "\nReturn a VenueOutput object only."),
                HumanMessage(
                    content=(
                        f"Venue: {venue_name}\n"
                        f"Match date: {match_date}\n"
                        f"Tool transcript:\n{tool_transcript}"
                    )
                ),
            ]
        )
        output = VenueOutput.model_validate(response)
        return {"venue_stats": output}
    except Exception as exc:
        venue_stats = get_venue_stats.invoke({"venue_name": venue_name})
        weather = get_weather.invoke({"venue": venue_name, "date": match_date})
        pitch_type = _fallback_pitch_type(
            float(venue_stats.get("pace_wicket_pct", 50.0)),
            float(venue_stats.get("spin_wicket_pct", 50.0)),
        )
        output = VenueOutput(
            venue_name=venue_name,
            pitch_type=pitch_type,
            avg_first_innings_score=int(venue_stats.get("avg_first_innings", 175)),
            avg_powerplay_score=int(venue_stats.get("avg_powerplay", 50)),
            pace_wicket_pct=float(venue_stats.get("pace_wicket_pct", 50.0)),
            spin_wicket_pct=float(venue_stats.get("spin_wicket_pct", 50.0)),
            venue_sr_index=_fallback_sr_index(
                venue_name,
                int(venue_stats.get("avg_first_innings", 175)),
                int(venue_stats.get("avg_powerplay", 50)),
            ),
            toss_recommendation=_fallback_toss_decision(
                pitch_type=pitch_type,
                avg_first_innings=int(venue_stats.get("avg_first_innings", 175)),
                toss_win_bat_pct=float(venue_stats.get("toss_win_bat_pct", 50.0)),
                dew_factor=bool(weather.get("dew_factor", False)),
            ),
        )
        return {
            "venue_stats": output,
            "errors": append_error(state, f"Venue node fell back to tool heuristics: {exc}"),
        }
