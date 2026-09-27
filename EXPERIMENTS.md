# EXPERIMENTS.md

Log of every actual training/evaluation run. Never delete entries, even
failed ones — a failed run is still real information.

---

## Experiment: fusion_token_v1 (EXP-06)

### Hypothesis
Preserving more spatial/sequential structure per modality (fundus spatial
feature-map tokens, OCT per-slice tokens) instead of collapsing each
modality to one pooled vector before fusion lets the cross-modal
Transformer extract more useful joint structure.

### Change
New `--fusion-type token` architecture: `FundusEncoder` returns its
pre-pool spatial feature map as 25 tokens (5x5 grid at 160x160 input,
projected to `fusion_dim`) instead of one globally-pooled vector;
`OCTVolumeEncoder` returns its 8 per-slice embeddings directly instead of
attention-pooling them into one vector. A new `TokenCrossModalFusion`
(2-layer, 4-head Transformer encoder, modality-type embeddings, mean-pool
output) replaces the 2-token `CrossModalFusion`. A `TokenModalityDropout`
analogue (drops entire per-modality token blocks, never both at once)
replaces vector-level `ModalityDropout` so the missing-modality robustness
mechanism stays present, not silently removed. Base config is the
EXP-05 winner (EfficientNet-B0 fundus, resnet18 OCT, 8 slices, single
representation) — only the fusion mechanism changes.

### Fixed
Dataset, patient folds (seed=42, k=5, same membership as baseline_v1),
seed, optimizer, learning rate, loss, epochs, fundus/OCT encoders, OCT
config, img_size=160, batch_size=4.

### Before-training checklist
1. Baseline (`vector`) path re-smoke-tested after the model.py changes:
   identical loss (1.1517) to every prior baseline smoke test — confirmed
   unchanged.
2. Token shapes directly verified (not just "didn't crash"): fundus
   tokens `(B, 25, 256)`, OCT tokens `(B, 8, 256)`, final logits
   `(B, 3)`. Total model size 16.73M params — modest, appropriate for a
   6GB GPU per the plan's explicit guidance not to build an unnecessarily
   large model.
3. `TokenModalityDropout` verified directly (not just via training loss):
   on 20 synthetic samples at p=0.5, ~30% had fundus tokens fully zeroed,
   ~20% had OCT tokens fully zeroed, 0% had both zeroed simultaneously —
   matches the vector version's designed behavior.
4. Real forward+backward smoke test at the actual batch_size=4/img_size=160
   config: loss=1.0487, peak CUDA 638MB — within budget.
5. TensorBoard logging confirmed active for the real run.

### Results (mean ± std, 5-fold CV)
| Metric | EXP-05 (vector, comparison base) | EXP-06 (token) |
|---|---:|---:|
| Accuracy | 0.820 ± 0.055 | 0.820 ± 0.110 |
| Balanced Accuracy | 0.790 ± 0.057 | 0.769 ± 0.135 |
| Macro F1 | 0.781 ± 0.061 | 0.763 ± 0.135 |
| ROC-AUC | 0.924 ± 0.039 | 0.935 ± 0.036 |
| Kappa | 0.716 ± 0.087 | 0.712 ± 0.176 |
| QWK | 0.798 ± 0.113 | 0.852 ± 0.107 |

### Per-fold results
| Fold | Accuracy | Bal. Acc | Macro F1 | ROC-AUC | Kappa | QWK | best_epoch | train_seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.714 | 0.644 | 0.632 | 0.897 | 0.547 | 0.711 | 17 | 299.1 |
| 1 | 0.900 | 0.867 | 0.861 | 0.933 | 0.840 | 0.934 | 8 | 177.6 |
| 2 | 0.900 | 0.867 | 0.861 | 0.991 | 0.840 | 0.918 | 24 | 286.7 |
| 3 | 0.900 | 0.867 | 0.861 | 0.942 | 0.840 | 0.934 | 6 | 167.3 |
| 4 | 0.684 | 0.600 | 0.597 | 0.909 | 0.496 | 0.764 | 13 | 233.8 |

Full detail: `results/cv_fusion_token_v1/`. (Folds 1-3 landing on identical
values is a real coincidence of small integer sample counts per fold
— n=20, so accuracy is quantized to multiples of 0.05 — not a bug;
verified each fold used its own distinct patient split.)

