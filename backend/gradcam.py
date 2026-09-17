"""
Grad-CAM (Selvaraju et al., 2017) for the fundus branch only.

Why fundus only, not OCT: the fundus branch is a standard single-image CNN
classifier path (one resnet18 backbone -> global pool -> linear head), so
hooking its last conv block (`layer4`, verified below) for Grad-CAM is the
textbook case with no architectural ambiguity. The OCT branch shares one
backbone across 8 slices and combines them with learned attention pooling
before the classifier; a per-slice Grad-CAM is architecturally plausible
(the same shared backbone produces one conv feature map per slice, and
gradients do flow back to each of them individually) but attributing
"importance" through an attention-pooled multi-instance aggregation is a
meaningfully different and less-established claim than single-image
Grad-CAM, and verifying it wasn't producing something misleading would
need more validation time than this change budgeted for. Deferred — see
backend/README.md's "Future enhancements" section — rather than shipped
undertested.

This computes a REAL Grad-CAM from a real forward + backward pass through
the real loaded model. It is not a decorative or fabricated heatmap: if
`layer4` isn't found (e.g. a future non-resnet backbone), this raises
rather than silently returning a blank/fake map.
"""

from __future__ import annotations

import base64
import io

import numpy as np
import torch
from PIL import Image


def _last_conv_module(backbone: torch.nn.Module) -> torch.nn.Module:
    if hasattr(backbone, "layer4"):
        return backbone.layer4
    raise ValueError(
        f"Grad-CAM target layer not known for backbone type {type(backbone).__name__} "
        "(only resnet-family timm backbones with `layer4` are supported)."
    )


def fundus_gradcam(model, fundus_tensor: torch.Tensor, oct_tensor: torch.Tensor, target_class: int) -> np.ndarray:
    """
    fundus_tensor: (1, 3, H, W) — the SAME preprocessed tensor used for the
        real prediction (not a separate/refetched image).
    oct_tensor: whatever the model's forward() expects for its OCT input;
        held fixed, gradients w.r.t. it are not used.
    target_class: which class's logit to explain (normally the model's own
        predicted class, so the heatmap explains the prediction actually
        shown to the user, not a hypothetical class).

    Returns an (h, w) float32 array in [0, 1] at the backbone's own conv
    feature-map resolution (caller resizes for display).
    """
    if model.fundus_encoder is None:
        raise ValueError("This model instance has no fundus encoder (modality='oct') — nothing to explain.")

    target_layer = _last_conv_module(model.fundus_encoder.backbone)

    activations: dict[str, torch.Tensor] = {}
    gradients: dict[str, torch.Tensor] = {}

    def fwd_hook(_module, _inp, out):
        activations["value"] = out

    def bwd_hook(_module, _grad_input, grad_output):
        gradients["value"] = grad_output[0]

    h_fwd = target_layer.register_forward_hook(fwd_hook)
    h_bwd = target_layer.register_full_backward_hook(bwd_hook)

    try:
        model.zero_grad(set_to_none=True)
        fundus_in = fundus_tensor.clone().detach().requires_grad_(True)
        logits = model(fundus_in, oct_tensor)
        score = logits[0, target_class]
        score.backward()

        acts = activations["value"][0]  # (C, h, w)
        grads = gradients["value"][0]  # (C, h, w)
        weights = grads.mean(dim=(1, 2))  # (C,) — global-average-pooled gradient per channel
        cam = torch.relu((weights[:, None, None] * acts).sum(dim=0))  # (h, w)
        cam = cam / (cam.max().clamp(min=1e-8))
        return cam.detach().cpu().numpy().astype(np.float32)
    finally:
        h_fwd.remove()
        h_bwd.remove()


def overlay_heatmap_as_data_url(base_image: Image.Image, cam: np.ndarray, alpha: float = 0.45) -> str:
    """Resizes `cam` to `base_image`'s size, applies a simple warm colormap
    (no extra colormap dependency needed), alpha-blends over the image, and
    returns a `data:image/png;base64,...` URL the frontend can render
    directly in an <img>/<Image> tag."""
    w, h = base_image.size
    cam_img = Image.fromarray((np.clip(cam, 0, 1) * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    cam_arr = np.asarray(cam_img).astype(np.float32) / 255.0

    heat = np.zeros((h, w, 3), dtype=np.float32)
    heat[..., 0] = np.clip(cam_arr * 2.2, 0, 1) * 255  # red ramps in first
    heat[..., 1] = np.clip((cam_arr - 0.45) * 2.2, 0, 1) * 255  # yellow at high activation

    base = np.asarray(base_image.convert("RGB")).astype(np.float32)
    blended = base * (1 - alpha * cam_arr[..., None]) + heat * (alpha * cam_arr[..., None])
    blended_img = Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8))

    buf = io.BytesIO()
    blended_img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
