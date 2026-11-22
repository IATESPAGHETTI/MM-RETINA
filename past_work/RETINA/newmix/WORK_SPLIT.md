# Retina Suite extras: work split between Claude and Codex

Goal: turn the Retina Suite into a demo-able product with six visible features.
Claude builds the **backend**. Codex builds the **frontend**. They meet at the
API contract below, which is frozen in this file's first commit.

| # | Feature | Backend (Claude) | Frontend (Codex) |
|---|---|---|---|
| 1 | Live model comparison + agreement banner + needs-review flag + risk gauge | `POST /api/glaucoma/compare` | comparison panel on `/workspace/glaucoma/multimodal` |
| 2 | OCT scan scrubber in the workspace | none | reuse `components/OCTViewer.tsx` + uploaded-slice scrubber |
| 3 | Saved patients (study IDs only), history, search | `/api/cases`, `/api/patients` (SQLite) | `/workspace/patients`, `/workspace/patients/[id]`, "Save to patient" |
| 4 | PDF report | `GET /api/cases/{id}/report.pdf`, `POST /api/report.pdf` | download buttons |
| 5 | Batch ZIP upload + CSV | `POST /api/batch`, `GET /api/batch/{id}.csv` | `/workspace/batch` |
| 6 | Plain-language explanation (DeepSeek) | `POST /api/explain` (template fallback) | "Explain this result" card |

## Ownership (this is what prevents merge conflicts)

| Area | Owner | The other agent may |
|---|---|---|
| `backend/**`, `tests/**`, `docs/**`, `README.md`, `WORK_SPLIT.md` | **Claude** | read only. Ask for changes via `docs/status/codex.md` |
| `frontend/**` | **Codex** | read only. Ask for changes via `docs/status/claude.md` |
| API contract (this file, section "API contract") | **Claude** | propose changes only; Claude amends and says so in its status file |

Each agent writes progress to its **own** status file (`docs/status/claude.md`,
`docs/status/codex.md`). Never edit the other agent's file; that is how two
branches end up conflicting.

## Git workflow

- Base commit for both branches: the first commit of `feat/suite-backend`
  (the one that adds this file). Codex: `git worktree add .worktrees/suite-frontend -b feat/suite-frontend feat/suite-backend~0`
  taken **at that commit** (use its SHA if the branch has moved).
- Claude works in `.claude/worktrees/suite-backend` on `feat/suite-backend`.
  Codex works in `.worktrees/suite-frontend` on `feat/suite-frontend`.
- **Do not push, and do not merge into `main`, without the owner's explicit
  approval.** The owner merges both branches (backend first).
- Never `git add .` or `git add -A`. Stage explicit paths. Never commit a
  `.env`, a model weight, a scan, or the SQLite file.
- No new dependency without saying so in your status file. Claude adds nothing
  to `requirements.txt` beyond `reportlab`. Codex adds none to `package.json`
  unless truly needed (prefer plain SVG/CSS over a chart library).

## Running it locally (Windows / PowerShell)

Fresh worktrees do not contain the git-ignored model files. Link them from the
main checkout (junctions, no copying):

```powershell
$src = "C:\Users\ASUS\Downloads\prj4\past_work\RETINA\newmix"
$dst = "<your worktree>\past_work\RETINA\newmix"
foreach ($rel in "models","data","ml\gamma\checkpoints") {
  if (-not (Test-Path "$dst\$rel")) { New-Item -ItemType Junction -Path "$dst\$rel" -Target "$src\$rel" | Out-Null }
}
```

