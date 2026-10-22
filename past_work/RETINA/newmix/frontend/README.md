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

- `src/app/` — pages: `/` (landing), `/model`, `/dataset`, `/results`, `/research`, `/about`, `/demo`.
- `src/components/` — `Navbar`, `Hero`, `WhyMultimodal`, `ArchitecturePipeline`
  (animated SVG pipeline diagram), `OCTViewer` (real, interactive B-scan
  slider), `DatasetFacts`, `ResultsPreview`, `AblationTable`,
  `ResearchIntegrity`, `GlassCard`, `Reveal` (scroll-triggered motion
  wrapper), `DemoBadge`.
- `src/lib/content.ts` — the single source of truth for page copy:
  `VERIFIED_*` (official GAMMA/GRAPE dataset facts), `CV_RESULTS` (real
  5-fold cross-validation metrics, copied verbatim from
  `../results/cv/summary.json`), `SINGLE_SPLIT_HISTORY` (the qualitative
  story of the earlier, superseded single-split experiment). There is no
  static demo-prediction data anymore — `/demo` calls the real backend.

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
- `/results` shows real 5-fold cross-validation metrics (15 total training
  runs — see `../EXPERIMENTS.md`), not placeholders. An earlier single-split
  experiment's numbers are intentionally not redisplayed (see
  `SINGLE_SPLIT_HISTORY` in content.ts for why) but remain in
  `EXPERIMENTS.md`/git history.
- `/demo` calls a real FastAPI backend (`../backend/`) running the actual
  trained checkpoints. It is not mocked — if the backend is down, the page
  says so and disables the run button rather than faking a result.
- The live demo's OCT path has one known, disclosed limitation: it accepts
  a single OCT image and repeats it across the model's expected 8-slice
  input (the model was trained on 8 real slices per volume). See
  `../backend/README.md`.

## Next steps if extending this

1. Grad-CAM/attribution visualization for `/demo` (not implemented yet).
2. Accept multiple OCT slice uploads instead of repeating one image.
3. k-fold-aware statistical significance testing between modalities
   (currently just mean±std, no paired test) — see `PROGRESS.md` at the
   repo root.
