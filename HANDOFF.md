# MM-RETINA — Project Handoff

_Written 2026-11-08 from git history (33 commits across all branches), `PROGRESS.md`, `EXPERIMENTS.md` and the newmix docs. All dates are commit dates (IST, +0530). Numbers are copied from those logs, not re-run._

---

## 1. One-paragraph summary

MM-RETINA started as a multimodal (fundus + OCT) glaucoma grading project on the **GAMMA** dataset (100 labeled patients; Normal / Early / Progressive). In ~5 weeks it grew into: a website, a real training pipeline, 5-fold patient-level CV, a controlled ablation series (EXP-01…06), side studies on two clinical cohorts (HVF, RNFL/GCC), a RETFound foundation-model attempt (negative), a product-grade pass (model card, CI, Docker), and finally **newmix**, which merges three people's projects (Kartik's diabetes models, Dashita's glaucoma OCT/clinical research, and MM-RETINA) into one FastAPI + Next.js app.

**Best honest result:** EfficientNet-B0 fundus + ResNet18 OCT (8 slices) + vector cross-modal fusion → **accuracy 0.820 ± 0.055, ROC-AUC 0.924 ± 0.039, QWK 0.798** in patient-level 5-fold CV (`results/cv_fusion_effnetb0_v1/`). This is the frozen benchmark.

---

## 2. Timeline

### Phase 1 — Website + first pipeline (2026-09-16 → 09-17)

| When | Commit | What happened |
|---|---|---|
| 09-16 00:21 | `263c7f6` | Initial commit: MM-RETINA multimodal glaucoma grading project |
| 09-16 00:34 | `3992c5f` | Website redesigned per a UI/UX brief |
| 09-16 00:52 | `1060bce` | "Warm Titanium" palette, real GAMMA imagery |
| 09-16 23:47 | `db593db` | Interactive OCT B-scan viewer; dataset loader schema fixed |
| 09-16 23:53 | `aab3722` | `gamma_loader` pointed at per-slice B-scan JPEGs rather than the raw volume |
| 09-17 00:06 | `84fb3fc` | Real multimodal training pipeline built + smoke-tested |
| 09-17 00:19 | `a43100d` | First real ablation (fundus / OCT / fusion, single split); real numbers wired into site |
| 09-17 00:57 | `da8be34` | Patient-level 5-fold CV script added |
| 09-17 01:54 | `44e080f` | **5-fold CV done.** Fundus 0.730 acc, OCT 0.661, Fusion 0.710 (ROC-AUC 0.892, most consistent across folds). Single-split result that "fundus beats fusion" turned out to be driven by one lucky fold |
| 09-17 02:41 | `aa6b39a` | `/results` shows real CV numbers; **FastAPI backend + live `/demo`** built. Found and fixed a real bug (OCT upload forced to RGB, model expects grayscale) |
| 09-17 02:52 | `aa0a411` | Demo supports 8-slice OCT volumes; checkpoint provenance disclosed |
| 09-17 08:33 | `147b4b1` | Fundus Grad-CAM added; OCT Grad-CAM documented as deferred |

### Phase 2 — Modality check + ablation series (2026-09-27)

| When | Commit | What happened |
|---|---|---|
| 09-27 13:14 | `64f1cb7` | Modality sanity check rejects wrong-slot uploads (e.g. fundus in OCT slot) |
| 09-27 19:13 | `64caa70` | Dataset audit, Kappa/QWK metrics, live TensorBoard, **EXP-01…06 ablation series** |
| 09-27 22:16 | `68a9702` | HVF + RNFL/GCC feature extraction, baseline models, M01 multi-dataset experiment, case examples, research-journey page (`better_fusion` branch) |

**Ablation ladder (all 5-fold patient-level CV, same folds):**

