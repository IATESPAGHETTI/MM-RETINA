/**
 * Content for the /suite page (Retina Suite).
 *
 * Every number here is copied from a saved results file, never estimated:
 *  - SUITE_EVIDENCE.nested / .exp05      -> EXPERIMENTS.md, EXP-05 and EXP-N01 (results/nested_cv_v1/)
 *  - SUITE_EVIDENCE.paperProtocol        -> past_work/RETINA/newmix/README.md ("paper protocol" row)
 *  - SUITE_EVIDENCE.clinical / .deferral -> past_work/RETINA/newmix/README.md (patient-grouped 5-fold CV,
 *                                           303 eyes / 162 patients)
 *  - GAMMA_SAMPLE_RUN                    -> a real /api/glaucoma/compare call on GAMMA sample 0001
 *                                           (single-split demonstration checkpoints, NOT the 5-fold CV models)
 * Illustrations (vessel tree, feature flow) carry no numbers and are labelled as illustrations in the UI.
 */

/**
 * Where the workspace app runs. This website normally owns port 3000 and the older MM-RETINA demo
 * backend owns 8000, so the suite is started on 3100 (app) and 8001 (API); see SUITE_RUN_COMMANDS.
 * Override with NEXT_PUBLIC_SUITE_URL when it is hosted elsewhere.
 */
export const SUITE_URL = process.env.NEXT_PUBLIC_SUITE_URL ?? "http://localhost:3100/workspace";

export type ModuleId = "multimodal" | "glaucoma" | "diabetes";

export interface SuiteModule {
  id: ModuleId;
  tab: string;
  project: string;
  title: string;
  summary: string;
  inputs: string;
  outputs: string;
  status: "Research model" | "Experimental";
  evidence: { headline: string; detail: string };
}

export const SUITE_MODULES: readonly SuiteModule[] = [
  {
    id: "multimodal",
    tab: "GAMMA multimodal",
    project: "MM-RETINA",
    title: "Fundus + OCT volume, graded together",
    summary:
      "A fundus photograph and eight OCT B-scans go through one fusion model and come back as Normal, Early or Progressive, with a fundus Grad-CAM and a side-by-side check of what each image type says on its own.",
    inputs: "Fundus photo + 8 OCT B-scans",
    outputs: "Normal / Early / Progressive, Grad-CAM, model agreement",
    status: "Research model",
    evidence: {
      headline: "82.0% accuracy, 74.3% under nested selection",
      detail:
        "5-fold CV on 100 patients (EXP-05). The reporting folds also picked each epoch; with selection kept inside training data (EXP-N01) accuracy is 0.743 and Early recall is 0.41.",
    },
  },
  {
    id: "glaucoma",
    tab: "Glaucoma staging",
    project: "Sankara glaucoma research",
    title: "Measurements first, and a way to say “not sure”",
    summary:
      "Clinical measurements (RNFL, GCC, cup-to-disc ratio, IOP, age, sex) plus an OCT B-scan give a four-stage grade with the features that drove it. When confidence is low the app answers Inconclusive and recommends a visual-field test instead of guessing.",
    inputs: "RNFL/GCC measurements + OCT B-scan",
    outputs: "Control / Mild / Moderate / Severe, or Inconclusive",
    status: "Research model",
    evidence: {
      headline: "67.7% balanced accuracy from clinical features",
      detail:
        "Patient-grouped 5-fold CV, 303 eyes from 162 patients. The OCT image alone reaches only about 44–47% balanced accuracy, and adding it to the clinical features gave no reliable gain.",
    },
  },
  {
    id: "diabetes",
    tab: "Diabetes vessels",
    project: "RETINA diabetes project",
    title: "Vessel analysis from a fundus photo",
    summary:
      "A vessel segmentation overlay and fractal dimension are measured from a fundus photograph, alongside an experimental HbA1c estimate that the app labels as exactly that.",
    inputs: "Fundus photo",
    outputs: "Vessel overlay, fractal dimension, experimental HbA1c",
    status: "Experimental",
    evidence: {
      headline: "HbA1c estimate: no validation shipped",
      detail:
        "On 22 reference images the six-bin model returned its lowest bin every time and the binary model flagged 95% as elevated, so the app warns when the two contradict each other.",
    },
  },
] as const;

/** A real run of the three GAMMA checkpoints on sample 0001 (single-split demonstration checkpoints). */
export const GAMMA_SAMPLE_RUN = {
  sample: "GAMMA sample 0001",
  caveat: "Single-split demonstration checkpoints, not the 5-fold CV models.",
  models: [
    { name: "Fundus only", prediction: "normal", probability: 0.417 },
    { name: "OCT only", prediction: "normal", probability: 0.826 },
    { name: "Fusion", prediction: "normal", probability: 0.738 },
  ],
  banner: "All 3 models agree on normal",
} as const;

export const SUITE_EVIDENCE = {
  nested: { optimistic: 82.0, honest: 74.3 },
  paperProtocol: { leaky: 81, grouped: 52 },
  clinical: { balancedAccuracy: 67.7, eyes: 303, patients: 162 },
  deferral: { answered: 76, forced: 70, coverage: 80 },
} as const;

export type FeatureIcon = "compare" | "scan" | "patients" | "report" | "batch" | "explain";

export const SUITE_FEATURES: readonly { icon: FeatureIcon; title: string; body: string }[] = [
  {
    icon: "compare",
    title: "Live model comparison",
    body: "Fundus-only, OCT-only and fusion on the same eye, with an agreement banner, a needs-review flag and a risk gauge.",
  },
  {
    icon: "scan",
    title: "OCT scan scrubber",
    body: "Drag through the B-scans of a volume to see exactly what the model was shown.",
  },
  {
    icon: "patients",
    title: "Saved patients",
    body: "Results saved under a study ID, with search and a history that shows how a case changed over time. No names are accepted.",
  },
  {
    icon: "report",
    title: "One-page PDF report",
    body: "Prediction, probabilities, review flags and the Grad-CAM in a single page you can hand over.",
  },
  {
    icon: "batch",
    title: "Batch ZIP and CSV",
    body: "Drop a ZIP of cases, get a results table with per-case errors, and export it as CSV.",
  },
  {
    icon: "explain",
    title: "Plain-language explanation",
    body: "A short, no-diagnosis explanation of each result. Only numbers are sent to the language model, never images or IDs.",
  },
] as const;

export const SUITE_RUN_COMMANDS = [
  "Set-Location past_work/RETINA/newmix",
  ".\\run.ps1 -ApiPort 8001 -AppPort 3100",
] as const;
