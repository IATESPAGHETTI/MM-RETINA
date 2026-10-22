import { RESEARCH_INTEGRITY_POINTS } from "@/lib/content";
import { Reveal } from "./Reveal";

export function ResearchIntegrity() {
  return (
    <section className="relative mx-auto max-w-3xl px-6 py-32">
      <Reveal>
        <p className="mb-4 text-xs uppercase tracking-[0.3em] text-ink-faint">Methodology</p>
        <h2 className="text-4xl font-semibold tracking-tight text-ink sm:text-5xl">Research integrity</h2>
      </Reveal>

      <ol className="mt-16 space-y-10 border-t border-white/10 pt-10">
        {RESEARCH_INTEGRITY_POINTS.map((point, i) => (
          <Reveal key={point} delay={i * 0.06}>
            <li className="flex gap-6">
              <span className="w-8 shrink-0 text-sm text-ink-faint tabular-nums">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="text-base leading-relaxed text-ink-muted">{point}</span>
            </li>
          </Reveal>
        ))}
      </ol>
    </section>
  );
}
