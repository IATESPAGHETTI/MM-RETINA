"""
Nested (honest) cross-validation for the GAMMA multimodal model  (EXP-N01).

Why this exists
---------------
cross_validate.py picks each fold's best epoch (checkpoint) using the SAME
validation fold it then reports metrics on. That slightly flatters every
reported number. Here, for every OUTER fold:

  * the outer-train patients are split again, patient-level and
    grade-stratified, into inner-train / inner-val;
  * training, early stopping and checkpoint selection use ONLY inner-val;
  * the selected checkpoint is scored ONCE on the outer-val patients.

Outer folds are identical to EXP-05's (same `make_folds`, seed 42, k=5), so
results are directly comparable. Only the training seed and the inner split
change across --seeds. Hyper-parameters are fixed at the EXP-05 values
(no grid search); only the training epoch is selected inside the fold.

Saves per-eye predictions (probabilities + labels + fold + seed + model) so
later analysis (Early-recall error study, abstention curve, demo cases)
never needs a re-run.

Usage (run from the training/ directory, like the other scripts):
    python nested_cv.py --smoke-test
    python nested_cv.py --manifest <abs path to gamma_manifest.json> \
        --modalities fusion --seeds 42 43 44
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from torch.utils.data import DataLoader

from cross_validate import make_folds
from data import GRADE_NAMES, GammaMultimodalDataset
from evaluate import run_evaluation
from train_multimodal import build_model, log_config, run_training

REPO_ROOT = Path(__file__).resolve().parent.parent
MODALITIES = ["fundus", "oct", "fusion"]
EARLY, PROGRESSIVE = "early", "progressive"


def patient_grade(manifest: list[dict]) -> dict[str, str]:
    by_patient: dict[str, list[str]] = defaultdict(list)
    for r in manifest:
        by_patient[r["patient_id"]].append(r["grade"])
    return {pid: Counter(gs).most_common(1)[0][0] for pid, gs in by_patient.items()}


def inner_split(train_pids: list[str], grade_of: dict[str, str], seed: int, frac: float = 0.2) -> set[str]:
    """Grade-stratified patient-level inner-validation set (~frac of train_pids)."""
    rng = random.Random(seed)
    by_grade: dict[str, list[str]] = defaultdict(list)
    for pid in sorted(train_pids):
        by_grade[grade_of[pid]].append(pid)
    inner_val: set[str] = set()
    for grade, pids in by_grade.items():
        rng.shuffle(pids)
        n_val = max(1, round(len(pids) * frac))
        inner_val.update(pids[:n_val])
    return inner_val


def write_split(manifest, labels: dict[str, str], path: Path, meta: dict) -> None:
    """labels: patient_id -> 'train' | 'val' | 'excluded'. Samples whose patient
    is 'excluded' get that label, which GammaMultimodalDataset ignores."""
    sample_split = {r["sample_id"]: labels[r["patient_id"]] for r in manifest}
    counts = {
        s: dict(Counter(r["grade"] for r in manifest if sample_split[r["sample_id"]] == s))
        for s in ("train", "val")
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**meta, "sample_split": sample_split, "class_distribution_per_split": counts}, indent=2))


def run_one(modality: str, outer_fold: int, seed: int, manifest, fold_of, grade_of, args, device, split_dir: Path) -> dict:
    outer_val = {p for p, f in fold_of.items() if f == outer_fold}
    outer_train = [p for p in fold_of if p not in outer_val]
    inner_val = inner_split(outer_train, grade_of, seed * 1000 + outer_fold)

    # Hard leakage checks.
    assert not (inner_val & outer_val), "inner-val overlaps outer-val"
    assert inner_val <= set(outer_train)

    fit_labels = {p: ("excluded" if p in outer_val else ("val" if p in inner_val else "train")) for p in fold_of}
    eval_labels = {p: ("val" if p in outer_val else "excluded") for p in fold_of}
    tag = f"s{seed}_f{outer_fold}"
    fit_path, eval_path = split_dir / f"fit_{tag}.json", split_dir / f"eval_{tag}.json"
    meta = {"outer_fold": outer_fold, "seed": seed, "k": args.k}
    write_split(manifest, fit_labels, fit_path, meta)
    write_split(manifest, eval_labels, eval_path, meta)

    train_args = SimpleNamespace(
        manifest=args.manifest, split=str(fit_path), run_name=f"nested_{modality}_{tag}",
        modality=modality, fundus_encoder=args.fundus_encoder, oct_encoder=args.oct_encoder,
        fusion_dim=args.fusion_dim, fusion_type=args.fusion_type, modality_dropout=args.modality_dropout,
        no_pretrained=args.no_pretrained, img_size=args.img_size, oct_slices=args.oct_slices,
        oct_representation=args.oct_representation, batch_size=args.batch_size, workers=args.workers,
        epochs=args.epochs, lr=args.lr, weight_decay=args.weight_decay, patience=args.patience,
        focal_loss=args.focal_loss, focal_gamma=args.focal_gamma, amp=args.amp, seed=seed,
        checkpoint_metric="val_loss", no_tensorboard=True,
    )
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)

    t0 = time.time()
    train_result = run_training(train_args, device)  # selects epoch on INNER val only
    train_seconds = time.time() - t0

    ckpt = torch.load(train_result["checkpoint"], map_location=device, weights_only=False)
    model = build_model(train_args, device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    outer_ds = GammaMultimodalDataset(
        args.manifest, str(eval_path), "val", args.img_size, args.img_size, args.oct_slices,
        train_augment=False, oct_representation=args.oct_representation,
    )
    res = run_evaluation(model, DataLoader(outer_ds, batch_size=args.batch_size, shuffle=False), device)
    if not args.keep_checkpoints:
        Path(train_result["checkpoint"]).unlink(missing_ok=True)

    preds = [
        {"patient_id": p["sample_id"], "fold": outer_fold, "seed": seed, "model": modality, **p}
        for p in res["predictions"]
    ]
    return {
        "modality": modality, "outer_fold": outer_fold, "seed": seed,
        "selected_epoch": ckpt["epoch"], "inner_val_loss": ckpt["val_loss"],
        "n_inner_val_patients": len(inner_val), "n_outer_val_patients": len(outer_val),
        "train_seconds": train_seconds, "metrics": res["metrics"],
        "confusion_matrix": res["confusion_matrix"], "predictions": preds,
    }


def save_run(result: dict, out_dir: Path) -> None:
    d = out_dir / result["modality"] / f"seed{result['seed']}" / f"fold{result['outer_fold']}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "metrics.json").write_text(json.dumps({k: v for k, v in result.items() if k != "predictions"}, indent=2))
    with open(d / "predictions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(result["predictions"][0].keys()))
        w.writeheader()
        w.writerows(result["predictions"])


def load_run(out_dir: Path, modality: str, seed: int, fold: int):
    d = out_dir / modality / f"seed{seed}" / f"fold{fold}"
    if not (d / "metrics.json").exists() or not (d / "predictions.csv").exists():
        return None
    r = json.loads((d / "metrics.json").read_text())
    with open(d / "predictions.csv", newline="") as f:
        r["predictions"] = list(csv.DictReader(f))
    return r


def recall_f1(rows: list[dict]) -> dict:
    """Macro F1 + per-class recall from prediction rows (true_label/pred_label)."""
    out, f1s = {}, []
    for g in GRADE_NAMES:
        tp = sum(1 for r in rows if r["true_label"] == g and r["pred_label"] == g)
        fn = sum(1 for r in rows if r["true_label"] == g and r["pred_label"] != g)
        fp = sum(1 for r in rows if r["true_label"] != g and r["pred_label"] == g)
        out[f"{g}_recall"] = tp / (tp + fn) if tp + fn else float("nan")
        f1s.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0)
    out["macro_f1"] = float(np.mean(f1s))
    out["accuracy"] = sum(r["true_label"] == r["pred_label"] for r in rows) / len(rows)
    return out


def aggregate(out_dir: Path, modalities, seeds, k, n_boot: int = 2000) -> dict:
    summary: dict = {"config": {"k": k, "seeds": list(seeds), "bootstrap_resamples": n_boot,
                                "selection": "epoch chosen on inner-val (patient-level) only"}}
    rng = np.random.default_rng(0)
    all_rows = []
    for modality in modalities:
        runs = [r for s in seeds for f in range(k) if (r := load_run(out_dir, modality, s, f))]
        if not runs:
            continue
        rows = [dict(p) for r in runs for p in r["predictions"]]
        all_rows.extend(rows)

        per_run = defaultdict(list)
        for r in runs:
            m = r["metrics"]
            for name in ("accuracy", "balanced_accuracy", "macro_f1", "roc_auc_ovr_macro", "cohen_kappa", "quadratic_weighted_kappa"):
                if m.get(name) is not None:
                    per_run[name].append(m[name])
            for g in (EARLY, PROGRESSIVE):
                per_run[f"{g}_recall"].append(m["per_class"][g]["recall"])
        entry = {
            "n_runs": len(runs),
            "per_run_mean_std": {n: {"mean": float(np.mean(v)), "std": float(np.std(v, ddof=1)) if len(v) > 1 else 0.0}
                                 for n, v in per_run.items()},
        }

        # Pooled out-of-fold per seed, then mean across seeds.
        per_seed = []
        for s in seeds:
            srows = [p for p in rows if int(p["seed"]) == s]
            if srows:
                per_seed.append(recall_f1(srows))
        entry["pooled_per_seed"] = per_seed
        entry["pooled_mean_over_seeds"] = {n: float(np.nanmean([d[n] for d in per_seed])) for n in per_seed[0]}

        # Patient-level bootstrap CI over all seed rows.
        by_pid = defaultdict(list)
        for p in rows:
            by_pid[p["patient_id"]].append(p)
        pids = list(by_pid)
        boots = defaultdict(list)
        for _ in range(n_boot):
            samp = [p for pid in rng.choice(pids, size=len(pids), replace=True) for p in by_pid[pid]]
            for n, v in recall_f1(samp).items():
                boots[n].append(v)
        entry["bootstrap_95ci"] = {n: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))] for n, v in boots.items()}
        summary[modality] = entry

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    if all_rows:
        with open(out_dir / "per_eye_predictions.csv", "w", newline="") as f:
            fields = ["patient_id", "fold", "seed", "model", "true_label", "pred_label",
                      "prob_normal", "prob_early", "prob_progressive"]
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(all_rows)
    print(f"[nested] wrote {out_dir / 'summary.json'}")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(REPO_ROOT / "dataset" / "gamma_manifest.json"))
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "results" / "nested_cv_v1"))
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--fold-seed", type=int, default=42, help="Outer fold assignment seed (42 = identical to EXP-05).")
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    ap.add_argument("--modalities", nargs="+", default=["fusion"], choices=MODALITIES)
    # EXP-05 frozen config
    ap.add_argument("--fundus-encoder", default="efficientnet_b0")
    ap.add_argument("--oct-encoder", default="resnet18")
    ap.add_argument("--fusion-dim", type=int, default=256)
    ap.add_argument("--fusion-type", choices=["vector", "token"], default="vector")
    ap.add_argument("--modality-dropout", type=float, default=0.15)
    ap.add_argument("--no-pretrained", action="store_true")
    ap.add_argument("--img-size", type=int, default=160)
    ap.add_argument("--oct-slices", type=int, default=8)
    ap.add_argument("--oct-representation", choices=["single", "2.5d"], default="single")
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--focal-loss", action="store_true", default=True)
    ap.add_argument("--focal-gamma", type=float, default=2.0)
    ap.add_argument("--amp", action="store_true", default=True)
    ap.add_argument("--keep-checkpoints", action="store_true")
    ap.add_argument("--aggregate-only", action="store_true", help="Skip training; just re-aggregate saved runs.")
    ap.add_argument("--smoke-test", action="store_true")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    manifest = json.loads(Path(args.manifest).read_text())
    fold_of = make_folds(manifest, args.k, args.fold_seed)
    grade_of = patient_grade(manifest)

    if args.smoke_test:
        args.fundus_encoder, args.oct_encoder = "resnet18", "resnet18"
        args.img_size, args.oct_slices, args.epochs, args.patience = 96, 4, 1, 1
        args.out_dir = str(REPO_ROOT / "results" / "nested_cv_smoke")
        args.seeds, args.modalities, folds = [42], ["fusion"], [0]
        print("[nested-smoke] 1 seed, 1 outer fold, 1 epoch, tiny config — NOT a result.")
    else:
        folds = list(range(args.k))

    out_dir = Path(args.out_dir)
    if args.aggregate_only:
        aggregate(out_dir, args.modalities, args.seeds, args.k)
        return

    log_config(SimpleNamespace(**{**vars(args), "modality": "+".join(args.modalities), "smoke_test": False, "smoke_batch_size": 0}), device)
    split_dir = REPO_ROOT / "dataset" / "splits" / ("nested_smoke" if args.smoke_test else "nested")
    (out_dir).mkdir(parents=True, exist_ok=True)
    (out_dir / "config.json").write_text(json.dumps(vars(args), indent=2))

    for seed in args.seeds:
        for fold in folds:
            for modality in args.modalities:
                if load_run(out_dir, modality, seed, fold):
                    print(f"[nested] skip (already done): {modality} seed={seed} fold={fold}")
                    continue
                print(f"\n[nested] === {modality} seed={seed} outer_fold={fold} ===")
                r = run_one(modality, fold, seed, manifest, fold_of, grade_of, args, device, split_dir)
                save_run(r, out_dir)
                m = r["metrics"]
                print(f"[nested] {modality} s{seed} f{fold}: epoch={r['selected_epoch']} acc={m['accuracy']:.3f} "
                      f"macroF1={m['macro_f1']:.3f} early_recall={m['per_class'][EARLY]['recall']:.3f} "
                      f"prog_recall={m['per_class'][PROGRESSIVE]['recall']:.3f} ({r['train_seconds']:.0f}s)")

    if not args.smoke_test:
        aggregate(out_dir, MODALITIES, args.seeds, args.k)  # every modality with saved runs, not just this call's
    else:
        print("[nested-smoke] PASSED: inner split, training, checkpoint reload, outer eval, and saving all ran. "
              "Do not record these numbers anywhere.")


if __name__ == "__main__":
    main()
