"use client";

import { useState } from "react";
import { REAL_RESULTS } from "@/lib/content";
import { Reveal } from "./Reveal";

export function AblationTable() {
  const [hovered, setHovered] = useState<number | null>(null);

  return (
    <section className="relative mx-auto max-w-4xl px-6 py-28">
      <Reveal className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">Ablation study</p>
          <h2 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            Does fusion actually help?
          </h2>
        </div>
      </Reveal>

      <Reveal delay={0.1} className="mt-12 overflow-hidden rounded-2xl border border-white/10">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-white/[0.03] text-left text-ink-muted">
              <th className="px-5 py-3 font-medium">Model</th>
              <th className="px-5 py-3 font-medium">Accuracy</th>
              <th className="px-5 py-3 font-medium">Balanced acc.</th>
              <th className="px-5 py-3 font-medium">Macro F1</th>
              <th className="px-5 py-3 font-medium">ROC-AUC</th>
            </tr>
          </thead>
          <tbody>
            {REAL_RESULTS.runs.map((row, i) => (
              <tr
                key={row.name}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
                className={`border-b border-white/5 transition-colors last:border-0 ${
                  hovered === i ? "bg-white/[0.06]" : ""
                }`}
              >
                <td className="px-5 py-3.5 text-ink">{row.name}</td>
                <td className="px-5 py-3.5 text-ink-muted">{(row.accuracy * 100).toFixed(1)}%</td>
                <td className="px-5 py-3.5 text-ink-muted">{(row.balancedAccuracy * 100).toFixed(1)}%</td>
                <td className="px-5 py-3.5 text-ink-muted">{row.macroF1.toFixed(3)}</td>
                <td className="px-5 py-3.5 text-ink-muted">{row.rocAuc.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Reveal>

      <Reveal delay={0.15} className="mt-6 rounded-xl border border-amber-300/20 bg-amber-300/[0.06] p-4">
        <p className="text-sm text-amber-200">
          On this run, fundus-only outperformed the fusion model — the
          opposite of what this project set out to show.
        </p>
        <p className="mt-2 text-xs text-ink-faint">{REAL_RESULTS.caveat}</p>
      </Reveal>

      <p className="mt-4 text-xs text-ink-faint">
        Test set: {REAL_RESULTS.testSetSize} GAMMA samples, held out from
        training and validation at the patient level. Full methodology,
        hyperparameters, and confusion matrices in EXPERIMENTS.md.
      </p>
    </section>
  );
}
