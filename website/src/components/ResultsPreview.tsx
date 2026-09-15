import { DEMO_METRICS } from "@/lib/content";
import { DemoBadge } from "./DemoBadge";
import { Reveal } from "./Reveal";

export function ResultsPreview() {
  return (
    <section className="relative mx-auto max-w-3xl px-6 py-32 text-center">
      <Reveal className="flex flex-col items-center gap-3">
        <p className="text-xs uppercase tracking-[0.3em] text-ink-faint">Model inference</p>
        <h2 className="max-w-xl text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          What a diagnostic readout will look like.
        </h2>
        <div className="mt-2">
          <DemoBadge />
        </div>
      </Reveal>

      <Reveal delay={0.1} className="mt-16">
        <p className="text-xs uppercase tracking-[0.3em] text-ink-faint">{DEMO_METRICS.label}</p>
        <p className="mt-4 text-5xl font-semibold tracking-tight text-ink sm:text-6xl">
          {DEMO_METRICS.grade}
        </p>
        <p className="mt-2 text-sm text-accent-champagne">{DEMO_METRICS.confidence}% confidence</p>

        <div className="mx-auto mt-14 grid max-w-md grid-cols-3 gap-6 border-t border-white/10 pt-10">
          <div>
            <div className="text-2xl font-medium text-ink-muted">{DEMO_METRICS.branchConfidence.oct}%</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">OCT</div>
          </div>
          <div>
            <div className="text-2xl font-medium text-ink-muted">{DEMO_METRICS.branchConfidence.fundus}%</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">Fundus</div>
          </div>
          <div>
            <div className="text-2xl font-medium text-accent-champagne">{DEMO_METRICS.branchConfidence.fusion}%</div>
            <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">Fused signal</div>
          </div>
        </div>
      </Reveal>

      <Reveal delay={0.2}>
        <p className="mt-12 text-xs text-ink-faint">
          Layout only — populated with real numbers once the model is trained. Never presented as a clinical diagnosis.
        </p>
      </Reveal>
    </section>
  );
}
