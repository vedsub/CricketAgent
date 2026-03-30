from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PlayerProfile(BaseModel):
    name: str
    role: Literal["batter", "bowler", "all-rounder", "wicket-keeper"]
    batting_style: str
    bowling_style: str
    is_overseas: bool
    nationality: str


class EligibilityOutput(BaseModel):
    team1_validated: list[PlayerProfile]
    team2_validated: list[PlayerProfile]
    overseas_count: dict[str, int]
    flagged_issues: list[str]


class VenueOutput(BaseModel):
    venue_name: str
    pitch_type: Literal["pace", "spin", "balanced"]
    avg_first_innings_score: int
    avg_powerplay_score: int
    pace_wicket_pct: float
    spin_wicket_pct: float
    venue_sr_index: float
    toss_recommendation: Literal["bat", "bowl"]


class FormOutput(BaseModel):
    team1_form_rankings: list[dict[str, Any]]
    team2_form_rankings: list[dict[str, Any]]
    in_form_players: list[str]
    out_of_form_players: list[str]


class BatterProfile(BaseModel):
    name: str
    venue_sr: float
    is_type_vulnerable: bool
    vulnerability_type: str | None
    recent_avg: float


class BatterOutput(BaseModel):
    batters_profiled: int
    type_vulnerable: list[str]
    high_venue_sr: list[str]
    batter_profiles: dict[str, BatterProfile]


class BowlerProfile(BaseModel):
    name: str
    bowling_type: str
    economy: float
    wickets_per_match: float
    best_phase: Literal["powerplay", "middle", "death"]


class BowlerOutput(BaseModel):
    bowler_profiles: dict[str, BowlerProfile]
    powerplay_specialists: list[str]
    death_specialists: list[str]
    middle_over_specialists: list[str]


class Matchup(BaseModel):
    batter: str
    bowler: str
    balls: int
    runs: int
    wickets: int
    strike_rate: float
    matchup_type: Literal["danger", "exploit", "neutral"]


class MatchupOutput(BaseModel):
    total_h2h: int
    danger_matchups: list[Matchup]
    exploit_matchups: list[Matchup]
    type_matchups: list[dict[str, Any]]
    bowl_hand_insights: list[str]


class TossOutput(BaseModel):
    decision: Literal["bat", "bowl"]
    confidence: float
    reasoning: str


class BowlingRotationOutput(BaseModel):
    powerplay_bowlers: list[str]
    middle_bowlers: list[str]
    death_bowlers: list[str]
    over_plan: dict[str, str]


class XIPlayer(BaseModel):
    name: str
    role: str
    batting_position: int
    reason: str


class XISelectionOutput(BaseModel):
    team1_xi: list[XIPlayer]
    team2_xi: list[XIPlayer]
    team1_impact_player: dict[str, Any]
    team2_impact_player: dict[str, Any]
    selection_notes: list[str]


class StrategyOutput(BaseModel):
    powerplay_target: int
    middle_overs_plan: str
    death_overs_plan: str
    key_partnerships: list[str]
    bowling_plan: str
    restriction_plan: str
    key_threats: list[str]


class FinalReport(BaseModel):
    match: str
    date: str
    venue: str
    pitch_type: str
    dom_type: str
    batting_summary: str
    bowling_summary: str
    form_summary: str
    key_battlegrounds: list[str]
    toss_recommendation: TossOutput
    team1_playing_xi: list[XIPlayer]
    team2_playing_xi: list[XIPlayer]
    team1_impact_player: dict[str, Any] = Field(default_factory=dict)
    team2_impact_player: dict[str, Any] = Field(default_factory=dict)
    team1_bowling_plan: dict[str, Any]
    team2_bowling_plan: dict[str, Any]
    first_innings_target: int
    key_matchups: list[Matchup]
    confidence_score: float


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
