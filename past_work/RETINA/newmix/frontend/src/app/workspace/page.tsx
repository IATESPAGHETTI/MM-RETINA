"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type ModelsInfo } from "@/lib/api";
import { clearRuns, useRuns } from "@/lib/history";
import { serviceSummary, useHealth } from "@/lib/useHealth";
import { Badge, Button, EmptyState, PageHeader, Panel, Stat } from "@/components/ui/primitives";

const FLOWS = [
  {
    href: "/workspace/glaucoma",
    title: "Glaucoma assessment",
    body: "OCT B-scan plus RNFL/GCC measurements. Stage, attention map and the drivers behind it.",
    tag: "OCT + clinical",
  },
  {
    href: "/workspace/glaucoma/multimodal",
    title: "Multimodal grading",
    body: "Fundus photograph and OCT volume fused into a Normal / Early / Progressive grade.",
    tag: "Fundus + OCT",
  },
  {
    href: "/workspace/diabetes",
    title: "Diabetes retina analysis",
    body: "Vessel segmentation, fractal complexity and an experimental HbA1c estimate.",
    tag: "Fundus",
  },
];

const ago = (t: number) => {
  const s = Math.max(1, Math.round((Date.now() - t) / 1000));
  return s < 60 ? `${s}s ago` : s < 3600 ? `${Math.round(s / 60)} min ago` : `${Math.round(s / 3600)} h ago`;
};

export default function Overview() {
  const { state } = useHealth();
  const runs = useRuns();
  const [m, setM] = useState<ModelsInfo | null>(null);
  useEffect(() => {
    const t = setTimeout(() => api.models().then(setM).catch(() => setM(null)), 0);
    return () => clearTimeout(t);
  }, []);

  const honest = m ? (m.clinical["multiclass/structural/rf"] as { balanced_accuracy?: { mean: number } } | undefined)?.balanced_accuracy?.mean : undefined;
  const leaky = m ? (m.clinical["multiclass/with_hvf_md/hgb"] as { balanced_accuracy?: { mean: number } } | undefined)?.balanced_accuracy?.mean : undefined;
  const octBest = m && m.oct.length ? Math.max(...m.oct.map((o) => o.bal)) : undefined;
  const answered = m?.defer?.clinical?.accuracy_answered;
  const fusion = (m?.fusion as { fused_minus_clinical?: { balanced_accuracy: { mean: number } } } | undefined)?.fused_minus_clinical?.balanced_accuracy.mean;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Retinal screening workspace"
        description="Glaucoma and diabetes analysis from retinal images and clinical measurements, with the evidence behind each model one click away."
      />

      <section aria-label="Start a screening" className="grid gap-4 md:grid-cols-3">
        {FLOWS.map((f) => (
          <Link
            key={f.href}
            href={f.href}
            className="group flex flex-col justify-between rounded-lg border border-line bg-panel p-5 transition-colors hover:border-line-strong hover:bg-panel-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne"
          >
            <div>
              <Badge tone="accent">{f.tag}</Badge>
              <h2 className="mt-3 text-base font-semibold text-ink">{f.title}</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">{f.body}</p>
            </div>
            <p className="mt-5 text-sm font-medium text-accent-champagne">
              Open <span className="inline-block transition-transform group-hover:translate-x-0.5">→</span>
            </p>
          </Link>
        ))}
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <Panel
          title="Recent runs"
          subtitle="Stored in this browser only. Images are never saved."
          action={runs.length > 0 ? <Button variant="ghost" onClick={clearRuns} className="h-8 px-2.5 text-xs">Clear</Button> : undefined}
          pad={runs.length === 0}
        >
          {runs.length === 0 ? (
            <EmptyState title="Nothing run yet" body="Your screenings will be listed here with their result and time." />
          ) : (
            <ul>
              {runs.slice(0, 8).map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-4 border-b border-line px-5 py-3 last:border-0">
                  <div className="min-w-0">
                    <p className="truncate text-sm text-ink">{r.title}</p>
                    <p className="text-xs text-ink-faint">{r.inputs} · {ago(r.at)}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-sm text-ink">{r.result}</p>
                    {r.confidence !== undefined && <p className="text-xs tabular-nums text-ink-faint">{(r.confidence * 100).toFixed(0)}%</p>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Models" subtitle="Loaded by the analysis service">
          {state.phase === "loading" && <p className="text-sm text-ink-faint">Checking…</p>}
          {state.phase === "offline" && (
            <p className="text-sm text-bad">
              Service offline. Start it with <code className="rounded bg-white/5 px-1.5 py-0.5 text-xs">run.ps1</code> and reload.
            </p>
          )}
          {state.phase === "ready" && (
            <ul className="space-y-3">
              {serviceSummary(state.health).items.map((i) => (
                <li key={i.key} className="flex items-center justify-between text-sm">
                  <span className="text-ink-muted">{i.label}</span>
                  <Badge tone={i.ok ? "ok" : "bad"}>{i.ok ? "Ready" : "Unavailable"}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <Panel
        title="Evidence at a glance"
        subtitle="Patient-grouped 5-fold cross-validation, 4-class glaucoma staging"
        action={<Link href="/workspace/models" className="text-xs text-accent-champagne hover:underline">All results →</Link>}
      >
        {!m ? (
          <p className="text-sm text-ink-faint">Results unavailable while the service is offline.</p>
        ) : (
          <div className="grid grid-cols-2 gap-6 lg:grid-cols-5">
            <Stat label="Clinical, honest features" value={honest !== undefined ? `${(honest * 100).toFixed(0)}%` : "—"} hint="balanced accuracy" />
            <Stat label="Same, with visual-field MD" value={leaky !== undefined ? `${(leaky * 100).toFixed(0)}%` : "—"} hint="circular, not a result" tone="bad" />
            <Stat label="Accuracy when it answers" value={answered !== undefined ? `${(answered * 100).toFixed(0)}%` : "—"} hint="answers ~80% of cases, defers the rest" tone="ok" />
            <Stat label="OCT scan alone" value={octBest !== undefined ? `${(octBest * 100).toFixed(0)}%` : "—"} hint="best architecture" />
            <Stat
              label="Gain from adding OCT"
              value={fusion !== undefined ? `${fusion > 0 ? "+" : ""}${(fusion * 100).toFixed(1)} pts` : "—"}
              hint="vs clinical alone"
            />
          </div>
        )}
      </Panel>
    </div>
  );
}
