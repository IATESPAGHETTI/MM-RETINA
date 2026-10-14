import Link from "next/link";
import { HEADLINE } from "@/lib/results";
import { Reveal } from "./Reveal";

export function ResultsPreview() {
  const { accuracy, balanced_accuracy, macro_f1, roc_auc_ovr_macro, quadratic_weighted_kappa } = HEADLINE.metrics;
  return (
    <section className="relative mx-auto max-w-3xl px-6 py-32 text-center">
      <Reveal className="flex flex-col items-center gap-3">
        <p className="text-xs uppercase tracking-[0.3em] text-ink-faint">5-fold cross-validation</p>
        <h2 className="max-w-xl text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          The fusion model, measured honestly.
        </h2>
      </Reveal>

      <Reveal delay={0.1} className="mt-16">
        <p className="text-xs uppercase tracking-[0.3em] text-ink-faint">Fusion — mean ROC-AUC</p>
        <p className="mt-4 text-5xl font-semibold tracking-tight text-ink sm:text-6xl">
          {roc_auc_ovr_macro.mean.toFixed(3)}
        </p>
        <p className="mt-2 text-sm text-accent-champagne">
          ± {roc_auc_ovr_macro.std.toFixed(3)} across {HEADLINE.numFolds} folds
        </p>

        <div className="mx-auto mt-14 grid max-w-lg grid-cols-2 gap-6 border-t border-white/10 pt-10 sm:grid-cols-4">
          <div>
            <div className="text-2xl font-medium text-ink-muted">{(accuracy.mean * 100).toFixed(0)}%</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">Accuracy</div>
          </div>
          <div>
            <div className="text-2xl font-medium text-ink-muted">{(balanced_accuracy.mean * 100).toFixed(0)}%</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">Balanced acc.</div>
          </div>
          <div>
            <div className="text-2xl font-medium text-ink-muted">{macro_f1.mean.toFixed(2)}</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">Macro F1</div>
          </div>
          <div>
            <div className="text-2xl font-medium text-accent-champagne">{quadratic_weighted_kappa.mean.toFixed(2)}</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">QWK</div>
          </div>
        </div>
      </Reveal>

      <Reveal delay={0.2} className="mt-14">
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/demo"
            className="inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3 text-sm font-medium text-bg transition-transform hover:-translate-y-0.5"
          >
            Try the live model
          </Link>
          <Link
            href="/results"
            className="text-sm text-ink-muted underline underline-offset-4 transition-colors hover:text-ink"
          >
            See every experiment
          </Link>
        </div>
        <p className="mx-auto mt-4 max-w-lg text-xs text-ink-faint">
          Run the actual trained model on a fundus photo, OCT B-scan, or both. Research prototype — never a
          clinical diagnosis.
        </p>
      </Reveal>
    </section>
  );
}
