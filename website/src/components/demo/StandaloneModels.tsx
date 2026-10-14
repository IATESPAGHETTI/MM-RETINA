"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { API_URL } from "@/lib/api";
import { GlassCard } from "@/components/GlassCard";
import type { PredictResult } from "./AnalysisReport";

type Reliability = {
  tier: "strong" | "moderate" | "weak" | "chance";
  label: string;
  rule: string;
  roc_auc: number;
  kappa: number;
};

type Field = { key: string; label: string; unit: string; min: number; max: number; median: number };
type CohortSchema = {
  title: string;
  version: string;
  class_names: string[];
  n_train: number;
  split: string;
  reliability: Reliability;
  features: Field[];
};

type TabularResult = {
  request_id: string;
  cohort: string;
  title: string;
  model_version: string;
  prediction: string;
  confidence: number;
  probabilities: Record<string, number>;
  drivers: { feature: string; label: string; contribution: number; direction: string; imputed: boolean }[];
  imputed_features: string[];
  out_of_range: { feature: string; value: number; train_min: number; train_max: number }[];
  reliability: Reliability;
  split: string;
};

const TIER_STYLE: Record<Reliability["tier"], string> = {
  strong: "border-accent-champagne/50 bg-accent-champagne/10 text-accent-champagne",
  moderate: "border-accent-olive/50 bg-accent-olive/10 text-accent-olive",
  weak: "border-amber-300/30 bg-amber-300/10 text-amber-200",
  chance: "border-red-400/30 bg-red-400/10 text-red-200",
};

export function ReliabilityBadge({ r }: { r: Reliability }) {
  return (
    <span
      title={`${r.rule}. Measured: ROC-AUC ${r.roc_auc.toFixed(2)}, kappa ${r.kappa.toFixed(2)}.`}
      className={clsx("inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px]", TIER_STYLE[r.tier])}
    >
      {r.label}
    </span>
  );
}

function ProbBars({ probs, top }: { probs: Record<string, number>; top: string }) {
  return (
    <ul className="space-y-2">
      {Object.entries(probs).map(([label, p]) => (
        <li key={label} className="grid grid-cols-[5.5rem_1fr_2.5rem] items-center gap-3 text-sm">
          <span className={clsx("capitalize", label === top ? "font-medium text-ink" : "text-ink-muted")}>{label}</span>
          <div className="h-2 overflow-hidden rounded-full bg-white/10" aria-hidden>
            <div
              className={clsx("h-full rounded-full", label === top ? "bg-accent-champagne" : "bg-ink-muted/50")}
              style={{ width: `${p * 100}%` }}
            />
          </div>
          <span className="text-right tabular-nums text-ink-muted">{(p * 100).toFixed(0)}%</span>
        </li>
      ))}
    </ul>
  );
}

type Props = { imaging: PredictResult | null };

/**
 * HVF and RNFL/GCC cannot be paired with GAMMA fundus+OCT (no shared patient
 * identity), so each is its own model on its own scale. The summary lists the
 * results side by side and never merges them.
 */
