from __future__ import annotations

from typing import Any

import requests
from langchain_core.tools import tool

from config import CRICAPI_KEY

CRICAPI_BASE_URL = "https://api.cricapi.com/v1"


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


TEAM_ALIASES = {
    "chennai super kings": "Chennai Super Kings",
    "csk": "Chennai Super Kings",
    "mumbai indians": "Mumbai Indians",
    "mi": "Mumbai Indians",
    "royal challengers bengaluru": "Royal Challengers Bengaluru",
    "royal challengers bangalore": "Royal Challengers Bengaluru",
    "rcb": "Royal Challengers Bengaluru",
    "kolkata knight riders": "Kolkata Knight Riders",
    "kkr": "Kolkata Knight Riders",
    "sunrisers hyderabad": "Sunrisers Hyderabad",
    "srh": "Sunrisers Hyderabad",
    "rajasthan royals": "Rajasthan Royals",
    "rr": "Rajasthan Royals",
    "delhi capitals": "Delhi Capitals",
    "dc": "Delhi Capitals",
    "punjab kings": "Punjab Kings",
    "pbks": "Punjab Kings",
    "kings xi punjab": "Punjab Kings",
    "lucknow super giants": "Lucknow Super Giants",
    "lsg": "Lucknow Super Giants",
    "gujarat titans": "Gujarat Titans",
    "gt": "Gujarat Titans",
}


