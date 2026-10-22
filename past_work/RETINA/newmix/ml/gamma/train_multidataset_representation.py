"""
EXP-M01 — Multi-Dataset Shared Representation Learning.

Per MM_RETINA_MULTIDATASET_REPRESENTATION_AND_CASE_EXAMPLES.md: this does
NOT physically merge GAMMA, HVF, and RNFL/GCC into one patient table, and
does NOT modify the frozen GAMMA benchmark (EXP-05/06,
results/cv_fusion_effnetb0_v1/). Three separately-supervised datasets each
keep their own identifiers, label taxonomy, and evaluation:

    GAMMA     — 100 patients,  Normal/Early/Progressive,  patient-level
    HVF       — 168 eyes/90 patients, Mild/Moderate/Severe, eye-level
                (C01b no-proxy feature set: md_db/psd_db/vfi_pct excluded
                because those are near-duplicates of the label-assignment
                criteria — see EXPERIMENTS.md's EXP-C01/C01b entries)
    RNFL/GCC  — 171 eye-level rows, Mild/Moderate/Severe, NO PATIENT ID
                (see dataset/rnfl_gcc_provenance_audit.md — no identifier
                is recoverable from the workbook by any means). Folded
                with plain StratifiedKFold, not patient-grouped, because
                there is no ID to group by; this is a standing limitation
                of every RNFL/GCC number reported here, not an oversight.

No cross-dataset patient pairing is ever constructed. Two architectures
are compared, using the SAME per-dataset encoders/heads/folds in both:

    M01-A (independent) — each dataset gets its OWN trunk instance;
        gradients never mix across datasets. This is the "modality-
        specific baseline" control.
    M01-B (shared)       — ONE trunk instance is shared by all three
        datasets' encoders. Each training step still uses only one
        dataset's own labeled batch for its own head's loss, but the
        trunk's weights are updated from all three datasets' losses
        (summed before backward()), which is what "shared representation"
        means here — no sample from one dataset is ever matched to a
        sample from another.

The GAMMA branch's input is a frozen 256-dim fused Fundus+OCT embedding
per patient (training/extract_gamma_embeddings.py) from a DIFFERENT,
weaker checkpoint than the frozen EXP-05/06 benchmark (see that script's
docstring for why) — GAMMA numbers produced here are a probe on top of
that frozen embedding, not a re-measurement of EXP-05/06, and must never
be presented as such.

Usage:
    python training/train_multidataset_representation.py --smoke-test
    python training/train_multidataset_representation.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from torch.utils.tensorboard import SummaryWriter

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cross_validate import make_folds as gamma_make_folds  # noqa: E402
from train_hvf_baseline import (  # noqa: E402
    NUMERIC_FEATURES_NO_PROXY as HVF_NUMERIC_FEATURES,
    load_dataset as load_hvf_dataset,
)

GAMMA_EMBEDDINGS_CSV = REPO_ROOT / "dataset" / "gamma_fusion_embeddings.csv"
GAMMA_MANIFEST = REPO_ROOT / "dataset" / "gamma_manifest.json"
RNFL_GCC_CSV = REPO_ROOT / "dataset" / "rnfl_gcc_features.csv"
OUT_DIR = REPO_ROOT / "results" / "m01"
TB_DIR = REPO_ROOT / "runs" / "m01"

RNFL_GCC_NUMERIC_FEATURES = [
    "Average_RNFL", "RNFL_Superior", "RNFL_Inferior", "RNFL_Nasal", "RNFL_Temporal",
    "Average_GCC", "GCC_Superior", "GCC_Inferior",
    "GCC_Supero_nasal", "GCC_Supero_temporal", "GCC_Infero_nasal", "GCC_Infero_temporal",
    "age",
]

DATASETS = {
    "gamma": {"class_names": ["normal", "early", "progressive"], "n_folds": 5},
    "hvf": {"class_names": ["mild", "moderate", "severe"], "n_folds": 5},
    "rnfl_gcc": {"class_names": ["mild", "moderate", "severe"], "n_folds": 5},
}
EMBED_DIM = 64
SEED = 42


# --------------------------------------------------------------------------
# Dataset loading + fold construction — each dataset keeps its own identity,
# label taxonomy, and split logic. No cross-dataset joins anywhere below.
# --------------------------------------------------------------------------

def load_gamma():
    # patient_id/sample_id are zero-padded strings ("0001") — force dtype=str
    # or pandas silently parses them as int and strips the leading zeros,
    # which then fails every lookup against gamma_make_folds' string keys.
    df = pd.read_csv(GAMMA_EMBEDDINGS_CSV, dtype={"patient_id": str, "sample_id": str})
    manifest = json.loads(GAMMA_MANIFEST.read_text())
    fold_of_patient = gamma_make_folds(manifest, k=DATASETS["gamma"]["n_folds"], seed=SEED)
    df["fold"] = df["patient_id"].map(fold_of_patient)
    embed_cols = [c for c in df.columns if c.startswith("dim_")]
    return df, embed_cols


def load_hvf():
    df = load_hvf_dataset()
    groups = df["patient_id"].to_numpy()
    gkf = GroupKFold(n_splits=DATASETS["hvf"]["n_folds"])
    fold_of_row = np.full(len(df), -1, dtype=int)
    for fold_idx, (_, val_idx) in enumerate(gkf.split(df, groups=groups)):
        fold_of_row[val_idx] = fold_idx
    df = df.copy()
    df["fold"] = fold_of_row
    return df


def load_rnfl_gcc():
    if not RNFL_GCC_CSV.exists():
        raise FileNotFoundError(f"{RNFL_GCC_CSV} not found — run dataset/rnfl_gcc_feature_extraction.py first.")
    df = pd.read_csv(RNFL_GCC_CSV)
    df["gender"] = df["gender"].fillna("unknown")
    # No patient ID exists (see dataset/rnfl_gcc_provenance_audit.md), so this
    # is a PLAIN stratified split, not patient-grouped — a standing limitation
    # of every RNFL/GCC number produced here, carried into every report.
    skf = StratifiedKFold(n_splits=DATASETS["rnfl_gcc"]["n_folds"], shuffle=True, random_state=SEED)
    fold_of_row = np.full(len(df), -1, dtype=int)
    for fold_idx, (_, val_idx) in enumerate(skf.split(df, df["severity_label"])):
        fold_of_row[val_idx] = fold_idx
    df = df.copy()
    df["fold"] = fold_of_row
    return df


def build_fold_matrices(train_df, val_df, numeric_features, categorical_col=None):
    imputer = SimpleImputer(strategy="median")
    X_num_train = imputer.fit_transform(train_df[numeric_features])
    X_num_val = imputer.transform(val_df[numeric_features])
    scaler = StandardScaler()
    X_num_train = scaler.fit_transform(X_num_train)
    X_num_val = scaler.transform(X_num_val)

    if categorical_col is not None:
        cats = sorted(train_df[categorical_col].unique())
        def onehot(series):
            return np.array([[1.0 if v == c else 0.0 for c in cats] for v in series])
        X_train = np.concatenate([X_num_train, onehot(train_df[categorical_col])], axis=1)
        X_val = np.concatenate([X_num_val, onehot(val_df[categorical_col])], axis=1)
    else:
        X_train, X_val = X_num_train, X_num_val
    return X_train.astype(np.float32), X_val.astype(np.float32)


# --------------------------------------------------------------------------
# Model: per-dataset encoder -> trunk (independent per dataset in M01-A,
# ONE shared instance across all three in M01-B) -> per-dataset head.
# --------------------------------------------------------------------------

class Encoder(nn.Module):
    def __init__(self, in_dim: int, embed_dim: int = EMBED_DIM):
        super().__init__()
        hidden = max(embed_dim, in_dim // 2)
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(hidden, embed_dim), nn.ReLU(),
        )

    def forward(self, x):
        return self.net(x)


class Trunk(nn.Module):
    def __init__(self, dim: int = EMBED_DIM):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(dim, dim), nn.ReLU(), nn.Dropout(0.2), nn.Linear(dim, dim))

    def forward(self, x):
        return x + self.net(x)  # residual so a randomly-initialized trunk never hurts early training


class Head(nn.Module):
    def __init__(self, dim: int = EMBED_DIM, n_classes: int = 3):
        super().__init__()
        self.net = nn.Linear(dim, n_classes)

    def forward(self, x):
        return self.net(x)


class DatasetBranch(nn.Module):
    def __init__(self, in_dim: int, trunk: Trunk, n_classes: int = 3, embed_dim: int = EMBED_DIM):
        super().__init__()
        self.encoder = Encoder(in_dim, embed_dim)
        self.trunk = trunk  # shared instance (M01-B) or private instance (M01-A) — caller decides
        self.head = Head(embed_dim, n_classes)

    def forward(self, x):
        return self.head(self.trunk(self.encoder(x)))


# --------------------------------------------------------------------------
# Metrics — identical shape/definitions to train_hvf_baseline.py's, kept
# separate here since class name lists differ per dataset.
# --------------------------------------------------------------------------

def compute_metrics(y_true, probs, class_names):
    preds = probs.argmax(axis=-1)
    precision, recall, f1_per_class, support = precision_recall_fscore_support(
        y_true, preds, labels=list(range(len(class_names))), zero_division=0
    )
    metrics = {
        "num_eval": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, preds)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, preds)),
        "macro_f1": float(f1_score(y_true, preds, average="macro", zero_division=0)),
        "cohen_kappa": float(cohen_kappa_score(y_true, preds)),
        "quadratic_weighted_kappa": float(cohen_kappa_score(y_true, preds, weights="quadratic")),
        "per_class": {
            class_names[i]: {
                "precision": float(precision[i]), "recall": float(recall[i]),
                "f1": float(f1_per_class[i]), "support": int(support[i]),
            } for i in range(len(class_names))
        },
    }
    try:
        metrics["roc_auc_ovr_macro"] = float(
            roc_auc_score(y_true, probs, multi_class="ovr", average="macro", labels=list(range(len(class_names))))
        )
    except ValueError as e:
        metrics["roc_auc_ovr_macro"] = None
        metrics["roc_auc_error"] = str(e)
    cm = confusion_matrix(y_true, preds, labels=list(range(len(class_names))))
    return {"metrics": metrics, "confusion_matrix": cm.tolist(), "preds": preds, "probs": probs}


def save_result(arch: str, dataset: str, fold_idx: int, id_cols_df: pd.DataFrame, result: dict,
                 class_names: list[str], out_dir: Path):
    fold_dir = out_dir / arch / dataset / f"fold{fold_idx}"
    fold_dir.mkdir(parents=True, exist_ok=True)
    (fold_dir / "metrics.json").write_text(json.dumps(result["metrics"], indent=2))
    with open(fold_dir / "confusion_matrix.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([""] + [f"pred_{g}" for g in class_names])
        for i, row in enumerate(result["confusion_matrix"]):
            w.writerow([f"true_{class_names[i]}"] + row)

    preds, probs = result["preds"], result["probs"]
    rows = []
    id_cols = list(id_cols_df.columns)
    for i, (_, r) in enumerate(id_cols_df.iterrows()):
        row = {c: r[c] for c in id_cols}
        row["pred_label"] = class_names[int(preds[i])]
        row.update({f"prob_{class_names[c]}": float(probs[i, c]) for c in range(len(class_names))})
        rows.append(row)
    with open(fold_dir / "predictions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def aggregate(all_results: list[dict], out_dir: Path):
    summary = {}
    metric_names = ["accuracy", "balanced_accuracy", "macro_f1", "roc_auc_ovr_macro",
                     "cohen_kappa", "quadratic_weighted_kappa"]
    for arch in sorted(set(r["arch"] for r in all_results)):
        summary[arch] = {}
        for dataset in sorted(set(r["dataset"] for r in all_results if r["arch"] == arch)):
            rows = [r for r in all_results if r["arch"] == arch and r["dataset"] == dataset]
            per_metric = {}
            for m in metric_names:
                values = [r["metrics"][m] for r in rows if r["metrics"].get(m) is not None]
                per_metric[m] = {
                    "values_per_fold": values,
                    "mean": float(np.mean(values)) if values else None,
                    "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                }
            summary[arch][dataset] = per_metric
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


# --------------------------------------------------------------------------
# Training
# --------------------------------------------------------------------------

def train_round(arch: str, fold_idx: int, branches: dict, batches: dict, writer: SummaryWriter,
                 epochs: int, patience: int, lr: float, device):
    """One joint training round. `branches` = {dataset: DatasetBranch}.
    `batches` = {dataset: (Xtr, ytr, class_weights, Xval, yval)} tensors.
    Trunk sharing (or not) was already decided by how `branches` were built
    — this function is identical for M01-A and M01-B."""
    params = []
    for b in branches.values():
        params += list(b.parameters())
    # De-duplicate shared trunk parameters (M01-B: the same Trunk instance
    # appears in all three branches — without this, its params would be
    # added to the optimizer 3x and get an effectively 3x learning rate).
    seen = set()
    unique_params = []
    for p in params:
        if id(p) not in seen:
            seen.add(id(p))
            unique_params.append(p)
    opt = torch.optim.Adam(unique_params, lr=lr, weight_decay=1e-4)

    best_val_loss = float("inf")
    best_state = {ds: None for ds in branches}
    epochs_since_improve = 0

    for epoch in range(epochs):
        for b in branches.values():
            b.train()
        opt.zero_grad()
        total_loss = 0.0
        for dataset, (Xtr, ytr, weights, _, _) in batches.items():
            logits = branches[dataset](Xtr)
            loss = nn.functional.cross_entropy(logits, ytr, weight=weights)
            total_loss = total_loss + loss
            writer.add_scalar(f"{arch}/{dataset}/fold{fold_idx}/train_loss", loss.item(), epoch)
        total_loss.backward()
        opt.step()

        for b in branches.values():
            b.eval()
        val_loss_sum = 0.0
        with torch.no_grad():
            for dataset, (_, _, weights, Xval, yval) in batches.items():
                val_logits = branches[dataset](Xval)
                val_loss = nn.functional.cross_entropy(val_logits, yval, weight=weights).item()
                val_acc = (val_logits.argmax(-1) == yval).float().mean().item()
                writer.add_scalar(f"{arch}/{dataset}/fold{fold_idx}/val_loss", val_loss, epoch)
                writer.add_scalar(f"{arch}/{dataset}/fold{fold_idx}/val_acc", val_acc, epoch)
                val_loss_sum += val_loss

        if val_loss_sum < best_val_loss - 1e-4:
            best_val_loss = val_loss_sum
            best_state = {ds: {k: v.clone() for k, v in b.state_dict().items()} for ds, b in branches.items()}
            epochs_since_improve = 0
        else:
            epochs_since_improve += 1
            if epochs_since_improve >= patience:
                break

    for ds, b in branches.items():
        if best_state[ds] is not None:
            b.load_state_dict(best_state[ds])
        b.eval()


def run_arch(arch: str, gamma_df, gamma_embed_cols, hvf_df, rnfl_df, writer, device,
             epochs: int, patience: int, lr: float, n_folds: int):
    assert arch in ("m01a", "m01b")
    all_results = []

    for fold_idx in range(n_folds):
        torch.manual_seed(SEED + fold_idx)

        # --- GAMMA fold ---
        g_train, g_val = gamma_df[gamma_df["fold"] != fold_idx], gamma_df[gamma_df["fold"] == fold_idx]
        Xg_tr, Xg_val = build_fold_matrices(g_train, g_val, gamma_embed_cols)
        yg_tr = g_train["grade_index"].to_numpy()
        yg_val = g_val["grade_index"].to_numpy()

        # --- HVF fold ---
        h_train, h_val = hvf_df[hvf_df["fold"] != fold_idx], hvf_df[hvf_df["fold"] == fold_idx]
        Xh_tr, Xh_val = build_fold_matrices(h_train, h_val, HVF_NUMERIC_FEATURES, categorical_col="sex")
        yh_tr = h_train["severity_label"].to_numpy()
        yh_val = h_val["severity_label"].to_numpy()

        # --- RNFL/GCC fold (plain stratified — no patient ID, see module docstring) ---
        r_train, r_val = rnfl_df[rnfl_df["fold"] != fold_idx], rnfl_df[rnfl_df["fold"] == fold_idx]
        Xr_tr, Xr_val = build_fold_matrices(r_train, r_val, RNFL_GCC_NUMERIC_FEATURES, categorical_col="gender")
        yr_tr = r_train["severity_label"].to_numpy()
        yr_val = r_val["severity_label"].to_numpy()

        def to_t(x, dtype=torch.float32):
            return torch.tensor(x, dtype=dtype, device=device)

        def class_weights(y, n_classes):
            counts = Counter(y.tolist())
            n = len(y)
            return to_t([n / (n_classes * counts.get(c, 1)) for c in range(n_classes)])

        batches = {
            "gamma": (to_t(Xg_tr), to_t(yg_tr, torch.long), class_weights(yg_tr, 3), to_t(Xg_val), to_t(yg_val, torch.long)),
            "hvf": (to_t(Xh_tr), to_t(yh_tr, torch.long), class_weights(yh_tr, 3), to_t(Xh_val), to_t(yh_val, torch.long)),
            "rnfl_gcc": (to_t(Xr_tr), to_t(yr_tr, torch.long), class_weights(yr_tr, 3), to_t(Xr_val), to_t(yr_val, torch.long)),
        }

        # M01-A: one private Trunk per dataset (no weight sharing at all).
        # M01-B: one Trunk instance, referenced by all three branches.
        shared_trunk = Trunk().to(device) if arch == "m01b" else None
        branches = {
            "gamma": DatasetBranch(Xg_tr.shape[1], shared_trunk or Trunk().to(device), n_classes=3).to(device),
            "hvf": DatasetBranch(Xh_tr.shape[1], shared_trunk or Trunk().to(device), n_classes=3).to(device),
            "rnfl_gcc": DatasetBranch(Xr_tr.shape[1], shared_trunk or Trunk().to(device), n_classes=3).to(device),
        }

        print(f"[{arch}] fold {fold_idx}: gamma train/val={len(g_train)}/{len(g_val)}  "
              f"hvf train/val={len(h_train)}/{len(h_val)}  rnfl_gcc train/val={len(r_train)}/{len(r_val)}")

        train_round(arch, fold_idx, branches, batches, writer, epochs, patience, lr, device)

        val_id_cols = {
            "gamma": g_val[["patient_id", "sample_id", "grade"]].rename(columns={"grade": "true_label"}),
            "hvf": h_val[["patient_id", "eye", "file", "severity_folder"]].rename(columns={"severity_folder": "true_label_raw"}),
            "rnfl_gcc": r_val[["si_no", "eye", "severity_label_str"]].rename(columns={"severity_label_str": "true_label_raw"}),
        }
        val_id_cols["hvf"]["true_label"] = val_id_cols["hvf"]["true_label_raw"].str.lower()
        val_id_cols["hvf"] = val_id_cols["hvf"].drop(columns=["true_label_raw"])
        val_id_cols["rnfl_gcc"]["true_label"] = val_id_cols["rnfl_gcc"]["true_label_raw"].str.lower()
        val_id_cols["rnfl_gcc"] = val_id_cols["rnfl_gcc"].drop(columns=["true_label_raw"])

        with torch.no_grad():
            for dataset, (_, _, _, Xval, yval) in batches.items():
                probs = torch.softmax(branches[dataset](Xval), dim=-1).cpu().numpy()
                y_np = yval.cpu().numpy()
                class_names = DATASETS[dataset]["class_names"]
                result = compute_metrics(y_np, probs, class_names)
                save_result(arch, dataset, fold_idx, val_id_cols[dataset], result, class_names, OUT_DIR)
                all_results.append({"arch": arch, "dataset": dataset, "fold": fold_idx, **result})
                m = result["metrics"]
                print(f"  [{arch}] {dataset} fold {fold_idx}: acc={m['accuracy']:.3f} "
                      f"bal_acc={m['balanced_accuracy']:.3f} macro_f1={m['macro_f1']:.3f} "
                      f"qwk={m['quadratic_weighted_kappa']:.3f}")

    return all_results


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke-test", action="store_true", help="1 fold, few epochs, verifies the pipeline runs end to end on real data.")
    ap.add_argument("--epochs", type=int, default=400)
    ap.add_argument("--patience", type=int, default=40)
    ap.add_argument("--lr", type=float, default=1e-3)
    args = ap.parse_args()

    if not GAMMA_EMBEDDINGS_CSV.exists():
        raise FileNotFoundError(f"{GAMMA_EMBEDDINGS_CSV} not found — run training/extract_gamma_embeddings.py first.")

    torch.manual_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    gamma_df, gamma_embed_cols = load_gamma()
    hvf_df = load_hvf()
    rnfl_df = load_rnfl_gcc()

    print(f"[m01] GAMMA: {len(gamma_df)} patients, embed_dim={len(gamma_embed_cols)}")
    print(f"[m01] HVF: {len(hvf_df)} eyes (patient-grouped folds), features={HVF_NUMERIC_FEATURES}")
    print(f"[m01] RNFL/GCC: {len(rnfl_df)} eye-rows (PLAIN stratified folds — no patient ID)")

    n_folds = 1 if args.smoke_test else DATASETS["gamma"]["n_folds"]
    epochs = 5 if args.smoke_test else args.epochs
    patience = 3 if args.smoke_test else args.patience

    TB_DIR.mkdir(parents=True, exist_ok=True)
    writer = SummaryWriter(log_dir=str(TB_DIR))

    all_results = []
    for arch in ("m01a", "m01b"):
        all_results += run_arch(arch, gamma_df, gamma_embed_cols, hvf_df, rnfl_df, writer, device,
                                 epochs, patience, args.lr, n_folds)
    writer.close()

    if args.smoke_test:
        print("\n[m01] SMOKE TEST PASSED — pipeline ran end to end on real data for both "
              "M01-A and M01-B on fold 0. This is NOT a real result — do not record these numbers.")
        return

    summary = aggregate(all_results, OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "config.json").write_text(json.dumps({
        "seed": SEED, "n_folds": n_folds, "epochs": epochs, "patience": patience, "lr": args.lr,
        "embed_dim": EMBED_DIM,
        "gamma_embedding_source": "training/extract_gamma_embeddings.py (fusion_run1.pt, resnet18/resnet18 — "
                                   "NOT the frozen EXP-05/06 EfficientNet-B0 checkpoint)",
        "hvf_features": HVF_NUMERIC_FEATURES,
        "rnfl_gcc_features": RNFL_GCC_NUMERIC_FEATURES,
        "rnfl_gcc_limitation": "plain StratifiedKFold, not patient-grouped — no patient ID exists "
                                "(dataset/rnfl_gcc_provenance_audit.md)",
    }, indent=2))
    print(f"\n[m01] wrote {OUT_DIR / 'summary.json'} and {OUT_DIR / 'config.json'}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
