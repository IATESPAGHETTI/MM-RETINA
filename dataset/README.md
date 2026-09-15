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

## Why this project does NOT download the full 13.4GB here

This dev environment has no bandwidth/storage budget for a 13GB gated
medical dataset, and pulling it also requires you to have accepted GAMMA's
license terms on the official challenge page first. Run `gamma_loader.py`
and `gamma_audit.py` in an environment where you've done that (Kaggle/Colab
with a Hugging Face token, or a local machine with the official download).

## Files

- `gamma_loader.py` — resolves the dataset from either an official-layout
  local folder or the HF `imagefolder` mirror, and reconstructs
  sample-level (fundus, oct_volume, grade, patient_id) records.
- `gamma_audit.py` — runs the checklist from the project brief (pair counts,
  patient counts, class balance, B-scan counts per volume, image dims,
  missing/duplicate files, laterality) and writes `audit_report.json`.

## Patient-level splitting

`gamma_loader.py` groups by `patient_id` before any split. Never do
`train_test_split` on individual image rows for this dataset — 276 patients
producing 300 samples means some patients have both eyes/visits present,
and B-scans within one OCT volume are obviously not independent.
