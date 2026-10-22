"""Clinical-feature glaucoma models with patient-grouped 5-fold CV.

Ablations answer a specific question each:
  structural      RNFL/GCC/CDR/IOP/age/sex           -> the honest model
  structural_noage same without age                   -> is age a shortcut (controls are younger)?
  with_hvf_md     structural + HVF MD                 -> shows the circularity (MD defines the label)

Outputs (ml/results/clinical/):  metrics.json, oof_<task>_<variant>.csv
Final artefacts (models/):       clinical_<task>.joblib  (fit on all 303 eyes)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, cohen_kappa_score,
                             f1_score, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from research_data import (CLASS_NAMES, LEAKY_MD_FEATURES, NO_AGE_FEATURES, ROOT,
                           STRUCT_FEATURES, assign_folds, load_master)

OUT = ROOT / "ml" / "results" / "clinical"
MODELS = ROOT / "models"
VARIANTS = {"structural": STRUCT_FEATURES, "structural_noage": NO_AGE_FEATURES,
            "with_hvf_md": LEAKY_MD_FEATURES}
SEEDS = [42, 43, 44]


def make_model(name: str, seed: int):
    if name == "logreg":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                             LogisticRegression(max_iter=2000, C=0.5, class_weight="balanced"))
    if name == "rf":
        return make_pipeline(SimpleImputer(strategy="median"),
                             RandomForestClassifier(n_estimators=400, min_samples_leaf=2,
                                                    class_weight="balanced", random_state=seed, n_jobs=-1))
    return make_pipeline(SimpleImputer(strategy="median"),
                         HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200,
                                                        class_weight="balanced", random_state=seed))


def score(y, proba, task):
    pred = proba.argmax(1)
    m = {"accuracy": accuracy_score(y, pred), "balanced_accuracy": balanced_accuracy_score(y, pred),
         "macro_f1": f1_score(y, pred, average="macro")}
    if task == "binary":
        m["auc"] = roc_auc_score(y, proba[:, 1])
    else:
        m["qwk"] = cohen_kappa_score(y, pred, weights="quadratic")
        m["auc_ovr_macro"] = roc_auc_score(y, proba, multi_class="ovr", average="macro")
        rec = [float((pred[y == c] == c).mean()) for c in range(4)]
        m["per_class_recall"] = dict(zip(CLASS_NAMES, rec))
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()}


def cv_oof(df, folds, feats, task, mname, seed):
    y = df["binary" if task == "binary" else "label"].values
    nclass = 2 if task == "binary" else 4
    oof = np.zeros((len(df), nclass))
    for f in range(folds.max() + 1):
        tr, te = folds != f, folds == f
        m = make_model(mname, seed).fit(df.loc[tr, feats], y[tr])
        oof[te] = m.predict_proba(df.loc[te, feats])
    return y, oof


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    df = load_master()
    base_folds = assign_folds(df, 5, 42)
    df["fold"] = base_folds
    results: dict = {}
    for task in ("binary", "multiclass"):
        for variant, feats in VARIANTS.items():
            for mname in ("logreg", "rf", "hgb"):
                per_seed = []
                for s in SEEDS:
                    folds = assign_folds(df, 5, s)
                    y, oof = cv_oof(df, folds, feats, task, mname, s)
                    per_seed.append(score(y, oof, task))
                    if s == 42:
                        pd.DataFrame(oof, columns=[f"p{i}" for i in range(oof.shape[1])]).assign(
                            y=y, fold=folds, si=df.si, source=df.source).to_csv(
                            OUT / f"oof_{task}_{variant}_{mname}.csv", index=False)
                keys = [k for k in per_seed[0] if k != "per_class_recall"]
                agg = {k: {"mean": round(float(np.mean([r[k] for r in per_seed])), 4),
                           "sd": round(float(np.std([r[k] for r in per_seed])), 4)} for k in keys}
                if task == "multiclass":
                    agg["per_class_recall"] = {c: round(float(np.mean([r["per_class_recall"][c] for r in per_seed])), 3)
                                               for c in CLASS_NAMES}
                results[f"{task}/{variant}/{mname}"] = agg
                print(f"{task:10s} {variant:16s} {mname:6s} acc={agg['accuracy']['mean']:.3f}±{agg['accuracy']['sd']:.3f} "
                      f"bal={agg['balanced_accuracy']['mean']:.3f}", flush=True)
    # majority-class baseline for context
    cnt = df.label.value_counts(normalize=True)
    results["baseline_majority"] = {"binary": round(float(df.binary.mean()), 4),
                                    "multiclass": round(float(cnt.max()), 4)}
    (OUT / "metrics.json").write_text(json.dumps(results, indent=2))

    # Final deployable models: honest structural feature set, best of the three by CV balanced accuracy.
    final = {}
    for task in ("binary", "multiclass"):
        cands = {m: results[f"{task}/structural/{m}"]["balanced_accuracy"]["mean"] for m in ("logreg", "rf", "hgb")}
        best = max(cands, key=cands.get)
        y = df["binary" if task == "binary" else "label"].values
        model = make_model(best, 42).fit(df[STRUCT_FEATURES], y)
        joblib.dump({"model": model, "features": STRUCT_FEATURES, "classes": ["No glaucoma", "Glaucoma"]
                     if task == "binary" else CLASS_NAMES, "medians": df[STRUCT_FEATURES].median().to_dict(),
                     "ranges": {f: [float(df[f].min()), float(df[f].max())] for f in STRUCT_FEATURES},
                     "algo": best}, MODELS / f"clinical_{task}.joblib")
        final[task] = {"algo": best, "cv_balanced_accuracy": cands[best]}
    (OUT / "final_models.json").write_text(json.dumps(final, indent=2))
    print("final:", final)


if __name__ == "__main__":
    main()
