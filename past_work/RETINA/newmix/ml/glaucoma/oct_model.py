"""OCT B-scan severity network (Control / Mild / Moderate / Severe).

Architectures
  resnet18, efficientnet_b0   timm backbone (ImageNet weights, cached offline)
  hybrid                      resnet18 features + a small U-Net branch whose
                              decoder output is globally pooled and concatenated,
                              following the structure described in the paper
                              (U-Net localisation branch + CNN classification head).
                              The paper uses InceptionV3; its ImageNet weights are
                              not available offline here, so ResNet18 is used and
                              this is NOT a replication of the paper's model.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import timm
from PIL import Image

IMG_H, IMG_W = 224, 336
MEAN, STD = 0.45, 0.225


def load_image_tensor(path) -> torch.Tensor:
    """Grayscale B-scan -> (1, H, W) float in [0,1], 3 px border cropped."""
    im = Image.open(path).convert("L")
    w, h = im.size
    im = im.crop((3, 3, w - 3, h - 3)).resize((IMG_W, IMG_H), Image.BILINEAR)
    return torch.from_numpy(np.asarray(im, dtype=np.float32) / 255.0).unsqueeze(0)


def _cb(i, o):
    return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True),
                         nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True))


class SmallUNet(nn.Module):
    """Encoder 32-64-128-256, decoder back to 32 with skips, GAP -> 32-d vector."""

    def __init__(self):
        super().__init__()
        self.e1, self.e2, self.e3, self.mid = _cb(1, 32), _cb(32, 64), _cb(64, 128), _cb(128, 256)
        self.d3, self.d2, self.d1 = _cb(256 + 128, 128), _cb(128 + 64, 64), _cb(64 + 32, 32)

    def forward(self, x):
        e1 = self.e1(x)
        e2 = self.e2(F.max_pool2d(e1, 2))
        e3 = self.e3(F.max_pool2d(e2, 2))
        m = self.mid(F.max_pool2d(e3, 2))
        up = lambda t, s: F.interpolate(t, size=s.shape[-2:], mode="bilinear", align_corners=False)
        d3 = self.d3(torch.cat([up(m, e3), e3], 1))
        d2 = self.d2(torch.cat([up(d3, e2), e2], 1))
        d1 = self.d1(torch.cat([up(d2, e1), e1], 1))
        return d1.mean((2, 3))


class OCTNet(nn.Module):
    def __init__(self, arch: str = "resnet18", num_classes: int = 4, pretrained: bool = True):
        super().__init__()
        self.arch = arch
        name = {"resnet18": "resnet18.a1_in1k", "hybrid": "resnet18.a1_in1k",
                "efficientnet_b0": "efficientnet_b0.ra_in1k"}[arch]
        self.backbone = timm.create_model(name, pretrained=pretrained, num_classes=0)
        dim = self.backbone.num_features
        self.unet = SmallUNet() if arch == "hybrid" else None
        if self.unet is not None:
            dim += 32
        self.drop = nn.Dropout(0.3)
        self.fc = nn.Linear(dim, num_classes)

    def features(self, x):  # x: (B,1,H,W) in [0,1]
        g = x
        x3 = ((x - MEAN) / STD).expand(-1, 3, -1, -1)
        f = self.backbone(x3)
        if self.unet is not None:
            f = torch.cat([f, self.unet((g - MEAN) / STD)], 1)
        return f

    def forward(self, x):
        return self.fc(self.drop(self.features(x)))

    def gradcam_layer(self):
        return self.backbone.layer4[-1] if self.arch in ("resnet18", "hybrid") else self.backbone.blocks[-1]


def augment(x: torch.Tensor) -> torch.Tensor:
    """GPU batch augmentation: small affine + brightness/contrast + noise. No flips
    (left/right orientation encodes the eye), no vertical changes beyond a few %."""
    b = x.shape[0]
    ang = (torch.rand(b, device=x.device) - 0.5) * 2 * np.deg2rad(5)
    sc = 1 + (torch.rand(b, device=x.device) - 0.5) * 0.2
    tx = (torch.rand(b, device=x.device) - 0.5) * 0.12
    ty = (torch.rand(b, device=x.device) - 0.5) * 0.08
    cos, sin = torch.cos(ang) / sc, torch.sin(ang) / sc
    theta = torch.stack([torch.stack([cos, -sin, tx], 1), torch.stack([sin, cos, ty], 1)], 1)
    grid = F.affine_grid(theta, x.shape, align_corners=False)
    x = F.grid_sample(x, grid, padding_mode="border", align_corners=False)
    x = x * (1 + (torch.rand(b, 1, 1, 1, device=x.device) - 0.5) * 0.3) + (torch.rand(b, 1, 1, 1, device=x.device) - 0.5) * 0.1
    return (x + torch.randn_like(x) * 0.02).clamp(0, 1)
