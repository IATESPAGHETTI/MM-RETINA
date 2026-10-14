"use client";

import { useState } from "react";
import { SINGLE_SPLIT_HISTORY } from "@/lib/content";
import { MODALITY_ABLATION, MODALITY_ABLATION_SOURCE, formatMetric, type MetricKey } from "@/lib/results";
import { Reveal } from "./Reveal";

const COLUMNS: { key: MetricKey; label: string }[] = [
  { key: "accuracy", label: "Accuracy" },
  { key: "balanced_accuracy", label: "Balanced acc." },
  { key: "macro_f1", label: "Macro F1" },
  { key: "roc_auc_ovr_macro", label: "ROC-AUC" },
];

/** The original modality ablation (fundus vs OCT vs fusion), run with the ResNet18 baselines. */
export function AblationTable() {
  const [hovered, setHovered] = useState<number | null>(null);

  return (
    <section className="relative mx-auto max-w-5xl px-6 py-20">
      <Reveal>
        <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">Modality ablation</p>
        <h2 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          Does fusion actually help?
        </h2>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-ink-muted">
          The first cross-validated comparison, run with ResNet18 encoders before the ablation series above.
          It asks the foundational question: fundus alone, OCT alone, or both.
        </p>
      </Reveal>

      <Reveal delay={0.1} className="mt-10 overflow-x-auto rounded-2xl border border-white/10">
        <table className="w-full min-w-[34rem] border-collapse text-sm">
          <caption className="sr-only">Modality ablation, mean ± std across 5 folds</caption>
          <thead>
            <tr className="border-b border-white/10 bg-white/[0.03] text-left text-ink-muted">
              <th scope="col" className="px-5 py-3 font-medium">Model</th>
              {COLUMNS.map((c) => (
                <th key={c.key} scope="col" className="px-5 py-3 font-medium">{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MODALITY_ABLATION.map((row, i) => (
              <tr
                key={row.key}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
                className={`border-b border-white/5 transition-colors last:border-0 ${
                  hovered === i ? "bg-white/[0.06]" : ""
                }`}
              >
                <th scope="row" className="px-5 py-3.5 text-left font-normal text-ink">{row.label}</th>
                {COLUMNS.map((c) => {
                  const f = formatMetric(c.key, row.metrics[c.key]);
                  return (
                    <td key={c.key} className="px-5 py-3.5 text-ink-muted">
                      {f.value} <span className="text-ink-faint">{f.std}</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </Reveal>

      <Reveal delay={0.15} className="mt-6 rounded-xl border border-white/10 bg-white/[0.03] p-4">
        <p className="text-sm text-ink">
          Fusion had the highest ROC-AUC and the tightest fold-to-fold spread. Fundus-only scored higher on
          accuracy and macro F1 but swung much more between folds; OCT-only was weakest. This pointed to
          fusion as the more reliable architecture and motivated the controlled ablation series.
        </p>
      </Reveal>

      <Reveal delay={0.2} className="mt-8">
        <h3 className="text-sm font-medium text-ink">Why cross-validation?</h3>
        <p className="mt-2 text-sm leading-relaxed text-ink-muted">
          A single train/test split made fundus-only look clearly superior. Five-fold, patient-level
          cross-validation showed that conclusion was sensitive to the particular split.
        </p>
        <p className="mt-3 text-xs text-ink-faint">{SINGLE_SPLIT_HISTORY.note}</p>
      </Reveal>

      <p className="mt-6 text-xs text-ink-faint">
        Source: {MODALITY_ABLATION_SOURCE}. Per-fold results, confusion matrices, and the earlier single-split
        numbers are in EXPERIMENTS.md.
      </p>
    </section>
  );
}
