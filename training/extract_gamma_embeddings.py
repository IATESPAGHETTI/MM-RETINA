"""
Extracts frozen fused Fundus+OCT embeddings for all 100 GAMMA patients,
for use as the GAMMA branch's input in EXP-M01 (multi-dataset shared
representation). Does NOT modify model.py or retrain anything.

IMPORTANT LIMITATION — read before using these embeddings anywhere:
the only available trained checkpoint with the fusion vector still
reachable is `checkpoints/fusion_run1.pt` (resnet18 fundus + resnet18 OCT,
single train/val/test split from gamma_split_v1.json). The actual frozen
EXP-05/06 benchmark (EfficientNet-B0 fundus + ResNet18 OCT, 0.820 acc /
0.924 ROC-AUC, results/cv_fusion_effnetb0_v1/) was cross-validated, and
cross_validate.py deletes each fold's checkpoint after evaluation by
default — none of those per-fold checkpoints exist on disk anymore.

So: embeddings here come from a DIFFERENT (weaker, resnet18-only) trained
model than the frozen benchmark. They are extracted for all 100 patients
regardless of which split fusion_run1.pt was originally trained/tested on,
because they are used here purely as a fixed feature extractor for a new
downstream task (EXP-M01), not to re-report fusion_run1's own accuracy.
EXP-M01's GAMMA-branch numbers must NEVER be compared to or presented as
the frozen EXP-05/06 benchmark — they answer a different question (does a
shared trunk help vs. an independent one on top of a frozen embedding),
not "how accurate is the frozen model".

Usage:
    python training/extract_gamma_embeddings.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import torch

from data import GRADE_NAMES, build_fundus_transform, build_oct_transform, evenly_spaced_indices
from model import GammaMultimodalModel
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = Path(__file__).resolve().parent / "checkpoints" / "fusion_run1.pt"
MANIFEST = REPO_ROOT / "dataset" / "gamma_manifest.json"
OUT_CSV = REPO_ROOT / "dataset" / "gamma_fusion_embeddings.csv"


def load_one_sample(row: dict, img_size: int, num_slices: int, oct_representation: str):
    fundus_transform = build_fundus_transform(img_size, train=False)
    oct_transform = build_oct_transform(img_size, train=False, channels=3 if oct_representation == "2.5d" else 1)

    fundus = Image.open(row["fundus_path"]).convert("RGB")
    fundus_t = fundus_transform(fundus)

    oct_dir = Path(row["oct_dir"])
    total = row["num_bscans"]
    indices = evenly_spaced_indices(total, num_slices)
    slices = []
    for i in indices:
        img = Image.open(oct_dir / f"{i}_image.jpg").convert("L")
        slices.append(oct_transform(img))
    oct_t = torch.stack(slices, dim=0)
    return fundus_t, oct_t


@torch.no_grad()
def extract_all():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(CHECKPOINT, map_location=device, weights_only=False)
    train_args = ckpt["args"]
    print(f"[gamma_embeddings] Loading {CHECKPOINT.name}: "
          f"fundus={train_args['fundus_encoder']} oct={train_args['oct_encoder']} "
          f"fusion_dim={train_args['fusion_dim']} img_size={train_args['img_size']} "
          f"oct_slices={train_args['oct_slices']}")
    print("[gamma_embeddings] LIMITATION: this is NOT the frozen EfficientNet-B0 "
          "EXP-05/06 checkpoint (those per-fold checkpoints were deleted by "
          "cross_validate.py's default cleanup). Used here only as a frozen "
          "feature extractor for EXP-M01 — never compare its numbers to 0.820/0.924.")

    model = GammaMultimodalModel(
        fundus_encoder=train_args["fundus_encoder"],
        oct_encoder=train_args["oct_encoder"],
        fusion_dim=train_args["fusion_dim"],
        modality_dropout=0.0,  # eval-mode extraction, no need to fight dropout
        pretrained=False,
        modality="fusion",
        fusion_type=train_args.get("fusion_type", "vector"),
    ).to(device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    manifest = json.loads(MANIFEST.read_text())
    print(f"[gamma_embeddings] Extracting embeddings for {len(manifest)} GAMMA patients...")

    rows_out = []
    for i, row in enumerate(manifest):
        fundus_t, oct_t = load_one_sample(
            row, train_args["img_size"], train_args["oct_slices"], train_args.get("oct_representation", "single")
        )
        fundus_t = fundus_t.unsqueeze(0).to(device)
        oct_t = oct_t.unsqueeze(0).to(device)

        # Replicate GammaMultimodalModel.forward's vector-fusion path up to
        # (but not including) the classification head — model.py itself is
        # untouched; this only calls its already-public submodules.
        fundus_vec = model.fundus_encoder(fundus_t)
        oct_vec = model.oct_encoder(oct_t)
        vec = model.fusion(fundus_vec, oct_vec)  # (1, fusion_dim)

        rows_out.append({
            "patient_id": row["patient_id"],
            "sample_id": row["sample_id"],
            "grade": row["grade"],
            "grade_index": row["grade_index"],
            **{f"dim_{d}": float(vec[0, d].item()) for d in range(vec.shape[1])},
        })
        if (i + 1) % 20 == 0 or i == len(manifest) - 1:
            print(f"[gamma_embeddings] {i + 1}/{len(manifest)}")

    fieldnames = list(rows_out[0].keys())
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)
    print(f"[gamma_embeddings] Wrote {OUT_CSV} ({len(rows_out)} patients, "
          f"{len(fieldnames) - 4}-dim embeddings)")


if __name__ == "__main__":
    extract_all()
