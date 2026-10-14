import clsx from "clsx";
import { STANDALONE, formatMetric, type MetricKey, type Reliability } from "@/lib/results";
import { Reveal } from "./Reveal";

const COLS: { key: MetricKey; label: string }[] = [
  { key: "accuracy", label: "Accuracy" },
  { key: "macro_f1", label: "Macro F1" },
  { key: "roc_auc_ovr_macro", label: "ROC-AUC" },
  { key: "cohen_kappa", label: "Kappa" },
  { key: "quadratic_weighted_kappa", label: "QWK" },
];

const TIER: Record<Reliability["tier"], string> = {
  strong: "border-accent-champagne/50 bg-accent-champagne/10 text-accent-champagne",
  moderate: "border-accent-olive/50 bg-accent-olive/10 text-accent-olive",
  weak: "border-amber-300/30 bg-amber-300/10 text-amber-200",
  chance: "border-red-400/30 bg-red-400/10 text-red-200",
};

/** HVF and RNFL/GCC: separate cohorts, separate models, no fusion with GAMMA. */
export function StandaloneResults() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <Reveal>
        <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">Standalone models</p>
        <h2 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          Where fusion isn&apos;t possible, one encoder each.
        </h2>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-ink-muted">
          The visual-field and RNFL/GCC cohorts have no valid patient link to the fundus + OCT data or to each other,
          so pairing them would mean inventing matches. Each gets its own linear model, graded on its own scale, and
          is reported with the reliability its cross-validation actually earned.
        </p>
      </Reveal>

      <div className="mt-10 grid gap-5 md:grid-cols-2">
        {STANDALONE.map((m, i) => (
          <Reveal key={m.key} delay={i * 0.06}>
            <article className="h-full rounded-2xl border border-white/10 p-6">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h3 className="text-base font-medium text-ink">{m.label}</h3>
                <span className={clsx("rounded-full border px-2.5 py-0.5 text-[11px]", TIER[m.reliability.tier])}>
                  {m.reliability.label}
                </span>
              </div>
              <p className="mt-1 text-xs text-ink-faint">
                {m.scale} · {m.nTrain} eyes · {m.split}
              </p>
              <dl className="mt-5 grid grid-cols-3 gap-x-4 gap-y-4 sm:grid-cols-5 md:grid-cols-3 lg:grid-cols-5">
                {COLS.map((c) => {
                  const f = formatMetric(c.key, m.metrics[c.key]);
                  return (
                    <div key={c.key}>
                      <dt className="text-[10px] uppercase tracking-wider text-ink-faint">{c.label}</dt>
                      <dd className="mt-1 text-lg font-medium tabular-nums text-ink">{f.value}</dd>
                      <dd className="text-[10px] text-ink-faint">{f.std}</dd>
                    </div>
                  );
                })}
              </dl>
            </article>
          </Reveal>
        ))}
      </div>

      <p className="mt-5 text-xs text-ink-faint">
        HVF excludes MD / PSD / VFI, which are near-duplicates of how the severity labels were assigned; including them
        reaches QWK ≈ 0.97 but only by recovering the labelling rule (see EXPERIMENTS.md, EXP-C01 / C01b). RNFL/GCC has
        no patient ID, so its folds are plain-stratified and its numbers are optimistic. Source:{" "}
        {STANDALONE.map((m) => m.source).join(", ")}.
      </p>
    </section>
  );
}
