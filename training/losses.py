"""Focal loss for the 3-class Normal/Early/Progressive head, plus a helper
to compute inverse-frequency class weights from a real training split
(never hand-picked)."""

from __future__ import annotations

from collections import Counter

import torch
import torch.nn as nn
import torch.nn.functional as F


def class_weights_from_counts(counts: dict[str, int], grade_names: list[str]) -> torch.Tensor:
    total = sum(counts.values())
    weights = [total / (len(grade_names) * counts.get(g, 1)) for g in grade_names]
    return torch.tensor(weights, dtype=torch.float32)


class FocalLoss(nn.Module):
    def __init__(self, gamma: float = 2.0, weight: torch.Tensor | None = None):
        super().__init__()
        self.gamma = gamma
        self.register_buffer("weight", weight if weight is not None else None, persistent=False)

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        log_probs = F.log_softmax(logits, dim=-1)
        probs = log_probs.exp()
        target_log_probs = log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        target_probs = probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        focal_term = (1 - target_probs) ** self.gamma
        loss = -focal_term * target_log_probs
        if self.weight is not None:
            loss = loss * self.weight[targets]
        return loss.mean()
