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

## Current status: the real dataset is being downloaded locally

A git-lfs clone of the official GAMMA layout now lives at `GAMMA/` in this
folder (gitignored — see below). It has the real structure, verified by
inspection rather than guessed:

```
GAMMA/grading/Glaucoma_grading/
  License-GAMMA_1019.pdf
  training/
    glaucoma_grading_training_GT.xlsx   — columns: data, non, early, mid_advanced
    multi-modality_images/<id>/<id>.jpg              — fundus photo
    multi-modality_images/<id>/<id>_Sequence/
        <id>_Sequence_OCT_Iowa.mhd + .raw            — the OCT volume (512x992x256 uint8)
  testing/
    multi-modality_images/...   — no labels shipped (challenge leaderboard holdout)
```

`<id>` is the sample number zero-padded to 4 digits. Only the `training`
split (100 samples) ships grades — `non`/`early`/`mid_advanced` are one-hot
columns mapping to Normal/Early/Progressive. `gamma_loader.py` was
originally written against a guessed schema before this real structure was
known; it's now been corrected to match the structure above exactly (see
`load_from_official_layout`).

As of this writing the LFS pull is incomplete: sample 0001 has its OCT
volume synced, the rest mostly have their fundus JPEG but not yet the
`_Sequence/*.raw` volume. The loader reports these as "missing", not
fabricated — rerun it as more of the clone finishes syncing.

This dev environment has no bandwidth/storage budget to drive that full
13GB pull itself, and pulling it also required accepting GAMMA's license
terms on the official challenge page first (already done, since the clone
exists) — that's a step you did, not something this session automated.

## Files

- `gamma_loader.py` — loads the real official "training" split layout above
  (or the HF `imagefolder` mirror via `load_from_huggingface()`), and
  reconstructs sample-level (fundus, oct_dir, grade, patient_id) records.
- `gamma_audit.py` — runs the checklist from the project brief (pair counts,
  patient counts, class balance, B-scan counts per volume, image dims,
  missing/duplicate files, laterality) and writes `audit_report.json`.
- `extract_oct_slices.py` — reads a sample's `.mhd`/`.raw` OCT volume and
  writes each B-scan out as a JPEG (used to populate
  `../website/public/oct-volume/<id>/` for the site's interactive viewer).

## Patient-level splitting

`gamma_loader.py` groups by `patient_id` before any split. Never do
`train_test_split` on individual image rows for this dataset — 276 patients
producing 300 samples means some patients have both eyes/visits present,
and B-scans within one OCT volume are obviously not independent.
