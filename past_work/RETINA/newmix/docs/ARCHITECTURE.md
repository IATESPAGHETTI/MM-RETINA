# Architecture

Three projects, one product.

| Origin | Brought into newmix as |
|---|---|
| **RETINA** (Kartik): diabetes, vessel segmentation, fractal, HbA1c | `backend/services/diabetes_service.py` + `backend/dipp/` (his models and preprocessing, unchanged) |
| **Research** (Dashita): Sankara OCT + clinical Excel, the paper | `ml/glaucoma/` (data loader, clinical models, OCT model, fusion) + `data/research/` |
| **MM-RETINA** (yours): GAMMA multimodal grading, website | `ml/gamma/` (training code + checkpoints), `backend/services/_gamma/` (inference), `frontend/` (design system and pages) |

```
Browser ── Next.js 16 (frontend/) ──HTTP──> FastAPI (backend/app.py)
                                              ├─ routers/glaucoma.py  ─ services/oct_service.py      (Research OCT, Grad-CAM)
                                              │                       ─ services/clinical_service.py (Research Excel features)
                                              │                       ─ services/gamma_service.py    (GAMMA fundus + OCT volume)
                                              ├─ routers/diabetes.py  ─ services/diabetes_service.py (Kartik)
                                              └─ routers/system.py    ─ reads ml/results/*.json (health, model cards, audit)
```

## Design rules

1. **Services never import FastAPI.** They take PIL images / dicts and return dicts, so they can be tested and scripted without a server.
2. **The UI shows only numbers that exist on disk.** `/api/models` and `/api/audit` read JSON written by the training and audit scripts; nothing is typed into the frontend.
3. **One module failing must not take the rest down.** Each service loads independently at startup and reports `ready` / `error` in `/api/health`; the UI greys out what is unavailable.
4. **Patient-grouped evaluation everywhere.** Both eyes of a patient are always in the same fold; the three models share fold assignments so their out-of-fold predictions can be fused honestly.
5. **No silent features.** Visual-field MD is excluded from model inputs (it defines the label); Pachy/CFT are excluded (missingness leaks the label). See `docs/DATA_AUDIT.md`.

## Why no login

Removed on request for the prototype. The API has CORS limited to localhost and no authentication; add one before exposing it.

## Why no TensorFlow

Kartik's `.keras` files were saved with Keras 3.5 and use only standard layers, so they run on Keras's torch backend (`KERAS_BACKEND=torch`). The port was checked against real TensorFlow 2.18 on identical preprocessed inputs: outputs differ by at most 0.014 and every predicted class is identical.

## Reproducing the numbers

```
python ml/glaucoma/audit_data.py --sankara <retinal-imaging-research dir> --hvf-csv <hvf_features.csv>
python ml/glaucoma/train_clinical.py          # clinical ablations + final models
python ml/glaucoma/train_oct.py --archs resnet18,hybrid,efficientnet_b0 --epochs 30 --seeds 42,43,44
python ml/glaucoma/oct_probe.py               # frozen-feature baseline
python ml/glaucoma/train_oct.py --archs "" --final <arch> --epochs 30   # final ensemble -> models/oct_research.pt
python ml/glaucoma/eval_fusion.py resnet18   # fusion + patient bootstrap
python ml/glaucoma/run_paper.py tune          # paper architecture: inner-validation tuning
python ml/glaucoma/run_paper.py cv --seeds 42 # paper architecture: patient-grouped CV (~1 h on a 6 GB GPU)
python ml/glaucoma/run_paper.py leaky --seeds 42 --epochs 10  # leakage test
python ml/glaucoma/make_defer.py              # deferral cut-offs (needs the OOF files above)
python ml/results/make_gamma_summary.py <MM-RETINA results dir>
```
