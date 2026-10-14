import { HEADLINE, METRIC_LABELS, formatMetric, type MetricKey } from "@/lib/results";
import { Reveal } from "./Reveal";

const PRIMARY: MetricKey[] = [
  "accuracy",
  "balanced_accuracy",
  "macro_f1",
  "roc_auc_ovr_macro",
  "cohen_kappa",
  "quadratic_weighted_kappa",
];

/** Per-fold dots: shows the spread behind each mean so variance is never hidden. */
function FoldStrip({ values }: { values: number[] }) {
  const lo = 0.5;
  return (
    <div
      className="relative mt-3 h-1.5 w-full rounded-full bg-white/10"
      role="img"
      aria-label={`Per-fold values: ${values.map((v) => v.toFixed(2)).join(", ")}`}
    >
      {values.map((v, i) => (
        <span
          key={i}
          className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent-champagne/80 ring-2 ring-[var(--bg)]"
          style={{ left: `${Math.min(100, Math.max(0, ((v - lo) / (1 - lo)) * 100))}%` }}
        />
      ))}
    </div>
  );
}

export function HeadlineMetrics() {
  const folds: Partial<Record<MetricKey, number[]>> = {
    accuracy: HEADLINE.perFold.accuracy,
    macro_f1: HEADLINE.perFold.macro_f1,
    roc_auc_ovr_macro: HEADLINE.perFold.roc_auc_ovr_macro,
  };

  return (
    <section className="mx-auto max-w-5xl px-6 py-10">
      <Reveal className="mb-8 flex flex-col gap-1 text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-ink-faint">
          Frozen best model · {HEADLINE.exp} · {HEADLINE.id}
        </p>
        <p className="text-sm text-ink-muted">
          EfficientNet-B0 fundus + ResNet18 OCT (8 slices) with cross-modal fusion. Mean ± std across{" "}
          {HEADLINE.numFolds} patient-level folds, {HEADLINE.numPatients} patients.
        </p>
      </Reveal>

      <div className="grid grid-cols-2 gap-x-8 gap-y-10 border-t border-white/10 pt-10 md:grid-cols-3">
        {PRIMARY.map((key, i) => {
          const f = formatMetric(key, HEADLINE.metrics[key]);
          const strip = folds[key];
          return (
            <Reveal key={key} delay={i * 0.05}>
              <div className="text-4xl font-semibold tracking-tight text-ink sm:text-5xl">{f.value}</div>
              <div className="mt-1 text-xs text-ink-faint">{f.std}</div>
              <div className="mt-2 text-xs uppercase tracking-wider text-ink-muted">
                {METRIC_LABELS[key].short}
              </div>
              {strip && <FoldStrip values={strip} />}
              {strip && <div className="mt-1.5 text-[10px] text-ink-faint">each dot = one held-out fold</div>}
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}
