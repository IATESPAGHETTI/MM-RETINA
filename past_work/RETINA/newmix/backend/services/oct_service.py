"""Research-cohort OCT B-scan severity model (Control / Mild / Moderate / Severe).

The saved file holds an ensemble of state dicts (different seeds, same
architecture). Probabilities are averaged; the Grad-CAM map is averaged over
the same members so the picture matches the number.
"""

from __future__ import annotations

import sys
import time

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from core import MODELS_DIR, ROOT, to_data_url
from services import defer_service

sys.path.insert(0, str(ROOT / "ml" / "glaucoma"))
from oct_model import IMG_H, IMG_W, OCTNet  # noqa: E402

_DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_members: list[OCTNet] = []
_meta: dict = {}
_error: str | None = None


def load() -> dict:
    global _error
    path = MODELS_DIR / "oct_research.pt"
    try:
        ck = torch.load(path, map_location="cpu", weights_only=False)
        for sd in ck["state_dicts"]:
            m = OCTNet(ck["arch"], pretrained=False)
            m.load_state_dict(sd)
            _members.append(m.to(_DEV).eval())
        _meta.update(arch=ck["arch"], classes=ck["classes"], members=len(_members), epochs=ck["epochs"])
        _error = None
    except Exception as e:  # noqa: BLE001
        _error = f"{type(e).__name__}: {e}"
    return status()


def status() -> dict:
    return {"ready": bool(_members), "error": _error, **_meta}


def _prep(img: Image.Image) -> torch.Tensor:
    im = img.convert("L")
    w, h = im.size
    im = im.crop((3, 3, w - 3, h - 3)).resize((IMG_W, IMG_H), Image.BILINEAR)
    return torch.from_numpy(np.asarray(im, dtype=np.float32) / 255.0)[None, None]


def _gradcam(model: OCTNet, x: torch.Tensor, cls: int) -> np.ndarray:
    acts, grads = [], []
    layer = model.gradcam_layer()
    h1 = layer.register_forward_hook(lambda _m, _i, o: acts.append(o))
    h2 = layer.register_full_backward_hook(lambda _m, _gi, go: grads.append(go[0]))
    try:
        model.zero_grad(set_to_none=True)
        out = model(x.requires_grad_(True))
        out[0, cls].backward()
    finally:
        h1.remove()
        h2.remove()
    w = grads[0].mean((2, 3), keepdim=True)
    cam = F.relu((w * acts[0]).sum(1, keepdim=True))
    cam = F.interpolate(cam, size=(IMG_H, IMG_W), mode="bilinear", align_corners=False)[0, 0]
    cam = cam - cam.min()
    return (cam / (cam.max() + 1e-8)).detach().cpu().numpy()


def predict(img: Image.Image, explain: bool = True) -> dict:
    if not _members:
        raise RuntimeError(_error or "OCT model not loaded")
    x = _prep(img).to(_DEV)
    t0 = time.perf_counter()
    with torch.no_grad():
        probs = torch.stack([torch.softmax(m(x), 1)[0] for m in _members]).mean(0).cpu().numpy()
    ms = (time.perf_counter() - t0) * 1000
    cls = int(probs.argmax())
    out = {
        "classes": _meta["classes"],
        "probabilities": {c: round(float(p), 4) for c, p in zip(_meta["classes"], probs)},
        "prediction": _meta["classes"][cls],
        "confidence": round(float(probs[cls]), 4),
        "p_glaucoma": round(float(1 - probs[0]), 4),
        "inference_ms": round(ms, 1),
        "ensemble_members": len(_members),
        "heatmap": None,
        "defer": defer_service.decide("oct", float(probs[cls])),
    }
    if explain:
        cam = np.mean([_gradcam(m, x.clone(), cls) for m in _members], axis=0)
        base = (x[0, 0].cpu().numpy() * 255).astype(np.uint8)
        heat = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)[:, :, ::-1]
        over = (0.55 * np.stack([base] * 3, -1) + 0.45 * heat).astype(np.uint8)
        out["heatmap"] = to_data_url(over)
        out["input_preview"] = to_data_url(np.stack([base] * 3, -1))
    return out
