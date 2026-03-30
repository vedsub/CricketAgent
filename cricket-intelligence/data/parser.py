from __future__ import annotations

from typing import Any


def extract_data_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the common list payload used by many cricket APIs."""

    data = payload.get("data", [])
    return data if isinstance(data, list) else []


def summarize_matches(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize current-match payloads into a compact summary structure."""

    matches = []
    for item in extract_data_payload(payload):
        matches.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "status": item.get("status"),
                "venue": item.get("venue"),
                "date": item.get("date"),
            }
        )
    return matches


def normalize_player_info(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract the most useful player fields into a predictable shape."""

    data = payload.get("data", {}) if isinstance(payload.get("data"), dict) else {}
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "country": data.get("country"),
        "role": data.get("role"),
        "batting_style": data.get("battingStyle"),
        "bowling_style": data.get("bowlingStyle"),
    }
