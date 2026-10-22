"""Aggregates the MM-RETINA / GAMMA 5-fold CV results into ml/results/gamma_cv_summary.json.

    python ml/results/make_gamma_summary.py <path to MM-RETINA results/ directory>

Reads only the per-fold metrics.json files the original runs wrote.
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\ASUS\Downloads\prj4\results")
OUT = Path(__file__).parent / "gamma_cv_summary.json"
RUNS = {  # label -> (directory, modality sub-folder or None)
    "fundus": ("cv", "fundus"), "oct": ("cv", "oct"), "fusion": ("cv", "fusion"),
    "fusion_effnetb0": ("cv_fusion_effnetb0_v1", None),
}


def agg(files):
    ms = [json.load(open(f))["metrics"] for f in sorted(files)]
    out = {"folds": len(ms)}
    for k, name in (("accuracy", "accuracy"), ("balanced_accuracy", "balanced_accuracy"),
                    ("macro_f1", "macro_f1"), ("roc_auc_ovr_macro", "auc")):
        v = [m[k] for m in ms if k in m]
        if v:
            out[name] = {"mean": round(float(np.mean(v)), 4), "sd": round(float(np.std(v)), 4)}
    return out


res = {}
for label, (d, sub) in RUNS.items():
    pat = f"{SRC / d}/{sub + '/' if sub else ''}fold*/metrics.json"
    files = glob.glob(pat)
    if not files:
        files = glob.glob(f"{SRC / d}/**/fold*/metrics.json", recursive=True)
    if files:
        res[label] = agg(files)
res["classes"] = ["Normal", "Early", "Progressive"]
res["dataset"] = "GAMMA (public), 300 eyes, patient-level 5-fold CV"
OUT.write_text(json.dumps(res, indent=2))
print(json.dumps(res, indent=2))
