"""
5-fold patient-grouped CV for the Jev/Laya-inspired decision-head arms
(research branch `jev-architecture`, see ../decisions.md).

Folds are built with cross_validate.make_folds (same seed/round-robin
stratification => same membership as every earlier CV experiment). This
script saves the validation-fold probabilities for EVERY epoch, so the
analysis can apply either:
  * the project's existing protocol (best epoch chosen on the held-out fold's
    weighted-CE val loss -- mildly optimistic, kept for comparability), or
  * a selection-free protocol (final epoch only).

ALWAYS run --smoke-test first.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from cross_validate import make_folds, write_fold_split
from data import GRADE_NAMES
from gpu_data import GpuGamma
from decision_heads import DecisionHeadModel, act_loss, decision_loss
from losses import class_weights_from_counts

REPO_ROOT = Path(__file__).resolve().parent.parent

ARMS = {
    # name: (head, loss, use_act_head)
    "a0_mlp_focalw": ("mlp", "focal_w", False),   # control = EXP-06 reproduced under this code path
    "a1_mlp_ce": ("mlp", "ce", False),            # tests: is under-confidence caused by focal+class weights?
    "a2_mlp_nllrps": ("mlp", "nll_rps", False),   # proper scoring rules, same head
    "a3_cl_nllrps": ("cl", "nll_rps", False),     # ordinal cumulative-link head
    "a4_query_nllrps": ("query", "nll_rps", True),  # Laya-style option-query head + act head
}


def run_fold(arm: str, fold_idx: int, split_path: Path, args, device) -> dict:
    head, loss_kind, use_act = ARMS[arm]
    torch.manual_seed(args.seed + fold_idx)
    np.random.seed(args.seed + fold_idx)

    gd = GpuGamma(args.manifest, args.img_size, args.oct_slices, device)
    smap = json.loads(split_path.read_text())["sample_split"]
    train_rows = gd.rows([i for i in gd.ids if smap[i] == "train"])
    val_ids = [i for i in gd.ids if smap[i] == "val"]
    val_rows = gd.rows(val_ids)
    bs = args.batch_size

    counts = json.loads(split_path.read_text())["class_distribution_per_split"]["train"]
    weights = class_weights_from_counts(counts, GRADE_NAMES).to(device)

    model = DecisionHeadModel(head=head).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    scaler = torch.amp.GradScaler("cuda", enabled=args.amp and device.type == "cuda")

    epochs = 1 if args.smoke_test else args.epochs
    all_probs, all_act, all_wce, ids_ref, labels_ref = [], [], [], None, None
    t0 = time.time()
    for ep in range(1, epochs + 1):
        model.train()
        tl, n = 0.0, 0
        perm = train_rows[torch.randperm(len(train_rows), device=device)]
        for k in range(0, len(perm), bs):
            fu, oc, y = gd.batch(perm[k:k + bs], augment=True)
            opt.zero_grad()
            with torch.amp.autocast("cuda", enabled=args.amp and device.type == "cuda"):
                lp, act = model(fu, oc)
                lp = lp.float()
                loss = decision_loss(loss_kind, lp, y, weights, args.focal_gamma)
                if use_act:
                    loss = loss + 0.5 * act_loss(act.float(), lp, y)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            tl += loss.item() * y.size(0)
            n += y.size(0)
        sched.step()

        model.eval()
        probs, acts, labels = [], [], []
        with torch.no_grad():
            for k in range(0, len(val_rows), bs):
                fu, oc, y = gd.batch(val_rows[k:k + bs], augment=False)
                lp, act = model(fu, oc)
                probs.append(lp.float().exp().cpu().numpy())
                acts.append((act.float().sigmoid() if act is not None else torch.full((fu.shape[0],), float("nan"), device=device)).cpu().numpy())
                labels.append(y.cpu().numpy())
        ids = val_ids
        probs, acts, labels = np.concatenate(probs), np.concatenate(acts), np.concatenate(labels)
        wce = float(F.nll_loss(torch.from_numpy(probs).clamp_min(1e-12).log(), torch.from_numpy(labels),
                               weight=weights.cpu()).item())
        all_probs.append(probs), all_act.append(acts), all_wce.append(wce)
        ids_ref, labels_ref = ids, labels
        acc = float((probs.argmax(1) == labels).mean())
        print(f"[{arm} f{fold_idx}] ep {ep:02d}/{epochs} train_loss={tl / n:.4f} val_wCE={wce:.4f} "
              f"val_acc={acc:.3f} t={time.time() - t0:.0f}s", flush=True)

    return {
        "probs": np.stack(all_probs), "act": np.stack(all_act), "wce": np.array(all_wce),
        "labels": labels_ref, "ids": np.array(ids_ref), "train_seconds": time.time() - t0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=list(ARMS))
    ap.add_argument("--manifest", default=str(REPO_ROOT / "dataset" / "gamma_manifest.json"))
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "results" / "jev_architecture" / "heads"))
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--folds", type=int, nargs="+", default=None)
    ap.add_argument("--img-size", type=int, default=160)
    ap.add_argument("--oct-slices", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--workers", type=int, default=0, help="unused (GPU-resident data pipeline)")
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--focal-gamma", type=float, default=2.0)
    ap.add_argument("--amp", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tag", default="")
    ap.add_argument("--smoke-test", action="store_true")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    manifest = json.loads(Path(args.manifest).read_text())
    fold_of = make_folds(manifest, args.k, 42)  # fold membership fixed at seed 42 (same as all prior CV)
    split_dir = REPO_ROOT / "dataset" / "splits" / "cv_jev"
    out = Path(args.out_dir) / (args.arm + args.tag)
    out.mkdir(parents=True, exist_ok=True)

    folds = args.folds if args.folds is not None else ([0] if args.smoke_test else list(range(args.k)))
    for f in folds:
        sp = split_dir / f"fold{f}.json"
        write_fold_split(manifest, fold_of, f, args.k, 42, sp)
        res = run_fold(args.arm, f, sp, args, device)
        if args.smoke_test:
            p = res["probs"][-1]
            assert p.shape[1] == 3 and np.allclose(p.sum(1), 1, atol=1e-4), "probs malformed"
            print(f"[smoke] PASSED arm={args.arm}: val probs shape {p.shape}, rows sum to 1, "
                  f"act present={not np.isnan(res['act']).all()}, train_seconds={res['train_seconds']:.1f}")
            return
        np.savez(out / f"fold{f}.npz", **res)
        print(f"[{args.arm}] fold {f} saved ({res['train_seconds']:.0f}s)", flush=True)
    print(f"[{args.arm}] DONE", flush=True)


if __name__ == "__main__":
    main()