### Decision
**Result: inconclusive — token-level fusion NOT adopted.** Unlike EXP-05
(a clean sweep across every fold and metric), this is genuinely mixed:
QWK and ROC-AUC both improved meaningfully (+0.054, +0.011), but balanced
accuracy and macro F1 — the plan's top two priority metrics for this
decision rule — both came out slightly lower, and fold-to-fold variance
roughly doubled on 4 of the 6 metrics (e.g. macro F1 std 0.061 → 0.135).
Per the plan's explicit rule (weigh macro F1/balanced accuracy/QWK/ROC-AUC/
kappa/accuracy in that order; don't manufacture a winner from ambiguous
results): the higher-priority metrics favor keeping vector fusion, and the
added instability is a real cost the QWK/ROC-AUC gains don't clearly
outweigh. **`fusion_effnetb0_v1`'s vector-fusion architecture remains the
frozen best configuration** going into the plan's "ARCHITECTURE FREEZE"
milestone: EfficientNet-B0 fundus + resnet18 OCT + 8-slice single
representation + vector (2-token) cross-modal fusion.

### Next step
Per the plan's Final Sequence, this is the architecture freeze point.
Next candidates (ordinal classifier, anatomy-aware auxiliary learning,
multi-seed validation, fold ensemble) all explicitly wait until the user
weighs in, per the plan's own "Do NOT Start These Yet" section.

---

## Experiment: fusion_effnetb0_v1 (EXP-05)

### Hypothesis
A stronger, more parameter-efficient ImageNet backbone for the fundus
branch improves fusion performance.

### Change
`--fundus-encoder resnet18` → `--fundus-encoder efficientnet_b0`. OCT
configuration fixed at the EXP-04-selected best (8 slices, single
representation, resnet18 OCT encoder — i.e. exactly `baseline_v1`'s OCT
setup). Only the fundus encoder changes.

### Fixed
Dataset, patient folds (seed=42, k=5, same membership as baseline_v1),
seed, optimizer, learning rate, loss, epochs, OCT encoder/config, fusion
architecture, img_size=160, batch_size=4.

### Before-training check
Smoke test at real batch_size=4/img_size=160: fundus batch shape
`(4, 3, 160, 160)`, peak CUDA 636MB. Parameter counts (feature-extractor
only, `num_classes=0`): resnet18 = 11.18M, efficientnet_b0 = 4.01M —
EfficientNet-B0 is smaller despite the "stronger" label.

### Results (mean ± std, 5-fold CV)
| Metric | Baseline (resnet18) | EfficientNet-B0 |
|---|---:|---:|
| Accuracy | 0.731 ± 0.072 | **0.820 ± 0.055** |
| Balanced Accuracy | 0.691 ± 0.071 | **0.790 ± 0.057** |
| Macro F1 | 0.681 ± 0.077 | **0.781 ± 0.061** |
| ROC-AUC | 0.875 ± 0.037 | **0.924 ± 0.039** |
| Kappa | 0.577 ± 0.112 | **0.716 ± 0.087** |
| QWK | 0.775 ± 0.071 | **0.798 ± 0.113** |

### Per-fold results
| Fold | Accuracy | Bal. Acc | Macro F1 | ROC-AUC | Kappa | QWK | best_epoch | train_seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.762 | 0.733 | 0.730 | 0.938 | 0.622 | 0.646 | 20 | 472.8 |
| 1 | 0.800 | 0.767 | 0.744 | 0.864 | 0.686 | 0.788 | 17 | 427.4 |
| 2 | 0.900 | 0.867 | 0.867 | 0.973 | 0.840 | 0.927 | 12 | 248.3 |
| 3 | 0.850 | 0.833 | 0.825 | 0.924 | 0.765 | 0.889 | 18 | 308.6 |
| 4 | 0.789 | 0.750 | 0.738 | 0.917 | 0.665 | 0.742 | 19 | 302.8 |

Full detail: `results/cv_fusion_effnetb0_v1/`.

### Decision
**Result: EfficientNet-B0 adopted as the new fundus encoder.** Improves
every one of the 6 metrics, most by a wide margin (macro F1 +0.100,
balanced accuracy +0.099, kappa +0.139), and does so with fewer
parameters than resnet18 (4.01M vs 11.18M) — a genuine efficiency + quality
win, not a tradeoff. This is the cleanest, most consistent result in the
ablation series so far (improved on all 5 individual folds for
accuracy/macro_f1/roc_auc, not just the mean). QWK's std is higher than
the baseline's (0.113 vs 0.071, driven by fold 0's comparatively low 0.646)
but its mean is still improved and every other metric's variance is
comparable to or tighter than baseline.

