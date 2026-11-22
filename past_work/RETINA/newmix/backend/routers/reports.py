"""PDF reports: from a stored case (GET) or stateless from a fresh result (POST, nothing stored)."""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Response
from pydantic import Field

from routers.cases import CaseIn
from services import report_service, store

router = APIRouter(prefix="/api", tags=["reports"])


class ReportIn(CaseIn):
    probabilities: Optional[Dict[str, float]] = None
    flags: Optional[List[str]] = Field(None, max_length=10)
    fundus_heatmap: Optional[str] = Field(None, max_length=3_000_000)


def _pdf_response(pdf: bytes, patient_id: str, stamp: str) -> Response:
    day = (stamp or "")[:10] or "report"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="report-{patient_id}-{day}.pdf"'})


@router.get("/cases/{case_id}/report.pdf")
def case_report(case_id: int):
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(404, "case not found")
    return _pdf_response(report_service.build_pdf(case), case["patient_id"], case["created_at"])


@router.post("/report.pdf")
def stateless_report(body: ReportIn):
    heatmap = None
    if body.fundus_heatmap:
        try:
            heatmap = report_service.decode_heatmap(body.fundus_heatmap)
        except ValueError as e:
            raise HTTPException(422, str(e))
    data = body.model_dump(exclude={"fundus_heatmap"})
    data["detail"] = store.strip_images(data.get("detail") or {})
    return _pdf_response(report_service.build_pdf(data, heatmap), body.patient_id, store.now())
