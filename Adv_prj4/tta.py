"""
Test-time augmentation (TTA) for the multi-modal severity model.

Applies a small set of label-preserving image transforms (horizontal flip,
slight brightness jitter) independently to each of the three image
branches, averages the softmax outputs across augmented copies, and
leaves the tabular branch untouched (flipping RNFL/GCC numbers has no
meaning). This trades inference latency for a few points of robustness
against sensor/scan noise — worth it here since inference is offline,
not real-time.
"""

from __future__ import annotations

import numpy as np


def _augmentations():
    """Each entry maps an image batch (B, H, W, C) in [0, 1] -> augmented batch."""
    return [
        lambda x: x,  # identity
        lambda x: x[:, :, ::-1, :],  # horizontal flip
        lambda x: np.clip(x * 1.1, 0.0, 1.0),  # brighten
        lambda x: np.clip(x * 0.9, 0.0, 1.0),  # darken
    ]


def predict_with_tta(model, fundus, hvf, oct_img, tabular, image_keys=("fundus", "hvf", "oct")):
    """Runs inference multiple times with image-only augmentations and
    averages the resulting class probabilities.

    fundus, hvf, oct_img: (B, H, W, C) float arrays in [0, 1]
    tabular: (B, 12) float array, passed through unaugmented
    """
    augs = _augmentations()
    all_preds = []
    for aug in augs:
        inputs = {
            "fundus_input": aug(fundus),
            "hvf_input": aug(hvf),
            "oct_input": aug(oct_img),
            "tabular_input": tabular,
        }
        all_preds.append(model.predict(inputs, verbose=0))
    return np.mean(all_preds, axis=0)
