"""
Export the website's results data straight from the CV summaries.

Why this exists: the website used to hard-code metrics by hand, and the
/results page silently drifted behind the real best model (it still showed the
ResNet18 baseline after EXP-05 improved accuracy 0.731 -> 0.820). Numbers are
now *computed* from `results/**/summary.json`; only the human-written labels
and the adopt/reject decisions (copied from EXPERIMENTS.md) live in this file.

    python scripts/export_site_results.py            # (re)write the JSON
    python scripts/export_site_results.py --check    # exit 1 if JSON is stale (CI)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "website" / "src" / "lib" / "results.generated.json"

METRICS = [
    "accuracy",
    "balanced_accuracy",
    "macro_f1",
    "roc_auc_ovr_macro",
    "cohen_kappa",
    "quadratic_weighted_kappa",
]

# The architecture-freeze configuration (PROGRESS.md, "Current best frozen
# architecture"). This is the model the headline numbers describe.
HEADLINE_ID = "fusion_effnetb0_v1"

# Human-written context. Decisions are copied from the "### Decision" section
# of each experiment in EXPERIMENTS.md - they are NOT inferred from the numbers.
LADDER = [
    dict(
        id="fusion_baseline_v1", exp="EXP-01", dir="cv_fusion_baseline_v1",
        label="Baseline fusion",
        change="ResNet18 fundus + ResNet18 OCT encoders, 8 OCT slices, cross-modal Transformer fusion.",
        decision="reference",
    ),
    dict(
        id="fusion_2p5d_v1", exp="EXP-02", dir="cv_fusion_2p5d_v1",
        label="OCT 2.5D",
        change="Neighbouring B-scans [i-1, i, i+1] stacked as 3 channels per OCT slice.",
        decision="inconclusive",
        note="Accuracy-family metrics slightly lower; ROC-AUC/QWK tied with lower variance. Not adopted.",
    ),
    dict(
        id="fusion_single_12s_v1", exp="EXP-03", dir="cv_fusion_single_12s_v1",
        label="12 OCT slices",
        change="Raise OCT slice count from 8 to 12.",
        decision="rejected",
        note="Worse on all 6 metrics, with wider fold-to-fold spread.",
    ),
    dict(
        id="fusion_single_16s_v1", exp="EXP-04", dir="cv_fusion_single_16s_v1",
        label="16 OCT slices",
        change="Raise OCT slice count from 8 to 16.",
        decision="rejected",
        note="Monotonically worse than 12 and 8 slices on every metric.",
    ),
    dict(
        id="fusion_effnetb0_v1", exp="EXP-05", dir="cv_fusion_effnetb0_v1",
        label="EfficientNet-B0 fundus",
        change="Swap the fundus encoder ResNet18 -> EfficientNet-B0 (4.0M vs 11.2M parameters).",
        decision="adopted",
        note="Improved every metric and every fold for accuracy / macro-F1 / ROC-AUC. Frozen as the best configuration.",
    ),
    dict(
        id="fusion_token_v1", exp="EXP-06", dir="cv_fusion_token_v1",
        label="Token-level fusion",
        change="Spatial fundus tokens + per-slice OCT tokens into a cross-modal Transformer.",
        decision="inconclusive",
        note="QWK/ROC-AUC up, but macro-F1/balanced accuracy down and variance roughly doubled. Not adopted.",
    ),
]

MODALITY_ABLATION = [
    ("fundus", "Fundus only"),
    ("oct", "OCT only"),
    ("fusion", "Fusion (fundus + OCT)"),
]


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _metrics(block: dict) -> dict:
    out = {}
    for m in METRICS:
        if m in block:
            out[m] = {"mean": round(block[m]["mean"], 4), "std": round(block[m]["std"], 4)}
    return out


STANDALONE = [
    ("hvf", "Visual field (HVF)", "Mild / Moderate / Severe"),
    ("rnfl_gcc", "RNFL / GCC thickness", "Mild / Moderate / Severe"),
]


def _standalone() -> list:
    out = []
    for key, label, scale in STANDALONE:
        d = _load(ROOT / "results" / "tabular" / key / "summary.json")
        meta = d["meta"]
        out.append({
            "key": key,
            "label": label,
            "scale": scale,
            "split": meta["split"],
            "nTrain": meta["n_train"],
            "reliability": meta["reliability"],
            "source": f"results/tabular/{key}/summary.json",
            "metrics": _metrics(d["tabular"]),
        })
    return out


def build() -> dict:
    ladder = []
    folds_for_headline: dict = {}
    for item in LADDER:
        summary = _load(ROOT / "results" / item["dir"] / "summary.json")["fusion"]
        entry = {k: v for k, v in item.items() if k != "dir"}
        entry["source"] = f"results/{item['dir']}/summary.json"
        entry["metrics"] = _metrics(summary)
        ladder.append(entry)
        if item["id"] == HEADLINE_ID:
            folds_for_headline = {
                m: [round(v, 4) for v in summary[m]["values_per_fold"]]
                for m in ("accuracy", "macro_f1", "roc_auc_ovr_macro")
            }

    headline = next(e for e in ladder if e["id"] == HEADLINE_ID)

    cv = _load(ROOT / "results" / "cv" / "summary.json")
    modality = [
        {"key": key, "label": label, "metrics": _metrics(cv[key])}
        for key, label in MODALITY_ABLATION
    ]

    return {
        "_comment": "GENERATED by scripts/export_site_results.py - do not edit by hand.",
        "headline": {
            **headline,
            "perFold": folds_for_headline,
            "numFolds": 5,
            "numPatients": 100,
        },
        "ladder": ladder,
        "modalityAblation": modality,
        "modalityAblationSource": "results/cv/summary.json",
        "standalone": _standalone(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if the generated JSON is out of date")
    args = ap.parse_args()

    text = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print(f"{OUT.relative_to(ROOT)} is stale - run scripts/export_site_results.py", file=sys.stderr)
            return 1
        print("results.generated.json is up to date")
        return 0

    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
