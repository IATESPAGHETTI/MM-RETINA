import { ResultsPreview } from "@/components/ResultsPreview";
import { AblationTable } from "@/components/AblationTable";
import { DemoBadge } from "@/components/DemoBadge";
import { Reveal } from "@/components/Reveal";
import { DEMO_METRICS } from "@/lib/content";

export const metadata = { title: "Results — MM-RETINA" };

export default function ResultsPage() {
  return (
    <div className="pt-20">
      <section className="mx-auto max-w-4xl px-6 pt-20 pb-8 text-center">
        <Reveal>
          <p className="mb-3 text-xs uppercase tracking-[0.3em] text-ink-faint">Results</p>
          <h1 className="text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
            Metrics
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-ink-muted">
            No model has been trained on GAMMA yet in this project. The layout
            below is real; the numbers are not — every metric is blank until
            it&apos;s measured on a held-out, patient-level test split.
          </p>
        </Reveal>
      </section>

      <section className="mx-auto max-w-4xl px-6 py-8">
        <Reveal className="mb-10 flex justify-center">
          <DemoBadge text="No experiments run yet" />
        </Reveal>
        <div className="grid grid-cols-2 gap-x-6 gap-y-10 border-t border-white/10 pt-10 sm:grid-cols-5">
          {DEMO_METRICS.metrics.map((m, i) => (
            <Reveal key={m.name} delay={i * 0.05}>
              <div className="text-4xl font-semibold tracking-tight text-ink-faint sm:text-5xl">{m.value}</div>
              <div className="mt-2 text-xs uppercase tracking-wider text-ink-muted">{m.name}</div>
            </Reveal>
          ))}
        </div>
      </section>

      <ResultsPreview />
      <AblationTable />
    </div>
  );
}
