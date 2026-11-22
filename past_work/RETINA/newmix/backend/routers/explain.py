"""POST /api/explain: plain-language explanation of a result (DeepSeek, template fallback)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import explain_service

router = APIRouter(prefix="/api", tags=["explain"])


class ExplainRequest(BaseModel):
    summary: dict


@router.post("/explain")
def explain(req: ExplainRequest):
    if not req.summary:
        raise HTTPException(422, "summary must not be empty")
    try:
        return explain_service.explain(req.summary)
    except explain_service.RateLimited:
        raise HTTPException(429, "too many explanation requests; wait a minute and try again")