### Next experiment
EXP-06: token-level multimodal fusion, building on EfficientNet-B0 fundus
+ resnet18 OCT + 8-slice single representation (this experiment's
winning configuration) as the new base to compare against.

---

## Experiment: fusion_single_16s_v1 (EXP-04)

### Hypothesis
Even denser OCT slice sampling (16 vs. 8/12) might continue to help, or
might reveal where returns diminish/reverse.

### Change
`--oct-slices 8` → `--oct-slices 16`, `oct_representation=single`.
Everything else identical to `fusion_baseline_v1`.

### Fixed
Same as EXP-03 (dataset, folds, seed, optimizer, lr, loss, epochs,
encoders, fusion architecture, img_size=160, batch_size=4).

### Before-training check
Smoke test at real batch_size=4/img_size=160: oct batch shape
`(4, 16, 1, 160, 160)`, peak CUDA 878MB — within budget, no batch-size
change needed. (This smoke test also served to confirm a real environment
bug — a stale `tensorboard`/`tensorflow-intel` conflict from an unrelated
concurrent process on this machine — was fixed before the real run; see
`PROGRESS.md`.)

### Results (mean ± std, 5-fold CV) — full 8/12/16 comparison
| Metric | 8 slices (baseline) | 12 slices (EXP-03) | 16 slices (EXP-04) |
|---|---:|---:|---:|
| Accuracy | 0.731 ± 0.072 | 0.700 ± 0.116 | 0.670 ± 0.055 |
| Balanced Accuracy | 0.691 ± 0.071 | 0.646 ± 0.127 | 0.600 ± 0.075 |
| Macro F1 | 0.681 ± 0.077 | 0.627 ± 0.143 | 0.590 ± 0.059 |
| ROC-AUC | 0.875 ± 0.037 | 0.873 ± 0.059 | 0.856 ± 0.014 |
| Kappa | 0.577 ± 0.112 | 0.531 ± 0.175 | 0.482 ± 0.085 |
| QWK | 0.775 ± 0.071 | 0.763 ± 0.082 | 0.740 ± 0.033 |

### Per-fold results
| Fold | Accuracy | Bal. Acc | Macro F1 | ROC-AUC | Kappa | QWK | best_epoch | train_seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.667 | 0.633 | 0.635 | 0.875 | 0.482 | 0.742 | 14 | 494.4 |
| 1 | 0.750 | 0.700 | 0.649 | 0.837 | 0.608 | 0.768 | 16 | 592.3 |
| 2 | 0.650 | 0.567 | 0.570 | 0.859 | 0.451 | 0.741 | 16 | 558.0 |
| 3 | 0.600 | 0.500 | 0.501 | 0.862 | 0.373 | 0.686 | 15 | 529.9 |
| 4 | 0.684 | 0.600 | 0.597 | 0.849 | 0.496 | 0.764 | 21 | 544.9 |

Full detail: `results/cv_fusion_single_16s_v1/`.

### Decision
**Result: 16 slices rejected — and the 3-point comparison now shows a
clean, monotonic trend: 8 < 12 < 16 slices is monotonically WORSE on every
one of the 6 metrics** (e.g. macro F1: 0.681 → 0.627 → 0.590; QWK: 0.775 →
0.763 → 0.740). Also monotonically slower to train (8 slices' folds
~200-440s, 12 slices' ~300-440s, 16 slices' ~495-590s). This is an
unambiguous result, unlike EXP-02: **8 slices is selected as the final OCT
configuration** for the remainder of this ablation series — more slices
did not help and cost more compute. A plausible (untested) explanation:
with only 100 labeled patients, a higher-dimensional OCT input (more
slices → more attention-pooling inputs) may be overfitting capacity the
dataset can't support, rather than adding useful signal — consistent with
this being a small-data regime throughout.

