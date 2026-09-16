# EXPERIMENTS.md

Log of every actual training/evaluation run. Never delete entries, even
failed ones — a failed run is still real information.

---

## cv-smoke-test-1

- **Date:** 2026-09-17
- **Git commit:** a4a9da4
- **Purpose:** validate `training/cross_validate.py` end-to-end (fold
  construction, per-fold split writing, leakage check, training, checkpoint
  reload, evaluation) before committing to a full 5-fold x 3-modality run.
- **Command:** `python cross_validate.py --smoke-test`
- **Fold construction:** 100 patients round-robin-assigned (grade-stratified,
  seed=42) across 5 folds: sizes {0: 21, 1: 20, 2: 20, 3: 20, 4: 19}. Fold 0
  verified programmatically to have zero patient overlap between its
  train (79 patients) and val (21 patients) sets.
- **Real 1-epoch train+eval, fold 0, tiny config (img_size=96, oct_slices=4,
  batch_size=4, 1 epoch):**
  - fundus: best_epoch=1, val_loss=1.0616, eval_accuracy=0.571 (n=21), 9.6s
  - oct: best_epoch=1, val_loss=1.1394, eval_accuracy=0.381 (n=21), 8.2s
  - fusion: best_epoch=1, val_loss=1.0820, eval_accuracy=0.333 (n=21), 8.4s
- **Status:** PASSED. These accuracy numbers are from a single untrained-ish
  epoch on tiny images — meaningless as performance numbers, only useful to
  confirm the full fold→train→checkpoint→eval→CSV pipeline runs without
  error on real data. Smoke-test split/checkpoints deleted after the run.
- **Notes:** No bugs found this time (unlike the single-split pipeline,
  which surfaced the manifest-path bug during its own smoke test) — the CV
  script reuses `run_training`/`run_evaluation`/`GammaMultimodalDataset`
  unchanged, so it inherited that already-fixed code path.

---

## cv-run-1 (5-fold cross-validation, fundus / OCT / fusion)

- **Date:** 2026-09-17
- **Git commit:** a4a9da4 (cross_validate.py added same session)
- **Command:**
  ```
  python cross_validate.py --k 5 --epochs 25 --img-size 160 --oct-slices 8 \
      --batch-size 4 --lr 1e-4 --focal-loss --amp --patience 8 --seed 42
  ```
- **Folds:** patient-level, grade-stratified round-robin, seed=42, same
  fold assignment as cv-smoke-test-1 (sizes 21/20/20/20/19 patients).
  Each fold's train/val split written to `dataset/splits/cv/fold{0..4}.json`
  and leakage-checked (hard assertion) before any training on it.
- **Architecture/hyperparameters:** identical to fusion_run1/fundus_run1/
  oct_run1 (resnet18 encoders, ImageNet-pretrained, fusion_dim=256,
  modality_dropout=0.15, focal loss gamma=2.0 with inverse-frequency class
  weights recomputed per fold's real train counts, AdamW lr=1e-4 wd=1e-4,
  CosineAnnealingLR, AMP, early stopping patience=8, max 25 epochs) — only
  the split and modality vary per run, for a fair comparison.
- **Checkpoints:** NOT retained (15 runs x ~90MB was not worth keeping;
  only metrics/confusion-matrices/predictions are saved, which is
  everything needed to reproduce the numbers below without needing to
  retrain — they are exactly what `evaluate.py`'s output already looks
  like, just called from inside the CV loop instead of standalone).
- **Status:** LAUNCHED in background at commit a4a9da4. **This entry is
  written before the run completes, per the "record before finishing"
  requirement — every fold's real result and the aggregate mean/std table
  will be appended below once the run actually finishes. Do not trust any
  per-fold or aggregate number under this heading that isn't there yet.**

### Per-fold results
PENDING — 15 runs (5 folds x {fundus, oct, fusion}), each saved to
`results/cv/<modality>/fold<k>/metrics.json` as it completes.

### Aggregate (mean ± std across 5 folds)
PENDING — will be computed by `cross_validate.py`'s own aggregation step
from the 15 real per-fold metrics files, written to `results/cv/summary.json`.

---

## smoke-test-1

