"""Frozen-backbone linear probe on OCT B-scans (same patient-grouped folds).

With ~300 images, fine-tuning a CNN can overfit; a logistic head on frozen
ImageNet features is a strong, cheap baseline. Writes the same OOF format as
train_oct.py so eval_fusion.py can use either.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import timm
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from oct_model import MEAN, STD, load_image_tensor
from research_data import ROOT, assign_folds, load_master
from train_clinical import score

OUT = ROOT / "ml" / "results" / "oct"
DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BACKBONES = {"resnet18": "resnet18.a1_in1k", "efficientnet_b0": "efficientnet_b0.ra_in1k"}


@torch.no_grad()
def features(name: str, X: torch.Tensor) -> np.ndarray:
    m = timm.create_model(BACKBONES[name], pretrained=True, num_classes=0).to(DEV).eval()
    out = []
    for i in range(0, len(X), 32):
        xb = X[i:i + 32].to(DEV)
        x3 = ((xb - MEAN) / STD).expand(-1, 3, -1, -1)
        out.append(((m(x3) + m(torch.flip(x3, dims=[3]))) / 2).cpu())  # flip-TTA on features
    return torch.cat(out).numpy()


def main():
    df = load_master()
    X = torch.stack([load_image_tensor(p) for p in df.image])
    y = df.label.values
    res = {}
    for name in BACKBONES:
        F = features(name, X)
        for C in (0.01, 0.1):
            runs = []
            for seed in (42, 43, 44):
                folds = assign_folds(df, 5, seed)
                oof = np.zeros((len(df), 4))
                for f in range(5):
                    tr, te = folds != f, folds == f
                    clf = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000, class_weight="balanced"))
                    oof[te] = clf.fit(F[tr], y[tr]).predict_proba(F[te])
                sc = score(y, oof, "multiclass")
                sb = score(df.binary.values, np.stack([oof[:, 0], 1 - oof[:, 0]], 1), "binary")
                runs.append({"multiclass": sc, "binary": sb})
                if seed == 42:
                    pd.DataFrame(oof, columns=[f"p{i}" for i in range(4)]).assign(y=y, fold=folds, si=df.si, source=df.source).to_csv(
                        OUT / f"oof_probe_{name}_C{C}_seed42.csv", index=False)
            key = f"probe_{name}_C{C}"
            res[key] = {"epochs": 0, "seeds": "42,43,44", "runs": runs}
            print(f"{key:28s} acc={np.mean([r['multiclass']['accuracy'] for r in runs]):.3f} "
                  f"bal={np.mean([r['multiclass']['balanced_accuracy'] for r in runs]):.3f} "
                  f"auc={np.mean([r['binary']['auc'] for r in runs]):.3f}", flush=True)
    p = OUT / "cv_summary.json"
    old = json.loads(p.read_text()) if p.exists() else {}
    old.update(res)
    p.write_text(json.dumps(old, indent=2))


if __name__ == "__main__":
    main()
