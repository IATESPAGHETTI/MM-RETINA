import { REAL_RESULTS } from "@/lib/content";
import { Reveal } from "./Reveal";

export function ResultsPreview() {
  const ex = REAL_RESULTS.exampleInference;
  return (
    <section className="relative mx-auto max-w-3xl px-6 py-32 text-center">
      <Reveal className="flex flex-col items-center gap-3">
        <p className="text-xs uppercase tracking-[0.3em] text-ink-faint">Model inference</p>
        <h2 className="max-w-xl text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          A real prediction from a real held-out test sample.
        </h2>
      </Reveal>

      <Reveal delay={0.1} className="mt-16">
        <p className="text-xs uppercase tracking-[0.3em] text-ink-faint">
          GAMMA sample {ex.sampleId} — true label: {ex.trueLabel}
        </p>
        <p className="mt-4 text-5xl font-semibold tracking-tight text-ink sm:text-6xl">
          {ex.predictedLabel}
        </p>
        <p className="mt-2 text-sm text-accent-champagne">{ex.confidence}% confidence — correct</p>

        <div className="mx-auto mt-14 grid max-w-md grid-cols-3 gap-6 border-t border-white/10 pt-10">
          <div>
            <div className="text-2xl font-medium text-ink-muted">{ex.probNormal}%</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">Normal</div>
          </div>
          <div>
            <div className="text-2xl font-medium text-ink-muted">{ex.probEarly}%</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">Early</div>
          </div>
          <div>
            <div className="text-2xl font-medium text-accent-champagne">{ex.probProgressive}%</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">Progressive</div>
          </div>
        </div>
      </Reveal>

      <Reveal delay={0.2}>
        <p className="mx-auto mt-12 max-w-lg text-xs text-ink-faint">
          From the fusion model&apos;s real softmax output on GAMMA training
          sample 0058 (held out from training/validation). One correct
          prediction on one sample is not evidence of general accuracy —
          see the ablation results below and EXPERIMENTS.md for the full
          picture. Research prototype — never a clinical diagnosis.
        </p>
      </Reveal>
    </section>
  );
}
