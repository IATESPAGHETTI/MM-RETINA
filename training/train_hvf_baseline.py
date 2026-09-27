"""
EXP-C01 — Real-World HVF Severity Baseline.

Standalone clinical study, per MM_RETINA_NEXT_HVF_EXPERIMENT.md: this does
NOT touch the frozen GAMMA Fundus+OCT benchmark, does NOT claim to improve
it, and does NOT fuse in the RNFL/GCC Excel (no patient/eye/date key exists
to link it to these HVF records — see MM_RETINA_SAFE_MULTIMODAL_STRATEGY.md).

Cohort: 168 real HVF eyes / 90 real patients (dataset/hvf_features.csv,
produced by dataset/hvf_feature_extraction.py). Labels are the ORIGINAL
Mild/Moderate/Severe clinical severity taxonomy — never renamed to or
pooled with GAMMA's Normal/Early/Progressive.

Unit of prediction: patient + eye (eye-level), NOT patient-level — severity
differs between fellow eyes for 27/90 patients (see audit), so collapsing
to one label per patient would destroy real information and would also be
an unjustified label-consistency assumption.

Splitting: patient-grouped 5-fold CV (GroupKFold on patient_id) so a
patient's two eyes never land in different folds, per the eye-level
labeling + splitting rules in MM_RETINA_SAFE_MULTIMODAL_STRATEGY.md
sections 12-13. All missing-value imputation and feature scaling is fit on
the training fold only and applied unchanged to that fold's validation
eyes — never fit on val, never fit on the pooled dataset.

Models (weakest/simplest first, per the doc's explicit instruction not to
start with a Transformer or a large model):
    1. Logistic Regression (linear baseline)
    2. Random Forest (nonlinear tabular baseline)
    3. Small MLP (3-class softmax), trained with class-weighted loss,
       TensorBoard logging per fold.

Usage:
    python training/train_hvf_baseline.py --feature-set full       # EXP-C01
    python training/train_hvf_baseline.py --feature-set no_proxy   # EXP-C01b:
        drops md_db/psd_db/vfi_pct (near-duplicates of the clinical
        staging criteria used to assign the label) to test whether the
        remaining reliability/demographic fields carry independent signal.
        See EXPERIMENTS.md for both experiments' results and conclusions.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from torch.utils.tensorboard import SummaryWriter

REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURES_CSV = REPO_ROOT / "dataset" / "hvf_features.csv"
OUT_DIR = REPO_ROOT / "results" / "hvf_c01"
TB_DIR = REPO_ROOT / "runs" / "hvf_c01"

SEVERITY_NAMES = ["mild", "moderate", "severe"]  # index-aligned with severity_label
SEED = 42
N_SPLITS = 5

# Only high/guessed-confidence NUMERIC fields go into the model. Deliberately
# excludes overall_result / md_significance / psd_significance: those are
# expert-derived categorical buckets of MD/PSD that are themselves close
# restatements of the severity label — using them as features would leak
# the target through a proxy, not test whether raw HVF indices carry signal.
NUMERIC_FEATURES_FULL = [
    "md_db", "psd_db", "vfi_pct", "false_positive_pct", "false_negative_pct",
    "fixation_loss_ratio", "test_duration_min", "refraction_used", "age_years",
]

# EXP-C01b feature set: md_db, psd_db, and vfi_pct removed. These three are
# not just correlated with severity — they are (or are near-duplicates of)
# the actual indices standard clinical criteria use to ASSIGN Mild/Moderate/
# Severe in the first place (see EXPERIMENTS.md's EXP-C01 caveat). Leaving
# them in tests "did we extract the tags correctly"; removing them tests
# whether the REMAINING, non-staging-criteria fields (catch-trial error
# rates, fixation reliability, test duration, refraction, age, sex) carry
# any independent severity signal on their own.
SEVERITY_PROXY_FEATURES = ["md_db", "psd_db", "vfi_pct"]
NUMERIC_FEATURES_NO_PROXY = [f for f in NUMERIC_FEATURES_FULL if f not in SEVERITY_PROXY_FEATURES]

FEATURE_SETS = {
    "full": NUMERIC_FEATURES_FULL,
    "no_proxy": NUMERIC_FEATURES_NO_PROXY,
}
CATEGORICAL_FEATURES = ["sex"]  # cheap, non-leaky; one-hot with an explicit "missing" bucket


def load_dataset() -> pd.DataFrame:
    if not FEATURES_CSV.exists():
        raise FileNotFoundError(
            f"{FEATURES_CSV} not found — run dataset/hvf_feature_extraction.py first. "
            "This script will not fabricate HVF features."
        )
    df = pd.read_csv(FEATURES_CSV)
    df = df[df["error"].isna()] if "error" in df.columns else df
    df["sex"] = df["sex"].fillna("unknown")
    return df.reset_index(drop=True)


def build_fold_matrices(df: pd.DataFrame, train_idx: np.ndarray, val_idx: np.ndarray,
                         numeric_features: list[str]):
    """Fits imputation/scaling/one-hot categories on the TRAIN fold only,
    applies the same fitted transform to val. Returns dense float arrays."""
    train_df, val_df = df.iloc[train_idx], df.iloc[val_idx]

    imputer = SimpleImputer(strategy="median")
    X_num_train = imputer.fit_transform(train_df[numeric_features])
    X_num_val = imputer.transform(val_df[numeric_features])

    scaler = StandardScaler()
    X_num_train = scaler.fit_transform(X_num_train)
    X_num_val = scaler.transform(X_num_val)

    # One-hot for sex, categories fixed from the TRAIN fold only.
    train_categories = sorted(train_df["sex"].unique())
    def onehot(series):
        return np.array([[1.0 if v == c else 0.0 for c in train_categories] for v in series])
    X_cat_train = onehot(train_df["sex"])
    X_cat_val = onehot(val_df["sex"])  # unseen categories in val silently map to all-zero row

    X_train = np.concatenate([X_num_train, X_cat_train], axis=1)
    X_val = np.concatenate([X_num_val, X_cat_val], axis=1)
    y_train = train_df["severity_label"].to_numpy()
    y_val = val_df["severity_label"].to_numpy()
    return X_train, y_train, X_val, y_val


class SmallMLP(nn.Module):
    def __init__(self, in_dim: int, n_classes: int = 3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 32), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(32, 16), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(16, n_classes),
        )

    def forward(self, x):
        return self.net(x)


def train_mlp_fold(X_train, y_train, X_val, y_val, fold_idx: int, writer: SummaryWriter,
                    epochs: int = 300, patience: int = 30, lr: float = 1e-3, seed: int = SEED):
    torch.manual_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Class weights from the TRAIN fold's label distribution only.
    counts = Counter(y_train.tolist())
    n = len(y_train)
    weights = torch.tensor(
        [n / (len(counts) * counts.get(c, 1)) for c in range(len(SEVERITY_NAMES))],
        dtype=torch.float32, device=device,
    )

    model = SmallMLP(X_train.shape[1]).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    loss_fn = nn.CrossEntropyLoss(weight=weights)

    Xtr = torch.tensor(X_train, dtype=torch.float32, device=device)
    ytr = torch.tensor(y_train, dtype=torch.long, device=device)
    Xva = torch.tensor(X_val, dtype=torch.float32, device=device)
    yva = torch.tensor(y_val, dtype=torch.long, device=device)

    best_val_loss = float("inf")
    best_state = None
    epochs_since_improve = 0

    for epoch in range(epochs):
        model.train()
        opt.zero_grad()
        logits = model(Xtr)
        loss = loss_fn(logits, ytr)
        loss.backward()
        opt.step()

        model.eval()
        with torch.no_grad():
            val_logits = model(Xva)
            val_loss = loss_fn(val_logits, yva).item()
            val_acc = (val_logits.argmax(-1) == yva).float().mean().item()

        writer.add_scalar(f"fold{fold_idx}/train_loss", loss.item(), epoch)
        writer.add_scalar(f"fold{fold_idx}/val_loss", val_loss, epoch)
        writer.add_scalar(f"fold{fold_idx}/val_acc", val_acc, epoch)

        if val_loss < best_val_loss - 1e-4:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            epochs_since_improve = 0
        else:
            epochs_since_improve += 1
            if epochs_since_improve >= patience:
                break

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        probs = torch.softmax(model(Xva), dim=-1).cpu().numpy()
    return probs


def compute_metrics(y_true: np.ndarray, probs: np.ndarray) -> dict:
    preds = probs.argmax(axis=-1)
    precision, recall, f1_per_class, support = precision_recall_fscore_support(
        y_true, preds, labels=list(range(len(SEVERITY_NAMES))), zero_division=0
    )
    metrics = {
        "num_eval_eyes": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, preds)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, preds)),
        "macro_f1": float(f1_score(y_true, preds, average="macro", zero_division=0)),
        "cohen_kappa": float(cohen_kappa_score(y_true, preds)),
        "quadratic_weighted_kappa": float(cohen_kappa_score(y_true, preds, weights="quadratic")),
        "per_class": {
            SEVERITY_NAMES[i]: {
                "precision": float(precision[i]), "recall": float(recall[i]),
                "f1": float(f1_per_class[i]), "support": int(support[i]),
            } for i in range(len(SEVERITY_NAMES))
        },
    }
    try:
        metrics["roc_auc_ovr_macro"] = float(
            roc_auc_score(y_true, probs, multi_class="ovr", average="macro", labels=list(range(len(SEVERITY_NAMES))))
        )
    except ValueError as e:
        metrics["roc_auc_ovr_macro"] = None
        metrics["roc_auc_error"] = str(e)
    cm = confusion_matrix(y_true, preds, labels=list(range(len(SEVERITY_NAMES))))
    return {"metrics": metrics, "confusion_matrix": cm.tolist(), "preds": preds, "probs": probs}


def save_fold_result(model_name: str, fold_idx: int, df_val: pd.DataFrame, result: dict, out_dir: Path):
    fold_dir = out_dir / model_name / f"fold{fold_idx}"
    fold_dir.mkdir(parents=True, exist_ok=True)
    (fold_dir / "metrics.json").write_text(json.dumps(result["metrics"], indent=2))

    with open(fold_dir / "confusion_matrix.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([""] + [f"pred_{g}" for g in SEVERITY_NAMES])
        for i, row in enumerate(result["confusion_matrix"]):
            writer.writerow([f"true_{SEVERITY_NAMES[i]}"] + row)

    preds, probs = result["preds"], result["probs"]
    rows = []
    for i, (_, r) in enumerate(df_val.iterrows()):
        row = {
            "patient_id": r["patient_id"], "eye": r["eye"], "file": r["file"],
            "true_label": SEVERITY_NAMES[int(r["severity_label"])],
            "pred_label": SEVERITY_NAMES[int(preds[i])],
        }
        row.update({f"prob_{SEVERITY_NAMES[c]}": float(probs[i, c]) for c in range(len(SEVERITY_NAMES))})
        rows.append(row)
    with open(fold_dir / "predictions.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def aggregate(all_results: list[dict], out_dir: Path) -> dict:
    summary = {}
    metric_names = ["accuracy", "balanced_accuracy", "macro_f1", "roc_auc_ovr_macro",
                     "cohen_kappa", "quadratic_weighted_kappa"]
    for model_name in sorted(set(r["model"] for r in all_results)):
        rows = [r for r in all_results if r["model"] == model_name]
        per_metric = {}
        for m in metric_names:
            values = [r["metrics"][m] for r in rows if r["metrics"].get(m) is not None]
            per_metric[m] = {
                "values_per_fold": values,
                "mean": float(np.mean(values)) if values else None,
                "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                "folds_skipped_missing_value": len(rows) - len(values),
            }
        summary[model_name] = per_metric
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def run_experiment(tag: str, numeric_features: list[str], out_dir: Path, tb_dir: Path):
    df = load_dataset()
    n_patients = df["patient_id"].nunique()
    print(f"[{tag}] {len(df)} eyes / {n_patients} patients loaded from {FEATURES_CSV}")
    print(f"[{tag}] numeric features used: {numeric_features}")
    class_dist = df["severity_folder"].value_counts().to_dict()
    print(f"[{tag}] eye-level class distribution: {class_dist}")

    groups = df["patient_id"].to_numpy()
    gkf = GroupKFold(n_splits=N_SPLITS)

    tb_dir.mkdir(parents=True, exist_ok=True)
    writer = SummaryWriter(log_dir=str(tb_dir))

    all_results = []
    for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(df, groups=groups)):
        # Hard assertion: no patient leakage between train/val for this fold.
        train_patients = set(df.iloc[train_idx]["patient_id"])
        val_patients = set(df.iloc[val_idx]["patient_id"])
        leaked = train_patients & val_patients
        if leaked:
            raise AssertionError(f"Fold {fold_idx}: patient leakage: {leaked}")

        X_train, y_train, X_val, y_val = build_fold_matrices(df, train_idx, val_idx, numeric_features)
        df_val = df.iloc[val_idx]
        val_dist = Counter(y_val.tolist())
        print(f"\n[{tag}] === Fold {fold_idx}/{N_SPLITS - 1} === "
              f"train_eyes={len(train_idx)} val_eyes={len(val_idx)} "
              f"val_class_dist={{k: v for k, v in val_dist.items()}}")

        # --- Logistic Regression ---
        lr = LogisticRegression(max_iter=2000, class_weight="balanced", multi_class="multinomial", random_state=SEED)
        lr.fit(X_train, y_train)
        result = compute_metrics(y_val, lr.predict_proba(X_val))
        save_fold_result("logistic_regression", fold_idx, df_val, result, out_dir)
        all_results.append({"model": "logistic_regression", "fold": fold_idx, **result})

        # --- Random Forest ---
        rf = RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=SEED, max_depth=5)
        rf.fit(X_train, y_train)
        result = compute_metrics(y_val, rf.predict_proba(X_val))
        save_fold_result("random_forest", fold_idx, df_val, result, out_dir)
        all_results.append({"model": "random_forest", "fold": fold_idx, **result})

        # --- Small MLP ---
        probs = train_mlp_fold(X_train, y_train, X_val, y_val, fold_idx, writer)
        result = compute_metrics(y_val, probs)
        save_fold_result("mlp", fold_idx, df_val, result, out_dir)
        all_results.append({"model": "mlp", "fold": fold_idx, **result})

        for model_name in ("logistic_regression", "random_forest", "mlp"):
            m = next(r for r in all_results if r["model"] == model_name and r["fold"] == fold_idx)["metrics"]
            print(f"[{tag}] fold {fold_idx} {model_name}: acc={m['accuracy']:.3f} "
                  f"bal_acc={m['balanced_accuracy']:.3f} macro_f1={m['macro_f1']:.3f} "
                  f"qwk={m['quadratic_weighted_kappa']:.3f} roc_auc={m.get('roc_auc_ovr_macro')}")

    writer.close()
    summary = aggregate(all_results, out_dir)
    (out_dir / "feature_set.json").write_text(json.dumps(
        {"tag": tag, "numeric_features": numeric_features, "categorical_features": CATEGORICAL_FEATURES}, indent=2
    ))
    print(f"\n[{tag}] wrote aggregate summary to {out_dir / 'summary.json'}")
    print(json.dumps(summary, indent=2))
    return summary


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--feature-set", choices=list(FEATURE_SETS.keys()), default="full",
                     help="'full' = EXP-C01 (includes md_db/psd_db/vfi_pct). "
                          "'no_proxy' = EXP-C01b (drops those 3 severity-staging-criteria fields).")
    args = ap.parse_args()

    if args.feature_set == "full":
        tag, out_dir, tb_dir = "hvf_c01", OUT_DIR, TB_DIR
    else:
        tag = "hvf_c01b"
        out_dir = REPO_ROOT / "results" / "hvf_c01b"
        tb_dir = REPO_ROOT / "runs" / "hvf_c01b"

    run_experiment(tag, FEATURE_SETS[args.feature_set], out_dir, tb_dir)


if __name__ == "__main__":
    main()
