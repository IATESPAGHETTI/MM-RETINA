# Codex frontend status

## 2026-11-22

Frontend branch `feat/suite-frontend`, based on `suite-contract-v1`.
Local frontend runs on port 3100 and uses the Retina Suite backend on port 8001.

- Added default GAMMA comparison, three versioned model cards, agreement,
  illustrative specialist-review flag, semicircular model-score gauge, and
  the fundus Grad-CAM toggle. The viewer supports eight ordered uploaded
  slices and all 256 slices of the bundled sample. Inference on the sample
  uses eight distinct slices.
- Added study-ID validation and autocomplete, save actions on all three
  module result pages, the patient directory and timeline with a confidence
  sparkline, recent cases, and the existing browser history fallback.
- Wired both PDF endpoints, the provider-labeled explanation card, and the
  batch ZIP workflow with sortable results, per-case errors, review
  highlighting, save-to-patients, and CSV export.
- Workspace results, saved explanations, and batch results carry research
  disclaimers. Diabetes stays experimental. No new npm dependencies.

## Verification

- `npm run lint`, `npx tsc --noEmit`, and `npm run build` pass.
- Exercised the frontend API client against the real port-8001 backend:
  three-model comparison with eight slices and single-slice fallback, a
  wrong-slot 400 and backend error text, Grad-CAM, health and CORS,
  study-ID validation and saved case lookup, patient search and trend,
  stored explanations, both PDF responses, and a three-case batch with two
  successes, one error, patient saving, and CSV. DeepSeek returned a real
  response for a bundled sample with only model outputs in the request.
- Browser checks at a 390 px viewport confirmed the sample keyboard
  scrubber, three live results, the Grad-CAM toggle, invalid study-ID
  handling, persistence of a saved case and explanation after reload, and
  the three-case ZIP results. The batch table scrolls within its panel.
  Eight-slice upload order and report/CSV downloads were also checked
  through the frontend API client. The browser did not confirm every
  download event before its continuation expired.
- Experimental diabetes returned the expected backend 503 for unloaded
  models. This verified the unavailable path. A successful diabetes result
  still needs the diabetes runtime and weights on the backend.

## Contract requests

None. The frozen contract supported the frontend implementation.
