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
  (animated SVG pipeline diagram), `OCTViewer` (real, interactive B-scan
  slider — see below), `DatasetFacts`, `ResultsPreview`, `AblationTable`,
  `ResearchIntegrity`, `GlassCard`, `Reveal` (scroll-triggered motion
  wrapper), `DemoBadge`.
- `src/lib/content.ts` — the single source of truth for page copy, split into
  `VERIFIED_*` (sourced from the official GAMMA/GRAPE dataset cards — see
  `../dataset/README.md`) and `DEMO_*` (UI placeholder values). Every
  `DEMO_*` consumer must render a visible "demo" label — never let a
  placeholder number appear unlabeled.

## Design language

"Warm Titanium" — warm charcoal background, ivory text, champagne/olive/copper
accents (see `src/app/globals.css` for the `--bg`, `--accent-champagne`,
`--accent-olive`, `--accent-copper` tokens). Glass (`.glass` / `.glass-strong`)
is reserved for the floating navbar and small status overlays, not general
section backgrounds — most content sits directly on the page. Respects
`prefers-reduced-motion`.

## Real imagery

Both the fundus photo and the OCT B-scans on this site are real, unmodified
GAMMA dataset content (training sample 0001), used under the dataset's
CC BY-NC-ND terms — see `../dataset/README.md` for the full license/citation.

- `public/samples/gamma-0001-fundus.jpg` — the real color fundus photograph.
- `public/oct-volume/0001/000.jpg` … `255.jpg` — all 256 real B-scans from
  that sample's actual OCT volume, extracted from the official `.mhd`/`.raw`
  format via `../dataset/extract_oct_slices.py` (downscaled to 320px wide,
  ~9MB total). `OCTViewer.tsx` serves these directly as static files and
  only ever fetches the current slice plus a small prefetch window — never
  the whole volume at once.

Both came from a git-lfs clone of the official GAMMA "training" split at
`../dataset/GAMMA/` (gitignored, not part of this repo — see that folder's
README for the verified real directory layout, which turned out to differ
from what `gamma_loader.py` originally assumed).

## What's real vs. placeholder right now

- Dataset facts (sample counts, license, acquisition devices) are sourced
  from the official GAMMA dataset card and paper — see `../dataset/README.md`.
- The fundus photo and every OCT B-scan are real (see above) — nothing about
  the retinal imagery is simulated.
- Every metric on `/results` and the prediction readout on `/` and `/results`
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
