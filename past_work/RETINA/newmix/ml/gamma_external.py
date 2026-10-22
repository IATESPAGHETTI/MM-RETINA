"""External check of the MM-RETINA fundus model on the Sankara fundus photographs.

Label mapping is exact, not approximate: GAMMA grades from visual-field MD with the same
cut-offs as the Sankara labels (Early: MD > -6 dB; Intermediate/Advanced: MD <= -6 dB, which GAMMA
groups as "progressive"). So Sankara Mild -> early, Moderate/Severe -> progressive.
There are no normal eyes in this set, so a "normal" prediction is a missed glaucoma.

Privacy: everything outside the circular retinal field is blacked out before inference,
which removes the burned-in identifier text in the corner. Nothing is saved.

    python ml/gamma_external.py <.../Glaucoma AI Project 1/Fundus image>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "services" / "_gamma"))
import inference  # noqa: E402

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\ASUS\Downloads\prj4\past_work\data\retinal-imaging-research\Glaucoma AI Project 1\Fundus image")
MAP = {"Mild": "early", "Moderate": "progressive", "Severe": "progressive"}


def mask_outside_field(img: Image.Image) -> Image.Image:
    w, h = img.size
    r = 0.49 * min(w, h)
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).ellipse((w / 2 - r, h / 2 - r, w / 2 + r, h / 2 + r), fill=255)
    return Image.composite(img.convert("RGB"), Image.new("RGB", (w, h)), m)


def main():
    status = inference.load_all_models()
    assert "fundus" in status["loaded"], status
    rows = []
    for sev, target in MAP.items():
        for p in sorted((SRC / sev).glob("*.jpg")):
            r = inference.predict("fundus", mask_outside_field(Image.open(p)))
            rows.append({"severity": sev, "target": target, "pred": r["prediction"], **{f"p_{k}": v for k, v in r["probabilities"].items()}})
    y = np.array([r["target"] == "progressive" for r in rows])
    pp = np.array([r["p_progressive"] for r in rows])
    pred = np.array([r["pred"] for r in rows])
    out = {
        "model": "fundus_run1 (single-split demo checkpoint)",
        "n": len(rows), "counts": {k: int(sum(r["severity"] == k for r in rows)) for k in MAP},
        "accuracy_3class": round(float((pred == np.array([r["target"] for r in rows])).mean()), 4),
        "predicted_normal_rate": round(float((pred == "normal").mean()), 4),
        "auc_progressive_vs_early": round(float(roc_auc_score(y, pp)), 4),
        "pred_distribution": {k: int((pred == k).sum()) for k in ("normal", "early", "progressive")},
        "by_true_class": {k: {c: int(((pred == c) & np.array([r["severity"] == k for r in rows])).sum()) for c in ("normal", "early", "progressive")} for k in MAP},
    }
    (ROOT / "ml" / "results" / "gamma_external_sankara.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
