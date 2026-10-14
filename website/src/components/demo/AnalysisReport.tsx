"use client";

import { useState } from "react";
import Image from "next/image";
import clsx from "clsx";

export type PredictResult = {
  success: boolean;
  request_id: string;
  modality: "fundus" | "oct" | "fusion";
  prediction: string;
  confidence: number;
  probabilities: Record<string, number>;
  inference_time_ms: number;
  model_version: string;
  oct_mode: "real_volume" | "repeated_single_slice" | "none" | "n/a";
  fundus_heatmap: string | null;
};

const OCT_MODE_CAPTION: Record<PredictResult["oct_mode"], string | null> = {
  real_volume: "8 real OCT slices used as an ordered volume",
  repeated_single_slice: "One OCT image repeated across the 8 slice positions (not a true volume)",
  none: null,
  "n/a": null,
};

/**
 * Margin heuristic for flagging results that need a human look. It is NOT a
 * calibrated uncertainty estimate - the classifier's probabilities are not
 * calibrated (see the model card) - so the copy says "heuristic" and never
 * "safe"/"reliable".
 */
const REVIEW_MARGIN = 0.2;
const REVIEW_CONFIDENCE = 0.5;

function triage(probabilities: Record<string, number>) {
  const sorted = Object.entries(probabilities).sort((a, b) => b[1] - a[1]);
  const margin = sorted[0][1] - (sorted[1]?.[1] ?? 0);
  const needsReview = margin < REVIEW_MARGIN || sorted[0][1] < REVIEW_CONFIDENCE;
  return { margin, needsReview, runnerUp: sorted[1]?.[0] ?? null };
}

type Props = {
  result: PredictResult;
  fundusPreview: string | null;
  analysedAt: Date;
  onReset: () => void;
};

