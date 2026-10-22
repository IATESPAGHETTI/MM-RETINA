"""Does restructuring the clinical model help? Patient-grouped CV, seeds 42/43/44.

  flat          one 4-class model (current)
  hierarchical  detect (glaucoma vs control) then stage (Mild/Moderate/Severe, trained on glaucoma eyes only)
  abstention    accuracy when the model may defer its least-confident cases to a visual-field test

Writes ml/results/explore/triage.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import balanced_accuracy_score, roc_auc_score, roc_curve

sys.path.insert(0, str(Path(__file__).parent))
from research_data import ROOT, STRUCT_FEATURES, assign_folds, load_master
from train_clinical import make_model, score

OUT = ROOT / "ml" / "results" / "explore"


def oof_flat(df, folds, seed):
    y = df.label.values
    oof = np.zeros((len(df), 4))
    for f in range(5):
        tr, te = folds != f, folds == f
        oof[te] = make_model("rf", seed).fit(df.loc[tr, STRUCT_FEATURES], y[tr]).predict_proba(df.loc[te, STRUCT_FEATURES])
    return oof


def oof_hier(df, folds, seed, det="logreg", stg="rf"):
    y = df.label.values
    oof = np.zeros((len(df), 4))
    for f in range(5):
        tr, te = folds != f, folds == f
        Xtr, Xte = df.loc[tr, STRUCT_FEATURES], df.loc[te, STRUCT_FEATURES]
        pg = make_model(det, seed).fit(Xtr, (y[tr] > 0).astype(int)).predict_proba(Xte)[:, 1]
        g = tr & (y > 0)
        ps = make_model(stg, seed).fit(df.loc[g, STRUCT_FEATURES], y[g] - 1).predict_proba(Xte)
        oof[te] = np.column_stack([1 - pg, pg[:, None] * ps])
    return oof


def coverage_table(y, p):
    conf = p.max(1)
    order = np.argsort(-conf)
    rows = {}
    for cov in (1.0, 0.8, 0.6):
        k = int(round(cov * len(y)))
        idx = order[:k]
        rows[f"{int(cov * 100)}%"] = {"accuracy": round(float((p[idx].argmax(1) == y[idx]).mean()), 4),
                                     "balanced_accuracy": round(float(balanced_accuracy_score(y[idx], p[idx].argmax(1))), 4)}
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_master()
    y = df.label.values
    res: dict = {}
    for name, fn in (("flat", oof_flat), ("hierarchical", oof_hier)):
        runs, covs, sens = [], [], []
        for seed in (42, 43, 44):
            folds = assign_folds(df, 5, seed)
            p = fn(df, folds, seed)
            runs.append(score(y, p, "multiclass"))
            covs.append(coverage_table(y, p))
            fpr, tpr, _ = roc_curve((y > 0).astype(int), 1 - p[:, 0])
            sens.append(float(np.interp(0.10, fpr, tpr)))  # sensitivity at 90% specificity
        res[name] = {
            "accuracy": round(float(np.mean([r["accuracy"] for r in runs])), 4),
            "balanced_accuracy": round(float(np.mean([r["balanced_accuracy"] for r in runs])), 4),
            "balanced_accuracy_sd": round(float(np.std([r["balanced_accuracy"] for r in runs])), 4),
            "qwk": round(float(np.mean([r["qwk"] for r in runs])), 4),
            "auc_glaucoma": round(float(np.mean([roc_auc_score((y > 0).astype(int), 1 - fn(df, assign_folds(df, 5, 42), 42)[:, 0])])), 4),
            "sensitivity_at_90_specificity": round(float(np.mean(sens)), 4),
            "per_class_recall": {c: round(float(np.mean([r["per_class_recall"][c] for r in runs])), 3) for c in runs[0]["per_class_recall"]},
            "coverage": {k: {m: round(float(np.mean([c[k][m] for c in covs])), 4) for m in covs[0][k]} for k in covs[0]},
        }
        print(name, json.dumps(res[name]), flush=True)
    (OUT / "triage.json").write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