- **Date:** 2026-09-17
- **Git commit:** bbda339 (before this session's training-pipeline commit)
- **Split:** dataset/splits/gamma_split_v1.json (seed=42)
- **Architecture:** GammaMultimodalModel, modality=fusion
- **Encoders:** resnet18 / resnet18 (fundus / OCT), ImageNet-pretrained
- **Image resolution:** 128x128
- **OCT slice count/sampling:** 4, evenly spaced from 256
- **Batch size:** 2
- **Optimizer:** AdamW, lr=1e-4
- **Loss:** CrossEntropyLoss (unweighted, smoke test only)
- **Augmentation:** train-mode fundus+OCT augmentation active
- **Epochs:** 1 batch only (not a training run)
- **Best validation epoch:** n/a
- **Test metrics:** n/a — this is a pipeline sanity check, not a trained model
- **Checkpoint path:** none saved
- **Notes:** Real forward+backward pass on real samples (ids 0013, 0061).
  loss=1.1517, peak CUDA memory 472MB. PASSED. Also verified
  modality=fundus (loss=0.953, 237MB) and modality=oct (loss=1.107, 242MB)
  smoke-test independently. Purpose was to catch shape/dtype/device bugs
  before spending real training time — it did catch one (see fusion_run1
  prerequisite note: gamma_loader relative-path bug, fixed before this run).

---

## fusion_run1

- **Date:** 2026-09-17
- **Git commit:** bbda339 (training/ pipeline added same session, not yet committed at run start)
- **Split:** dataset/splits/gamma_split_v1.json (seed=42) — train=70, val=16, test=14
- **Architecture:** GammaMultimodalModel, modality=fusion (fundus + OCT cross-attention)
- **Encoders:** resnet18 / resnet18 (fundus / OCT), ImageNet-pretrained
- **Image resolution:** 160x160
- **OCT slice count/sampling:** 8, evenly spaced from 256
- **Batch size:** 4
- **Optimizer:** AdamW, lr=1e-4, weight_decay=1e-4
- **LR schedule:** CosineAnnealingLR, T_max=25
- **Loss:** Focal loss (gamma=2.0), weighted by inverse class frequency from the real train split
- **Augmentation:** fundus flip/rotation/color-jitter; OCT brightness/contrast only
- **Modality dropout:** 0.15
- **Mixed precision:** enabled
- **Epochs (max):** 25, early stopping patience=8 on val loss
- **Command:**
  ```
  python train_multimodal.py --modality fusion --run-name fusion_run1 \
      --img-size 160 --oct-slices 8 --batch-size 4 --epochs 25 --lr 1e-4 \
      --focal-loss --amp --patience 8
  ```
- **Status:** COMPLETED. Early-stopped at epoch 17 (patience=8, no val_loss
  improvement since epoch 9).
- **Best validation epoch:** 9 (val_loss=0.7441, val_acc=0.688)
- **Test metrics** (from actual `evaluate.py` run on the 14-sample test split,
  copy-pasted verbatim from `results/fusion_run1/metrics.json`):
  - accuracy: 0.643
  - balanced_accuracy: 0.563
  - macro_f1: 0.567
  - per-class: normal P/R/F1=0.75/0.86/0.80 (n=7); early P/R/F1=0.50/0.50/0.50 (n=4); progressive P/R/F1=0.50/0.33/0.40 (n=3)
  - roc_auc_ovr_macro: 0.800
  - confusion matrix (rows=true, cols=pred [normal, early, progressive]):
    normal [6,1,0], early [1,2,1], progressive [1,1,1]
- **Checkpoint path:** training/checkpoints/fusion_run1.pt (gitignored — not committed, regenerate via the command above)
- **Notes:** First real training run on the actual GAMMA dataset in this
  project. Test split is only 14 samples — expect high variance in any
  single test metric. See the cross-run comparison note after oct_run1
  below: on this particular test split, fundus_run1 actually beat this
  fusion run, which fundus-only-helps-most is not what the architecture
  was built to demonstrate — flagged honestly, not smoothed over.

---

## fundus_run1

- **Date:** 2026-09-17
- **Git commit:** 7b9c7b8
- **Split:** dataset/splits/gamma_split_v1.json (seed=42) — same split as fusion_run1
- **Architecture:** GammaMultimodalModel, modality=fundus (single-modality baseline, same codebase)
- **Encoder:** resnet18, ImageNet-pretrained
- **Image resolution:** 160x160
- **OCT slice count/sampling:** n/a (unused in this modality)
- **Batch size:** 4
- **Optimizer:** AdamW, lr=1e-4, weight_decay=1e-4, CosineAnnealingLR T_max=25
- **Loss:** Focal loss (gamma=2.0), same class weights as fusion_run1
- **Augmentation:** fundus flip/rotation/color-jitter (same as fusion_run1's fundus branch)
- **Mixed precision:** enabled
- **Epochs (max):** 25, early stopping patience=8 — stopped at epoch 15
- **Command:**
  ```
  python train_multimodal.py --modality fundus --run-name fundus_run1 \
      --img-size 160 --oct-slices 8 --batch-size 4 --epochs 25 --lr 1e-4 \
      --focal-loss --amp --patience 8
  ```
- **Best validation epoch:** 7 (val_loss=0.9268, val_acc=0.750)
- **Test metrics** (from `results/fundus_run1/metrics.json`):
  - accuracy: 0.786
  - balanced_accuracy: 0.786
  - macro_f1: 0.748
  - per-class: normal P/R/F1=1.00/0.86/0.92 (n=7); early P/R/F1=0.67/0.50/0.57 (n=4); progressive P/R/F1=0.60/1.00/0.75 (n=3)
  - roc_auc_ovr_macro: 0.930
  - confusion matrix: normal [6,1,0], early [0,2,2], progressive [0,0,3]
- **Checkpoint path:** training/checkpoints/fundus_run1.pt (gitignored)
- **Notes:** Same split, hyperparameters, and loss as fusion_run1 — only the
  modality differs, for a fair comparison.

---

## oct_run1

- **Date:** 2026-09-17
- **Git commit:** 7b9c7b8
- **Split:** dataset/splits/gamma_split_v1.json (seed=42) — same split as fusion_run1
- **Architecture:** GammaMultimodalModel, modality=oct (single-modality baseline, same codebase)
- **Encoder:** resnet18, ImageNet-pretrained, shared across 8 sampled slices + attention pooling
- **Image resolution:** 160x160
- **OCT slice count/sampling:** 8, evenly spaced from 256
- **Batch size:** 4
- **Optimizer:** AdamW, lr=1e-4, weight_decay=1e-4, CosineAnnealingLR T_max=25
- **Loss:** Focal loss (gamma=2.0), same class weights as fusion_run1
- **Augmentation:** OCT brightness/contrast only (same as fusion_run1's OCT branch)
- **Mixed precision:** enabled
- **Epochs (max):** 25, early stopping patience=8 — stopped at epoch 23
- **Command:**
  ```
  python train_multimodal.py --modality oct --run-name oct_run1 \
      --img-size 160 --oct-slices 8 --batch-size 4 --epochs 25 --lr 1e-4 \
      --focal-loss --amp --patience 8
  ```
- **Best validation epoch:** 15 (val_loss=0.8831, val_acc=0.438)
- **Test metrics** (from `results/oct_run1/metrics.json`):
  - accuracy: 0.500
  - balanced_accuracy: 0.405
  - macro_f1: 0.378
  - per-class: normal P/R/F1=0.83/0.71/0.77 (n=7); early P/R/F1=0.29/0.50/0.36 (n=4); progressive P/R/F1=0.00/0.00/0.00 (n=3)
  - roc_auc_ovr_macro: 0.817
  - confusion matrix: normal [5,2,0], early [1,2,1], progressive [0,3,0]
- **Checkpoint path:** training/checkpoints/oct_run1.pt (gitignored)
- **Notes:** The OCT-only model never correctly predicted "progressive" on
  this 3-sample test slice (0/3 recall) — with only 3 progressive samples
  in the test set, that's one or two wrong predictions, not necessarily a
  real pattern.

---

### Honest cross-run comparison (fusion_run1 vs fundus_run1 vs oct_run1)

| Run | Test accuracy | Balanced accuracy | Macro F1 | ROC-AUC (OvR macro) |
|---|---|---|---|---|
| fundus only | **0.786** | **0.786** | **0.748** | **0.930** |
| fusion (fundus+OCT) | 0.643 | 0.563 | 0.567 | 0.800 |
| OCT only | 0.500 | 0.405 | 0.378 | 0.817 |

**On this specific 14-sample test split, fundus-only outperformed the
fusion model, and fusion outperformed OCT-only.** This is the opposite of
what a multimodal-fusion project sets out to demonstrate, and it is
reported exactly as measured — not smoothed over or hidden.

Do NOT treat this as "fusion doesn't work." With a 14-sample test set,
a difference of 2 correct predictions changes accuracy by ~14 percentage
points — the confidence intervals on all three of these numbers almost
certainly overlap heavily. Legitimate next steps before drawing any real
conclusion: (1) k-fold cross-validation instead of one fixed split, given
N=100 total, (2) multiple random seeds per configuration, (3) a paired
statistical test (e.g. McNemar's) on the same test samples across models
rather than comparing point accuracy. None of that has been done yet.
