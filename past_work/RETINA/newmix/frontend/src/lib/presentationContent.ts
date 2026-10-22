/**
 * Content for the /presentation deck. Every number is copied from
 * the per-experiment summary.json files under results (5-fold CV means), results/augmented/results.json
 * (the Kaggle notebook re-run), or EXPERIMENTS.md. Notebook kappa/QWK are
 * computed from the notebook's own confusion matrix. Nothing is rounded up.
 */

export type MetricKey = "accuracy" | "balancedAccuracy" | "macroF1" | "rocAuc" | "kappa" | "qwk";

export const METRIC_LABELS: Record<MetricKey, string> = {
  accuracy: "Accuracy",
  balancedAccuracy: "Balanced acc.",
  macroF1: "Macro F1",
  rocAuc: "ROC-AUC",
  kappa: "Kappa",
  qwk: "QWK",
};

export type Verdict = "baseline" | "rejected" | "adopted" | "inconclusive";

export interface Experiment {
  id: string;
  title: string;
  change: string;
  verdict: Verdict;
  verdictLabel: string;
  metrics: Record<MetricKey, number>;
  accuracyStd: number;
}

/** The ladder, in the order the experiments were run. All 5-fold patient-level CV. */
export const LADDER: Experiment[] = [
  {
    id: "EXP-01",
    title: "Frozen baseline",
    change: "ResNet18 fundus + ResNet18 OCT, 8 slices, vector fusion",
    verdict: "baseline",
    verdictLabel: "Baseline",
    metrics: { accuracy: 0.731, balancedAccuracy: 0.691, macroF1: 0.681, rocAuc: 0.875, kappa: 0.577, qwk: 0.775 },
    accuracyStd: 0.072,
  },
  {
    id: "EXP-02",
    title: "OCT 2.5D",
    change: "Neighbouring-slice stacks instead of single slices",
    verdict: "rejected",
    verdictLabel: "Rejected",
    metrics: { accuracy: 0.711, balancedAccuracy: 0.648, macroF1: 0.63, rocAuc: 0.876, kappa: 0.543, qwk: 0.77 },
    accuracyStd: 0.058,
  },
  {
    id: "EXP-03",
    title: "12 OCT slices",
    change: "More B-scans per volume",
    verdict: "rejected",
    verdictLabel: "Rejected",
    metrics: { accuracy: 0.7, balancedAccuracy: 0.646, macroF1: 0.627, rocAuc: 0.873, kappa: 0.531, qwk: 0.763 },
    accuracyStd: 0.116,
  },
  {
    id: "EXP-04",
    title: "16 OCT slices",
    change: "Even more B-scans per volume",
    verdict: "rejected",
    verdictLabel: "Rejected",
    metrics: { accuracy: 0.67, balancedAccuracy: 0.6, macroF1: 0.59, rocAuc: 0.856, kappa: 0.482, qwk: 0.74 },
    accuracyStd: 0.055,
  },
  {
    id: "EXP-05",
    title: "EfficientNet-B0 fundus",
    change: "Swap the fundus encoder: ResNet18 → EfficientNet-B0",
    verdict: "adopted",
    verdictLabel: "Adopted · frozen",
    metrics: { accuracy: 0.82, balancedAccuracy: 0.79, macroF1: 0.781, rocAuc: 0.924, kappa: 0.716, qwk: 0.798 },
    accuracyStd: 0.055,
  },
  {
    id: "EXP-06",
    title: "Token-level fusion",
    change: "Small transformer over per-modality feature tokens",
    verdict: "inconclusive",
    verdictLabel: "Not adopted",
    metrics: { accuracy: 0.82, balancedAccuracy: 0.769, macroF1: 0.763, rocAuc: 0.935, kappa: 0.712, qwk: 0.852 },
    accuracyStd: 0.11,
  },
];

export const BASELINE = LADDER[0];
export const FINAL = LADDER[4];
export const FINAL_STD = { accuracy: 0.055, rocAuc: 0.039, macroF1: 0.061, balancedAccuracy: 0.057 } as const;

