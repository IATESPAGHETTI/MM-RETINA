# MM-RETINA website

Premium marketing/research site for the multimodal (OCT + fundus) glaucoma
grading project. Next.js 16 (App Router, Turbopack) + TypeScript + Tailwind
CSS v4 + Framer Motion.

## Run it

```bash
npm install
cp .env.local.example .env.local   # points the site at the inference backend
npm run dev
```

Then open http://localhost:3000. For `/demo` to actually run inference,
also start the backend — see `../backend/README.md`.

## Structure

- `src/app/` — pages: `/` (landing), `/model`, `/dataset`, `/results`, `/model-card`, `/research`, `/research/journey`, `/about`, `/demo`.
- `src/components/` — `Navbar`, `Hero`, `WhyMultimodal`, `ArchitecturePipeline`
  (animated SVG pipeline diagram), `OCTViewer` (real, interactive B-scan
  slider), `DatasetFacts`, `ResultsPreview`, `AblationTable`,
  `ResearchIntegrity`, `GlassCard`, `Reveal` (scroll-triggered motion
  wrapper), `DemoBadge`.
- `src/lib/content.ts` — page copy: `VERIFIED_*` (official GAMMA/GRAPE
  dataset facts), `SINGLE_SPLIT_HISTORY` (the qualitative story of the
  earlier, superseded single-split experiment).
- `src/lib/results.ts` + `results.generated.json` — cross-validation
  metrics. The JSON is **generated** from `../results/**/summary.json` by
  `python ../scripts/export_site_results.py` (CI runs it with `--check`), so
  nothing is hand-copied. Re-run it after any new experiment. There is no
  static demo-prediction data — `/demo` calls the real backend.
- `src/components/demo/AnalysisReport.tsx` — the demo's result report
  (probability bars, margin heuristic, Grad-CAM, print/copy).

## Design language

"Warm Titanium" — warm charcoal background, ivory text, champagne/olive/copper
accents (see `src/app/globals.css` for the `--bg`, `--accent-champagne`,
`--accent-olive`, `--accent-copper` tokens). Glass (`.glass` / `.glass-strong`)
is reserved for the floating navbar and small status overlays, not general
section backgrounds. Respects `prefers-reduced-motion`.

## Real imagery

Both the fundus photo and the OCT B-scans on this site are real, unmodified
GAMMA dataset content (training sample 0001), used under the dataset's
CC BY-NC-ND terms — see `../dataset/README.md` for the full license/citation.

- `public/samples/gamma-0001-fundus.jpg` — the real color fundus photograph.
- `public/oct-volume/0001/000.jpg` … `255.jpg` — all 256 real B-scans from
  that sample's actual OCT volume (used by `OCTViewer.tsx` on `/model`,
  lazy-loaded — only the current slice plus a small prefetch window, never
  the whole volume at once).
- `public/demo/fundus/gamma-0001.jpg` and `public/demo/oct/gamma-0001-slice128.jpg`
  — copies of the same real, matched pair, used as the "Select demo" option
  on `/demo`. See `../demo_images/` for provenance notes.

## What's real vs. what to know about

- Dataset facts are sourced from the official GAMMA dataset card/paper.
- `/results` shows real 5-fold cross-validation metrics for the frozen best
  model, the full six-experiment ablation ladder (with rejected results), and
  the original modality ablation. An earlier single-split experiment's numbers
  are intentionally not redisplayed (see `SINGLE_SPLIT_HISTORY` in content.ts)
  but remain in `EXPERIMENTS.md`/git history.
- `/demo` calls a real FastAPI backend (`../backend/`) running the actual
  trained checkpoints. It is not mocked — if the backend is down, the page
  says so and disables the run button rather than faking a result.
- The live demo serves earlier single-split checkpoints (`fusion_run1`), not
  the EfficientNet-B0 model behind the headline metrics. Disclosed on `/demo`,
  `/model-card` and in `../backend/README.md`.
- A single uploaded OCT image is repeated across the model's 8 slice
  positions; the bundled sample uses a real 8-slice volume. The API reports
  which one was used (`oct_mode`).

## Next steps if extending this

1. OCT-branch attribution (deferred, see `../backend/README.md`).
2. Paired significance tests between configurations (currently mean ± std only).
3. Retain one CV fold checkpoint of the frozen EfficientNet-B0 model so the demo
   can serve the model the metrics describe.
