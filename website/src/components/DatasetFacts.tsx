import { VERIFIED_GAMMA_FACTS } from "@/lib/content";
import { GlassCard } from "./GlassCard";
import { Reveal } from "./Reveal";

const STATS = [
  { label: "Paired samples", value: VERIFIED_GAMMA_FACTS.pairedSamples },
  { label: "Patients", value: VERIFIED_GAMMA_FACTS.patients },
  { label: "B-scans / volume", value: VERIFIED_GAMMA_FACTS.bscansPerVolume },
  { label: "Grading classes", value: VERIFIED_GAMMA_FACTS.classes.length },
];

export function DatasetFacts() {
  return (
    <section className="relative mx-auto max-w-6xl px-6 py-28">
      <Reveal>
        <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">Dataset</p>
        <h2 className="max-w-2xl text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          Built on GAMMA, a genuinely paired dataset.
        </h2>
        <p className="mt-4 max-w-2xl text-ink-muted">
          Every OCT volume and fundus image here comes from the same eye and
          examination — not two datasets stitched together by matching
          disease labels.
        </p>
      </Reveal>

      <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {STATS.map((s, i) => (
          <Reveal key={s.label} delay={i * 0.06}>
            <GlassCard className="text-center">
              <div className="text-3xl font-semibold text-ink">{s.value}</div>
              <div className="mt-1 text-xs text-ink-muted">{s.label}</div>
            </GlassCard>
          </Reveal>
        ))}
      </div>

      <Reveal delay={0.2} className="mt-6">
        <GlassCard className="flex flex-col gap-3 text-sm text-ink-muted sm:flex-row sm:items-center sm:justify-between">
          <span>
            License: <span className="text-ink">{VERIFIED_GAMMA_FACTS.license}</span> — official
            release via the GAMMA challenge page.
          </span>
          <a
            href={VERIFIED_GAMMA_FACTS.officialUrl}
            target="_blank"
            rel="noreferrer"
            className="text-ink underline underline-offset-4 hover:text-accent-cyan"
          >
            gamma.grand-challenge.org
          </a>
        </GlassCard>
      </Reveal>
    </section>
  );
}