/** The original Kaggle notebook, re-run locally on its own augmented dataset (results/augmented/). */
export const NOTEBOOK = {
  name: "Kaggle baseline notebook",
  model: "4-branch Keras net · EfficientNetV2S + EfficientNetB0 · attention U-Net decoder",
  classes: ["Mild", "Moderate", "Severe"],
  trainSamples: 1877,
  trainOriginals: 100,
  trainAugmented: 1777,
  valSamples: 13,
  testSamples: 29,
  valAccuracy: 0.923,
  testAccuracy: 0.69,
  metrics: { accuracy: 0.69, balancedAccuracy: 0.626, macroF1: 0.622, kappa: 0.467, qwk: 0.632 },
  confusion: [
    [13, 3, 1],
    [2, 2, 1],
    [1, 1, 5],
  ],
  classMinority: { name: "Moderate", originals: 20, afterAugmentation: 630 },
  augCopiesPerOriginal: "8–9",
} as const;

export const PROTOCOL_COMPARE = [
  { label: "Held-out evaluation", notebook: "29 images, one split", ours: "100 patients, 5 folds" },
  { label: "Training data", notebook: "94.7% augmented copies", ours: "Real images; augmented on-the-fly" },
  { label: "Split unit", notebook: "Image files", ours: "Patient — never crosses folds" },
  { label: "Clinical table link", notebook: "Row position (index mod n)", ours: "No fabricated links" },
  { label: "Error bar", notebook: "None (1 image = 3.4 pts)", ours: "Mean ± SD across folds" },
] as const;

