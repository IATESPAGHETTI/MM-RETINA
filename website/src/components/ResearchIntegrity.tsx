import { RESEARCH_INTEGRITY_POINTS } from "@/lib/content";
import { GlassCard } from "./GlassCard";
import { Reveal } from "./Reveal";

export function ResearchIntegrity() {
  return (
    <section className="relative mx-auto max-w-4xl px-6 py-28">
      <Reveal>
        <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">Methodology</p>
        <h2 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Research integrity</h2>
      </Reveal>

      <Reveal delay={0.1}>
        <GlassCard className="mt-10">
          <ul className="space-y-4">
            {RESEARCH_INTEGRITY_POINTS.map((point) => (
              <li key={point} className="flex items-start gap-3 text-sm leading-relaxed text-ink-muted">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="mt-0.5 shrink-0 text-accent-cyan" aria-hidden>
                  <path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </GlassCard>
      </Reveal>
    </section>
  );
}