export function AnalysisReport({ result, fundusPreview, analysedAt, onReset }: Props) {
  const [copied, setCopied] = useState(false);
  const { margin, needsReview, runnerUp } = triage(result.probabilities);
  const octCaption = OCT_MODE_CAPTION[result.oct_mode];

  async function copyJson() {
    // The heatmap is a large base64 blob; leave it out of the clipboard copy.
    const { fundus_heatmap, ...rest } = result;
    const payload = { ...rest, fundus_heatmap: fundus_heatmap ? "<omitted: base64 PNG>" : null, analysed_at: analysedAt.toISOString() };
    try {
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <article className="mt-6 border-t border-white/10 pt-6" aria-labelledby="report-title" aria-live="polite">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-ink-faint">Analysis report</p>
          <h2 id="report-title" className="mt-2 text-3xl font-semibold capitalize tracking-tight text-ink">
            {result.prediction}
          </h2>
          <p className="mt-1 text-sm text-accent-champagne">
            {(result.confidence * 100).toFixed(1)}% model probability
          </p>
        </div>
        <dl className="text-right text-[11px] leading-relaxed text-ink-faint">
          <div>
            <dt className="inline">Report </dt>
            <dd className="inline font-mono text-ink-muted">{result.request_id}</dd>
          </div>
          <div>{analysedAt.toLocaleString()}</div>
          <div>
            <dt className="inline">Model </dt>
            <dd className="inline font-mono text-ink-muted">{result.model_version}</dd>
          </div>
        </dl>
      </header>

      <div
        role="status"
        className={clsx(
          "mt-5 rounded-lg border px-4 py-3 text-sm",
          needsReview
            ? "border-amber-300/25 bg-amber-300/10 text-amber-100"
            : "border-white/10 bg-white/[0.03] text-ink-muted"
        )}
      >
        <p className="font-medium">
          {needsReview ? "Low-margin result — would warrant human review" : "Clear margin between top two classes"}
        </p>
        <p className="mt-1 text-xs opacity-80">
          Top class leads {runnerUp ? <span className="capitalize">{runnerUp}</span> : "the next class"} by{" "}
          {(margin * 100).toFixed(0)} points. Heuristic only (flags margin &lt; {REVIEW_MARGIN * 100} points or
          top probability &lt; {REVIEW_CONFIDENCE * 100}%); the model&apos;s probabilities are not calibrated.
        </p>
      </div>

      <section className="mt-6" aria-label="Class probabilities">
        <h3 className="mb-3 text-xs uppercase tracking-[0.2em] text-ink-faint">Class probabilities</h3>
        <ul className="space-y-3">
          {Object.entries(result.probabilities).map(([label, p]) => {
            const top = label === result.prediction;
            return (
              <li key={label} className="grid grid-cols-[6.5rem_1fr_3rem] items-center gap-3 text-sm">
                <span className={clsx("capitalize", top ? "font-medium text-ink" : "text-ink-muted")}>{label}</span>
                <div
                  className="h-2 overflow-hidden rounded-full bg-white/10"
                  role="meter"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={Math.round(p * 100)}
                  aria-label={`${label} probability`}
                >
                  <div
                    className={clsx(
                      "h-full rounded-full transition-[width] duration-700 ease-out",
                      top ? "bg-accent-champagne" : "bg-ink-muted/50"
                    )}
                    style={{ width: `${p * 100}%` }}
                  />
                </div>
                <span className="text-right tabular-nums text-ink-muted">{(p * 100).toFixed(0)}%</span>
              </li>
            );
          })}
        </ul>
      </section>

      {result.fundus_heatmap && (
        <section className="mt-8" aria-label="Fundus explanation">
          <h3 className="mb-3 text-xs uppercase tracking-[0.2em] text-ink-faint">Fundus explanation (Grad-CAM)</h3>
          <div className="grid grid-cols-2 gap-3">
            {fundusPreview && (
              <figure>
                <div className="relative aspect-square overflow-hidden rounded-xl border border-white/10">
                  <Image src={fundusPreview} alt="Input fundus image" fill className="object-cover" unoptimized />
                </div>
                <figcaption className="mt-1.5 text-center text-[11px] text-ink-faint">Input</figcaption>
              </figure>
            )}
            <figure className={fundusPreview ? "" : "col-span-2 mx-auto w-1/2"}>
              <div className="relative aspect-square overflow-hidden rounded-xl border border-white/10">
                <Image src={result.fundus_heatmap} alt="Grad-CAM heatmap over the fundus image" fill className="object-cover" unoptimized />
              </div>
              <figcaption className="mt-1.5 text-center text-[11px] text-ink-faint">Regions driving the prediction</figcaption>
            </figure>
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">
            Model attribution for the fundus branch only — it shows where the network looked, not proof of causal
            or clinical reasoning.
          </p>
        </section>
      )}

      <section className="mt-8 border-t border-white/10 pt-5" aria-label="Run details">
        <h3 className="mb-2 text-xs uppercase tracking-[0.2em] text-ink-faint">Run details</h3>
        <ul className="space-y-1 text-xs text-ink-muted">
          <li>
            Modality: <span className="capitalize text-ink">{result.modality}</span>
          </li>
          {octCaption && <li>OCT input: {octCaption}</li>}
          <li>Inference time: {result.inference_time_ms.toFixed(1)} ms</li>
        </ul>
        <p className="mt-4 text-[11px] leading-relaxed text-ink-faint">
          Research prototype. Not a medical device and not a diagnosis; do not use it to make decisions about
          patient care.
        </p>
      </section>

      <div className="no-print mt-5 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => window.print()}
          className="rounded-full border border-white/15 px-4 py-1.5 text-xs text-ink transition-colors hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne"
        >
          Print / save as PDF
        </button>
        <button
          type="button"
          onClick={copyJson}
          className="rounded-full border border-white/15 px-4 py-1.5 text-xs text-ink transition-colors hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne"
        >
          {copied ? "Copied" : "Copy result JSON"}
        </button>
        <button
          type="button"
          onClick={onReset}
          className="rounded-full px-4 py-1.5 text-xs text-ink-muted transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne"
        >
          New analysis
        </button>
      </div>
    </article>
  );
}
