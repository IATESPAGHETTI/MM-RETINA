"""
Exploratory: do retinal-vessel features (from the merged RETINA/DIPP module) relate to the
GAMMA glaucoma grade?

Uses Kartik's DRIVE-trained vessel U-Net (weights NOT in git) via the newmix diabetes service:
  * vessel_density_pct   fraction of retinal-disc pixels labelled vessel
  * fractal_dimension    box-counting dimension of the vessel-mask boundary
Runs on CPU on all 100 GAMMA training fundus photographs, then:
  1. descriptive stats per grade + Kruskal-Wallis (exploratory, uncorrected)
  2. 5-fold patient-level CV of a tiny logistic model on the 2 features (same make_folds as EXP-05)
     vs the majority-class baseline.

Not a diagnostic claim. The U-Net was trained on DRIVE (adult fundus, different camera); transfer
to GAMMA photos is unverified except by the sanity overlays this script saves.

Usage (from training/):
    python vessel_features.py --unet <path/to/unet_drive.pth>
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
NEWMIX = REPO_ROOT / "past_work" / "RETINA" / "newmix"
sys.path.insert(0, str(NEWMIX / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import importlib.util  # noqa: E402

from cross_validate import make_folds  # noqa: E402

GRADES = ["normal", "early", "progressive"]


def load_service(unet_path: Path):
    import services.diabetes_service as ds  # needs newmix/backend on sys.path

    spec = importlib.util.spec_from_file_location("dipp_model", NEWMIX / "backend" / "dipp" / "model.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    net = mod.UNet().to(ds._DEV)
    net.load_state_dict(torch.load(unet_path, map_location="cpu"))
    ds._unet = net.eval()
    return ds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unet", required=True)
    ap.add_argument("--manifest", default="C:/Users/ASUS/Downloads/prj4/dataset/gamma_manifest.json")
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "results" / "vessel_features"))
    ap.add_argument("--n-overlays", type=int, default=6)
    args = ap.parse_args()

    out = Path(args.out_dir)
    (out / "overlays").mkdir(parents=True, exist_ok=True)
    manifest = json.loads(Path(args.manifest).read_text())
    ds = load_service(Path(args.unet))

    rows = []
    for i, r in enumerate(manifest):
        img = Image.open(r["fundus_path"]).convert("RGB")
        v = ds.vessels(img)
        f = ds.fractal(img)
        rows.append({"patient_id": r["patient_id"], "grade": r["grade"],
                     "vessel_density_pct": v["vessel_density_pct"],
                     "fractal_dimension": f["fractal_dimension"], "fractal_r2": f["r_squared"]})
        if i < args.n_overlays:
            import base64
            (out / "overlays" / f"{r['patient_id']}_{r['grade']}.png").write_bytes(
                base64.b64decode(v["overlay"].split(",", 1)[1]))
        if (i + 1) % 20 == 0:
            print(f"[vessel] {i + 1}/{len(manifest)}")

    with open(out / "features.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    summary: dict = {"n": len(rows), "per_grade": {}, "kruskal_wallis": {}}
    for feat in ("vessel_density_pct", "fractal_dimension"):
        groups = [[r[feat] for r in rows if r["grade"] == g] for g in GRADES]
        for g, vals in zip(GRADES, groups):
            summary["per_grade"].setdefault(g, {})[feat] = {
                "n": len(vals), "mean": float(np.mean(vals)), "std": float(np.std(vals, ddof=1))}
        h, p = stats.kruskal(*groups)
        summary["kruskal_wallis"][feat] = {"H": float(h), "p": float(p)}

    # tiny patient-level CV vs majority baseline
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    fold_of = make_folds(manifest, 5, 42)
    X = np.array([[r["vessel_density_pct"], r["fractal_dimension"]] for r in rows])
    y = np.array([GRADES.index(r["grade"]) for r in rows])
    folds = np.array([fold_of[r["patient_id"]] for r in rows])
    correct = base_correct = 0
    for f in range(5):
        tr, te = folds != f, folds == f
        sc = StandardScaler().fit(X[tr])
        clf = LogisticRegression(max_iter=1000, class_weight="balanced").fit(sc.transform(X[tr]), y[tr])
        correct += int((clf.predict(sc.transform(X[te])) == y[te]).sum())
        base_correct += int((np.bincount(y[tr]).argmax() == y[te]).sum())
    summary["cv_logistic_two_features"] = {"accuracy": correct / len(y), "majority_baseline_accuracy": base_correct / len(y)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