export const NOTES: Record<string, string[]> = {
  title: [
    "Open with the punchline: we started at 73.1% accuracy and finished at 82.0%, with a ROC-AUC of 92.4%.",
    "The interesting part isn't only the number. It's that every number in this deck survived a patient-level cross-validation, and we can say what each one cost us.",
    "Roughly 10 minutes: problem, the notebook we started from, our protocol, the experiment ladder, the head-to-head, and what we deliberately refused to claim.",
  ],
  problem: [
    "GAMMA gives us 100 labeled patients, each with a colour fundus photo and a 3D OCT volume, graded Normal / Early / Progressive.",
    "100 patients is small. That drives every design decision: patient-level splits, cross-validation instead of one lucky split, and skepticism of any single high number.",
    "If asked about other modalities: we explored four data sources in total. Fundus and OCT (both from GAMMA) make up the fusion model. HVF visual fields and RNFL/GCC measurements were explored separately, but they come from different cohorts with no patient overlap with GAMMA, so they could not be fused into the same model. Details on the integrity slide.",
  ],
  notebook: [
    "This is the reference point: the Kaggle baseline notebook, unchanged architecture, re-run locally on its own dataset. We didn't sandbag it.",
    "Its dataset is 'Augmented_Multimodal'. Only 113 real training images exist. The training set is 1,877 images, and 1,777 of them are augmented copies.",
    "Test accuracy is 69.0% on 29 images. Its validation accuracy reads 92.3% — remember that gap, it comes back on the next slide.",
  ],
  asterisk: [
    "This is the slide that reframes the notebook. Four issues, all traceable in the code and the data folder.",
    "Leakage: every original image has 8–9 augmented siblings whose filenames carry the source index. Validation images are held out from the originals, but their augmented siblings sit in the training set. A 92.3% validation score against a 69.0% test score is exactly what that looks like.",
    "Class balance: Moderate has 20 real images and is inflated to 630 by augmentation. The model sees the same 20 pictures ~30 times each.",
    "Clinical link: the notebook attaches RNFL/GCC rows by row position modulo table length. There's no patient key — we proved that separately in the workbook audit.",
    "Sample size: with 29 test images, one image is 3.4 accuracy points.",
  ],
  protocol: [
    "Our answer to each of those problems. Same class of data, stricter test.",
    "Five folds, split by patient, stratified by grade. Every one of the 100 patients is held out exactly once. Fixed seed, so every experiment sees identical folds and differences are attributable to the change, not the split.",
    "We report mean ± SD across folds. When an experiment has a higher mean but a much wider spread, we say so — that decided EXP-06.",
  ],
  fusion: [
    "Before any experiment: what is 'fusion'? Each eye gives us two very different pictures. A fundus photo is a flat colour image of the back of the eye. An OCT is a 3D volume of 256 cross-section scans (B-scans).",
    "Each modality gets its own encoder network that turns pictures into vectors. A small cross-modal transformer then lets the fundus vector and the OCT vector 'talk' to each other before one severity grade comes out.",
    "In our first cross-validated comparison fundus-only scored 73.0% accuracy, OCT-only 66.1%, and fusion 71.0% — but fusion had the best ROC-AUC (89.2%) and by far the steadiest fold-to-fold results. That's why we kept building on fusion.",
    "EXP-01 is that same model re-run under the final evaluation code (73.1% accuracy) and frozen as the yardstick. Every later experiment changes exactly one glowing box.",
  ],
  exp02: [
    "EXP-02 changes the OCT slice sampler. 2.5D feeds each B-scan together with its two neighbours as a 3-channel image, giving the network a little local depth context.",
    "We tried it because on the OCT-only model it was a clean win over single slices (66.1% to 68.0% accuracy).",
    "Inside the fusion model it did not carry over: balanced accuracy and macro F1 both dropped, ROC-AUC was tied. One real upside: much lower fold-to-fold spread on ROC-AUC (0.016 vs 0.037).",
    "Our decision rule puts macro F1 and balanced accuracy first, so 2.5D was rejected. Our hypothesis, not proven: cross-modal attention already pulls most of the useful OCT signal from one good slice.",
  ],
  slices: [
    "EXP-03 and EXP-04 ask a simple question: does showing the OCT branch more of the volume help? 8 slices to 12 to 16.",
    "It got steadily worse: 73.1% to 70.0% to 67.0% accuracy, with 12 slices also the noisiest run.",
    "With only 100 patients, more slices means more inputs to the attention pool and more capacity to overfit. That's a hypothesis, consistent with a small-data regime, not a demonstrated finding.",
    "Useful negative result: it told us OCT depth was not the bottleneck, so we looked at the fundus branch next.",
  ],
  exp05: [
    "EXP-05 is the breakthrough, and it's the smallest change in the whole series: one box. The fundus encoder goes from ResNet18 to EfficientNet-B0.",
    "Accuracy +8.9 pts, macro F1 +10.0, balanced accuracy +9.9, kappa +0.139 — every one of six metrics improved, and on essentially every individual fold, so it isn't a lucky split.",
    "And it's smaller: 4.01M parameters instead of 11.18M. This is the frozen reference model.",
  ],
  exp06: [
    "EXP-06 changes the fusion box. Instead of squeezing each modality into one vector, keep the spatial detail: 25 fundus feature-map tokens plus 8 OCT slice tokens go through a 2-layer transformer.",
    "ROC-AUC went up to 93.5% and QWK to 0.852, but balanced accuracy and macro F1 dropped, and the fold-to-fold spread roughly doubled.",
    "By our own rule, higher AUC with a wobblier, lower balanced accuracy is not a win. EXP-05 stays frozen. This is where we stopped architecture changes.",
  ],
  ladder: [
    "Recap of the whole ladder on one chart. Same folds, one change at a time.",
    "Three OCT ideas failed to beat baseline, one fundus swap lifted everything, and the fancier fusion did not beat the simple one.",
  ],
  headtohead: [
    "Now the comparison the notebook deserves. Be careful with the framing: different dataset, different label names, so this is not a controlled A/B. It's a comparison of what each pipeline can honestly defend.",
    "Even with a stricter protocol, ours is higher on every shared metric: accuracy 82.0 vs 69.0, macro F1 78.1 vs 62.2, kappa 0.716 vs 0.467.",
    "And the notebook's own best-looking number, 92.3% validation, is the one we'd tell people not to trust.",
  ],
  final: [
    "The end state: EfficientNet-B0 fundus + ResNet18 OCT (8 slices) + vector fusion. 82.0% ± 5.5 accuracy, 92.4% ± 3.9 ROC-AUC, macro F1 78.1%.",
    "ROC-AUC above 92% means the model ranks severity well even when the hard label boundary is fuzzy — which matters for a graded disease.",
    "These are cross-validated means over 100 patients. That's the version of 'high' we're willing to stand behind.",
  ],
  integrity: [
    "This is what separates the project from a leaderboard chase. We found a 96.4% number — a random forest on HVF features — and threw it out.",
    "MD, PSD and VFI are the same indices clinicians use to assign severity. Remove them and the score collapses to QWK 0.14, essentially chance. It was a label proxy, not a model.",
    "The RNFL/GCC workbook has no patient ID, no date, no linking key — verified in every hidden layer of the file. So we did not force a join.",
    "That is why the final model uses two modalities, not four: HVF and RNFL/GCC have no verified link to the GAMMA patients. The shared-representation experiment over all three cohorts showed a small, mixed effect, so we report it as inconclusive.",
  ],
  next: [
    "Close on what's next and what we're not promising. Ordinal classifier, anatomy-aware auxiliary loss, multi-seed validation, fold ensembles — all gated on more data and a real patient link for HVF/RNFL.",
    "Suggested last line: good research isn't finding the highest number, it's finding out which numbers deserve to be trusted.",
  ],
};
