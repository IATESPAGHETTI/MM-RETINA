"""
Deterministic, patient-level stratified split of the GAMMA training
manifest into train/val/test.

Patient-level, not sample-level: even though this particular manifest
happens to have one sample per patient (verified by gamma_audit.py — 100
samples, 100 unique patients, no bilateral entries), we still split by
`patient_id` rather than by row index or `sample_id`. That keeps this
script correct if it's ever pointed at a manifest where that 1:1 mapping
doesn't hold (e.g. a future extraction that includes bilateral eyes), and
it costs nothing here since patient_id == sample_id in the current data.

Usage:
    python split_gamma.py \
        --manifest ../dataset/gamma_manifest.json \
        --out ../dataset/splits/gamma_split_v1.json \
        --seed 42 --train 0.70 --val 0.15
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


def git_commit_or_none() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=Path(__file__).parent
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except FileNotFoundError:
        return None


def make_split(manifest: list[dict], seed: int, train: float, val: float) -> dict:
    test = round(1 - train - val, 4)
    assert abs(train + val + test - 1.0) < 1e-6, "train+val+test must sum to 1"

    by_patient: dict[str, list[dict]] = defaultdict(list)
    for row in manifest:
        by_patient[row["patient_id"]].append(row)

    # Stratify by each patient's majority grade so class balance is
    # preserved across splits (small-N dataset — this matters a lot at 100
    # samples).
    patient_grade = {
        pid: Counter(r["grade"] for r in rows).most_common(1)[0][0]
        for pid, rows in by_patient.items()
    }
    by_grade: dict[str, list[str]] = defaultdict(list)
    for pid, grade in patient_grade.items():
        by_grade[grade].append(pid)

    rng = random.Random(seed)
    assignment: dict[str, str] = {}
    for grade, pids in by_grade.items():
        pids = sorted(pids)  # sort first so shuffle is reproducible across platforms
        rng.shuffle(pids)
        n = len(pids)
        n_train = round(n * train)
        n_val = round(n * val)
        for pid in pids[:n_train]:
            assignment[pid] = "train"
        for pid in pids[n_train : n_train + n_val]:
            assignment[pid] = "val"
        for pid in pids[n_train + n_val :]:
            assignment[pid] = "test"

    sample_split = {row["sample_id"]: assignment[row["patient_id"]] for row in manifest}

    counts = {
        split: Counter(
            row["grade"] for row in manifest if sample_split[row["sample_id"]] == split
        )
        for split in ("train", "val", "test")
    }

    return {
        "seed": seed,
        "ratios": {"train": train, "val": val, "test": test},
        "git_commit": git_commit_or_none(),
        "num_samples": len(manifest),
        "num_patients": len(by_patient),
        "sample_split": sample_split,
        "class_distribution_per_split": {
            split: dict(c) for split, c in counts.items()
        },
    }


def verify_no_patient_leakage(manifest: list[dict], split: dict) -> None:
    """Hard-fails if any patient_id appears in more than one split — the
    one invariant this whole pipeline depends on."""
    patient_splits: dict[str, set[str]] = defaultdict(set)
    for row in manifest:
        s = split["sample_split"][row["sample_id"]]
        patient_splits[row["patient_id"]].add(s)

    leaked = {pid: splits for pid, splits in patient_splits.items() if len(splits) > 1}
    if leaked:
        raise AssertionError(f"Patient leakage across splits detected: {leaked}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="../dataset/gamma_manifest.json")
    ap.add_argument("--out", default="../dataset/splits/gamma_split_v1.json")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--train", type=float, default=0.70)
    ap.add_argument("--val", type=float, default=0.15)
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    split = make_split(manifest, args.seed, args.train, args.val)
    verify_no_patient_leakage(manifest, split)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(split, indent=2))

    print(f"[split_gamma] Verified: no patient appears in more than one split.")
    print(f"[split_gamma] Wrote split for {split['num_samples']} samples "
          f"({split['num_patients']} patients) to {out_path}")
    for s in ("train", "val", "test"):
        n = sum(1 for v in split["sample_split"].values() if v == s)
        print(f"  {s:5s}: {n:3d} samples  {split['class_distribution_per_split'][s]}")
