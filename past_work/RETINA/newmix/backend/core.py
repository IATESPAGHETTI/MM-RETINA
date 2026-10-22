"""Shared paths and helpers for the unified ProcureFlow-style service layer.

Every route module stays thin: validation + serialisation here, model logic in
`services/`. Services never import FastAPI, so they can be called from
scripts and tests directly.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import numpy as np
from fastapi import HTTPException, UploadFile
from PIL import Image, ImageStat, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
RESULTS_DIR = ROOT / "ml" / "results"
GAMMA_DIR = ROOT / "ml" / "gamma"
DIPP_DIR = ROOT / "backend" / "dipp"

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff"}


async def read_image(upload: UploadFile, field: str = "image") -> Image.Image:
    if upload.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"{field}: unsupported type {upload.content_type!r}; use JPEG, PNG or WEBP")
    data = await upload.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"{field}: file larger than {MAX_UPLOAD_BYTES // 2**20} MB")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, f"{field}: not a readable image")
    return img


def mean_saturation(img: Image.Image) -> float:
    hsv = img.convert("RGB").resize((64, 64)).convert("HSV")
    return ImageStat.Stat(hsv).mean[1] / 255.0


def check_kind(img: Image.Image, expected: str) -> str | None:
    """Cheap wrong-slot guard: OCT B-scans are near-grayscale, fundus photos
    are strongly coloured. Returns an error message or None."""
    s = mean_saturation(img)
    if expected == "oct" and s > 0.20:
        return (f"this image is too colour-saturated (saturation {s:.2f}) to be an OCT B-scan. "
                "Did you upload a fundus photo?")
    if expected == "fundus" and s < 0.15:
        return (f"this image is almost grayscale (saturation {s:.2f}), so it is not a colour fundus photo. "
                "Did you upload an OCT scan?")
    return None


def to_data_url(arr: np.ndarray | Image.Image, fmt: str = "PNG") -> str:
    img = arr if isinstance(arr, Image.Image) else Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(buf.getvalue()).decode()}"


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default
