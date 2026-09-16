"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { GlassCard } from "@/components/GlassCard";
import { Reveal } from "@/components/Reveal";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Modality = "fundus" | "oct" | "fusion";

const DEMO_IMAGES = {
  fundus: "/demo/fundus/gamma-0001.jpg",
  oct: "/demo/oct/gamma-0001-slice128.jpg",
};

type PredictResult = {
  success: boolean;
  prediction: string;
  confidence: number;
  probabilities: Record<string, number>;
  inference_time_ms: number;
  model_version: string;
  oct_repeated_single_slice: boolean;
};

async function urlToFile(url: string, filename: string): Promise<File> {
  const res = await fetch(url);
  const blob = await res.blob();
  return new File([blob], filename, { type: blob.type });
}

export default function DemoPage() {
  const [modality, setModality] = useState<Modality>("fusion");
  const [fundusFile, setFundusFile] = useState<File | null>(null);
  const [octFile, setOctFile] = useState<File | null>(null);
  const [fundusPreview, setFundusPreview] = useState<string | null>(null);
  const [octPreview, setOctPreview] = useState<string | null>(null);

  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [modelsLoaded, setModelsLoaded] = useState<string[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PredictResult | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then((r) => {
        if (!r.ok) throw new Error("unhealthy");
        return r.json();
      })
      .then((data) => {
        setBackendStatus("online");
        setModelsLoaded(data.models_loaded || []);
      })
      .catch(() => setBackendStatus("offline"));
  }, []);

  function onFileChange(kind: "fundus" | "oct", file: File | null) {
    setResult(null);
    setError(null);
    if (kind === "fundus") {
      setFundusFile(file);
      setFundusPreview(file ? URL.createObjectURL(file) : null);
    } else {
      setOctFile(file);
      setOctPreview(file ? URL.createObjectURL(file) : null);
    }
  }

  async function selectDemo(kind: "fundus" | "oct") {
    const file = await urlToFile(DEMO_IMAGES[kind], `demo-${kind}.jpg`);
    onFileChange(kind, file);
  }

  const needsFundus = modality === "fundus" || modality === "fusion";
  const needsOct = modality === "oct" || modality === "fusion";
  const canRun =
    backendStatus === "online" &&
    !loading &&
    (!needsFundus || fundusFile) &&
    (!needsOct || octFile);

  async function runAnalysis() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const form = new FormData();
      form.append("modality", modality);
      if (needsFundus && fundusFile) form.append("fundus", fundusFile);
      if (needsOct && octFile) form.append("oct", octFile);

      const res = await fetch(`${API_URL}/api/predict`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `Request failed (HTTP ${res.status})`);
      }
      setResult(data);
    } catch (e) {
      if (e instanceof TypeError) {
        setError("Could not reach the inference backend. Is it running? See backend/README.md.");
      } else {
        setError(e instanceof Error ? e.message : "Inference failed.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="pt-20">
      <section className="mx-auto max-w-3xl px-6 pt-20 pb-8 text-center">
        <Reveal>
          <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">Demo</p>
          <h1 className="text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
            Inference demo
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-ink-muted">
            Runs the actual trained model. Research prototype — not for clinical diagnosis.
          </p>
        </Reveal>
      </section>

      <section className="mx-auto max-w-2xl px-6 py-8">
        <Reveal className="mb-6 flex justify-center">
          {backendStatus === "checking" && (
            <span className="text-xs text-ink-faint">Checking backend…</span>
          )}
          {backendStatus === "online" && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-ink-muted">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              Backend online — models loaded: {modelsLoaded.join(", ") || "none"}
            </span>
          )}
          {backendStatus === "offline" && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-300/20 bg-amber-300/10 px-3 py-1 text-xs text-amber-200">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-300" />
              Backend unreachable at {API_URL} — start it (see backend/README.md)
            </span>
          )}
        </Reveal>

        <Reveal delay={0.1}>
          <GlassCard strong>
            <div className="mb-6 flex justify-center gap-2">
              {(["fundus", "oct", "fusion"] as Modality[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => {
                    setModality(m);
                    setResult(null);
                    setError(null);
                  }}
                  className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                    modality === m ? "bg-ink text-bg" : "border border-white/12 text-ink-muted hover:text-ink"
                  }`}
                >
                  {m === "fundus" ? "Fundus" : m === "oct" ? "OCT" : "Fusion"}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div
                className={`flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed p-6 text-center transition-colors ${
                  needsFundus ? "border-white/20" : "border-white/8 opacity-40"
                }`}
              >
                {fundusPreview ? (
                  <div className="relative h-24 w-24 overflow-hidden rounded-lg">
                    <Image src={fundusPreview} alt="Fundus preview" fill className="object-cover" unoptimized />
                  </div>
                ) : (
                  <span className="text-sm font-medium text-ink">Fundus image</span>
                )}
                <div className="flex gap-2 text-xs">
                  <label className="cursor-pointer text-ink-muted underline underline-offset-4 hover:text-ink">
                    Upload
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      className="hidden"
                      disabled={!needsFundus}
                      onChange={(e) => onFileChange("fundus", e.target.files?.[0] ?? null)}
                    />
                  </label>
                  <button
                    type="button"
                    disabled={!needsFundus}
                    onClick={() => selectDemo("fundus")}
                    className="text-ink-muted underline underline-offset-4 hover:text-ink disabled:opacity-40"
                  >
                    Select demo
                  </button>
                </div>
              </div>

              <div
                className={`flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed p-6 text-center transition-colors ${
                  needsOct ? "border-white/20" : "border-white/8 opacity-40"
                }`}
              >
                {octPreview ? (
                  <div className="relative h-24 w-24 overflow-hidden rounded-lg">
                    <Image src={octPreview} alt="OCT preview" fill className="object-cover" unoptimized />
                  </div>
                ) : (
                  <span className="text-sm font-medium text-ink">OCT B-scan</span>
                )}
                <div className="flex gap-2 text-xs">
                  <label className="cursor-pointer text-ink-muted underline underline-offset-4 hover:text-ink">
                    Upload
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      className="hidden"
                      disabled={!needsOct}
                      onChange={(e) => onFileChange("oct", e.target.files?.[0] ?? null)}
                    />
                  </label>
                  <button
                    type="button"
                    disabled={!needsOct}
                    onClick={() => selectDemo("oct")}
                    className="text-ink-muted underline underline-offset-4 hover:text-ink disabled:opacity-40"
                  >
                    Select demo
                  </button>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={runAnalysis}
              disabled={!canRun}
              className="mt-6 w-full rounded-full bg-ink px-6 py-3 text-sm font-medium text-bg transition-opacity disabled:cursor-not-allowed disabled:opacity-30"
            >
              {loading ? "Running…" : "Run analysis"}
            </button>

            {error && (
              <p className="mt-4 rounded-lg border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">
                {error}
              </p>
            )}

            {result && (
              <div className="mt-6 border-t border-white/10 pt-6 text-center">
                <p className="text-xs uppercase tracking-[0.3em] text-ink-faint">Prediction</p>
                <p className="mt-2 text-3xl font-semibold capitalize tracking-tight text-ink">
                  {result.prediction}
                </p>
                <p className="mt-1 text-sm text-accent-champagne">
                  {(result.confidence * 100).toFixed(1)}% confidence
                </p>

                <div className="mx-auto mt-6 flex max-w-sm justify-center gap-6">
                  {Object.entries(result.probabilities).map(([label, p]) => (
                    <div key={label}>
                      <div className="text-lg font-medium text-ink-muted">{(p * 100).toFixed(0)}%</div>
                      <div className="mt-1 text-xs uppercase tracking-wider text-ink-faint">{label}</div>
                    </div>
                  ))}
                </div>

                <p className="mt-6 text-xs text-ink-faint">
                  {result.inference_time_ms.toFixed(1)}ms inference · model {result.model_version}
                  {result.oct_repeated_single_slice && (
                    <> · single OCT image repeated across the model&apos;s expected slice sequence</>
                  )}
                </p>
              </div>
            )}
          </GlassCard>
        </Reveal>

        <Reveal delay={0.2} className="mt-6">
          <p className="text-center text-xs text-ink-faint">
            Demo predictions are generated by the project&apos;s trained model
            and are for research demonstration only. They are not medical
            diagnoses.
          </p>
        </Reveal>
      </section>
    </div>
  );
}
