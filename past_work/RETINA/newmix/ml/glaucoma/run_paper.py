"""Paper-architecture experiments on the Research OCT cohort.

  bench   time one epoch
  tune    pick hyper-parameters on an INNER validation split of fold 0's training eyes only
          (the held-out folds never influence the choice)
  cv      patient-grouped 5-fold CV with the chosen config (honest number)
  leaky   the paper's apparent protocol: augment 303 -> 1818 images, then a random image-level
          70/20/10 split, best-validation-epoch checkpoint. Run to measure how much that protocol inflates results.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedGroupKFold, train_test_split

sys.path.insert(0, str(Path(__file__).parent))
from paper_hybrid import PaperHybrid, paper_augment, preprocess_paper
from research_data import ROOT, assign_folds, load_master
from train_clinical import score

OUT = ROOT / "ml" / "results" / "paper"
CACHE = OUT / "pre512.npy"
DEV = torch.device("cuda")
DEFAULT = {"lr_bb": 1e-4, "lr_rest": 1e-4, "epochs": 25, "bs": 8, "ls": 0.0}


def load_cache(df) -> torch.Tensor:
    OUT.mkdir(parents=True, exist_ok=True)
    if CACHE.exists():
        arr = np.load(CACHE)
    else:
        arr = np.stack([preprocess_paper(p) for p in df.image])
        np.save(CACHE, arr)
    return torch.from_numpy(arr)  # uint8 (N,512,512)


def batch(X: torch.Tensor, idx) -> torch.Tensor:
    return (X[idx].to(DEV, non_blocking=True).float() / 255.0).unsqueeze(1)


@torch.no_grad()
def predict(m, X, idx, bs=16):
    m.eval()
    out = []
    for i in range(0, len(idx), bs):
        with torch.autocast("cuda", dtype=torch.float16):
            out.append(torch.softmax(m(batch(X, idx[i:i + bs])).float(), 1).cpu())
    return torch.cat(out).numpy()


def fit(X, y, tr, cfg, seed, online_aug=True, val=None, log=None):
    """Train on indices `tr`. If `val` is given, keep the best-validation-loss weights (Keras-ModelCheckpoint style)."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    m = PaperHybrid().to(DEV)
    opt = torch.optim.Adam(m.param_groups(cfg["lr_bb"], cfg["lr_rest"]))
    cnt = np.bincount(y[tr], minlength=4).astype(float)
    w = torch.tensor((cnt.sum() / (4 * np.maximum(cnt, 1))) ** 0.5, dtype=torch.float32, device=DEV)
    crit = nn.CrossEntropyLoss(weight=w, label_smoothing=cfg["ls"])
    scaler = torch.amp.GradScaler("cuda")
    yt = torch.tensor(y, device=DEV)
    best, best_loss = None, 1e9
    for ep in range(cfg["epochs"]):
        m.train()
        perm = np.random.permutation(tr)
        for i in range(0, len(perm), cfg["bs"]):
            idx = perm[i:i + cfg["bs"]]
            if len(idx) < 2:
                continue
            xb = batch(X, idx)
            if online_aug:
                xb = paper_augment(xb)
            with torch.autocast("cuda", dtype=torch.float16):
                loss = crit(m(xb).float(), yt[idx])
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
        if val is not None:
            p = predict(m, X, val)
            vl = float(-np.log(np.clip(p[np.arange(len(val)), y[val]], 1e-8, 1)).mean())
            if vl < best_loss:
                best_loss, best = vl, copy.deepcopy(m.state_dict())
        if log:
            log(f"  ep {ep + 1}/{cfg['epochs']}")
    if best is not None:
        m.load_state_dict(best)
    return m


def cmd_bench(a):
    df = load_master()
    X, y = load_cache(df), df.label.values
    t = time.time()
    fit(X, y, np.arange(240), {**DEFAULT, "epochs": 1}, 0)
    print(f"1 epoch on 240 images: {time.time() - t:.1f}s; peak mem {torch.cuda.max_memory_allocated() / 1e9:.2f} GB")


CONFIGS = {
    "paper_spec": {**DEFAULT},
    "diff_lr": {**DEFAULT, "lr_bb": 3e-5, "lr_rest": 3e-4},
    "diff_lr_smooth": {**DEFAULT, "lr_bb": 3e-5, "lr_rest": 3e-4, "ls": 0.1, "epochs": 35},
}


