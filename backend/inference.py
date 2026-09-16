"""
Thin inference wrapper around the EXISTING, validated training pipeline.

This does not reimplement preprocessing or the model architecture — it
imports directly from training/data.py (transforms, class names) and
training/evaluate.py (checkpoint loading), which are the same functions
the CV/single-split experiments used. If those functions are wrong, this
is wrong the same way; there is deliberately no second implementation to
drift out of sync.

Known, documented limitation: the trained models expect a short sequence
of OCT B-scan slices (8, sampled evenly from a 256-slice volume — see
training/data.py's evenly_spaced_indices). The live demo accepts a single
OCT image (one B-scan or a representative image), which is repeated
across all 8 slice positions to match the model's expected input shape.
This is a real forward pass through the real trained model on a real
(if repeated) input — not a fabricated prediction — but it is not the
same as running the model on an actual 256-slice volume the way the CV
experiments did. Flagged here and in the API response/docs, not hidden.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import torch
from PIL import Image

TRAINING_DIR = Path(__file__).resolve().parent.parent / "training"
sys.path.insert(0, str(TRAINING_DIR))

from data import build_fundus_transform, build_oct_transform, GRADE_NAMES  # noqa: E402
from evaluate import load_model_from_checkpoint  # noqa: E402

CHECKPOINTS_DIR = TRAINING_DIR / "checkpoints"
CHECKPOINT_FILES = {
    "fundus": CHECKPOINTS_DIR / "fundus_run1.pt",
    "oct": CHECKPOINTS_DIR / "oct_run1.pt",
    "fusion": CHECKPOINTS_DIR / "fusion_run1.pt",
}

_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_models: dict[str, torch.nn.Module] = {}
_train_args: dict[str, dict] = {}
_load_errors: dict[str, str] = {}


def load_all_models() -> dict:
    """Loads every checkpoint that exists. Only ever reports a modality as
    'loaded' if load_model_from_checkpoint actually succeeded — a missing
    or corrupt checkpoint shows up in `errors`, not as a silently-skipped
    success."""
    for modality, path in CHECKPOINT_FILES.items():
        try:
            model, targs = load_model_from_checkpoint(path, _device)
            model.eval()
            _models[modality] = model
            _train_args[modality] = targs
        except Exception as e:  # noqa: BLE001 - report every failure mode, don't guess which
            _load_errors[modality] = str(e)
    return {"loaded": sorted(_models.keys()), "errors": dict(_load_errors), "device": str(_device)}


def is_ready(modality: str) -> bool:
    return modality in _models


def _dummy_fundus(img_size: int) -> torch.Tensor:
    return torch.zeros(1, 3, img_size, img_size)


def _dummy_oct(img_size: int, n_slices: int) -> torch.Tensor:
    return torch.zeros(1, n_slices, 1, img_size, img_size)


def predict(modality: str, fundus_image: Image.Image | None, oct_image: Image.Image | None) -> dict:
    if modality not in _models:
        raise RuntimeError(f"Model for modality={modality!r} is not loaded — check /api/health")

    model = _models[modality]
    targs = _train_args[modality]
    img_size = targs["img_size"]
    n_slices = targs["oct_slices"]

    t_pre0 = time.perf_counter()

    if fundus_image is not None:
        fundus_t = build_fundus_transform(img_size, train=False)(fundus_image.convert("RGB")).unsqueeze(0)
    else:
        fundus_t = _dummy_fundus(img_size)

    if oct_image is not None:
        single_slice = build_oct_transform(img_size, train=False)(oct_image.convert("L"))  # (1, H, W)
        oct_t = single_slice.unsqueeze(0).repeat(n_slices, 1, 1, 1).unsqueeze(0)  # (1, N, 1, H, W)
    else:
        oct_t = _dummy_oct(img_size, n_slices)

    preprocessing_ms = (time.perf_counter() - t_pre0) * 1000

    fundus_t = fundus_t.to(_device)
    oct_t = oct_t.to(_device)

    t_inf0 = time.perf_counter()
    with torch.no_grad():
        logits = model(fundus_t, oct_t)
        probs = torch.softmax(logits, dim=-1)[0].cpu().numpy()
    inference_ms = (time.perf_counter() - t_inf0) * 1000

    pred_idx = int(probs.argmax())

    return {
        "modality": modality,
        "prediction": GRADE_NAMES[pred_idx],
        "confidence": float(probs[pred_idx]),
        "probabilities": {GRADE_NAMES[i]: float(probs[i]) for i in range(len(GRADE_NAMES))},
        "preprocessing_ms": preprocessing_ms,
        "inference_ms": inference_ms,
        "model_version": targs.get("run_name", CHECKPOINT_FILES[modality].stem),
        "oct_repeated_single_slice": oct_image is not None and modality in ("oct", "fusion"),
    }
