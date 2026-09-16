"""
Evaluate a trained checkpoint on the held-out TEST split only.

Refuses to run without a real checkpoint file — there is no code path here
that can produce a metrics.json without an actual trained model scoring
actual samples. Every number in the output is computed from real model
predictions on the real test split; nothing here is a placeholder.

Usage:
    python evaluate.py --checkpoint checkpoints/fusion_run1.pt --out-dir ../results/fusion_run1
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from torch.utils.data import DataLoader

from data import GammaMultimodalDataset, GRADE_NAMES
from model import GammaMultimodalModel

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_model_from_checkpoint(ckpt_path: Path, device: torch.device):
    if not ckpt_path.exists():
        raise FileNotFoundError(
            f"No checkpoint at {ckpt_path} — train a model first with train_multimodal.py. "
            "This script will not fabricate evaluation results for a model that doesn't exist."
        )
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    train_args = ckpt["args"]

    model = GammaMultimodalModel(
        fundus_encoder=train_args["fundus_encoder"],
        oct_encoder=train_args["oct_encoder"],
        fusion_dim=train_args["fusion_dim"],
        modality_dropout=train_args["modality_dropout"],
        pretrained=False,  # weights come from the checkpoint, not ImageNet, at eval time
        modality=train_args["modality"],
    ).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    print(f"[evaluate] Loaded checkpoint from epoch {ckpt['epoch']} "
          f"(val_loss={ckpt['val_loss']:.4f}), modality={train_args['modality']}")
    return model, train_args


def run_evaluation(model, loader, device) -> dict:
    all_logits, all_labels, all_ids = [], [], []
    with torch.no_grad():
        for batch in loader:
            fundus = batch["fundus"].to(device)
            oct_vol = batch["oct"].to(device)
            logits = model(fundus, oct_vol)
            all_logits.append(logits.cpu().numpy())
            all_labels.append(batch["label"].numpy())
            all_ids.extend(batch["sample_id"])

    logits = np.concatenate(all_logits, axis=0)
    labels = np.concatenate(all_labels, axis=0)
    probs = torch.softmax(torch.from_numpy(logits), dim=-1).numpy()
    preds = probs.argmax(axis=-1)

    precision, recall, f1_per_class, support = precision_recall_fscore_support(
        labels, preds, labels=list(range(len(GRADE_NAMES))), zero_division=0
    )

    metrics = {
        "num_test_samples": int(len(labels)),
        "accuracy": float(accuracy_score(labels, preds)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, preds)),
        "macro_f1": float(f1_score(labels, preds, average="macro", zero_division=0)),
        "per_class": {
            GRADE_NAMES[i]: {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1_per_class[i]),
                "support": int(support[i]),
            }
            for i in range(len(GRADE_NAMES))
        },
    }

    try:
        metrics["roc_auc_ovr_macro"] = float(
            roc_auc_score(labels, probs, multi_class="ovr", average="macro", labels=list(range(len(GRADE_NAMES))))
        )
    except ValueError as e:
        # Happens if the test split doesn't contain all classes — report why,
        # don't silently substitute a number.
        metrics["roc_auc_ovr_macro"] = None
        metrics["roc_auc_error"] = str(e)

    cm = confusion_matrix(labels, preds, labels=list(range(len(GRADE_NAMES))))

    return {
        "metrics": metrics,
        "confusion_matrix": cm.tolist(),
        "predictions": [
            {
                "sample_id": sid,
                "true_label": GRADE_NAMES[int(t)],
                "pred_label": GRADE_NAMES[int(p)],
                **{f"prob_{GRADE_NAMES[c]}": float(probs[i, c]) for c in range(len(GRADE_NAMES))},
            }
            for i, (sid, t, p) in enumerate(zip(all_ids, labels, preds))
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--manifest", default=str(REPO_ROOT / "dataset" / "gamma_manifest.json"))
    ap.add_argument("--split", default=str(REPO_ROOT / "dataset" / "splits" / "gamma_split_v1.json"))
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, train_args = load_model_from_checkpoint(Path(args.checkpoint), device)

    test_ds = GammaMultimodalDataset(
        args.manifest,
        args.split,
        "test",
        img_size=train_args["img_size"],
        oct_img_size=train_args["img_size"],
        num_slices=train_args["oct_slices"],
        train_augment=False,
    )
    print(f"[evaluate] Evaluating on {len(test_ds)} REAL held-out test samples "
          f"(never seen during training)")
    test_loader = DataLoader(test_ds, batch_size=train_args["batch_size"], shuffle=False)

    result = run_evaluation(model, test_loader, device)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "metrics.json").write_text(json.dumps(result["metrics"], indent=2))

    with open(out_dir / "confusion_matrix.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([""] + [f"pred_{g}" for g in GRADE_NAMES])
        for i, row in enumerate(result["confusion_matrix"]):
            writer.writerow([f"true_{GRADE_NAMES[i]}"] + row)

    with open(out_dir / "predictions.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(result["predictions"][0].keys()))
        writer.writeheader()
        writer.writerows(result["predictions"])

    print(f"[evaluate] Wrote metrics.json, confusion_matrix.csv, predictions.csv to {out_dir}")
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    main()