def cmd_tune(a):
    df = load_master()
    X, y = load_cache(df), df.label.values
    folds = assign_folds(df, 5, 42)
    tr0 = np.where(folds != 0)[0]
    sgk = StratifiedGroupKFold(5, shuffle=True, random_state=0)
    i_tr, i_va = next(sgk.split(tr0, y[tr0], df.group.values[tr0]))
    tr, va = tr0[i_tr], tr0[i_va]
    res = {}
    for name, cfg in CONFIGS.items():
        t = time.time()
        m = fit(X, y, tr, cfg, 1)
        p = predict(m, X, va)
        res[name] = {"cfg": cfg, "val_bal_acc": float(balanced_accuracy_score(y[va], p.argmax(1))), "val_acc": float((p.argmax(1) == y[va]).mean())}
        print(f"{name:16s} inner-val bal={res[name]['val_bal_acc']:.3f} acc={res[name]['val_acc']:.3f} ({time.time() - t:.0f}s)", flush=True)
    best = max(res, key=lambda k: res[k]["val_bal_acc"])
    res["chosen"] = best
    (OUT / "tune.json").write_text(json.dumps(res, indent=2))
    print("chosen:", best)


def cmd_cv(a):
    df = load_master()
    X, y = load_cache(df), df.label.values
    name = a.config or json.loads((OUT / "tune.json").read_text())["chosen"]
    cfg = CONFIGS[name]
    runs = []
    for seed in map(int, a.seeds.split(",")):
        folds = assign_folds(df, 5, seed)
        oof = np.zeros((len(df), 4))
        t = time.time()
        for f in range(5):
            tr, te = np.where(folds != f)[0], np.where(folds == f)[0]
            m = fit(X, y, tr, cfg, seed + f)
            oof[te] = predict(m, X, te)
            print(f"  seed {seed} fold {f} done ({time.time() - t:.0f}s)", flush=True)
        sc, sb = score(y, oof, "multiclass"), score(df.binary.values, np.stack([oof[:, 0], 1 - oof[:, 0]], 1), "binary")
        runs.append({"multiclass": sc, "binary": sb})
        pd.DataFrame(oof, columns=[f"p{i}" for i in range(4)]).assign(y=y, fold=folds, si=df.si, source=df.source).to_csv(
            OUT.parent / "oct" / f"oof_paper_hybrid_seed{seed}.csv", index=False)
        print(f"paper_hybrid[{name}] seed {seed}: acc={sc['accuracy']:.3f} bal={sc['balanced_accuracy']:.3f} qwk={sc['qwk']:.3f} "
              f"| binary acc={sb['accuracy']:.3f} auc={sb['auc']:.3f}", flush=True)
    p = OUT.parent / "oct" / "cv_summary.json"
    old = json.loads(p.read_text())
    old["paper_hybrid"] = {"epochs": cfg["epochs"], "seeds": a.seeds, "config": name, "runs": runs}
    p.write_text(json.dumps(old, indent=2))


def cmd_leaky(a):
    df = load_master()
    X, y = load_cache(df), df.label.values
    n = len(df)
    # 303 originals + 5 augmented copies each = 1818 (the paper's count)
    torch.manual_seed(0)
    copies, src = [X], [np.arange(n)]
    for _ in range(5):
        aug = torch.cat([(paper_augment(batch(X, np.arange(i, min(i + 32, n)))) * 255).byte().squeeze(1).cpu() for i in range(0, n, 32)])
        copies.append(aug)
        src.append(np.arange(n))
    XA, srcA = torch.cat(copies), np.concatenate(src)
    yA = y[srcA]
    grp = df.group.values[srcA]
    res = []
    for seed in map(int, a.seeds.split(",")):
        for mode in ("image_level_random (paper-style)", "patient_grouped"):
            if mode.startswith("image"):
                idx = np.arange(len(yA))
                rest, te = train_test_split(idx, test_size=0.10, stratify=yA, random_state=seed)
                tr, va = train_test_split(rest, test_size=2 / 9, stratify=yA[rest], random_state=seed)
            else:
                sgk = StratifiedGroupKFold(10, shuffle=True, random_state=seed)
                rest, te = next(sgk.split(np.arange(len(yA)), yA, grp))
                sgk2 = StratifiedGroupKFold(4, shuffle=True, random_state=seed)
                a_, b_ = next(sgk2.split(rest, yA[rest], grp[rest]))
                tr, va = rest[a_], rest[b_]
            sibling = float(np.isin(srcA[te], srcA[tr]).mean())
            m = fit(XA, yA, tr, {**DEFAULT, "epochs": a.epochs}, seed, online_aug=False, val=va)
            p = predict(m, XA, te)
            sc = score(yA[te], p, "multiclass")
            r = {"seed": seed, "protocol": mode, "n_train": len(tr), "n_test": len(te), "test_acc": sc["accuracy"],
                 "test_balanced_acc": sc["balanced_accuracy"], "test_images_with_sibling_in_train": round(sibling, 3)}
            res.append(r)
            print(r, flush=True)
    (OUT / "leaky_protocol.json").write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["bench", "tune", "cv", "leaky"])
    ap.add_argument("--config", default="")
    ap.add_argument("--seeds", default="42")
    ap.add_argument("--epochs", type=int, default=12)
    a = ap.parse_args()
    {"bench": cmd_bench, "tune": cmd_tune, "cv": cmd_cv, "leaky": cmd_leaky}[a.cmd](a)