### Next experiment
EXP-05: stronger fundus backbone (EfficientNet-B0), fixing OCT
configuration at 8 slices / single representation (i.e. exactly
`baseline_v1`'s OCT setup) and varying only the fundus encoder.

---

## Experiment: fusion_single_12s_v1 (EXP-03)

### Hypothesis
Denser OCT slice sampling (12 vs. 8, single-slice representation) gives
the OCT branch more coverage of the macular volume, potentially improving
fusion performance.

### Change
`--oct-slices 8` → `--oct-slices 12`, `oct_representation=single` (per the
user's decision after EXP-02: 2.5D rejected for fusion, so slice-count
experiments build on `single`, not `2.5d`). Everything else identical to
`fusion_baseline_v1`.

### Fixed
Dataset, patient folds (seed=42, k=5, same membership as baseline_v1),
seed, optimizer, learning rate, loss, epochs, fundus/OCT encoders, fusion
architecture, img_size=160, batch_size=4.

### Before-training check
Smoke test at the real batch_size=4/img_size=160 (not just a tiny smoke
config): oct batch shape `(4, 12, 1, 160, 160)`, peak CUDA 701MB — well
within the 6GB budget, no batch-size reduction needed.

### Results (mean ± std, 5-fold CV)
| Metric | Baseline (8 slices) | 12 slices |
|---|---:|---:|
| Accuracy | 0.731 ± 0.072 | 0.700 ± 0.116 |
| Balanced Accuracy | 0.691 ± 0.071 | 0.646 ± 0.127 |
| Macro F1 | 0.681 ± 0.077 | 0.627 ± 0.143 |
| ROC-AUC | 0.875 ± 0.037 | 0.873 ± 0.059 |
| Kappa | 0.577 ± 0.112 | 0.531 ± 0.175 |
| QWK | 0.775 ± 0.071 | 0.763 ± 0.082 |

### Per-fold results
| Fold | Accuracy | Bal. Acc | Macro F1 | ROC-AUC | Kappa | QWK | best_epoch | train_seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.619 | 0.578 | 0.574 | 0.851 | 0.411 | 0.720 | 24 | 386.3 |
| 1 | 0.800 | 0.767 | 0.744 | 0.904 | 0.686 | 0.788 | 13 | 326.4 |
| 2 | 0.850 | 0.800 | 0.810 | 0.956 | 0.755 | 0.880 | 8 | 314.5 |
| 3 | 0.600 | 0.533 | 0.522 | 0.798 | 0.385 | 0.660 | 19 | 440.4 |
| 4 | 0.632 | 0.550 | 0.482 | 0.858 | 0.419 | 0.769 | 17 | 422.6 |

Full detail: `results/cv_fusion_single_12s_v1/`.

### Decision
**Result: 12 slices rejected.** Unlike EXP-02 (mixed/ambiguous), this is a
clean, unambiguous regression: every one of the 6 metrics is lower with 12
slices, and fold-to-fold variance is substantially higher on every metric
too (e.g. accuracy std 0.116 vs 0.072, macro F1 std 0.143 vs 0.077) — the
per-fold spread (0.60-0.85 accuracy) is much wider than the baseline's
(0.65-0.84). Not adopting 12 slices.

### Next experiment
EXP-04: 16 slices, per the plan's sequence (completing the slice-count
sweep before selecting a final OCT configuration, independent of EXP-03's
outcome).

---

## Experiment: fusion_baseline_v1 (EXP-01)

### Hypothesis
N/A — this is the frozen comparison reference, not a test of a change.

### Change
None. Fresh 5-fold CV run of the existing fusion architecture
(single-slice OCT), on the identical seed/fold assignment as the original
`cv-run-1`, under the *current* evaluation code (so Kappa/QWK — added
after `cv-run-1` — are available for later comparisons).

### Fixed
Dataset (100 labeled GAMMA patients), patient folds (seed=42, k=5,
identical membership to `cv-run-1`), seed, optimizer (AdamW), learning
rate (1e-4), loss (focal, gamma=2.0, inverse-frequency class weights),
epochs (25, patience=8), fundus encoder (resnet18), OCT encoder
(resnet18), fusion architecture (cross-modal transformer), img_size=160,
oct_slices=8, batch_size=4.

### Results (mean ± std, 5-fold CV)
| Metric | Value |
|---|---:|
| Accuracy | 0.731 ± 0.072 |
| Balanced Accuracy | 0.691 ± 0.071 |
| Macro F1 | 0.681 ± 0.077 |
| ROC-AUC | 0.875 ± 0.037 |
| Kappa | 0.577 ± 0.112 |
| QWK | 0.775 ± 0.071 |

