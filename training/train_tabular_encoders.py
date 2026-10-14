"""
Single-modality encoders for the cohorts that CANNOT be fused with GAMMA.

HVF (visual field) and RNFL/GCC (OCT thickness) share no valid patient/eye
link with GAMMA or with each other (see dataset/rnfl_gcc_provenance_audit.md),
so there is no honest joint model. Each gets its own standalone model, graded
on its own Mild/Moderate/Severe scale, and the product reports them as
separate pieces of evidence - never as one fused verdict.

Model: median-impute -> standardise -> multinomial logistic regression with
balanced class weights. Linear on purpose: the per-feature contribution
(coefficient x standardised value) is an exact, honest explanation, and on
~170 rows a bigger model has nothing to gain.

  HVF       C01b no-proxy features (md_db/psd_db/vfi_pct excluded: they are
            near-duplicates of the label-assignment criteria). 5-fold,
            patient-grouped.
  RNFL/GCC  13 numeric features. No patient ID exists, so 5-fold is plain
            stratified - every RNFL/GCC number is optimistic for that reason.

Writes results/tabular/<name>/summary.json (CV metrics, same schema as the
other summaries) and training/tabular_models/<name>.joblib (final fit on all
rows; small, tracked in git so the demo works on a fresh clone).

    python training/train_tabular_encoders.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    cohen_kappa_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from train_hvf_baseline import NUMERIC_FEATURES_NO_PROXY, load_dataset as load_hvf  # noqa: E402

MODELS_DIR = REPO_ROOT / "training" / "tabular_models"
RESULTS_DIR = REPO_ROOT / "results" / "tabular"
RNFL_GCC_CSV = REPO_ROOT / "dataset" / "rnfl_gcc_features.csv"
SEED = 42
N_FOLDS = 5
CLASS_NAMES = ["mild", "moderate", "severe"]

RNFL_GCC_FEATURES = [
    "Average_RNFL", "RNFL_Superior", "RNFL_Inferior", "RNFL_Nasal", "RNFL_Temporal",
    "Average_GCC", "GCC_Superior", "GCC_Inferior",
    "GCC_Supero_nasal", "GCC_Supero_temporal", "GCC_Infero_nasal", "GCC_Infero_temporal",
    "age",
]

# Plain-language labels + units shown in the UI form.
FEATURE_META = {
    "false_positive_pct": ("False positives", "%"),
    "false_negative_pct": ("False negatives", "%"),
    "fixation_loss_ratio": ("Fixation loss ratio", "0-1"),
    "test_duration_min": ("Test duration", "min"),
    "refraction_used": ("Refraction used", "D"),
    "age_years": ("Age", "years"),
    "Average_RNFL": ("Average RNFL", "µm"),
    "RNFL_Superior": ("RNFL superior", "µm"),
    "RNFL_Inferior": ("RNFL inferior", "µm"),
    "RNFL_Nasal": ("RNFL nasal", "µm"),
    "RNFL_Temporal": ("RNFL temporal", "µm"),
    "Average_GCC": ("Average GCC", "µm"),
    "GCC_Superior": ("GCC superior", "µm"),
    "GCC_Inferior": ("GCC inferior", "µm"),
    "GCC_Supero_nasal": ("GCC supero-nasal", "µm"),
    "GCC_Supero_temporal": ("GCC supero-temporal", "µm"),
    "GCC_Infero_nasal": ("GCC infero-nasal", "µm"),
    "GCC_Infero_temporal": ("GCC infero-temporal", "µm"),
    "age": ("Age", "years"),
}

COHORTS = {
    "hvf": {
        "title": "Visual field (HVF)",
        "features": NUMERIC_FEATURES_NO_PROXY,
        "split": "patient-grouped 5-fold (90 patients, 168 eyes)",
    },
    "rnfl_gcc": {
        "title": "RNFL / GCC thickness",
        "features": RNFL_GCC_FEATURES,
        "split": "plain stratified 5-fold (171 eyes, NO patient ID - optimistic)",
    },
}


def load(name: str) -> tuple[pd.DataFrame, np.ndarray | None]:
    if name == "hvf":
        df = load_hvf()
        return df, df["patient_id"].to_numpy()
    return pd.read_csv(RNFL_GCC_CSV), None


def make_pipeline() -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)),
    ])


def fold_metrics(y: np.ndarray, probs: np.ndarray) -> dict:
    pred = probs.argmax(1)
    return {
        "accuracy": accuracy_score(y, pred),
        "balanced_accuracy": balanced_accuracy_score(y, pred),
        "macro_f1": f1_score(y, pred, average="macro", zero_division=0),
        "roc_auc_ovr_macro": roc_auc_score(y, probs, multi_class="ovr", average="macro", labels=[0, 1, 2]),
        "cohen_kappa": cohen_kappa_score(y, pred),
        "quadratic_weighted_kappa": cohen_kappa_score(y, pred, weights="quadratic"),
    }


def reliability(auc: float, kappa: float) -> dict:
    """Tier from CV ROC-AUC. The thresholds are a stated convention, not a clinical standard."""
    if auc >= 0.85:
        tier, text = "strong", "Strong in cross-validation"
    elif auc >= 0.70:
        tier, text = "moderate", "Moderate in cross-validation"
    elif auc >= 0.60:
        tier, text = "weak", "Weak in cross-validation"
    else:
        tier, text = "chance", "No better than chance in cross-validation"
    return {
        "tier": tier,
        "label": text,
        "rule": "ROC-AUC >= 0.85 strong, >= 0.70 moderate, >= 0.60 weak, else no better than chance",
        "roc_auc": round(auc, 4),
        "kappa": round(kappa, 4),
    }


def run(name: str) -> None:
    cfg = COHORTS[name]
    feats = cfg["features"]
    df, groups = load(name)
    X = df[feats].to_numpy(dtype=float)
    y = df["severity_label"].to_numpy(dtype=int)

    splitter = (
        GroupKFold(n_splits=N_FOLDS).split(X, y, groups)
        if groups is not None
        else StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED).split(X, y)
    )
    per_fold = []
    for train, val in splitter:
        pipe = make_pipeline().fit(X[train], y[train])
        probs = np.zeros((len(val), 3))
        probs[:, pipe.named_steps["clf"].classes_] = pipe.predict_proba(X[val])
        per_fold.append(fold_metrics(y[val], probs))

    summary = {}
    for m in per_fold[0]:
        vals = [f[m] for f in per_fold]
        summary[m] = {"values_per_fold": vals, "mean": float(np.mean(vals)), "std": float(np.std(vals))}

    final = make_pipeline().fit(X, y)
    clf = final.named_steps["clf"]
    scaler = final.named_steps["scale"]
    imputer = final.named_steps["impute"]
    bundle = {
        "name": name,
        "title": cfg["title"],
        "features": feats,
        "feature_meta": {f: {"label": FEATURE_META[f][0], "unit": FEATURE_META[f][1]} for f in feats},
        "class_names": CLASS_NAMES,
        "pipeline": final,
        "train_min": df[feats].min().to_dict(),
        "train_max": df[feats].max().to_dict(),
        "train_median": dict(zip(feats, imputer.statistics_.tolist())),
        "n_train": int(len(df)),
        "split": cfg["split"],
        "reliability": reliability(summary["roc_auc_ovr_macro"]["mean"], summary["cohen_kappa"]["mean"]),
        "version": f"{name}_lr_v1",
    }
    assert list(clf.classes_) == [0, 1, 2], "all three severity classes must be present"
    assert scaler.scale_.shape[0] == len(feats)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, MODELS_DIR / f"{name}.joblib")
    out = RESULTS_DIR / name
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(
        json.dumps({"tabular": summary, "meta": {k: bundle[k] for k in ("title", "split", "n_train", "reliability", "version")}},
                   indent=2),
        encoding="utf-8",
    )
    s = summary
    print(f"{name}: acc {s['accuracy']['mean']:.3f}±{s['accuracy']['std']:.3f}  "
          f"AUC {s['roc_auc_ovr_macro']['mean']:.3f}  kappa {s['cohen_kappa']['mean']:.3f}  "
          f"QWK {s['quadratic_weighted_kappa']['mean']:.3f}  -> {bundle['reliability']['label']}")


if __name__ == "__main__":
    for n in COHORTS:
        run(n)
