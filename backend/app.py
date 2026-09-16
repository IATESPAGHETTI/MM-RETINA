"""
FastAPI backend for the MM-RETINA live demo.

Loads the real trained checkpoints ONCE at startup (see inference.py) and
serves POST /api/predict for the website's /demo page. All preprocessing
and model code is reused from training/ — nothing here duplicates that
logic.

Run (from this directory, same Python env as training/):
    uvicorn app:app --reload --port 8000

See README.md in this folder for full setup/API docs.
"""

from __future__ import annotations

import io
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

import inference

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("mm-retina-backend")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
VALID_MODALITIES = {"fundus", "oct", "fusion"}
CORS_ORIGIN = os.environ.get("MM_RETINA_CORS_ORIGIN", "http://localhost:3000")

_model_status: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Loading models from training/checkpoints/ ...")
    _model_status.update(inference.load_all_models())
    if _model_status["errors"]:
        log.warning("Some models failed to load: %s", _model_status["errors"])
    log.info("Model load complete. Loaded=%s device=%s", _model_status["loaded"], _model_status["device"])
    yield


app = FastAPI(title="MM-RETINA inference API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """Only reports a model as available if it was actually loaded successfully."""
    return {
        "status": "ok",
        "models_loaded": _model_status.get("loaded", []),
        "model_errors": _model_status.get("errors", {}),
        "device": _model_status.get("device"),
    }


async def _read_and_validate_image(upload: Optional[UploadFile], field_name: str) -> Optional[Image.Image]:
    if upload is None:
        return None
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name}: unsupported content type — use JPEG, PNG, or WEBP",
        )
    data = await upload.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"{field_name}: file too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)}MB)",
        )
    try:
        img = Image.open(io.BytesIO(data))
        img.load()  # force full decode now so corrupt files fail here, not mid-inference
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail=f"{field_name}: not a valid image file")
    # Color-mode conversion (RGB for fundus, grayscale for OCT) happens in
    # inference.py, matching training/data.py's per-modality handling —
    # don't force a single mode here for both.
    return img


@app.post("/api/predict")
async def predict(
    modality: str = Form(...),
    fundus: Optional[UploadFile] = File(None),
    oct: Optional[UploadFile] = File(None),
    oct_slices: Optional[List[UploadFile]] = File(None),
):
    """
    OCT input, in priority order:
      1. `oct_slices` — multiple files, sent in volume order. Must contain
         exactly the model's expected slice count (see /api/health ->
         load a modality then GET the count via a 400 error message, or
         just send 8 — that's what every checkpoint here expects). Used
         as a real ordered volume, no repetition.
      2. `oct` — single file, repeated across the expected slice count
         (documented fallback for an arbitrary user upload).
    """
    request_id = str(uuid.uuid4())[:8]
    t0 = time.perf_counter()

    if modality not in VALID_MODALITIES:
        log.warning("[%s] rejected: invalid modality=%r", request_id, modality)
        raise HTTPException(status_code=400, detail=f"modality must be one of {sorted(VALID_MODALITIES)}")

    fundus_img = await _read_and_validate_image(fundus, "fundus")
    oct_img = await _read_and_validate_image(oct, "oct")

    oct_slice_imgs: Optional[list] = None
    if oct_slices:
        oct_slice_imgs = [
            await _read_and_validate_image(f, f"oct_slices[{i}]") for i, f in enumerate(oct_slices)
        ]
        if modality in ("oct", "fusion"):
            expected = inference.expected_oct_slices(modality)
            if expected is not None and len(oct_slice_imgs) != expected:
                log.warning(
                    "[%s] rejected: oct_slices has %d images, model expects %d",
                    request_id, len(oct_slice_imgs), expected,
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"oct_slices must contain exactly {expected} images for modality={modality!r}, got {len(oct_slice_imgs)}",
                )

    has_oct_input = oct_img is not None or oct_slice_imgs is not None

    if modality in ("fundus", "fusion") and fundus_img is None:
        log.warning("[%s] rejected: missing fundus image for modality=%s", request_id, modality)
        raise HTTPException(status_code=400, detail="fundus image is required for this modality")
    if modality in ("oct", "fusion") and not has_oct_input:
        log.warning("[%s] rejected: missing oct image(s) for modality=%s", request_id, modality)
        raise HTTPException(status_code=400, detail="oct image (single or oct_slices) is required for this modality")

    if not inference.is_ready(modality):
        log.error("[%s] model for modality=%s not loaded", request_id, modality)
        raise HTTPException(
            status_code=503,
            detail=f"model for modality={modality!r} failed to load at startup — see /api/health",
        )

    log.info(
        "[%s] request modality=%s has_fundus=%s has_oct=%s oct_slices=%s",
        request_id, modality, fundus_img is not None, oct_img is not None,
        len(oct_slice_imgs) if oct_slice_imgs else 0,
    )

    try:
        result = inference.predict(modality, fundus_img, oct_img, oct_slice_imgs)
    except ValueError as e:
        log.warning("[%s] rejected: %s", request_id, e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        log.exception("[%s] inference failed", request_id)
        raise HTTPException(status_code=500, detail="inference failed — see server logs")

    total_ms = (time.perf_counter() - t0) * 1000
    log.info(
        "[%s] success prediction=%s confidence=%.3f inference_ms=%.1f total_ms=%.1f oct_mode=%s",
        request_id, result["prediction"], result["confidence"], result["inference_ms"], total_ms, result["oct_mode"],
    )

    return {
        "success": True,
        "request_id": request_id,
        "modality": modality,
        "prediction": result["prediction"],
        "confidence": round(result["confidence"], 4),
        "probabilities": {k: round(v, 4) for k, v in result["probabilities"].items()},
        "inference_time_ms": round(result["inference_ms"], 2),
        "model_version": result["model_version"],
        "oct_mode": result["oct_mode"],
    }
