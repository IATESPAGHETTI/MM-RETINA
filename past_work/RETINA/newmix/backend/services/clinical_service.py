"""Clinical-feature glaucoma risk model + the MD staging rule.

`predict` uses only the structural feature set (see docs/DATA_AUDIT.md for why
HVF MD is not a model input). `stage_from_md` is a deterministic rule that
reproduces how the cohort's labels were defined; it is presented as a rule.
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd

from core import MODELS_DIR
from services import defer_service

_models: dict = {}
_error: str | None = None

FIELD_LABELS = {
    "Age": "Age (years)", "Gender": "Sex (1 = male)", "IOP": "IOP (mmHg)", "CDR": "Cup-to-disc ratio",
    "RNFL_Avg": "RNFL average (µm)", "RNFL_S": "RNFL superior", "RNFL_I": "RNFL inferior",
    "RNFL_N": "RNFL nasal", "RNFL_T": "RNFL temporal", "GCC_Avg": "GCC average (µm)",
    "GCC_SUPERIOR": "GCC superior", "GCC_INFERIOR": "GCC inferior", "GCC_ST": "GCC supero-temporal",
    "GCC_SN": "GCC supero-nasal", "GCC_IT": "GCC infero-temporal", "GCC_IN": "GCC infero-nasal",
}


def load() -> dict:
    global _error
    try:
        for task in ("binary", "multiclass"):
            _models[task] = joblib.load(MODELS_DIR / f"clinical_{task}.joblib")
        _error = None
    except Exception as e:  # noqa: BLE001
        _error = f"{type(e).__name__}: {e}"
    return status()


def status() -> dict:
    return {"ready": len(_models) == 2, "error": _error,
            "algos": {k: v["algo"] for k, v in _models.items()}}


def feature_spec() -> list[dict]:
    b = _models["binary"]
    return [{"key": f, "label": FIELD_LABELS.get(f, f), "min": b["ranges"][f][0], "max": b["ranges"][f][1],
             "median": b["medians"][f]} for f in b["features"]]


def stage_from_md(md: float) -> dict:
    stage = "Mild" if md > -6 else ("Moderate" if md > -12 else "Severe")
    return {"md_db": md, "stage": stage, "rule": "Mild > -6 dB; Moderate -6 to -12 dB; Severe < -12 dB",
            "note": "Stages an eye that already has glaucoma. It cannot tell a healthy eye from a mild one."}


def _row(bundle, values: dict) -> pd.DataFrame:
    row = {f: values.get(f, np.nan) if values.get(f) is not None else np.nan for f in bundle["features"]}
    return pd.DataFrame([row])


def predict(values: dict) -> dict:
    if len(_models) < 2:
        raise RuntimeError(_error or "clinical models not loaded")
    given = [f for f in _models["binary"]["features"] if values.get(f) is not None]
    if len(given) < 4:
        raise ValueError("provide at least 4 measurements (RNFL/GCC values are the most informative)")
    out = {"fields_provided": len(given), "fields_total": len(_models["binary"]["features"])}
    for task in ("binary", "multiclass"):
        b = _models[task]
        X = _row(b, values)
        p = b["model"].predict_proba(X)[0]
        out[task] = {"classes": b["classes"], "probabilities": {c: round(float(v), 4) for c, v in zip(b["classes"], p)},
                     "prediction": b["classes"][int(p.argmax())], "confidence": round(float(p.max()), 4)}
    # Per-feature effect: how much the predicted-class probability moves when one
    # supplied value is replaced by the cohort median (works for any model type).
    b = _models["multiclass"]
    base_p = b["model"].predict_proba(_row(b, values))[0]
    cls = int(base_p.argmax())
    effects = []
    for f in given:
        alt = dict(values)
        alt[f] = b["medians"][f]
        d = float(base_p[cls] - b["model"].predict_proba(_row(b, alt))[0][cls])
        effects.append({"feature": f, "label": FIELD_LABELS.get(f, f), "value": values[f], "effect": round(d, 4)})
    out["drivers"] = sorted(effects, key=lambda e: -abs(e["effect"]))[:6]
    out["p_glaucoma"] = out["binary"]["probabilities"]["Glaucoma"]
    out["defer"] = defer_service.decide("clinical", out["multiclass"]["confidence"])
    return out
