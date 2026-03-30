from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from graph.graph import intelligence_graph
from schemas.models import AnalysisRequest, CricketIntelligenceResponse

app = FastAPI(title="Cricket Intelligence API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "cricket-intelligence",
        "message": "Cricket intelligence graph API is running.",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=CricketIntelligenceResponse)
async def analyze(request: AnalysisRequest) -> CricketIntelligenceResponse:
    result = intelligence_graph.invoke({"request": request.model_dump()})
    return CricketIntelligenceResponse.model_validate(result["final_response"])
