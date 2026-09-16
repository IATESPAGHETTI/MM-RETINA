"""
GammaMultimodalDataset — loads real fundus + OCT B-scan data for one GAMMA
sample per __getitem__ call.

OCT slice sampling is configurable (`num_slices`) because loading all 256
B-scans per sample would blow past 6GB of VRAM at any reasonable batch
size. Default is a small, evenly-spaced subset — evenly spaced rather than
random so the sampled slices still span the whole macular volume instead of
clustering.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

GRADE_NAMES = ["normal", "early", "progressive"]


def evenly_spaced_indices(total: int, k: int) -> list[int]:
    if k >= total:
        return list(range(total))
    return [round(i * (total - 1) / (k - 1)) for i in range(k)] if k > 1 else [total // 2]


def build_fundus_transform(img_size: int, train: bool) -> transforms.Compose:
    if train:
        return transforms.Compose(
            [
                transforms.Resize((img_size, img_size)),
                transforms.RandomHorizontalFlip(p=0.5),
                # Small rotation + color jitter: fundus cameras vary in
                # framing/exposure across devices/sessions, but large
                # geometric distortion would misrepresent anatomy.
                transforms.RandomRotation(degrees=10),
                transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )
    return transforms.Compose(
        [
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


def build_oct_transform(img_size: int, train: bool) -> transforms.Compose:
    """OCT augmentation is deliberately conservative: B-scans are grayscale
    cross-sections with a fixed anatomical orientation (vitreous above,
    choroid below) — vertical flips or large rotations would invert or
    distort real tissue geometry, so only intensity-domain augmentation and
    a small horizontal jitter (nasal/temporal shift within the same B-scan
    orientation) are used."""
    if train:
        return transforms.Compose(
            [
                transforms.Resize((img_size, img_size)),
                transforms.ColorJitter(brightness=0.2, contrast=0.2),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5], std=[0.5]),
            ]
        )
    return transforms.Compose(
        [
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5], std=[0.5]),
        ]
    )


class GammaMultimodalDataset(Dataset):
    def __init__(
        self,
        manifest_path: str | Path,
        split_path: str | Path,
        split: str,
        img_size: int = 224,
        oct_img_size: int = 224,
        num_slices: int = 8,
        train_augment: bool = False,
    ):
        manifest = json.loads(Path(manifest_path).read_text())
        split_map = json.loads(Path(split_path).read_text())["sample_split"]

        self.rows = [r for r in manifest if split_map.get(r["sample_id"]) == split]
        if not self.rows:
            raise ValueError(f"No samples found for split={split!r} — check manifest/split paths")

        self.num_slices = num_slices
        self.fundus_transform = build_fundus_transform(img_size, train_augment)
        self.oct_transform = build_oct_transform(oct_img_size, train_augment)

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int):
        row = self.rows[idx]

        fundus = Image.open(row["fundus_path"]).convert("RGB")
        fundus_t = self.fundus_transform(fundus)

        oct_dir = Path(row["oct_dir"])
        total = row["num_bscans"]
        indices = evenly_spaced_indices(total, self.num_slices)
        slices = []
        for i in indices:
            img = Image.open(oct_dir / f"{i}_image.jpg").convert("L")
            slices.append(self.oct_transform(img))
        oct_t = torch.stack(slices, dim=0)  # (num_slices, 1, H, W)

        label = row["grade_index"]

        return {
            "fundus": fundus_t,
            "oct": oct_t,
            "label": torch.tensor(label, dtype=torch.long),
            "sample_id": row["sample_id"],
        }
