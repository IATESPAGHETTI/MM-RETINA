"""Glaucoma endpoints: OCT B-scan model, clinical-feature model, fused assessment,
and the GAMMA multimodal demo."""

from __future__ import annotations

import json
import logging
import time
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile

import core
from services import clinical_service, defer_service, gamma_service, oct_service

log = logging.getLogger("newmix.glaucoma")
router = APIRouter(prefix="/api/glaucoma", tags=["glaucoma"])

GAMMA_MODALITIES = {"fundus", "oct", "fusion"}
DISCLAIMER = ("Research prototype for decision support. It is not a medical device and does not "
              "replace an ophthalmologist's examination.")


def _fusion_weights() -> dict:
    m = core.read_json(core.RESULTS_DIR / "fusion" / "metrics.json", {})
    return m.get("weights", {"oct": 0.5, "clinical": 0.5})


@router.post("/oct")
async def oct_scan(file: UploadFile = File(...), explain: bool = Form(True)):
    img = await core.read_image(file, "OCT scan")
    err = core.check_kind(img, "oct")
    if err:
        raise HTTPException(400, err)
    if not oct_service.status()["ready"]:
        raise HTTPException(503, "OCT model is not loaded; see /api/health")
    return {"success": True, **oct_service.predict(img, explain), "disclaimer": DISCLAIMER}


@router.get("/clinical/spec")
def clinical_spec():
    if not clinical_service.status()["ready"]:
        raise HTTPException(503, "clinical models are not loaded; see /api/health")
    return {"fields": clinical_service.feature_spec()}


@router.post("/clinical")
def clinical(values: dict = Body(...)):
    try:
        out = clinical_service.predict({k: v for k, v in values.items() if k != "HVF_MD"})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    if values.get("HVF_MD") is not None:
        out["md_rule"] = clinical_service.stage_from_md(float(values["HVF_MD"]))
    return {"success": True, **out, "disclaimer": DISCLAIMER}


@router.post("/assess")
async def assess(file: Optional[UploadFile] = File(None), clinical_json: str = Form("{}"), explain: bool = Form(True)):
    """One call, any subset of inputs. Fuses OCT + clinical probabilities when both are present."""
    try:
        values = json.loads(clinical_json) if clinical_json else {}
    except json.JSONDecodeError:
        raise HTTPException(400, "clinical_json is not valid JSON")
    n_clin = sum(v is not None for k, v in values.items() if k != "HVF_MD")
    if file is None and n_clin == 0:
        raise HTTPException(400, "provide an OCT scan, clinical measurements, or both")
    out: dict = {"success": True, "components": [], "disclaimer": DISCLAIMER}
    oct_res = clin_res = None
    if file is not None:
        img = await core.read_image(file, "OCT scan")
        err = core.check_kind(img, "oct")
        if err:
            raise HTTPException(400, err)
        if not oct_service.status()["ready"]:
            raise HTTPException(503, "OCT model is not loaded")
        oct_res = oct_service.predict(img, explain)
        out["oct"] = oct_res
        out["components"].append("oct")
    if n_clin:
        try:
            clin_res = clinical_service.predict({k: v for k, v in values.items() if k != "HVF_MD"})
        except ValueError as e:
            raise HTTPException(400, str(e))
        out["clinical"] = clin_res
        out["components"].append("clinical")
    if values.get("HVF_MD") is not None:
        out["md_rule"] = clinical_service.stage_from_md(float(values["HVF_MD"]))
    if oct_res and clin_res:
        w = _fusion_weights()
        classes = oct_res["classes"]
        po = np.array([oct_res["probabilities"][c] for c in classes])
        pc = np.array([clin_res["multiclass"]["probabilities"][c] for c in classes])
        p = (w["oct"] * po + w["clinical"] * pc) / (w["oct"] + w["clinical"])
        k = int(p.argmax())
        out["fused"] = {"classes": classes, "probabilities": {c: round(float(v), 4) for c, v in zip(classes, p)},
                        "prediction": classes[k], "confidence": round(float(p[k]), 4),
                        "p_glaucoma": round(float(1 - p[0]), 4), "weights": w,
                        "agreement": oct_res["prediction"] == clin_res["multiclass"]["prediction"],
                        "defer": defer_service.decide("fused", float(p[k]))}
        out["components"].append("fused")
    return out


@router.post("/multimodal")
async def multimodal(
    modality: str = Form(...),
    fundus: Optional[UploadFile] = File(None),
    oct: Optional[UploadFile] = File(None),
    oct_slices: Optional[List[UploadFile]] = File(None),
    explain: bool = Form(False),
):
    """GAMMA fundus + OCT-volume model (Normal / Early / Progressive)."""
    if modality not in GAMMA_MODALITIES:
        raise HTTPException(400, f"modality must be one of {sorted(GAMMA_MODALITIES)}")
    fundus_img = oct_img = None
    if fundus is not None:
        fundus_img = await core.read_image(fundus, "fundus")
        if (e := gamma_service.check_sanity(fundus_img, "fundus")):
            raise HTTPException(400, f"fundus: {e}")
    if oct is not None:
        oct_img = await core.read_image(oct, "oct")
        if (e := gamma_service.check_sanity(oct_img, "oct")):
            raise HTTPException(400, f"oct: {e}")
    slices = None
    if oct_slices:
        slices = [await core.read_image(f, f"oct_slices[{i}]") for i, f in enumerate(oct_slices)]
        need = gamma_service.expected_slices(modality)
        if need and len(slices) != need:
            raise HTTPException(400, f"oct_slices must contain exactly {need} images, got {len(slices)}")
    if modality in ("fundus", "fusion") and fundus_img is None:
        raise HTTPException(400, "a fundus image is required for this modality")
    if modality in ("oct", "fusion") and oct_img is None and slices is None:
        raise HTTPException(400, "an OCT image (or 8 ordered slices) is required for this modality")
    if not gamma_service.is_ready(modality):
        raise HTTPException(503, f"model {modality!r} did not load; see /api/health")
    t0 = time.perf_counter()
    try:
        r = gamma_service.predict(modality, fundus_img, oct_img, slices, explain=explain)
    except ValueError as e:
        raise HTTPException(400, str(e))
    log.info("multimodal %s -> %s (%.0f ms)", modality, r["prediction"], (time.perf_counter() - t0) * 1000)
    return {"success": True, "modality": modality, "prediction": r["prediction"],
            "confidence": round(r["confidence"], 4),
            "probabilities": {k: round(v, 4) for k, v in r["probabilities"].items()},
            "inference_time_ms": round(r["inference_ms"], 2), "model_version": r["model_version"],
            "oct_mode": r["oct_mode"], "fundus_heatmap": r["fundus_heatmap"], "disclaimer": DISCLAIMER}