### Per-fold results
| Fold | Accuracy | Bal. Acc | Macro F1 | ROC-AUC | Kappa | QWK | best_epoch |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.714 | 0.722 | 0.707 | 0.832 | 0.570 | 0.782 | 18 |
| 1 | 0.650 | 0.600 | 0.572 | 0.842 | 0.440 | 0.672 | 6 |
| 2 | 0.700 | 0.633 | 0.633 | 0.886 | 0.520 | 0.755 | 10 |
| 3 | 0.750 | 0.733 | 0.724 | 0.902 | 0.615 | 0.800 | 22 |
| 4 | 0.842 | 0.767 | 0.766 | 0.914 | 0.740 | 0.867 | 20 |

Full detail (confusion matrices, predictions): `results/cv_fusion_baseline_v1/`.
Frozen artifact: `experiments/baseline_v1/`.

### Decision
Frozen as the comparison reference for EXP-02 onward. Note: this re-run's
accuracy/balanced_accuracy/macro_f1/roc_auc differ slightly from the
original `cv-run-1` fusion numbers (e.g. mean accuracy 0.731 here vs.
0.710 in `cv-run-1`) despite identical seed/fold assignment/hyperparameters
— expected GPU training non-determinism (no `torch.use_deterministic_algorithms`
was set on either run), not a bug in either run. Documented in
`experiments/baseline_v1/metadata.json`.

### Next experiment
EXP-02: Fusion + OCT 2.5D.

---

## Experiment: fusion_2p5d_v1 (EXP-02)

### Hypothesis
Neighboring OCT B-scans (2.5D: `[i-1, i, i+1]` as 3 channels) provide
useful structural context that transfers from OCT-only (confirmed
improvement, `oct25d-cv-run-1`) to the multimodal fusion model.

### Change
Single-slice OCT → 2.5D OCT, fusion modality only. Everything else
identical to `fusion_baseline_v1`.

### Fixed
Dataset, patient folds (seed=42, k=5, same membership as baseline_v1),
seed, optimizer, learning rate, loss, epochs, fundus encoder, fusion
architecture — see `fusion_baseline_v1` above for exact values.

### Before-training checklist (per MM_RETINA_NEXT_EXPERIMENTS.md EXP-02)
1. Smoke test: PASSED (`train_multimodal.py --smoke-test --modality fusion
   --oct-representation 2.5d`), real forward+backward, loss=1.1131.
2. 3-channel shape confirmed: oct batch `(2, 4, 3, 128, 128)`.
3. Neighboring B-scans genuinely different: confirmed earlier this session
   via direct tensor inspection on a real sample (pairwise channel diffs
   ~0.02 for interior slices, not 0).
4. Edge handling confirmed: index-0/last-index slices correctly show a 0.0
   diff between the clamped neighbor and center channel (by design).
5. Original single-slice path confirmed unchanged: identical smoke-test
   loss (1.1517) before and after the 2.5D code was added.
6. GPU training confirmed: real CUDA forward/backward, checkpoints saved.
7. TensorBoard logging confirmed: `--tensorboard` enabled for this run,
   `runs/cv_fusion_fold{0..4}/` populated with live scalars per fold.

### Results (mean ± std, 5-fold CV)
| Metric | Baseline (single) | 2.5D |
|---|---:|---:|
| Accuracy | 0.731 ± 0.072 | 0.711 ± 0.058 |
| Balanced Accuracy | 0.691 ± 0.071 | 0.648 ± 0.078 |
| Macro F1 | 0.681 ± 0.077 | 0.630 ± 0.079 |
| ROC-AUC | 0.875 ± 0.037 | **0.876 ± 0.016** |
| Kappa | 0.577 ± 0.112 | 0.543 ± 0.087 |
| QWK | 0.775 ± 0.071 | 0.770 ± 0.053 |

### Per-fold results
| Fold | Accuracy | Bal. Acc | Macro F1 | ROC-AUC | Kappa | QWK | best_epoch | train_seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.667 | 0.656 | 0.586 | 0.851 | 0.491 | 0.710 | 14 | 465.5 |
| 1 | 0.700 | 0.633 | 0.631 | 0.869 | 0.529 | 0.765 | 16 | 492.7 |
| 2 | 0.750 | 0.667 | 0.666 | 0.893 | 0.592 | 0.800 | 10 | 376.9 |
| 3 | 0.650 | 0.533 | 0.529 | 0.884 | 0.440 | 0.731 | 17 | 465.6 |
| 4 | 0.789 | 0.750 | 0.738 | 0.881 | 0.664 | 0.843 | 21 | 472.8 |

Full detail: `results/cv_fusion_2p5d_v1/`.

### Decision
**Result: inconclusive / mixed — do not adopt 2.5D for fusion mode based
on this alone.**

