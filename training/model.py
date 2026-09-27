"""
Multimodal fusion model: fundus CNN + shared per-slice OCT CNN with
attention pooling, combined via cross-modal transformer attention, into a
3-class (Normal/Early/Progressive) classifier.

Encoders are pulled from `timm` so swapping architectures is a config
change (--fundus-encoder, --oct-encoder), not a code change — pass any
timm model name that supports `num_classes=0` (feature extraction mode).
Defaults are small (resnet18) to fit comfortably in 6GB of VRAM alongside
an OCT slice batch; move to something heavier only after confirming the
smoke test and a short real run fit in memory.
"""

from __future__ import annotations

import timm
import torch
import torch.nn as nn


class AttentionPool1d(nn.Module):
    """Learned-query attention pooling over a sequence of embeddings.

    Plain mean/max pooling weighs every OCT slice equally; a real macular
    OCT volume is not uniformly informative (peripheral slices carry much
    less signal than central ones), so this lets the model learn which
    slices to weight more per sample instead of assuming a fixed pattern.
    """

    def __init__(self, dim: int):
        super().__init__()
        self.query = nn.Parameter(torch.randn(1, 1, dim) * 0.02)
        self.attn = nn.MultiheadAttention(embed_dim=dim, num_heads=4, batch_first=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, N, D)
        b = x.shape[0]
        q = self.query.expand(b, -1, -1)
        pooled, _ = self.attn(q, x, x)  # (B, 1, D)
        return pooled.squeeze(1)


class OCTVolumeEncoder(nn.Module):
    """Applies one shared 2D encoder to every sampled B-scan, then pools
    the per-slice embeddings into a single volume-level vector."""

    def __init__(self, backbone_name: str, out_dim: int, pretrained: bool = True, in_chans: int = 1):
        super().__init__()
        self.backbone = timm.create_model(
            backbone_name, pretrained=pretrained, num_classes=0, in_chans=in_chans
        )
        feat_dim = self.backbone.num_features
        self.proj = nn.Linear(feat_dim, out_dim)
        self.pool = AttentionPool1d(out_dim)

    def forward(self, x: torch.Tensor, return_tokens: bool = False) -> torch.Tensor:
        # x: (B, N, C, H, W) -> flatten slices into the batch dim for the
        # shared encoder, then reshape back to (B, N, D).
        b, n = x.shape[:2]
        x = x.view(b * n, *x.shape[2:])
        feats = self.backbone(x)
        feats = self.proj(feats)
        feats = feats.view(b, n, -1)
        if return_tokens:
            # One token per sampled B-scan (B, N, out_dim) -- used by
            # token-level fusion (EXP-06) instead of attention-pooling the
            # whole volume into one vector.
            return feats
        return self.pool(feats)


class FundusEncoder(nn.Module):
    def __init__(self, backbone_name: str, out_dim: int, pretrained: bool = True):
        super().__init__()
        self.backbone = timm.create_model(
            backbone_name, pretrained=pretrained, num_classes=0, in_chans=3
        )
        self.proj = nn.Linear(self.backbone.num_features, out_dim)

    def forward(self, x: torch.Tensor, return_tokens: bool = False) -> torch.Tensor:
        if return_tokens:
            # Spatial feature map (B, C, H, W) -> per-location tokens (B, H*W, out_dim),
            # e.g. 5x5=25 tokens at 160x160 input for a resnet18/efficientnet_b0
            # backbone (stride 32) -- used by token-level fusion (EXP-06) instead
            # of collapsing the whole image into one pooled vector.
            feat_map = self.backbone.forward_features(x)  # (B, C, H, W)
            b, c, h, w = feat_map.shape
            tokens = feat_map.flatten(2).transpose(1, 2)  # (B, H*W, C)
            return self.proj(tokens)  # (B, H*W, out_dim)
        return self.proj(self.backbone(x))


