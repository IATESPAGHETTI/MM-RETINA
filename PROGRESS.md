# PROGRESS.md

Persistent progress log for the MM-RETINA / GAMMA multimodal glaucoma
grading project. Update this BEFORE finishing each substantial task. Never
delete history — append new entries above older ones.

---

## 2026-09-27 (EXP-06 implemented, run, and recorded — architecture freeze point reached)

### Completed
Implemented token-level multimodal fusion (`--fusion-type token`) in
`model.py`/`train_multimodal.py`/`evaluate.py`/`cross_validate.py`:
`FundusEncoder`/`OCTVolumeEncoder` gained a `return_tokens` mode (spatial
feature-map tokens / per-slice tokens instead of one pooled vector), new
`TokenCrossModalFusion` (small 2-layer Transformer) and
`TokenModalityDropout` modules. Default (`vector`) path re-verified
byte-identical to every prior baseline smoke test. Directly verified token
shapes (25 fundus + 8 OCT tokens) and modality-dropout behavior on
synthetic data before running anything real, per the project's own
smoke-test standard.

Ran the real 5-fold CV comparison against `fusion_effnetb0_v1` (EXP-05,
the current best config). Result: **inconclusive, not adopted** — QWK/
ROC-AUC improved, but macro F1/balanced accuracy (higher decision-rule
priority per the plan) both came out slightly lower, and fold-to-fold
variance roughly doubled on most metrics. Full numbers and reasoning in
`EXPERIMENTS.md` → `fusion_token_v1`.

### Current best frozen architecture (per the plan's "ARCHITECTURE FREEZE"
milestone)
Fusion model: EfficientNet-B0 fundus encoder + resnet18 OCT encoder + 8
OCT slices (single/non-2.5D representation) + vector (2-token)
cross-modal fusion. Real 5-fold CV: accuracy 0.820±0.055, balanced_accuracy
0.790±0.057, macro_f1 0.781±0.061, roc_auc 0.924±0.039, kappa 0.716±0.087,
qwk 0.798±0.113 (`results/cv_fusion_effnetb0_v1/`).

### Files changed
`training/model.py`, `training/train_multimodal.py`,
`training/evaluate.py`, `training/cross_validate.py`, `EXPERIMENTS.md`,
`PROGRESS.md`. `results/cv_fusion_token_v1/` (new, real, 5 folds +
summary.json).

### Next action
This is the plan's explicit architecture-freeze checkpoint. The next
candidates in the plan's Final Sequence (ordinal classifier, anatomy-aware
auxiliary learning, multi-seed validation, fold ensemble) are all
explicitly gated on the user's go-ahead per the plan's own "Do NOT Start
These Yet" section — not started without it.

---

## 2026-09-27 (EXP-04/EXP-05 recorded — OCT slices settled, fundus backbone win)

### Completed
- EXP-04 (16 slices) recorded: monotonic regression vs. 8/12 slices on
  every metric. **Selected 8 slices + single representation** as the final
  OCT configuration — clean, unambiguous, no tie-breaking needed.
- EXP-05 (EfficientNet-B0 fundus encoder, OCT config fixed at the EXP-04
  winner) recorded: **clear win on every metric** (accuracy 0.731→0.820,
  macro F1 0.681→0.781, kappa 0.577→0.716, all improved on essentially
  every individual fold, not just the mean), with fewer parameters than
  resnet18 (4.01M vs 11.18M). Adopted as the new fundus encoder. This is
  the strongest, least ambiguous result in the whole series so far.

### Next action
EXP-06: token-level multimodal fusion. Unlike EXP-02..EXP-05 (CLI-flag
sweeps over the existing architecture), this requires new model code —
spatial fundus feature tokens instead of one pooled vector, OCT per-slice
tokens instead of the attention-pooled single vector, and a cross-modal
transformer over the concatenated token sequence. Building on the
EXP-05-winning config (EfficientNet-B0 fundus + resnet18 OCT + 8-slice
single) as the new comparison base. Will implement behind a new
`fusion_type` flag so the existing (winning) vector-fusion path stays
completely unchanged/available, smoke-test thoroughly per the project's
own standing rule (real shapes, real forward/backward, VRAM check) before
any real training run.

