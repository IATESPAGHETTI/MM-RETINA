"""Confidence cut-offs for "defer to a visual-field test", from out-of-fold predictions only.

For each head (clinical RF, OCT ResNet18, fused 20/80) the cut-off is the 20th percentile of the
model's own top-class probability on held-out eyes, so the model answers ~80% of cases and defers the
least confident fifth. Writes ml/results/clinical/defer.json, which the API reads.

The deployed models are refit on all 303 eyes; their confidence on genuinely new eyes should resemble the
out-of-fold confidence used here, but this is an assumption, not something measured on new patients.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score

sys.path.insert(0, str(Path(__file__).parent))
from research_data import ROOT, STRUCT_FEATURES, assign_folds, load_master
from train_clinical import make_model

R = ROOT / "ml" / "results"
COVERAGE = 0.80
W_OCT = json.loads((R / "fusion" / "metrics.json").read_text())["weights"]["oct"]


def head_stats(y, p, name):
    conf = p.max(1)
    t = float(np.quantile(conf, 1 - COVERAGE))
    ans = conf >= t
    pred = p.argmax(1)
    table = {}
    order = np.argsort(-conf)
    for cov in (1.0, 0.8, 0.6):
        idx = order[: int(round(cov * len(y)))]
        table[f"{int(cov * 100)}%"] = {"accuracy": round(float((pred[idx] == y[idx]).mean()), 4),
                                      "balanced_accuracy": round(float(balanced_accuracy_score(y[idx], pred[idx])), 4)}
    return {
        "head": name, "threshold": round(t, 4), "target_coverage": COVERAGE,
        "coverage_achieved": round(float(ans.mean()), 4),
        "accuracy_answered": round(float((pred[ans] == y[ans]).mean()), 4),
        "accuracy_deferred": round(float((pred[~ans] == y[~ans]).mean()), 4),
        "n_deferred": int((~ans).sum()), "n": int(len(y)), "table": table,
    }


def clinical_oof(df, seed):
    y = df.label.values
    folds = assign_folds(df, 5, seed)
    oof = np.zeros((len(df), 4))
    for f in range(5):
        tr, te = folds != f, folds == f
        oof[te] = make_model("rf", seed).fit(df.loc[tr, STRUCT_FEATURES], y[tr]).predict_proba(df.loc[te, STRUCT_FEATURES])
    return oof


def main():
    df = load_master()
    cols = [f"p{i}" for i in range(4)]
    ys, pcs, pos = [], [], []
    for seed in (42, 43, 44):  # same folds for both models within a seed, so the fused OOF is honest
        pcs.append(clinical_oof(df, seed))
        pos.append(pd.read_csv(R / "oct" / f"oof_resnet18_seed{seed}.csv")[cols].values)
        ys.append(df.label.values)
    y, pc, po = np.concatenate(ys), np.concatenate(pcs), np.concatenate(pos)
    out = {
        "clinical": head_stats(y, pc, "clinical"),
        "oct": head_stats(y, po, "oct"),
        "fused": head_stats(y, W_OCT * po + (1 - W_OCT) * pc, "fused"),
        "note": "Cut-offs are the 20th percentile of out-of-fold top-class probability, pooled over 3 seeds of patient-grouped 5-fold CV.",
    }
    (R / "clinical" / "defer.json").write_text(json.dumps(out, indent=2))
    for k in ("clinical", "oct", "fused"):
        s = out[k]
        print(f"{k:9s} t={s['threshold']:.3f} answered {s['coverage_achieved']:.0%} acc={s['accuracy_answered']:.3f} | deferred acc={s['accuracy_deferred']:.3f} | 100%/80%/60% acc = " + " / ".join(f"{s['table'][c]['accuracy']:.3f}" for c in ('100%', '80%', '60%')))


if __name__ == "__main__":
    main()
