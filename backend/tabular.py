"""
Standalone single-modality models (HVF visual field, RNFL/GCC thickness).

These cohorts have no valid patient link to GAMMA or to each other, so they are
served as independent models on their own Mild/Moderate/Severe scale. Nothing in
here combines them with each other or with the fundus/OCT model.

Models are produced by training/train_tabular_encoders.py and loaded from
training/tabular_models/*.joblib. A missing file is reported as unavailable,
never replaced by a made-up prediction. The files are scikit-learn pickles:
only load ones you trained yourself, with the scikit-learn version in
requirements.txt.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np

MODELS_DIR = Path(__file__).resolve().parent.parent / "training" / "tabular_models"
COHORTS = ("hvf", "rnfl_gcc")

_bundles: dict[str, dict[str, Any]] = {}
_errors: dict[str, str] = {}


def load_all() -> dict:
    _bundles.clear()
    _errors.clear()
    for name in COHORTS:
        path = MODELS_DIR / f"{name}.joblib"
        try:
            _bundles[name] = joblib.load(path)
        except Exception as e:  # noqa: BLE001 - reported verbatim via /api/health
            _errors[name] = f"{type(e).__name__}: {e}"
    return {"loaded": sorted(_bundles), "errors": dict(_errors)}


def is_ready(name: str) -> bool:
    return name in _bundles


def schema() -> dict:
    """What the UI needs to render a form: fields, units, typical ranges, reliability."""
    out = {}
    for name, b in _bundles.items():
        out[name] = {
            "title": b["title"],
            "version": b["version"],
            "class_names": b["class_names"],
            "n_train": b["n_train"],
            "split": b["split"],
            "reliability": b["reliability"],
            "features": [
                {
                    "key": f,
                    "label": b["feature_meta"][f]["label"],
                    "unit": b["feature_meta"][f]["unit"],
                    "min": b["train_min"][f],
                    "max": b["train_max"][f],
                    "median": b["train_median"][f],
                }
                for f in b["features"]
            ],
        }
    return out


def predict(name: str, values: dict[str, float | None]) -> dict:
    b = _bundles[name]
    feats: list[str] = b["features"]
    unknown = sorted(set(values) - set(feats))
    if unknown:
        raise ValueError(f"unknown feature(s) for {name!r}: {unknown}")

    row, imputed, out_of_range = [], [], []
    for f in feats:
        v = values.get(f)
        if v is None:
            row.append(np.nan)
            imputed.append(f)
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"{f}: must be a finite number")
        row.append(float(v))
        lo, hi = b["train_min"][f], b["train_max"][f]
        if v < lo or v > hi:
            out_of_range.append({"feature": f, "value": v, "train_min": lo, "train_max": hi})

    if len(imputed) > len(feats) // 2:
        raise ValueError(f"too many missing fields ({len(imputed)}/{len(feats)}); provide at least half")

    pipe = b["pipeline"]
    X = np.array([row], dtype=float)
    probs = pipe.predict_proba(X)[0]
    classes = b["class_names"]
    k = int(np.argmax(probs))

    # Exact linear explanation: coefficient x standardised value, for the predicted class.
    z = pipe.named_steps["scale"].transform(pipe.named_steps["impute"].transform(X))[0]
    contrib = pipe.named_steps["clf"].coef_[k] * z
    order = np.argsort(-np.abs(contrib))[:4]
    drivers = [
        {
            "feature": feats[i],
            "label": b["feature_meta"][feats[i]]["label"],
            "contribution": round(float(contrib[i]), 3),
            "direction": "toward" if contrib[i] > 0 else "away from",
            "imputed": feats[i] in imputed,
        }
        for i in order
    ]

    return {
        "success": True,
        "cohort": name,
        "title": b["title"],
        "model_version": b["version"],
        "prediction": classes[k],
        "confidence": round(float(probs[k]), 4),
        "probabilities": {c: round(float(p), 4) for c, p in zip(classes, probs)},
        "drivers": drivers,
        "imputed_features": imputed,
        "out_of_range": out_of_range,
        "reliability": b["reliability"],
        "split": b["split"],
    }
