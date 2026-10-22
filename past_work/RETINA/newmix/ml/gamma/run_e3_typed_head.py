"""
E3 (jev-architecture branch): does a SHARED typed decision head help the
M01 multi-dataset setting? Extends EXP-M01 without touching it.

Arms (same folds, encoders, class-weighted loss and optimiser as M01 -- only
the head changes, so any difference is attributable to the head):
  m01a  independent trunks + per-dataset linear heads        (M01-A, control)
  m01b  ONE shared trunk  + per-dataset linear heads         (M01-B, control)
  m01c  shared trunk + ONE shared option-query decoder. Each option query =
        shared ordinal-rank embedding (0<1<2) + per-dataset embedding; all
        three label taxonomies are ordinal 3-level severities, so they are
        exposed to the decoder as the same typed question.
  m01d  shared trunk + ONE shared severity scorer with per-dataset
        cumulative-link thresholds (shared latent severity axis).

No cross-dataset patient pairing anywhere (each step uses each dataset's own
batch, as in M01). Protocols:
  P1  best summed-val-loss state (M01's own protocol; mildly optimistic)
  P2  fixed `--fixed-epochs`, no use of held-out data (honest)
Runs on CUDA when available (tiny feature models, full-batch).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train_multidataset_representation as m01  # noqa: E402
from decision_heads import rps_loss  # noqa: E402

REPO = m01.REPO_ROOT
OUT = REPO / "results" / "jev_architecture" / "e3"
DS = ["gamma", "hvf", "rnfl_gcc"]
D = m01.EMBED_DIM
M_TOK = 4  # tokens per dataset state for the decoder arm


class LinearBranch(nn.Module):
    def __init__(self, in_dim, trunk):
        super().__init__()
        self.b = m01.DatasetBranch(in_dim, trunk)

    def forward(self, x):
        return F.log_softmax(self.b(x), -1)


class SharedQueryDecoder(nn.Module):
    def __init__(self):
        super().__init__()
        layer = nn.TransformerDecoderLayer(D, 4, 128, 0.1, batch_first=True, norm_first=True)
        self.dec = nn.TransformerDecoder(layer, 2)
        self.norm = nn.LayerNorm(D)
        self.rank_emb = nn.Parameter(torch.randn(3, D) * 0.02)          # shared ordinal positions
        self.ds_emb = nn.ParameterDict({d: nn.Parameter(torch.randn(1, D) * 0.02) for d in DS})
        self.score = nn.Linear(D, 1)

    def forward(self, tokens, ds):
        q = (self.rank_emb + self.ds_emb[ds]).unsqueeze(0).expand(tokens.shape[0], -1, -1)
        return F.log_softmax(self.score(self.norm(self.dec(q, tokens))).squeeze(-1), -1)


class QueryBranch(nn.Module):
    def __init__(self, in_dim, trunk, decoder, ds):
        super().__init__()
        self.enc, self.trunk, self.decoder, self.ds = m01.Encoder(in_dim), trunk, decoder, ds
        self.tokens = nn.Linear(D, M_TOK * D)  # private state -> tokens adapter

    def forward(self, x):
        h = self.trunk(self.enc(x))
        return self.decoder(self.tokens(h).view(-1, M_TOK, D), self.ds)


class SharedScorer(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(D, D // 2), nn.ReLU(), nn.Dropout(0.2), nn.Linear(D // 2, 1))


class CLBranch(nn.Module):
    def __init__(self, in_dim, trunk, scorer):
        super().__init__()
        self.enc, self.trunk, self.scorer = m01.Encoder(in_dim), trunk, scorer
        self.theta0 = nn.Parameter(torch.tensor(-0.5))   # dataset-specific thresholds
        self.gap = nn.Parameter(torch.zeros(1))

    def forward(self, x):
        s = self.scorer.net(self.trunk(self.enc(x)))
        th = torch.cat([self.theta0.view(1), self.theta0 + F.softplus(self.gap) + 1e-3])
        cum = torch.sigmoid(th.unsqueeze(0) - s)
        cum = torch.cat([torch.zeros_like(cum[:, :1]), cum, torch.ones_like(cum[:, :1])], 1)
        return (cum[:, 1:] - cum[:, :-1]).clamp_min(1e-8).log()


def build_branches(arm, dims, dev):
    if arm == "m01a":
        return {d: LinearBranch(dims[d], m01.Trunk().to(dev)).to(dev) for d in DS}
    trunk = m01.Trunk().to(dev)
    if arm == "m01b":
        return {d: LinearBranch(dims[d], trunk).to(dev) for d in DS}
    if arm == "m01c":
        dec = SharedQueryDecoder().to(dev)
        return {d: QueryBranch(dims[d], trunk, dec, d).to(dev) for d in DS}
    if arm == "m01d":
        sc = SharedScorer().to(dev)
        return {d: CLBranch(dims[d], trunk, sc).to(dev) for d in DS}
    raise ValueError(arm)


def train(branches, batches, epochs, patience, lr, fixed):
    params, seen = [], set()
    for b in branches.values():
        for p in b.parameters():
            if id(p) not in seen:
                seen.add(id(p)); params.append(p)
    opt = torch.optim.Adam(params, lr=lr, weight_decay=1e-4)
    best, best_state, since = float("inf"), None, 0
    for ep in range(epochs):
        for b in branches.values():
            b.train()
        opt.zero_grad()
        loss = 0
        for d, (Xtr, ytr, w, _, _) in batches.items():
            loss = loss + F.nll_loss(branches[d](Xtr), ytr, weight=w)
        loss.backward(); opt.step()
        for b in branches.values():
            b.eval()
        with torch.no_grad():
            v = sum(F.nll_loss(branches[d](Xv), yv, weight=w).item() for d, (_, _, w, Xv, yv) in batches.items())
        if not fixed:
            if v < best - 1e-4:
                best, since = v, 0
                best_state = {d: {k: t.clone() for k, t in b.state_dict().items()} for d, b in branches.items()}
            else:
                since += 1
                if since >= patience:
                    break
    if not fixed and best_state is not None:
        for d, b in branches.items():
            b.load_state_dict(best_state[d])
    for b in branches.values():
        b.eval()


def run(arm, seed, protocol, args, data):
    """-> {dataset: (ids, y, probs)} pooled OOF."""
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pooled = {d: ([], [], []) for d in DS}
    for f in range(5):
        torch.manual_seed(seed * 100 + f)
        mats, ids = {}, {}
        for d in DS:
            df, cols, catcol, ycol, idcol = data[d]
            tr, va = df[df["fold"] != f], df[df["fold"] == f]
            Xtr, Xva = m01.build_fold_matrices(tr, va, cols, categorical_col=catcol)
            ytr, yva = tr[ycol].to_numpy(), va[ycol].to_numpy()
            cnt = Counter(ytr.tolist())
            w = torch.tensor([len(ytr) / (3 * cnt.get(c, 1)) for c in range(3)], dtype=torch.float32, device=dev)
            mats[d] = (torch.tensor(Xtr, device=dev), torch.tensor(ytr, dtype=torch.long, device=dev), w,
                       torch.tensor(Xva, device=dev), torch.tensor(yva, dtype=torch.long, device=dev))
            ids[d] = va[idcol].astype(str).tolist()
        branches = build_branches(arm, {d: mats[d][0].shape[1] for d in DS}, dev)
        train(branches, mats, args.fixed_epochs if protocol == "P2" else args.epochs, args.patience, args.lr,
              fixed=(protocol == "P2"))
        with torch.no_grad():
            for d in DS:
                p = branches[d](mats[d][3]).exp().cpu().numpy()
                pooled[d][0].extend(ids[d]); pooled[d][1].extend(mats[d][4].cpu().numpy().tolist()); pooled[d][2].append(p)
    return {d: (np.array(pooled[d][0]), np.array(pooled[d][1]), np.concatenate(pooled[d][2])) for d in DS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=["m01a", "m01b", "m01c", "m01d"])
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    ap.add_argument("--epochs", type=int, default=400)
    ap.add_argument("--patience", type=int, default=40)
    ap.add_argument("--fixed-epochs", type=int, default=100)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--smoke-test", action="store_true")
    args = ap.parse_args()

    g, gcols = m01.load_gamma()
    data = {
        "gamma": (g, gcols, None, "grade_index", "sample_id"),
        "hvf": (m01.load_hvf(), m01.HVF_NUMERIC_FEATURES, "sex", "severity_label", "file"),
        "rnfl_gcc": (m01.load_rnfl_gcc(), m01.RNFL_GCC_NUMERIC_FEATURES, "gender", "severity_label", "si_no"),
    }
    if args.smoke_test:
        args.seeds, args.epochs, args.fixed_epochs = [0], 5, 5
    OUT.mkdir(parents=True, exist_ok=True)
    for arm in args.arms:
        for seed in args.seeds:
            for proto in ("P1", "P2"):
                res = run(arm, seed, proto, args, data)
                if args.smoke_test:
                    for d in DS:
                        ids, y, p = res[d]
                        assert np.allclose(p.sum(1), 1, atol=1e-4) and len(ids) == len(set(ids)) == len(y)
                    print(f"[smoke] {arm} {proto} OK: " + ", ".join(f"{d} n={len(res[d][1])}" for d in DS))
                    continue
                np.savez(OUT / f"{arm}_s{seed}_{proto}.npz",
                         **{f"{d}_{k}": v for d in DS for k, v in zip(("ids", "y", "p"), res[d])})
            print(f"[e3] {arm} seed {seed} done", flush=True)
    print("[e3] DONE")


if __name__ == "__main__":
    main()
