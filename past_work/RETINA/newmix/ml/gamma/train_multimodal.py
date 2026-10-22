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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

from data import GammaMultimodalDataset, GRADE_NAMES
from evaluate import compute_classification_metrics
from losses import FocalLoss, class_weights_from_counts
from model import GammaMultimodalModel

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "runs"


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
        oct_in_chans=3 if args.oct_representation == "2.5d" else 1,
        fusion_type=args.fusion_type,
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
        oct_representation=args.oct_representation,
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
    """Runs one real forward pass over `loader`, returns loss plus the full
    metric set (accuracy/balanced_accuracy/macro_f1/roc_auc/kappa/qwk/
    confusion_matrix), via the same `compute_classification_metrics` that
    evaluate.py's standalone test-set evaluation uses — so a val-time number
    logged to TensorBoard is defined identically to the final reported one."""
    model.eval()
    total_loss, n = 0.0, 0
    all_logits, all_labels = [], []
    with torch.no_grad():
        for batch in loader:
            fundus = batch["fundus"].to(device)
            oct_vol = batch["oct"].to(device)
            labels = batch["label"].to(device)
            logits = model(fundus, oct_vol)
            loss = criterion(logits, labels)
            total_loss += loss.item() * labels.size(0)
            n += labels.size(0)
            all_logits.append(logits.detach().cpu().numpy())
            all_labels.append(labels.detach().cpu().numpy())

    logits = np.concatenate(all_logits, axis=0)
    labels = np.concatenate(all_labels, axis=0)
    probs = torch.softmax(torch.from_numpy(logits), dim=-1).numpy()
    result = compute_classification_metrics(labels, probs)
    m = result["metrics"]
    return {
        "loss": total_loss / n,
        "accuracy": m["accuracy"],
        "balanced_accuracy": m["balanced_accuracy"],
        "macro_f1": m["macro_f1"],
        "roc_auc_ovr_macro": m["roc_auc_ovr_macro"],
        "cohen_kappa": m["cohen_kappa"],
        "quadratic_weighted_kappa": m["quadratic_weighted_kappa"],
        "confusion_matrix": result["confusion_matrix"],
    }


def log_confusion_matrix_figure(writer: SummaryWriter, cm: list[list[int]], epoch: int, tag: str):
    cm_arr = np.array(cm)
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.imshow(cm_arr, cmap="Blues")
    ax.set_xticks(range(len(GRADE_NAMES)))
    ax.set_yticks(range(len(GRADE_NAMES)))
    ax.set_xticklabels(GRADE_NAMES, rotation=45, ha="right")
    ax.set_yticklabels(GRADE_NAMES)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    for i in range(cm_arr.shape[0]):
        for j in range(cm_arr.shape[1]):
            ax.text(j, i, str(cm_arr[i, j]), ha="center", va="center")
    fig.tight_layout()
    writer.add_figure(tag, fig, global_step=epoch)
    plt.close(fig)


def build_fixed_sample_panel(val_ds, n: int = 8):
    """Picks the same n validation samples every epoch (first n by dataset
    order, which is deterministic given the split file) so their predictions
    can be visually tracked over the course of training."""
    n = min(n, len(val_ds))
    indices = list(range(n))
    batch = [val_ds[i] for i in indices]
    return {
        "sample_ids": [b["sample_id"] for b in batch],
        "fundus": torch.stack([b["fundus"] for b in batch]),
        "oct": torch.stack([b["oct"] for b in batch]),
        "labels": torch.stack([b["label"] for b in batch]),
    }


