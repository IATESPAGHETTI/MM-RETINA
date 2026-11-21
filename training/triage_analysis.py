"""
Triage analysis ("teleophthalmology" story): screen with the cheap fundus-only model,
and send only uncertain eyes for OCT, where the fundus+OCT fusion model decides.

For each eye (nested-CV out-of-fold predictions, same patients/folds/seed):
    fundus confidence >= t  -> answer = fundus-only prediction  (no OCT needed)
    fundus confidence <  t  -> "send for OCT"; answer = fusion prediction
t is swept; this is a DESCRIPTIVE trade-off curve, not a tuned/validated operating point.
Only seeds for which BOTH models have all outer folds are used.

Usage (from training/):  python triage_analysis.py
Outputs: results/nested_cv_v1/triage_analysis.json and triage_curve.png
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "results" / "nested_cv_v1"
GRADES = ["normal", "early", "progressive"]
K = 5


def load_model(model: str) -> dict[tuple[int, str], dict]:
    """(seed, patient) -> row; only seeds with all K folds present."""
    rows: dict[tuple[int, str], dict] = {}
    seeds = defaultdict(set)
    for p in (OUT / model).glob("seed*/fold*/predictions.csv"):
        seed = int(p.parent.parent.name.removeprefix("seed"))
        fold = int(p.parent.name.removeprefix("fold"))
        seeds[seed].add(fold)
        with open(p, newline="") as f:
            for r in csv.DictReader(f):
                probs = np.array([float(r[f"prob_{g}"]) for g in GRADES])
                rows[(seed, r["patient_id"])] = {
                    "seed": seed, "pid": r["patient_id"], "true": r["true_label"],
                    "pred": r["pred_label"], "conf": float(probs.max()),
                }
    complete = {s for s, folds in seeds.items() if len(folds) == K}
    return {k: v for k, v in rows.items() if k[0] in complete}


def evaluate(pairs: list[tuple[dict, dict]], t: float) -> dict:
    final, to_oct = [], 0
    for fund, fus in pairs:
        if fund["conf"] >= t:
            final.append((fund["true"], fund["pred"]))
        else:
            to_oct += 1
            final.append((fus["true"], fus["pred"]))
    n = len(final)
    early = [(a, b) for a, b in final if a == "early"]
    return {
        "threshold": t,
        "share_sent_for_oct": to_oct / n,
        "accuracy": sum(a == b for a, b in final) / n,
        "early_recall": sum(a == b for a, b in early) / len(early) if early else float("nan"),
    }


def main():
    fund, fus = load_model("fundus"), load_model("fusion")
    keys = sorted(set(fund) & set(fus))
    seeds = sorted({k[0] for k in keys})
    if not keys:
        raise SystemExit("no seeds with complete fundus AND fusion runs yet")
    pairs = [(fund[k], fus[k]) for k in keys]
    pids = sorted({k[1] for k in keys})
    by_pid = defaultdict(list)
    for (fu, fs) in pairs:
        by_pid[fu["pid"]].append((fu, fs))

    thresholds = [0.0] + [round(x, 2) for x in np.arange(0.40, 0.96, 0.05)] + [1.01]
    curve = [evaluate(pairs, t) for t in thresholds]

    rng = np.random.default_rng(0)
    def boot_acc(t, n=1000):
        vals = []
        for _ in range(n):
            samp = [pr for p in rng.choice(pids, size=len(pids), replace=True) for pr in by_pid[p]]
            vals.append(evaluate(samp, t)["accuracy"])
        return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]

    for pt in (curve[0], curve[-1]):
        pt["accuracy_ci95"] = boot_acc(pt["threshold"])
    # also CI for the middle operating points shown in the write-up
    for pt in curve[1:-1]:
        pt["accuracy_ci95"] = boot_acc(pt["threshold"], n=500)

    out = {
        "claim": "Descriptive triage trade-off on nested-CV out-of-fold predictions; not a tuned or validated operating point.",
        "seeds_used": seeds, "n_patients": len(pids),
        "rule": "fundus confidence >= t -> fundus answer; else send for OCT and use fusion answer",
        "fundus_only": curve[0], "fusion_for_all": curve[-1], "curve": curve,
    }
    (OUT / "triage_analysis.json").write_text(json.dumps(out, indent=2))

    print(f"seeds used: {seeds}  patients: {len(pids)}")
    print(f"{'t':>5} {'sent for OCT':>13} {'accuracy [95% CI]':>24} {'early recall':>13}")
    for p in curve:
        lo, hi = p["accuracy_ci95"]
        print(f"{p['threshold']:>5.2f} {p['share_sent_for_oct']:>13.1%} {p['accuracy']:>8.3f} [{lo:.3f}, {hi:.3f}] {p['early_recall']:>13.3f}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    xs = [p["share_sent_for_oct"] * 100 for p in curve]
    ys = [p["accuracy"] * 100 for p in curve]
    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=160)
    ax.plot(xs, ys, marker="o", color="#c8873a")
    ax.axhline(curve[0]["accuracy"] * 100, ls="--", color="#888", lw=1)
    ax.axhline(curve[-1]["accuracy"] * 100, ls="--", color="#888", lw=1)
    ax.text(1, curve[0]["accuracy"] * 100 + 0.8, "fundus only (no OCT)", fontsize=8, color="#555")
    ax.text(1, curve[-1]["accuracy"] * 100 + 0.8, "fusion for everyone (OCT for all)", fontsize=8, color="#555")
    ax.set_xlabel("Share of eyes sent for OCT (%)")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Triage: screen with fundus, send uncertain eyes for OCT", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "triage_curve.png")
    print("wrote triage_analysis.json and triage_curve.png")


if __name__ == "__main__":
    main()
