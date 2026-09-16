"""
Extract real B-scan slices from a GAMMA .mhd/.raw OCT volume into JPEGs
the website can serve directly — no server-side volume parsing needed.

Usage:
    python extract_oct_slices.py <sample_dir> <out_dir> [--width 320] [--every 1]

<sample_dir> is the folder containing <id>_Sequence_OCT_Iowa.mhd/.raw
(e.g. GAMMA/grading/Glaucoma_grading/training/multi-modality_images/0001/0001_Sequence).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
from PIL import Image


def parse_mhd(mhd_path: Path) -> dict:
    fields = {}
    for line in mhd_path.read_text().splitlines():
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        fields[key.strip()] = val.strip()
    return fields


def load_volume(sample_dir: Path) -> np.ndarray:
    mhd_files = list(sample_dir.glob("*_OCT_Iowa.mhd"))
    if not mhd_files:
        raise FileNotFoundError(f"No *_OCT_Iowa.mhd found in {sample_dir}")
    mhd = parse_mhd(mhd_files[0])

    if mhd["ElementType"] != "MET_UCHAR":
        raise ValueError(f"Unsupported ElementType {mhd['ElementType']} — only MET_UCHAR handled")

    w, h, d = (int(x) for x in mhd["DimSize"].split())
    raw_path = sample_dir / mhd["ElementDataFile"]
    data = np.fromfile(raw_path, dtype=np.uint8)
    expected = w * h * d
    if data.size != expected:
        raise ValueError(f"Raw file size {data.size} != expected {expected} (w={w} h={h} d={d})")

    # ITK MetaImage: fastest-varying axis first (X), then Y, then Z.
    volume = data.reshape((d, h, w))
    return volume


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--width", type=int, default=320, help="Output slice width in px")
    ap.add_argument("--every", type=int, default=1, help="Keep every Nth slice")
    ap.add_argument("--quality", type=int, default=78, help="JPEG quality")
    args = ap.parse_args()

    volume = load_volume(args.sample_dir)
    depth, height, width = volume.shape
    print(f"Loaded volume: {depth} B-scans, {width}x{height} each")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    scale = args.width / width
    out_h = round(height * scale)

    kept = 0
    for i in range(0, depth, args.every):
        slice_img = Image.fromarray(volume[i], mode="L").resize((args.width, out_h), Image.LANCZOS)
        slice_img.save(args.out_dir / f"{i:03d}.jpg", quality=args.quality, optimize=True)
        kept += 1

    print(f"Wrote {kept} slices to {args.out_dir} ({args.width}x{out_h} each)")


if __name__ == "__main__":
    main()