def log_fixed_sample_predictions(writer: SummaryWriter, model, panel: dict, device, epoch: int):
    model.eval()
    with torch.no_grad():
        fundus = panel["fundus"].to(device)
        oct_vol = panel["oct"].to(device)
        logits = model(fundus, oct_vol)
        probs = torch.softmax(logits, dim=-1).cpu().numpy()
    preds = probs.argmax(axis=-1)

    # De-normalize fundus (ImageNet mean/std) and OCT (mean/std=0.5) for a
    # human-viewable image; take the middle OCT slice as the representative
    # B-scan for this sample.
    fundus_mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
    fundus_std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
    fundus_vis = (panel["fundus"] * fundus_std + fundus_mean).clamp(0, 1)
    mid_slice = panel["oct"][:, panel["oct"].shape[1] // 2]  # (n, 1, H, W)
    oct_vis = (mid_slice * 0.5 + 0.5).clamp(0, 1)

    for i, sid in enumerate(panel["sample_ids"]):
        true_label = GRADE_NAMES[int(panel["labels"][i])]
        pred_label = GRADE_NAMES[int(preds[i])]
        prob_str = ", ".join(f"{GRADE_NAMES[c]}={probs[i, c]:.2f}" for c in range(len(GRADE_NAMES)))
        writer.add_image(f"val_samples/{sid}_fundus", fundus_vis[i], global_step=epoch)
        writer.add_image(f"val_samples/{sid}_oct_mid_slice", oct_vis[i], global_step=epoch)
        writer.add_text(
            f"val_samples/{sid}_prediction",
            f"true={true_label}  pred={pred_label}  probs=[{prob_str}]",
            global_step=epoch,
        )


def run_training(args, device):
    train_ds = GammaMultimodalDataset(
        args.manifest, args.split, "train", args.img_size, args.img_size, args.oct_slices,
        train_augment=True, oct_representation=args.oct_representation,
    )
    val_ds = GammaMultimodalDataset(
        args.manifest, args.split, "val", args.img_size, args.img_size, args.oct_slices,
        train_augment=False, oct_representation=args.oct_representation,
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

    log_dir = RUNS_DIR / args.run_name
    writer = SummaryWriter(log_dir=str(log_dir)) if not getattr(args, "no_tensorboard", False) else None
    if writer is not None:
        print(f"[train] TensorBoard: http://localhost:6006  (logdir={RUNS_DIR}, run={args.run_name})")
    fixed_panel = build_fixed_sample_panel(val_ds) if writer is not None else None

    # Higher-is-better for every supported checkpoint metric except val_loss.
    higher_is_better = args.checkpoint_metric != "val_loss"
    best_metric = float("-inf") if higher_is_better else float("inf")
    epochs_without_improvement = 0
    history = []

    for epoch in range(1, args.epochs + 1):
        epoch_t0 = time.time()
        model.train()
        running_loss, n = 0.0, 0
        train_logits, train_labels = [], []
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
            train_logits.append(logits.detach().float().cpu().numpy())
            train_labels.append(labels.detach().cpu().numpy())

        scheduler.step()
        train_loss = running_loss / n
        train_probs = torch.softmax(torch.from_numpy(np.concatenate(train_logits, axis=0)), dim=-1).numpy()
        train_metrics = compute_classification_metrics(np.concatenate(train_labels, axis=0), train_probs)["metrics"]

        val_metrics = evaluate_split(model, val_loader, device, nn.CrossEntropyLoss(weight=weights))
        epoch_seconds = time.time() - epoch_t0
        lr = scheduler.get_last_lr()[0]
        gpu_mem_mb = torch.cuda.max_memory_allocated(device) / (1024**2) if device.type == "cuda" else 0.0

        print(f"[train] epoch {epoch:03d}/{args.epochs}  train_loss={train_loss:.4f}  "
              f"val_loss={val_metrics['loss']:.4f}  val_acc={val_metrics['accuracy']:.3f}  "
              f"val_macro_f1={val_metrics['macro_f1']:.3f}  val_roc_auc={val_metrics['roc_auc_ovr_macro']}  "
              f"val_qwk={val_metrics['quadratic_weighted_kappa']:.3f}  lr={lr:.2e}  "
              f"epoch_time={epoch_seconds:.1f}s  gpu_mem={gpu_mem_mb:.0f}MB")

        history.append({"epoch": epoch, "train_loss": train_loss, **val_metrics})

        if writer is not None:
            writer.add_scalar("train/loss", train_loss, epoch)
            writer.add_scalar("train/accuracy", train_metrics["accuracy"], epoch)
            writer.add_scalar("train/macro_f1", train_metrics["macro_f1"], epoch)
            writer.add_scalar("val/loss", val_metrics["loss"], epoch)
            writer.add_scalar("val/accuracy", val_metrics["accuracy"], epoch)
            writer.add_scalar("val/balanced_accuracy", val_metrics["balanced_accuracy"], epoch)
            writer.add_scalar("val/macro_f1", val_metrics["macro_f1"], epoch)
            writer.add_scalar("val/cohen_kappa", val_metrics["cohen_kappa"], epoch)
            writer.add_scalar("val/quadratic_weighted_kappa", val_metrics["quadratic_weighted_kappa"], epoch)
            if val_metrics["roc_auc_ovr_macro"] is not None:
                writer.add_scalar("val/roc_auc", val_metrics["roc_auc_ovr_macro"], epoch)
            writer.add_scalar("learning_rate", lr, epoch)
            writer.add_scalar("epoch_time_seconds", epoch_seconds, epoch)
            if device.type == "cuda":
                writer.add_scalar("gpu_memory_mb", gpu_mem_mb, epoch)
            log_confusion_matrix_figure(writer, val_metrics["confusion_matrix"], epoch, "val/confusion_matrix")
            log_fixed_sample_predictions(writer, model, fixed_panel, device, epoch)
            model.train()  # log_fixed_sample_predictions leaves the model in eval mode
            writer.flush()

        current_metric = val_metrics["loss"] if args.checkpoint_metric == "val_loss" else val_metrics[args.checkpoint_metric]
        improved = current_metric > best_metric if higher_is_better else current_metric < best_metric
        if improved:
            best_metric = current_metric
            epochs_without_improvement = 0
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "optimizer_state": optimizer.state_dict(),
                    "scheduler_state": scheduler.state_dict(),
                    "args": vars(args),
                    "epoch": epoch,
                    "val_loss": val_metrics["loss"],
                    "checkpoint_metric": args.checkpoint_metric,
                    "checkpoint_metric_value": best_metric,
                },
                ckpt_path,
            )
            print(f"[train]   -> new best {args.checkpoint_metric}={best_metric:.4f}, saved checkpoint to {ckpt_path}")
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= args.patience:
                print(f"[train] early stopping at epoch {epoch} (no improvement for {args.patience} epochs)")
                break

    if writer is not None:
        writer.close()

    return {
        "history": history,
        "checkpoint": str(ckpt_path),
        "checkpoint_metric": args.checkpoint_metric,
        "best_checkpoint_metric_value": best_metric,
        "best_val_loss": min(h["loss"] for h in history) if history else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(REPO_ROOT / "dataset" / "gamma_manifest.json"))
    ap.add_argument("--split", default=str(REPO_ROOT / "dataset" / "splits" / "gamma_split_v1.json"))
    ap.add_argument("--run-name", default="fusion_run1")

    ap.add_argument("--modality", choices=["fusion", "fundus", "oct"], default="fusion")
    ap.add_argument("--fundus-encoder", default="resnet18")
    ap.add_argument("--oct-encoder", default="resnet18")
    ap.add_argument("--fusion-dim", type=int, default=256)
    ap.add_argument(
        "--fusion-type",
        choices=["vector", "token"],
        default="vector",
        help="'vector' (default, baseline): each modality collapsed to one pooled vector "
             "before cross-attention. 'token' (EXP-06): fundus spatial feature-map tokens "
             "+ OCT per-slice tokens attend jointly through a small Transformer.",
    )
    ap.add_argument("--modality-dropout", type=float, default=0.15)
    ap.add_argument("--no-pretrained", action="store_true")

    ap.add_argument("--img-size", type=int, default=224)
    ap.add_argument("--oct-slices", type=int, default=8)
    ap.add_argument(
        "--oct-representation",
        choices=["single", "2.5d"],
        default="single",
        help="'single' (default, baseline): one grayscale B-scan per sampled slice index. "
             "'2.5d' (Experiment OCT-2): stacks B-scans [i-1, i, i+1] as 3 channels per "
             "sampled slice index, giving the 2D backbone local depth context.",
    )
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

    ap.add_argument(
        "--checkpoint-metric",
        choices=["val_loss", "quadratic_weighted_kappa", "macro_f1", "roc_auc_ovr_macro", "accuracy"],
        default="val_loss",
        help="Metric used for best-checkpoint selection and early stopping. "
             "Default (val_loss) preserves the original baseline's behavior; "
             "the improvement plan's preferred metric for new runs is "
             "quadratic_weighted_kappa.",
    )
    ap.add_argument("--no-tensorboard", action="store_true", help="Disable TensorBoard logging.")

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
