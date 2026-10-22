/**
 * Content for the /research/journey scroll story. Every number here is
 * copied verbatim from EXPERIMENTS.md / dataset/rnfl_gcc_provenance_audit.md
 * / results/case_examples/CASE_EXAMPLES.md — never rounded up, invented, or
 * adjusted for narrative effect. If a number can't be traced to one of
 * those files, it doesn't belong in this file.
 */

export type JourneyStageId =
  | "hero"
  | "gamma"
  | "exp01"
  | "exp05"
  | "exp06"
  | "audit"
  | "c01"
  | "c01b"
  | "eyecase"
  | "rnfl"
  | "m01"
  | "conclusion";

export const JOURNEY_NAV: { id: JourneyStageId; label: string }[] = [
  { id: "hero", label: "Question" },
  { id: "gamma", label: "GAMMA" },
  { id: "exp01", label: "Baseline" },
  { id: "exp05", label: "EXP-05" },
  { id: "exp06", label: "EXP-06" },
  { id: "audit", label: "Clinical audit" },
  { id: "c01", label: "C01" },
  { id: "c01b", label: "C01b" },
  { id: "eyecase", label: "Eye-level case" },
  { id: "rnfl", label: "RNFL/GCC" },
  { id: "m01", label: "M01" },
  { id: "conclusion", label: "Conclusion" },
];

export const EXP01 = {
  id: "EXP-01",
  name: "fusion_baseline_v1",
  accuracy: 0.731,
  rocAuc: 0.875,
} as const;

export const EXP05 = {
  id: "EXP-05",
  name: "fusion_effnetb0_v1",
  accuracy: 0.82,
  balancedAccuracy: 0.79,
  macroF1: 0.781,
  rocAuc: 0.924,
  kappa: 0.716,
  qwk: 0.798,
  change: "ResNet18 fundus encoder → EfficientNet-B0 fundus encoder",
  why: "The baseline fundus branch used a ResNet18 backbone. EfficientNet-B0 is a more parameter-efficient ImageNet architecture at a similar scale.",
  result:
    "Improved every one of the 6 cross-validated metrics, most by a wide margin (macro F1 +0.100, balanced accuracy +0.099, kappa +0.139), with fewer parameters than ResNet18 (4.01M vs 11.18M).",
  decision:
    "Frozen as the reference configuration going into the architecture-freeze milestone.",
} as const;

export const EXP06 = {
  id: "EXP-06",
  name: "fusion_token_v1",
  rocAuc: 0.935,
  balancedAccuracy: 0.769,
  macroF1: 0.763,
  kappa: 0.712,
  qwk: 0.852,
  accuracy: 0.82,
  why: "Test whether preserving more spatial/sequential structure per modality (token-level fusion through a small transformer) beats collapsing each modality to one pooled vector.",
  result:
    "QWK and ROC-AUC improved (+0.054, +0.011), but macro F1 and balanced accuracy — the higher-priority metrics in the project's own decision rule — both came out lower, and fold-to-fold variance roughly doubled on 4 of 6 metrics.",
  decision:
    "EXP-06 produced a higher mean ROC-AUC but had substantially higher variance and lower balanced accuracy/macro F1. EXP-05 was therefore retained as the stable reference.",
} as const;

export const AUDIT = {
  gammaPatients: 100,
  gammaModalities: "Fundus + OCT",
  hvfEyes: 168,
  hvfPatients: 90,
  rnflRows: 171,
  gammaClinicalCoverage: "0/100 GAMMA patients with confirmed HVF or RNFL/GCC coverage",
  steps: [
    { label: "Patient IDs", verified: false },
    { label: "Examination dates", verified: false },
    { label: "Eye / laterality key", verified: false },
    { label: "Hidden sheets / rows / columns", verified: true, note: "checked — none exist" },
    { label: "Formulas, comments, embedded objects", verified: true, note: "checked — none exist" },
    { label: "Workbook XML metadata", verified: true, note: "checked — no identifying data" },
  ],
} as const;