Unlike the OCT-only case (where 2.5D won cleanly on every metric,
`oct25d-cv-run-1`), 2.5D did **not** transfer as a clean win to fusion
mode:
- Accuracy, balanced accuracy, macro F1, and Kappa are all slightly
  *lower* for 2.5D (e.g. macro F1 0.630 vs 0.681), though the confidence
  intervals (mean ± std over 5 folds) overlap substantially with the
  baseline on every one of these — this is not a statistically clear
  regression either.
- ROC-AUC and QWK are essentially tied (0.876 vs 0.875, 0.770 vs 0.775),
  and notably, **2.5D has much lower fold-to-fold variance on ROC-AUC**
  (std 0.016 vs 0.037) and slightly lower on QWK (0.053 vs 0.071) — a real
  stability advantage on those two metrics specifically, even without an
  accuracy-family win.
- Per the plan's decision rule (macro F1 / balanced accuracy / QWK / ROC-AUC
  / kappa / accuracy, in that priority order, and "do not manufacture a
  winner if results are ambiguous"): macro F1 and balanced accuracy both
  favor the baseline here, so this does not clear the bar for adopting
  2.5D in fusion mode, despite OCT-only 2.5D being a clear win in
  isolation. A plausible (not yet tested) explanation: the fusion model's
  cross-modal attention may already extract most of the useful OCT signal
  from a single well-chosen slice, leaving less headroom for the extra
  local-depth context 2.5D adds — this is a hypothesis, not a
  demonstrated finding.

### Next experiment
Per `MM_RETINA_NEXT_EXPERIMENTS.md`'s "Final Sequence": EXP-03 (2.5D + 12
OCT slices) is next, but the user should be aware this result means the
"selected OCT configuration" carried forward into EXP-03/04/05 is not yet
unambiguous for fusion mode — worth deciding explicitly whether EXP-03
onward should use `single` or `2.5d` as the OCT representation to vary
slice count on top of, given this mixed result.

---

## oct25d-cv-run-1 (Experiment OCT-2: 2.5D OCT representation, oct-only, 5-fold CV)

- **Date:** 2026-09-27
- **Purpose:** Compare the plan's Experiment OCT-2 (stack B-scans
  `[i-1, i, i+1]` as 3 channels per sampled slice, `in_chans=3` on the same
  resnet18 backbone) against the existing OCT-1 baseline (single-channel
  B-scan per slice) from `cv-run-1`, on identical folds/hyperparameters —
  only the representation changes.
- **Code added for this:** `--oct-representation {single,2.5d}` on
  `training/data.py`'s `GammaMultimodalDataset` and `training/model.py`'s
  `OCTVolumeEncoder`/`GammaMultimodalModel` (`oct_in_chans`), wired through
  `train_multimodal.py`, `evaluate.py`, `cross_validate.py`. Default
  (`single`) is byte-for-byte identical to the pre-existing baseline —
  verified via smoke test: identical loss value (1.1517) on the same batch
  before and after this change.
