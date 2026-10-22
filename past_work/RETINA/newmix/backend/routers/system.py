"""Health, model cards and dataset audit. Every number served here is read from a
results file written by the training scripts; nothing is hard-coded, so the UI
cannot show a metric that was not actually computed."""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter

import core
from services import clinical_service, diabetes_service, oct_service

router = APIRouter(prefix="/api", tags=["system"])
R = core.RESULTS_DIR


@router.get("/health")
def health():
    import inference  # services/_gamma on sys.path (added by gamma_service import)

    gamma_loaded = sorted(inference._models.keys())
    return {
        "status": "ok",
        # legacy keys kept for the original /demo page
        "models_loaded": gamma_loaded,
        "model_errors": inference._load_errors,
        "device": str(inference._device),
        "services": {
            "glaucoma_oct": oct_service.status(),
            "glaucoma_clinical": clinical_service.status(),
            "glaucoma_multimodal": {"ready": bool(gamma_loaded), "loaded": gamma_loaded,
                                    "errors": inference._load_errors},
            "diabetes": diabetes_service.status(),
        },
    }


def _ms(vals):
    return f"{np.mean(vals):.3f} ± {np.std(vals):.3f}"


def _pct(m, sd=None):
    return f"{m * 100:.1f}%" + (f" ± {sd * 100:.1f}" if sd is not None else "")


def _oct_card():
    cv = core.read_json(R / "oct" / "cv_summary.json", {})
    best, rows = None, []
    for arch, v in cv.items():
        runs = v["runs"]
        acc = [r["multiclass"]["accuracy"] for r in runs]
        bal = [r["multiclass"]["balanced_accuracy"] for r in runs]
        qwk = [r["multiclass"]["qwk"] for r in runs]
        auc = [r["binary"]["auc"] for r in runs]
        bacc = [r["binary"]["accuracy"] for r in runs]
        rows.append({"arch": arch, "acc": float(np.mean(acc)), "acc_sd": float(np.std(acc)),
                     "bal": float(np.mean(bal)), "qwk": float(np.mean(qwk)),
                     "bin_acc": float(np.mean(bacc)), "auc": float(np.mean(auc)), "seeds": len(runs)})
    return rows


@router.get("/models")
def models():
    clin = core.read_json(R / "clinical" / "metrics.json", {})
    fusion = core.read_json(R / "fusion" / "metrics.json", {})
    gamma = core.read_json(R / "gamma_cv_summary.json", {})
    final = core.read_json(R / "clinical" / "final_models.json", {})
    return {
        "clinical": clin, "clinical_final": final,
        "oct": _oct_card(), "fusion": fusion, "gamma": gamma,
        "defer": core.read_json(R / "clinical" / "defer.json", {}),
        "paper_protocol": core.read_json(R / "paper" / "leaky_protocol.json", []),
        "diabetes": {"validation": None,
                     "note": "Kartik's HbA1c and vessel models shipped without validation metrics."},
    }


@router.get("/audit")
def audit():
    return core.read_json(R / "data_audit.json", {})
