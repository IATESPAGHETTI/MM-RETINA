# MM-RETINA inference backend

A small FastAPI service that loads the actual trained checkpoints from
`../training/checkpoints/` once at startup and serves real predictions for
the website's `/demo` page. It does not reimplement preprocessing or the
model architecture — `inference.py` imports directly from
`../training/data.py` (transforms, class names) and `../training/evaluate.py`
(checkpoint loading), the same code the CV/single-split experiments used.

**These are not the 5-fold CV checkpoints.** This service serves
`fundus_run1.pt`/`oct_run1.pt`/`fusion_run1.pt`, the demonstration
checkpoints from the earlier single-split experiments (`EXPERIMENTS.md`).
The performance numbers on the website's `/results` page come from a
*separate* 5-fold cross-validation experiment (`training/cross_validate.py`,
`results/cv/`) whose 15 fold checkpoints were intentionally not retained
(see `--keep-checkpoints` in that script if you want to change that). Do
not present a live-demo prediction as evidence for the CV metrics, or vice
versa — they're different trained instances of the same architecture.

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
| `oct` | if modality is `oct` or `fusion`, and `oct_slices` isn't sent | single image, repeated across the model's expected slice count (fallback — see below) |
| `oct_slices` | if modality is `oct` or `fusion`, and `oct` isn't sent | multiple files, real ordered B-scan slices — must contain exactly as many as the loaded checkpoint expects (8 for the checkpoints here); real volume, no repetition |
| `explain` | no | `true` to also compute a real Grad-CAM heatmap for the fundus branch (only meaningful when a fundus image is provided) |

Example (single-slice fallback):

```bash
curl -X POST http://localhost:8000/api/predict \
  -F "modality=fusion" \
  -F "fundus=@../website/public/demo/fundus/gamma-0001.jpg" \
  -F "oct=@../website/public/demo/oct/gamma-0001-slice128.jpg"
```

Example (real 8-slice volume + explanation):

```bash
B=../website/public/oct-volume/0001
curl -X POST http://localhost:8000/api/predict \
  -F "modality=fusion" \
  -F "fundus=@../website/public/demo/fundus/gamma-0001.jpg" \
  -F "oct_slices=@$B/000.jpg" -F "oct_slices=@$B/036.jpg" -F "oct_slices=@$B/073.jpg" \
  -F "oct_slices=@$B/109.jpg" -F "oct_slices=@$B/146.jpg" -F "oct_slices=@$B/182.jpg" \
  -F "oct_slices=@$B/219.jpg" -F "oct_slices=@$B/255.jpg" \
  -F "explain=true"
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
  "oct_mode": "real_volume",
  "fundus_heatmap": "data:image/png;base64,..."
}
```

`prediction`/`probabilities` keys come from `training/data.py`'s
`GRADE_NAMES` — they are not hardcoded in the backend. `oct_mode` is
`"real_volume"`, `"repeated_single_slice"`, `"none"`, or `"n/a"` (fundus
modality — no OCT input at all) — never conflated. `fundus_heatmap` is
`null` unless `explain=true` was sent and a fundus image was provided.

Errors return a normal HTTP status (400/413/503/500) with a `detail`
string — never a stack trace, and never a 200 with a fabricated result.

### `GET /api/health` is the only way to know if a model is really loaded

Do not assume `/api/predict` will work just because the server is up —
check `/api/health` first (the frontend does this on page load).

## OCT input: real volume vs. single-slice fallback

The trained models expect a short sequence of OCT B-scan slices (8,
sampled evenly from a real 256-slice volume during training via
`training/data.py`'s `evenly_spaced_indices(256, 8)` ==
`[0, 36, 73, 109, 146, 182, 219, 255]`). Two modes:

- **Real volume** (`oct_slices` field, `oct_mode: "real_volume"`) — the
  caller supplies exactly 8 real, ordered B-scan images. These are
  stacked as-is, matching training/CV semantics exactly. The website's
  "Demo (real 8-slice volume)" button sends GAMMA sample 0001's actual
  slices at the exact 8 indices above, already served at
  `website/public/oct-volume/0001/`.
- **Single-slice fallback** (`oct` field, `oct_mode: "repeated_single_slice"`)
  — one image repeated across all 8 slice positions. Still a real forward
  pass through the real trained model, just not equivalent to a real
  volume. Used for an arbitrary user-uploaded single image, where a real
  8-slice volume for that image doesn't exist.

## Grad-CAM (fundus branch only)

`explain=true` runs a real Grad-CAM (Selvaraju et al. 2017) forward+backward
pass hooking the fundus encoder's last conv block (`layer4` of the timm
resnet18 backbone) and returns a heatmap overlay as a base64 PNG data URL
in `fundus_heatmap`. See `gradcam.py`'s module docstring for exactly how,
and for why this is implemented for the fundus branch only:

- Fundus is a standard single-image CNN path — the textbook Grad-CAM case,
  verified against a real image (heatmap correctly highlighted the optic
  disc region on GAMMA sample 0001, the anatomically relevant structure
  for glaucoma assessment).
- OCT shares one backbone across 8 slices combined via learned attention
  pooling before the classifier. A per-slice Grad-CAM is architecturally
  plausible, but attributing "importance" through an attention-pooled
  multi-instance aggregation is a meaningfully different and less
  established claim than single-image Grad-CAM. **Deferred as a future
  enhancement** rather than shipped without enough validation time to be
  confident it isn't misleading — not because it's known to be invalid,
  but because it wasn't verified to the same standard as the fundus case.

`explain=true` is a no-op (not an error) when modality is `oct` or no
fundus image was given — nothing to explain in that case.

## Logging

Every request logs a short id, modality, whether each image/slice-set was
present, and either a success line (prediction/confidence/timing/oct_mode)
or a failure line with the exception — never the image bytes themselves.
Model load status/errors are logged once at startup.

## What's NOT implemented here

- No persistence of uploaded images (processed in memory, never written
  to disk, nothing to clean up).
- No auth — this is a local research demo, not a public deployment.
- No OCT Grad-CAM/attribution (see above — deferred, not abandoned).
- No Docker packaging (discussed with the user, deferred as unnecessary
  for the current localhost-only scope).
