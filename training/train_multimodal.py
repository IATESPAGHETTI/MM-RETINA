"""
Real training loop for the GAMMA fundus+OCT multimodal model.

Run a smoke test FIRST, on a real 6GB GPU, before any long run:

    python train_multimodal.py --smoke-test --oct-slices 4 --img-size 128

The smoke test loads real samples from the actual train split, runs one
real forward + backward pass, and reports the actual loss value and
tensor shapes. It does not train to convergence and does not report any
accuracy/F1 — those only mean something after a real evaluation run
(see evaluate.py). If the smoke test fails, it fails loudly; it is not
allowed to silently report success.

For a real training run:

    python train_multimodal.py --modality fusion --epochs 30 \
        --oct-slices 8 --img-size 224 --batch-size 4 --amp
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from data import GammaMultimodalDataset, GRADE_NAMES
from losses import FocalLoss, class_weights_from_counts
from model import GammaMultimodalModel

REPO_ROOT = Path(__file__).resolve().parent.parent


def log_config(args, device: torch.device):
    print("=" * 70)
    print("CONFIGURATION")
    print("=" * 70)
    for k, v in vars(args).items():
        print(f"  {k}: {v}")
    print(f"  device: {device}")
    if device.type == "cuda":
        props = torch.cuda.get_device_properties(device)
        total_gb = props.total_memory / (1024**3)
        print(f"  gpu: {props.name}  total_vram: {total_gb:.1f} GB")
        approx_activation_mb = (
            args.batch_size * args.oct_slices * (args.img_size**2) * 4 / (1024**2)
        )
        print(f"  approx per-batch OCT tensor size: {approx_activation_mb:.0f} MB (input only, "
              f"excludes activations/gradients — reduce --batch-size/--oct-slices/--img-size if you OOM)")
        if total_gb <= 6.5 and args.batch_size * args.oct_slices > 64:
            print("  WARNING: batch_size * oct_slices is large for a 6GB GPU — expect possible OOM.")
    print("=" * 70)


def build_model(args, device) -> nn.Module:
    model = GammaMultimodalModel(
        fundus_encoder=args.fundus_encoder,
        oct_encoder=args.oct_encoder,
        fusion_dim=args.fusion_dim,
        modality_dropout=args.modality_dropout,
        pretrained=not args.no_pretrained,
        modality=args.modality,
    ).to(device)
    return model


def run_smoke_test(args, device):
    print("\n[smoke-test] Loading REAL samples from the train split...")
    ds = GammaMultimodalDataset(
        manifest_path=args.manifest,
        split_path=args.split,
        split="train",
        img_size=args.img_size,
        oct_img_size=args.img_size,
        num_slices=args.oct_slices,
        train_augment=True,
    )
    n = min(args.smoke_batch_size, len(ds))
    loader = DataLoader(ds, batch_size=n, shuffle=True, num_workers=0)
    batch = next(iter(loader))

    print(f"[smoke-test] fundus batch shape: {tuple(batch['fundus'].shape)}")
    print(f"[smoke-test] oct batch shape:    {tuple(batch['oct'].shape)}")
    print(f"[smoke-test] label batch shape:  {tuple(batch['label'].shape)}")
    print(f"[smoke-test] sample ids in batch: {batch['sample_id']}")

    model = build_model(args, device)
    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    fundus = batch["fundus"].to(device)
    oct_vol = batch["oct"].to(device)
    labels = batch["label"].to(device)

    t0 = time.time()
    logits = model(fundus, oct_vol)
    loss = criterion(logits, labels)
    loss.backward()
    optimizer.step()
    elapsed = time.time() - t0

    grad_norms = [
        p.grad.norm().item() for p in model.parameters() if p.grad is not None
    ]
    print(f"[smoke-test] logits shape: {tuple(logits.shape)}")
    print(f"[smoke-test] REAL loss value after 1 batch: {loss.item():.4f}")
    print(f"[smoke-test] forward+backward+step wall time: {elapsed:.2f}s")
    print(f"[smoke-test] {len(grad_norms)} parameter tensors received gradients "
          f"(max grad norm: {max(grad_norms):.4f})")

    if device.type == "cuda":
        peak_mb = torch.cuda.max_memory_allocated(device) / (1024**2)
        print(f"[smoke-test] peak CUDA memory allocated: {peak_mb:.0f} MB")

    print("[smoke-test] PASSED — real forward and backward pass completed on real data. "
          "This is not a trained model and reports no accuracy.")
    return {
        "status": "passed",
        "fundus_shape": list(batch["fundus"].shape),
        "oct_shape": list(batch["oct"].shape),
        "loss": loss.item(),
        "elapsed_seconds": elapsed,
        "peak_cuda_mb": peak_mb if device.type == "cuda" else None,
    }


def evaluate_split(model, loader, device, criterion) -> dict:
    model.eval()
    total_loss, n = 0.0, 0
    correct = 0
    with torch.no_grad():
        for batch in loader:
            fundus = batch["fundus"].to(device)
            oct_vol = batch["oct"].to(device)
            labels = batch["label"].to(device)
            logits = model(fundus, oct_vol)
            loss = criterion(logits, labels)
            total_loss += loss.item() * labels.size(0)
            correct += (logits.argmax(dim=-1) == labels).sum().item()
            n += labels.size(0)
    return {"loss": total_loss / n, "accuracy": correct / n}


def run_training(args, device):
    train_ds = GammaMultimodalDataset(
        args.manifest, args.split, "train", args.img_size, args.img_size, args.oct_slices, train_augment=True
    )
    val_ds = GammaMultimodalDataset(
        args.manifest, args.split, "val", args.img_size, args.img_size, args.oct_slices, train_augment=False
    )
    print(f"[train] train={len(train_ds)} samples, val={len(val_ds)} samples")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=args.workers)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.workers)

    split_data = json.loads(Path(args.split).read_text())
    train_counts = split_data["class_distribution_per_split"]["train"]
    weights = class_weights_from_counts(train_counts, GRADE_NAMES).to(device)
    print(f"[train] class weights from real train-split counts {train_counts}: {weights.tolist()}")

    criterion = FocalLoss(gamma=args.focal_gamma, weight=weights) if args.focal_loss else nn.CrossEntropyLoss(weight=weights)

    model = build_model(args, device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    scaler = torch.amp.GradScaler("cuda", enabled=args.amp and device.type == "cuda")

    ckpt_dir = REPO_ROOT / "training" / "checkpoints"
    ckpt_dir.mkdir(exist_ok=True)
    ckpt_path = ckpt_dir / f"{args.run_name}.pt"

    best_val_loss = float("inf")
    epochs_without_improvement = 0
    history = []

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss, n = 0.0, 0
        for batch in train_loader:
            fundus = batch["fundus"].to(device)
            oct_vol = batch["oct"].to(device)
            labels = batch["label"].to(device)

            optimizer.zero_grad()
            with torch.amp.autocast("cuda", enabled=args.amp and device.type == "cuda"):
                logits = model(fundus, oct_vol)
                loss = criterion(logits, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_loss += loss.item() * labels.size(0)
            n += labels.size(0)

        scheduler.step()
        train_loss = running_loss / n
        val_metrics = evaluate_split(model, val_loader, device, nn.CrossEntropyLoss(weight=weights))

        print(f"[train] epoch {epoch:03d}/{args.epochs}  train_loss={train_loss:.4f}  "
              f"val_loss={val_metrics['loss']:.4f}  val_acc={val_metrics['accuracy']:.3f}  "
              f"lr={scheduler.get_last_lr()[0]:.2e}")

        history.append({"epoch": epoch, "train_loss": train_loss, **val_metrics})

        if val_metrics["loss"] < best_val_loss:
            best_val_loss = val_metrics["loss"]
            epochs_without_improvement = 0
            torch.save(
                {"model_state": model.state_dict(), "args": vars(args), "epoch": epoch, "val_loss": best_val_loss},
                ckpt_path,
            )
            print(f"[train]   -> new best val_loss, saved checkpoint to {ckpt_path}")
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= args.patience:
                print(f"[train] early stopping at epoch {epoch} (no improvement for {args.patience} epochs)")
                break

    return {"history": history, "checkpoint": str(ckpt_path), "best_val_loss": best_val_loss}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(REPO_ROOT / "dataset" / "gamma_manifest.json"))
    ap.add_argument("--split", default=str(REPO_ROOT / "dataset" / "splits" / "gamma_split_v1.json"))
    ap.add_argument("--run-name", default="fusion_run1")

    ap.add_argument("--modality", choices=["fusion", "fundus", "oct"], default="fusion")
    ap.add_argument("--fundus-encoder", default="resnet18")
    ap.add_argument("--oct-encoder", default="resnet18")
    ap.add_argument("--fusion-dim", type=int, default=256)
    ap.add_argument("--modality-dropout", type=float, default=0.15)
    ap.add_argument("--no-pretrained", action="store_true")

    ap.add_argument("--img-size", type=int, default=224)
    ap.add_argument("--oct-slices", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--workers", type=int, default=0)

    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--focal-loss", action="store_true")
    ap.add_argument("--focal-gamma", type=float, default=2.0)
    ap.add_argument("--amp", action="store_true")
    ap.add_argument("--seed", type=int, default=42)

    ap.add_argument("--smoke-test", action="store_true")
    ap.add_argument("--smoke-batch-size", type=int, default=2)
    args = ap.parse_args()

    torch.manual_seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log_config(args, device)

    if args.smoke_test:
        result = run_smoke_test(args, device)
    else:
        result = run_training(args, device)

    print("\n[main] Done. Result summary:")
    print(json.dumps({k: v for k, v in result.items() if k != "history"}, indent=2))


if __name__ == "__main__":
    main()
