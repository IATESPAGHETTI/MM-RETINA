"use client";

import { useState } from "react";
import { Badge, Button, Callout, Panel, ProbBars, severityTone } from "@/components/ui/primitives";
import { ResultActions, ResultDisclaimer } from "@/components/workspace/ResultActions";
import type { CompareResult, GammaModel, MultimodalResult } from "@/lib/api";

export const GAMMA_MODELS: { id: GammaModel; label: string }[] = [
  { id: "fundus", label: "Fundus only" },
  { id: "oct", label: "OCT only" },
  { id: "fusion", label: "Fundus + OCT" },
];

const OCT_MODE: Record<string, string> = {
  real_volume: "Eight distinct B-scan inputs",
  repeated_single_slice: "A single B-scan repeated across the model input",
};

export function GammaHeatmap({ heatmap, fundus }: { heatmap: string; fundus: string | null }) {
  const [active, setActive] = useState(true);
  return (
    <Panel title="Fundus Grad-CAM" subtitle="Shows model sensitivity in the input.">
      <Button type="button" variant="secondary" aria-pressed={active} disabled={!fundus} onClick={() => setActive(!active)}>
        {active ? "Show original fundus" : "Show Grad-CAM"}
      </Button>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="mt-3 h-52 w-full rounded-lg bg-black object-contain" src={active || !fundus ? heatmap : fundus}
        alt={active ? "Fundus with Grad-CAM overlay" : "Original fundus photograph"} />
    </Panel>
  );
}

function RiskGauge({ risk }: { risk: CompareResult["risk"] }) {
  const value = Math.min(1, Math.max(0, risk.score));
  const angle = Math.PI * (1 - value);
  const x = 100 + Math.cos(angle) * 81;
  const y = 96 - Math.sin(angle) * 81;
  const color = { low: "var(--ok)", elevated: "var(--warn)", high: "var(--bad)" }[risk.level];
  return (
    <Panel title="Fusion model score">
      <div className="flex flex-wrap items-center gap-4">
        <svg viewBox="0 0 200 123" className="w-full max-w-48" role="img"
          aria-label={`${risk.level} model score, ${value.toFixed(2)} on a scale from 0 to 1`}>
          <path d="M19 96a81 81 0 0 1 162 0" fill="none" stroke="currentColor" opacity=".15" strokeWidth="12" strokeLinecap="round" />
          <path d="M19 96a81 81 0 0 1 162 0" fill="none" stroke={color} pathLength="100"
            strokeDasharray={`${value * 100} 100`} strokeWidth="12" strokeLinecap="round" />
          <circle cx={x} cy={y} r="5" fill="white" />
          <text x="100" y="91" textAnchor="middle" fill="currentColor" fontSize="27" fontWeight="600">{value.toFixed(2)}</text>
          <text x="19" y="118" textAnchor="middle" fill="currentColor" fontSize="13">0</text>
          <text x="181" y="118" textAnchor="middle" fill="currentColor" fontSize="13">1</text>
        </svg>
        <div className="min-w-0 flex-1 space-y-2 text-sm text-ink-muted">
          <Badge tone={risk.level === "low" ? "ok" : risk.level === "elevated" ? "warn" : "bad"}>{risk.level} score band</Badge>
          <p>{risk.basis}</p><p>{risk.note}</p>
        </div>
      </div>
    </Panel>
  );
}

