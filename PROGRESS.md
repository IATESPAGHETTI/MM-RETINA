# PROGRESS.md

Persistent progress log for the MM-RETINA / GAMMA multimodal glaucoma
grading project. Update this BEFORE finishing each substantial task. Never
delete history — append new entries above older ones.

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
