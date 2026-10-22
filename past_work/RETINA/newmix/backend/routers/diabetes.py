"""Diabetes-module endpoints (Kartik's retinal vessel / fractal / HbA1c models)."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

import core
from services import diabetes_service as svc

router = APIRouter(prefix="/api/diabetes", tags=["diabetes"])
DISCLAIMER = ("Experimental research estimate. Not a diagnostic test; confirm with laboratory HbA1c "
              "and clinical assessment.")


async def _fundus(file: UploadFile):
    img = await core.read_image(file, "fundus photo")
    err = core.check_kind(img, "fundus")
    if err:
        raise HTTPException(400, err)
    return img


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """Runs every available diabetes-module analysis on one fundus photo."""
    img = await _fundus(file)
    st = svc.status()
    out: dict = {"success": True, "disclaimer": DISCLAIMER, "modules": {}, "skipped": {}}
    for name, ok, fn in (("vessels", st["vessels"], svc.vessels), ("fractal", st["vessels"], svc.fractal),
                         ("hba1c", st["hba1c"], svc.hba1c)):
        if not ok:
            out["skipped"][name] = st["errors"].get(name, "model not loaded")
            continue
        try:
            out["modules"][name] = fn(img)
        except (ValueError, RuntimeError) as e:
            out["skipped"][name] = str(e)
    if not out["modules"]:
        raise HTTPException(503, "no diabetes models are loaded; see /api/health")
    out["skipped"]["av_classification"] = st["av_note"]
    return out


@router.post("/vessels")
async def vessels(file: UploadFile = File(...)):
    return {"success": True, **svc.vessels(await _fundus(file))}


@router.post("/fractal")
async def fractal(file: UploadFile = File(...)):
    try:
        return {"success": True, **svc.fractal(await _fundus(file))}
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.post("/hba1c")
async def hba1c(file: UploadFile = File(...)):
    return {"success": True, "disclaimer": DISCLAIMER, **svc.hba1c(await _fundus(file))}