| Exp | Change | Outcome |
|---|---|---|
| EXP-01 | Baseline (ResNet18 + ResNet18, vector fusion) | Frozen as reference: acc 0.731, macro F1 0.681, kappa 0.577 |
| EXP-02 | OCT 2.5D (3 neighbouring slices) | Mixed / inconclusive → **not adopted** |
| EXP-03 | 12 OCT slices | Rejected |
| EXP-04 | 16 OCT slices | Rejected (monotonic regression) → **8 slices, single** kept |
| EXP-05 | **EfficientNet-B0** fundus encoder | **Clear win**: acc 0.731→0.820, F1 0.681→0.781, kappa 0.577→0.716, fewer params (4.0M vs 11.2M). **Adopted** |
| EXP-06 | Token-level cross-modal transformer fusion | QWK/AUC up, but F1/balanced-acc down and variance doubled → **inconclusive, not adopted** |

Architecture freeze reached after EXP-06. Documented blocker: GAMMA's 100 "testing" samples have **no public labels**, so the labeled set stays at 100 patients.

**Side studies (same day):**
- **EXP-C01 (HVF severity):** 168 eyes / 90 patients, QWK ≈ 0.92–0.97 — but this was circular.
- **EXP-C01b:** drop MD/PSD/VFI (which essentially *define* the label) → QWK ≈ 0.10–0.16, i.e. chance. Almost all prior signal came from label-defining fields.
- **Provenance audit:** RNFL/GCC (171 eyes) and HVF have **no valid patient link** to GAMMA or to each other, so they are never fused at the patient level.
- **EXP-M01 (shared trunk across GAMMA/HVF/RNFL-GCC, no patient pairing):** shared trunk slightly helped HVF (kappa 0.036→0.125) and RNFL/GCC (0.356→0.442), slightly hurt GAMMA probe (QWK 0.851→0.832). Suggestive, not conclusive. GAMMA numbers here use a weaker ResNet18 checkpoint and are **not** the benchmark.

### Phase 3 — RETFound foundation model (2026-10-13)

| When | Commit | Result |
|---|---|---|
| 10-13 02:04 | `6d091b9` | **EXP-R01** frozen RETFound ViT-L + logistic head: acc 0.690, AUC 0.871 vs ResNet18 fundus-only 0.730 / 0.885 → no gain, not adopted. Root README added |
| 10-13 02:12 | `07b93e8` | **EXP-R02** LoRA fine-tune of RETFound: acc 0.640, AUC 0.813, fold 4 collapsed → worse than both. **RETFound line closed.** Fixed recipe, no tuning on val folds (to avoid leakage) |

