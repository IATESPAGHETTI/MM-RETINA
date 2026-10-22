"use client";

import { useEffect, useRef, useState } from "react";
import { api, urlToFile, type DiabetesResult } from "@/lib/api";
import { addRun } from "@/lib/history";
import { Badge, Button, Callout, EmptyState, ErrorNote, LoadingBlock, Meter, PageHeader, Panel, ProbBars, Stat, UploadZone } from "@/components/ui/primitives";

const SAMPLES = [
  { id: "d1", label: "Sample fundus A", url: "/samples/diabetes-1.jpg" },
  { id: "d2", label: "Sample fundus B", url: "/samples/diabetes-2.jpg" },
];

export default function DiabetesPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [res, setRes] = useState<DiabetesResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const out = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    const t = setTimeout(() => setPreview(url), 0);
    return () => {
      clearTimeout(t);
      URL.revokeObjectURL(url);
    };
  }, [file]);

  function pick(f: File | null) {
    setFile(f);
    if (!f) setPreview(null);
    setRes(null);
    setPhase("idle");
    setError(null);
  }

  async function run() {
    if (!file) return;
    setPhase("loading");
    setError(null);
    try {
      const r = await api.diabetesAnalyze(file);
      setRes(r);
      setPhase("done");
      addRun({
        module: "diabetes",
        title: "Diabetes retina analysis",
        result: r.modules.hba1c?.binary.label ?? "Vessel analysis",
        confidence: r.modules.hba1c?.binary.confidence,
        inputs: "Fundus",
      });
      setTimeout(() => out.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed.");
      setPhase("error");
    }
  }

  const m = res?.modules;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Screening"
        title="Diabetes retina analysis"
        description="Segment retinal vessels, measure their branching complexity, and estimate an HbA1c range from a colour fundus photograph."
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <div className="space-y-6">
          <Panel title="Fundus photograph" subtitle="Colour image, JPEG or PNG. Macula- or disc-centred.">
            <UploadZone label="Fundus image" hint="Colour retinal photograph" file={file} previewUrl={preview} onFile={pick} disabled={phase === "loading"} />
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="text-xs text-ink-faint">Or try:</span>
              {SAMPLES.map((s) => (
                <button
                  key={s.id}
                  disabled={phase === "loading"}
                  onClick={async () => pick(await urlToFile(s.url, `${s.id}.jpg`))}
                  className="rounded-md border border-line-strong px-3 py-1.5 text-sm text-ink-muted transition-colors hover:bg-white/5 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne disabled:opacity-50"
                >
                  {s.label}
                </button>
              ))}
            </div>
          </Panel>
          <div className="flex items-center gap-3">
            <Button onClick={run} loading={phase === "loading"} disabled={!file} className="h-10 px-5">
              {phase === "loading" ? "Analysing…" : "Analyse retina"}
            </Button>
            {!file && <span className="text-xs text-ink-faint">Add a fundus photograph first.</span>}
          </div>
          {error && <ErrorNote message={error} onRetry={run} />}
          <Callout tone="warn" title="Read before relying on this">
            The HbA1c and vessel models came from a separate project and shipped without validation metrics. Results here are descriptive research output, not a diagnostic test.
          </Callout>
        </div>

        <div ref={out} className="min-w-0 scroll-mt-20 space-y-6">
          {phase === "idle" && (
            <EmptyState
              title="No analysis yet"
              body="Upload a fundus photograph and run the analysis. Vessel overlay, fractal dimension and the HbA1c estimate appear here."
              icon={<svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden><path d="M12 3s6 6.2 6 10.5A6 6 0 0 1 6 13.5C6 9.2 12 3 12 3Z" /></svg>}
            />
          )}
          {phase === "loading" && (
            <Panel title="Analysing">
              <LoadingBlock label="Segmenting vessels, measuring fractal dimension, estimating HbA1c…" />
            </Panel>
          )}
          {phase === "done" && res && (
            <>
              {m?.vessels && (
                <Panel title="Vessel segmentation" subtitle="U-Net trained on DRIVE">
                  <div className="grid gap-5 sm:grid-cols-[1fr_auto]">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={m.vessels.overlay} alt="Fundus photograph with segmented vessels highlighted" className="w-full rounded-md bg-black" />
                    <div className="space-y-5 sm:w-40">
                      <Stat label="Vessel density" value={`${m.vessels.vessel_density_pct.toFixed(1)}%`} hint="of the retinal disc" />
                      <Stat label="Inference" value={`${Math.round(m.vessels.inference_ms)} ms`} />
                    </div>
                  </div>
                </Panel>
              )}

              {m?.fractal && (
                <Panel title="Vessel complexity" subtitle="Box-counting fractal dimension of the vessel boundary">
                  <div className="grid gap-5 sm:grid-cols-[1fr_auto]">
                    <FractalPlot x={m.fractal.log_sizes} y={m.fractal.log_counts} />
                    <div className="space-y-5 sm:w-40">
                      <Stat label="Fractal dimension" value={m.fractal.fractal_dimension.toFixed(3)} />
                      <Stat label="Fit R²" value={m.fractal.r_squared.toFixed(3)} />
                    </div>
                  </div>
                  <p className="mt-3 text-xs leading-relaxed text-ink-faint">{m.fractal.note}</p>
                </Panel>
              )}

              {m?.hba1c && (
                <Panel title="HbA1c estimate" action={<Badge tone="warn">Experimental</Badge>}>
                  <div className="grid gap-6 sm:grid-cols-2">
                    <div className="space-y-4">
                      <div>
                        <p className="text-xs text-ink-faint">Screening class</p>
                        <p className="mt-1 text-lg font-semibold">{m.hba1c.binary.label}</p>
                      </div>
                      <Meter value={m.hba1c.binary.probability_elevated} label="Score for HbA1c ≥ 6.5" tone={m.hba1c.binary.probability_elevated > 0.5 ? "warn" : "ok"} />
                      <div>
                        <p className="text-xs text-ink-faint">Most likely range</p>
                        <p className="mt-1 text-lg font-semibold tabular-nums">{m.hba1c.multi.range} <span className="text-sm font-normal text-ink-faint">· {(m.hba1c.multi.confidence * 100).toFixed(0)}%</span></p>
                      </div>
                    </div>
                    <ProbBars probs={m.hba1c.multi.probabilities} highlight={m.hba1c.multi.range} />
                  </div>
                  <div className="mt-5 space-y-3">
                    {m.hba1c.consistency_note && <Callout tone="warn" title="The two models disagree">{m.hba1c.consistency_note}</Callout>}
                    <Callout tone="warn">{m.hba1c.validation}</Callout>
                  </div>
                </Panel>
              )}

              {Object.entries(res.skipped).map(([k, why]) => (
                <p key={k} className="text-xs text-ink-faint">
                  <span className="font-medium text-ink-muted">{k.replace("_", " ")}</span> not run: {why}.
                </p>
              ))}
              <p className="text-xs leading-relaxed text-ink-faint">{res.disclaimer}</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function FractalPlot({ x, y }: { x: number[]; y: number[] }) {
  const W = 360, H = 220, P = { l: 40, r: 12, t: 12, b: 32 };
  const minX = Math.min(...x), maxX = Math.max(...x), minY = Math.min(...y), maxY = Math.max(...y);
  const sx = (v: number) => P.l + ((v - minX) / (maxX - minX || 1)) * (W - P.l - P.r);
  const sy = (v: number) => H - P.b - ((v - minY) / (maxY - minY || 1)) * (H - P.t - P.b);
  const n = x.length, mx = x.reduce((a, b) => a + b, 0) / n, my = y.reduce((a, b) => a + b, 0) / n;
  const slope = x.reduce((a, v, i) => a + (v - mx) * (y[i] - my), 0) / (x.reduce((a, v) => a + (v - mx) ** 2, 0) || 1);
  const b0 = my - slope * mx;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Log-log plot of box count versus box size with a fitted line">
      <line x1={P.l} y1={H - P.b} x2={W - P.r} y2={H - P.b} stroke="currentColor" className="text-line-strong" />
      <line x1={P.l} y1={P.t} x2={P.l} y2={H - P.b} stroke="currentColor" className="text-line-strong" />
      <line x1={sx(minX)} y1={sy(slope * minX + b0)} x2={sx(maxX)} y2={sy(slope * maxX + b0)} stroke="var(--accent-champagne)" strokeWidth="1.5" strokeDasharray="4 3" />
      {x.map((v, i) => <circle key={i} cx={sx(v)} cy={sy(y[i])} r="3.2" fill="var(--accent-champagne)" />)}
      <text x={W / 2} y={H - 6} textAnchor="middle" className="fill-ink-faint" fontSize="10">log(1 / box size)</text>
      <text x="10" y={H / 2} textAnchor="middle" transform={`rotate(-90 10 ${H / 2})`} className="fill-ink-faint" fontSize="10">log(box count)</text>
    </svg>
  );
}
