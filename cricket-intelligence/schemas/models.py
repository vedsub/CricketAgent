from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    opponent: str
    venue: str
    format: str = "T20"
    squad: list[str] = Field(default_factory=list)
    own_team: str = "Your Team"
    opposition_team: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class NodeSection(BaseModel):
    title: str
    summary: str
    key_points: list[str] = Field(default_factory=list)


class PlayingXIRecommendation(BaseModel):
    playing_xi: list[str] = Field(default_factory=list)
    bench: list[str] = Field(default_factory=list)
    rationale: str


class BowlingPlan(BaseModel):
    opening_pair: list[str] = Field(default_factory=list)
    middle_overs: list[str] = Field(default_factory=list)
    death_overs: list[str] = Field(default_factory=list)
    rationale: str


class TossPlan(BaseModel):
    decision_if_win_toss: str
    rationale: str


class CricketIntelligenceResponse(BaseModel):
    match_context: AnalysisRequest
    sections: list[NodeSection] = Field(default_factory=list)
    xi_selection: PlayingXIRecommendation
    bowling_rotation: BowlingPlan
    toss_plan: TossPlan
    coach_summary: str
