import { DEMO_METRICS } from "@/lib/content";
import { GlassCard } from "./GlassCard";
import { DemoBadge } from "./DemoBadge";
import { Reveal } from "./Reveal";

export function ResultsPreview() {
  return (
    <section className="relative mx-auto max-w-6xl px-6 py-28">
      <Reveal className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">Prediction demo</p>
          <h2 className="max-w-xl text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            What the diagnostic card will look like.
          </h2>
        </div>
        <DemoBadge />
      </Reveal>

      <Reveal delay={0.1} className="mt-12 mx-auto max-w-md">
        <GlassCard strong>
          <div className="mb-5 flex items-center justify-between text-xs text-ink-muted">
            <span>AI ANALYSIS</span>
            <span>{DEMO_METRICS.label}</span>
          </div>

          <div className="mb-1 text-sm text-ink-muted">Glaucoma grade</div>
          <div className="mb-4 flex items-baseline gap-3">
            <span className="text-2xl font-semibold text-ink">{DEMO_METRICS.grade}</span>
            <span className="text-sm text-accent-cyan">{DEMO_METRICS.confidence}%</span>
          </div>

          <div className="grid grid-cols-3 gap-3 border-t border-white/10 pt-4 text-center">
            <div>
              <div className="text-lg font-medium text-ink">{DEMO_METRICS.branchConfidence.oct}%</div>
              <div className="text-xs text-ink-muted">OCT</div>
            </div>
            <div>
              <div className="text-lg font-medium text-ink">{DEMO_METRICS.branchConfidence.fundus}%</div>
              <div className="text-xs text-ink-muted">Fundus</div>
            </div>
            <div>
              <div className="text-lg font-medium text-accent-cyan">{DEMO_METRICS.branchConfidence.fusion}%</div>
              <div className="text-xs text-ink-muted">Fusion</div>
            </div>
          </div>
        </GlassCard>
        <p className="mt-4 text-center text-xs text-ink-faint">
          Layout only — populated with real numbers once the model is trained. Never presented as a clinical diagnosis.
        </p>
      </Reveal>
    </section>
  );
}
