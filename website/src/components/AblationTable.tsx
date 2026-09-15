"use client";

import { useState } from "react";
import { DEMO_ABLATION_ROWS } from "@/lib/content";
import { DemoBadge } from "./DemoBadge";
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
        <DemoBadge text="Pending real experiments" />
      </Reveal>

      <Reveal delay={0.1} className="mt-12 overflow-hidden rounded-2xl border border-white/10">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-white/[0.03] text-left text-ink-muted">
              <th className="px-5 py-3 font-medium">Model</th>
              <th className="px-5 py-3 font-medium">AUROC</th>
              <th className="px-5 py-3 font-medium">Macro F1</th>
            </tr>
          </thead>
          <tbody>
            {DEMO_ABLATION_ROWS.map((row, i) => (
              <tr
                key={row.model}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
                className={`border-b border-white/5 transition-colors last:border-0 ${
                  hovered === i ? "bg-white/[0.06]" : ""
                }`}
              >
                <td className="px-5 py-3.5 text-ink">{row.model}</td>
                <td className="px-5 py-3.5 text-ink-faint">{row.auroc}</td>
                <td className="px-5 py-3.5 text-ink-faint">{row.f1}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Reveal>
      <p className="mt-4 text-xs text-ink-faint">
        Rows are the planned comparison; cells stay blank until measured on a
        patient-level held-out test split — never filled with placeholder numbers.
      </p>
    </section>
  );
}