export function StandaloneModels({ imaging }: Props) {
  const [schema, setSchema] = useState<Record<string, CohortSchema> | null>(null);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [cohort, setCohort] = useState<string>("rnfl_gcc");
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [results, setResults] = useState<Record<string, TabularResult>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/tabular/schema`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("schema unavailable"))))
      .then((s: Record<string, CohortSchema>) => {
        setSchema(s);
        setCohort(Object.keys(s).includes("rnfl_gcc") ? "rnfl_gcc" : Object.keys(s)[0]);
      })
      .catch(() => setSchemaError("Standalone models are unavailable (backend offline or models not loaded)."));
  }, []);

  if (schemaError) {
    return <p className="mt-6 text-center text-xs text-ink-faint">{schemaError}</p>;
  }
  if (!schema) return null;

  const cfg = schema[cohort];
  const result = results[cohort];

  function selectCohort(c: string) {
    setCohort(c);
    setInputs({});
    setError(null);
  }

  function fillTypical() {
    setInputs(Object.fromEntries(cfg.features.map((f) => [f.key, String(Math.round(f.median * 100) / 100)])));
  }

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const values: Record<string, number | null> = {};
      for (const f of cfg.features) {
        const raw = (inputs[f.key] ?? "").trim();
        if (raw === "") {
          values[f.key] = null;
          continue;
        }
        const n = Number(raw);
        if (!Number.isFinite(n)) throw new Error(`${f.label}: enter a number`);
        values[f.key] = n;
      }
      const res = await fetch(`${API_URL}/api/predict/tabular/${cohort}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Request failed (HTTP ${res.status})`);
      setResults((prev) => ({ ...prev, [cohort]: data }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Prediction failed.");
    } finally {
      setLoading(false);
    }
  }

  const summaryRows = [
    ...(imaging
      ? [{
          key: "imaging",
          name: imaging.modality === "fusion" ? "Fundus + OCT (fused)" : imaging.modality === "oct" ? "OCT" : "Fundus",
          scale: "normal / early / progressive",
          prediction: imaging.prediction,
          confidence: imaging.confidence,
          badge: null as Reliability | null,
        }]
      : []),
    ...Object.values(results).map((r) => ({
      key: r.cohort,
      name: r.title,
      scale: "mild / moderate / severe",
      prediction: r.prediction,
      confidence: r.confidence,
      badge: r.reliability,
    })),
  ];

  return (
    <section className="mx-auto mt-16 max-w-2xl px-6" aria-labelledby="standalone-title">
      <div className="mb-6 text-center">
        <p className="mb-2 text-xs uppercase tracking-[0.3em] text-ink-faint">Standalone models</p>
        <h2 id="standalone-title" className="text-2xl font-semibold tracking-tight text-ink">
          Visual field and OCT thickness
        </h2>
        <p className="mx-auto mt-3 max-w-lg text-sm text-ink-muted">
          These datasets share no patient identity with the fundus + OCT data, so they can&apos;t be fused with it.
          Each runs as its own model on its own scale, and results are listed side by side — never merged.
        </p>
      </div>

      <GlassCard strong>
        <div className="mb-5 flex justify-center gap-2" role="tablist" aria-label="Standalone model">
          {Object.entries(schema).map(([key, s]) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={cohort === key}
              onClick={() => selectCohort(key)}
              className={clsx(
                "rounded-full px-4 py-1.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne",
                cohort === key ? "bg-ink text-bg" : "border border-white/12 text-ink-muted hover:text-ink"
              )}
            >
              {s.title}
            </button>
          ))}
        </div>

        <div className="mb-5 flex flex-wrap items-center justify-between gap-2 text-xs text-ink-faint">
          <ReliabilityBadge r={cfg.reliability} />
          <span>
            Trained on {cfg.n_train} eyes · {cfg.split}
          </span>
        </div>

        <div className="grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2">
          {cfg.features.map((f) => (
            <label key={f.key} className="block text-xs text-ink-muted">
              <span className="flex justify-between">
                <span>{f.label}</span>
                <span className="text-ink-faint">{f.unit}</span>
              </span>
              <input
                type="number"
                inputMode="decimal"
                step="any"
                value={inputs[f.key] ?? ""}
                placeholder={`${f.min}–${f.max}`}
                onChange={(e) => setInputs((p) => ({ ...p, [f.key]: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-white/12 bg-white/[0.03] px-3 py-1.5 text-sm text-ink placeholder:text-ink-faint focus-visible:outline-2 focus-visible:outline-accent-champagne"
              />
            </label>
          ))}
        </div>
        <p className="mt-3 text-[11px] text-ink-faint">
          Leave a field blank to use the training median (reported in the result). Placeholders show the training range.
        </p>

        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            onClick={run}
            disabled={loading}
            className="w-full rounded-full bg-ink px-6 py-3 text-sm font-medium text-bg transition-opacity focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne disabled:cursor-not-allowed disabled:opacity-30"
          >
            {loading ? "Running…" : "Run model"}
          </button>
          <button
            type="button"
            onClick={fillTypical}
            className="w-full whitespace-nowrap rounded-full border border-white/15 px-6 py-3 text-sm font-medium text-ink transition-colors hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne sm:w-auto"
          >
            Fill typical values
          </button>
        </div>

        {error && (
          <p role="alert" className="mt-4 rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
            {error}
          </p>
        )}

        {result && (
          <div className="mt-6 border-t border-white/10 pt-6" aria-live="polite">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-2xl font-semibold capitalize tracking-tight text-ink">{result.prediction}</h3>
              <span className="text-xs text-ink-faint">
                {(result.confidence * 100).toFixed(0)}% · {result.model_version} · {result.request_id}
              </span>
            </div>

            {result.reliability.tier === "chance" && (
              <p className="mt-3 rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-xs text-red-100">
                This model scored ROC-AUC {result.reliability.roc_auc.toFixed(2)} in cross-validation — about the same
                as guessing. Its output is shown for transparency; do not read anything into it.
              </p>
            )}

            <div className="mt-4">
              <ProbBars probs={result.probabilities} top={result.prediction} />
            </div>

            <h4 className="mt-5 text-xs uppercase tracking-[0.2em] text-ink-faint">Largest drivers</h4>
            <ul className="mt-2 space-y-1 text-xs text-ink-muted">
              {result.drivers.map((d) => (
                <li key={d.feature}>
                  <span className="text-ink">{d.label}</span> pushed the result {d.direction}{" "}
                  <span className="capitalize">{result.prediction}</span> ({d.contribution > 0 ? "+" : ""}
                  {d.contribution.toFixed(2)}){d.imputed && <span className="text-ink-faint"> — imputed</span>}
                </li>
              ))}
            </ul>
            <p className="mt-1 text-[11px] text-ink-faint">
              Exact for this linear model: coefficient × standardised value. It describes the model, not the eye.
            </p>

            {result.imputed_features.length > 0 && (
              <p className="mt-3 text-xs text-amber-200">
                {result.imputed_features.length} field(s) filled with the training median.
              </p>
            )}
            {result.out_of_range.length > 0 && (
              <p className="mt-2 text-xs text-amber-200">
                Outside the training range (extrapolating): {result.out_of_range.map((o) => o.feature).join(", ")}.
              </p>
            )}
          </div>
        )}
      </GlassCard>

      {summaryRows.length > 0 && (
        <div className="mt-6 rounded-2xl border border-white/10 p-5" aria-label="Evidence summary">
          <h3 className="text-xs uppercase tracking-[0.2em] text-ink-faint">Evidence summary — separate models</h3>
          <ul className="mt-3 divide-y divide-white/8">
            {summaryRows.map((r) => (
              <li key={r.key} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
                <span className="text-ink">{r.name}</span>
                <span className="flex items-center gap-3">
                  <span className="text-ink-muted">
                    <span className="capitalize">{r.prediction}</span> · {(r.confidence * 100).toFixed(0)}%
                  </span>
                  {r.badge && <ReliabilityBadge r={r.badge} />}
                </span>
                <span className="w-full text-[11px] text-ink-faint">scale: {r.scale}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">
            Different scales, different cohorts, different models. There is deliberately no combined score.
          </p>
        </div>
      )}
    </section>
  );
}
