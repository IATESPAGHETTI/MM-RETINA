"use client";

import { useState } from "react";
import { CV_RESULTS, SINGLE_SPLIT_HISTORY } from "@/lib/content";
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
            {CV_RESULTS.runs.map((row, i) => (
              <tr
                key={row.name}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
                className={`border-b border-white/5 transition-colors last:border-0 ${
                  hovered === i ? "bg-white/[0.06]" : ""
                }`}
              >
                <td className="px-5 py-3.5 text-ink">{row.name}</td>
                <td className="px-5 py-3.5 text-ink-muted">
                  {(row.accuracy * 100).toFixed(1)}% <span className="text-ink-faint">± {(row.accuracyStd * 100).toFixed(1)}</span>
                </td>
                <td className="px-5 py-3.5 text-ink-muted">
                  {(row.balancedAccuracy * 100).toFixed(1)}% <span className="text-ink-faint">± {(row.balancedAccuracyStd * 100).toFixed(1)}</span>
                </td>
                <td className="px-5 py-3.5 text-ink-muted">
                  {row.macroF1.toFixed(3)} <span className="text-ink-faint">± {row.macroF1Std.toFixed(3)}</span>
                </td>
                <td className="px-5 py-3.5 text-ink-muted">
                  {row.rocAuc.toFixed(3)} <span className="text-ink-faint">± {row.rocAucStd.toFixed(3)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Reveal>

      <Reveal delay={0.15} className="mt-6 rounded-xl border border-white/10 bg-white/[0.03] p-4">
        <p className="text-sm text-ink">{CV_RESULTS.interpretation}</p>
      </Reveal>

      <Reveal delay={0.2} className="mt-8">
        <h3 className="text-sm font-medium text-ink">Why cross-validation?</h3>
        <p className="mt-2 text-sm leading-relaxed text-ink-muted">{CV_RESULTS.whyCrossValidation}</p>
        <p className="mt-3 text-xs text-ink-faint">{SINGLE_SPLIT_HISTORY.note}</p>
      </Reveal>

      <p className="mt-6 text-xs text-ink-faint">{CV_RESULTS.methodologyNote} Full per-fold results, confusion matrices, and the earlier single-split numbers are in EXPERIMENTS.md.</p>
    </section>
  );
}
