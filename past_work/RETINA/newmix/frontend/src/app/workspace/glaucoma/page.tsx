"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, urlToFile, type AssessResult, type ClinicalField } from "@/lib/api";
import { addRun } from "@/lib/history";
import samples from "@/lib/samples.json";
import {
  Badge, Button, Callout, EmptyState, ErrorNote, LoadingBlock, Meter, NumberField, PageHeader, Panel, ProbBars,
  UploadZone, severityTone,
} from "@/components/ui/primitives";

type Sample = (typeof samples)[number];

const GROUPS: { title: string; keys: string[] }[] = [
  { title: "Patient & pressure", keys: ["Age", "Gender", "IOP", "CDR"] },
  { title: "RNFL thickness (µm)", keys: ["RNFL_Avg", "RNFL_S", "RNFL_I", "RNFL_N", "RNFL_T"] },
  { title: "Ganglion cell complex (µm)", keys: ["GCC_Avg", "GCC_SUPERIOR", "GCC_INFERIOR", "GCC_ST", "GCC_SN", "GCC_IT", "GCC_IN"] },
];

export default function GlaucomaPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [fields, setFields] = useState<ClinicalField[] | null>(null);
  const [fieldsError, setFieldsError] = useState<string | null>(null);
  const [vals, setVals] = useState<Record<string, string>>({});
  const [md, setMd] = useState("");
  const [sample, setSample] = useState<Sample | null>(null);
  const [phase, setPhase] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [result, setResult] = useState<AssessResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  const loadSpec = useCallback(() => {
    setFieldsError(null);
    api.clinicalSpec().then((r) => setFields(r.fields)).catch((e: Error) => setFieldsError(e.message));
  }, []);
  useEffect(() => {
    const t = setTimeout(loadSpec, 0);
    return () => clearTimeout(t);
  }, [loadSpec]);

  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    const t = setTimeout(() => setPreview(url), 0);
    return () => {
      clearTimeout(t);
      URL.revokeObjectURL(url);
    };
  }, [file]);

  const spec = useMemo(() => Object.fromEntries((fields ?? []).map((f) => [f.key, f])), [fields]);
  const filled = Object.values(vals).filter((v) => v !== "").length;
  const canRun = (file !== null || filled >= 4) && phase !== "loading";

  function onFile(f: File | null) {
    setFile(f);
    if (!f) setPreview(null);
    setSample(null);
  }

  async function loadSample(s: Sample) {
    setError(null);
    try {
      setFile(s.image ? await urlToFile(s.image, `${s.id}-oct.jpg`) : null);
      if (!s.image) setPreview(null);
      setVals(Object.fromEntries(Object.entries(s.values).map(([k, v]) => [k, v === null ? "" : String(v)])));
      setMd(String(s.hvf_md));
      setSample(s);
      setResult(null);
      setPhase("idle");
    } catch {
      setError("Could not load the sample image.");
    }
  }

  function reset() {
    setFile(null);
    setPreview(null);
    setVals({});
    setMd("");
    setSample(null);
    setResult(null);
    setPhase("idle");
    setError(null);
  }

  async function run() {
    setPhase("loading");
    setError(null);
    const clinical: Record<string, number | null> = {};
    for (const [k, v] of Object.entries(vals)) if (v !== "") clinical[k] = Number(v);
    if (md !== "") clinical.HVF_MD = Number(md);
    try {
      const r = await api.assess(file, clinical, true);
      setResult(r);
      setPhase("done");
      const top = r.fused ?? r.oct ?? r.clinical?.multiclass;
      const dfr = (r.fused ?? r.oct ?? r.clinical)?.defer;
      addRun({
        module: "glaucoma",
        title: "Glaucoma screening",
        result: dfr?.deferred ? "Inconclusive" : top ? `${top.prediction}` : "—",
        confidence: top?.confidence,
        inputs: [file ? "OCT" : null, filled >= 4 ? "clinical" : null].filter(Boolean).join(" + "),
      });
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed.");
      setPhase("error");
    }
  }

  const setVal = (k: string) => (v: string) => setVals((p) => ({ ...p, [k]: v }));

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Screening"
        title="Glaucoma assessment"
        description="Combine an optic-nerve-head OCT B-scan with clinical measurements. Either input works alone; with both, the two model outputs are fused."
        actions={
          <Button variant="ghost" onClick={reset} disabled={phase === "loading" || (!file && !filled && !result)}>
            Clear
          </Button>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        {/* ---------- inputs ---------- */}
        <div className="space-y-6">
          <Panel title="Start from a sample" subtitle="Real eyes from the development cohort, so they were seen during training.">
            <div className="flex flex-wrap gap-2">
              {samples.map((s) => (
                <button
                  key={s.id}
                  onClick={() => loadSample(s)}
                  disabled={phase === "loading"}
                  className={`rounded-md border px-3 py-1.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne disabled:opacity-50 ${
                    sample?.id === s.id ? "border-accent-champagne bg-accent-champagne/10 text-accent-champagne" : "border-line-strong text-ink-muted hover:bg-white/5 hover:text-ink"
                  }`}
                >
                  {s.label}
                  {s.image && <span className="ml-1.5 text-xs text-ink-faint">{s.eye}</span>}
                </button>
              ))}
            </div>
            {sample && (
              <p className="mt-3 text-xs text-ink-faint">
                {sample.image ? (
                  <>Loaded <span className="text-ink-muted">{sample.label}</span> sample. This eye was part of the training data, so the output is not an out-of-sample test.</>
                ) : (
                  <>Synthetic clinical values blended between a Mild and a Moderate eye, with no scan. Not a real patient; it exists to show how the app behaves when the model is unsure.</>
                )}
              </p>
            )}
          </Panel>

          <Panel title="1 · OCT B-scan" subtitle="Optic-nerve-head scan, JPEG or PNG. Grayscale expected.">
            <UploadZone label="OCT scan" hint="B-scan through the optic disc" file={file} previewUrl={preview} onFile={onFile} disabled={phase === "loading"} />
          </Panel>

          <Panel
            title="2 · Clinical measurements"
            subtitle={`${filled} of ${fields?.length ?? 16} entered · at least 4 needed when no scan is given`}
          >
            {fieldsError ? (
              <ErrorNote message={fieldsError} onRetry={loadSpec} />
            ) : !fields ? (
              <LoadingBlock label="Loading form…" lines={3} />
            ) : (
              <div className="space-y-5">
                {GROUPS.map((g) => (
                  <fieldset key={g.title}>
                    <legend className="mb-2 text-xs font-medium uppercase tracking-wider text-ink-faint">{g.title}</legend>
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                      {g.keys.map((k) =>
                        k === "Gender" ? (
                          <div key={k}>
                            <label htmlFor="sex" className="mb-1 block text-xs text-ink-muted">Sex</label>
                            <select
                              id="sex"
                              value={vals.Gender ?? ""}
                              onChange={(e) => setVal("Gender")(e.target.value)}
                              className="h-9 w-full rounded-md border border-line-strong bg-panel-2 px-2 text-sm text-ink focus:border-accent-champagne focus:outline-none focus:ring-1 focus:ring-accent-champagne"
                            >
                              <option value="">—</option>
                              <option value="1">Male</option>
                              <option value="0">Female</option>
                            </select>
                          </div>
                        ) : (
                          <NumberField
                            key={k}
                            label={spec[k]?.label ?? k}
                            value={vals[k] ?? ""}
                            onChange={setVal(k)}
                            hint={spec[k] ? `${Math.round(spec[k].min * 100) / 100}–${Math.round(spec[k].max * 100) / 100}` : undefined}
                          />
                        ),
                      )}
                    </div>
                  </fieldset>
                ))}
                <fieldset className="border-t border-line pt-4">
                  <legend className="mb-2 text-xs font-medium uppercase tracking-wider text-ink-faint">Visual field (optional)</legend>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                    <NumberField label="HVF mean deviation (dB)" value={md} onChange={setMd} hint="e.g. -7.4" />
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-ink-faint">
                    Used only for the staging rule, never as a model input. In this cohort, severity is defined by this value, so feeding it to the model would be circular.
                  </p>
                </fieldset>
              </div>
            )}
          </Panel>

          <div className="flex items-center gap-3">
            <Button onClick={run} loading={phase === "loading"} disabled={!canRun} className="h-10 px-5">
              {phase === "loading" ? "Analysing…" : "Run assessment"}
            </Button>
            {!canRun && phase !== "loading" && <span className="text-xs text-ink-faint">Add an OCT scan or at least 4 measurements.</span>}
          </div>
          {error && <ErrorNote message={error} onRetry={canRun ? run : undefined} />}
        </div>

        {/* ---------- results ---------- */}
        <div ref={resultRef} className="min-w-0 scroll-mt-20 space-y-6">
          {phase === "idle" && !result && (
            <EmptyState
              title="No assessment yet"
              body="Load a sample or add your own inputs, then run the assessment. Results, the attention map and the main drivers appear here."
              icon={<svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /></svg>}
            />
          )}
          {phase === "loading" && (
            <Panel title="Analysing">
              <LoadingBlock label="Running OCT model, clinical model and explanation…" />
            </Panel>
          )}
          {phase === "done" && result && <Results r={result} />}
        </div>
      </div>
    </div>
  );
}

