/**
 * Typed access to the cross-validation results.
 *
 * The numbers come from `results.generated.json`, which is produced by
 * `scripts/export_site_results.py` straight from `results/**\/summary.json`.
 * Nothing in here is hand-typed, so the site cannot silently fall behind the
 * experiment log again. CI runs the exporter with `--check`.
 */

import raw from "./results.generated.json";

export type MetricKey =
  | "accuracy"
  | "balanced_accuracy"
  | "macro_f1"
  | "roc_auc_ovr_macro"
  | "cohen_kappa"
  | "quadratic_weighted_kappa";

export type MetricStat = { mean: number; std: number };
export type MetricSet = Record<MetricKey, MetricStat>;

export type Decision = "reference" | "adopted" | "rejected" | "inconclusive";

export type Experiment = {
  id: string;
  exp: string;
  label: string;
  change: string;
  decision: Decision;
  note?: string;
  source: string;
  metrics: MetricSet;
};

export type Headline = Experiment & {
  perFold: Record<"accuracy" | "macro_f1" | "roc_auc_ovr_macro", number[]>;
  numFolds: number;
  numPatients: number;
};

export type ModalityRow = { key: string; label: string; metrics: MetricSet };

export type Reliability = {
  tier: "strong" | "moderate" | "weak" | "chance";
  label: string;
  rule: string;
  roc_auc: number;
  kappa: number;
};

export type StandaloneModel = {
  key: string;
  label: string;
  scale: string;
  split: string;
  nTrain: number;
  reliability: Reliability;
  source: string;
  metrics: MetricSet;
};

const data = raw as unknown as {
  standalone: StandaloneModel[];
  headline: Headline;
  ladder: Experiment[];
  modalityAblation: ModalityRow[];
  modalityAblationSource: string;
};

export const HEADLINE: Headline = data.headline;
export const LADDER: Experiment[] = data.ladder;
export const MODALITY_ABLATION: ModalityRow[] = data.modalityAblation;
export const STANDALONE: StandaloneModel[] = data.standalone;
export const MODALITY_ABLATION_SOURCE = data.modalityAblationSource;
export const BASELINE: Experiment = LADDER.find((e) => e.decision === "reference")!;

export const METRIC_LABELS: Record<MetricKey, { short: string; long: string; asPercent: boolean }> = {
  accuracy: { short: "Accuracy", long: "Accuracy", asPercent: true },
  balanced_accuracy: { short: "Balanced acc.", long: "Balanced accuracy", asPercent: true },
  macro_f1: { short: "Macro F1", long: "Macro F1", asPercent: false },
  roc_auc_ovr_macro: { short: "ROC-AUC", long: "ROC-AUC (one-vs-rest, macro)", asPercent: false },
  cohen_kappa: { short: "Kappa", long: "Cohen's kappa", asPercent: false },
  quadratic_weighted_kappa: { short: "QWK", long: "Quadratic-weighted kappa", asPercent: false },
};

export function formatMetric(key: MetricKey, stat: MetricStat): { value: string; std: string } {
  const { asPercent } = METRIC_LABELS[key];
  return asPercent
    ? { value: `${(stat.mean * 100).toFixed(1)}%`, std: `± ${(stat.std * 100).toFixed(1)}` }
    : { value: stat.mean.toFixed(3), std: `± ${stat.std.toFixed(3)}` };
}
