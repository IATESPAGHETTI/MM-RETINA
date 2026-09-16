# MM-RETINA inference backend

A small FastAPI service that loads the actual trained checkpoints from
`../training/checkpoints/` once at startup and serves real predictions for
the website's `/demo` page. It does not reimplement preprocessing or the
model architecture — `inference.py` imports directly from
`../training/data.py` (transforms, class names) and `../training/evaluate.py`
(checkpoint loading), the same code the CV/single-split experiments used.

## Setup

```bash
cd backend
pip install -r requirements.txt
```

`requirements.txt` lists plain `torch`/`torchvision`. If you want GPU
acceleration and pip resolves a CPU-only wheel by default on your platform,
install the CUDA build first per
[pytorch.org's instructions](https://pytorch.org/get-started/locally/) for
your CUDA version (this project was built/tested against
`torch==2.5.1+cu121` on an RTX 3060), then run the requirements install —
pip will leave an already-satisfied `torch` alone.

Copy `.env.example` to `.env` if you need a CORS origin other than
`http://localhost:3000` (the Next dev server default).

## Model files expected

```
training/checkpoints/
  fundus_run1.pt
  oct_run1.pt
  fusion_run1.pt
```

These are the checkpoints from the single-split experiments in
`EXPERIMENTS.md` (not the 5-fold CV runs — those checkpoints were
intentionally not retained; see `training/cross_validate.py`'s
`--keep-checkpoints` flag if you want to keep a CV fold's checkpoint for
demo use instead). If a checkpoint is missing, that modality is reported
as unavailable in `/api/health` and returns HTTP 503 from `/api/predict`
— it will not silently fall back to a fake prediction.

## Run

```bash
uvicorn app:app --reload --port 8000
```

## Endpoints

### `GET /api/health`

```json
{
  "status": "ok",
  "models_loaded": ["fundus", "fusion", "oct"],
  "model_errors": {},
  "device": "cuda"
}
```

A modality only appears in `models_loaded` if its checkpoint actually
loaded successfully; otherwise it appears in `model_errors` with the real
exception message.

### `POST /api/predict`

Multipart form:

| Field | Required | Notes |
|---|---|---|
| `modality` | yes | one of `fundus`, `oct`, `fusion` |
| `fundus` | if modality is `fundus` or `fusion` | JPEG/PNG/WEBP, max 10MB |
| `oct` | if modality is `oct` or `fusion` | JPEG/PNG/WEBP, max 10MB |

Example:

```bash
curl -X POST http://localhost:8000/api/predict \
  -F "modality=fusion" \
  -F "fundus=@../website/public/demo/fundus/gamma-0001.jpg" \
  -F "oct=@../website/public/demo/oct/gamma-0001-slice128.jpg"
```

Response:

```json
{
  "success": true,
  "request_id": "e8657fc7",
  "modality": "fusion",
  "prediction": "normal",
  "confidence": 0.7386,
  "probabilities": { "normal": 0.7386, "early": 0.2104, "progressive": 0.0511 },
  "inference_time_ms": 63.12,
  "model_version": "fusion_run1",
  "oct_repeated_single_slice": true
}
```

`prediction`/`probabilities` keys come from `training/data.py`'s
`GRADE_NAMES` — they are not hardcoded in the backend.

Errors return a normal HTTP status (400/413/503/500) with a `detail`
string — never a stack trace, and never a 200 with a fabricated result.

### `GET /api/health` is the only way to know if a model is really loaded

Do not assume `/api/predict` will work just because the server is up —
check `/api/health` first (the frontend does this on page load).

## Known limitation: single OCT image, not a real volume

The trained models expect a short sequence of OCT B-scan slices (8,
sampled evenly from a real 256-slice volume during training — see
`training/data.py`). The live demo only accepts one OCT image, which
`inference.py` repeats across all 8 slice positions to match the model's
input shape. This is a real forward pass through the real trained model
on a real (if repeated) input — genuinely not a fabricated prediction —
but it is not equivalent to running the model on an actual multi-slice
volume the way the CV experiments did. The API response flags this via
`oct_repeated_single_slice: true`, and the frontend surfaces it in the
result text. A future improvement would accept multiple OCT slice uploads
(or a small volume file) instead of one image.

## Logging

Every request logs a short id, modality, whether each image was present,
and either a success line (prediction/confidence/timing) or a failure
line with the exception — never the image bytes themselves. Model load
status/errors are logged once at startup.

## What's NOT implemented here

- No persistence of uploaded images (processed in memory, never written
  to disk, nothing to clean up).
- No auth — this is a local research demo, not a public deployment.
- No Grad-CAM/explainability endpoint yet (see `PROGRESS.md`'s "Next
  action" list at the repo root).