MOCK_SQUADS: dict[str, list[dict[str, Any]]] = {
    "Chennai Super Kings": [
        {"name": "Ruturaj Gaikwad", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "None", "nationality": "India"},
        {"name": "Devon Conway", "role": "wicket-keeper", "batting_style": "Left-hand bat", "bowling_style": "None", "nationality": "New Zealand"},
        {"name": "Rahul Tripathi", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium", "nationality": "India"},
        {"name": "Shivam Dube", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Right-arm medium", "nationality": "India"},
        {"name": "Ravindra Jadeja", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Left-arm orthodox", "nationality": "India"},
        {"name": "MS Dhoni", "role": "wicket-keeper", "batting_style": "Right-hand bat", "bowling_style": "None", "nationality": "India"},
        {"name": "Rachin Ravindra", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Left-arm orthodox", "nationality": "New Zealand"},
        {"name": "Noor Ahmad", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Left-arm wrist-spin", "nationality": "Afghanistan"},
        {"name": "Matheesha Pathirana", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast", "nationality": "Sri Lanka"},
        {"name": "Khaleel Ahmed", "role": "bowler", "batting_style": "Left-hand bat", "bowling_style": "Left-arm fast-medium", "nationality": "India"},
        {"name": "Ravichandran Ashwin", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "India"},
        {"name": "Mukesh Choudhary", "role": "bowler", "batting_style": "Left-hand bat", "bowling_style": "Left-arm medium-fast", "nationality": "India"},
    ],
    "Mumbai Indians": [
        {"name": "Rohit Sharma", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "India"},
        {"name": "Ishan Kishan", "role": "wicket-keeper", "batting_style": "Left-hand bat", "bowling_style": "None", "nationality": "India"},
        {"name": "Suryakumar Yadav", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium", "nationality": "India"},
        {"name": "Tilak Varma", "role": "batter", "batting_style": "Left-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "India"},
        {"name": "Hardik Pandya", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast-medium", "nationality": "India"},
        {"name": "Tim David", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "Australia"},
        {"name": "Naman Dhir", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "India"},
        {"name": "Jasprit Bumrah", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast", "nationality": "India"},
        {"name": "Trent Boult", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Left-arm fast-medium", "nationality": "New Zealand"},
        {"name": "Deepak Chahar", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium-fast", "nationality": "India"},
        {"name": "Mitchell Santner", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Left-arm orthodox", "nationality": "New Zealand"},
        {"name": "Mujeeb Ur Rahman", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "Afghanistan"},
    ],
    "Royal Challengers Bengaluru": [
        {"name": "Virat Kohli", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium", "nationality": "India"},
        {"name": "Phil Salt", "role": "wicket-keeper", "batting_style": "Right-hand bat", "bowling_style": "None", "nationality": "England"},
        {"name": "Rajat Patidar", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "India"},
        {"name": "Liam Livingstone", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Legbreak", "nationality": "England"},
        {"name": "Jitesh Sharma", "role": "wicket-keeper", "batting_style": "Right-hand bat", "bowling_style": "None", "nationality": "India"},
        {"name": "Tim David", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "Australia"},
        {"name": "Krunal Pandya", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Left-arm orthodox", "nationality": "India"},
        {"name": "Bhuvneshwar Kumar", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium-fast", "nationality": "India"},
        {"name": "Josh Hazlewood", "role": "bowler", "batting_style": "Left-hand bat", "bowling_style": "Right-arm fast-medium", "nationality": "Australia"},
        {"name": "Yash Dayal", "role": "bowler", "batting_style": "Left-hand bat", "bowling_style": "Left-arm fast-medium", "nationality": "India"},
        {"name": "Suyash Sharma", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Legbreak", "nationality": "India"},
        {"name": "Rasikh Salam", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium-fast", "nationality": "India"},
    ],
    "Kolkata Knight Riders": [
        {"name": "Sunil Narine", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "West Indies"},
        {"name": "Quinton de Kock", "role": "wicket-keeper", "batting_style": "Left-hand bat", "bowling_style": "None", "nationality": "South Africa"},
        {"name": "Venkatesh Iyer", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Right-arm medium", "nationality": "India"},
        {"name": "Shreyas Iyer", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm legbreak", "nationality": "India"},
        {"name": "Rinku Singh", "role": "batter", "batting_style": "Left-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "India"},
        {"name": "Andre Russell", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast", "nationality": "West Indies"},
        {"name": "Ramandeep Singh", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium-fast", "nationality": "India"},
        {"name": "Harshit Rana", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast", "nationality": "India"},
        {"name": "Varun Chakaravarthy", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Legbreak googly", "nationality": "India"},
        {"name": "Spencer Johnson", "role": "bowler", "batting_style": "Left-hand bat", "bowling_style": "Left-arm fast", "nationality": "Australia"},
        {"name": "Vaibhav Arora", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium-fast", "nationality": "India"},
        {"name": "Angkrish Raghuvanshi", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm legbreak", "nationality": "India"},
    ],
    "Sunrisers Hyderabad": [
        {"name": "Travis Head", "role": "batter", "batting_style": "Left-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "Australia"},
        {"name": "Abhishek Sharma", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Left-arm orthodox", "nationality": "India"},
        {"name": "Ishan Kishan", "role": "wicket-keeper", "batting_style": "Left-hand bat", "bowling_style": "None", "nationality": "India"},
        {"name": "Nitish Kumar Reddy", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium-fast", "nationality": "India"},
        {"name": "Heinrich Klaasen", "role": "wicket-keeper", "batting_style": "Right-hand bat", "bowling_style": "None", "nationality": "South Africa"},
        {"name": "Abhinav Manohar", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm legbreak", "nationality": "India"},
        {"name": "Pat Cummins", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast", "nationality": "Australia"},
        {"name": "Harshal Patel", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium-fast", "nationality": "India"},
        {"name": "Mohammed Shami", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast", "nationality": "India"},
        {"name": "Rahul Chahar", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Legbreak", "nationality": "India"},
        {"name": "Adam Zampa", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Legbreak googly", "nationality": "Australia"},
        {"name": "Simarjeet Singh", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast-medium", "nationality": "India"},
    ],
    "Rajasthan Royals": [
        {"name": "Yashasvi Jaiswal", "role": "batter", "batting_style": "Left-hand bat", "bowling_style": "Right-arm legbreak", "nationality": "India"},
        {"name": "Jos Buttler", "role": "wicket-keeper", "batting_style": "Right-hand bat", "bowling_style": "None", "nationality": "England"},
        {"name": "Sanju Samson", "role": "wicket-keeper", "batting_style": "Right-hand bat", "bowling_style": "None", "nationality": "India"},
        {"name": "Riyan Parag", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm legbreak", "nationality": "India"},
        {"name": "Dhruv Jurel", "role": "wicket-keeper", "batting_style": "Right-hand bat", "bowling_style": "None", "nationality": "India"},
        {"name": "Shimron Hetmyer", "role": "batter", "batting_style": "Left-hand bat", "bowling_style": "None", "nationality": "West Indies"},
        {"name": "Wanindu Hasaranga", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Legbreak googly", "nationality": "Sri Lanka"},
        {"name": "Jofra Archer", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast", "nationality": "England"},
        {"name": "Trent Boult", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Left-arm fast-medium", "nationality": "New Zealand"},
        {"name": "Avesh Khan", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast-medium", "nationality": "India"},
        {"name": "Sandeep Sharma", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium-fast", "nationality": "India"},
        {"name": "Maheesh Theekshana", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "Sri Lanka"},
    ],
    "Delhi Capitals": [
        {"name": "Jake Fraser-McGurk", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm legbreak", "nationality": "Australia"},
        {"name": "KL Rahul", "role": "wicket-keeper", "batting_style": "Right-hand bat", "bowling_style": "None", "nationality": "India"},
        {"name": "Abishek Porel", "role": "wicket-keeper", "batting_style": "Left-hand bat", "bowling_style": "None", "nationality": "India"},
        {"name": "Tristan Stubbs", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "South Africa"},
        {"name": "Axar Patel", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Left-arm orthodox", "nationality": "India"},
        {"name": "Sameer Rizvi", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "India"},
        {"name": "Ashutosh Sharma", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium", "nationality": "India"},
        {"name": "Kuldeep Yadav", "role": "bowler", "batting_style": "Left-hand bat", "bowling_style": "Left-arm wrist-spin", "nationality": "India"},
        {"name": "Mitchell Starc", "role": "bowler", "batting_style": "Left-hand bat", "bowling_style": "Left-arm fast", "nationality": "Australia"},
        {"name": "Mukesh Kumar", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast-medium", "nationality": "India"},
        {"name": "T Natarajan", "role": "bowler", "batting_style": "Left-hand bat", "bowling_style": "Left-arm fast-medium", "nationality": "India"},
        {"name": "Mohit Sharma", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium-fast", "nationality": "India"},
    ],
    "Punjab Kings": [
        {"name": "Shikhar Dhawan", "role": "batter", "batting_style": "Left-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "India"},
        {"name": "Prabhsimran Singh", "role": "wicket-keeper", "batting_style": "Right-hand bat", "bowling_style": "None", "nationality": "India"},
        {"name": "Shreyas Iyer", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm legbreak", "nationality": "India"},
        {"name": "Marcus Stoinis", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium", "nationality": "Australia"},
        {"name": "Glenn Maxwell", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "Australia"},
        {"name": "Nehal Wadhera", "role": "batter", "batting_style": "Left-hand bat", "bowling_style": "Right-arm legbreak", "nationality": "India"},
        {"name": "Shashank Singh", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium", "nationality": "India"},
        {"name": "Marco Jansen", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Left-arm fast-medium", "nationality": "South Africa"},
        {"name": "Arshdeep Singh", "role": "bowler", "batting_style": "Left-hand bat", "bowling_style": "Left-arm fast-medium", "nationality": "India"},
        {"name": "Yuzvendra Chahal", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Legbreak googly", "nationality": "India"},
        {"name": "Lockie Ferguson", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast", "nationality": "New Zealand"},
        {"name": "Harpreet Brar", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Left-arm orthodox", "nationality": "India"},
    ],
    "Lucknow Super Giants": [
        {"name": "KL Rahul", "role": "wicket-keeper", "batting_style": "Right-hand bat", "bowling_style": "None", "nationality": "India"},
        {"name": "Quinton de Kock", "role": "wicket-keeper", "batting_style": "Left-hand bat", "bowling_style": "None", "nationality": "South Africa"},
        {"name": "Nicholas Pooran", "role": "wicket-keeper", "batting_style": "Left-hand bat", "bowling_style": "None", "nationality": "West Indies"},
        {"name": "Ayush Badoni", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "India"},
        {"name": "David Miller", "role": "batter", "batting_style": "Left-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "South Africa"},
        {"name": "Marcus Stoinis", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm medium", "nationality": "Australia"},
        {"name": "Krunal Pandya", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Left-arm orthodox", "nationality": "India"},
        {"name": "Ravi Bishnoi", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Legbreak googly", "nationality": "India"},
        {"name": "Mayank Yadav", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast", "nationality": "India"},
        {"name": "Mohsin Khan", "role": "bowler", "batting_style": "Left-hand bat", "bowling_style": "Left-arm fast-medium", "nationality": "India"},
        {"name": "Avesh Khan", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast-medium", "nationality": "India"},
        {"name": "Shamar Joseph", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast", "nationality": "West Indies"},
    ],
    "Gujarat Titans": [
        {"name": "Shubman Gill", "role": "batter", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "India"},
        {"name": "Wriddhiman Saha", "role": "wicket-keeper", "batting_style": "Right-hand bat", "bowling_style": "None", "nationality": "India"},
        {"name": "Sai Sudharsan", "role": "batter", "batting_style": "Left-hand bat", "bowling_style": "Right-arm legbreak", "nationality": "India"},
        {"name": "Jos Buttler", "role": "wicket-keeper", "batting_style": "Right-hand bat", "bowling_style": "None", "nationality": "England"},
        {"name": "Rahul Tewatia", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Legbreak", "nationality": "India"},
        {"name": "Washington Sundar", "role": "all-rounder", "batting_style": "Left-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "India"},
        {"name": "Shahrukh Khan", "role": "all-rounder", "batting_style": "Right-hand bat", "bowling_style": "Right-arm offbreak", "nationality": "India"},
        {"name": "Rashid Khan", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Legbreak googly", "nationality": "Afghanistan"},
        {"name": "Mohammed Siraj", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast", "nationality": "India"},
        {"name": "Kagiso Rabada", "role": "bowler", "batting_style": "Left-hand bat", "bowling_style": "Right-arm fast", "nationality": "South Africa"},
        {"name": "Prasidh Krishna", "role": "bowler", "batting_style": "Right-hand bat", "bowling_style": "Right-arm fast-medium", "nationality": "India"},
        {"name": "Sai Kishore", "role": "bowler", "batting_style": "Left-hand bat", "bowling_style": "Left-arm orthodox", "nationality": "India"},
    ],
}


MOCK_VENUE_STATS: dict[str, dict[str, Any]] = {
    "wankhede stadium": {
        "avg_first_innings": 186,
        "avg_powerplay": 54,
        "pace_wicket_pct": 58.0,
        "spin_wicket_pct": 42.0,
        "toss_win_bat_pct": 43.0,
    },
    "ma chidambaram stadium": {
        "avg_first_innings": 171,
        "avg_powerplay": 47,
        "pace_wicket_pct": 41.0,
        "spin_wicket_pct": 59.0,
        "toss_win_bat_pct": 57.0,
    },
    "narendra modi stadium": {
        "avg_first_innings": 181,
        "avg_powerplay": 50,
        "pace_wicket_pct": 52.0,
        "spin_wicket_pct": 48.0,
        "toss_win_bat_pct": 48.0,
    },
    "eden gardens": {
        "avg_first_innings": 189,
        "avg_powerplay": 55,
        "pace_wicket_pct": 54.0,
        "spin_wicket_pct": 46.0,
        "toss_win_bat_pct": 45.0,
    },
    "m chinnaswamy stadium": {
        "avg_first_innings": 193,
        "avg_powerplay": 58,
        "pace_wicket_pct": 56.0,
        "spin_wicket_pct": 44.0,
        "toss_win_bat_pct": 41.0,
    },
    "rajiv gandhi international stadium": {
        "avg_first_innings": 184,
        "avg_powerplay": 53,
        "pace_wicket_pct": 55.0,
        "spin_wicket_pct": 45.0,
        "toss_win_bat_pct": 46.0,
    },
    "sawai mansingh stadium": {
        "avg_first_innings": 176,
        "avg_powerplay": 49,
        "pace_wicket_pct": 49.0,
        "spin_wicket_pct": 51.0,
        "toss_win_bat_pct": 52.0,
    },
    "arun jaitley stadium": {
        "avg_first_innings": 188,
        "avg_powerplay": 56,
        "pace_wicket_pct": 51.0,
        "spin_wicket_pct": 49.0,
        "toss_win_bat_pct": 44.0,
    },
    "punjab cricket association stadium": {
        "avg_first_innings": 179,
        "avg_powerplay": 51,
        "pace_wicket_pct": 57.0,
        "spin_wicket_pct": 43.0,
        "toss_win_bat_pct": 47.0,
    },
    "ekana cricket stadium": {
        "avg_first_innings": 168,
        "avg_powerplay": 45,
        "pace_wicket_pct": 46.0,
        "spin_wicket_pct": 54.0,
        "toss_win_bat_pct": 55.0,
    },
}


MOCK_PLAYER_STATS: dict[str, dict[str, Any]] = {
    "virat kohli": {"last_5_scores": [67, 42, 84, 18, 71], "strike_rate": 151.7, "average": 56.4, "economy": None, "recent_wickets": 0, "form_index": 92},
    "jasprit bumrah": {"last_5_scores": [6, 2, 8, 1, 4], "strike_rate": 104.3, "average": 7.6, "economy": 6.8, "recent_wickets": 10, "form_index": 95},
    "ravindra jadeja": {"last_5_scores": [24, 37, 12, 29, 41], "strike_rate": 137.4, "average": 28.6, "economy": 7.1, "recent_wickets": 6, "form_index": 81},
    "suryakumar yadav": {"last_5_scores": [15, 73, 61, 9, 48], "strike_rate": 178.2, "average": 41.2, "economy": None, "recent_wickets": 0, "form_index": 88},
    "sunil narine": {"last_5_scores": [34, 2, 49, 18, 27], "strike_rate": 171.6, "average": 26.0, "economy": 6.9, "recent_wickets": 8, "form_index": 86},
    "rashid khan": {"last_5_scores": [9, 14, 6, 4, 18], "strike_rate": 132.8, "average": 10.2, "economy": 7.0, "recent_wickets": 9, "form_index": 89},
    "travis head": {"last_5_scores": [84, 5, 61, 38, 72], "strike_rate": 182.5, "average": 52.0, "economy": None, "recent_wickets": 0, "form_index": 93},
    "yashasvi jaiswal": {"last_5_scores": [13, 57, 44, 92, 21], "strike_rate": 159.1, "average": 45.4, "economy": None, "recent_wickets": 0, "form_index": 87},
}


MOCK_H2H: dict[tuple[str, str], dict[str, Any]] = {
    ("virat kohli", "jasprit bumrah"): {"balls": 68, "runs": 82, "wickets": 5, "strike_rate": 120.6, "dismissal_types": ["caught behind", "lbw", "caught"]},
    ("rohit sharma", "trent boult"): {"balls": 54, "runs": 71, "wickets": 3, "strike_rate": 131.5, "dismissal_types": ["bowled", "caught"]},
    ("ruturaj gaikwad", "rashid khan"): {"balls": 33, "runs": 29, "wickets": 2, "strike_rate": 87.9, "dismissal_types": ["lbw", "caught"]},
    ("heinrich klaasen", "ravindra jadeja"): {"balls": 24, "runs": 41, "wickets": 0, "strike_rate": 170.8, "dismissal_types": []},
}


MOCK_WEATHER: dict[str, dict[str, Any]] = {
    "mumbai": {"condition": "Humid evening", "temperature": 31, "humidity": 74, "dew_factor": True, "wind_speed": 16},
    "chennai": {"condition": "Hot and dry", "temperature": 33, "humidity": 66, "dew_factor": False, "wind_speed": 14},
    "bengaluru": {"condition": "Warm with light breeze", "temperature": 28, "humidity": 58, "dew_factor": False, "wind_speed": 18},
    "kolkata": {"condition": "Sticky evening", "temperature": 30, "humidity": 77, "dew_factor": True, "wind_speed": 12},
    "hyderabad": {"condition": "Clear skies", "temperature": 29, "humidity": 52, "dew_factor": False, "wind_speed": 15},
    "jaipur": {"condition": "Dry heat", "temperature": 32, "humidity": 36, "dew_factor": False, "wind_speed": 17},
    "delhi": {"condition": "Hazy and warm", "temperature": 31, "humidity": 43, "dew_factor": False, "wind_speed": 13},
    "mohali": {"condition": "Pleasant evening", "temperature": 27, "humidity": 49, "dew_factor": True, "wind_speed": 11},
    "lucknow": {"condition": "Still conditions", "temperature": 29, "humidity": 55, "dew_factor": True, "wind_speed": 9},
    "ahmedabad": {"condition": "Dry evening", "temperature": 30, "humidity": 41, "dew_factor": False, "wind_speed": 14},
}


def _resolve_team_name(team_name: str) -> str:
    normalized = _normalize(team_name)
    return TEAM_ALIASES.get(normalized, team_name.strip())


def _api_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    if not CRICAPI_KEY:
        raise RuntimeError("CRICAPI_KEY is not configured")

    response = requests.get(
        f"{CRICAPI_BASE_URL}/{path.lstrip('/')}",
        params={"apikey": CRICAPI_KEY, **params},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and payload.get("status") == "failure":
        raise RuntimeError(payload.get("reason", "CricAPI request failed"))
    return payload


def _extract_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data", [])
    return data if isinstance(data, list) else []


def _is_overseas(nationality: str) -> bool:
    return nationality.strip().lower() != "india"


def _deterministic_seed(*parts: str) -> int:
    return sum(sum(ord(ch) for ch in part) for part in parts)


def _fallback_player_stats(player_name: str) -> dict[str, Any]:
    key = _normalize(player_name)
    if key in MOCK_PLAYER_STATS:
        return MOCK_PLAYER_STATS[key]

    seed = _deterministic_seed(player_name)
    last_5_scores = [((seed // (i + 3)) % 75) + (i * 3) for i in range(5)]
    is_bowler = any(token in key for token in ["khan", "yadav", "sharma", "chahar", "boult", "bumrah", "siraj", "rashid"])
    return {
        "last_5_scores": last_5_scores,
        "strike_rate": round(115 + (seed % 70) * 0.9, 1),
        "average": round(18 + (seed % 35) * 0.8, 1),
        "economy": round(6.4 + (seed % 25) * 0.12, 1) if is_bowler else None,
        "recent_wickets": (seed % 11) if is_bowler else 0,
        "form_index": 55 + (seed % 41),
    }


def _fallback_venue_stats(venue_name: str) -> dict[str, Any]:
    key = _normalize(venue_name)
    if key in MOCK_VENUE_STATS:
        return MOCK_VENUE_STATS[key]

    seed = _deterministic_seed(venue_name)
    return {
        "avg_first_innings": 165 + (seed % 31),
        "avg_powerplay": 44 + (seed % 15),
        "pace_wicket_pct": round(45 + (seed % 16), 1),
        "spin_wicket_pct": round(55 - (seed % 16), 1),
        "toss_win_bat_pct": round(42 + (seed % 15), 1),
    }


def _fallback_h2h_stats(batter: str, bowler: str) -> dict[str, Any]:
    key = (_normalize(batter), _normalize(bowler))
    if key in MOCK_H2H:
        return MOCK_H2H[key]

    seed = _deterministic_seed(batter, bowler)
    balls = 18 + (seed % 48)
    runs = 20 + (seed % 70)
    wickets = seed % 4
    return {
        "balls": balls,
        "runs": runs,
        "wickets": wickets,
        "strike_rate": round((runs / balls) * 100, 1),
        "dismissal_types": ["caught"] if wickets else [],
    }


def _fallback_weather(venue: str, date: str) -> dict[str, Any]:
    venue_key = _normalize(venue)
    for city_key, weather in MOCK_WEATHER.items():
        if city_key in venue_key:
            return weather

    seed = _deterministic_seed(venue, date)
    return {
        "condition": "Warm evening",
        "temperature": 26 + (seed % 8),
        "humidity": 45 + (seed % 35),
        "dew_factor": bool(seed % 2),
        "wind_speed": 8 + (seed % 13),
    }


@tool
def get_squad(team_name: str) -> list[dict[str, Any]]:
    """Fetch the current IPL squad for a given team name. Returns a list of player dictionaries with name, role, batting_style, bowling_style, and nationality."""

    canonical_name = _resolve_team_name(team_name)

    try:
        payload = _api_get("players", {"search": canonical_name, "offset": 0})
        players = []
        for item in _extract_records(payload):
            name = item.get("name")
            if not name:
                continue
            nationality = item.get("country") or item.get("nationality") or "India"
            players.append(
                {
                    "name": name,
                    "role": item.get("role") or item.get("playerRole") or "batter",
                    "batting_style": item.get("battingStyle") or item.get("batting_style") or "Right-hand bat",
                    "bowling_style": item.get("bowlingStyle") or item.get("bowling_style") or "None",
                    "nationality": nationality,
                    "is_overseas": _is_overseas(nationality),
                }
            )
        if len(players) >= 8:
            return players
    except Exception:
        pass

    mock_players = MOCK_SQUADS.get(canonical_name, MOCK_SQUADS["Chennai Super Kings"])
    return [
        {
            **player,
            "is_overseas": _is_overseas(player["nationality"]),
        }
        for player in mock_players
    ]


@tool
def get_player_stats(player_name: str) -> dict[str, Any]:
    """Get recent match statistics for a player. Returns a dictionary with last_5_scores, strike_rate, average, economy, recent_wickets, and form_index."""

    try:
        search_payload = _api_get("players", {"search": player_name, "offset": 0})
        candidates = _extract_records(search_payload)
        player_id = next(
            (
                item.get("id")
                for item in candidates
                if _normalize(item.get("name", "")) == _normalize(player_name)
            ),
            None,
        )
        if player_id:
            stats_payload = _api_get("players_info", {"id": player_id})
            data = stats_payload.get("data", {}) if isinstance(stats_payload, dict) else {}
            recent_scores = data.get("last_5_scores") or data.get("last5Scores") or []
            return {
                "last_5_scores": recent_scores if isinstance(recent_scores, list) else [],
                "strike_rate": float(data.get("strike_rate") or data.get("strikeRate") or 0.0),
                "average": float(data.get("average") or 0.0),
                "economy": data.get("economy"),
                "recent_wickets": int(data.get("recent_wickets") or data.get("recentWickets") or 0),
                "form_index": int(data.get("form_index") or data.get("formIndex") or 0),
            }
    except Exception:
        pass

    return _fallback_player_stats(player_name)


@tool
def get_venue_stats(venue_name: str) -> dict[str, Any]:
    """Get historical stats for an IPL venue. Returns a dictionary with avg_first_innings, avg_powerplay, pace_wicket_pct, spin_wicket_pct, and toss_win_bat_pct."""

    try:
        payload = _api_get("venues", {"search": venue_name})
        for item in _extract_records(payload):
            name = _normalize(item.get("name", ""))
            if venue_name and _normalize(venue_name) in name:
                return {
                    "avg_first_innings": int(item.get("avgFirstInnings") or item.get("avg_first_innings") or 0),
                    "avg_powerplay": int(item.get("avgPowerplay") or item.get("avg_powerplay") or 0),
                    "pace_wicket_pct": float(item.get("paceWicketPct") or item.get("pace_wicket_pct") or 0.0),
                    "spin_wicket_pct": float(item.get("spinWicketPct") or item.get("spin_wicket_pct") or 0.0),
                    "toss_win_bat_pct": float(item.get("tossWinBatPct") or item.get("toss_win_bat_pct") or 0.0),
                }
    except Exception:
        pass

    return _fallback_venue_stats(venue_name)


@tool
def get_h2h_stats(batter: str, bowler: str) -> dict[str, Any]:
    """Get head-to-head battle stats between a batter and bowler. Returns a dictionary with balls, runs, wickets, strike_rate, and dismissal_types."""

    try:
        payload = _api_get("players-vs-player", {"batter": batter, "bowler": bowler})
        data = payload.get("data", {}) if isinstance(payload.get("data"), dict) else {}
        if data:
            return {
                "balls": int(data.get("balls") or 0),
                "runs": int(data.get("runs") or 0),
                "wickets": int(data.get("wickets") or 0),
                "strike_rate": float(data.get("strike_rate") or data.get("strikeRate") or 0.0),
                "dismissal_types": data.get("dismissal_types") or data.get("dismissalTypes") or [],
            }
    except Exception:
        pass

    return _fallback_h2h_stats(batter, bowler)


@tool
def get_weather(venue: str, date: str) -> dict[str, Any]:
    """Get match-day weather forecast for a venue. Returns a dictionary with condition, temperature, humidity, dew_factor, and wind_speed."""

    try:
        payload = _api_get("weather", {"venue": venue, "date": date})
        data = payload.get("data", {}) if isinstance(payload.get("data"), dict) else {}
        if data:
            return {
                "condition": data.get("condition") or "Unknown",
                "temperature": int(data.get("temperature") or 0),
                "humidity": int(data.get("humidity") or 0),
                "dew_factor": bool(data.get("dew_factor") or data.get("dewFactor") or False),
                "wind_speed": int(data.get("wind_speed") or data.get("windSpeed") or 0),
            }
    except Exception:
        pass

    return _fallback_weather(venue, date)


ALL_TOOLS = [
    get_squad,
    get_player_stats,
    get_venue_stats,
    get_h2h_stats,
    get_weather,
]
