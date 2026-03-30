from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from schemas.models import (
    BatterOutput,
    BowlerOutput,
    BowlingRotationOutput,
    EligibilityOutput,
    FinalReport,
    FormOutput,
    MatchupOutput,
    StrategyOutput,
    TossOutput,
    VenueOutput,
    XISelectionOutput,
)


class CricketState(TypedDict):
    # Inputs
    team1_name: str
    team2_name: str
    venue: str
    match_date: str
    team1_squad_raw: list[dict]
    team2_squad_raw: list[dict]

    # Layer 0
    eligibility: EligibilityOutput | None

    # Layer 1
    venue_stats: VenueOutput | None
    form: FormOutput | None
    batter_data: BatterOutput | None
    bowler_data: BowlerOutput | None

    # Layer 2
    matchups: MatchupOutput | None
    toss: TossOutput | None
    bowling_rotation: BowlingRotationOutput | None

    # Layer 2.5
    xi_selection: XISelectionOutput | None

    # Layer 3
    own_strategy: StrategyOutput | None
    opposition_strategy: StrategyOutput | None

    # Layer 4
    final_report: FinalReport | None

    # Meta
    errors: list[str]
    completed_layers: list[str]
    messages: Annotated[list, add_messages]
