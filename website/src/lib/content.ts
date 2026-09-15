/**
 * Central content store. Two categories, kept structurally separate so no
 * component can accidentally present one as the other:
 *
 *  - VERIFIED_* : facts about the GAMMA/GRAPE datasets, sourced from the
 *    official dataset cards / papers (see dataset/README.md in the repo root).
 *  - DEMO_* : placeholder numbers for UI layout only. Every consumer of
 *    DEMO_* data must render the `isDemo` flag as a visible label —
 *    never let a demo number appear unlabeled.
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

/** All numbers below are illustrative UI placeholders, not experimental results. */
export const DEMO_METRICS = {
  isDemo: true,
  label: "Example values — no model has been trained yet",
  grade: "Progressive",
  confidence: 92.8,
  branchConfidence: { oct: 88, fundus: 90, fusion: 93 },
  metrics: [
    { name: "AUROC", value: "—" },
    { name: "Macro F1", value: "—" },
    { name: "Sensitivity", value: "—" },
    { name: "Specificity", value: "—" },
    { name: "ECE", value: "—" },
  ],
} as const;

export const DEMO_ABLATION_ROWS = [
  { model: "OCT baseline", auroc: "—", f1: "—" },
  { model: "OCT + Fundus (concat)", auroc: "—", f1: "—" },
  { model: "Concatenation fusion", auroc: "—", f1: "—" },
  { model: "Cross-attention fusion", auroc: "—", f1: "—" },
  { model: "Final model", auroc: "—", f1: "—" },
] as const;

export const RESEARCH_INTEGRITY_POINTS = [
  "Patient-level splitting — no patient's data crosses train/val/test.",
  "No fabricated labels or invented dataset contents.",
  "No invented experimental results — metric cells stay blank until measured.",
  "Missing-data and duplicate-file handling is logged, not silently patched.",
  "Reproducible experiments: fixed seeds, versioned splits, documented preprocessing.",
] as const;
