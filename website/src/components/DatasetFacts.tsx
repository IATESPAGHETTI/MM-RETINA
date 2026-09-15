import { VERIFIED_GAMMA_FACTS } from "@/lib/content";
import { Reveal } from "./Reveal";

const STATS = [
  { label: "Paired samples", value: VERIFIED_GAMMA_FACTS.pairedSamples },
  { label: "Patients", value: VERIFIED_GAMMA_FACTS.patients },
  { label: "B-scans / volume", value: VERIFIED_GAMMA_FACTS.bscansPerVolume },
  { label: "Grading classes", value: VERIFIED_GAMMA_FACTS.classes.length },
];

export function DatasetFacts() {
  return (
    <section className="relative mx-auto max-w-5xl px-6 py-32">
      <Reveal>
        <p className="mb-4 text-xs uppercase tracking-[0.3em] text-ink-faint">Dataset</p>
        <h2 className="max-w-xl text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
          Built on GAMMA, a genuinely paired dataset.
        </h2>
        <p className="mt-5 max-w-xl text-ink-muted">
          Every OCT volume and fundus image here comes from the same eye and
          examination — not two datasets stitched together by matching
          disease labels.
        </p>
      </Reveal>

      <div className="mt-20 grid grid-cols-2 gap-x-6 gap-y-14 border-t border-white/10 pt-14 sm:grid-cols-4">
        {STATS.map((s, i) => (
          <Reveal key={s.label} delay={i * 0.08}>
            <div className="text-5xl font-semibold tracking-tight text-ink sm:text-6xl">{s.value}</div>
            <div className="mt-2 text-xs uppercase tracking-wider text-ink-muted">{s.label}</div>
          </Reveal>
        ))}
      </div>

      <Reveal delay={0.25} className="mt-14 flex flex-col gap-2 border-t border-white/10 pt-8 text-sm text-ink-muted sm:flex-row sm:items-center sm:justify-between">
        <span>
          License: <span className="text-ink">{VERIFIED_GAMMA_FACTS.license}</span> — official
          release via the GAMMA challenge page.
        </span>
        <a
          href={VERIFIED_GAMMA_FACTS.officialUrl}
          target="_blank"
          rel="noreferrer"
          className="text-ink underline underline-offset-4 hover:text-accent-champagne"
        >
          gamma.grand-challenge.org
        </a>
      </Reveal>
    </section>
  );
}
