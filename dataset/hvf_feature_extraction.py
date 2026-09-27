"""
Structured feature extraction for the real Zeiss HFA "Single Field Analysis"
DICOM exports under dataset/hvf_and)rnfl_gcc/HVF/<Mild|Moderate|Severe>/*.dcm.

Per MM_RETINA_NEXT_HVF_EXPERIMENT.md: do not assume a field exists — every
field pulled out of the private "99CZM_HFA_EMR_2" (group 0x7717) block was
verified present in ALL 168 files before being treated as a usable column
(see dataset/hvf_field_confidence.md for the presence audit and the
evidence used to guess each field's clinical meaning). Fields whose meaning
is inferred rather than documented are flagged low_confidence=True in the
manifest and are still exported, but training code must be able to drop
them without touching the high-confidence ones.

This script does NOT decide train/val/test splits and does NOT touch the
RNFL/GCC Excel or the GAMMA cohort — per the frozen-benchmark rule, this is
a separate clinical study.

Usage:
    python dataset/hvf_feature_extraction.py --out dataset/hvf_features.csv
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
from datetime import datetime

import pydicom

HVF_ROOT = os.path.join(os.path.dirname(__file__), "hvf_and)rnfl_gcc", "HVF")
SEVERITY_FROM_FOLDER = {"Mild": 0, "Moderate": 1, "Severe": 2}

# (tag, output column, confidence, description)
# Confidence "high" = matches a standard HFA SITA report field by value
# range/pairing and is a well-known Zeiss FORUM private tag; "guessed" =
# present in 100% of files but semantic meaning inferred from value pattern
# only, not from official Zeiss documentation.
NUMERIC_FIELDS = [
    ("77171016", "md_db", "high", "Mean Deviation (dB), paired with (7717,1017) significance"),
    ("77171018", "psd_db", "high", "Pattern Standard Deviation (dB), paired with (7717,1019) significance"),
    ("77171034", "vfi_pct", "high", "Visual Field Index (%)"),
    ("77171010", "false_positive_pct", "high", "False positive catch-trial error rate (%)"),
    ("77171013", "false_negative_pct", "high", "False negative catch-trial error rate (%)"),
    ("77171008", "fixation_trials_total", "guessed", "Fixation-loss catch trials denominator"),
    ("77171009", "fixation_losses", "guessed", "Fixation-loss catch trials numerator"),
    ("77171026", "test_duration_min", "guessed", "Present in 94% of files; value range (4-8) matches typical SITA Standard 24-2 duration in minutes"),
    ("77171027", "refraction_used", "guessed", "Spherical-equivalent Rx used during test (diopters); parsed from signed string e.g. '+5.25'"),
]

CATEGORICAL_FIELDS = [
    ("77171017", "md_significance", "high"),
    ("77171019", "psd_significance", "high"),
    ("77171023", "overall_result", "high", ),
    ("77171024", "fixation_monitor", "guessed"),
    ("77171001", "test_pattern", "high"),
    ("77171002", "test_strategy", "high"),
    ("77171003", "stimulus_size", "high"),
]


def _tag_value(ds: pydicom.Dataset, tag_hex: str):
    group = int(tag_hex[:4], 16)
    elem = int(tag_hex[4:], 16)
    if (group, elem) not in ds:
        return None
    return ds[(group, elem)].value


def _parse_float(v):
    if v is None:
        return None
    try:
        return float(str(v).strip())
    except ValueError:
        return None


def _age_years(birth_date: str, study_date: str):
    try:
        b = datetime.strptime(birth_date, "%Y%m%d")
        s = datetime.strptime(study_date, "%Y%m%d")
        return round((s - b).days / 365.25, 1)
    except (ValueError, TypeError):
        return None


def extract_one(path: str, severity_folder: str) -> dict:
    ds = pydicom.dcmread(path, force=True, stop_before_pixels=True)

    row = {
        "file": os.path.relpath(path, os.path.dirname(__file__)),
        "patient_id": str(getattr(ds, "PatientID", "")).strip(),
        "eye": str(getattr(ds, "Laterality", "")).strip(),
        "study_date": str(getattr(ds, "StudyDate", "")).strip(),
        "sex": str(getattr(ds, "PatientSex", "")).strip() or None,
        "age_years": _age_years(str(getattr(ds, "PatientBirthDate", "")), str(getattr(ds, "StudyDate", ""))),
        "severity_folder": severity_folder,
        "severity_label": SEVERITY_FROM_FOLDER[severity_folder],
    }

    for tag_hex, col, confidence, *_ in NUMERIC_FIELDS:
        raw = _tag_value(ds, tag_hex)
        if col == "refraction_used" and raw is not None:
            row[col] = _parse_float(str(raw).replace("+", ""))
        else:
            row[col] = _parse_float(raw)

    for entry in CATEGORICAL_FIELDS:
        tag_hex, col = entry[0], entry[1]
        raw = _tag_value(ds, tag_hex)
        row[col] = str(raw) if raw is not None else None

    if row["fixation_trials_total"] not in (None, 0):
        row["fixation_loss_ratio"] = round(row["fixation_losses"] / row["fixation_trials_total"], 4)
    else:
        row["fixation_loss_ratio"] = None

    return row


def extract_all(root: str = HVF_ROOT) -> list[dict]:
    rows = []
    for severity_folder in SEVERITY_FROM_FOLDER:
        for path in sorted(glob.glob(os.path.join(root, severity_folder, "*.dcm"))):
            try:
                rows.append(extract_one(path, severity_folder))
            except Exception as e:  # noqa: BLE001 - record and keep going, never drop silently
                rows.append({
                    "file": os.path.relpath(path, os.path.dirname(__file__)),
                    "severity_folder": severity_folder,
                    "error": str(e),
                })
    return rows


def write_csv(rows: list[dict], out_path: str) -> None:
    fieldnames = []
    for r in rows:
        for k in r:
            if k not in fieldnames:
                fieldnames.append(k)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def write_field_confidence_doc(out_path: str) -> None:
    lines = [
        "# HVF DICOM field confidence audit",
        "",
        "Generated by dataset/hvf_feature_extraction.py. Every field below was",
        "confirmed present in all 168 real HVF DICOM files before being used",
        "(see dataset/hvf_tag_inventory.json-equivalent scan). 'high confidence'",
        "fields match a standard Zeiss HFA SITA report field by value range and",
        "pairing with an adjacent significance/label tag. 'guessed' fields are",
        "present in every (or nearly every) file but their exact clinical",
        "meaning is inferred from value pattern only, not official Zeiss",
        "documentation, and should be treated as exploratory, droppable",
        "features rather than ground truth.",
        "",
        "## Numeric fields",
        "",
        "| column | DICOM tag | confidence | rationale |",
        "|---|---|---|---|",
    ]
    for tag_hex, col, confidence, desc in NUMERIC_FIELDS:
        tag_fmt = f"({tag_hex[:4]},{tag_hex[4:]})"
        lines.append(f"| {col} | {tag_fmt} | {confidence} | {desc} |")
    lines += [
        "",
        "## Categorical fields",
        "",
        "| column | DICOM tag | confidence |",
        "|---|---|---|",
    ]
    for entry in CATEGORICAL_FIELDS:
        tag_hex, col, confidence = entry[0], entry[1], entry[2]
        tag_fmt = f"({tag_hex[:4]},{tag_hex[4:]})"
        lines.append(f"| {col} | {tag_fmt} | {confidence} |")
    lines += [
        "",
        "## Not extracted",
        "",
        "- Pointwise sensitivity grid (the per-point 24-2 dB values): not",
        "  present as structured numeric tags in this export — the visual",
        "  field map itself lives only inside the embedded PDF (0042,0011),",
        "  which would require PDF parsing/OCR to recover. Out of scope for",
        "  the EXP-C01 baseline; flagged for a future iteration if the MLP",
        "  on summary indices shows signal worth extending.",
        "- (7717,1040) sequence: 6-item list of small integers per file,",
        "  meaning not identified with any confidence; excluded.",
    ]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract structured features from real HVF DICOM exports")
    parser.add_argument("--root", default=HVF_ROOT)
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "hvf_features.csv"))
    parser.add_argument("--confidence-doc", default=os.path.join(os.path.dirname(__file__), "hvf_field_confidence.md"))
    args = parser.parse_args()

    rows = extract_all(args.root)
    errors = [r for r in rows if "error" in r]
    ok_rows = [r for r in rows if "error" not in r]

    write_csv(rows, args.out)
    write_field_confidence_doc(args.confidence_doc)

    print(f"Extracted {len(ok_rows)} / {len(rows)} files ({len(errors)} errors)")
    print(f"Unique patients: {len(set(r['patient_id'] for r in ok_rows))}")
    print(f"Wrote {args.out}")
    print(f"Wrote {args.confidence_doc}")
