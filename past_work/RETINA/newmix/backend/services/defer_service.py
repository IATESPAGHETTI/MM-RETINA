"""Defer-to-visual-field policy: when a model's top-class probability is below its
cut-off, the app withholds the stage and recommends a visual-field (HVF) test.

Cut-offs come from ml/glaucoma/make_defer.py (out-of-fold predictions, never training-set
confidence). The evidence quoted to the user is read from the same file.
"""

from __future__ import annotations

from core import RESULTS_DIR, read_json

_cfg: dict = {}


def load() -> dict:
    _cfg.clear()
    _cfg.update(read_json(RESULTS_DIR / "clinical" / "defer.json", {}) or {})
    return status()


def status() -> dict:
    return {"ready": all(k in _cfg for k in ("clinical", "oct", "fused")), "heads": [k for k in _cfg if k != "note"]}


def decide(head: str, confidence: float) -> dict | None:
    """-> None when no cut-off is configured (the UI then shows the stage as before)."""
    c = _cfg.get(head)
    if not c:
        return None
    deferred = confidence < c["threshold"]
    reliable = head != "oct"  # OCT alone stays near chance even after deferral; never presented as dependable
    return {
        "head": head,
        "deferred": bool(deferred),
        "confidence": round(float(confidence), 4),
        "threshold": c["threshold"],
        "coverage": c["target_coverage"],
        "accuracy_if_answered": c["accuracy_answered"],
        "accuracy_if_deferred": c["accuracy_deferred"],
        "reliable_head": reliable,
        "action": (
            "Inconclusive: confidence is below the cut-off, so no stage is given. "
            "In cross-validation, cases like this were staged correctly only "
            f"{c['accuracy_deferred'] * 100:.0f}% of the time. Order a visual-field (HVF) test, whose mean deviation defines the stage."
            if deferred else
            f"Above the confidence cut-off. Across cross-validation the model answers about {c['target_coverage'] * 100:.0f}% "
            f"of cases and stages those correctly {c['accuracy_answered'] * 100:.0f}% of the time."
        ),
    }
