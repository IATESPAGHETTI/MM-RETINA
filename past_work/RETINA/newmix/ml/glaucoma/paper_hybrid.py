"""The paper's hybrid (Garg et al.): U-Net branch + InceptionV3, 512x512 input.

Implemented from the paper's text:
  preprocessing  grayscale -> median filter -> Gaussian blur -> CLAHE -> intensity normalisation -> 512x512
  U-Net branch   encoder 32-64-128-256 (3 max-pools, 64x64 bottleneck), decoder with skips back to 32, GAP -> 32-d
  backbone       InceptionV3 (ImageNet weights, top removed) -> 2048-d
  head           concat -> dense 256/128/64, each BatchNorm + ReLU + dropout 0.5/0.3/0.2, L2 1e-4 -> softmax
  optimiser      Adam, lr 1e-4, cross-entropy
  augmentation   rotation 20 deg, shift 15% x / 10% y, shear 10%, brightness 85-115%, channel shift +-10,
                 zoom 0.9-1.1, horizontal flip, reflection padding

Not specified by the paper (chosen here and disclosed): batch size, epochs, CLAHE clip/tile, kernel sizes.
"""

from __future__ import annotations

import cv2
import numpy as np
import timm
import torch
import torch.nn as nn
import torch.utils.checkpoint
import torch.nn.functional as F

SIZE = 512
MEAN3 = (0.485, 0.456, 0.406)
STD3 = (0.229, 0.224, 0.225)


def preprocess_paper(path_or_gray) -> np.ndarray:
    """-> uint8 (512, 512). Order follows the paper's Fig. 2."""
    g = cv2.imread(str(path_or_gray), cv2.IMREAD_GRAYSCALE) if not isinstance(path_or_gray, np.ndarray) else path_or_gray
    h, w = g.shape
    g = g[3:h - 3, 3:w - 3]  # drop the 3 px green frame burned into every scan
    g = cv2.medianBlur(g, 5)
    g = cv2.GaussianBlur(g, (5, 5), 0)
    g = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(g)
    g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX)
    return cv2.resize(g, (SIZE, SIZE), interpolation=cv2.INTER_AREA)


def _cb(i, o):
    return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True),
                         nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True))


class PaperUNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.e1, self.e2, self.e3, self.mid = _cb(1, 32), _cb(32, 64), _cb(64, 128), _cb(128, 256)
        self.d3, self.d2, self.d1 = _cb(256 + 128, 128), _cb(128 + 64, 64), _cb(64 + 32, 32)

    def forward(self, x):
        e1 = self.e1(x)
        e2 = self.e2(F.max_pool2d(e1, 2))
        e3 = self.e3(F.max_pool2d(e2, 2))
        m = self.mid(F.max_pool2d(e3, 2))                       # 64x64 bottleneck for a 512 input
        up = lambda t, s: F.interpolate(t, size=s.shape[-2:], mode="bilinear", align_corners=False)
        d3 = self.d3(torch.cat([up(m, e3), e3], 1))
        d2 = self.d2(torch.cat([up(d3, e2), e2], 1))
        d1 = self.d1(torch.cat([up(d2, e1), e1], 1))
        return d1.mean((2, 3))                                  # GAP -> 32


class PaperHybrid(nn.Module):
    def __init__(self, num_classes: int = 4, pretrained: bool = True):
        super().__init__()
        self.incep = timm.create_model("inception_v3.tv_in1k", pretrained=pretrained, num_classes=0)
        self.unet = PaperUNet()
        dims = [2048 + 32, 256, 128, 64]
        drops = [0.5, 0.3, 0.2]
        layers: list[nn.Module] = []
        for i in range(3):
            layers += [nn.Linear(dims[i], dims[i + 1]), nn.BatchNorm1d(dims[i + 1]), nn.ReLU(inplace=True), nn.Dropout(drops[i])]
        self.head = nn.Sequential(*layers, nn.Linear(64, num_classes))
        self.register_buffer("mean", torch.tensor(MEAN3).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor(STD3).view(1, 3, 1, 1))

    def forward(self, x):  # x: (B,1,512,512) in [0,1]
        x3 = ((x.expand(-1, 3, -1, -1) - self.mean) / self.std)
        xu = (x - 0.45) / 0.225
        if self.training and torch.is_grad_enabled():
            # same maths, ~30% faster on a 6 GB card because the full-resolution U-Net activations are recomputed
            u = torch.utils.checkpoint.checkpoint(self.unet, xu, use_reentrant=False)
        else:
            u = self.unet(xu)
        return self.head(torch.cat([self.incep(x3), u], 1))

    def param_groups(self, lr_backbone: float, lr_rest: float, wd: float = 1e-4):
        bb = list(self.incep.parameters())
        ids = {id(p) for p in bb}
        rest = [p for p in self.parameters() if id(p) not in ids]
        return [{"params": bb, "lr": lr_backbone, "weight_decay": wd}, {"params": rest, "lr": lr_rest, "weight_decay": wd}]


def paper_augment(x: torch.Tensor, flip: bool = True) -> torch.Tensor:
    """Batch augmentation matching the paper's list. x: (B,1,H,W) in [0,1]."""
    b, dev = x.shape[0], x.device
    u = lambda lo, hi: lo + (hi - lo) * torch.rand(b, device=dev)
    ang = torch.deg2rad(u(-20, 20))
    shear = u(-0.1, 0.1)
    zoom = u(0.9, 1.1)
    tx, ty = u(-0.15, 0.15) * 2, u(-0.10, 0.10) * 2   # affine_grid works in [-1,1] units
    fl = torch.where(torch.rand(b, device=dev) < 0.5, -1.0, 1.0) if flip else torch.ones(b, device=dev)
    cos, sin = torch.cos(ang), torch.sin(ang)
    a = torch.stack([fl * cos / zoom, (-sin + shear) / zoom, tx], 1)
    c = torch.stack([fl * sin / zoom, cos / zoom, ty], 1)
    grid = F.affine_grid(torch.stack([a, c], 1), x.shape, align_corners=False)
    x = F.grid_sample(x, grid, padding_mode="reflection", align_corners=False)
    x = x * u(0.85, 1.15).view(b, 1, 1, 1)
    x3 = x.expand(-1, 3, -1, -1) + (torch.randint(-10, 11, (b, 3, 1, 1), device=dev).float() / 255.0)
    return x3.mean(1, keepdim=True).clamp(0, 1)  # channel shifts collapse back to the single gray input
