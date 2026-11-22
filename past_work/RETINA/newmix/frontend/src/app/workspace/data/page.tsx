"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Audit } from "@/lib/api";
import { Badge, Callout, ErrorNote, LoadingBlock, PageHeader, Panel, Stat } from "@/components/ui/primitives";

export default function DataPage() {
  const [a, setA] = useState<Audit | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    setError(null);
    api.audit().then(setA).catch((e: Error) => setError(e.message));
  }, []);
  useEffect(() => {
    const t = setTimeout(load, 0);
    return () => clearTimeout(t);
  }, [load]);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Evidence"
        title="Data and integrity"
        description="What the combined datasets contain, how they relate, and the checks that decided what each model is allowed to learn from. Recomputed from the raw files by an audit script."
      />
      {error && <ErrorNote message={error} onRetry={load} />}
      {!a && !error && <LoadingBlock label="Loading audit…" />}
      {a && <Body a={a} />}
    </div>
  );
}

function Body({ a }: { a: Audit }) {
  const r = a.research;
  const s = a.sankara;
  const total = r.glaucoma.Mild + r.glaucoma.Moderate + r.glaucoma.Severe;

  const flow: { name: string; n: string; link: string; tone: "ok" | "warn" | "bad" | "neutral" }[] = [
    { name: "Research Excel + OCT B-scans", n: `${r.eyes} eyes`, link: "Master table. Each scan maps 1:1 to a row.", tone: "ok" },
    ...(s
      ? [
          { name: "Sankara RNFL/GCC workbook", n: `${s.rnfl_gcc_rows} rows`, link: `${s.rnfl_gcc_exact_matches_in_research} rows are the same eyes as the master table (exact 12-value match). The rest have no images.`, tone: "warn" as const },
          { name: "Sankara HVF visual-field reports", n: `${s.hvf_files} files`, link: `${s.hvf_unique_strict_matches} link to exactly one master-table eye (MD + eye + age). The others cannot be placed.`, tone: "warn" as const },
          { name: "Sankara fundus photographs", n: `${s.fundus_images} images`, link: "Glaucoma only, no patient identifier. Not linkable, so not used for training.", tone: "bad" as const },
          { name: "Sankara “disc photos”", n: `${s.disc_photos} images`, link: `${s.disc_identical_to_fundus} are byte-identical copies of the fundus photographs.`, tone: "bad" as const },
        ]
      : []),
  ];

  return (
    <>
      <Panel title="Research cohort" subtitle="Sankara Nethralaya, optic-nerve-head OCT with clinical measurements">
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
          <Stat label="Eyes" value={String(r.eyes)} hint={`${r.reconstructed_patients} reconstructed patients`} />
          <Stat label="Controls" value={String(r.controls)} />
          <Stat label="Glaucoma" value={String(total)} hint={`Mild ${r.glaucoma.Mild} · Moderate ${r.glaucoma.Moderate} · Severe ${r.glaucoma.Severe}`} />
          <Stat label="Mean age" value={`${r.mean_age.glaucoma} / ${r.mean_age.control}`} hint="glaucoma / control" />
        </div>
      </Panel>

      <Panel title="How the datasets relate" subtitle="Which records can be joined, and which cannot" pad={false}>
        <ul>
          {flow.map((f) => (
            <li key={f.name} className="flex flex-col gap-1 border-b border-line px-5 py-4 last:border-0 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
              <div className="min-w-0">
                <p className="text-sm font-medium text-ink">{f.name}</p>
                <p className="mt-0.5 text-sm text-ink-muted">{f.link}</p>
              </div>
              <Badge tone={f.tone}>{f.n}</Badge>
            </li>
          ))}
        </ul>
        {!s && <p className="px-5 pb-4 text-xs text-ink-faint">Sankara checks were not run (raw files not supplied to the audit script).</p>}
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Findings that changed the models">
          <ol className="space-y-5 text-sm leading-relaxed text-ink-muted">
            <li>
              <span className="font-medium text-ink">Severity is a rule on visual-field MD.</span> The −6 / −12 dB cut-offs reproduce the label on {(r.md_rule_agreement * 100).toFixed(0)}% of glaucoma eyes. MD is therefore never a model input; it only drives a displayed staging rule.
            </li>
            <li>
              <span className="font-medium text-ink">Missingness leaks the label.</span> Pachymetry is missing for {r.pachy_missing_pct.glaucoma}% of glaucoma rows but {r.pachy_missing_pct.control}% of controls; central foveal thickness for {r.cft_missing_pct.glaucoma}% vs {r.cft_missing_pct.control}%. Both columns are excluded.
            </li>
            <li>
              <span className="font-medium text-ink">Controls are younger</span> ({r.mean_age.control} vs {r.mean_age.glaucoma} years). Age is tested as an ablation so it cannot silently carry the result.
            </li>
            <li>
              <span className="font-medium text-ink">No patient IDs.</span> Both eyes of a patient are rebuilt from adjacent rows and always stay in the same fold.
            </li>
          </ol>
        </Panel>
        <Panel title="Handled on purpose">
          <ul className="space-y-4 text-sm leading-relaxed text-ink-muted">
            <li>
              <span className="font-medium text-ink">Identifiers in images.</span> The fundus photographs carry burned-in text in a corner. They are not displayed or used for record linkage.
            </li>
            <li>
              <span className="font-medium text-ink">Small classes.</span> Moderate ({r.glaucoma.Moderate}) and Severe ({r.glaucoma.Severe}) eyes are few, so per-class recall is uncertain. Intervals are reported where it matters.
            </li>
            <li>
              <span className="font-medium text-ink">Paper claims.</span> The 87.5% four-class and 92.5% binary figures were not reproduced under patient-grouped evaluation; see the Models page for what the same data supports.
            </li>
          </ul>
          <div className="mt-5"><Callout tone="info">To audit with the raw files: <code className="rounded bg-white/5 px-1.5 py-0.5 text-xs">python ml/glaucoma/audit_data.py</code></Callout></div>
        </Panel>
      </div>
    </>
  );
}
