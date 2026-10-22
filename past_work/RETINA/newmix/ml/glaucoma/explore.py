"""Round-2 experiments: which changes actually help? All patient-grouped 5-fold CV,
same folds as every other result, seeds 42/43/44, fixed epoch budget.

  oct      variants of the OCT CNN: full vs disc-crop, CE vs ordinal, with/without RNFL/GCC auxiliary head
  clinical clinical ensemble (logreg + rf + hgb averaged)
  early    early fusion: PCA of frozen OCT features appended to the clinical features

Writes ml/results/explore/*.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import timm
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from oct_model import MEAN, STD, augment
from research_data import ROOT, STRUCT_FEATURES, assign_folds, load_master
from train_clinical import make_model, score

OUT = ROOT / "ml" / "results" / "explore"
DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu")
AUX = ["RNFL_Avg", "RNFL_S", "RNFL_I", "RNFL_N", "RNFL_T", "GCC_Avg", "GCC_SUPERIOR", "GCC_INFERIOR",
       "GCC_ST", "GCC_SN", "GCC_IT", "GCC_IN"]


def load_img(path, crop: bool):
    im = Image.open(path).convert("L")
    w, h = im.size
    if crop:  # optic-nerve-head region: the cup sits in the central part of every scan
        im = im.crop((int(0.2 * w), int(0.1 * h), int(0.8 * w), int(0.9 * h))).resize((288, 256), Image.BILINEAR)
    else:
        im = im.crop((3, 3, w - 3, h - 3)).resize((336, 224), Image.BILINEAR)
    return torch.from_numpy(np.asarray(im, dtype=np.float32) / 255.0).unsqueeze(0)


class Net(nn.Module):
    def __init__(self, ordinal: bool, aux: bool):
        super().__init__()
        self.b = timm.create_model("resnet18.a1_in1k", pretrained=True, num_classes=0)
        self.drop = nn.Dropout(0.3)
        self.ordinal = ordinal
        self.cls = nn.Linear(512, 3 if ordinal else 4)
        self.aux = nn.Linear(512, len(AUX)) if aux else None

    def forward(self, x):
        f = self.drop(self.b(((x - MEAN) / STD).expand(-1, 3, -1, -1)))
        return self.cls(f), (self.aux(f) if self.aux is not None else None)

    def probs(self, logits):
        if not self.ordinal:
            return torch.softmax(logits, 1)
        s = torch.sigmoid(logits)                                  # P(y > k), k = 0,1,2
        s = torch.cummin(s, dim=1).values                          # enforce monotone
        p = torch.stack([1 - s[:, 0], s[:, 0] - s[:, 1], s[:, 1] - s[:, 2], s[:, 2]], 1)
        return p.clamp_min(1e-6) / p.clamp_min(1e-6).sum(1, keepdim=True)


def fit_predict(X, y, A, tr, te, ordinal, aux, seed, epochs=30, bs=16, lr=3e-4):
    torch.manual_seed(seed)
    np.random.seed(seed)
    m = Net(ordinal, aux).to(DEV)
    opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=1e-2)
    steps = epochs * int(np.ceil(len(tr) / bs))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps, pct_start=0.15)
    cnt = np.bincount(y[tr], minlength=4).astype(float)
    w = torch.tensor((cnt.sum() / (4 * np.maximum(cnt, 1))) ** 0.5, dtype=torch.float32, device=DEV)
    Xg, yg, Ag = X.to(DEV), torch.tensor(y, device=DEV), torch.tensor(A, dtype=torch.float32, device=DEV)
    scaler = torch.amp.GradScaler("cuda", enabled=DEV.type == "cuda")
    for _ in range(epochs):
        m.train()
        perm = torch.tensor(np.random.permutation(tr), device=DEV)
        for i in range(0, len(perm), bs):
            idx = perm[i:i + bs]
            if len(idx) < 2:
                continue
            with torch.autocast(DEV.type, dtype=torch.float16, enabled=DEV.type == "cuda"):
                logits, a = m(augment(Xg[idx]))
                logits = logits.float()
                if ordinal:
                    tgt = (yg[idx].unsqueeze(1) > torch.arange(3, device=DEV)).float()
                    loss = F.binary_cross_entropy_with_logits(logits, tgt, weight=w[yg[idx]].unsqueeze(1))
                else:
                    loss = F.cross_entropy(logits, yg[idx], weight=w, label_smoothing=0.1)
                if aux:
                    loss = loss + 0.5 * F.mse_loss(a.float(), Ag[idx])
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
    m.eval()
    with torch.no_grad():
        out = []
        for i in range(0, len(te), 32):
            logits, _ = m(Xg[te[i:i + 32]])
            out.append(m.probs(logits.float()).cpu())
    return torch.cat(out).numpy()


def summarise(runs):
    keys = ("accuracy", "balanced_accuracy", "qwk")
    s = {k: [round(float(np.mean([r["multiclass"][k] for r in runs])), 4), round(float(np.std([r["multiclass"][k] for r in runs])), 4)] for k in keys}
    s["auc"] = [round(float(np.mean([r["binary"]["auc"] for r in runs])), 4), round(float(np.std([r["binary"]["auc"] for r in runs])), 4)]
    return s


def cmd_oct(a):
    df = load_master()
    y = df.label.values
    A = df[AUX].values.astype(float)
    res = {}
    variants = [v.split(":") for v in a.variants.split(",")]  # crop:ordinal:aux as 0/1
    cache = {}
    for crop, ordn, aux in variants:
        name = f"crop{crop}_ord{ordn}_aux{aux}"
        crop, ordn, aux = bool(int(crop)), bool(int(ordn)), bool(int(aux))
        if crop not in cache:
            cache[crop] = torch.stack([load_img(p, crop) for p in df.image])
        X = cache[crop]
        runs, t = [], time.time()
        for seed in (42, 43, 44):
            folds = assign_folds(df, 5, seed)
            oof = np.zeros((len(df), 4))
            for f in range(5):
                tr, te = np.where(folds != f)[0], np.where(folds == f)[0]
                Az = (A - A[tr].mean(0)) / (A[tr].std(0) + 1e-6)     # standardise with training fold only
                oof[te] = fit_predict(X, y, Az, tr, te, ordn, aux, seed + f)
            runs.append({"multiclass": score(y, oof, "multiclass"),
                         "binary": score(df.binary.values, np.stack([oof[:, 0], 1 - oof[:, 0]], 1), "binary")})
            if seed == 42:
                np.save(OUT / f"oof_{name}.npy", oof)
        res[name] = summarise(runs)
        print(f"{name:24s} {res[name]}  ({time.time() - t:.0f}s)", flush=True)
    p = OUT / "oct_variants.json"
    old = json.loads(p.read_text()) if p.exists() else {}
    old.update(res)
    p.write_text(json.dumps(old, indent=2))


def cmd_clinical(a):
    df = load_master()
    y = df.label.values
    runs = []
    for seed in (42, 43, 44):
        folds = assign_folds(df, 5, seed)
        oof = np.zeros((len(df), 4))
        for f in range(5):
            tr, te = folds != f, folds == f
            ps = [make_model(n, seed).fit(df.loc[tr, STRUCT_FEATURES], y[tr]).predict_proba(df.loc[te, STRUCT_FEATURES]) for n in ("logreg", "rf", "hgb")]
            oof[te] = np.mean(ps, 0)
        runs.append({"multiclass": score(y, oof, "multiclass"), "binary": score(df.binary.values, np.stack([oof[:, 0], 1 - oof[:, 0]], 1), "binary")})
    r = summarise(runs)
    print("clinical ensemble", r)
    (OUT / "clinical_ensemble.json").write_text(json.dumps(r, indent=2))


@torch.no_grad()
def frozen_features(df, crop):
    m = timm.create_model("efficientnet_b0.ra_in1k", pretrained=True, num_classes=0).to(DEV).eval()
    X = torch.stack([load_img(p, crop) for p in df.image])
    out = []
    for i in range(0, len(X), 32):
        x3 = ((X[i:i + 32].to(DEV) - MEAN) / STD).expand(-1, 3, -1, -1)
        out.append(((m(x3) + m(torch.flip(x3, dims=[3]))) / 2).cpu())
    return torch.cat(out).numpy()


def cmd_early(a):
    df = load_master()
    y = df.label.values
    res = {}
    for crop in (False, True):
        Fimg = frozen_features(df, crop)
        for k in (4, 8, 16):
            for algo in ("logreg", "rf"):
                runs = []
                for seed in (42, 43, 44):
                    folds = assign_folds(df, 5, seed)
                    oof = np.zeros((len(df), 4))
                    for f in range(5):
                        tr, te = folds != f, folds == f
                        pca = make_pipeline(StandardScaler(), PCA(k, random_state=0)).fit(Fimg[tr])
                        imp = SimpleImputer(strategy="median").fit(df.loc[tr, STRUCT_FEATURES])
                        Xtr = np.hstack([imp.transform(df.loc[tr, STRUCT_FEATURES]), pca.transform(Fimg[tr])])
                        Xte = np.hstack([imp.transform(df.loc[te, STRUCT_FEATURES]), pca.transform(Fimg[te])])
                        oof[te] = make_model(algo, seed).fit(Xtr, y[tr]).predict_proba(Xte)
                    runs.append({"multiclass": score(y, oof, "multiclass"), "binary": score(df.binary.values, np.stack([oof[:, 0], 1 - oof[:, 0]], 1), "binary")})
                name = f"early_crop{int(crop)}_pca{k}_{algo}"
                res[name] = summarise(runs)
                print(f"{name:28s} {res[name]}", flush=True)
    (OUT / "early_fusion.json").write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["oct", "clinical", "early"])
    ap.add_argument("--variants", default="0:0:0,1:0:0,0:1:0,0:0:1,1:1:1")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"oct": cmd_oct, "clinical": cmd_clinical, "early": cmd_early}[a.cmd](a)
