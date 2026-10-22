"""Diabetes-focused retinal analysis (Kartik's DIPP work, unchanged models).

  * vessel segmentation   U-Net trained on DRIVE (PyTorch, 256x256)
  * fractal analysis      box-counting dimension of the vessel-mask boundary
  * HbA1c estimation      two Keras-3 CNNs (binary >=6.5 and 6-bin), run on the torch backend

Preprocessing and thresholds are Kartik's. Only the box-counting loop is
vectorised (same quantity, integer box sizes). No validation metrics ship
with these model files, so the API says so rather than implying accuracy.
"""

from __future__ import annotations

import importlib.util
import os
import time

os.environ.setdefault("KERAS_BACKEND", "torch")

import cv2
import numpy as np
import torch
from PIL import Image
from scipy import stats
from skimage.segmentation import find_boundaries
from torchvision import transforms

from core import DIPP_DIR, to_data_url

_DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_unet = None
_hba1c: dict = {}
_errors: dict[str, str] = {}

HBA1C_BINS = {0: "3.7-5.1", 1: "5.2-5.6", 2: "5.7-6.4", 3: "6.5-7.5", 4: "7.6-9.0", 5: ">9.0"}


def load() -> dict:
    global _unet
    try:
        spec = importlib.util.spec_from_file_location("dipp_model", DIPP_DIR / "model.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        net = mod.UNet().to(_DEV)
        net.load_state_dict(torch.load(DIPP_DIR / "saved_model" / "unet_drive.pth", map_location=_DEV))
        _unet = net.eval()
    except Exception as e:  # noqa: BLE001
        _errors["vessels"] = f"{type(e).__name__}: {e}"
    try:
        import keras
        for name in ("binary", "multi"):
            _hba1c[name] = keras.models.load_model(DIPP_DIR / "models" / f"{name}_final_best_hba1c_model.keras", compile=False)
    except Exception as e:  # noqa: BLE001
        _errors["hba1c"] = f"{type(e).__name__}: {e}"
    return status()


def status() -> dict:
    return {"vessels": _unet is not None, "hba1c": len(_hba1c) == 2, "errors": dict(_errors),
            "av_classification": False,
            "av_note": "artery/vein weights (av_model.pth) were not part of the delivered project"}


# ---- preprocessing (Kartik's) ---------------------------------------------------------------------
def _resize_pad(image, size=(512, 512)):
    tw, th = size
    h, w = image.shape[:2]
    s = min(tw / w, th / h)
    nw, nh = int(w * s), int(h * s)
    r = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_AREA)
    out = np.zeros((th, tw, 3), np.uint8)
    y0, x0 = (th - nh) // 2, (tw - nw) // 2
    out[y0:y0 + nh, x0:x0 + nw] = r
    return out


