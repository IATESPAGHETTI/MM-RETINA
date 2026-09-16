"""
Patient-level K-fold cross-validation over the GAMMA training manifest.

Reuses the existing, unmodified pipeline (train_multimodal.run_training,
evaluate.run_evaluation, data.GammaMultimodalDataset, model.GammaMultimodalModel)
by generating one fold-specific split file per fold — in the same JSON
schema split_gamma.py already produces — and feeding it straight into the
existing training/evaluation functions. No changes to data.py, model.py,
losses.py, train_multimodal.py, or evaluate.py were needed or made.

Patients are assigned to folds by round-robin within each grade group
(after a seeded shuffle), so every fold gets a similar class balance and
every patient appears in exactly one fold's validation set and every other
fold's training set — never in both for the same fold.

Usage:
    # ALWAYS run this first:
    python cross_validate.py --smoke-test

    # Then the real thing:
    python cross_validate.py --k 5 --epochs 25 --img-size 160 --oct-slices 8 \
        --batch-size 4 --lr 1e-4 --focal-loss --amp --patience 8
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from torch.utils.data import DataLoader

from data import GammaMultimodalDataset, GRADE_NAMES
from evaluate import run_evaluation
from train_multimodal import build_model, log_config, run_training

REPO_ROOT = Path(__file__).resolve().parent.parent
MODALITIES = ["fundus", "oct", "fusion"]


def git_commit_or_none() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=Path(__file__).parent)
        return out.stdout.strip() if out.returncode == 0 else None
    except FileNotFoundError:
        return None


def make_folds(manifest: list[dict], k: int, seed: int) -> dict[str, int]:
    """Round-robin, grade-stratified fold assignment per patient.
    Deterministic given (manifest content, k, seed)."""
    by_patient: dict[str, list[dict]] = defaultdict(list)
    for row in manifest:
        by_patient[row["patient_id"]].append(row)

    patient_grade = {
        pid: Counter(r["grade"] for r in rows).most_common(1)[0][0] for pid, rows in by_patient.items()
    }
    by_grade: dict[str, list[str]] = defaultdict(list)
    for pid, grade in patient_grade.items():
        by_grade[grade].append(pid)

    rng = random.Random(seed)
    fold_of: dict[str, int] = {}
    for grade, pids in by_grade.items():
        pids = sorted(pids)
        rng.shuffle(pids)
        for i, pid in enumerate(pids):
            fold_of[pid] = i % k

    return fold_of


def write_fold_split(manifest: list[dict], fold_of: dict[str, int], fold_idx: int, k: int, seed: int, out_path: Path) -> dict:
    sample_split = {
        row["sample_id"]: ("val" if fold_of[row["patient_id"]] == fold_idx else "train") for row in manifest
    }

    # Hard assertion: no patient in both train and val for this fold.
    patient_splits: dict[str, set[str]] = defaultdict(set)
    for row in manifest:
        patient_splits[row["patient_id"]].add(sample_split[row["sample_id"]])
    leaked = {pid: s for pid, s in patient_splits.items() if len(s) > 1}
    if leaked:
        raise AssertionError(f"Fold {fold_idx}: patient leakage between train/val: {leaked}")

    counts = {
        split: dict(Counter(row["grade"] for row in manifest if sample_split[row["sample_id"]] == split))
        for split in ("train", "val")
    }

    split_doc = {
        "cv_fold": fold_idx,
        "cv_k": k,
        "seed": seed,
        "git_commit": git_commit_or_none(),
        "num_samples": len(manifest),
        "num_patients": len({row["patient_id"] for row in manifest}),
        "sample_split": sample_split,
        "class_distribution_per_split": counts,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(split_doc, indent=2))
    return split_doc


def train_and_eval_one_fold(modality: str, fold_idx: int, split_path: Path, args, device) -> dict:
    train_args = SimpleNamespace(
        manifest=args.manifest,
        split=str(split_path),
        run_name=f"cv_{modality}_fold{fold_idx}",
        modality=modality,
        fundus_encoder=args.fundus_encoder,
        oct_encoder=args.oct_encoder,
        fusion_dim=args.fusion_dim,
        modality_dropout=args.modality_dropout,
        no_pretrained=args.no_pretrained,
        img_size=args.img_size,
        oct_slices=args.oct_slices,
        batch_size=args.batch_size,
        workers=args.workers,
        epochs=args.epochs,
        lr=args.lr,
        weight_decay=args.weight_decay,
        patience=args.patience,
        focal_loss=args.focal_loss,
        focal_gamma=args.focal_gamma,
        amp=args.amp,
        seed=args.seed,
    )

    t0 = time.time()
    train_result = run_training(train_args, device)
    train_seconds = time.time() - t0

    # Reload the best checkpoint for this fold and evaluate on its val split.
    ckpt = torch.load(train_result["checkpoint"], map_location=device, weights_only=False)
    model = build_model(train_args, device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    val_ds = GammaMultimodalDataset(
        args.manifest, str(split_path), "val", args.img_size, args.img_size, args.oct_slices, train_augment=False
    )
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False)
    eval_result = run_evaluation(model, val_loader, device)

    # Don't keep 15 full checkpoints on disk — only the metrics matter for CV.
    if not args.keep_checkpoints:
        Path(train_result["checkpoint"]).unlink(missing_ok=True)

    return {
        "modality": modality,
        "fold": fold_idx,
        "best_epoch": ckpt["epoch"],
        "best_val_loss": ckpt["val_loss"],
        "train_seconds": train_seconds,
        "metrics": eval_result["metrics"],
        "confusion_matrix": eval_result["confusion_matrix"],
        "predictions": eval_result["predictions"],
    }


def save_fold_result(result: dict, out_dir: Path):
    fold_dir = out_dir / result["modality"] / f"fold{result['fold']}"
    fold_dir.mkdir(parents=True, exist_ok=True)
    (fold_dir / "metrics.json").write_text(json.dumps(
        {k: v for k, v in result.items() if k not in ("confusion_matrix", "predictions")}, indent=2
    ))
    with open(fold_dir / "confusion_matrix.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([""] + [f"pred_{g}" for g in GRADE_NAMES])
        for i, row in enumerate(result["confusion_matrix"]):
            writer.writerow([f"true_{GRADE_NAMES[i]}"] + row)
    with open(fold_dir / "predictions.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(result["predictions"][0].keys()))
        writer.writeheader()
        writer.writerows(result["predictions"])
    print(f"[cv] wrote {fold_dir}")


def aggregate(all_results: list[dict], out_dir: Path) -> dict:
    summary = {}
    for modality in MODALITIES:
        rows = [r for r in all_results if r["modality"] == modality]
        if not rows:
            continue
        metric_names = ["accuracy", "balanced_accuracy", "macro_f1", "roc_auc_ovr_macro"]
        per_metric = {}
        for m in metric_names:
            values = [r["metrics"][m] for r in rows if r["metrics"].get(m) is not None]
            skipped = len(rows) - len(values)
            per_metric[m] = {
                "values_per_fold": values,
                "mean": float(np.mean(values)) if values else None,
                "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                "folds_skipped_missing_value": skipped,
            }
        summary[modality] = per_metric

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n[cv] wrote aggregate summary to {out_dir / 'summary.json'}")
    print(json.dumps(summary, indent=2))
    return summary


def run_smoke_test(args, device):
    print("\n[cv-smoke-test] Building REAL folds from the real manifest...")
    manifest = json.loads(Path(args.manifest).read_text())
    fold_of = make_folds(manifest, args.k, args.seed)

    fold_sizes = Counter(fold_of.values())
    print(f"[cv-smoke-test] {len(fold_of)} patients across {args.k} folds: {dict(sorted(fold_sizes.items()))}")

    tmp_split_dir = REPO_ROOT / "dataset" / "splits" / "cv_smoke"
    split_path = tmp_split_dir / "fold0.json"
    split_doc = write_fold_split(manifest, fold_of, 0, args.k, args.seed, split_path)
    print(f"[cv-smoke-test] Verified: no patient leakage in fold 0.")
    print(f"[cv-smoke-test] fold 0 train={sum(1 for v in split_doc['sample_split'].values() if v=='train')} "
          f"val={sum(1 for v in split_doc['sample_split'].values() if v=='val')} "
          f"class_dist={split_doc['class_distribution_per_split']}")

    smoke_args = SimpleNamespace(
        manifest=args.manifest,
        fundus_encoder="resnet18",
        oct_encoder="resnet18",
        fusion_dim=256,
        modality_dropout=0.15,
        no_pretrained=False,
        img_size=96,
        oct_slices=4,
        batch_size=4,
        workers=0,
        epochs=1,
        lr=1e-4,
        weight_decay=1e-4,
        patience=1,
        focal_loss=True,
        focal_gamma=2.0,
        amp=True,
        seed=args.seed,
        keep_checkpoints=False,
    )

    for modality in MODALITIES:
        print(f"\n[cv-smoke-test] Real 1-epoch train+eval for modality={modality} on fold 0 (tiny config)...")
        result = train_and_eval_one_fold(modality, 0, split_path, smoke_args, device)
        print(f"[cv-smoke-test] modality={modality}: best_epoch={result['best_epoch']} "
              f"val_loss={result['best_val_loss']:.4f} train_seconds={result['train_seconds']:.1f} "
              f"eval_accuracy={result['metrics']['accuracy']:.3f} (n={result['metrics']['num_test_samples']})")

    print("\n[cv-smoke-test] PASSED — fold construction, training, checkpoint reload, and evaluation "
          "all completed for real, on real data, for all three modalities. This is a 1-epoch sanity "
          "check, not a real CV result — do not record these numbers anywhere as findings.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(REPO_ROOT / "dataset" / "gamma_manifest.json"))
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "results" / "cv"))
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--modalities", nargs="+", default=MODALITIES, choices=MODALITIES)

    ap.add_argument("--fundus-encoder", default="resnet18")
    ap.add_argument("--oct-encoder", default="resnet18")
    ap.add_argument("--fusion-dim", type=int, default=256)
    ap.add_argument("--modality-dropout", type=float, default=0.15)
    ap.add_argument("--no-pretrained", action="store_true")

    ap.add_argument("--img-size", type=int, default=160)
    ap.add_argument("--oct-slices", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--workers", type=int, default=0)

    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--focal-loss", action="store_true")
    ap.add_argument("--focal-gamma", type=float, default=2.0)
    ap.add_argument("--amp", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--keep-checkpoints", action="store_true",
                     help="Keep all fold checkpoints (default: delete after eval to save disk — 15 runs' worth adds up).")

    ap.add_argument("--smoke-test", action="store_true")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if args.smoke_test:
        run_smoke_test(args, device)
        return

    log_config(SimpleNamespace(**{**vars(args), "smoke_test": False, "smoke_batch_size": 0, "modality": "+".join(args.modalities)}), device)

    manifest = json.loads(Path(args.manifest).read_text())
    fold_of = make_folds(manifest, args.k, args.seed)
    fold_sizes = Counter(fold_of.values())
    print(f"[cv] {len(fold_of)} patients across {args.k} folds: {dict(sorted(fold_sizes.items()))}")

    out_dir = Path(args.out_dir)
    split_dir = REPO_ROOT / "dataset" / "splits" / "cv"

    all_results = []
    for fold_idx in range(args.k):
        split_path = split_dir / f"fold{fold_idx}.json"
        split_doc = write_fold_split(manifest, fold_of, fold_idx, args.k, args.seed, split_path)
        print(f"\n[cv] === Fold {fold_idx}/{args.k - 1} === "
              f"train={sum(1 for v in split_doc['sample_split'].values() if v == 'train')} "
              f"val={sum(1 for v in split_doc['sample_split'].values() if v == 'val')} "
              f"val_class_dist={split_doc['class_distribution_per_split']['val']}")

        for modality in args.modalities:
            print(f"[cv] --- fold {fold_idx}, modality={modality} ---")
            result = train_and_eval_one_fold(modality, fold_idx, split_path, args, device)
            save_fold_result(result, out_dir)
            all_results.append(result)
            m = result["metrics"]
            print(f"[cv] fold {fold_idx} {modality}: accuracy={m['accuracy']:.3f} "
                  f"balanced_accuracy={m['balanced_accuracy']:.3f} macro_f1={m['macro_f1']:.3f} "
                  f"roc_auc={m.get('roc_auc_ovr_macro')}")

    aggregate(all_results, out_dir)


if __name__ == "__main__":
    main()
