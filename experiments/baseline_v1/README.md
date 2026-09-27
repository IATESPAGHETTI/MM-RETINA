# baseline_v1 — frozen fusion comparison reference

This is the immutable baseline for the EXP-01..EXP-06 ablation series
(`MM_RETINA_NEXT_EXPERIMENTS.md`). Every later fusion experiment in that
series is compared against these exact numbers, on these exact folds.

Fundus + OCT fusion model, **single-slice OCT representation** (the
pre-2.5D baseline), resnet18/resnet18 encoders, cross-modal transformer
fusion, 5-fold patient-level grade-stratified CV, seed=42.

## Results (mean ± std across 5 folds, ddof=1)

| Metric | Value |
|---|---:|
| Accuracy | 0.731 ± 0.072 |
| Balanced accuracy | 0.691 ± 0.071 |
| Macro F1 | 0.681 ± 0.077 |
| ROC-AUC (OvR macro) | 0.875 ± 0.037 |
| Cohen's Kappa | 0.577 ± 0.112 |
| Quadratic Weighted Kappa | 0.775 ± 0.071 |

Per-fold values and confusion matrices: `../../results/cv_fusion_baseline_v1/`.
Full config: `config.json`. Provenance/notes: `metadata.json`.

## Why this exists

The original 5-fold fusion baseline (`cv-run-1`, 2026-09-17,
`results/cv/fusion/`) predates Kappa/QWK support. This is a fresh run on
the identical seed/fold assignment/hyperparameters, under the current
evaluation code, so later experiments can be compared on the complete
metric set (including kappa/QWK) — not a different experiment, a
same-protocol re-verification. See `metadata.json` for the small,
expected (GPU non-determinism) numeric differences from the original run.

## Dataset caveat

100 labeled patients (Normal 50 / Early 26 / Progressive 24) — the full
supervised GAMMA benchmark actually available on disk. The GAMMA
"testing" split's other 100 samples have no public labels anywhere in
this download (see `dataset/audit_report.json`).
