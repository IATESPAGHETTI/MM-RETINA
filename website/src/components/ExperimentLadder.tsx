import clsx from "clsx";
import {
  BASELINE,
  LADDER,
  METRIC_LABELS,
  formatMetric,
  type Decision,
  type MetricKey,
} from "@/lib/results";
import { Reveal } from "./Reveal";

const BAR_METRICS: MetricKey[] = ["accuracy", "macro_f1", "roc_auc_ovr_macro"];

const DECISION_STYLE: Record<Decision, { label: string; className: string }> = {
  reference: { label: "Reference", className: "border-white/15 text-ink-muted" },
  adopted: { label: "Adopted", className: "border-accent-champagne/50 bg-accent-champagne/10 text-accent-champagne" },
  rejected: { label: "Rejected", className: "border-accent-copper/40 bg-accent-copper/10 text-accent-copper" },
  inconclusive: { label: "Not adopted", className: "border-accent-olive/40 bg-accent-olive/10 text-accent-olive" },
};

function Delta({ value }: { value: number }) {
  if (Math.abs(value) < 0.0005) return <span className="text-ink-faint">±0.000</span>;
  const up = value > 0;
  return (
    <span className={up ? "text-accent-champagne" : "text-accent-copper"}>
      {up ? "+" : "−"}
      {Math.abs(value).toFixed(3)}
    </span>
  );
}

/**
 * The ablation series as a ladder: every change tested against the same folds,
 * with the decision that was actually recorded in EXPERIMENTS.md. Failed and
 * inconclusive experiments are shown on purpose.
 */
export function ExperimentLadder() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <Reveal>
        <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">Ablation series</p>
        <h2 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          Six controlled changes. One survived.
        </h2>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-ink-muted">
          Each experiment changes one thing against the same patient-level folds, seed, and training recipe.
          Deltas are versus the {BASELINE.exp} baseline. Rejected and inconclusive results are listed — they are
          part of the evidence.
        </p>
      </Reveal>

      <ol className="mt-10 divide-y divide-white/8 border-y border-white/10">
        {LADDER.map((e, i) => {
          const d = DECISION_STYLE[e.decision];
          const adopted = e.decision === "adopted";
          return (
            <li
              key={e.id}
              className={clsx("transition-colors hover:bg-white/[0.03]", adopted && "bg-accent-champagne/[0.04]")}
            >
              <Reveal delay={i * 0.04} className="grid gap-5 px-2 py-6 md:grid-cols-[1.25fr_1fr] md:px-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className="font-mono text-xs text-ink-faint">{e.exp}</span>
                    <h3 className="text-base font-medium text-ink">{e.label}</h3>
                    <span className={clsx("rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider", d.className)}>
                      {d.label}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-ink-muted">{e.change}</p>
                  {e.note && <p className="mt-1.5 text-xs leading-relaxed text-ink-faint">{e.note}</p>}
                </div>

                <dl className="space-y-2.5">
                  {BAR_METRICS.map((m) => {
                    const stat = e.metrics[m];
                    const f = formatMetric(m, stat);
                    const delta = stat.mean - BASELINE.metrics[m].mean;
                    return (
                      <div key={m} className="grid grid-cols-[5.5rem_1fr_6.5rem] items-center gap-3 text-xs">
                        <dt className="text-ink-faint">{METRIC_LABELS[m].short}</dt>
                        <dd className="relative h-1.5 overflow-hidden rounded-full bg-white/10" aria-hidden>
                          <span
                            className={clsx(
                              "absolute inset-y-0 left-0 rounded-full",
                              adopted ? "bg-accent-champagne" : "bg-ink-muted/60"
                            )}
                            style={{ width: `${stat.mean * 100}%` }}
                          />
                        </dd>
                        <dd className="text-right tabular-nums text-ink">
                          {f.value}
                          {e.decision !== "reference" && (
                            <span className="ml-1.5 text-[10px]">
                              <Delta value={delta} />
                            </span>
                          )}
                        </dd>
                      </div>
                    );
                  })}
                </dl>
              </Reveal>
            </li>
          );
        })}
      </ol>

      <p className="mt-5 text-xs text-ink-faint">
        Source: results/cv_fusion_*/summary.json via scripts/export_site_results.py. With only 100 labelled
        patients, differences smaller than about one fold-standard-deviation should not be read as real.
      </p>
    </section>
  );
}
