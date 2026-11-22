# Claude status (backend)

Branch `feat/suite-backend` (worktree `.claude\worktrees\suite-backend`). Contract tag: `suite-contract-v1`.
Codex: read this file for what is real (named backend-status.md because a file called claude.md is auto-loaded as instructions). Request contract changes in `docs/status/codex.md`, not here.

## Done and verified against the real running backend (28 integration checks, 17 unit tests)

| Feature | Endpoint(s) | Verified |
|---|---|---|
| Model comparison | `POST /api/glaucoma/compare` | real GAMMA samples: 3 models, agreement banner, review flag, risk band, Grad-CAM; 400 for wrong slice count, OCT in fundus slot, missing OCT; single-slice fallback |
| Explain (DeepSeek) | `POST /api/explain` | real provider call (`source: deepseek`, ~1.5 s); falls back to `template` on no key, bad key (401), unreachable host; 429 rate limit; only whitelisted numbers are sent |
| Cases and patients | `/api/cases`, `/api/patients` | create/list/search/get/delete, trend, cascade delete; names rejected with 422; images stripped from `detail` |
| PDF | `GET /api/cases/{id}/report.pdf`, `POST /api/report.pdf` | opened and checked visually: one page, probability bars, flags, explanation, Grad-CAM, disclaimer |
| Batch | `POST /api/batch`, `GET /api/batch/{id}.csv` | 4-case ZIP gives 2 ok and 2 explained errors; single `oct.jpg` accepted; `save=true` stores patients; path traversal, corrupt and non-ZIP rejected; CSV formula injection neutralised |
| Health | `GET /api/health` | `services.extras = {store:{ready}, explain:{configured, provider, model}}` |

## How to run

```powershell
cd C:\Users\ASUS\Downloads\prj4\.claude\worktrees\suite-backend\past_work\RETINA\newmix\backend
python -m uvicorn app:app --port 8001      # 8000 is held by the older demo backend; do not use it
```

- Needs `backend/.env` with `DEEPSEEK_API_KEY` (git-ignored; copy `.env.example`). Without it, explain uses the template.
- Git-ignored model/data folders are junctions to the main checkout (`models`, `data`, `ml/gamma/checkpoints`, `frontend/public/samples`).
- CORS allows `localhost:3000` and `:3100`, methods GET, POST, DELETE.

## Things to know (not bugs, but they affect the UI)

- `compare` and `batch` run the **single-split** checkpoints (`fundus_run1`, `oct_run1`, `fusion_run1`), not the 5-fold CV models. Show `caveat`.
- The 0.60 review threshold and the risk bands (low below 0.35, high from 0.65) are illustrative, not validated. Label them so.
- `batch` is synchronous (about 0.3 s per case). A 100-case ZIP means a long spinner; the limit is 100 cases and 150 MB.
- Explain is rate limited to 30 requests per minute per process (429).
- Keras is not installed in this Python, so `services.diabetes` is not ready in `/api/health`. Expected here; unrelated to the extras.
- `tests/smoke_test.py` (the original) cannot finish on this machine: it needs Sankara OCT sample images that are not in the checkout. The extras have their own `tests/smoke_extras.py`.

## Not done

- No authentication (none was asked for).
- No automatic cleanup of old batch results in SQLite.
- Nothing has been pushed or merged.
