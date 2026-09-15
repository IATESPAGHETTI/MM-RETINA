# MM-RETINA website

Premium marketing/research site for the multimodal (OCT + fundus) glaucoma
grading project. Next.js 16 (App Router, Turbopack) + TypeScript + Tailwind
CSS v4 + Framer Motion.

## Run it

```bash
npm install
npm run dev
```

Then open http://localhost:3000.

## Structure

- `src/app/` — pages: `/` (landing), `/model`, `/dataset`, `/results`, `/research`, `/about`, `/demo`.
- `src/components/` — `Navbar`, `Hero`, `WhyMultimodal`, `ArchitecturePipeline`
  (animated SVG pipeline diagram), `DatasetFacts`, `ResultsPreview`,
  `AblationTable`, `ResearchIntegrity`, `GlassCard`, `Reveal` (scroll-triggered
  motion wrapper), `DemoBadge`.
- `src/lib/content.ts` — the single source of truth for page copy, split into
  `VERIFIED_*` (sourced from the official GAMMA/GRAPE dataset cards — see
  `../dataset/README.md`) and `DEMO_*` (UI placeholder values). Every
  `DEMO_*` consumer must render a visible "demo" label — never let a
  placeholder number appear unlabeled.

## Design language

Dark, glass-surfaced, Apple-inspired — see `src/app/globals.css` for the
color tokens (`--bg`, `--accent-cyan`, `--accent-violet`, `.glass` /
`.glass-strong` utilities) and `prefers-reduced-motion` handling.

## What's real vs. placeholder right now

- Dataset facts (sample counts, license, acquisition devices) are sourced
  from the official GAMMA dataset card and paper — see `../dataset/README.md`.
- Every metric on `/results` and the prediction card on `/` and `/results`
  is a UI placeholder, explicitly labeled. No model has been trained on
  GAMMA in this repo yet.
- `/demo` is a static UI mock — it does not call any inference backend
  (none exists yet) and explicitly refuses to show a "prediction" when you
  interact with it, rather than faking one.

## Wiring in real results later

Once you've trained a model (see `../Adv_prj4/` for the cross-attention
fusion architecture) and have real metrics:

1. Replace the `DEMO_METRICS` / `DEMO_ABLATION_ROWS` objects in
   `src/lib/content.ts` with real numbers, and drop the `isDemo`/`DemoBadge`
   usage at each call site once the data is real.
2. For `/demo` to actually run inference, add a route handler (e.g.
   `src/app/api/predict/route.ts`) that proxies to a Python inference
   service (FastAPI + the trained Keras model), and replace the disabled
   "Run inference" button's `disabled` state with a real fetch call.
