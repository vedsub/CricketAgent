from __future__ import annotations

from typing import Any

from schemas.models import EligibilityOutput, PlayerProfile


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def infer_role(raw_role: Any, batting_style: str, bowling_style: str) -> str:
    role_text = normalize_text(raw_role).lower()
    batting = batting_style.lower()
    bowling = bowling_style.lower()

    if "keeper" in role_text or "wicket" in role_text:
        return "wicket-keeper"
    if "all" in role_text:
        return "all-rounder"
    if "bowl" in role_text:
        return "bowler"
    if "bat" in role_text:
        return "batter"

    has_bowling = bowling not in {"", "none", "n/a", "na"}
    has_batting = batting not in {"", "none", "n/a", "na"}
    if has_bowling and has_batting:
        return "all-rounder"
    if has_bowling:
        return "bowler"
    return "batter"


def coerce_player_profile(player: dict[str, Any]) -> PlayerProfile:
    name = normalize_text(
        player.get("name") or player.get("player_name") or player.get("player") or "Unknown Player"
    )
    batting_style = normalize_text(player.get("batting_style") or player.get("battingStyle") or "Unknown")
    bowling_style = normalize_text(player.get("bowling_style") or player.get("bowlingStyle") or "None")
    nationality = normalize_text(player.get("nationality") or player.get("country") or "India")
    role = infer_role(player.get("role"), batting_style, bowling_style)
    is_overseas = bool(player.get("is_overseas", nationality.lower() != "india"))

    return PlayerProfile(
        name=name,
        role=role,
        batting_style=batting_style,
        bowling_style=bowling_style,
        is_overseas=is_overseas,
        nationality=nationality,
    )


def get_validated_teams(state: dict[str, Any]) -> tuple[list[PlayerProfile], list[PlayerProfile]]:
    eligibility = state.get("eligibility")
    if isinstance(eligibility, EligibilityOutput):
        return eligibility.team1_validated, eligibility.team2_validated

    if isinstance(eligibility, dict):
        team1 = [PlayerProfile.model_validate(player) for player in eligibility.get("team1_validated", [])]
        team2 = [PlayerProfile.model_validate(player) for player in eligibility.get("team2_validated", [])]
        if team1 or team2:
            return team1, team2

    raw_team1 = [coerce_player_profile(player) for player in state.get("team1_squad_raw", [])]
    raw_team2 = [coerce_player_profile(player) for player in state.get("team2_squad_raw", [])]
    return raw_team1, raw_team2


def append_error(state: dict[str, Any], message: str) -> list[str]:
    errors = list(state.get("errors", []))
    errors.append(message)
    return errors


def to_payload(value: Any) -> Any:
    return value.model_dump() if hasattr(value, "model_dump") else value


def get_form_index_map(state: dict[str, Any]) -> dict[str, int]:
    form = to_payload(state.get("form") or {})
    mapping: dict[str, int] = {}
    for item in form.get("team1_form_rankings", []) + form.get("team2_form_rankings", []):
        name = normalize_text(item.get("name")).lower()
        if name:
            mapping[name] = int(item.get("form_index", 50))
    return mapping


def overseas_count(players: list[PlayerProfile]) -> int:
    return sum(player.is_overseas for player in players)


def message_content(messages: list[Any]) -> str:
    chunks: list[str] = []
    for message in messages:
        content = getattr(message, "content", message)
        if isinstance(content, str):
            chunks.append(content)
        elif isinstance(content, list):
            chunks.extend(str(item) for item in content)
        else:
            chunks.append(str(content))
    return "\n".join(chunk for chunk in chunks if chunk)
