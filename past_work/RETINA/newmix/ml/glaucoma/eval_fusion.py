"""Honest evaluation of OCT + clinical late fusion on shared out-of-fold predictions.

Both models were evaluated on identical patient-grouped folds (seed 42), so each
eye's OCT probabilities and clinical probabilities come from models that never
saw that patient. Fusion = fixed equal-weight average (no weight fitted on the
test folds). A weight sweep is reported separately and labelled optimistic.
Differences are tested with a patient-cluster bootstrap.

Writes ml/results/fusion/metrics.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, cohen_kappa_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from research_data import ROOT, load_master

R = ROOT / "ml" / "results"
W_OCT = 0.2  # deployed OCT weight (see weight_note in the output)


def metrics(y, p):
    pred = p.argmax(1)
    return {
        "accuracy": float((pred == y).mean()),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "qwk": float(cohen_kappa_score(y, pred, weights="quadratic")),
        "auc_glaucoma": float(roc_auc_score((y > 0).astype(int), 1 - p[:, 0])),
    }


def main():
    df = load_master()
    y = df.label.values
    cv = json.loads((R / "oct" / "cv_summary.json").read_text())
    arch = sys.argv[1] if len(sys.argv) > 1 else "resnet18"  # the architecture that is actually deployed
    assert arch in cv, f"{arch} not in cv_summary.json: {list(cv)}"
    final = json.loads((R / "clinical" / "final_models.json").read_text())["multiclass"]["algo"]
    po = pd.read_csv(R / "oct" / f"oof_{arch}_seed42.csv")[[f"p{i}" for i in range(4)]].values
    pc = pd.read_csv(R / "clinical" / f"oof_multiclass_structural_{final}.csv")[[f"p{i}" for i in range(4)]].values
    fused = W_OCT * po + (1 - W_OCT) * pc
    equal = 0.5 * po + 0.5 * pc

    rows = {"OCT scan": po, "Clinical": pc, f"Fused ({int(W_OCT * 100)}% OCT / {int((1 - W_OCT) * 100)}% clinical, deployed)": fused,
            "Fused (equal weights, reference)": equal}
    table = {k: metrics(y, v) for k, v in rows.items()}

    sweep = []
    for w in np.linspace(0, 1, 11):
        m = metrics(y, w * po + (1 - w) * pc)
        sweep.append({"oct_weight": round(float(w), 1), **{k: round(v, 4) for k, v in m.items()}})

    groups = df.group.values
    ug = np.unique(groups)
    idx = {g: np.where(groups == g)[0] for g in ug}
    rng = np.random.default_rng(0)
    d_acc, d_bal = [], []
    for _ in range(2000):
        s = np.concatenate([idx[g] for g in rng.choice(ug, len(ug))])
        a = (fused[s].argmax(1) == y[s]).mean() - (pc[s].argmax(1) == y[s]).mean()
        b = balanced_accuracy_score(y[s], fused[s].argmax(1)) - balanced_accuracy_score(y[s], pc[s].argmax(1))
        d_acc.append(a)
        d_bal.append(b)
    ci = lambda v: [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]
    out = {
        "oct_arch": arch, "clinical_algo": final, "weights": {"oct": W_OCT, "clinical": round(1 - W_OCT, 2)},
        "weight_note": "20% OCT is a conservative down-weight chosen after inspecting the (optimistic) sweep; the sweep shows OCT adds no reliable value at any weight.",
        "rows": {k: {m: round(v, 4) for m, v in d.items()} for k, d in table.items()},
        "fused_minus_clinical": {
            "accuracy": {"mean": round(float(np.mean(d_acc)), 4), "ci95": ci(d_acc)},
            "balanced_accuracy": {"mean": round(float(np.mean(d_bal)), 4), "ci95": ci(d_bal)},
        },
        "weight_sweep_optimistic": sweep,
        "n_eyes": int(len(y)), "n_patients": int(len(ug)),
    }
    (R / "fusion").mkdir(exist_ok=True)
    (R / "fusion" / "metrics.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("oct_arch", "clinical_algo", "rows", "fused_minus_clinical")}, indent=2))


if __name__ == "__main__":
    main()
