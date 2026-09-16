/**
 * Central content store. Categories kept structurally separate so no
 * component can accidentally present one as another:
 *
 *  - VERIFIED_* : facts about the GAMMA/GRAPE datasets, sourced from the
 *    official dataset cards / papers (see dataset/README.md in the repo root).
 *  - CV_RESULTS : real 5-fold cross-validation metrics (15 total training
 *    runs) copied verbatim from results/cv/summary.json and EXPERIMENTS.md —
 *    never rounded up, adjusted, or "cleaned up".
 *  - SINGLE_SPLIT_HISTORY : the earlier, superseded single-split experiment.
 *    Its full numbers live in EXPERIMENTS.md/git history, not here — this
 *    is only the qualitative "why we moved to CV" story.
 *
 * Live model predictions (the /demo page) come from the real backend at
 * runtime (see backend/README.md) — there is no static demo data in this
 * file for that anymore.
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
 * Real 5-fold cross-validation results (2026-09-17): 15 total training
 * runs (5 folds x {fundus, oct, fusion}), patient-level grade-stratified
 * folds over all 100 labeled GAMMA training patients. Copied verbatim from
 * results/cv/summary.json / EXPERIMENTS.md's cv-run-1 entry — never
 * rounded up or adjusted. This superseded an earlier single 70/15/15
 * split (see SINGLE_SPLIT_HISTORY below) whose numbers are intentionally
 * NOT redisplayed here, since they were sensitive to that one split.
 */
export const CV_RESULTS = {
  numFolds: 5,
  numPatients: 100,
  totalRuns: 15,
  methodologyNote:
    "Results are reported using 5-fold cross-validation across 100 patients, with 15 total model runs across the three modalities. Values are reported as mean ± standard deviation across folds.",
  runs: [
    {
      name: "Fundus only",
      accuracy: 0.73,
      accuracyStd: 0.156,
      balancedAccuracy: 0.697,
      balancedAccuracyStd: 0.173,
      macroF1: 0.682,
      macroF1Std: 0.183,
      rocAuc: 0.876,
      rocAucStd: 0.086,
    },
    {
      name: "OCT only",
      accuracy: 0.661,
      accuracyStd: 0.089,
      balancedAccuracy: 0.599,
      balancedAccuracyStd: 0.076,
      macroF1: 0.587,
      macroF1Std: 0.09,
      rocAuc: 0.842,
      rocAucStd: 0.041,
    },
    {
      name: "Fusion (fundus + OCT)",
      accuracy: 0.71,
      accuracyStd: 0.052,
      balancedAccuracy: 0.644,
      balancedAccuracyStd: 0.058,
      macroF1: 0.636,
      macroF1Std: 0.061,
      rocAuc: 0.892,
      rocAucStd: 0.035,
    },
  ],
  interpretation:
    "Fusion achieved the highest mean ROC-AUC (0.892 ± 0.035) and demonstrated substantially more consistent fold-to-fold performance than fundus-only. Fundus-only achieved higher mean accuracy, balanced accuracy, and macro F1 in this experiment, but with considerably higher variability. OCT-only was weakest across the evaluated metrics.",
  whyCrossValidation:
    "The earlier single train/test split made fundus-only appear clearly superior. Five-fold cross-validation showed that conclusion was sensitive to the particular split. The cross-validated experiment provides a more robust view of performance and reveals that fusion has the highest mean ROC-AUC and substantially lower variance.",
} as const;

/**
 * The earlier single-split experiment (fusion_run1/fundus_run1/oct_run1,
 * one 70/15/15 split, 14-sample test set) is kept in EXPERIMENTS.md and
 * git history in full — it is NOT deleted. Its specific numbers are
 * intentionally not redisplayed on the results page (see CV_RESULTS
 * above for why), but the qualitative story of why CV was needed is worth
 * telling honestly.
 */
export const SINGLE_SPLIT_HISTORY = {
  note: "An earlier single train/test split (14 held-out samples) made fundus-only look like the clear winner over fusion. Full numbers are preserved in EXPERIMENTS.md, not repeated here, because 5-fold cross-validation showed that result was sensitive to which 14 samples happened to land in that one test set.",
} as const;

export const RESEARCH_INTEGRITY_POINTS = [
  "Patient-level splitting — no patient's data crosses train/val/test.",
  "No fabricated labels or invented dataset contents.",
  "No invented experimental results — metric cells stay blank until measured.",
  "Missing-data and duplicate-file handling is logged, not silently patched.",
  "Reproducible experiments: fixed seeds, versioned splits, documented preprocessing.",
] as const;