def _circular_mask(image):
    h, w = image.shape[:2]
    size = max(h, w)
    canvas = np.full((size, size, 3), 255, np.uint8)
    y0, x0 = (size - h) // 2, (size - w) // 2
    canvas[y0:y0 + h, x0:x0 + w] = image
    mask = np.zeros((size, size), np.uint8)
    cv2.circle(mask, (size // 2, size // 2), min(h, w) // 2, 255, -1)
    return np.where(mask[:, :, None] == 255, canvas, 255).astype(np.uint8)


def _prep_hba1c(img: Image.Image) -> np.ndarray:
    bgr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.addWeighted(l, 1.5, cv2.GaussianBlur(l, (3, 3), 0), -0.5, 0)
    l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
    l = np.uint8(np.power(l / 255.0, 1.2) * 255)
    out = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    out = _circular_mask(_resize_pad(out))
    return (out / 255.0)[None].astype("float32")


# ---- public API -----------------------------------------------------------------------------------
def segment(img: Image.Image) -> np.ndarray:
    if _unet is None:
        raise RuntimeError(_errors.get("vessels", "vessel model not loaded"))
    x = transforms.Compose([transforms.Resize((256, 256)), transforms.ToTensor()])(img.convert("RGB"))
    with torch.no_grad():
        p = _unet(x[None].to(_DEV))[0, 0].cpu().numpy()
    return (p > 0.5).astype(np.uint8)


def vessels(img: Image.Image) -> dict:
    t0 = time.perf_counter()
    m256 = segment(img)
    rgb = np.array(img.convert("RGB").resize((512, 512)))
    mask = cv2.resize(m256, (512, 512), interpolation=cv2.INTER_NEAREST).astype(bool)
    over = rgb.copy()
    over[mask] = (0.35 * over[mask] + 0.65 * np.array([255, 70, 60])).astype(np.uint8)
    # vessel density inside the retinal disc only (the fundus corners are black)
    disc = rgb.mean(2) > 15
    density = float(mask[disc].mean()) if disc.any() else 0.0
    return {"overlay": to_data_url(over), "mask": to_data_url((mask * 255).astype(np.uint8)),
            "vessel_density_pct": round(density * 100, 2), "inference_ms": round((time.perf_counter() - t0) * 1000, 1)}


def _box_counts(b: np.ndarray, size: int) -> int:
    h, w = b.shape
    hp, wp = -(-h // size) * size, -(-w // size) * size
    p = np.zeros((hp, wp), bool)
    p[:h, :w] = b
    return int(p.reshape(hp // size, size, wp // size, size).any(axis=(1, 3)).sum())


def fractal(img: Image.Image) -> dict:
    mask = segment(img)
    bnd = find_boundaries(mask, mode="inner")
    if not bnd.any():
        raise ValueError("no vessel boundaries found; the image may not be a fundus photo")
    sizes = np.unique(np.round(np.logspace(0, np.log10(min(bnd.shape) / 2), 15, endpoint=False)).astype(int))
    counts = np.array([_box_counts(bnd, int(s)) for s in sizes])
    slope, _, r, _, _ = stats.linregress(-np.log(sizes), np.log(counts))
    return {"fractal_dimension": round(float(slope), 4), "r_squared": round(float(r) ** 2, 4),
            "box_sizes": sizes.tolist(), "counts": counts.tolist(),
            "log_sizes": (-np.log(sizes)).round(4).tolist(), "log_counts": np.log(counts).round(4).tolist(),
            "note": "Higher values mean a more branched, space-filling vessel pattern. This is a descriptive "
                    "measurement under this pipeline (256 px mask boundary); no reference range has been "
                    "validated here, so compare only between images processed the same way."}


def hba1c(img: Image.Image) -> dict:
    if len(_hba1c) < 2:
        raise RuntimeError(_errors.get("hba1c", "HbA1c models not loaded"))
    x = _prep_hba1c(img)
    t0 = time.perf_counter()
    pb = float(np.asarray(_hba1c["binary"].predict(x, verbose=0)).ravel()[0])
    pm = np.asarray(_hba1c["multi"].predict(x, verbose=0))[0]
    pos = pb > 0.5
    k = int(np.argmax(pm))
    # the 6-bin model's bins 3-5 are all >= 6.5, so the two models must agree on that side of the cut
    consistent = pos == (k >= 3)
    return {
        "consistent": consistent,
        "consistency_note": None if consistent else
            "The two HbA1c models contradict each other (one says elevated, the other a normal-range bin). "
            "On the 22 reference images supplied with the project the 6-bin model returned its lowest bin "
            "every time and the binary model flagged 95% as elevated, so these outputs are not informative.",
        "binary": {"label": "Elevated (HbA1c >= 6.5)" if pos else "Not elevated (HbA1c < 6.5)",
                   "probability_elevated": round(pb, 4), "confidence": round(pb if pos else 1 - pb, 4)},
        "multi": {"bin": k, "range": HBA1C_BINS[k], "confidence": round(float(pm[k]), 4),
                  "probabilities": {HBA1C_BINS[i]: round(float(v), 4) for i, v in enumerate(pm)}},
        "inference_ms": round((time.perf_counter() - t0) * 1000, 1),
        "validation": "No validation metrics were delivered with these two models. Treat as an "
                      "experimental research estimate; confirm any result with a laboratory HbA1c test.",
    }