class CrossModalFusion(nn.Module):
    """Two modality tokens (fundus, OCT) attend to each other via a
    standard transformer encoder layer, then are pooled into one vector.
    This is genuine cross-modal query/key/value attention over both
    tokens — not self-attention dressed up as "cross-attention"."""

    def __init__(self, dim: int, num_heads: int = 4, ff_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        self.modality_embed = nn.Parameter(torch.randn(1, 2, dim) * 0.02)
        self.layer = nn.TransformerEncoderLayer(
            d_model=dim,
            nhead=num_heads,
            dim_feedforward=ff_dim,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )

    def forward(self, fundus_vec: torch.Tensor, oct_vec: torch.Tensor) -> torch.Tensor:
        tokens = torch.stack([fundus_vec, oct_vec], dim=1)  # (B, 2, D)
        tokens = tokens + self.modality_embed
        fused = self.layer(tokens)  # (B, 2, D)
        return fused.mean(dim=1)


class TokenCrossModalFusion(nn.Module):
    """Token-level cross-modal fusion (EXP-06): instead of collapsing each
    modality into a single vector before fusion, keeps the fundus branch's
    spatial feature-map tokens and the OCT branch's per-slice tokens intact,
    tags each with a modality-type embedding, concatenates them into one
    sequence, and lets a small Transformer encoder attend across all of
    them jointly. Deliberately small (2-4 layers / 4 heads / a modest
    feedforward width) per the project's guidance not to build an
    unnecessarily large model for a 6GB GPU / 100-sample dataset."""

    def __init__(self, dim: int, num_layers: int = 2, num_heads: int = 4, ff_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        self.modality_embed = nn.Parameter(torch.randn(1, 2, dim) * 0.02)  # 0=fundus, 1=oct
        layer = nn.TransformerEncoderLayer(
            d_model=dim,
            nhead=num_heads,
            dim_feedforward=ff_dim,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=num_layers)

    def forward(self, fundus_tokens: torch.Tensor, oct_tokens: torch.Tensor) -> torch.Tensor:
        # fundus_tokens: (B, Nf, D), oct_tokens: (B, No, D)
        fundus_tokens = fundus_tokens + self.modality_embed[:, 0:1, :]
        oct_tokens = oct_tokens + self.modality_embed[:, 1:2, :]
        tokens = torch.cat([fundus_tokens, oct_tokens], dim=1)  # (B, Nf+No, D)
        fused = self.encoder(tokens)
        return fused.mean(dim=1)


class TokenModalityDropout(nn.Module):
    """Token-sequence analogue of ModalityDropout: zeroes every token of an
    entire modality (not individual scalars) at train time, keeping the
    same missing-modality robustness behavior when moving from vector-level
    to token-level fusion, so EXP-06 changes only the fusion mechanism and
    not also whether modality dropout exists."""

    def __init__(self, p: float = 0.15):
        super().__init__()
        self.p = p

    def forward(self, fundus_tokens: torch.Tensor, oct_tokens: torch.Tensor):
        if not self.training or self.p <= 0:
            return fundus_tokens, oct_tokens
        b = fundus_tokens.shape[0]
        drop_fundus = (torch.rand(b, device=fundus_tokens.device) < self.p).float().view(b, 1, 1)
        drop_oct = (torch.rand(b, device=oct_tokens.device) < self.p).float().view(b, 1, 1)
        both = drop_fundus * drop_oct
        drop_fundus = drop_fundus * (1 - both)
        drop_oct = drop_oct * (1 - both)
        return fundus_tokens * (1 - drop_fundus), oct_tokens * (1 - drop_oct)


class ModalityDropout(nn.Module):
    """Zeroes an entire modality's token (not individual scalars) at
    train time, forcing the fusion layer to tolerate a missing modality —
    the real-world failure mode of a missing OCT export or corrupted
    fundus capture."""

    def __init__(self, p: float = 0.15):
        super().__init__()
        self.p = p

    def forward(self, fundus_vec: torch.Tensor, oct_vec: torch.Tensor):
        if not self.training or self.p <= 0:
            return fundus_vec, oct_vec
        b = fundus_vec.shape[0]
        drop_fundus = (torch.rand(b, device=fundus_vec.device) < self.p).float().unsqueeze(1)
        drop_oct = (torch.rand(b, device=oct_vec.device) < self.p).float().unsqueeze(1)
        # Never drop both for the same sample.
        both = drop_fundus * drop_oct
        drop_fundus = drop_fundus * (1 - both)
        drop_oct = drop_oct * (1 - both)
        return fundus_vec * (1 - drop_fundus), oct_vec * (1 - drop_oct)


class GammaMultimodalModel(nn.Module):
    def __init__(
        self,
        fundus_encoder: str = "resnet18",
        oct_encoder: str = "resnet18",
        fusion_dim: int = 256,
        num_classes: int = 3,
        modality_dropout: float = 0.15,
        pretrained: bool = True,
        modality: str = "fusion",  # "fusion" | "fundus" | "oct" — for ablations
        oct_in_chans: int = 1,  # 1 = single B-scan per slice; 3 = 2.5D (i-1, i, i+1) stack
        fusion_type: str = "vector",  # "vector" (baseline, 2 pooled tokens) | "token" (EXP-06)
    ):
        super().__init__()
        self.modality = modality
        self.fusion_type = fusion_type

        self.fundus_encoder = (
            FundusEncoder(fundus_encoder, fusion_dim, pretrained) if modality in ("fusion", "fundus") else None
        )
        self.oct_encoder = (
            OCTVolumeEncoder(oct_encoder, fusion_dim, pretrained, in_chans=oct_in_chans)
            if modality in ("fusion", "oct") else None
        )
        if modality == "fusion" and fusion_type == "token":
            self.modality_dropout = TokenModalityDropout(modality_dropout)
            self.fusion = TokenCrossModalFusion(fusion_dim)
        elif modality == "fusion":
            self.modality_dropout = ModalityDropout(modality_dropout)
            self.fusion = CrossModalFusion(fusion_dim)
        else:
            self.modality_dropout = None
            self.fusion = None

        self.head = nn.Sequential(
            nn.LayerNorm(fusion_dim),
            nn.Linear(fusion_dim, fusion_dim // 2),
            nn.GELU(),
            nn.Dropout(0.3),
            nn.Linear(fusion_dim // 2, num_classes),
        )

    def forward(self, fundus: torch.Tensor, oct_vol: torch.Tensor) -> torch.Tensor:
        if self.modality == "fundus":
            vec = self.fundus_encoder(fundus)
        elif self.modality == "oct":
            vec = self.oct_encoder(oct_vol)
        elif self.fusion_type == "token":
            fundus_tokens = self.fundus_encoder(fundus, return_tokens=True)
            oct_tokens = self.oct_encoder(oct_vol, return_tokens=True)
            fundus_tokens, oct_tokens = self.modality_dropout(fundus_tokens, oct_tokens)
            vec = self.fusion(fundus_tokens, oct_tokens)
        else:
            fundus_vec = self.fundus_encoder(fundus)
            oct_vec = self.oct_encoder(oct_vol)
            fundus_vec, oct_vec = self.modality_dropout(fundus_vec, oct_vec)
            vec = self.fusion(fundus_vec, oct_vec)
        return self.head(vec)
