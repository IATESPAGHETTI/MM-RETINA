"""Saved cases and patients (study IDs only; no images are ever stored)."""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from services import store

router = APIRouter(prefix="/api", tags=["cases"])


def study_id_or_422(value: str) -> str:
    if not store.valid_study_id(value):
        raise HTTPException(422, "study id must be letters, digits, '-' or '_' (1 to 32 characters, "
                                 "starting with a letter or digit); names are not accepted")
    return value


class CaseIn(BaseModel):
    patient_id: str
    module: Literal["glaucoma", "diabetes", "multimodal"]
    title: str = Field(min_length=1, max_length=120)
    result: str = Field(min_length=1, max_length=120)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    inputs: str = Field("", max_length=200)
    detail: Optional[dict] = None
    explanation: Optional[str] = Field(None, max_length=4000)

    @field_validator("patient_id")
    @classmethod
    def _study_id(cls, v: str) -> str:
        if not store.valid_study_id(v):
            raise ValueError("study id must be letters, digits, '-' or '_' (1 to 32 characters); names are not accepted")
        return v


@router.post("/cases", status_code=201)
def create_case(body: CaseIn):
    try:
        return store.create_case(body.patient_id, body.module, body.title, body.result, body.confidence,
                                 body.inputs, body.detail, body.explanation)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/cases")
def list_cases(patient_id: Optional[str] = None, q: Optional[str] = Query(None, max_length=80),
               module: Optional[Literal["glaucoma", "diabetes", "multimodal"]] = None,
               limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    if patient_id:
        study_id_or_422(patient_id)
    items, total = store.list_cases(patient_id, q, module, limit, offset)
    return {"items": items, "total": total}


@router.get("/cases/{case_id}")
def get_case(case_id: int):
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(404, "case not found")
    return case


@router.delete("/cases/{case_id}")
def delete_case(case_id: int):
    if not store.delete_case(case_id):
        raise HTTPException(404, "case not found")
    return {"deleted": case_id}


@router.get("/patients")
def list_patients(q: Optional[str] = Query(None, max_length=32)):
    return store.list_patients(q)


@router.get("/patients/{study_id}")
def get_patient(study_id: str):
    patient = store.get_patient(study_id_or_422(study_id))
    if not patient:
        raise HTTPException(404, "patient not found")
    return patient


@router.delete("/patients/{study_id}")
def delete_patient(study_id: str):
    n = store.delete_patient(study_id_or_422(study_id))
    if n is None:
        raise HTTPException(404, "patient not found")
    return {"deleted": study_id, "cases_deleted": n}
