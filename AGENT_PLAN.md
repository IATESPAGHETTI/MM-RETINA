# AGENT_PLAN.md — Work split: Claude vs Codex

_Drafted 2026-11-21. **Status: NOT STARTED.** Neither agent begins until the user says "start". Once started, work continues without waiting for per-step approval, except where "Stop and ask" applies._

## Goals

1. **Better results:** raise Early-glaucoma recall (EXP-05: 16/26 = 61.5%; 9 of 10 errors predicted Progressive) without hurting macro F1 or Progressive recall, using an honest nested-CV baseline.
2. **More polished product:** a rehearsable panel demo (case review, case library, "Needs review" state, one-click launch) whose every number traces to a saved results file.

Frozen benchmark for reference: EfficientNet-B0 fundus + ResNet18 OCT (8 slices) + vector fusion → acc 0.820 ± 0.055, ROC-AUC 0.924, QWK 0.798 (`results/cv_fusion_effnetb0_v1/`). Do not overwrite it.

---

## Ownership (files each agent may edit)

| Area | Claude | Codex |
|---|---|---|
| `training/`, `results/`, `experiments/` | **owns** | read-only |
| `EXPERIMENTS.md`, `PROGRESS.md` | **owns** (Codex appends only under its own dated heading) | append-only |
| `website/` (pages, components, results page) | read-only | **owns** |
| `backend/` API endpoints, startup check | shared — see contract | **owns** UI-facing routes + startup check |
| `scripts/` (launcher, export script) | read-only | **owns** |
| CI / Docker / README | read-only | **owns** |
| `scripts/export_site_results.py` input side (JSON schema) | **owns the schema** | consumes it |

Never edit a file the other agent owns. If you need a change there, write it under "Requests" at the bottom of this file.

---

## Claude's tasks (experiments + evidence)

1. **Nested-CV baseline rerun (first, runs unattended).** Rerun EXP-05 with patient-level outer folds; choose epoch and tune settings inside each training fold only. 3 seeds. Track macro F1, Early recall, Progressive recall (plus acc, AUC, QWK). Save **per-eye predictions** (probabilities + labels + fold + seed) for fusion, fundus-only and OCT-only on identical folds. Smoke-test first, per project convention.
2. **Error analysis.** Inspect the 9 Early→Progressive errors: scan quality, optic-disc framing, whether fundus-only / OCT-only got each right. Treat as hypothesis-forming (n=9), not proof.
3. **One exploratory change at a time** (e.g. optic-disc-centered crop vs full frame), judged on pooled out-of-fold predictions across seeds with bootstrap CIs. Adopt only if the gain clears the noise; log rejected runs too.
4. **Abstention ("Needs review") evidence.** Using nested CV (calibration split separate from evaluation split), produce the answered-vs-error curve **with confidence intervals**. Output a threshold file for the exact checkpoint the demo serves. Do not present one threshold as validated.
5. **Results contract.** Publish stable JSON files (see below) and log everything in `EXPERIMENTS.md` / `PROGRESS.md`.

## Codex's tasks (demo + product polish)

1. **Case-review screen.** One click loads a matched fundus + 8-slice OCT case. Reuse the OCT slice viewer and fundus Grad-CAM overlay. Show fundus / OCT / fusion outputs side by side with probability bars and where they agree/disagree.
2. **Case library.** Three cases: a clear correct case, an Early/Normal near-tie, and a missing-input example (app must refuse cleanly, never fabricate a prediction). Each result labeled **"live run"** or **"saved cross-validation result"**; saved cases double as an offline fallback.
3. **"Needs review" UI state** for GAMMA, reusing the Retina Suite interaction pattern. Consumes Claude's threshold + curve files; wire it only after those exist.
4. **One-click launch + startup check** for API, checkpoints and sample assets, with clear messages when something is missing. Verify the demo uses a **real 8-slice OCT volume** for the matched case (not one slice repeated).
5. **Consistent evidence.** Generate the results page and deck numbers from saved experiment files (extend `scripts/export_site_results.py`); CI should fail on drift. Every result on screen must say which model produced it.
6. Review `scripts/claude-pro.ps1` is unnecessary for this plan; leave it alone unless it breaks something.

---

## Shared contract (so we don't block each other)

Claude writes, Codex reads. Paths are proposed; Claude confirms the final names when the first run finishes and updates this section.

- `results/nested_cv_v1/summary.json` — per-model mean ± std and pooled metrics, incl. Early/Progressive recall and bootstrap CIs.
- `results/nested_cv_v1/per_eye_predictions.csv` — columns: `patient_id, fold, seed, model, y_true, p_normal, p_early, p_progressive, y_pred`.
- `results/nested_cv_v1/abstention.json` — threshold, coverage-vs-error curve with CIs, checkpoint identifier it applies to.
- Until these exist, Codex builds against clearly marked placeholder fixtures and **must not** display them as real results.

---

## Rules for both agents

1. **Separate branches/worktrees.** Never write to the same checkout. Merge via PR; the user decides when.
2. **One GPU job at a time** (6 GB RTX 3060). Only Claude launches training; Codex does not start GPU jobs.
3. **Honest numbers only.** No tuning on evaluation folds, no cherry-picked folds, no claims beyond the data. Keep the "research prototype, not a medical device" disclaimer.
4. **Synthetic/placeholder data is labeled as such** in code and UI.
5. **No model weights, patient data or scans committed** (excluded from git).
6. **Log as you go:** each agent writes a dated entry in `PROGRESS.md` before finishing a task.
7. **Do not touch** the frozen EXP-05/06 results or the website numbers except via the generated export.

## Known constraints (don't plan around what isn't there)

- Only 100 labeled GAMMA patients; 26 Early cases → wide CIs (Early recall 61.5% ≈ 41–79%).
- **No external paired fundus+OCT dataset exists** here, so "confirm on another clinic/device" is out of scope until such data is obtained.
- HVF and RNFL/GCC cohorts have no valid patient link to GAMMA; do not fuse them.
- Demo checkpoints differ from CV benchmark checkpoints (weights not in git); the startup check must say which one is loaded.
- Docker images were never build-tested.

## Stop and ask the user

- Before any push to a remote or merge to `main`.
- If a result contradicts the frozen benchmark, or a step needs data/weights that aren't on disk.
- Before adding a dependency that changes the environment (e.g. a disc-detector model).

## Requests between agents

_(append below: `YYYY-MM-DD from <agent> to <agent>: request`)_
