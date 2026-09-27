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


def build_oct_transform(img_size: int, train: bool, channels: int = 1) -> transforms.Compose:
    """OCT augmentation is deliberately conservative: B-scans are grayscale
    cross-sections with a fixed anatomical orientation (vitreous above,
    choroid below) — vertical flips or large rotations would invert or
    distort real tissue geometry, so only intensity-domain augmentation and
    a small horizontal jitter (nasal/temporal shift within the same B-scan
    orientation) are used.

    `channels` controls the normalization stats' length: 1 for the original
    single-slice representation, 3 for the 2.5D (i-1, i, i+1) representation
    (see `oct_representation="2.5d"` on GammaMultimodalDataset). The mean/std
    of 0.5 per channel is kept identical to the single-slice case in either
    mode — these are not real RGB channels, just stacked grayscale B-scans,
    so there's no ImageNet-style per-channel statistic to match."""
    mean = [0.5] * channels
    std = [0.5] * channels
    if train:
        return transforms.Compose(
            [
                transforms.Resize((img_size, img_size)),
                transforms.ColorJitter(brightness=0.2, contrast=0.2),
                transforms.ToTensor(),
                transforms.Normalize(mean=mean, std=std),
            ]
        )
    return transforms.Compose(
        [
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
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
        oct_representation: str = "single",
    ):
        if oct_representation not in ("single", "2.5d"):
            raise ValueError(f"oct_representation must be 'single' or '2.5d', got {oct_representation!r}")

        manifest = json.loads(Path(manifest_path).read_text())
        split_map = json.loads(Path(split_path).read_text())["sample_split"]

        self.rows = [r for r in manifest if split_map.get(r["sample_id"]) == split]
        if not self.rows:
            raise ValueError(f"No samples found for split={split!r} — check manifest/split paths")

        self.num_slices = num_slices
        self.oct_representation = oct_representation
        self.fundus_transform = build_fundus_transform(img_size, train_augment)
        oct_channels = 3 if oct_representation == "2.5d" else 1
        self.oct_transform = build_oct_transform(oct_img_size, train_augment, channels=oct_channels)

    def __len__(self) -> int:
        return len(self.rows)

    def _load_bscan(self, oct_dir: Path, i: int) -> Image.Image:
        return Image.open(oct_dir / f"{i}_image.jpg").convert("L")

    def _load_slice_2_5d(self, oct_dir: Path, i: int, total: int) -> Image.Image:
        """Stacks B-scans [i-1, i, i+1] as 3 channels of one PIL image, so
        the existing transform pipeline (resize/jitter/crop) is applied
        identically across all three — as if it were a single RGB image —
        rather than risking independently-randomized augmentation per
        channel. Edge slices clamp to the nearest valid index (replicating
        the boundary slice) rather than padding with zeros, since a real
        near-edge B-scan is a better neighbor than a blank one."""
        prev_img = self._load_bscan(oct_dir, max(i - 1, 0))
        center_img = self._load_bscan(oct_dir, i)
        next_img = self._load_bscan(oct_dir, min(i + 1, total - 1))
        return Image.merge("RGB", (prev_img, center_img, next_img))

    def __getitem__(self, idx: int):
        row = self.rows[idx]

        fundus = Image.open(row["fundus_path"]).convert("RGB")
        fundus_t = self.fundus_transform(fundus)

        oct_dir = Path(row["oct_dir"])
        total = row["num_bscans"]
        indices = evenly_spaced_indices(total, self.num_slices)
        slices = []
        for i in indices:
            if self.oct_representation == "2.5d":
                img = self._load_slice_2_5d(oct_dir, i, total)
            else:
                img = self._load_bscan(oct_dir, i)
            slices.append(self.oct_transform(img))
        oct_t = torch.stack(slices, dim=0)  # (num_slices, C, H, W) — C=1 (single) or 3 (2.5d)

        label = row["grade_index"]

        return {
            "fundus": fundus_t,
            "oct": oct_t,
            "label": torch.tensor(label, dtype=torch.long),
            "sample_id": row["sample_id"],
        }
