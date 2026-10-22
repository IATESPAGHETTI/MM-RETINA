"""Patient-grouped 5-fold CV for the OCT B-scan model + final fit.

Fixed epoch budget with a cosine schedule: nothing is selected on the held-out
fold (best-epoch selection on the reporting fold inflates accuracy by 3-4
points, see PROGRESS.md of MM-RETINA). Out-of-fold probabilities are written
so late fusion with the clinical model uses identical folds.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).parent))
from oct_model import OCTNet, augment, load_image_tensor
from research_data import CLASS_NAMES, ROOT, assign_folds, load_master
from train_clinical import score

OUT = ROOT / "ml" / "results" / "oct"
MODELS = ROOT / "models"
DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def fit(arch, X, y, epochs, seed, Xte=None, bs=16, lr=3e-4):
    torch.manual_seed(seed)
    np.random.seed(seed)
    m = OCTNet(arch).to(DEV)
    cnt = np.bincount(y, minlength=4).astype(float)
    w = torch.tensor((cnt.sum() / (4 * np.maximum(cnt, 1))) ** 0.5, dtype=torch.float32, device=DEV)
    crit = nn.CrossEntropyLoss(weight=w, label_smoothing=0.1)
    opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=1e-2)
    steps = epochs * int(np.ceil(len(X) / bs))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps, pct_start=0.15)
    scaler = torch.amp.GradScaler("cuda", enabled=DEV.type == "cuda")
    Xg, yg = X.to(DEV), torch.tensor(y, device=DEV)
    for ep in range(epochs):
        m.train()
        perm = torch.randperm(len(Xg), device=DEV)
        for i in range(0, len(perm), bs):
            idx = perm[i:i + bs]
            if len(idx) < 2:
                continue
            xb = augment(Xg[idx])
            with torch.autocast(DEV.type, dtype=torch.float16, enabled=DEV.type == "cuda"):
                loss = crit(m(xb), yg[idx])
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
    if Xte is None:
        return m
    return m, predict(m, Xte)


@torch.no_grad()
def predict(m, X, bs=32):
    m.eval()
    out = []
    for i in range(0, len(X), bs):
        xb = X[i:i + bs].to(DEV)
        with torch.autocast(DEV.type, dtype=torch.float16, enabled=DEV.type == "cuda"):
            out.append(torch.softmax(m(xb).float(), 1).cpu())
    return torch.cat(out).numpy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archs", default="resnet18,hybrid,efficientnet_b0")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--seeds", default="42")
    ap.add_argument("--final", default="", help="arch to fit on all 303 eyes and save")
    ap.add_argument("--final-seeds", default="42,43,44")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    df = load_master()
    X = torch.stack([load_image_tensor(p) for p in df.image])
    y = df.label.values
    print("images", tuple(X.shape), "device", DEV, flush=True)
    summary = {}
    for arch in [s for s in a.archs.split(",") if s]:
        per_seed, t0 = [], time.time()
        for seed in map(int, a.seeds.split(",")):
            folds = assign_folds(df, 5, seed)
            oof = np.zeros((len(df), 4))
            for f in range(5):
                tr, te = np.where(folds != f)[0], np.where(folds == f)[0]
                _, oof[te] = fit(arch, X[tr], y[tr], a.epochs, seed + f, X[te])
            sc = score(y, oof, "multiclass")
            sc_bin = score(df.binary.values, np.stack([oof[:, 0], 1 - oof[:, 0]], 1), "binary")
            per_seed.append({"multiclass": sc, "binary": sc_bin})
            pd.DataFrame(oof, columns=[f"p{i}" for i in range(4)]).assign(
                y=y, fold=folds, si=df.si, source=df.source).to_csv(OUT / f"oof_{arch}_seed{seed}.csv", index=False)
            print(f"{arch:16s} seed {seed}: acc={sc['accuracy']:.3f} bal={sc['balanced_accuracy']:.3f} "
                  f"qwk={sc['qwk']:.3f} | binary acc={sc_bin['accuracy']:.3f} auc={sc_bin['auc']:.3f} "
                  f"({time.time() - t0:.0f}s)", flush=True)
        summary[arch] = per_seed
    if summary:
        p = OUT / "cv_summary.json"
        old = json.loads(p.read_text()) if p.exists() else {}
        old.update({k: {"epochs": a.epochs, "seeds": a.seeds, "runs": v} for k, v in summary.items()})
        p.write_text(json.dumps(old, indent=2))
    if a.final:
        sd = []
        for s in map(int, a.final_seeds.split(",")):
            m = fit(a.final, X, y, a.epochs, s)
            sd.append({k: v.cpu() for k, v in m.state_dict().items()})
        torch.save({"arch": a.final, "state_dicts": sd, "classes": CLASS_NAMES, "epochs": a.epochs,
                    "img_hw": [224, 336]}, MODELS / "oct_research.pt")
        print("saved", MODELS / "oct_research.pt")


if __name__ == "__main__":
    main()
