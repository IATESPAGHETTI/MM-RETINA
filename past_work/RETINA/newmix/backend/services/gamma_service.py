"""GAMMA multimodal (fundus + OCT volume) glaucoma grading: Normal / Early / Progressive.

Thin wrapper over the MM-RETINA inference code in `_gamma/` (unchanged except
for its checkpoint path). These are the single-split demonstration checkpoints,
not the 5-fold CV models; /api/models reports the CV numbers separately.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "_gamma"))
import inference as _inf  # noqa: E402


def load() -> dict:
    return _inf.load_all_models()


def is_ready(modality: str) -> bool:
    return _inf.is_ready(modality)


def expected_slices(modality: str):
    return _inf.expected_oct_slices(modality)


check_sanity = _inf.check_modality_sanity
predict = _inf.predict
