from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from config import get_llm
from graph.nodes._shared import append_error, to_payload
from graph.state import CricketState
from schemas.models import FinalReport, Matchup, TossOutput

SYSTEM_PROMPT = """
You are the head coach of an IPL franchise delivering the final
pre-match intelligence briefing to your coaching staff.

You have received analysis from 10+ specialized agents.
Your job is to synthesize everything into one authoritative,
concise report.

Structure your final report as:
1. Match context (2 lines: venue, conditions, what matters today)
2. The one key factor that will decide this match
   (e.g., "Dew will make chasing much easier — toss is critical")
3. Our batting plan in 3 bullet points
4. Our bowling plan in 3 bullet points
5. The three matchups that will define the match outcome
6. First innings target recommendation with reasoning
7. Overall confidence in the match plan (0.6-0.95)

Tone: Authoritative, data-backed, concise.
This is a coach talking to coaches — no fluff, all signal.
Make it feel like a real IPL dressing room document.
""".strip()


def _fallback_report(state: CricketState) -> FinalReport:
    team1_name = state.get("team1_name", "Team 1")
    team2_name = state.get("team2_name", "Team 2")
    match = f"{team1_name} vs {team2_name}"
    venue = to_payload(state.get("venue_stats") or {})
    toss = state.get("toss")
    toss_output = TossOutput.model_validate(to_payload(toss or {"decision": "bowl", "confidence": 0.72, "reasoning": "Chasing is marginally cleaner here. The surface should stay true enough for a stable pursuit."}))
    xi = to_payload(state.get("xi_selection") or {})
    own_strategy = to_payload(state.get("own_strategy") or {})
    opposition_strategy = to_payload(state.get("opposition_strategy") or {})
    matchups_payload = to_payload(state.get("matchups") or {})

    key_matchups = [
        Matchup.model_validate(item)
        for item in (matchups_payload.get("danger_matchups", []) + matchups_payload.get("exploit_matchups", []))[:3]
    ]

    sr_index = float(venue.get("venue_sr_index", 100))
    first_innings_target = 188 if sr_index > 110 else 154 if sr_index < 90 else 168

    batting_summary = (
        f"Powerplay target {own_strategy.get('powerplay_target', 55)} with the top order taking on identified danger matchups early; "
        f"middle overs revolve around {own_strategy.get('middle_overs_plan', 'controlled acceleration through the best matchup windows')}."
    )
    bowling_summary = (
        f"Restriction hinges on {opposition_strategy.get('middle_overs_plan', 'owning overs 7-15 with control bowlers')} "
        f"before executing {opposition_strategy.get('death_overs_plan', 'a disciplined death-over split')}."
    )
    form_summary = "Selection leaned on current form first, then venue fit and matchup leverage."

    return FinalReport(
        match=match,
        date=state.get("match_date", ""),
        venue=state.get("venue", ""),
        pitch_type=venue.get("pitch_type", "balanced"),
        dom_type=f"{venue.get('pitch_type', 'balanced')}-leaning conditions",
        batting_summary=batting_summary,
        bowling_summary=bowling_summary,
        form_summary=form_summary,
        key_battlegrounds=[
            f"{item.batter} vs {item.bowler} (SR {item.strike_rate}, {item.balls} balls)"
            for item in key_matchups
        ],
        toss_recommendation=toss_output,
        team1_playing_xi=xi.get("team1_xi", []),
        team2_playing_xi=xi.get("team2_xi", []),
        team1_bowling_plan=to_payload(state.get("bowling_rotation") or {}),
        team2_bowling_plan={"plan": opposition_strategy.get("death_overs_plan", "Mirror the matchup-led death plan for the opposition innings.")},
        first_innings_target=first_innings_target,
        key_matchups=key_matchups,
        confidence_score=float(toss_output.confidence),
    )


def run(state: CricketState) -> dict:
    llm = get_llm()
    structured_llm = llm.with_structured_output(FinalReport)

    try:
        response = structured_llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT + "\nReturn a FinalReport object only."),
                HumanMessage(
                    content=(
                        f"Match metadata: {state.get('team1_name', 'Team 1')} vs {state.get('team2_name', 'Team 2')} on {state.get('match_date', '')} at {state.get('venue', '')}\n"
                        f"Eligibility: {to_payload(state.get('eligibility'))}\n"
                        f"Venue: {to_payload(state.get('venue_stats'))}\n"
                        f"Form: {to_payload(state.get('form'))}\n"
                        f"Batter analysis: {to_payload(state.get('batter_data'))}\n"
                        f"Bowler analysis: {to_payload(state.get('bowler_data'))}\n"
                        f"Matchups: {to_payload(state.get('matchups'))}\n"
                        f"Toss: {to_payload(state.get('toss'))}\n"
                        f"Bowling rotation: {to_payload(state.get('bowling_rotation'))}\n"
                        f"XI selection: {to_payload(state.get('xi_selection'))}\n"
                        f"Own strategy: {to_payload(state.get('own_strategy'))}\n"
                        f"Opposition strategy: {to_payload(state.get('opposition_strategy'))}\n"
                        "Synthesize this into a concise dressing-room quality final report."
                    )
                ),
            ]
        )
        output = FinalReport.model_validate(response)
        return {"final_report": output}
    except Exception as exc:
        return {
            "final_report": _fallback_report(state),
            "errors": append_error(state, f"Coach node fell back to synthesized summary: {exc}"),
        }
