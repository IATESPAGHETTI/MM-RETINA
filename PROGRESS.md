# PROGRESS.md

Persistent progress log for the MM-RETINA / GAMMA multimodal glaucoma
grading project. Update this BEFORE finishing each substantial task. Never
delete history — append new entries above older ones.

---

## 2026-09-17 01:47 (5-fold cross-validation: COMPLETED, real results)

### Completed
All 15 CV runs (5 folds x {fundus, oct, fusion}) finished successfully,
~50 minutes total wall time. Aggregated into `results/cv/summary.json`.
Full per-fold table and aggregate mean±std written to EXPERIMENTS.md
under `cv-run-1` — nothing here is estimated, all copied from real
metrics.json / summary.json files.

### Current status — real, cross-validated results
| Modality | Accuracy | Balanced accuracy | Macro F1 | ROC-AUC |
|---|---|---|---|---|
| Fundus only | 0.730 ± 0.156 | 0.697 ± 0.173 | 0.682 ± 0.183 | 0.876 ± 0.086 |
| OCT only | 0.661 ± 0.089 | 0.599 ± 0.076 | 0.587 ± 0.090 | 0.842 ± 0.041 |
| Fusion | 0.710 ± 0.052 | 0.644 ± 0.058 | 0.636 ± 0.061 | **0.892 ± 0.035** |

This changes the picture from the single-split result. Fundus's higher
mean accuracy is driven almost entirely by one fold where it scored a
perfect 1.000 (real, not an error) — its variance across folds (std up to
0.183) is far higher than fusion's (std 0.052-0.061 on every metric).
Fusion has the highest mean ROC-AUC and is clearly the most consistent
model fold-to-fold. This is a genuinely more defensible finding than
"fundus beats fusion" from the single 14-sample test split.

### Files changed
- `EXPERIMENTS.md` — `cv-run-1` completed with full per-fold table +
  aggregate + honest interpretation.
- `PROGRESS.md` — this entry.
- `results/cv/` — 15 real fold results (metrics.json/confusion_matrix.csv/
  predictions.csv each) + summary.json. Not yet committed as of this
  entry — see Next action.
- Website: **still not touched**, per instruction. A decision on whether/
  how to reflect the CV numbers (vs. the current single-split numbers
  already on `/results`) is the user's call, not made unilaterally here.

### Experiments
`cv-run-1` — COMPLETED. See EXPERIMENTS.md for full detail.

### Results
Real, tabulated above and in EXPERIMENTS.md. All 15 individual fold
results are on disk under `results/cv/` for inspection.

### Problems / blockers
None. All 15 runs completed with exit code 0, no crashes, no missing
metrics. GPU was underutilized during the run (9-60%, ~1.8/6GB) because
`--workers 0` makes data loading synchronous — noted as a real
inefficiency for next time (`--workers 4+`), not a correctness problem.

### Next action
1. Commit `results/cv/` (15 fold results + summary.json) and the
   EXPERIMENTS.md/PROGRESS.md updates.
2. Ask the user whether to update the website's `/results` page to show
   the cross-validated numbers (mean±std, 5 folds) instead of / alongside
   the single-split numbers currently there — this is a presentation
   decision, not something to change without asking, per "do not modify
   website metrics until CV results are actually generated" (they now
   are, but that instruction didn't authorize an unprompted website edit).
3. If pursuing further rigor: a paired statistical test (e.g. fold-wise
   paired t-test) between fusion and fundus-only on accuracy, since eyeballing
   overlapping std ranges isn't a real significance test.

---

## 2026-09-17 01:15 (5-fold cross-validation: implemented, smoke-tested, launched)

### Completed
- Read PROGRESS.md and EXPERIMENTS.md first, per the working-brief
  requirement, before touching anything.