---

## 2026-09-27 (EXP-03 recorded, environment break found+fixed, EXP-04 launched)

Continuing the plan autonomously. EXP-03 (12 slices) finished: a clean,
unambiguous regression vs. `baseline_v1` on every one of the 6 metrics,
with substantially higher fold-to-fold variance too (accuracy std 0.116 vs
0.072). Not adopted. Full numbers in `EXPERIMENTS.md`.

### Real environment bug found and fixed (not caused by this session's own
work, but blocking it)
Before launching EXP-04 (16 slices), the pre-training smoke test failed:
`from torch.utils.tensorboard import SummaryWriter` crashed with
`AttributeError: module 'numpy' has no attribute 'bool8'`. Root cause,
traced step by step rather than guessed at:
1. `tensorboard` had been silently downgraded from 2.21.0 (installed
   earlier this session) to 2.10.1 by something external to this session —
   `pip show tensorflow-intel` showed a `tensorflow-intel==2.10.0` package
   present that requires `tensorboard<2.11`, and its dist-info timestamps
   matched almost exactly when the failure first appeared. This session
   never installed tensorflow; it must have come from something else
   running against the same global Python environment.
2. Reinstalling `tensorboard>=2.16` fixed the numpy issue but exposed a
   second, real problem: `tensorflow-intel` itself doesn't even import
   standalone anymore (`TypeError: Descriptors cannot be created
   directly` — a protobuf version too new for that old TF build).
   Verified with a bare `import tensorflow` in isolation before touching
   anything, confirming it was already completely unusable by anyone on
   this machine, not something this session was breaking.
3. Fix: uninstalled `tensorflow-intel` (confirmed already-broken,
   confirmed not used anywhere in this PyTorch-only project — consistent
   with the original session's note that TensorFlow "is not installed" /
   only relevant to the never-run `Adv_prj4/` Keras sketch). Re-verified
   `torch.utils.tensorboard` imports cleanly afterward, then re-ran the
   16-slice smoke test for real (878MB peak CUDA, well within budget).
4. Launched EXP-04 (16 slices) for real once the environment was
   confirmed healthy again.

### Next action
Wait for EXP-04 to finish, record it, then select the best OCT slice
count for fusion (8 vs 12 vs 16) before EXP-05.

---

## 2026-09-27 (EXP-01 + EXP-02 per MM_RETINA_NEXT_EXPERIMENTS.md)

Following the new execution plan the user provided: freeze a clean fusion
baseline (EXP-01), then test whether OCT-2.5D's clear win in oct-only mode
transfers to the full fusion model (EXP-02). Stopped after EXP-02, per the
plan's explicit "STOP HERE" instruction.

