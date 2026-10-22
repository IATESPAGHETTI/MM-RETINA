"use client";

import { useEffect, useRef, useState } from "react";
import { api, urlToFile, type MultimodalResult } from "@/lib/api";
import { addRun } from "@/lib/history";
import { Badge, Button, Callout, EmptyState, ErrorNote, LoadingBlock, PageHeader, Panel, ProbBars, UploadZone, severityTone } from "@/components/ui/primitives";

type Modality = "fusion" | "fundus" | "oct";
const SLICES = [0, 36, 73, 109, 146, 182, 219, 255];
const SAMPLE_FUNDUS = "/demo/fundus/gamma-0001.jpg";
const sliceUrl = (i: number) => `/oct-volume/0001/${String(i).padStart(3, "0")}.jpg`;

const MODES: { id: Modality; label: string; hint: string }[] = [
  { id: "fusion", label: "Fundus + OCT", hint: "Both modalities, cross-attention fusion" },
  { id: "fundus", label: "Fundus only", hint: "Colour photograph" },
  { id: "oct", label: "OCT only", hint: "Macular OCT volume" },
];

export default function MultimodalPage() {
  const [mode, setMode] = useState<Modality>("fusion");
  const [fundus, setFundus] = useState<File | null>(null);
  const [fundusUrl, setFundusUrl] = useState<string | null>(null);
  const [volume, setVolume] = useState<File[] | null>(null);
  const [single, setSingle] = useState<File | null>(null);
  const [singleUrl, setSingleUrl] = useState<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [res, setRes] = useState<MultimodalResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const out = useRef<HTMLDivElement>(null);

  const needF = mode !== "oct";
  const needO = mode !== "fundus";

  useEffect(() => {
    if (!fundus) return;
    const u = URL.createObjectURL(fundus);
    const t = setTimeout(() => setFundusUrl(u), 0);
    return () => { clearTimeout(t); URL.revokeObjectURL(u); };
  }, [fundus]);
  useEffect(() => {
    if (!single) return;
    const u = URL.createObjectURL(single);
    const t = setTimeout(() => setSingleUrl(u), 0);
    return () => { clearTimeout(t); URL.revokeObjectURL(u); };
  }, [single]);

  async function loadSample() {
    setError(null);
    try {
      setFundus(await urlToFile(SAMPLE_FUNDUS, "gamma-0001-fundus.jpg"));
      setVolume(await Promise.all(SLICES.map((i) => urlToFile(sliceUrl(i), `slice-${i}.jpg`))));
      setSingle(null);
      setSingleUrl(null);
      setRes(null);
      setPhase("idle");
    } catch {
      setError("Could not load the sample files.");
    }
  }

  const octReady = (volume?.length ?? 0) === 8 || !!single;
  const canRun = phase !== "loading" && (!needF || !!fundus) && (!needO || octReady);

  async function run() {
    setPhase("loading");
    setError(null);
    const fd = new FormData();
    fd.append("modality", mode);
    if (needF && fundus) { fd.append("fundus", fundus); fd.append("explain", "true"); }
    if (needO) {
      if (volume?.length === 8) volume.forEach((f) => fd.append("oct_slices", f));
      else if (single) fd.append("oct", single);
    }
    try {
      const r = await api.multimodal(fd);
      setRes(r);
      setPhase("done");
      addRun({ module: "multimodal", title: "Multimodal grading (GAMMA)", result: r.prediction, confidence: r.confidence, inputs: mode === "fusion" ? "Fundus + OCT" : mode });
      setTimeout(() => out.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed.");
      setPhase("error");
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Screening"
        title="Multimodal grading (GAMMA)"
        description="Fundus photograph and a macular OCT volume fused by a cross-modal transformer, graded Normal, Early or Progressive. Trained on the public GAMMA dataset."
        actions={<Button variant="secondary" onClick={loadSample} disabled={phase === "loading"}>Load sample eye</Button>}
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <div className="space-y-6">
          <Panel title="Inputs">
            <div role="radiogroup" aria-label="Modality" className="mb-5 grid grid-cols-3 gap-2">
              {MODES.map((m) => (
                <button
                  key={m.id}
                  role="radio"
                  aria-checked={mode === m.id}
                  onClick={() => setMode(m.id)}
                  disabled={phase === "loading"}
                  className={`rounded-md border px-3 py-2 text-left text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne ${
                    mode === m.id ? "border-accent-champagne bg-accent-champagne/10 text-ink" : "border-line-strong text-ink-muted hover:bg-white/5"
                  }`}
                >
                  <span className="block font-medium">{m.label}</span>
                  <span className="mt-0.5 hidden text-xs text-ink-faint sm:block">{m.hint}</span>
                </button>
              ))}
            </div>
            <div className="space-y-5">
              {needF && <UploadZone label="Fundus photograph" hint="Colour retinal photograph" file={fundus} previewUrl={fundusUrl} onFile={(f) => { setFundus(f); if (!f) setFundusUrl(null); }} disabled={phase === "loading"} />}
              {needO && (
                volume?.length === 8 ? (
                  <div>
                    <p className="mb-1.5 text-xs font-medium text-ink-muted">OCT volume</p>
                    <div className="rounded-lg border border-line-strong bg-panel-2 p-3">
                      <div className="grid grid-cols-4 gap-1.5">
                        {SLICES.map((i) => (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img key={i} src={sliceUrl(i)} alt={`OCT B-scan ${i}`} className="aspect-[4/3] w-full rounded bg-black object-cover" />
                        ))}
                      </div>
                      <div className="mt-2 flex items-center justify-between text-xs">
                        <span className="text-ink-muted">8 real B-scans from sample eye 0001</span>
                        <button className="text-ink-faint underline underline-offset-2 hover:text-ink" onClick={() => setVolume(null)}>Remove</button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <UploadZone label="OCT B-scan (single image)" hint="Repeated across slices unless you load the sample volume" file={single} previewUrl={singleUrl} onFile={(f) => { setSingle(f); if (!f) setSingleUrl(null); }} disabled={phase === "loading"} />
                )
              )}
            </div>
          </Panel>
          <div className="flex items-center gap-3">
            <Button onClick={run} loading={phase === "loading"} disabled={!canRun} className="h-10 px-5">
              {phase === "loading" ? "Analysing…" : "Run grading"}
            </Button>
            {!canRun && phase !== "loading" && <span className="text-xs text-ink-faint">Add the required inputs, or load the sample eye.</span>}
          </div>
          {error && <ErrorNote message={error} onRetry={run} />}
        </div>

        <div ref={out} className="min-w-0 scroll-mt-20 space-y-6">
          {phase === "idle" && <EmptyState title="No grading yet" body="Load the sample eye or add your own images, choose a modality and run." />}
          {phase === "loading" && <Panel title="Analysing"><LoadingBlock label="Running the multimodal model…" /></Panel>}
          {phase === "done" && res && (
            <>
              <Panel title="Grade" action={<Badge tone="info">{MODES.find((m) => m.id === mode)?.label}</Badge>}>
                <p className="flex items-center gap-3 text-3xl font-semibold capitalize tracking-tight">
                  {res.prediction}
                  <Badge tone={severityTone(res.prediction)}>{(res.confidence * 100).toFixed(0)}% confidence</Badge>
                </p>
                <div className="mt-5 border-t border-line pt-5"><ProbBars probs={res.probabilities} highlight={res.prediction} /></div>
                <p className="mt-4 text-xs text-ink-faint">
                  {res.inference_time_ms.toFixed(0)} ms · {res.model_version}
                  {res.oct_mode === "real_volume" ? " · real 8-slice volume" : res.oct_mode === "repeated_single_slice" ? " · single slice repeated" : ""}
                </p>
              </Panel>
              {res.fundus_heatmap && (
                <Panel title="Fundus attention" subtitle="Grad-CAM for the predicted class">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={res.fundus_heatmap} alt="Fundus photograph with attention overlay" className="w-full max-w-md rounded-md bg-black" />
                  <p className="mt-3 text-xs text-ink-faint">An OCT attention map is not produced for this model; it is documented as future work.</p>
                </Panel>
              )}
              <Callout tone="info" title="About these numbers">
                This live model is a single-split demonstration checkpoint. Its accuracy is reported from separate 5-fold cross-validation on the Models page, not from this prediction.
              </Callout>
              <p className="text-xs leading-relaxed text-ink-faint">{res.disclaimer}</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
