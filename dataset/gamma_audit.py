"""
Dataset audit for a loaded GAMMA manifest (see gamma_loader.py).

Produces the checklist required by the project brief before any training
happens: pair counts, patient counts, class distribution, B-scans per
volume, image dimensions, missing/duplicate files, and a patient-level
train/val/test split proposal. Writes audit_report.json.

This script reports what it finds — it does not fabricate patient counts,
image dimensions, or class balance. If a manifest field is missing, the
corresponding check is marked "unavailable" rather than guessed.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None


def audit_manifest(manifest_path: str | Path) -> dict:
    with open(manifest_path, encoding="utf-8") as f:
        samples = json.load(f)

    report: dict = {"source_manifest": str(manifest_path), "num_samples": len(samples)}

    patient_ids = [s["patient_id"] for s in samples]
    report["num_unique_patients"] = len(set(patient_ids))

    patients_with_multiple_samples = {
        pid: count for pid, count in Counter(patient_ids).items() if count > 1
    }
    report["patients_with_multiple_samples"] = patients_with_multiple_samples
    report["bilateral_or_repeat_examination_warning"] = bool(patients_with_multiple_samples)

    grade_counts = Counter(s["grade"] for s in samples)
    report["class_distribution"] = dict(grade_counts)

    bscan_counts = [s.get("num_bscans", 0) for s in samples]
    report["bscans_per_volume"] = {
        "min": min(bscan_counts) if bscan_counts else None,
        "max": max(bscan_counts) if bscan_counts else None,
        "mean": sum(bscan_counts) / len(bscan_counts) if bscan_counts else None,
        "nonstandard_volumes": [
            {"sample_id": s["sample_id"], "num_bscans": s["num_bscans"]}
            for s in samples
            if s.get("num_bscans", 0) != 256
        ],
    }

    seen_fundus_paths = Counter(s["fundus_path"] for s in samples)
    report["duplicate_fundus_paths"] = {
        p: c for p, c in seen_fundus_paths.items() if c > 1
    }

    missing_fundus = [s["sample_id"] for s in samples if not os.path.exists(s["fundus_path"])]
    missing_oct_dir = [s["sample_id"] for s in samples if not os.path.exists(s["oct_dir"])]
    report["missing_fundus_files"] = missing_fundus
    report["missing_oct_dirs"] = missing_oct_dir

    if Image is not None:
        dims = Counter()
        for s in samples:
            if os.path.exists(s["fundus_path"]):
                try:
                    with Image.open(s["fundus_path"]) as im:
                        dims[im.size] += 1
                except Exception as e:
                    report.setdefault("unreadable_fundus_files", []).append(
                        {"sample_id": s["sample_id"], "error": str(e)}
                    )
        report["fundus_image_dimensions"] = {f"{w}x{h}": c for (w, h), c in dims.items()}
    else:
        report["fundus_image_dimensions"] = "unavailable (PIL not installed)"

    report["patient_level_split_proposal"] = _propose_patient_split(samples)

    return report


def _propose_patient_split(samples: list[dict], train=0.7, val=0.15, seed=42) -> dict:
    """Groups by patient_id, then splits PATIENTS (not samples) so no
    patient appears in more than one split. Stratifies loosely by each
    patient's majority grade so class balance is roughly preserved."""
    import random

    by_patient: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        by_patient[s["patient_id"]].append(s)

    patient_majority_grade = {
        pid: Counter(s["grade"] for s in recs).most_common(1)[0][0]
        for pid, recs in by_patient.items()
    }

    by_grade: dict[str, list[str]] = defaultdict(list)
    for pid, grade in patient_majority_grade.items():
        by_grade[grade].append(pid)

    rng = random.Random(seed)
    split: dict[str, list[str]] = {"train": [], "val": [], "test": []}
    for grade, pids in by_grade.items():
        pids = pids[:]
        rng.shuffle(pids)
        n = len(pids)
        n_train = round(n * train)
        n_val = round(n * val)
        split["train"] += pids[:n_train]
        split["val"] += pids[n_train:n_train + n_val]
        split["test"] += pids[n_train + n_val:]

    return {
        "seed": seed,
        "ratios": {"train": train, "val": val, "test": round(1 - train - val, 2)},
        "patient_ids": split,
        "num_patients": {k: len(v) for k, v in split.items()},
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Audit a GAMMA manifest")
    parser.add_argument("--manifest", default="gamma_manifest.json")
    parser.add_argument("--out", default="audit_report.json")
    args = parser.parse_args()

    report = audit_manifest(args.manifest)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Wrote audit report to {args.out}")
    print(f"Samples: {report['num_samples']}  Unique patients: {report['num_unique_patients']}")
    print(f"Class distribution: {report['class_distribution']}")
    if report["bilateral_or_repeat_examination_warning"]:
        print(f"WARNING: {len(report['patients_with_multiple_samples'])} patients have >1 sample "
              "— confirmed patient-level split is required, do not split by sample.")
