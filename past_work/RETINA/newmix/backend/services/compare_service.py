"""Run the fundus-only, OCT-only and fusion checkpoints on the same input, then derive
agreement, a needs-review flag and a display risk band.

The agreement / review / risk functions are pure (dicts in, dicts out) so they can be
unit-tested without loading any model. The 0.60 review threshold and the risk bands are
illustrative display rules, not validated operating points.
"""

from __future__ import annotations

from collections import Counter

import core
from services import gamma_service

MODELS = ("fundus", "oct", "fusion")
CONF_THRESHOLD = 0.60
RISK_LOW, RISK_HIGH = 0.35, 0.65
CAVEAT = core.GAMMA_CAVEAT


class ModelsNotReady(Exception):
    def __init__(self, missing: list[str]):
        super().__init__(f"models not loaded: {', '.join(missing)}")
        self.missing = missing


def agreement(preds: dict[str, str]) -> dict:
    total = len(preds)
    top, n = Counter(preds.values()).most_common(1)[0]
    if n == total:
        return {"all_agree": True, "n_agree": n, "majority": top, "outliers": [],
                "banner": f"All {total} models agree on {top}"}
    if n >= 2:
        outliers = sorted(m for m, p in preds.items() if p != top)
        verb = "disagrees" if len(outliers) == 1 else "disagree"
        return {"all_agree": False, "n_agree": n, "majority": top, "outliers": outliers,
                "banner": f"{n} of {total} models agree on {top}; {', '.join(outliers)} {verb}"}
    return {"all_agree": False, "n_agree": 1, "majority": None, "outliers": [],
            "banner": f"All {total} models disagree"}


def review(agr: dict, fusion_confidence: float, threshold: float = CONF_THRESHOLD) -> dict:
    reasons: list[str] = []
    if not agr["all_agree"]:
        reasons.append("models disagree")
    if fusion_confidence < threshold:
        reasons.append(f"low fusion confidence ({fusion_confidence:.2f} < {threshold:.2f})")
    return {"flag": bool(reasons), "reasons": reasons, "confidence_threshold": threshold}


def risk(fusion_probs: dict[str, float]) -> dict:
    score = round(1.0 - float(fusion_probs["normal"]), 4)
    level = "low" if score < RISK_LOW else "elevated" if score < RISK_HIGH else "high"
    return {"score": score, "level": level, "basis": "1 - P(normal) from the fusion model",
            "note": "Model-score band for display; not a clinical risk estimate."}


def validate_inputs(fundus_img, oct_img, slices) -> None:
    """Raises ValueError with a user-facing message; routers map it to HTTP 400."""
    if fundus_img is None:
        raise ValueError("a fundus image is required")
    if (e := gamma_service.check_sanity(fundus_img, "fundus")):
        raise ValueError(f"fundus: {e}")
    if slices is None and oct_img is None:
        raise ValueError("an OCT image (or 8 ordered slices) is required")
    if oct_img is not None and (e := gamma_service.check_sanity(oct_img, "oct")):
        raise ValueError(f"oct: {e}")
    if slices is not None:
        for need in {gamma_service.expected_slices(m) for m in ("oct", "fusion")} - {None}:
            if len(slices) != need:
                raise ValueError(f"oct: expected {need} slices, got {len(slices)}")
        for i, s in enumerate(slices):
            if (e := gamma_service.check_sanity(s, "oct")):
                raise ValueError(f"oct slice {i + 1}: {e}")


def _shape(r: dict) -> dict:
    return {"prediction": r["prediction"], "confidence": round(r["confidence"], 4),
            "probabilities": {k: round(v, 4) for k, v in r["probabilities"].items()},
            "inference_time_ms": round(r["inference_ms"], 2), "model_version": r["model_version"]}


def run(fundus_img, oct_img=None, slices=None, explain: bool = False) -> dict:
    missing = [m for m in MODELS if not gamma_service.is_ready(m)]
    if missing:
        raise ModelsNotReady(missing)
    validate_inputs(fundus_img, oct_img, slices)
    raw = {
        "fundus": gamma_service.predict("fundus", fundus_img),
        "oct": gamma_service.predict("oct", None, oct_img, slices),
        "fusion": gamma_service.predict("fusion", fundus_img, oct_img, slices, explain=explain),
    }
    models = {m: _shape(r) for m, r in raw.items()}
    agr = agreement({m: r["prediction"] for m, r in models.items()})
    return {
        "success": True,
        "models": models,
        "agreement": agr,
        "needs_review": review(agr, models["fusion"]["confidence"]),
        "risk": risk(models["fusion"]["probabilities"]),
        "oct_mode": raw["fusion"]["oct_mode"],
        "fundus_heatmap": raw["fusion"]["fundus_heatmap"],
        "caveat": CAVEAT,
        "disclaimer": core.DISCLAIMER,
    }