Weights (3.95 GB, CC BY-NC 4.0) live outside the repo at `C:\Users\ASUS\data\retfound\`.

### Phase 4 — Product-grade pass (2026-10-15)

`0d7f6d1` (branch `claude/product-level-improvements-58a147`):
- Fixed stale website numbers (were showing the ResNet18 baseline). Site numbers now generated from `results/**/summary.json` by `scripts/export_site_results.py`; CI fails on drift.
- Rebuilt `/results`, added `/model-card`, turned `/demo` output into an analysis report (probability bars, Grad-CAM, copy JSON, print/PDF).
- Standalone HVF and RNFL/GCC linear models served at `/api/tabular/*` with reliability badges (HVF labelled "no better than chance").
- Backend pytest suite, GitHub Actions CI, Dockerfiles + docker-compose (**images not build-tested**).

### Phase 5 — newmix (2026-10-23)

| When | Commit | What happened |
|---|---|---|
| 10-23 04:09 | `6b697d4` | **newmix**: unified glaucoma + diabetes retinal screening workspace (`past_work/RETINA/newmix/`), 429 files |
| 10-23 04:18 | `c518551` | PR #2 merged into `main` (on `origin/main`) |

Combines Kartik's diabetes module (vessel segmentation, fractal analysis, HbA1c estimate), Dashita's Sankara glaucoma OCT + clinical Excel, and MM-RETINA's GAMMA model. Run with `.\run.ps1`; `python tests/smoke_test.py` runs 32 checks.

**Key newmix findings (303 eyes / 162 patients, patient-grouped 5-fold CV):**
- Clinical features → 4-class stage: **67.7% balanced accuracy** (~0.95 AUC glaucoma vs control).
- Adding visual-field MD → 92.2%, but **circular** (severity label is a rule on MD, 100% agreement).
- OCT B-scan alone: ~44–47% balanced accuracy, regardless of architecture.
- The source paper's 87.5% / 92.5% were **not reproduced**; with its apparent protocol (augment, then random image split) the same model hit 81.3% because 100% of test images had a twin in training. Patient-grouped: 52%. (Doesn't prove what the paper did.)
- OCT + clinical fusion: no reliable gain over clinical alone.
- **Defer-to-visual-field policy:** answering the 80% most-confident cases gives 76% accuracy; the deferred ones were right only 45% of the time.
- Data audit: "Disc photos" folder is a byte-identical copy of "Fundus image"; 82/171 RNFL/GCC rows duplicate the Research Excel; pachymetry/CFT missingness leaks the label (excluded).
- GAMMA fundus model on Sankara fundus photos: no better than the class prior (always-"early" scores 77.6%).
- Kartik's HbA1c models: no validation shipped; non-informative on his 22 reference images. Artery/vein weights never delivered.

---

## 3. Current state of git (as of 2026-11-08)

- `origin` = `github.com/IATESPAGHETTI/MM-RETINA`; `retina_prj4` = `github.com/IATESPAGHETTI/retina_prj4`.
- `origin/main` is at `c518551` (everything through newmix).
- **NOT on any remote:** `claude/project-improvement-suggestions-6d84f0` → `07b93e8` (RETFound LoRA, EXP-R02).
- Local `main` is 4 commits ahead of `retina_prj4/main` (those commits are on `origin/main`).
- **This worktree (`claude/github-push-status-fdb470`) is at `c518551`, so it does NOT contain the RETFound commits (`6d091b9`, `07b93e8`). It does not contain the product-grade commit `0d7f6d1` either** — check that branch/origin before assuming those features exist in `main`. Several commits above (RETFound, product-grade) are not in `origin/main`'s ancestry; verify with `git branch -r --contains <sha>`.
- Many stale `claude/*` worktree branches exist; most point at commits already on `origin`.

---

## 4. Open items / next steps

1. Push `07b93e8` (RETFound LoRA) and decide whether to merge RETFound + product-grade branches into `main`.
2. Push `main` to `retina_prj4` if that remote should stay current.
3. Email the data provider for a real **HVF ↔ RNFL/GCC ↔ patient key**. Without it, EXP-C02/C03 (fusion of those cohorts) are impossible. Draft written, not sent.
4. Harvard-GDP (open, Zenodo 13178701, 9.4 GB; RNFL map + VF) identified as an extra data source, not downloaded.
5. If frozen EfficientNet-B0 GAMMA embeddings are needed again, rerun `cross_validate.py --keep-checkpoints` once (checkpoints are deleted by default).
6. Not started, gated on go-ahead: ordinal classifier, anatomy-aware auxiliary learning, multi-seed validation, fold ensemble.
7. Docker images never build-tested. OCT Grad-CAM deferred.

---

## 5. Known limitations (be upfront about these)

- Only **100 labeled GAMMA patients**; CIs are wide and fold variance high.
- RNFL/GCC has no patient ID, so its splits are stratified, not patient-grouped.
- Live demo repeats one OCT image across 8 slices unless a real volume is supplied. The demo checkpoints differ from the CV benchmark checkpoints (disclosed on `/model-card`).
- newmix deployed fusion gives OCT 20% weight, a conservative choice made after seeing the sweep.
- Research prototype, **not a medical device**.

---

## 6. Where things live

| Path | What |
|---|---|
| `PROGRESS.md` | Dated log of every task (newest first) |
| `EXPERIMENTS.md` | Every training/eval run, including failures |
| `results/` | Per-fold metrics, predictions, confusion matrices, `summary.json` |
| `training/` | Model, training, CV, evaluation scripts |
| `backend/` | FastAPI inference service |
| `website/` | Next.js site (`CLAUDE.md`, `AGENTS.md` inside) |
| `dataset/` | Feature extraction, provenance audits, split files |
| `past_work/RETINA/newmix/` | The merged product (`README.md`, `docs/DATA_AUDIT.md`, `docs/EXPERIMENTS.md`, `docs/ARCHITECTURE.md`) |
