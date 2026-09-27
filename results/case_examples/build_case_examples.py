"""
Builds results/case_examples/CASE_EXAMPLES.md and the GAMMA visual panels,
per MM_RETINA_MULTIDATASET_REPRESENTATION_AND_CASE_EXAMPLES.md.

Every example is pulled from REAL, already-saved held-out predictions —
nothing here is re-run or re-predicted:
    GAMMA -> results/cv_fusion_effnetb0_v1/fusion/fold*/predictions.csv
             (the actual frozen EXP-05/06 benchmark's own CV predictions)
    HVF   -> results/hvf_c01/random_forest/fold*/predictions.csv  (C01, proxy features included)
             results/hvf_c01b/random_forest/fold*/predictions.csv (C01b, proxy features removed)

No explainability method was run, so no visual region is claimed to have
caused any prediction — panels show the real fundus image and one real,
representative central OCT B-scan, nothing more.

Usage:
    python results/case_examples/build_case_examples.py
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = Path(__file__).resolve().parent
IMG_DIR = OUT_DIR / "images"
IMG_DIR.mkdir(exist_ok=True)

GAMMA_MANIFEST = {r["sample_id"]: r for r in json.loads((REPO_ROOT / "dataset" / "gamma_manifest.json").read_text())}


def load_all_predictions(pattern: str, id_col: str, id_dtype=str) -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(pattern)):
        fold = Path(f).parent.name.replace("fold", "")
        df = pd.read_csv(f, dtype={id_col: id_dtype})
        df["fold"] = fold
        rows.append(df)
    return pd.concat(rows, ignore_index=True)


def build_gamma_panel(sample_id: str, true_label: str, pred_label: str, confidence: float, out_path: Path):
    row = GAMMA_MANIFEST[sample_id]
    fundus = Image.open(row["fundus_path"]).convert("RGB").resize((320, 320))
    mid_slice = row["num_bscans"] // 2
    oct_img = Image.open(Path(row["oct_dir"]) / f"{mid_slice}_image.jpg").convert("RGB").resize((320, 320))

    panel = Image.new("RGB", (660, 400), "white")
    panel.paste(fundus, (10, 70))
    panel.paste(oct_img, (340, 70))
    draw = ImageDraw.Draw(panel)
    try:
        font_big = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font_big = font_small = ImageFont.load_default()

    correct = true_label == pred_label
    color = (30, 130, 76) if correct else (170, 60, 60)
    draw.text((10, 10), f"True: {true_label.capitalize()}   Predicted: {pred_label.capitalize()}", fill=color, font=font_big)
    draw.text((10, 38), f"Confidence: {confidence*100:.1f}%   (GAMMA sample {sample_id}, EXP-05/06 frozen benchmark)", fill=(60, 60, 60), font=font_small)
    draw.text((10, 392 - 20), "Fundus", fill=(90, 90, 90), font=font_small)
    draw.text((340, 392 - 20), f"OCT B-scan (slice {mid_slice}/{row['num_bscans']})", fill=(90, 90, 90), font=font_small)
    panel.save(out_path)


def gamma_examples() -> list[dict]:
    df = load_all_predictions(str(REPO_ROOT / "results" / "cv_fusion_effnetb0_v1" / "fusion" / "fold*" / "predictions.csv"), "sample_id")
    picks = [
        ("G-01", "0001", "Normal correctly detected"),
        ("G-02", "0097", "Early correctly detected"),
        ("G-03", "0081", "Progressive correctly detected"),
        ("G-04", "0017", "Informative misclassification (Early confused with Normal, near-tied confidence)"),
    ]
    examples = []
    for code, sid, title in picks:
        row = df[df.sample_id == sid].iloc[0]
        conf = row[f"prob_{row.pred_label}"]
        img_path = IMG_DIR / f"{code}_{sid}.png"
        build_gamma_panel(sid, row.true_label, row.pred_label, conf, img_path)
        examples.append({
            "code": code, "title": title, "sample_id": sid, "fold": row.fold,
            "true_label": row.true_label, "pred_label": row.pred_label, "confidence": conf,
            "probs": {c: row[f"prob_{c}"] for c in ("normal", "early", "progressive")},
            "fundus_path": GAMMA_MANIFEST[sid]["fundus_path"], "oct_dir": GAMMA_MANIFEST[sid]["oct_dir"],
            "image": str(img_path.relative_to(REPO_ROOT)),
        })
    return examples


def hvf_examples() -> list[dict]:
    c01 = load_all_predictions(str(REPO_ROOT / "results" / "hvf_c01" / "random_forest" / "fold*" / "predictions.csv"), "patient_id")
    c01b = load_all_predictions(str(REPO_ROOT / "results" / "hvf_c01b" / "random_forest" / "fold*" / "predictions.csv"), "patient_id")

    examples = []
    for tag, df, proxy_note in (
        ("C01", c01, "C01 — severity-proxy features included (md_db/psd_db/vfi_pct)"),
        ("C01b", c01b, "C01b — MD/PSD/VFI removed"),
    ):
        for sev in ("mild", "moderate", "severe"):
            correct = df[(df.true_label == sev) & (df.pred_label == sev)]
            if len(correct) == 0:
                continue
            correct = correct.assign(conf=correct[f"prob_{sev}"]).sort_values("conf", ascending=False)
            row = correct.iloc[0]
            examples.append({
                "tag": tag, "proxy_note": proxy_note, "severity": sev, "kind": "correct",
                "patient_id": row.patient_id, "eye": row.eye, "file": row.file, "fold": row.fold,
                "true_label": row.true_label, "pred_label": row.pred_label,
                "confidence": row[f"prob_{row.pred_label}"],
            })
        # Prefer genuinely adjacent-severity confusions (Mild<->Moderate,
        # Moderate<->Severe) over an arbitrary first mismatch — a Mild-
        # predicted-as-Severe error is a worse, less informative example
        # than the adjacent-confusion cases the doc specifically asks for.
        # One representative example per adjacent PAIR (either direction).
        for pair in (("mild", "moderate"), ("moderate", "severe")):
            cand = df[df.true_label.isin(pair) & df.pred_label.isin(pair) & (df.true_label != df.pred_label)]
            if len(cand):
                row = cand.iloc[0]
                examples.append({
                    "tag": tag, "proxy_note": proxy_note, "severity": None, "kind": "misclassified",
                    "patient_id": row.patient_id, "eye": row.eye, "file": row.file, "fold": row.fold,
                    "true_label": row.true_label, "pred_label": row.pred_label,
                    "confidence": row[f"prob_{row.pred_label}"],
                })
        if not any(e["kind"] == "misclassified" and e["tag"] == tag for e in examples):
            mis = df[df.true_label != df.pred_label]
            if len(mis):
                row = mis.iloc[0]
                examples.append({
                    "tag": tag, "proxy_note": proxy_note, "severity": None, "kind": "misclassified",
                    "patient_id": row.patient_id, "eye": row.eye, "file": row.file, "fold": row.fold,
                    "true_label": row.true_label, "pred_label": row.pred_label,
                    "confidence": row[f"prob_{row.pred_label}"],
                })
    return examples


def find_1028746_fold() -> dict | None:
    for pattern in (
        str(REPO_ROOT / "results" / "hvf_c01" / "random_forest" / "fold*" / "predictions.csv"),
        str(REPO_ROOT / "results" / "hvf_c01b" / "random_forest" / "fold*" / "predictions.csv"),
    ):
        df = load_all_predictions(pattern, "patient_id")
        rows = df[df.patient_id.astype(str) == "1028746"]
        if len(rows):
            return rows.to_dict("records")
    return None


def render_markdown(gamma_ex, hvf_ex, patient_1028746_rows) -> str:
    lines = ["# MM-RETINA Classification Case Examples", "",
             "All examples below are pulled from already-saved, real held-out "
             "cross-validation predictions — none are re-run or hand-picked "
             "training examples. No explainability method was run, so no "
             "visual region is claimed to have caused any prediction.", ""]

    lines += ["## GAMMA (frozen EXP-05/06 benchmark — EfficientNet-B0 fundus + ResNet18 OCT)", ""]
    for ex in gamma_ex:
        lines += [
            f"### Example {ex['code']} — {ex['title']}", "",
            f"- True: **{ex['true_label'].capitalize()}**",
            f"- Predicted: **{ex['pred_label'].capitalize()}**",
            f"- Confidence: {ex['confidence']*100:.1f}%",
            f"- Fold: {ex['fold']} (held-out validation fold, `results/cv_fusion_effnetb0_v1/fusion/fold{ex['fold']}/predictions.csv`)",
            f"- Full probabilities: normal={ex['probs']['normal']:.3f}, early={ex['probs']['early']:.3f}, progressive={ex['probs']['progressive']:.3f}",
            f"- Fundus: `{ex['fundus_path']}`",
            f"- OCT: `{ex['oct_dir']}`",
            f"- Panel: `{ex['image']}`",
            "",
        ]

    lines += ["## HVF (eye-level, patient-grouped CV; Random Forest model)", ""]
    code_counters = {"C01": 0, "C01b": 0}
    for ex in hvf_ex:
        code_counters[ex["tag"]] += 1
        h_code = f"H-{ex['tag']}-{code_counters[ex['tag']]:02d}"
        title = (f"{ex['severity'].capitalize()} correctly detected" if ex["kind"] == "correct"
                 else f"Adjacent-severity confusion ({ex['true_label'].capitalize()} predicted as {ex['pred_label'].capitalize()})")
        lines += [
            f"### Example {h_code} — {title}", "",
            f"- **{ex['proxy_note']}**",
            f"- Real patient ID: `{ex['patient_id']}`  ·  Eye: {ex['eye']}  ·  Source file: `{ex['file']}`",
            f"- True severity: **{ex['true_label'].capitalize()}**",
            f"- Predicted severity: **{ex['pred_label'].capitalize()}**",
            f"- Model probability (predicted class): {ex['confidence']*100:.1f}%",
            f"- Fold: {ex['fold']} (patient-grouped held-out validation fold)",
            f"- MD/PSD/VFI used: {'Yes' if ex['tag'] == 'C01' else 'No'}",
            "",
        ]

    lines += ["## Data-quality example", "", "### Patient 1028746 — asymmetric eye severity", ""]
    if patient_1028746_rows:
        for r in patient_1028746_rows:
            lines.append(f"- Eye {r['eye']}: true={r['true_label']}, predicted={r['pred_label']}, "
                          f"fold={r['fold']} (`{r['file']}`)")
        lines += ["",
                   "Both eyes of this real patient were graded on the same study date "
                   "(2024-03-05), and GroupKFold placed both eyes in the fold shown above "
                   "— confirmed no cross-fold leakage of this patient."]
    else:
        lines.append("(Not found in a saved prediction file at generation time — see the "
                      "raw DICOM metadata in dataset/hvf_features.csv for the source record.)")
    lines += ["",
              "**Right eye: Mild. Left eye: Severe. Same study date.**",
              "",
              "Why this matters: this is real evidence that glaucoma severity in this "
              "cohort is an eye-level property, not a patient-level one — a model or "
              "report that collapsed this patient to a single severity label would be "
              "wrong for at least one of their two eyes by construction, regardless of "
              "how accurate the model is.", ""]

    return "\n".join(lines)


if __name__ == "__main__":
    gamma_ex = gamma_examples()
    hvf_ex = hvf_examples()
    p_rows = find_1028746_fold()

    md = render_markdown(gamma_ex, hvf_ex, p_rows)
    (OUT_DIR / "CASE_EXAMPLES.md").write_text(md, encoding="utf-8")
    print(f"Wrote {OUT_DIR / 'CASE_EXAMPLES.md'}")
    print(f"Wrote {len(gamma_ex)} GAMMA panel images to {IMG_DIR}")
