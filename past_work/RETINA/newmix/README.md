# Retina Suite (newmix)

One working product built from three projects:

| Project | Author | What it contributes |
|---|---|---|
| RETINA | Kartik | Diabetes module: vessel segmentation, fractal analysis, HbA1c estimate (his models, unchanged) |
| Research | Dashita | Sankara glaucoma OCT + clinical Excel; the OCT model, clinical-feature models and the paper audit |
| MM-RETINA | you | GAMMA multimodal grading, Grad-CAM, the website's design system |

No login (removed on request). Research prototype, **not a medical device**.

## Run it

```powershell
.\run.ps1          # creates the venv, installs, starts API :8000 and app :3000
```

Then open http://localhost:3000/workspace. API docs: http://localhost:8000/docs.
To verify everything end to end: `python tests/smoke_test.py` (32 checks).

Needs Python 3.10+ and Node 20+. The code falls back to CPU when no GPU is present, but it has only been run and tested on an RTX 3060. TensorFlow is **not** required.

## What is in the app

| Page | Does |
|---|---|
| Overview | entry points, live model status, session history (browser-only) |
| Glaucoma | OCT B-scan + RNFL/GCC measurements → stage, **or "inconclusive, order a visual-field test" when the model is unsure**, Grad-CAM, per-feature drivers, MD staging rule |
| Multimodal (GAMMA) | fundus + 8-slice OCT volume → Normal / Early / Progressive, fundus Grad-CAM |
| Diabetes | vessel overlay, fractal dimension, experimental HbA1c estimate |
| Models | every cross-validation result, read from `ml/results/` |
| Data & integrity | how the datasets relate and what the audit found |

The original research site (home, dataset, model, results, presentation) still lives at `/`.

## What the evidence says (patient-grouped 5-fold CV, 303 eyes / 162 patients)

| Question | Result |
|---|---|
| Clinical features (RNFL, GCC, CDR, IOP, age, sex) → 4-class stage | **67.7% balanced accuracy** (70% accuracy), ~0.95 AUC glaucoma vs control |
| Same, plus visual-field MD | 92.2%. **Circular**: the cohort's severity label is a rule on MD (100% agreement) |
| OCT B-scan alone → 4-class | ~44–47% balanced accuracy, ~49% accuracy, 0.78 AUC. Same for ResNet18, EfficientNet-B0, a U-Net hybrid, frozen-feature probes and the paper's own architecture |
| Paper protocol (augment, then random image split) | 81% accuracy, but 100% of test images have a twin in training; patient-grouped: 52% |
| OCT + clinical fused | no reliable gain over clinical alone (−0.4 points, 95% CI −2.2 to +1.1) |
| GAMMA fundus + OCT (your model) | 71% accuracy (82% with the EfficientNet-B0 variant), 5-fold CV |
| **Defer the least-confident fifth** (clinical model) | answers 80% of cases at **76% accuracy** (70% if forced to answer all); the deferred cases were right only 45% of the time. Cut-offs from held-out eyes; not tested on new patients |
| Kartik's HbA1c models | no validation shipped; on his 22 reference images they are non-informative (see below) |

**The paper's image results (87.5% four-class, 92.5% binary) were not reproduced under patient-grouped evaluation, and the likely reason was tested.** I built the paper's architecture as written (U-Net branch + InceptionV3, 512 px, their preprocessing and augmentation) and tuned it on inner validation only: 49.8% accuracy, 0.78 AUC, the same as every other image model. Then, with that same model and data, I ran the paper's apparent protocol (augment 303 scans to 1,818, then split at random by image): **81.3% accuracy**, with 100% of test images having an augmented copy of the same scan in training. A patient-grouped split of the identical data gave 52.2%. So that protocol can produce numbers like the paper's. This does not prove the paper used it (its split is not described), and the test was one seed on ~180 images. The paper's 91–93% *clinical-feature* figures are reproduced only when HVF MD is included, and MD defines the label.

### Findings about the data (`docs/DATA_AUDIT.md`)

- The Sankara "Disc photos" folder is a byte-identical copy of the "Fundus image" folder (107 files).
- 82 of the 171 rows in the Sankara RNFL/GCC workbook are the same eyes as the Research Excel; 67 HVF files link to exactly one Research eye. The fundus photographs cannot be linked (no identifier), so they are not used for training.
- Pachymetry and CFT are missing far more often in controls, so they would leak the label and are excluded.

### Kartik's models

The Keras models run on the torch backend and were checked against real TensorFlow 2.18 on identical inputs (max output difference 0.014, identical predictions), so the port is faithful. On his 22 reference images the 6-bin HbA1c model returns its lowest bin every time and the binary model flags 95% as elevated. The app labels the output experimental and warns when the two models contradict each other. Artery/vein weights (`av_model.pth`) were never delivered, so that feature is not offered.

## Layout

```
backend/    FastAPI: routers/ (HTTP), services/ (models, no FastAPI imports), dipp/ (Kartik's code + weights)
frontend/   Next.js 16: /workspace/* product, (site)/* research pages
ml/glaucoma/  data loader, clinical + OCT training, fusion eval, audit
ml/gamma/     MM-RETINA training code and the demo checkpoints
ml/results/   every metric the UI shows (JSON/CSV)
models/       oct_research.pt (3-seed ResNet18 ensemble), clinical_*.joblib
data/research/ the 303 OCT B-scans + Excel
docs/         DATA_AUDIT.md, ARCHITECTURE.md
tests/        smoke_test.py
```

See `docs/ARCHITECTURE.md` for the design rules and the commands that regenerate every number.

## Known limitations

- The deployed fusion gives the OCT scan 20% weight. That weight was set after looking at the (optimistic) sweep, as a conservative choice; the data show the scan adds no reliable value.
- The GAMMA live demo serves single-split checkpoints, not the cross-validation models.
- Sample cases on the Glaucoma page come from the development cohort, so they were seen during training.
- The final OCT and clinical models were trained on all 303 eyes; reported accuracy comes from the cross-validation, not from them.
- Small cohort: Moderate (47) and Severe (38) eyes are few, so per-class results are uncertain.
- The API has no authentication and CORS is limited to localhost.

## Getting the data and weights (not in this repository)

The repo holds code, results and docs only. These are deliberately left out:

- `data/research/` — the Sankara OCT scans and clinical Excel (patient data; obtain from the data owner).
- `frontend/public/samples/oct-*.jpg` — four real patient scans used as UI samples.
- `models/` — `oct_research.pt` (re-create with `train_oct.py --final resnet18`), `clinical_*.joblib` (re-create with `train_clinical.py`).
- `ml/gamma/checkpoints/` — MM-RETINA demo checkpoints.
- `backend/dipp/models/`, `backend/dipp/saved_model/` — Kartik's two HbA1c `.keras` models and the vessel U-Net.

Without them the API starts and reports those services as unavailable in `/api/health`; the pages that need them show that state.