- Built `training/cross_validate.py`: patient-level, grade-stratified
  5-fold CV. Deliberately reuses the existing, unmodified
  `train_multimodal.run_training`, `evaluate.run_evaluation`,
  `data.GammaMultimodalDataset`, and `model.GammaMultimodalModel` rather
  than reimplementing training/eval logic — no changes were made to any
  of those files.
  - Folds: patients round-robin-assigned per grade group after a seeded
    shuffle (seed=42), so class balance is similar across folds and every
    patient lands in exactly one fold.
  - Per fold, writes a `dataset/splits/cv/fold{k}.json` in the same schema
    `split_gamma.py` already uses, and hard-asserts zero patient overlap
    between that fold's train and val sets before any training touches it.
  - Runs fundus/OCT/fusion for every fold with matched hyperparameters,
    saves per-fold metrics.json/confusion_matrix.csv/predictions.csv under
    `results/cv/<modality>/fold<k>/`, then aggregates mean+std (sample std,
    ddof=1) across folds into `results/cv/summary.json`.
- **Ran the required smoke test before launching all folds** (real fold
  construction + 1 real epoch of train+eval for all 3 modalities on real
  data, tiny image size) — PASSED, see EXPERIMENTS.md `cv-smoke-test-1`.
  Deleted the smoke-test's split file and checkpoints afterward.
- Launched the real 5-fold x 3-modality run (15 real training jobs) in the
  background with the same hyperparameters as the earlier single-split
  runs (img_size=160, oct_slices=8, batch_size=4, epochs=25 w/ early
  stopping patience=8, focal loss, AMP).

### Current status
CV run is IN PROGRESS at the time of this entry. Do not trust any CV
number until a later PROGRESS.md/EXPERIMENTS.md entry explicitly says the
run completed — see EXPERIMENTS.md `cv-run-1` for the live/placeholder
status.

### Files changed
- `training/cross_validate.py` (new)
- `EXPERIMENTS.md` — added `cv-smoke-test-1` (complete) and `cv-run-1`
  (launched, pending real numbers)
- `PROGRESS.md` — this entry
- Website: **not touched**, per the explicit instruction not to modify
  website metrics until CV results actually exist.

### Experiments
`cv-smoke-test-1` — COMPLETED (sanity check only, not a performance result).
`cv-run-1` — LAUNCHED, in progress.

### Results
None yet for the real CV run. `cv-smoke-test-1`'s numbers are explicitly
not results — see EXPERIMENTS.md for why.

### Problems / blockers
None. The smoke test caught no new bugs, since this script's core
train/eval logic is the already-debugged code from the single-split
pipeline.

### Next action
1. Wait for `cv-run-1` to actually finish (15 runs — expect this to take
   a while; do not estimate a number here, check back on the actual
   process).
2. Copy the real per-fold and aggregate numbers from
   `results/cv/summary.json` into EXPERIMENTS.md and this file — verbatim,
   not rounded/adjusted.
3. Only then, decide with the user whether/how to reflect the
   cross-validated (rather than single-split) numbers on the website.

---

## 2026-09-17 00:20 (first real experiments completed)

### Completed
- `fusion_run1` training run finished (early-stopped epoch 17, best epoch 9).
- Ran the two required ablation baselines with matched hyperparameters/split:
  `fundus_run1` (early-stopped epoch 15, best epoch 7) and `oct_run1`
  (early-stopped epoch 23, best epoch 15).
- Ran `evaluate.py` for real against all three checkpoints on the 14-sample
  TEST split (never touched during training/val). Wrote
  `results/{fusion,fundus,oct}_run1/{metrics.json,confusion_matrix.csv,predictions.csv}`.

### Current status — real results, reported honestly
| Run | Test accuracy | Balanced accuracy | Macro F1 | ROC-AUC |
|---|---|---|---|---|
| fundus only | 0.786 | 0.786 | 0.748 | 0.930 |
| fusion | 0.643 | 0.563 | 0.567 | 0.800 |
| OCT only | 0.500 | 0.405 | 0.378 | 0.817 |

