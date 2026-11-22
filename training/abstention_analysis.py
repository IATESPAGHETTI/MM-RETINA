"""
Recipe-level abstention ("Needs review") analysis from nested-CV out-of-fold predictions.

Question: if the model defers its least-confident cases to a human, how does
accuracy on the answered cases change as coverage drops?

Honest cut-off selection (no threshold ever sees the cases it is applied to):
for every outer fold f, the confidence cut-off for target coverage c is the
(1-c) quantile of max-probability computed on the OTHER outer folds' out-of-fold
predictions (same seed), then applied to fold f. Patients are disjoint across
folds, so cut-off data and evaluation data never overlap.

This is RECIPE-level evidence (EfficientNet-B0 + ResNet18, 8 slices, vector
fusion, epoch chosen on inner-val). It is not a claim about any particular
saved weights file.

Usage (from training/):
    python abstention_analysis.py [--model fusion]
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
GRADES = ["normal", "early", "progressive"]
TARGET_COVERAGES = [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.6, 0.5]


def load(path: Path, model: str) -> list[dict]:
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["model"] != model:
                continue
            p = np.array([float(r[f"prob_{g}"]) for g in GRADES])
            rows.append({"pid": r["patient_id"], "fold": int(r["fold"]), "seed": int(r["seed"]),
                         "conf": float(p.max()), "correct": r["true_label"] == r["pred_label"],
                         "true": r["true_label"]})
    return rows


def apply_cutoffs(rows: list[dict], coverage: float) -> list[bool]:
    """answered[i] for each row, with cut-offs chosen leave-one-fold-out per seed."""
    answered = [True] * len(rows)
    if coverage >= 1.0:
        return answered
    by_seed = defaultdict(list)
    for i, r in enumerate(rows):
        by_seed[r["seed"]].append(i)
    for seed, idx in by_seed.items():
        folds = sorted({rows[i]["fold"] for i in idx})
        for f in folds:
            other = [rows[i]["conf"] for i in idx if rows[i]["fold"] != f]
            cut = float(np.quantile(other, 1.0 - coverage))
            for i in idx:
                if rows[i]["fold"] == f:
                    answered[i] = rows[i]["conf"] >= cut
    return answered


def metrics(rows, answered):
    n = len(rows)
    a = [r for r, k in zip(rows, answered) if k]
    d = [r for r, k in zip(rows, answered) if not k]
    return {
        "coverage": len(a) / n,
        "acc_answered": float(np.mean([r["correct"] for r in a])) if a else float("nan"),
        "acc_deferred": float(np.mean([r["correct"] for r in d])) if d else float("nan"),
        "early_answered_share": (sum(r["true"] == "early" for r in a) / max(1, sum(r["true"] == "early" for r in rows))),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="fusion")
    ap.add_argument("--pred", default=str(REPO_ROOT / "results" / "nested_cv_v1" / "per_eye_predictions.csv"))
    ap.add_argument("--out", default=str(REPO_ROOT / "results" / "nested_cv_v1" / "abstention_recipe.json"))
    ap.add_argument("--n-boot", type=int, default=2000)
    args = ap.parse_args()

    rows = load(Path(args.pred), args.model)
    if not rows:
        raise SystemExit(f"no rows for model={args.model}")
    rng = np.random.default_rng(0)
    pids = sorted({r["pid"] for r in rows})
    seeds = sorted({r["seed"] for r in rows})

    curve = []
    for cov in TARGET_COVERAGES:
        answered = apply_cutoffs(rows, cov)
        point = metrics(rows, answered)
        # patient-level bootstrap over the same (fixed) answered/deferred decisions
        idx_by_pid = defaultdict(list)
        for i, r in enumerate(rows):
            idx_by_pid[r["pid"]].append(i)
        boots = {"coverage": [], "acc_answered": []}
        for _ in range(args.n_boot):
            samp = [i for p in rng.choice(pids, size=len(pids), replace=True) for i in idx_by_pid[p]]
            sub = [rows[i] for i in samp]
            sa = [answered[i] for i in samp]
            m = metrics(sub, sa)
            boots["coverage"].append(m["coverage"])
            boots["acc_answered"].append(m["acc_answered"])
        point["target_coverage"] = cov
        point["acc_answered_ci95"] = [float(np.nanpercentile(boots["acc_answered"], 2.5)),
                                      float(np.nanpercentile(boots["acc_answered"], 97.5))]
        point["coverage_ci95"] = [float(np.percentile(boots["coverage"], 2.5)),
                                  float(np.percentile(boots["coverage"], 97.5))]
        curve.append(point)

    out = {
        "evidence_level": "recipe",
        "claim": "Estimates how the EXP-N01 recipe behaves; NOT calibration of any specific saved checkpoint.",
        "model": args.model,
        "seeds": seeds,
        "n_patients": len(pids),
        "cutoff_method": "per seed, leave-one-outer-fold-out quantile of max-probability; disjoint patients between cutoff data and evaluation data",
        "confidence": "max softmax probability",
        "bootstrap": {"unit": "patient", "resamples": args.n_boot},
        "curve": curve,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"{'target':>7} {'coverage':>9} {'acc_answered [95% CI]':>28} {'acc_deferred':>13}")
    for p in curve:
        lo, hi = p["acc_answered_ci95"]
        print(f"{p['target_coverage']:>7.2f} {p['coverage']:>9.3f} {p['acc_answered']:>10.3f} [{lo:.3f}, {hi:.3f}] {p['acc_deferred']:>13.3f}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
