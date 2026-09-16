/**
 * Central content store. Three categories, kept structurally separate so no
 * component can accidentally present one as another:
 *
 *  - VERIFIED_* : facts about the GAMMA/GRAPE datasets, sourced from the
 *    official dataset cards / papers (see dataset/README.md in the repo root).
 *  - REAL_RESULTS : actual metrics from actual `evaluate.py` runs against
 *    real trained checkpoints on the real held-out test split. Copied
 *    verbatim from ../../results/*\/metrics.json and EXPERIMENTS.md —
 *    never rounded up, adjusted, or "cleaned up". Every consumer must
 *    render `REAL_RESULTS.caveat` visibly, since the test set is only 14
 *    samples from a single split (see EXPERIMENTS.md for why that matters).
 *  - DEMO_* : placeholder numbers for UI layout only, for things that
 *    genuinely have no real output yet (e.g. the live /demo inference
 *    button). Every consumer of DEMO_* data must render the `isDemo` flag
 *    as a visible label — never let a demo number appear unlabeled.
 */

export const NAV_LINKS = [
  { href: "/model", label: "Model" },
  { href: "/dataset", label: "Dataset" },
  { href: "/results", label: "Results" },
  { href: "/research", label: "Research" },
] as const;

export const VERIFIED_GAMMA_FACTS = {
  name: "GAMMA",
  fullName: "Glaucoma grAding from Multi-Modality imAges",
  officialUrl: "https://gamma.grand-challenge.org/",
  mirrorUrl: "https://huggingface.co/datasets/yujiaxue/GAMMA",
  paperUrl: "https://arxiv.org/abs/2202.06511",
  license: "CC BY-NC-ND",
  pairedSamples: 300,
  patients: 276,
  bscansPerVolume: 256,
  ageRange: "19-77",
  classes: ["Normal", "Early", "Progressive"] as const,
  classDistribution: {
    normal: "~50%",
    early: "~52% of glaucoma cases",
    progressive: "~48% of glaucoma cases (intermediate + advanced grouped)",
  },
  acquisition: {
    oct: "Topcon DRI OCT Triton, 3x3mm en-face FOV",
    fundus: "KOWA / Topcon TRC-NW400, macula or disc-midpoint centered",
  },
  citation:
    "Wu J., Fang H., Li F., Fu H., Lin F., et al. \"GAMMA Challenge: Glaucoma grAding from Multi-Modality imAges.\" Medical Image Analysis, 2023.",
} as const;

export const VERIFIED_GRAPE_FACTS = {
  name: "GRAPE",
  fullName:
    "A multi-modal glaucoma dataset of follow-up visual field and fundus images for glaucoma management",
  collectionUrl:
    "https://springernature.figshare.com/collections/GRAPE_A_multi-modal_glaucoma_dataset_of_follow-up_visual_field_and_fundus_images_for_glaucoma_management/6406319",
  paperUrl: "https://www.nature.com/articles/s41597-023-02424-4",
  license: "CC0",
  baselineEyeRecords: 263,
  followUpVisits: 1115,
  fundusPhotographs: 631,
  modalities: ["Clinical information", "Visual field values", "Fundus photographs", "IOP", "OCT measurements"],
} as const;

/**
 * Real results from the first three training runs (2026-09-17), evaluated
 * on the real 14-sample GAMMA test split. See EXPERIMENTS.md at the repo
 * root for the full methodology, hyperparameters, and confusion matrices.
 */
export const REAL_RESULTS = {
  caveat:
    "Preliminary — a single 14-sample test split, one run each, no cross-validation yet. Differences this small are not statistically meaningful; see EXPERIMENTS.md.",
  testSetSize: 14,
  runs: [
    {
      name: "Fundus only",
      accuracy: 0.786,
      balancedAccuracy: 0.786,
      macroF1: 0.748,
      rocAuc: 0.93,
    },
    {
      name: "Fusion (fundus + OCT)",
      accuracy: 0.643,
      balancedAccuracy: 0.563,
      macroF1: 0.567,
      rocAuc: 0.8,
    },
    {
      name: "OCT only",
      accuracy: 0.5,
      balancedAccuracy: 0.405,
      macroF1: 0.378,
      rocAuc: 0.817,
    },
  ],
  /** One real prediction from fusion_run1/predictions.csv (test sample
   * 0058, GAMMA training split) — a genuine correct prediction with its
   * actual softmax confidence, not a cherry-picked high number. */
  exampleInference: {
    sampleId: "0058",
    trueLabel: "Progressive",
    predictedLabel: "Progressive",
    confidence: 49.1,
    probNormal: 8.8,
    probEarly: 42.1,
    probProgressive: 49.1,
  },
} as const;

/** Placeholder for the still-unimplemented live /demo inference endpoint —
 * not the same thing as REAL_RESULTS above, which came from actual runs. */
export const DEMO_METRICS = {
  isDemo: true,
  label: "Illustrative only — the /demo page has no live inference backend",
} as const;

export const RESEARCH_INTEGRITY_POINTS = [
  "Patient-level splitting — no patient's data crosses train/val/test.",
  "No fabricated labels or invented dataset contents.",
  "No invented experimental results — metric cells stay blank until measured.",
  "Missing-data and duplicate-file handling is logged, not silently patched.",
  "Reproducible experiments: fixed seeds, versioned splits, documented preprocessing.",
] as const;