/* ================================ results ================================ */

function Results({ r }: { r: AssessResult }) {
  const head = r.fused ?? (r.oct ? { ...r.oct } : r.clinical ? { ...r.clinical.multiclass, p_glaucoma: r.clinical.p_glaucoma } : null);
  if (!head) return null;
  const defer = (r.fused ?? r.oct ?? r.clinical)?.defer ?? null;
  const deferred = !!defer?.deferred;
  const top2 = Object.entries(head.probabilities).sort((a, b) => b[1] - a[1]).slice(0, 2);
  const warnings: string[] = [];
  if (defer && !defer.reliable_head)
    warnings.push(`The OCT scan alone is not a dependable stager: even when it answers, it was right ${(defer.accuracy_if_answered * 100).toFixed(0)}% of the time in cross-validation. Use it as supporting evidence only.`);
  if (r.fused && !r.fused.agreement) warnings.push("The OCT model and the clinical model disagree on the stage. The fused result averages two conflicting signals.");
  if (r.oct && !r.clinical) warnings.push("Image-only result. Adding RNFL/GCC measurements gives a far more reliable stage; see the Models page.");
  const source = r.fused ? "Fused · OCT + clinical" : r.oct ? "OCT only" : "Clinical only";
  const pg = head.p_glaucoma;

  return (
    <>
      <Panel title="Assessment" action={<Badge tone="info">{source}</Badge>}>
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <p className="text-xs text-ink-faint">{deferred ? "Stage" : "Most likely class"}</p>
            {deferred ? (
              <>
                <p className="mt-1 flex items-center gap-3 text-3xl font-semibold tracking-tight">
                  Inconclusive
                  <Badge tone="warn">below confidence cut-off</Badge>
                </p>
                <p className="mt-1.5 text-sm text-ink-muted">
                  Leading candidates: {top2.map(([k, v]) => `${k} (${(v * 100).toFixed(0)}%)`).join(" or ")}
                </p>
              </>
            ) : (
              <p className="mt-1 flex items-center gap-3 text-3xl font-semibold tracking-tight">
                {head.prediction}
                <Badge tone={severityTone(head.prediction)}>{(head.confidence * 100).toFixed(0)}% confidence</Badge>
              </p>
            )}
          </div>
          <div className="w-full max-w-xs min-w-[220px] flex-1">
            <Meter value={pg} label="Model score for glaucoma" tone={pg > 0.66 ? "bad" : pg > 0.4 ? "warn" : "ok"} />
            <p className="mt-1.5 text-xs text-ink-faint">A model score, not a calibrated clinical probability.</p>
          </div>
        </div>
        {defer && (
          <div className="mt-5">
            <Callout tone={deferred ? "warn" : "info"} title={deferred ? "Recommended next step: visual-field test" : "Confidence check"}>
              {defer.action}
            </Callout>
          </div>
        )}
        {warnings.length > 0 && (
          <ul className="mt-5 space-y-2">
            {warnings.map((w) => (
              <li key={w}><Callout tone="warn">{w}</Callout></li>
            ))}
          </ul>
        )}
        <div className="mt-6 border-t border-line pt-5">
          {deferred && <p className="mb-3 text-xs text-ink-faint">Model probabilities, shown for transparency. No stage is assigned.</p>}
          <ProbBars probs={head.probabilities} highlight={deferred ? undefined : head.prediction} />
        </div>
      </Panel>

      {r.oct?.heatmap && <AttentionMap oct={r.oct} />}

      {r.clinical && (
        <Panel title="What drove the clinical result" subtitle="Change in predicted-class probability when a value is replaced by the cohort median.">
          <ul className="space-y-3">
            {r.clinical.drivers.map((d) => {
              const w = Math.min(Math.abs(d.effect) / 0.35, 1) * 50;
              return (
                <li key={d.feature} className="grid grid-cols-[140px_1fr_52px] items-center gap-3 text-sm">
                  <span className="truncate text-ink-muted" title={d.label}>{d.label}</span>
                  <div className="relative h-2 rounded-full bg-white/[0.06]" aria-hidden>
                    <div className="absolute inset-y-0 left-1/2 w-px bg-line-strong" />
                    <div
                      className={`absolute inset-y-0 rounded-full ${d.effect >= 0 ? "bg-accent-champagne" : "bg-info"}`}
                      style={d.effect >= 0 ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }}
                    />
                  </div>
                  <span className="text-right tabular-nums text-ink-faint">{d.effect > 0 ? "+" : ""}{(d.effect * 100).toFixed(0)}</span>
                </li>
              );
            })}
          </ul>
          <p className="mt-4 text-xs text-ink-faint">Right (gold) pushes toward the predicted class; left (blue) pushes away. Values in percentage points.</p>
        </Panel>
      )}

      {r.md_rule && (
        <Panel title="Visual-field staging rule" subtitle="Deterministic rule, not a model">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-ink-muted">
              MD {r.md_rule.md_db.toFixed(2)} dB → <Badge tone={severityTone(r.md_rule.stage)}>{r.md_rule.stage}</Badge>
            </p>
            <p className="text-xs text-ink-faint">{r.md_rule.rule}</p>
          </div>
          {r.md_rule.note && <p className="mt-3 text-xs text-ink-faint">{r.md_rule.note}</p>}
        </Panel>
      )}

      {r.oct && r.clinical && (
        <Panel title="Per-source results" pad={false}>
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-ink-faint">
              <tr className="border-b border-line">
                <th className="px-5 py-2.5 font-medium">Source</th>
                <th className="px-5 py-2.5 font-medium">Stage</th>
                <th className="px-5 py-2.5 text-right font-medium">Confidence</th>
                <th className="px-5 py-2.5 text-right font-medium">Glaucoma score</th>
              </tr>
            </thead>
            <tbody>
              {[
                { n: "OCT scan", p: r.oct.prediction, c: r.oct.confidence, g: r.oct.p_glaucoma },
                { n: "Clinical", p: r.clinical.multiclass.prediction, c: r.clinical.multiclass.confidence, g: r.clinical.p_glaucoma },
                ...(r.fused ? [{ n: "Fused", p: r.fused.prediction, c: r.fused.confidence, g: r.fused.p_glaucoma }] : []),
              ].map((row) => (
                <tr key={row.n} className="border-b border-line last:border-0">
                  <td className="px-5 py-3 text-ink-muted">{row.n}</td>
                  <td className="px-5 py-3"><Badge tone={severityTone(row.p)}>{row.p}</Badge></td>
                  <td className="px-5 py-3 text-right tabular-nums">{(row.c * 100).toFixed(0)}%</td>
                  <td className="px-5 py-3 text-right tabular-nums">{(row.g * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}

      <p className="text-xs leading-relaxed text-ink-faint">{r.disclaimer}</p>
    </>
  );
}

function AttentionMap({ oct }: { oct: NonNullable<AssessResult["oct"]> }) {
  const [view, setView] = useState<"map" | "scan">("map");
  const src = view === "map" ? oct.heatmap : oct.input_preview;
  return (
    <Panel
      title="Where the OCT model looked"
      subtitle="Grad-CAM for the predicted class, averaged over the ensemble"
      action={
        <div className="inline-flex rounded-md border border-line-strong p-0.5 text-xs" role="group" aria-label="Image view">
          {(["map", "scan"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              aria-pressed={view === v}
              className={`rounded px-2.5 py-1 transition-colors ${view === v ? "bg-white/10 text-ink" : "text-ink-faint hover:text-ink"}`}
            >
              {v === "map" ? "Attention" : "Scan"}
            </button>
          ))}
        </div>
      }
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      {src && <img src={src} alt={view === "map" ? "OCT scan with attention overlay" : "Input OCT scan"} className="w-full rounded-md bg-black" />}
      <p className="mt-3 text-xs leading-relaxed text-ink-faint">
        Attention maps show where the network&apos;s decision was most sensitive, not a verified anatomical finding. Check that it sits on the optic-nerve-head region before trusting the result.
      </p>
    </Panel>
  );
}
