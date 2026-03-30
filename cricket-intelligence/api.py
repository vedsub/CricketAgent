from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config import LANGCHAIN_API_KEY, get_llm
from graph.graph import app_graph, build_run_config
from graph.state import CricketState
from schemas.models import FinalReport
from tools.cricket_tools import MOCK_SQUADS, MOCK_VENUE_STATS, get_squad

app = FastAPI(title="Cricket Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    team1: str
    team2: str
    venue: str
    match_date: str


NODE_PROGRESS = {
    "eligibility": ("Layer 0 - Eligibility & Squad Validation", 10),
    "venue": ("Layer 1 - Venue Agent", 18),
    "form": ("Layer 1 - Form Agent", 26),
    "batter": ("Layer 1 - Batter Agent", 34),
    "bowler": ("Layer 1 - Bowler Agent", 40),
    "matchup": ("Layer 2 - Matchup Agent", 48),
    "toss": ("Layer 2 - Toss Agent", 56),
    "bowling_rotation": ("Layer 2 - Bowling Rotation Agent", 65),
    "xi_selection": ("Layer 2.5 - XI Selection", 75),
    "own_strategy": ("Layer 3 - Strategy", 80),
    "opposition_strategy": ("Layer 3 - Strategy", 85),
    "coach": ("Layer 4 - Coach Final Synthesis", 100),
}

VENUE_CITIES = {
    "wankhede stadium": "Mumbai",
    "ma chidambaram stadium": "Chennai",
    "narendra modi stadium": "Ahmedabad",
    "eden gardens": "Kolkata",
    "m chinnaswamy stadium": "Bengaluru",
    "rajiv gandhi international stadium": "Hyderabad",
    "sawai mansingh stadium": "Jaipur",
    "arun jaitley stadium": "Delhi",
    "punjab cricket association stadium": "Mohali",
    "ekana cricket stadium": "Lucknow",
}

DISPLAY_VENUES = {
    "wankhede stadium": "Wankhede Stadium",
    "ma chidambaram stadium": "M A Chidambaram Stadium",
    "narendra modi stadium": "Narendra Modi Stadium",
    "eden gardens": "Eden Gardens",
    "m chinnaswamy stadium": "M Chinnaswamy Stadium",
    "rajiv gandhi international stadium": "Rajiv Gandhi International Stadium",
    "sawai mansingh stadium": "Sawai Mansingh Stadium",
    "arun jaitley stadium": "Arun Jaitley Stadium",
    "punjab cricket association stadium": "Punjab Cricket Association Stadium",
    "ekana cricket stadium": "Ekana Cricket Stadium",
}


def _to_payload(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {key: _to_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_payload(item) for item in value]
    return value


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _pitch_type(stats: dict[str, Any]) -> str:
    pace = float(stats.get("pace_wicket_pct", 50.0))
    spin = float(stats.get("spin_wicket_pct", 50.0))
    if pace >= spin + 6:
        return "pace"
    if spin >= pace + 6:
        return "spin"
    return "balanced"


def _venue_sr_index(venue_name: str, stats: dict[str, Any]) -> float:
    avg_first = int(stats.get("avg_first_innings", 175))
    avg_powerplay = int(stats.get("avg_powerplay", 50))
    key = _normalize(venue_name)
    base = 100 + ((avg_first - 175) * 0.45) + ((avg_powerplay - 50) * 0.8)
    if "chinnaswamy" in key:
        base = max(base, 115)
    if "chepauk" in key or "chidambaram" in key:
        base = min(base, 94)
    return round(max(80, min(120, base)), 1)


async def _fetch_squad(team_name: str) -> list[dict[str, Any]]:
    return await asyncio.to_thread(get_squad.invoke, {"team_name": team_name})


async def build_initial_state(request: AnalyzeRequest) -> CricketState:
    team1_squad_raw, team2_squad_raw = await asyncio.gather(
        _fetch_squad(request.team1),
        _fetch_squad(request.team2),
    )

    return {
        "team1_name": request.team1,
        "team2_name": request.team2,
        "venue": request.venue,
        "match_date": request.match_date,
        "team1_squad_raw": team1_squad_raw,
        "team2_squad_raw": team2_squad_raw,
        "eligibility": None,
        "venue_stats": None,
        "form": None,
        "batter_data": None,
        "bowler_data": None,
        "matchups": None,
        "toss": None,
        "bowling_rotation": None,
        "xi_selection": None,
        "own_strategy": None,
        "opposition_strategy": None,
        "final_report": None,
        "errors": [],
        "completed_layers": [],
        "messages": [],
    }


def _node_summary(node_name: str, output: dict[str, Any]) -> str:
    if node_name == "eligibility":
        data = _to_payload(output.get("eligibility", {}))
        team1_count = len(data.get("team1_validated", []))
        team2_count = len(data.get("team2_validated", []))
        issues = len(data.get("flagged_issues", []))
        return f"{team1_count + team2_count} players validated across both squads. Flagged issues: {issues}."

    if node_name == "venue":
        data = _to_payload(output.get("venue_stats", {}))
        return (
            f"{data.get('pitch_type', 'balanced').title()} surface, avg first innings "
            f"{data.get('avg_first_innings_score', '?')}, toss call: {data.get('toss_recommendation', '?')}."
        )

    if node_name == "form":
        data = _to_payload(output.get("form", {}))
        return (
            f"In-form players: {len(data.get('in_form_players', []))}. "
            f"Out-of-form players: {len(data.get('out_of_form_players', []))}."
        )

    if node_name == "batter":
        data = _to_payload(output.get("batter_data", {}))
        high_sr = ", ".join(data.get("high_venue_sr", [])[:3]) or "none highlighted"
        return f"{data.get('batters_profiled', 0)} batters profiled. High venue SR: [{high_sr}]."

    if node_name == "bowler":
        data = _to_payload(output.get("bowler_data", {}))
        death = ", ".join(data.get("death_specialists", [])[:3]) or "none highlighted"
        return f"{len(data.get('bowler_profiles', {}))} bowlers profiled. Death options: [{death}]."

    if node_name == "matchup":
        data = _to_payload(output.get("matchups", {}))
        return (
            f"Danger matchups: {len(data.get('danger_matchups', []))}. "
            f"Exploit matchups: {len(data.get('exploit_matchups', []))}."
        )

    if node_name == "toss":
        data = _to_payload(output.get("toss", {}))
        return f"Toss recommendation: {data.get('decision', '?')} with confidence {data.get('confidence', '?')}."

    if node_name == "bowling_rotation":
        data = _to_payload(output.get("bowling_rotation", {}))
        powerplay = ", ".join(data.get("powerplay_bowlers", [])[:3]) or "not set"
        return f"Powerplay bowlers: [{powerplay}]. 20-over plan prepared."

    if node_name == "xi_selection":
        data = _to_payload(output.get("xi_selection", {}))
        preview = ", ".join(player.get("name", "") for player in data.get("team1_xi", [])[:3])
        return f"Playing XIs selected. Team 1 top order starts with [{preview}]."

    if node_name == "own_strategy":
        data = _to_payload(output.get("own_strategy", {}))
        return f"Own batting plan set. Powerplay target: {data.get('powerplay_target', '?')}."

    if node_name == "opposition_strategy":
        data = _to_payload(output.get("opposition_strategy", {}))
        threats = ", ".join(data.get("key_threats", [])[:2]) or "top opposition threats"
        return f"Restriction plan ready. Key threats: [{threats}]."

    if node_name == "coach":
        data = _to_payload(output.get("final_report", {}))
        return f"Final report ready for {data.get('match', 'the match')}."

    return "Node completed."


def _event_node_name(event: dict[str, Any]) -> str | None:
    metadata = event.get("metadata", {}) or {}
    node_name = metadata.get("langgraph_node")
    if node_name in NODE_PROGRESS and event.get("name") == node_name:
        return node_name
    return None


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "cricket-intelligence", "message": "Cricket intelligence graph API is running."}


@app.post("/analyze", response_model=FinalReport)
async def analyze(request: AnalyzeRequest) -> FinalReport:
    initial_state = await build_initial_state(request)
    config = build_run_config(request.team1, request.team2, request.match_date, str(uuid.uuid4()))
    result = await app_graph.ainvoke(initial_state, config=config)
    return FinalReport.model_validate(_to_payload(result["final_report"]))


@app.post("/analyze/stream")
async def analyze_stream(request: AnalyzeRequest) -> EventSourceResponse:
    return EventSourceResponse(_analyze_stream_generator(request))


@app.get("/analyze/stream")
async def analyze_stream_get(
    team1: str = Query(...),
    team2: str = Query(...),
    venue: str = Query(...),
    match_date: str = Query(...),
) -> EventSourceResponse:
    request = AnalyzeRequest(team1=team1, team2=team2, venue=venue, match_date=match_date)
    return EventSourceResponse(_analyze_stream_generator(request))


@app.get("/teams")
async def teams() -> list[str]:
    return sorted(MOCK_SQUADS.keys())


@app.get("/venues")
async def venues() -> list[dict[str, Any]]:
    items = []
    for venue_key, stats in MOCK_VENUE_STATS.items():
        items.append(
            {
                "name": DISPLAY_VENUES.get(venue_key, venue_key.title()),
                "city": VENUE_CITIES.get(venue_key, "Unknown"),
                "sr_index": _venue_sr_index(venue_key, stats),
                "pitch_type": _pitch_type(stats),
            }
        )
    return items


@app.get("/health")
async def health() -> dict[str, Any]:
    try:
        graph_nodes = len(app_graph.get_graph().nodes)
    except Exception:
        graph_nodes = len(NODE_PROGRESS) + 3

    llm = get_llm()
    model_name = getattr(llm, "model_name", None) or getattr(llm, "model", "gpt-4o-mini")
    return {
        "status": "ok",
        "llm": model_name,
        "langsmith_enabled": bool(LANGCHAIN_API_KEY),
        "graph_nodes": graph_nodes,
    }


async def _analyze_stream_generator(request: AnalyzeRequest):
    initial_state = await build_initial_state(request)
    config = build_run_config(request.team1, request.team2, request.match_date, str(uuid.uuid4()))
    final_report: dict[str, Any] | None = None
    collected_errors: list[str] = []

    async for event in app_graph.astream_events(initial_state, config=config, version="v2"):
        node_name = _event_node_name(event)
        if event.get("event") != "on_chain_end" or not node_name:
            continue

        output = _to_payload((event.get("data", {}) or {}).get("output", {}))
        layer_name, progress = NODE_PROGRESS[node_name]
        for error in output.get("errors", []):
            if error not in collected_errors:
                collected_errors.append(error)

        if node_name == "coach":
            final_report = _to_payload(output.get("final_report", {}))
            yield {
                "event": "message",
                "data": json.dumps(
                    {
                        "layer": "complete",
                        "status": "done",
                        "report": final_report,
                        "errors": collected_errors,
                        "progress": 100,
                    }
                ),
            }
            return

        yield {
            "event": "message",
            "data": json.dumps(
                {
                    "layer": layer_name,
                    "status": "complete",
                    "summary": _node_summary(node_name, output),
                    "warnings": collected_errors,
                    "progress": progress,
                }
            ),
        }

    if final_report is None:
        yield {
            "event": "message",
            "data": json.dumps(
                {
                    "layer": "complete",
                    "status": "done",
                    "report": {"error": "Graph completed without a final report."},
                    "errors": collected_errors,
                    "progress": 100,
                }
            ),
        }