### Completed
1. **EXP-01**: froze `experiments/baseline_v1/` — a fresh 5-fold fusion
   (single-slice OCT) CV run, same seed/folds/hyperparameters as the
   original `cv-run-1`, but under the current evaluation code so Kappa/QWK
   are available (they didn't exist when `cv-run-1` ran). Result: accuracy
   0.731±0.072, balanced_accuracy 0.691±0.071, macro_f1 0.681±0.077,
   roc_auc 0.875±0.037, kappa 0.577±0.112, qwk 0.775±0.071. Noted (not
   hidden) that these numbers differ slightly from `cv-run-1`'s original
   fusion result despite the identical seed — expected GPU
   non-determinism, documented in `experiments/baseline_v1/metadata.json`.
2. **EXP-02**: ran the pre-training checklist from the plan (smoke test,
   3-channel shape, neighbor-slice distinctness, edge-clamp behavior,
   single-slice-path-unchanged, GPU/TensorBoard confirmation), then the
   real 5-fold fusion+2.5D CV run on identical folds.

### Real result — and it's a genuine mixed finding, not a clean win
Unlike OCT-only 2.5D (clean win on every metric, see the prior entry),
**2.5D did not clearly improve the fusion model**: accuracy/balanced
accuracy/macro F1/Kappa are all slightly lower with 2.5D (though within
overlapping std ranges), while ROC-AUC and QWK are essentially tied —
with 2.5D showing meaningfully *lower* fold-to-fold variance on ROC-AUC
(std 0.016 vs 0.037) and QWK (0.053 vs 0.071). Per the plan's own decision
rule (don't manufacture a winner from ambiguous results, weigh macro F1/
balanced accuracy alongside QWK/ROC-AUC), this is recorded as **inconclusive
— not adopted** for fusion mode, called out explicitly as a mixed/negative
result rather than reframed as a win. Full numbers and the decision
rationale: `EXPERIMENTS.md` → `fusion_baseline_v1` / `fusion_2p5d_v1`.

### Files changed
`experiments/baseline_v1/{config,metadata,metrics}.json`,
`experiments/baseline_v1/README.md` (new), `EXPERIMENTS.md`, `PROGRESS.md`.
`results/cv_fusion_baseline_v1/`, `results/cv_fusion_2p5d_v1/` (new, real,
5 folds each + summary.json).

### Problems / blockers
None blocking, but a genuine open question: EXP-03 (12-slice 2.5D) in the
plan's sequence assumes 2.5D is the carried-forward OCT configuration —
this result means that assumption isn't clean-cut for fusion mode. Flagged
in `EXPERIMENTS.md`'s "Next experiment" note rather than deciding
unilaterally which OCT representation EXP-03 should build on.

### Next action
Per the plan: **stop here, do not start EXP-03 until this is reviewed** —
specifically, decide whether EXP-03 (denser slices) should vary slice
count on top of `single` or `2.5d`, given EXP-02's mixed result for fusion.

---

## 2026-09-27 (improvement-plan step 32: repo audit, dataset-expansion blocker found, metric expansion + live TensorBoard)

Working from `MM_RETINA_CLAUDE_IMPROVEMENT_PLAN.md`'s step-32 instruction:
report on the existing repo, then implement only dataset audit + metric
expansion + TensorBoard live logging (not the new architecture work) before
proceeding further.

### Repository inspection (no code changes made during this phase)
Confirmed the pipeline described in earlier entries is exactly what's on
disk: `training/{data,model,losses,train_multimodal,evaluate,cross_validate,
split_gamma}.py`, existing single-split baseline checkpoints/results, and
the completed 5-fold CV in `results/cv/`. No TensorBoard usage anywhere;
`tensorboard` package wasn't even installed. Metrics before this entry:
accuracy, balanced accuracy, macro F1, per-class P/R/F1, confusion matrix,
one-vs-rest macro ROC-AUC — no Cohen's Kappa, no QWK.

### Real blocker found: the plan's Section 2 premise doesn't hold
The plan asks to expand to the "complete GAMMA dataset, ~300 samples."
Inspected `dataset/GAMMA/grading/Glaucoma_grading/`: it has a `training/`
split (100 samples, **with** a ground-truth grade file) and a `testing/`
split (100 more raw samples, **no ground-truth file anywhere** — checked
every candidate filename pattern). This matches the public GAMMA challenge
structure: only the 100-sample training split ever had public grade labels;
validation/testing labels are withheld for the competition leaderboard.
**Conclusion: the full labeled dataset available for supervised
training/evaluation is exactly the 100 samples already in the manifest —
it cannot be expanded to ~300 without labels that don't exist in this
download.** Encoded this as a real, verifiable check
(`_check_full_dataset_availability` in `dataset/gamma_audit.py`) rather
than asserting it in prose only — reran the audit, confirmed the finding
programmatically (`dataset/audit_report.json` → `full_dataset_availability`).

### Completed
1. **Metric expansion.** Added Cohen's Kappa and Quadratic Weighted Kappa
   (QWK) to `training/evaluate.py`, refactored into a shared
   `compute_classification_metrics()` so `evaluate.py` (test-set) and
   `train_multimodal.py` (per-epoch validation) can never silently diverge
   on how a metric is defined. Documented the ROC-AUC averaging choice
   (one-vs-rest, macro) inline, per the plan's requirement not to leave that
   ambiguous. `cross_validate.py`'s fold aggregation now includes kappa/QWK
   too.
2. **TensorBoard live logging**, added to `train_multimodal.py`:
   - Per-epoch scalars: train/{loss,accuracy,macro_f1}, val/{loss,accuracy,
     balanced_accuracy,macro_f1,roc_auc,cohen_kappa,quadratic_weighted_kappa},
     learning_rate, epoch_time_seconds, gpu_memory_mb.
   - Live confusion matrix (matplotlib figure logged via `add_figure`).
   - A **fixed set of 8 validation samples**, same ones every epoch
     (deterministic — first 8 by dataset order for a given split file):
     de-normalized fundus image, de-normalized middle OCT slice, and a text
     summary of true label / predicted label / per-class probabilities.
   - `runs/<run-name>/` per run; added `scripts/start_tensorboard.{sh,bat}`
     and `runs/` to `.gitignore` (large binary event files, regenerated).
   - New `--checkpoint-metric` flag (`val_loss` default — preserves the
     existing baseline's exact behavior; `quadratic_weighted_kappa` and
     others available, matching the plan's Section 23 preference for QWK
     on *new* runs without silently changing what the already-reported
     baseline numbers mean). Checkpoints now also save optimizer/scheduler
     state, per Section 23.
   - `cross_validate.py` gained matching `--checkpoint-metric` and an opt-in
     `--tensorboard` flag (off by default for the 15-run CV sweep, since a
     wall of live logs isn't useful there — plain `train_multimodal.py` is
     the live-monitored single-run path).

### Real testing performed (not just "should work")
- Reran the existing `--smoke-test` path unchanged — still passes byte-for-
  byte the same forward/backward behavior as before this change.
- Ran a real 2-epoch training job (`tb_smoke_test`, fusion, tiny config) end
  to end. Verified via `tensorboard.backend.event_processing` that all 24
  expected scalar/figure/image/text tags actually landed in the event file
  (not just "no crash").
- Started the real TensorBoard server (`tensorboard --logdir runs`),
  opened it in a real browser, and visually confirmed: the scalar dashboard
  updates, the confusion-matrix figure renders with correct axis labels and
  real counts, and the fixed-sample panel shows an actual (correctly
  de-normalized, recognizable) fundus photo with its prediction text.
- Deleted the smoke-test run's TensorBoard logs and checkpoint afterward —
  not committed, not left as clutter.

### Files changed
`dataset/gamma_audit.py`, `dataset/audit_report.json` (regenerated),
`training/evaluate.py`, `training/train_multimodal.py`,
`training/cross_validate.py`, `scripts/start_tensorboard.sh` (new),
`scripts/start_tensorboard.bat` (new), `.gitignore`, `PROGRESS.md`.
No changes to `model.py`, `losses.py`, `data.py`, or the split logic — none
of that was needed for this phase, per the plan's own gating.

### Problems / blockers
The dataset-expansion blocker above is real and unresolved: Section 2 of
the improvement plan cannot be carried out as written with what's on disk.
Options if this is pursued further: (a) proceed with rigorous work on the
existing 100 labeled samples (what the rest of the plan's experiment list
mostly doesn't actually depend on sample count), (b) source the withheld
labels from elsewhere if the user has legitimate access, (c) explicitly
retarget the plan's dataset-size ambitions to 100 samples. Not decided here
— this is the user's call, not something to resolve unilaterally.

### Next action
Per the plan's implementation order, the next gated items are OCT 2.5D
(Experiment OCT-2) and denser slice sampling (OCT-3) — but only after the
user has weighed in on the dataset-size blocker above, since it changes the
practical scope of "run the full-dataset baseline" (plan Section 29/Step 7).

---

## 2026-09-27 (follow-up: Experiment OCT-2 implemented and run for real, oct-only)

User said to proceed with the dataset-size blocker unresolved and go
straight to Experiment OCT-2 (2.5D OCT representation).

### Completed
- Implemented `--oct-representation {single,2.5d}` across `data.py`
  (stacks B-scans `[i-1, i, i+1]` as 3 channels via `Image.merge("RGB", ...)`
  so the existing augmentation pipeline applies identically to all 3;
  edge slices clamp to the nearest valid index), `model.py`
  (`OCTVolumeEncoder`/`GammaMultimodalModel` gained `oct_in_chans`),
  `train_multimodal.py`, `evaluate.py`, `cross_validate.py`. Default
  (`single`) verified byte-identical to the pre-existing baseline (same
  smoke-test loss, 1.1517, before and after).
- Ran the real 5-fold CV comparison (oct-only, matched folds/hyperparameters
  against the existing `cv-run-1` OCT baseline) — see `EXPERIMENTS.md`
  `oct25d-cv-run-1` for full per-fold numbers.
- **Result: 2.5D beats single-channel on every directly comparable metric**
  (accuracy 0.680±0.058 vs 0.661±0.089, balanced_accuracy 0.608±0.085 vs
  0.599±0.076, macro_f1 0.602±0.089 vs 0.587±0.090, roc_auc 0.863±0.035 vs
  0.842±0.041), with slightly lower fold-to-fold variance too. Real but
  modest (~0.02 mean gain) — not oversold as a dramatic win.

### Problems found and fixed live during this work (not hidden)
1. First launch attempt used a nested `nohup ... &` inside an
   already-backgrounded shell call — this decoupled the real training
   process from the session's own background-task tracking, so no
   completion notification would ever have fired. Fixed by launching the
   training command directly as the tracked background process on the
   second attempt.
2. Python's stdout was fully block-buffered under file redirection, so the
   live log file looked frozen (0 lines) even while training was
   genuinely progressing (confirmed separately via GPU utilization and
   growing files on disk) — fixed with `python -u`.
3. User asked for actual live monitoring (not just a static log) — added
   `--tensorboard` to the CV run (off by default for CV sweeps, on by
   request here), started the real TensorBoard server, and visually
   verified in a real browser that live scalars were updating epoch to
   epoch.
4. User correctly flagged that GPU utilization looked low (~20-30%,
   2.2/6GB VRAM) and asked to fix it. Tried `--workers 4` — this made
   epoch time *worse* (71s vs ~22s), because Windows respawns DataLoader
   worker processes every epoch by default (no `persistent_workers`), and
   that spawn cost dominates for a 79-sample fold with only ~20
   batches/epoch. Diagnosed correctly rather than assuming more workers
   must help; reverted to `--workers 0` (confirmed faster) and explained
   why low GPU utilization here is an expected property of this specific
   workload (small batch, small backbone, small dataset — not something
   data-loading parallelism fixes) rather than silently declaring the
   problem solved.

### Files changed
`training/data.py`, `training/model.py`, `training/train_multimodal.py`,
`training/evaluate.py`, `training/cross_validate.py`, `EXPERIMENTS.md`,
`PROGRESS.md`. `results/cv_oct25d/` (new, real, 5 folds + summary.json).

### Next action
1. Decide whether to adopt 2.5D as the new OCT default going forward
   (modest, consistent real improvement) or run it once more with a second
   seed before committing, given n=5 folds' std values carry real
   uncertainty on their own.
2. Per the plan's order: Experiment OCT-3 (denser slice sampling:
   12/16/24 slices) is next, then the stronger-fundus-backbone experiment
   — still gated on the user's call about the 100-vs-300-sample dataset
   question from the previous entry.
3. If 2.5D is adopted, it should also be tried in `fusion` mode (this run
   only tested oct-only) for a complete before/after comparison.

---

## 2026-09-17 08:40 (follow-up: checkpoint disclosure, real multi-slice OCT, Grad-CAM)

Follow-up to the previous entry, addressing a review of the live demo.

### Completed
1. **Checkpoint disclosure.** Added explicit text to `/demo` and
   `backend/README.md` stating the live demo uses the single-split
   demonstration checkpoints (`fundus_run1`/`oct_run1`/`fusion_run1`),
   not the 5-fold CV fold checkpoints behind `/results`. Investigated
   exposing the exact CV fold checkpoints instead: confirmed none exist
   on disk (`cross_validate.py` deletes them by default) — reproducing
   them means retraining, which is out of scope for a disclosure fix, so
   documented instead of retrained.
2. **Real multi-slice OCT input.** `training/data.py`'s
   `evenly_spaced_indices(256, 8)` gives an exact fixed index set
   `[0,36,73,109,146,182,219,255]`; all of GAMMA sample 0001's 256 real
   slices are already served at `website/public/oct-volume/0001/`, so
   real 8-slice-volume support was straightforward and reliable to add
   (not fabricated, not a workaround). `inference.predict()` now accepts
   an ordered list of real slice images and stacks them with zero
   repetition — same shape/semantics as training/CV. `POST /api/predict`
   gained an `oct_slices` multipart field (validated against the loaded
   model's expected count before inference runs). The single-slice
   fallback is unchanged and still available; both modes are now reported
   via `oct_mode` (`"real_volume"` vs `"repeated_single_slice"`), replacing
   the old boolean `oct_repeated_single_slice` field.
3. **Grad-CAM — fundus only, OCT deferred.** Implemented and tested a
   real Grad-CAM (`backend/gradcam.py`) hooking the fundus encoder's
   `layer4` (verified this exists on the actual loaded resnet18 backbone
   before writing the hook). Ran a real forward+backward pass on the real
   GAMMA sample 0001 fundus photo and **visually inspected the actual
   output image** (not just checked it didn't crash) — the heatmap
   correctly highlighted the optic disc, the anatomically relevant region
   for glaucoma grading. Wired through `inference.predict(explain=True)`
   and `POST /api/predict`'s `explain` field; confirmed via curl that it
   works for fundus and fusion modality, and is a clean no-op (no error,
   `fundus_heatmap: null`) for oct-only. OCT Grad-CAM was investigated
   (architecturally plausible — shared backbone per slice — but attention-
   pooled multi-instance attribution is a different and less-established
   claim than single-image Grad-CAM) and **explicitly deferred**, not
   attempted, per the instruction to only ship what's verified reliable.

### Real testing performed
- curl: fundus/oct/fusion all still work after the OCT input refactor.
- curl: real 8-slice volume for oct-only and fusion — both succeeded,
  `oct_mode: "real_volume"`.
- curl: wrong slice count (5 instead of 8) — clean 400, not a crash.
- curl: single-slice fallback still works for all 3 modalities.
- curl: `explain=true` for fundus and fusion — real heatmap returned;
  saved and visually inspected the actual decoded PNG (twice — once from
  a standalone script, once from the live API response — identical).
- curl: `explain=true` for oct-only — correctly no-op, no error.
- Browser, full end-to-end against the real running dev server: fundus/
  OCT (both single-slice and real-volume)/fusion all produce predictions
  matching the curl results; Grad-CAM checkbox produces a real rendered
  heatmap image in the DOM (verified via `naturalWidth`/`naturalHeight`/
  `complete` on the actual `<img>` element, since this session's
  screenshot tool was unreliable throughout — DOM-level checks were used
  as the source of truth instead, consistent with earlier in this
  project).

### Files changed
`backend/gradcam.py` (new), `backend/inference.py`, `backend/app.py`,
`backend/README.md`, `website/src/app/demo/page.tsx`, `PROGRESS.md`.
No changes to `EXPERIMENTS.md`, CV methodology, or `training/`'s
validated training/evaluation code — nothing there needed a genuine bug
fix this round.

### Verification checklist (per the follow-up request)
1. Fundus: works (curl + browser).
2. OCT: works, both single-slice and real-8-slice-volume modes (curl + browser).
3. Fusion: works, both OCT input modes, with and without Grad-CAM (curl + browser).
4. Browser end-to-end: works (DOM-verified, screenshot tool unreliable this session).
5. Real multi-slice OCT support: ADDED (not left as a limitation — the
   single-slice repeat is now an explicit fallback, not the only option).
6. Grad-CAM: ADDED for fundus/fusion; OCT explicitly DEFERRED with reasoning.
7. Files changed: listed above.
8. Remaining limitations: OCT Grad-CAM not implemented (deferred, see
   backend/README.md); no Docker; no auth; uploaded images processed
   in-memory only (no persistence, by design).

### Next action
If continuing: OCT Grad-CAM (per-slice, aggregated through the attention
weights) would be the natural next explainability step, but should get
its own dedicated validation pass (visual inspection across multiple
samples, not just one) before shipping, per how the fundus version was
verified here.

---

## 2026-09-17 02:35 (website updated with CV results; live demo backend built)

### Completed
- Updated `/results` to show the real 5-fold CV numbers (mean±std, all
  four metrics, all three modalities) instead of the old single-split
  numbers. Old numbers are NOT displayed anywhere on the page anymore
  (still fully preserved in EXPERIMENTS.md/git history). Added the
  required interpretation wording and a "why cross-validation" section.
- Built `backend/` — a FastAPI service (`app.py` + a thin `inference.py`
  wrapper) that loads the real `fundus_run1.pt`/`oct_run1.pt`/`fusion_run1.pt`
  checkpoints once at startup and serves `POST /api/predict` +
  `GET /api/health`. Reuses `training/data.py`'s transforms and
  `training/evaluate.py`'s checkpoint loader directly — no duplicated
  preprocessing/model code.
- Rewrote `/demo` to actually call this backend: modality picker
  (fundus/OCT/fusion), upload or "select demo" (real GAMMA sample 0001
  images, copied into `website/public/demo/`), real prediction + per-class
  probabilities + inference timing rendered from the actual API response.
  Backend-offline and validation-error states are handled and were tested.
- Created `demo_images/` (fundus/oct/fusion READMEs documenting provenance
  — Next.js serves the actual files from `website/public/demo/` instead,
  since it can't serve outside `public/`).
- `.env.example` (backend) / `.env.local.example` (website) added; both
  `.gitignore`s patched so `.env*.example` isn't swept up by the `.env*`
  rule that (correctly) keeps real `.env` files out of git.
- Removed `DemoBadge.tsx` — dead code once `/demo` and `/results` stopped
  needing a "this is fake" label.

### Real end-to-end testing actually performed
Backend, via curl, against real images:
- `GET /api/health` — reports `{"models_loaded": ["fundus","fusion","oct"]}`.
- `POST /api/predict` fundus-only on the real GAMMA-0001 fundus photo:
  succeeded, prediction=normal.
- `POST /api/predict` oct-only on a real B-scan: **failed on first try**
  (real bug — see below), then succeeded after the fix.
- `POST /api/predict` fusion on the real matched pair: succeeded,
  prediction=normal, 63ms inference.
- Validation: missing required image → 400; invalid modality → 400;
  corrupt/non-image upload → 400; unsupported content-type → 400. All
  return clean JSON errors, no stack traces.
- Model-loading failure: renamed `oct_run1.pt` away, restarted the
  server — `/api/health` correctly showed the load error and
  `/api/predict` for that modality returned 503, not a fake result.
  Checkpoint restored afterward.

Frontend, via the actual running Next.js dev server in a real browser
(not just curl): loaded `/demo`, confirmed "Backend online" status,
clicked "Select demo" for both images, clicked "Run analysis", and got
back the SAME real prediction the curl test produced (normal, 73.9%
confidence) rendered in the UI. Also killed the backend and reloaded —
confirmed the "Backend unreachable" state shows and the Run button
disables, rather than the page pretending to work.

### Real bug found and fixed during this work
`app.py` was force-converting every upload to RGB before handing it to
`inference.py`. OCT B-scans need grayscale (matching how
`training/data.py` loads them during training) — the mismatch produced a
3-channel tensor into a 1-channel-expecting conv layer and crashed with a
clear PyTorch shape error. Fixed by deferring color-mode conversion to
`inference.py` (RGB for fundus, `L` for OCT), matching `data.py` exactly.

### Files changed
See the commit for the full list; summary: `backend/` (new: app.py,
inference.py, requirements.txt, README.md, .env.example), `demo_images/`
(new), `website/public/demo/` (new — 2 real image files),
`website/.env.local.example` (new), `website/src/app/demo/page.tsx`
(rewritten), `website/src/app/results/page.tsx`,
`website/src/components/{AblationTable,ResultsPreview}.tsx`,
`website/src/lib/content.ts` (CV_RESULTS replaces the old single-split
REAL_RESULTS), `website/src/components/DemoBadge.tsx` (deleted, dead
code), `.gitignore` / `website/.gitignore` (env-example exception).

### Problems / blockers
None remaining. The OCT-grayscale bug above was caught by actually
running the intended test (not by inspection) and fixed before commit.

### Next action
1. Grad-CAM/attribution for the demo (still not implemented — see the
   backend README's "what's NOT implemented" section).
2. Accept multiple OCT slice uploads instead of repeating one image.
3. Consider a Dockerfile for the backend if deployment beyond localhost
   is ever needed (discussed with the user, deferred as unnecessary for
   now).

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
