"""
Thin inference wrapper around the EXISTING, validated training pipeline.

This does not reimplement preprocessing or the model architecture — it
imports directly from training/data.py (transforms, class names) and
training/evaluate.py (checkpoint loading), which are the same functions
the CV/single-split experiments used. If those functions are wrong, this
is wrong the same way; there is deliberately no second implementation to
drift out of sync.

The trained models expect a short sequence of OCT B-scan slices (8,
sampled evenly from a 256-slice volume via training/data.py's
evenly_spaced_indices(256, 8) == [0, 36, 73, 109, 146, 182, 219, 255]).
Two OCT input modes are supported here:

  - Real volume (preferred): the caller supplies exactly `n_slices` real,
    ordered B-scan images (e.g. the actual GAMMA sample 0001 slices at
    those exact 8 indices, already extracted to
    website/public/oct-volume/0001/). These are stacked in the given
    order and passed through unchanged — this is the same shape and
    semantics the model was trained and cross-validated on, just for one
    live sample instead of a batch.
  - Single-slice fallback: the caller supplies one OCT image, which is
    repeated across all 8 slice positions. This is a real forward pass
    through the real trained model on a real (if repeated) input — not a
    fabricated prediction — but it is not equivalent to a real volume.
    Used when the user uploads their own single image rather than
    selecting the real demo volume.

Both modes are reported in the API response (`oct_mode`), never silently
conflated.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import torch
from PIL import Image

import gradcam

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


def expected_oct_slices(modality: str) -> int | None:
    """How many real slices `oct_images` must contain for this modality's
    checkpoint, so the API layer can validate a multi-slice upload before
    calling predict(). None if the modality isn't loaded."""
    targs = _train_args.get(modality)
    return targs["oct_slices"] if targs else None


def _dummy_fundus(img_size: int) -> torch.Tensor:
    return torch.zeros(1, 3, img_size, img_size)


def _dummy_oct(img_size: int, n_slices: int) -> torch.Tensor:
    return torch.zeros(1, n_slices, 1, img_size, img_size)


def predict(
    modality: str,
    fundus_image: Image.Image | None,
    oct_image: Image.Image | None = None,
    oct_images: list[Image.Image] | None = None,
    explain: bool = False,
) -> dict:
    """
    oct_image: single image, repeated across all slice positions (fallback).
    oct_images: ordered list of real slices, length must equal the
        checkpoint's expected `oct_slices` — stacked as-is, no repetition.
        Takes priority over oct_image if both are somehow given.
    explain: if True and a fundus image was provided (modality in
        {"fundus", "fusion"}), also runs a real Grad-CAM forward+backward
        pass (see gradcam.py) and includes `fundus_heatmap` as a base64
        PNG data URL in the result. No-op (silently skipped, not an
        error) for modality="oct" or when no fundus image is given —
        there's nothing to explain in that case.
    """
    if modality not in _models:
        raise RuntimeError(f"Model for modality={modality!r} is not loaded — check /api/health")

    model = _models[modality]
    targs = _train_args[modality]
    img_size = targs["img_size"]
    n_slices = targs["oct_slices"]

    if oct_images is not None and len(oct_images) != n_slices:
        raise ValueError(f"oct_images must contain exactly {n_slices} slices, got {len(oct_images)}")

    t_pre0 = time.perf_counter()

    if fundus_image is not None:
        fundus_t = build_fundus_transform(img_size, train=False)(fundus_image.convert("RGB")).unsqueeze(0)
    else:
        fundus_t = _dummy_fundus(img_size)

    oct_mode = "none"
    if oct_images is not None:
        oct_tf = build_oct_transform(img_size, train=False)
        slices = [oct_tf(img.convert("L")) for img in oct_images]  # each (1, H, W), in given order
        oct_t = torch.stack(slices, dim=0).unsqueeze(0)  # (1, N, 1, H, W)
        oct_mode = "real_volume"
    elif oct_image is not None:
        single_slice = build_oct_transform(img_size, train=False)(oct_image.convert("L"))  # (1, H, W)
        oct_t = single_slice.unsqueeze(0).repeat(n_slices, 1, 1, 1).unsqueeze(0)  # (1, N, 1, H, W)
        oct_mode = "repeated_single_slice"
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

    result = {
        "modality": modality,
        "prediction": GRADE_NAMES[pred_idx],
        "confidence": float(probs[pred_idx]),
        "probabilities": {GRADE_NAMES[i]: float(probs[i]) for i in range(len(GRADE_NAMES))},
        "preprocessing_ms": preprocessing_ms,
        "inference_ms": inference_ms,
        "model_version": targs.get("run_name", CHECKPOINT_FILES[modality].stem),
        "oct_mode": oct_mode if modality in ("oct", "fusion") else "n/a",
        "fundus_heatmap": None,
    }

    if explain and fundus_image is not None and modality in ("fundus", "fusion"):
        # Explains the class the model actually predicted (pred_idx), not a
        # hypothetical one — the heatmap matches the prediction shown to
        # the user. A fresh forward+backward pass; the no_grad() one above
        # is untouched/unaffected.
        cam = gradcam.fundus_gradcam(model, fundus_t, oct_t, pred_idx)
        base_image = fundus_image.convert("RGB").resize((img_size, img_size))
        result["fundus_heatmap"] = gradcam.overlay_heatmap_as_data_url(base_image, cam)

    return result