**Fundus-only beat the fusion model on this run/split.** Full numbers,
confusion matrices, and an explicit "don't over-read this" caveat are in
EXPERIMENTS.md. Reasons this is not a final verdict: 14-sample test set
(huge variance per prediction), single split (no cross-validation yet),
single seed, no statistical test between models. The honest scientific
takeaway right now is "the pipeline works and produces real, reproducible
numbers" — not "single-modality beats fusion" or vice versa.

### Files changed
- `EXPERIMENTS.md` — added real completed entries for fusion_run1,
  fundus_run1, oct_run1, plus a cross-run comparison table.
- `results/fusion_run1/`, `results/fundus_run1/`, `results/oct_run1/` —
  new, real, committed (metrics.json/confusion_matrix.csv/predictions.csv
  only — checkpoints themselves stay local/gitignored).
- `website/src/lib/content.ts`, `website/src/components/ResultsPreview.tsx`,
  `website/src/components/AblationTable.tsx` — replaced demo/placeholder
  numbers with these real results, with an explicit "n=14, preliminary"
  label — see the website integration note below.

### Experiments
fusion_run1, fundus_run1, oct_run1 — all COMPLETED, see EXPERIMENTS.md.

### Results
Real, as tabulated above. Not fabricated, not rounded up, not spun.

### Problems / blockers
None blocking. The main open methodological gap is statistical rigor
(single split, N=14 test) — noted, not hidden, not yet fixed.

### Next action
1. If pursuing this further: implement k-fold cross-validation across the
   100 patients so results aren't a single 14-sample roll of the dice.
2. Try a stronger/larger encoder or more OCT slices now that VRAM headroom
   is confirmed large (peak usage was under 1GB of the 6GB budget in the
   smoke test at a smaller config — these runs likely have similar
   headroom; a real run could afford more slices/higher resolution).