export const C01 = {
  id: "EXP-C01",
  cohort: "168 real HVF eyes / 90 real patients (Zeiss HFA “Single Field Analysis” DICOM exports)",
  model: "Random Forest",
  accuracy: 0.964,
  balancedAccuracy: 0.928,
  kappa: 0.93,
  qwk: 0.972,
  features: ["md_db", "psd_db", "vfi_pct"],
  why: "Test whether the newly available real HVF data contained predictive severity information.",
  warning:
    "MD, PSD, and VFI are the same indices standard clinical staging criteria commonly use to assign glaucoma severity in the first place.",
  nextStep: "EXP-C01b — rerun with those three fields removed.",
} as const;

export const C01B = {
  id: "EXP-C01b",
  model: "Random Forest",
  accuracy: 0.595,
  balancedAccuracy: 0.362,
  kappa: 0.086,
  qwk: 0.14,
  removed: ["md_db", "psd_db", "vfi_pct"],
  kept: [
    "false_positive_pct",
    "false_negative_pct",
    "fixation_loss_ratio",
    "test_duration_min",
    "refraction_used",
    "age_years",
    "sex",
  ],
  conclusion:
    "Removing md_db/psd_db/vfi_pct collapsed performance from QWK ≈ 0.97 to QWK ≈ 0.14 — essentially chance. Almost all of EXP-C01's predictive power came from the three fields that overlap with the label-assignment criteria itself.",
  decision: "C01's apparent performance was largely driven by severity-related proxy variables.",
} as const;

export const EYE_CASE = {
  patientId: "1028746",
  date: "2024-03-05",
  fold: 2,
  right: { severity: "Mild", predicted: "Mild" },
  left: { severity: "Severe", predicted: "Severe" },
  takeaway:
    "Same patient, same study date, different eye severity — confirmed no cross-fold leakage. Glaucoma severity in this cohort is modeled at the eye level, not the patient level.",
} as const;

export const RNFL_AUDIT_LAYERS = [
  "Visible cells",
  "Hidden sheets",
  "Hidden rows/columns",
  "Formulas",
  "Comments",
  "Hyperlinks / embedded objects",
  "Defined names",
  "Document metadata (XML)",
] as const;

export const RNFL_CONCLUSION = {
  headline: "NO PATIENT ID · NO DATE · NO LINKING KEY",
  detail:
    "No real patient ID, eye-visit key, or examination date is recoverable from this workbook by any means — not just absent from the visible columns, but absent from every non-visible part of the file that could plausibly carry one.",
  decision: "RNFL/GCC remains exploratory.",
} as const;

export const M01 = {
  id: "EXP-M01",
  question: "Can separate datasets with no valid patient-level link still contribute to a shared representation?",
  rows: [
    { metric: "HVF — Cohen's Kappa", independent: 0.036, shared: 0.125 },
    { metric: "RNFL/GCC — Cohen's Kappa", independent: 0.356, shared: 0.442 },
    { metric: "GAMMA† — QWK", independent: 0.851, shared: 0.832 },
  ],
  note:
    "† GAMMA numbers here use a probe on a different, weaker frozen embedding — not the official EXP-05/06 benchmark (0.820 accuracy / 0.924 ROC-AUC), which was never re-measured by this experiment.",
  decision: "Small + mixed effect. Suggestive, not conclusive.",
} as const;

export const FINAL_STACK = [
  {
    title: "Main benchmark",
    lines: ["Fundus + OCT", `${(EXP05.accuracy * 100).toFixed(1)}% Accuracy`, `${(EXP05.rocAuc * 100).toFixed(1)}% ROC-AUC`],
  },
  {
    title: "Clinical investigation",
    lines: ["HVF C01 → C01b", "label-proxy effect found"],
  },
  {
    title: "Data provenance",
    lines: ["RNFL/GCC cannot be linked"],
  },
  {
    title: "Representation study",
    lines: ["M01 mixed / inconclusive"],
  },
] as const;

export const CLOSING_LINE =
  "Good research is not just about finding a higher number. It's about finding out which numbers deserve to be trusted.";
