"""POST /api/glaucoma/compare: fundus-only vs OCT-only vs fusion on the same input."""

from __future__ import annotations

import logging
import time
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

import core
from services import compare_service

log = logging.getLogger("newmix.compare")
router = APIRouter(prefix="/api/glaucoma", tags=["glaucoma"])


@router.post("/compare")
async def compare(
    fundus: UploadFile = File(...),
    oct: Optional[UploadFile] = File(None),
    oct_slices: Optional[List[UploadFile]] = File(None),
    explain: bool = Form(False),
):
    fundus_img = await core.read_image(fundus, "fundus")
    oct_img = await core.read_image(oct, "oct") if oct is not None else None
    slices = None
    if oct_slices:
        slices = [await core.read_image(f, f"oct_slices[{i}]") for i, f in enumerate(oct_slices)]
    t0 = time.perf_counter()
    try:
        out = compare_service.run(fundus_img, oct_img, slices, explain=explain)
    except compare_service.ModelsNotReady as e:
        raise HTTPException(503, f"{e}; see /api/health")
    except ValueError as e:
        raise HTTPException(400, str(e))
    log.info("compare -> %s | %s (%.0f ms)", out["models"]["fusion"]["prediction"], out["agreement"]["banner"],
             (time.perf_counter() - t0) * 1000)
    return out
