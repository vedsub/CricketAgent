from __future__ import annotations

import logging
import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CRICAPI_KEY = os.getenv("CRICAPI_KEY", "")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "cricket-intelligence"

if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
if LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is required to start cricket-intelligence. "
        "Add it to your environment or .env file before running the app."
    )

if not CRICAPI_KEY:
    logging.warning("CRICAPI_KEY is not configured. The project will use mock cricket data.")


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


__all__ = [
    "OPENAI_API_KEY",
    "CRICAPI_KEY",
    "LANGCHAIN_API_KEY",
    "get_llm",
]
