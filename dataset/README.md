# GAMMA dataset — access, audit, loading

## What GAMMA actually is (verified against the official sources)

- **Official page (use this first, always):** https://gamma.grand-challenge.org/
- **HF mirror used for programmatic loading:** https://huggingface.co/datasets/yujiaxue/GAMMA
- **Paper:** Wu, Fang, Li, Fu, Lin et al., "GAMMA challenge: Glaucoma grAding from
  Multi-Modality imAges", Medical Image Analysis 2023, DOI 10.1016/j.media.2023.102938.
  arXiv: https://arxiv.org/abs/2202.06511
- **License:** CC BY-NC-ND, distributed via the official challenge page — accepting
  the challenge's terms is a step *you* need to do (registration/agreement),
  not something automatable. The HF mirror is convenient for loading but is
  not a substitute for citing/crediting the official release.

Verified facts (from the HF dataset card, cross-checked against the challenge
description — do not inflate or round these differently in the report/website):

- 300 paired samples (fundus + OCT), 276 patients (some bilateral).
- Each OCT volume: 256 B-scans, 3×3mm en-face FOV, Topcon DRI OCT Triton.
- Fundus: KOWA / Topcon TRC-NW400, macula or disc-midpoint centered.
- Grade derived from visual-field Mean Deviation (MD): Early (MD > -6dB),
  Intermediate (-12dB < MD <= -6dB), Advanced (MD <= -12dB). Challenge task
  groups Intermediate+Advanced into a single "Progressive" class, i.e. 3-way:
  Normal / Early / Progressive.
- The HF `imagefolder` copy is split per B-scan/image (~52k rows total,
  13.4GB) — this is NOT 300 rows. You must reconstruct the 300
  fundus+volume pairs yourself; do not train sample-level splits on the raw
  row count or you will leak patients across train/val/test.

## Current status: training split fully synced and audited

A git-lfs clone of the official GAMMA layout lives at `GAMMA/` in this
folder (gitignored — see below). It has the real structure, verified by
inspection rather than guessed:

```
GAMMA/grading/Glaucoma_grading/
  License-GAMMA_1019.pdf
  training/
    glaucoma_grading_training_GT.xlsx   — columns: data, non, early, mid_advanced
    multi-modality_images/<id>/<id>.jpg          — fundus photo
    multi-modality_images/<id>/<id>/<n>_image.jpg — real per-slice B-scans (n = 0..255)
    multi-modality_images/<id>/<id>_Sequence/
        <id>_Sequence_OCT_Iowa.mhd + .raw            — the same volume, ITK format
  testing/
    multi-modality_images/...   — no labels shipped (challenge leaderboard holdout)
```

`<id>` is the sample number zero-padded to 4 digits. Only the `training`
split (100 samples) ships grades — `non`/`early`/`mid_advanced` are one-hot
columns mapping to Normal/Early/Progressive. `gamma_loader.py` was
originally written against a guessed schema before any real data existed;
it's now corrected against the structure above.

**All 100 training samples are fully synced.** Running

```bash
python gamma_loader.py --root GAMMA/grading/Glaucoma_grading/training --out gamma_manifest.json
python gamma_audit.py --manifest gamma_manifest.json --out audit_report.json
```

gives a clean bill of health:

- 100/100 samples loaded, 0 missing fundus or OCT files
- 100 unique patients — **no bilateral/repeat entries in this split**, so a
  patient-level split here is equivalent to a sample-level split (still use
  `gamma_audit.py`'s split proposal for reproducibility/seeding, not because
  leakage is otherwise possible)
- Every volume has exactly 256 B-scans, no exceptions
- Class distribution: 50 normal / 26 early / 24 progressive — matches the
  dataset card's stated ~52%/~48% early/progressive split of the glaucoma
  half almost exactly
- Two fundus resolutions in the wild: 1956x1934 (6 samples) and 2992x2000
  (94 samples) — resize to a common size before batching for training

The `testing` split (samples 0101+) has no labels — it's the challenge's
held-out leaderboard set, not usable for your own supervised splits.

## Files

- `gamma_loader.py` — loads the real official "training" split layout above
  (or the HF `imagefolder` mirror via `load_from_huggingface()`), and
  reconstructs sample-level (fundus, oct_dir, grade, patient_id) records.
- `gamma_audit.py` — runs the checklist from the project brief (pair counts,
  patient counts, class balance, B-scan counts per volume, image dims,
  missing/duplicate files, laterality) and writes `audit_report.json`.
- `extract_oct_slices.py` — reads a sample's `.mhd`/`.raw` OCT volume and
  writes each B-scan out as a JPEG. Not needed for the loader above (which
  uses the dataset's own pre-extracted `<n>_image.jpg` files directly), but
  useful if you ever need the ITK volume's exact voxel spacing/orientation
  metadata that the flat JPEGs don't carry.

## Patient-level splitting

`gamma_loader.py` groups by `patient_id` before any split. Never do
`train_test_split` on individual image rows for this dataset — 276 patients
producing 300 samples means some patients have both eyes/visits present,
and B-scans within one OCT volume are obviously not independent.
