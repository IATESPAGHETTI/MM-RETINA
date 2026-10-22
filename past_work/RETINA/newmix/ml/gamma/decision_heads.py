"""
Jev/Laya-inspired decision heads (research branch `jev-architecture`).

Reuses the EXISTING encoders + token-level cross-modal fusion from model.py
(unmodified) and swaps only what sits on top of the fused token sequence:

  head="mlp"    original mean-pool + MLP head (control)
  head="cl"     cumulative-link ordinal head (one latent severity score +
                K-1 ordered thresholds) -- proper for ordinal grades
  head="query"  Laya-style option-marker head: one learned query per answer
                option cross-attends to the fused tokens through a small
                Transformer decoder; each option's output is scored to a
                logit. An extra "act" query predicts whether the model's own
                answer is correct (learned deferral signal).

Losses (see `decision_loss`):
  "focal_w"  class-weighted focal loss (the project's existing baseline)
  "ce"       plain unweighted cross-entropy (= log score)
  "nll_rps"  log score + Ranked Probability Score (both strictly proper;
             RPS is the ordinal one)
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from model import GammaMultimodalModel

K = 3


def rps_loss(probs: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    cp = probs.cumsum(-1)[:, :-1]
    co = F.one_hot(y, K).float().cumsum(-1)[:, :-1]
    return ((cp - co) ** 2).sum(-1).mean() / (K - 1)


class CumulativeLinearHead(nn.Module):
    """P(y<=k) = sigmoid(theta_k - s). Thresholds are kept ordered by
    construction (first threshold + cumulative softplus increments)."""

    def __init__(self, dim: int):
        super().__init__()
        self.score = nn.Sequential(
            nn.LayerNorm(dim), nn.Linear(dim, dim // 2), nn.GELU(), nn.Dropout(0.3), nn.Linear(dim // 2, 1)
        )
        self.theta0 = nn.Parameter(torch.tensor(-0.5))
        self.raw_gap = nn.Parameter(torch.zeros(K - 2))

    def thresholds(self) -> torch.Tensor:
        gaps = F.softplus(self.raw_gap) + 1e-3
        return torch.cat([self.theta0.view(1), self.theta0 + gaps.cumsum(0)])

    def forward(self, pooled: torch.Tensor) -> torch.Tensor:
        """Returns log-probabilities over the K ordered classes."""
        s = self.score(pooled)  # (B,1)
        cum = torch.sigmoid(self.thresholds().unsqueeze(0) - s)  # (B,K-1) = P(y<=k)
        cum = torch.cat([torch.zeros_like(cum[:, :1]), cum, torch.ones_like(cum[:, :1])], dim=1)
        probs = (cum[:, 1:] - cum[:, :-1]).clamp_min(1e-8)
        return probs.log()


class OptionQueryHead(nn.Module):
    """Laya's option-marker idea without the text encoder: K label-specific
    queries (+1 'act' query) attend over the fused multimodal tokens.
    Queries may attend to each other (options compete, as in Laya's shared
    sequence) and to the evidence tokens (cross-attention)."""

    def __init__(self, dim: int, num_layers: int = 2, num_heads: int = 4, ff_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        self.queries = nn.Parameter(torch.randn(1, K + 1, dim) * 0.02)  # K options + act
        layer = nn.TransformerDecoderLayer(
            d_model=dim, nhead=num_heads, dim_feedforward=ff_dim, dropout=dropout, batch_first=True, norm_first=True
        )
        self.decoder = nn.TransformerDecoder(layer, num_layers=num_layers)
        self.norm = nn.LayerNorm(dim)
        self.option_score = nn.Linear(dim, 1)
        self.act_score = nn.Linear(dim, 1)

    def forward(self, tokens: torch.Tensor):
        b = tokens.shape[0]
        h = self.norm(self.decoder(self.queries.expand(b, -1, -1), tokens))  # (B,K+1,D)
        option_logits = self.option_score(h[:, :K]).squeeze(-1)  # (B,K)
        act_logit = self.act_score(h[:, K]).squeeze(-1)  # (B,)
        return option_logits, act_logit


class DecisionHeadModel(nn.Module):
    def __init__(
        self,
        head: str = "mlp",
        fundus_encoder: str = "efficientnet_b0",
        oct_encoder: str = "resnet18",
        fusion_dim: int = 256,
        modality_dropout: float = 0.15,
        pretrained: bool = True,
    ):
        super().__init__()
        assert head in ("mlp", "cl", "query")
        self.head_type = head
        base = GammaMultimodalModel(
            fundus_encoder=fundus_encoder,
            oct_encoder=oct_encoder,
            fusion_dim=fusion_dim,
            modality_dropout=modality_dropout,
            pretrained=pretrained,
            modality="fusion",
            fusion_type="token",
        )
        self.fundus_encoder = base.fundus_encoder
        self.oct_encoder = base.oct_encoder
        self.modality_dropout = base.modality_dropout
        self.fusion = base.fusion  # TokenCrossModalFusion (modality_embed + encoder)
        if head == "mlp":
            self.head = base.head
        elif head == "cl":
            self.head = CumulativeLinearHead(fusion_dim)
        else:
            self.head = OptionQueryHead(fusion_dim)

    def fused_tokens(self, fundus: torch.Tensor, oct_vol: torch.Tensor) -> torch.Tensor:
        ft = self.fundus_encoder(fundus, return_tokens=True)
        ot = self.oct_encoder(oct_vol, return_tokens=True)
        ft, ot = self.modality_dropout(ft, ot)
        ft = ft + self.fusion.modality_embed[:, 0:1, :]
        ot = ot + self.fusion.modality_embed[:, 1:2, :]
        return self.fusion.encoder(torch.cat([ft, ot], dim=1))  # (B, Nf+No, D)

    def forward(self, fundus: torch.Tensor, oct_vol: torch.Tensor):
        """Returns (log_probs (B,K), act_logit (B,) or None)."""
        tokens = self.fused_tokens(fundus, oct_vol)
        if self.head_type == "mlp":
            return F.log_softmax(self.head(tokens.mean(1)), dim=-1), None
        if self.head_type == "cl":
            return self.head(tokens.mean(1)), None
        logits, act = self.head(tokens)
        return F.log_softmax(logits, dim=-1), act


def decision_loss(kind: str, log_probs: torch.Tensor, y: torch.Tensor, class_w: torch.Tensor | None = None,
                  gamma: float = 2.0) -> torch.Tensor:
    if kind == "focal_w":
        lp_t = log_probs.gather(1, y[:, None]).squeeze(1)
        loss = -((1 - lp_t.exp()) ** gamma) * lp_t
        if class_w is not None:
            loss = loss * class_w[y]
        return loss.mean()
    if kind == "ce":
        return F.nll_loss(log_probs, y)
    if kind == "nll_rps":
        return F.nll_loss(log_probs, y) + rps_loss(log_probs.exp(), y)
    raise ValueError(kind)


def act_loss(act_logit: torch.Tensor, log_probs: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """BCE on 'was the model's own (detached) answer correct?'."""
    correct = (log_probs.detach().argmax(-1) == y).float()
    return F.binary_cross_entropy_with_logits(act_logit, correct)