3. Grad-CAM/attribution work (brief's "Explainability" section) — not
   started yet.
4. `/demo` page still has no real inference backend — still intentionally
   inert, per its own on-page disclaimer.

---

## 2026-09-17 00:10 (session start: real training pipeline)

### Completed
- Inspected existing state: `dataset/gamma_manifest.json` (100 samples),
  `dataset/gamma_loader.py`, `dataset/gamma_audit.py` — all sound, per
  earlier audit (100/100 samples, 100 unique patients, 256 B-scans each,
  no missing/duplicate files, class distribution 50 normal/26 early/24
  progressive).
- **Fixed a real bug found during this work**: `gamma_loader.py` stored
  `fundus_path`/`oct_dir` as paths relative to whatever directory the
  loader was invoked from, so the manifest broke as soon as a script in a
  different directory (`training/`) tried to read it. Changed to
  `.resolve()` so the manifest always stores absolute paths. Regenerated
  `dataset/gamma_manifest.json` with the fix.
- Built `training/split_gamma.py`: deterministic (seed=42), patient-level,
  stratified-by-grade 70/15/15 split. Verifies zero patient leakage across
  splits as a hard assertion, not just a log line. Wrote
  `dataset/splits/gamma_split_v1.json` (includes the git commit the split
  was generated at, for reproducibility).
  - Result: train=70 (35 normal/18 early/17 progressive), val=16 (8/4/4),
    test=14 (7/4/3).
- Built the real multimodal pipeline:
  - `training/data.py` — `GammaMultimodalDataset`: loads real fundus JPEG
    + a configurable number of evenly-spaced real B-scan JPEGs per sample
    (default 8 of 256, to fit 6GB VRAM). Fundus augmentation: flip,
    small rotation, color jitter. OCT augmentation: intensity-domain only
    (brightness/contrast) — no flips/rotation, since B-scans have a fixed
    anatomical orientation that geometric augmentation would violate.
  - `training/model.py` — `GammaMultimodalModel`: timm-backed fundus
    encoder + shared per-slice OCT encoder with learned attention pooling
    over slices + `CrossModalFusion` (real transformer cross-attention
    over a [fundus, OCT] token pair, not self-attention relabeled) +
    classifier head. `--modality {fusion,fundus,oct}` flag swaps in
    single-modality baselines from the same codebase for a fair ablation.
    `ModalityDropout` zeroes a whole modality token (not scalars) at train
    time for missing-modality robustness.
  - `training/losses.py` — focal loss + inverse-frequency class weights
    computed from the real train-split counts (not hand-picked).
  - `training/train_multimodal.py` — full training loop: AdamW, cosine LR
    schedule, early stopping on val loss, checkpointing best-val, AMP,
    configurable img size/slice count/batch size, prints GPU+config+a VRAM
    warning before running.
  - `training/evaluate.py` — loads a checkpoint (refuses to run without
    one — see "Research integrity" below) and computes accuracy, balanced
    accuracy, macro F1, per-class precision/recall/support, confusion
    matrix, and one-vs-rest macro ROC-AUC on the TEST split only. Writes
    `results/<run>/metrics.json`, `confusion_matrix.csv`, `predictions.csv`.

### Real smoke test (ACTUALLY RUN, not simulated)
Environment: NVIDIA GeForce RTX 3060 Laptop GPU (6.0GB), PyTorch 2.5.1+cu121,
CUDA available and used.

```
python train_multimodal.py --smoke-test --oct-slices 4 --img-size 128 --smoke-batch-size 2
```
- Loaded 2 real train-split samples (ids 0013, 0061).
- fundus batch shape (2,3,128,128), oct batch shape (2,4,1,128,128) — as
  expected for batch=2, 4 sampled slices, 1 channel.
- Real forward + backward pass completed: loss=1.1517 (sane — near ln(3)=
  1.099 for an untrained 3-class head), 148 parameter tensors received
  gradients, max grad norm 14.0, peak CUDA memory 472MB (well under 6GB).
- Also smoke-tested `--modality fundus` (loss=0.953, 237MB peak) and
  `--modality oct` (loss=1.107, 242MB peak) — both ablation code paths
  work.

This confirms the pipeline is real and functional. It is NOT a trained
model and these loss values say nothing about eventual performance.

### Current status
A real training run was launched after the smoke test passed:
```
python train_multimodal.py --modality fusion --run-name fusion_run1 \
    --img-size 160 --oct-slices 8 --batch-size 4 --epochs 25 --lr 1e-4 \
    --focal-loss --amp --patience 8
```
Status of this run and its actual results: **see the next PROGRESS.md
entry and EXPERIMENTS.md — do not trust any number here that isn't in
those places with a timestamp after this one.**

### Files changed
- `dataset/gamma_loader.py` (path-resolution fix)
- `dataset/gamma_manifest.json` (regenerated)
- `dataset/splits/gamma_split_v1.json` (new)
- `training/split_gamma.py`, `training/data.py`, `training/model.py`,
  `training/losses.py`, `training/train_multimodal.py`,
  `training/evaluate.py` (new)
- `PROGRESS.md`, `EXPERIMENTS.md` (new)

### Experiments
See EXPERIMENTS.md for `fusion_run1`.

### Results
None yet with statistical meaning — see EXPERIMENTS.md for the real
numbers once `fusion_run1` finishes. **Known methodological concern**:
the test split is only 14 samples. Any single accuracy/F1 number from it
will have wide variance — treat one run's test metrics as a data point,
not a verdict, and prefer looking at the val-loss curve and, eventually,
cross-validation or repeated splits before drawing conclusions.

### Problems / blockers
- None blocking. The dataset-relative-path bug above is fixed.
- TensorFlow is not installed in this environment (only used by the older
  `Adv_prj4/` Keras architecture sketch, which was never actually run
  against real data). This new `training/` pipeline uses PyTorch instead,
  since that's what's actually installed with working CUDA here.

### Next action
1. Read back `fusion_run1`'s actual training log / EXPERIMENTS.md entry.
2. Run `evaluate.py` against its checkpoint on the test split.
3. Run the `fundus`-only and `oct`-only ablations with the same split/
   epochs/hyperparameters for a fair comparison.
4. Only after all three have real test-set metrics: fill in the website's
   `/results` ablation table — and only with real numbers, never before.
