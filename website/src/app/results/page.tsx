import { ResultsPreview } from "@/components/ResultsPreview";
import { AblationTable } from "@/components/AblationTable";
import { Reveal } from "@/components/Reveal";
import { REAL_RESULTS } from "@/lib/content";

export const metadata = { title: "Results — MM-RETINA" };

const fusionRun = REAL_RESULTS.runs.find((r) => r.name.startsWith("Fusion"))!;

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
            The first real training runs on GAMMA finished on 2026-09-17.
            Numbers below are real, measured on a held-out, patient-level
            test split — and preliminary, from a single 14-sample split.
          </p>
        </Reveal>
      </section>

      <section className="mx-auto max-w-4xl px-6 py-8">
        <Reveal className="mb-3 text-center text-xs uppercase tracking-[0.3em] text-ink-faint">
          Fusion model (fundus + OCT)
        </Reveal>
        <div className="grid grid-cols-2 gap-x-6 gap-y-10 border-t border-white/10 pt-10 sm:grid-cols-4">
          {[
            { name: "Accuracy", value: `${(fusionRun.accuracy * 100).toFixed(1)}%` },
            { name: "Balanced acc.", value: `${(fusionRun.balancedAccuracy * 100).toFixed(1)}%` },
            { name: "Macro F1", value: fusionRun.macroF1.toFixed(3) },
            { name: "ROC-AUC", value: fusionRun.rocAuc.toFixed(3) },
          ].map((m, i) => (
            <Reveal key={m.name} delay={i * 0.05}>
              <div className="text-4xl font-semibold tracking-tight text-ink sm:text-5xl">{m.value}</div>
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
