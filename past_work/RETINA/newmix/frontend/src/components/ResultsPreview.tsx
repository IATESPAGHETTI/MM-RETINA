import Link from "next/link";
import { CV_RESULTS } from "@/lib/content";
import { Reveal } from "./Reveal";

export function ResultsPreview() {
  const fusion = CV_RESULTS.runs.find((r) => r.name.startsWith("Fusion"))!;
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
          {fusion.rocAuc.toFixed(3)}
        </p>
        <p className="mt-2 text-sm text-accent-champagne">± {fusion.rocAucStd.toFixed(3)} across 5 folds</p>

        <div className="mx-auto mt-14 grid max-w-md grid-cols-3 gap-6 border-t border-white/10 pt-10">
          <div>
            <div className="text-2xl font-medium text-ink-muted">{(fusion.accuracy * 100).toFixed(0)}%</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">Accuracy</div>
          </div>
          <div>
            <div className="text-2xl font-medium text-ink-muted">{(fusion.balancedAccuracy * 100).toFixed(0)}%</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">Balanced acc.</div>
          </div>
          <div>
            <div className="text-2xl font-medium text-accent-champagne">{fusion.macroF1.toFixed(2)}</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">Macro F1</div>
          </div>
        </div>
      </Reveal>

      <Reveal delay={0.2} className="mt-14">
        <Link
          href="/demo"
          className="inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3 text-sm font-medium text-bg transition-transform hover:-translate-y-0.5"
        >
          Try the live model
        </Link>
        <p className="mx-auto mt-4 max-w-lg text-xs text-ink-faint">
          Run the actual trained model on a fundus photo, OCT B-scan, or
          both. Research prototype — never a clinical diagnosis.
        </p>
      </Reveal>
    </section>
  );
}