- **Backend** (Claude's worktree): `cd backend; python -m uvicorn app:app --port 8000`.
  Codex should point at it; if it is not running, start your own on `:8001`.
  CORS already allows `:3000` and `:3100`.
- **Frontend** (Codex): `cd frontend; npm install; $env:NEXT_PUBLIC_API_URL="http://localhost:8000"; npm run dev -- -p 3100`.
- Keras is not installed in this Python, so the diabetes module reports "not
  loaded" in `/api/health`. That is expected; do not "fix" it.
- 6 GB GPU shared with other jobs: run **one** backend at a time.

## API contract

General: JSON in and out unless stated. Errors are `{"detail": "<message>"}` with
a 4xx/5xx status (already how `frontend/src/lib/api.ts` parses them). Timestamps
are ISO-8601 UTC strings. Probabilities are `{"normal": 0.0, "early": 0.0, "progressive": 0.0}`
and sum to about 1. `DISCLAIMER` text is the same string the existing
`/api/glaucoma/multimodal` returns; show it wherever a result or explanation is shown.

### 1. Compare: `POST /api/glaucoma/compare` (multipart)

Fields: `fundus` (file, required), and **either** `oct_slices` (exactly 8 files,
in order) **or** `oct` (one file). `explain` (bool, default false) adds the
fundus Grad-CAM. Runs the fundus-only, OCT-only and fusion checkpoints on the
same input.

```json
{
  "success": true,
  "models": {
    "fundus": {"prediction": "early", "confidence": 0.61, "probabilities": {"normal": 0.30, "early": 0.61, "progressive": 0.09}, "inference_time_ms": 41.2, "model_version": "fundus_run1"},
    "oct":    {"prediction": "normal", "confidence": 0.52, "probabilities": {"normal": 0.52, "early": 0.33, "progressive": 0.15}, "inference_time_ms": 38.0, "model_version": "oct_run1"},
    "fusion": {"prediction": "early", "confidence": 0.48, "probabilities": {"normal": 0.41, "early": 0.48, "progressive": 0.11}, "inference_time_ms": 63.5, "model_version": "fusion_run1"}
  },
  "agreement": {"all_agree": false, "n_agree": 2, "majority": "early", "outliers": ["oct"], "banner": "2 of 3 models agree on early; oct disagrees"},
  "needs_review": {"flag": true, "reasons": ["models disagree", "low fusion confidence (0.48 < 0.60)"], "confidence_threshold": 0.6},
  "risk": {"score": 0.59, "level": "elevated", "basis": "1 - P(normal) from the fusion model", "note": "Model-score band for display; not a clinical risk estimate."},
  "oct_mode": "real_volume",
  "fundus_heatmap": "data:image/png;base64,...",
  "caveat": "Single-split demonstration checkpoints, not the 5-fold CV models.",
  "disclaimer": "Research prototype for decision support..."
}
```

- `agreement.majority` is `null` and `outliers` is `[]` when all three differ; `banner` then reads "all three models disagree".
- `risk.level`: `low` below 0.35, `elevated` below 0.65, else `high`. The threshold 0.60 for review is **illustrative, not a validated operating point**; label it that way in the UI.
- 400 for bad uploads (wrong slot, wrong slice count), 503 if any of the three models failed to load.

### 2. Cases and patients (SQLite, study IDs only)

`study_id` must match `^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$` (no names, no dates of
birth: the API rejects anything else with 422). No images are ever stored: the
server drops any `heatmap`, `*_preview`, `overlay` key and any string starting
with `data:image` from `detail`.

`module` is one of `"glaucoma"`, `"diabetes"`, `"multimodal"` (same values as `RunRecord` in `lib/history.ts`).

| Method and path | Body or query | Returns |
|---|---|---|
| `POST /api/cases` | `{patient_id, module, title, result, confidence?, inputs?, detail?, explanation?}` | the created case (201). Creates the patient if new |
| `GET /api/cases` | `patient_id?`, `q?`, `module?`, `limit?`(<=200, default 50), `offset?` | `{"items": [case, ...], "total": n}` (list items omit `detail`) |
| `GET /api/cases/{id}` | | full case, including `detail` and `explanation` |
| `DELETE /api/cases/{id}` | | `{"deleted": id}` |
| `GET /api/patients` | `q?` | `[{"study_id","case_count","last_case_at","last_result","last_module"}]` |
| `GET /api/patients/{study_id}` | | `{"study_id","created_at","cases":[case...newest first],"trend":[{"at","module","result","confidence"}...oldest first]}` |
| `DELETE /api/patients/{study_id}` | | `{"deleted": study_id, "cases_deleted": n}` |

Case shape: `{"id": 12, "patient_id": "P-014", "module": "multimodal", "title": "GAMMA fusion", "result": "early", "confidence": 0.48, "inputs": "fundus + 8 OCT slices", "detail": {...}, "explanation": "...", "created_at": "..."}`.
`DELETE` is now in the CORS allowed methods.

### 3. PDF report

- `GET /api/cases/{id}/report.pdf`: report built from the stored case (no images).
- `POST /api/report.pdf`: stateless, nothing stored. JSON body: the case fields above (without `id`) plus optional `probabilities` (map), `flags` (list of strings) and `fundus_heatmap` (a `data:image/...;base64,` URL, at most 2 MB). Use this one from a fresh result page so the Grad-CAM can be included.
- Both return `application/pdf` with `Content-Disposition: attachment`. In the browser: `fetch` then `blob()` then an object URL.

### 4. Batch: `POST /api/batch` (multipart)

Fields: `file` (ZIP, at most 150 MB), `save` (bool, default false: when true each
case is stored under its folder name as the study ID). Only the GAMMA
multimodal module is supported. Layout inside the ZIP, one folder per case:

```
P-001/fundus.jpg
P-001/oct/00.jpg ... 07.jpg      (8 slices, sorted by file name)   OR   P-001/oct.jpg  (one B-scan)
P-002/...
```

At most 100 cases; files are read in memory, never extracted to disk. The call
is synchronous (about 0.3 s per case), so show a spinner.

```json
{"batch_id": "b_9f2c...", "n_cases": 3, "n_ok": 2, "n_error": 1,
 "items": [
  {"study_id": "P-001", "status": "ok", "fusion_prediction": "early", "fusion_confidence": 0.48,
   "probabilities": {"normal": 0.41, "early": 0.48, "progressive": 0.11},
   "fundus_prediction": "early", "oct_prediction": "normal", "all_agree": false, "needs_review": true, "risk_level": "elevated"},
  {"study_id": "P-002", "status": "error", "error": "oct: expected 8 slices, got 5"}
 ]}
```

`GET /api/batch/{batch_id}.csv` returns `text/csv` with columns
`study_id,status,error,fusion_prediction,fusion_confidence,p_normal,p_early,p_progressive,fundus_prediction,oct_prediction,all_agree,needs_review,risk_level`.

### 5. Explain: `POST /api/explain`

```json
{"summary": {"module": "multimodal", "prediction": "early", "confidence": 0.48,
             "probabilities": {"normal": 0.41, "early": 0.48, "progressive": 0.11},
             "models": {"fundus": "early", "oct": "normal", "fusion": "early"},
             "agreement": {"all_agree": false}, "needs_review": {"flag": true, "reasons": ["models disagree"]},
             "risk": {"score": 0.59, "level": "elevated"}, "drivers": [{"feature": "RNFL inferior", "direction": "lowers risk"}]}}
```

Response: `{"explanation": "...", "source": "deepseek" | "template", "model": "deepseek-chat" | null, "disclaimer": "..."}`.

- Only these numbers are sent to the provider: **never images, never the study ID**. Free-text strings over 200 characters and unknown keys are dropped.
- The server appends the disclaimer itself; do not rely on the model to include it.
- With no key, a provider error or a timeout (20 s) the server returns a deterministic **template** explanation with `source: "template"`. The UI must show which one it got (a small badge) and a visible "AI-generated, not medical advice" label.
- 30 requests per minute per process, then 429.

### 6. Health additions

`GET /api/health` gains `services.extras = {"store": {"ready": true}, "explain": {"configured": true, "provider": "deepseek", "model": "deepseek-chat"}}`. Use it to grey out the explain button when `configured` is false (the template fallback still works, so the button may stay enabled).

## Frontend deliverables (Codex), with acceptance checks

1. **Comparison panel.** On the multimodal page, a default "Compare all models" mode: three cards (probability bars, prediction, confidence, latency), an agreement banner using `agreement.banner`, a "Needs specialist review" chip with the reasons, a semi-circular risk gauge from `risk.score`, and the Grad-CAM toggle. Check: upload the shipped samples and see all four elements; wrong-slot upload shows the backend message.
2. **OCT scrubber.** Slider through the uploaded 8 slices (and through the 256-slice sample via the existing `OCTViewer`). Check: keyboard arrows work; no layout shift.
3. **Patients.** "Save to patient" on every module result (study-ID field with live validation against the regex above and autocomplete from `GET /api/patients`), `/workspace/patients` (search, empty state), `/workspace/patients/[id]` (timeline, small trend sparkline in plain SVG, per-case report button). Keep the existing localStorage history as the fallback when the API is unreachable. Check: refresh the page and the data is still there.
4. **PDF buttons** on result pages (use `POST /api/report.pdf`) and on patient history (use `GET .../report.pdf`).
5. **Batch.** `/workspace/batch`: drag-and-drop ZIP, a short layout help block, results table (sortable, needs-review rows highlighted, per-row error text), "Download CSV", and a "save to patients" checkbox. Check: a 3-case ZIP with one broken case shows 2 ok and 1 error.
6. **Explanation card.** "Explain in plain language" button, loading state, text, a `deepseek`/`template` badge, and the always-visible "AI-generated, not medical advice" line. When the result is saved, send the text as `explanation`.
7. **Navigation and polish.** Add Patients and Batch to `components/workspace/Shell.tsx`; recent saved cases on the overview page; loading, empty and error states everywhere; usable at 390 px width.
8. **Types.** Add the new response types and client functions to `lib/api.ts`.

Definition of done for Codex: `npm run lint`, `npx tsc --noEmit` and `npm run build` pass, and each check above was exercised against the real backend (not only mocks).

## Backend deliverables (Claude), with acceptance checks

1. `settings.py` env loader (no new dependency), `services/explain_service.py`, `routers/explain.py`. Check: real DeepSeek call succeeds; with the key removed the template path returns 200.
2. `services/compare_service.py`, `routers/compare.py`. Check: the three-model response above for the shipped samples; 400 and 503 paths.
3. `services/store.py` (SQLite, standard library), `routers/cases.py`. Check: study-ID regex, image-stripping, cascade delete.
4. `services/report_service.py` (reportlab). Check: PDF opens, includes disclaimer, no patient identifiers beyond the study ID.
5. `services/batch_service.py`, `routers/batch.py`. Check: path-traversal names (`../x`), oversized and corrupt ZIPs are rejected cleanly.
6. Tests: pure-function unit tests plus new sections in `tests/smoke_test.py`; README and `docs/ARCHITECTURE.md` updated.

## Safety and honesty rules (both agents)

- This is a **research prototype, not a medical device**. Keep the disclaimer visible on results, reports and explanations.
- The live GAMMA endpoints serve the early **single-split** checkpoints (64.3% accuracy on 14 test cases), not the 5-fold CV models. The comparison panel must show the `caveat` text.
- The diabetes module stays labeled **experimental** (HbA1c has no validation, see README).
- Study IDs only. No names, dates of birth, or free-text notes are collected anywhere.
- No login: it was removed on request. Do not add one unless the owner asks.
- The DeepSeek key lives only in `backend/.env` (git-ignored). Never print it, log it, put it in a URL, or commit it.
- The bundled sample images come from the GAMMA dataset, whose license limits redistribution. Do not deploy this app publicly with them before the owner checks `License-GAMMA_1019.pdf`.
- Log failures in your status file; do not hide a broken feature.