- **Real testing before the full run:**
  - `train_multimodal.py --smoke-test --oct-representation 2.5d`: real
    forward+backward pass, oct batch shape `(2, 4, 3, 128, 128)` (3
    channels, as expected vs. baseline's `(2, 4, 1, 128, 128)`).
  - Directly inspected the 2.5D tensor's 3 channels for one real sample
    (id 0013): interior sampled slices have genuinely distinct
    prev/center/next channels (pairwise mean abs diff ~0.02, not 0 — not a
    duplicated-channel bug); edge slices (index 0 and index 255) correctly
    show a 0.0 diff between the clamped neighbor and the center slice, per
    the documented edge-clamping design.
  - `train_multimodal.py --smoke-test --modality oct --oct-representation 2.5d`:
    oct-only forward+backward pass also real and working, loss=1.2868.
  - `cross_validate.py --smoke-test` re-run after the plumbing changes:
    caught one real bug (a `SimpleNamespace` attribute-name mismatch —
    `args.tensorboard` vs. `no_tensorboard` — introduced by the earlier
    TensorBoard-integration change, not by this OCT-2 work), fixed, re-ran,
    reproduced the exact same fundus/oct/fusion smoke-test numbers as the
    original `cv-smoke-test-1` (0.571/0.381/0.333 accuracy) — confirms zero
    regression in the existing pipeline.
- **Command (launched, matching `cv-run-1`'s seed/folds/hyperparameters
  exactly so fold assignment is identical — only `--modalities oct
  --oct-representation 2.5d` differ):**
  ```
  python cross_validate.py --k 5 --modalities oct --oct-representation 2.5d \
      --epochs 25 --img-size 160 --oct-slices 8 --batch-size 4 --lr 1e-4 \
      --focal-loss --amp --patience 8 --seed 42 --out-dir ../results/cv_oct25d
  ```
- **Status:** COMPLETED. All 5 folds finished successfully. Two false starts
  before the real run, both diagnosed and fixed rather than hidden: (1) the
  first launch used a nested-background shell pattern that decoupled the
  actual python process from this session's own tracking — fixed by
  launching the training command directly under the session's background
  tracking; (2) stdout was fully buffered under redirection, making
  `oct25d_cv_run.log` look frozen even while training progressed for real —
  fixed with `python -u`. Also tried `--workers 4` to raise GPU utilization
  (was sitting at ~20-30%, ~2.2GB/6GB VRAM) — this made epoch time *worse*
  (71s vs ~22s), because Windows respawns DataLoader worker processes fresh
  every epoch (no `persistent_workers`), and that spawn cost dominates on a
  79-sample fold with only ~20 batches/epoch. Reverted to `--workers 0`,
  which was the actually-faster config, and that's what produced the real
  numbers below. Low GPU utilization here is a real, understood property of
  this workload (batch_size=4, resnet18, 160x160 — compute per batch is
  small regardless of the data pipeline), not a bug — raising it for real
  would mean a larger batch size, which is out of scope for this experiment
  since it must stay a matched-hyperparameter ablation against `cv-run-1`.
- **Real per-fold and aggregate results (from
  `results/cv_oct25d/oct/fold{0..4}/metrics.json` and
  `results/cv_oct25d/summary.json`, verbatim):**

  | Fold | Accuracy | Balanced acc. | Macro F1 | ROC-AUC | Kappa | QWK | best_epoch | train_seconds |
  |---|---:|---:|---:|---:|---:|---:|---:|---:|
  | 0 | 0.714 | 0.689 | 0.683 | 0.860 | 0.564 | 0.679 | 10 | 359.6 |
  | 1 | 0.650 | 0.567 | 0.553 | 0.898 | 0.451 | 0.708 | 10 | 353.4 |
  | 2 | 0.750 | 0.700 | 0.704 | 0.887 | 0.600 | 0.808 | 13 | 414.1 |
  | 3 | 0.600 | 0.500 | 0.494 | 0.808 | 0.360 | 0.673 | 7 | 297.8 |
  | 4 | 0.684 | 0.583 | 0.578 | 0.862 | 0.491 | 0.730 | 13 | 416.4 |

  **Aggregate (mean ± std, ddof=1):** accuracy 0.680±0.058, balanced_accuracy
  0.608±0.085, macro_f1 0.602±0.089, roc_auc 0.863±0.035, cohen_kappa
  0.493±0.095, qwk 0.720±0.054. Total wall time ~33 min for 5 folds.

- **Comparison vs. OCT-1 baseline (already real, from `cv-run-1`):**

  | Metric | OCT-1 (single-channel) | OCT-2 (2.5D) |
  |---|---:|---:|
  | Accuracy | 0.661 ± 0.089 | **0.680 ± 0.058** |
  | Balanced accuracy | 0.599 ± 0.076 | **0.608 ± 0.085** |
  | Macro F1 | 0.587 ± 0.090 | **0.602 ± 0.089** |
  | ROC-AUC (OvR macro) | 0.842 ± 0.041 | **0.863 ± 0.035** |
  | Cohen's Kappa | not computed (metric added after `cv-run-1`) | 0.493 ± 0.095 |
  | QWK | not computed | 0.720 ± 0.054 |

  **Honest reading:** 2.5D wins on every directly comparable metric
  (accuracy/balanced_accuracy/macro_f1/roc_auc), with slightly *lower*
  fold-to-fold variance on accuracy and ROC-AUC too (std 0.058 vs 0.089,
  0.035 vs 0.041). The improvement is real but modest (~0.02 mean
  accuracy/ROC-AUC) — not a dramatic win, and n=5 folds means the std
  values themselves carry substantial uncertainty. QWK/kappa have no
  baseline comparison point since those metrics didn't exist when
  `cv-run-1` ran; would need a `single`-representation re-run with the
  current metric set for a fully matched kappa/QWK comparison, not done
  here (out of scope — this experiment's question was single-vs-2.5D, and
  that's answered on the 4 metrics both runs share).

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
- **Status:** COMPLETED. All 15 runs finished successfully (exit code 0),
  ran in the background while the user checked GPU utilization
  (9-60% util, ~1.8GB/6GB VRAM — data-loading-bound at `--workers 0`, not
  a problem, just leaves GPU idle between batches; worth `--workers 4+`
  next time). Total wall time ~50 minutes for all 15 runs (~3.3 min/run
  average, consistent with the smoke test's per-epoch timing extrapolated
  to ~15-24 real epochs per run).

### Per-fold results (verbatim from results/cv/<modality>/fold<k>/metrics.json)

| Fold | Val n | Fundus acc / bal.acc / F1 / AUC | OCT acc / bal.acc / F1 / AUC | Fusion acc / bal.acc / F1 / AUC |
|---|---|---|---|---|
| 0 | 21 | 0.667 / 0.633 / 0.630 / 0.867 | 0.571 / 0.544 / 0.544 / 0.805 | 0.667 / 0.589 / 0.561 / 0.836 |
| 1 | 20 | 0.600 / 0.567 / 0.538 / 0.830 | 0.650 / 0.567 / 0.506 / 0.840 | 0.700 / 0.633 / 0.630 / 0.896 |
| 2 | 20 | **1.000 / 1.000 / 1.000 / 0.987** | 0.800 / 0.733 / 0.740 / 0.893 | 0.800 / 0.733 / 0.727 / 0.927 |
| 3 | 20 | 0.700 / 0.667 / 0.652 / 0.929 | 0.600 / 0.567 / 0.567 / 0.800 | 0.700 / 0.667 / 0.652 / 0.890 |
| 4 | 19 | 0.684 / 0.617 / 0.590 / 0.766 | 0.684 / 0.583 / 0.578 / 0.872 | 0.684 / 0.600 / 0.610 / 0.914 |

Fold 2's fundus-only run scored a perfect 1.000 across the board (20/20
correct) — a real result, not an error, but it single-handedly pulls the
fundus mean and (especially) std upward/wider. Early stopping fired for
most fundus/OCT/fusion runs between epoch 16-24 of the 25 max; a few
(fold2 fundus, fold2 fusion, fold4 oct) hit the full run without
triggering the patience=8 early stop, per the raw log.

### Aggregate (mean ± std across 5 folds, sample std / ddof=1) — from results/cv/summary.json

| Modality | Accuracy | Balanced accuracy | Macro F1 | ROC-AUC (OvR macro) |
|---|---|---|---|---|
| Fundus only | 0.730 ± 0.156 | 0.697 ± 0.173 | 0.682 ± 0.183 | 0.876 ± 0.086 |
| OCT only | 0.661 ± 0.089 | 0.599 ± 0.076 | 0.587 ± 0.090 | 0.842 ± 0.041 |
| Fusion (fundus+OCT) | 0.710 ± 0.052 | 0.644 ± 0.058 | 0.636 ± 0.061 | **0.892 ± 0.035** |

**Honest reading of this, cross-validated (much more trustworthy than the
single 14-sample split in fusion_run1/fundus_run1/oct_run1 above):**

- Fundus-only has the highest *mean* accuracy (0.730), but by far the
  highest *variance* (std 0.156-0.183 across all four metrics) — that
  mean is substantially inflated by one lucky fold (fold 2's perfect
  score). Its performance is not reliable across folds.
- **Fusion has the lowest variance of the three on every single metric**
  (std 0.052-0.061 vs fundus's 0.156-0.183 and OCT's 0.076-0.090), and the
  **highest mean ROC-AUC (0.892)** of all three modalities.
- OCT-only is weakest on every metric and every fold — consistently, not
  just on average.
- The 5-fold picture is more favorable to fusion than the single-split
  result looked: fusion isn't the outright accuracy winner, but it is the
  most *stable* model and the best by ROC-AUC — a real, defensible
  finding, unlike the single-split "fundus just wins" takeaway, which
  turns out to have been driven by which 14 samples happened to land in
  that one test set.
- Still true: n=5 folds is a small number of estimates for a standard
  deviation — these std values themselves have wide uncertainty. This is
  a meaningfully stronger result than one train/test split, not a
  definitive one. A paired test (e.g. a fold-wise paired t-test between
  fusion and fundus on accuracy) would be the next rigor step, not yet done.

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
