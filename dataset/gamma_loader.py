"""
GAMMA dataset loader — reconstructs sample-level (fundus, OCT volume, grade,
patient) records from either:

  (a) an official-layout local extraction of the GAMMA challenge download, or
  (b) the Hugging Face `yujiaxue/GAMMA` imagefolder mirror.

Run this where you've actually accepted the GAMMA license and have the data
(Kaggle/Colab/local) — it is not meant to run in a bandwidth/storage-limited
sandbox. See README.md in this folder for the verified dataset facts and why
that matters for splitting.

This script never invents file paths that don't exist: every path is
verified before being added to a record, and unresolvable samples are
reported, not silently guessed at.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path

GRADE_MAP = {"normal": 0, "early": 1, "progressive": 2}


@dataclass
class GammaSample:
    sample_id: str
    patient_id: str
    fundus_path: str
    oct_dir: str
    num_bscans: int
    grade: str
    grade_index: int


def _infer_patient_id(sample_id: str) -> str:
    """GAMMA sample IDs generally encode the patient; strip any eye/visit
    suffix (e.g. '0001_OD' -> '0001'). Adjust this if your extracted
    labels.csv already carries an explicit patient_id column — prefer
    that column over inference whenever it exists."""
    m = re.match(r"^(\d+)", sample_id)
    return m.group(1) if m else sample_id


def load_from_official_layout(root: str | Path) -> list[GammaSample]:
    """Expects the structure documented in the GAMMA README:

        root/
          images/fundus/sample_XXXX_fundus.jpg
          images/oct/sample_XXXX_oct/*.jpg (256 B-scans)
          labels/grades.csv   (sample_id, grade[, patient_id])
    """
    root = Path(root)
    grades_csv = root / "labels" / "grades.csv"
    if not grades_csv.exists():
        raise FileNotFoundError(
            f"Expected {grades_csv} — this loader targets the official GAMMA "
            "layout. If you're using the HF mirror instead, call "
            "load_from_huggingface() below."
        )

    import csv

    samples: list[GammaSample] = []
    missing: list[str] = []

    with open(grades_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sample_id = row["sample_id"]
            grade = row["grade"].strip().lower()
            patient_id = row.get("patient_id") or _infer_patient_id(sample_id)

            fundus_path = root / "images" / "fundus" / f"sample_{sample_id}_fundus.jpg"
            oct_dir = root / "images" / "oct" / f"sample_{sample_id}_oct"

            if not fundus_path.exists() or not oct_dir.exists():
                missing.append(sample_id)
                continue

            bscans = sorted(oct_dir.glob("*.jpg")) + sorted(oct_dir.glob("*.png"))
            samples.append(
                GammaSample(
                    sample_id=sample_id,
                    patient_id=patient_id,
                    fundus_path=str(fundus_path),
                    oct_dir=str(oct_dir),
                    num_bscans=len(bscans),
                    grade=grade,
                    grade_index=GRADE_MAP.get(grade, -1),
                )
            )

    if missing:
        print(f"[gamma_loader] WARNING: {len(missing)} sample_ids in grades.csv "
              f"had no matching files on disk: {missing[:10]}{'...' if len(missing) > 10 else ''}")

    return samples


def load_from_huggingface(cache_dir: str | None = None):
    """Loads the HF `imagefolder` mirror. This is row-per-image (fundus rows
    and OCT B-scan rows interleaved with `split`/`label` metadata) — you
    must group rows back into samples using whatever id/label columns the
    current repo snapshot actually exposes.

    This function intentionally does NOT guess a fixed schema: HF dataset
    internals can change. It loads the dataset and hands you the raw
    object plus the column names actually present, so you can inspect
    them before trusting any downstream grouping logic.
    """
    try:
        from datasets import load_dataset
    except ImportError as e:
        raise ImportError(
            "pip install datasets huggingface_hub — required for the HF mirror path."
        ) from e

    ds = load_dataset("yujiaxue/GAMMA", cache_dir=cache_dir)
    print("[gamma_loader] Loaded splits:", list(ds.keys()))
    for split_name, split in ds.items():
        print(f"[gamma_loader] split={split_name} rows={len(split)} columns={split.column_names}")
    print(
        "[gamma_loader] Inspect the printed column names above and adapt the "
        "grouping logic to them — do not assume a fixed schema without checking."
    )
    return ds


def save_manifest(samples: list[GammaSample], out_path: str | Path) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([asdict(s) for s in samples], f, indent=2)
    print(f"[gamma_loader] wrote {len(samples)} sample records to {out_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load GAMMA dataset manifest")
    parser.add_argument("--root", help="Path to official-layout GAMMA extraction")
    parser.add_argument("--hf", action="store_true", help="Use the Hugging Face mirror instead")
    parser.add_argument("--out", default="gamma_manifest.json")
    args = parser.parse_args()

    if args.hf:
        load_from_huggingface()
    elif args.root:
        samples = load_from_official_layout(args.root)
        save_manifest(samples, args.out)
    else:
        parser.error("Pass --root <path> for a local extraction, or --hf for the HF mirror.")
