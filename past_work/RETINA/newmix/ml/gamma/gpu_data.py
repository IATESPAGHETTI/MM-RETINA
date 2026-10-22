"""
GPU-resident data pipeline for the GAMMA fusion CV (research branch
`jev-architecture`).

Why: the stock `GammaMultimodalDataset` decodes 9 JPEGs per sample and does
PIL resize+augmentation on the CPU every epoch, so the GPU sat at ~2%
utilisation. Here every image is decoded and resized ONCE (same PIL
`Resize((S,S))` as data.py, so pixels are identical), cached as uint8, kept on
the GPU, and augmentation runs on the GPU per sample with the SAME
parameters as data.py's train transforms:

  fundus: HFlip(0.5), Rotation(+-10, nearest), ColorJitter(b.15,c.15,s.1), ImageNet normalise
  OCT   : ColorJitter(b.2,c.2) per slice, normalise mean=std=0.5   (no geometric aug)

Deviation (documented in decisions.md): tensor-based ColorJitter/Rotation are
numerically not bit-identical to the PIL versions, so augmented training
batches are equal in distribution, not in value. Un-augmented (validation)
tensors ARE bit-identical to data.py's (verified by `verify_equivalence`).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms as T

from data import GRADE_NAMES, evenly_spaced_indices

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "results" / "jev_architecture" / "cache"

FUNDUS_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
FUNDUS_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


def build_cache(manifest_path: str, img_size: int, num_slices: int) -> Path:
    """Decode + resize every sample once -> uint8 npz (idempotent)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"gamma_s{img_size}_n{num_slices}.npz"
    if path.exists():
        return path
    rows = json.loads(Path(manifest_path).read_text())
    resize = T.Resize((img_size, img_size))
    fundus, octs, ids, labels = [], [], [], []
    for r in rows:
        fundus.append(np.asarray(resize(Image.open(r["fundus_path"]).convert("RGB")), dtype=np.uint8))
        oct_dir = Path(r["oct_dir"])
        idx = evenly_spaced_indices(r["num_bscans"], num_slices)
        octs.append(np.stack([np.asarray(resize(Image.open(oct_dir / f"{i}_image.jpg").convert("L")), dtype=np.uint8) for i in idx]))
        ids.append(r["sample_id"]); labels.append(r["grade_index"])
    np.savez_compressed(path, fundus=np.stack(fundus), oct=np.stack(octs), ids=np.array(ids), labels=np.array(labels))
    return path


class GpuGamma:
    """All samples as uint8 CUDA tensors + batched, GPU-side (aug)normalisation."""

    def __init__(self, manifest_path: str, img_size: int, num_slices: int, device: torch.device):
        z = np.load(build_cache(manifest_path, img_size, num_slices))
        self.device = device
        self.fundus = torch.from_numpy(z["fundus"]).permute(0, 3, 1, 2).contiguous().to(device)  # (N,3,S,S) u8
        self.oct = torch.from_numpy(z["oct"]).unsqueeze(2).contiguous().to(device)               # (N,n,1,S,S) u8
        self.ids = [str(i) for i in z["ids"]]
        self.labels = torch.from_numpy(z["labels"]).long().to(device)
        self.index = {i: k for k, i in enumerate(self.ids)}
        self.f_mean, self.f_std = FUNDUS_MEAN.to(device), FUNDUS_STD.to(device)
        self.rot = T.RandomRotation(degrees=10)
        self.f_jit = T.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1)
        self.o_jit = T.ColorJitter(brightness=0.2, contrast=0.2)

    def rows(self, sample_ids: list[str]) -> torch.Tensor:
        return torch.tensor([self.index[s] for s in sample_ids], device=self.device)

    def batch(self, rows: torch.Tensor, augment: bool):
        f = self.fundus[rows].float() / 255.0            # (B,3,S,S) in [0,1]
        o = self.oct[rows].float() / 255.0               # (B,n,1,S,S)
        if augment:
            fs, os_ = [], []
            for b in range(f.shape[0]):
                x = f[b]
                if torch.rand(1).item() < 0.5:
                    x = torch.flip(x, dims=[-1])
                x = self.f_jit(self.rot(x))
                fs.append(x)
                os_.append(torch.stack([self.o_jit(o[b, k]) for k in range(o.shape[1])]))
            f, o = torch.stack(fs), torch.stack(os_)
        f = (f - self.f_mean) / self.f_std
        o = (o - 0.5) / 0.5
        return f, o, self.labels[rows]


def verify_equivalence(manifest_path: str, split_path: str, img_size: int, num_slices: int, device) -> dict:
    """Un-augmented GPU batches must equal GammaMultimodalDataset(val) exactly."""
    from data import GammaMultimodalDataset

    ds = GammaMultimodalDataset(manifest_path, split_path, "val", img_size, img_size, num_slices, train_augment=False)
    g = GpuGamma(manifest_path, img_size, num_slices, device)
    worst_f = worst_o = 0.0
    for i in range(len(ds)):
        item = ds[i]
        f, o, y = g.batch(g.rows([item["sample_id"]]), augment=False)
        worst_f = max(worst_f, (f[0].cpu() - item["fundus"]).abs().max().item())
        worst_o = max(worst_o, (o[0].cpu() - item["oct"]).abs().max().item())
        assert int(y.item()) == int(item["label"])
    return {"n": len(ds), "max_abs_diff_fundus": worst_f, "max_abs_diff_oct": worst_o}