export function GammaComparison({ result, fundus, inputs }: { result: CompareResult; fundus: string | null; inputs: string }) {
  const { models, agreement, needs_review: review, risk } = result;
  const fusion = models.fusion;
  return (
    <div className="space-y-5">
      <Callout title="Model agreement" tone={agreement.all_agree ? "ok" : "warn"}>{agreement.banner}</Callout>
      <div className="grid gap-3 md:grid-cols-3">
        {GAMMA_MODELS.map(({ id, label }) => {
          const row = models[id];
          return (
            <Panel title={label} className="min-w-0" key={id}>
              <div className="space-y-3">
                <p className="text-lg font-semibold capitalize">{row.prediction}</p>
                <p className="text-sm tabular-nums text-ink-muted">{(row.confidence * 100).toFixed(1)}% confidence</p>
                <ProbBars probs={row.probabilities} highlight={row.prediction} />
                <p className="break-all text-xs text-ink-muted">{row.model_version} · {row.inference_time_ms.toFixed(1)} ms</p>
              </div>
            </Panel>
          );
        })}
      </div>
      <Panel title="Review flag">
        <div className="space-y-2">
          <Badge tone={review.flag ? "warn" : "neutral"}>{review.flag ? "Needs specialist review" : "No illustrative flag triggered"}</Badge>
          {review.reasons.length > 0 && <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">{review.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>}
          <p className="text-sm text-ink-muted">Fusion confidence threshold {review.confidence_threshold.toFixed(2)} · illustrative, not a validated operating point.</p>
        </div>
      </Panel>
      <RiskGauge risk={risk} />
      {result.fundus_heatmap && <GammaHeatmap heatmap={result.fundus_heatmap} fundus={fundus} />}
      <Callout title="Model and input provenance">
        <p>{result.caveat}</p>
        {OCT_MODE[result.oct_mode] && <p>{OCT_MODE[result.oct_mode]}.</p>}
      </Callout>
      <ResultDisclaimer text={result.disclaimer} />
      <ResultActions
        disclaimer={result.disclaimer}
        result={{ module: "multimodal", title: "GAMMA comparison", result: fusion.prediction, confidence: fusion.confidence, inputs,
          detail: { models, agreement, needs_review: review, risk, oct_mode: result.oct_mode, caveat: result.caveat, disclaimer: result.disclaimer } }}
        summary={{ module: "multimodal", prediction: fusion.prediction, confidence: fusion.confidence, probabilities: fusion.probabilities,
          models: { fundus: models.fundus.prediction, oct: models.oct.prediction, fusion: fusion.prediction },
          agreement: { all_agree: agreement.all_agree }, needs_review: { flag: review.flag, reasons: review.reasons },
          risk: { score: risk.score, level: risk.level } }}
        report={{ probabilities: fusion.probabilities, flags: review.flag ? ["Needs specialist review (illustrative)", ...review.reasons] : [],
          fundus_heatmap: result.fundus_heatmap ?? undefined }}
      />
    </div>
  );
}

export function GammaSingleResult({ result, fundus, inputs }: { result: MultimodalResult; fundus: string | null; inputs: string }) {
  return (
    <div className="space-y-5">
      <Panel title="GAMMA result" subtitle="Single-split demonstration checkpoint">
        <div className="space-y-3">
          <Badge tone={severityTone(result.prediction)}>{result.prediction}</Badge>
          <p className="text-sm text-ink-muted">{(result.confidence * 100).toFixed(1)}% confidence · {result.model_version} · {result.inference_time_ms.toFixed(1)} ms</p>
          <ProbBars probs={result.probabilities} highlight={result.prediction} />
          {OCT_MODE[result.oct_mode] && <p className="text-sm text-ink-muted">{OCT_MODE[result.oct_mode]}.</p>}
          <ResultDisclaimer text={result.disclaimer} />
        </div>
      </Panel>
      {result.fundus_heatmap && <GammaHeatmap heatmap={result.fundus_heatmap} fundus={fundus} />}
      <ResultActions
        disclaimer={result.disclaimer}
        result={{ module: "multimodal", title: "GAMMA grading", result: result.prediction, confidence: result.confidence, inputs,
          detail: { model_version: result.model_version, oct_mode: result.oct_mode, probabilities: result.probabilities, disclaimer: result.disclaimer } }}
        summary={{ module: "multimodal", prediction: result.prediction, confidence: result.confidence, probabilities: result.probabilities }}
        report={{ probabilities: result.probabilities, fundus_heatmap: result.fundus_heatmap ?? undefined }}
      />
    </div>
  );
}
