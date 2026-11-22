"use client";

import { useEffect, useId, useState } from "react";
import { api, urlToFile, type CompareResult, type GammaModel, type MultimodalResult } from "@/lib/api";
import { addRun } from "@/lib/history";
import { OCTViewer } from "@/components/OCTViewer";
import { Button, EmptyState, ErrorNote, LoadingBlock, PageHeader, Panel, UploadZone } from "@/components/ui/primitives";
import { GAMMA_MODELS, GammaComparison, GammaSingleResult } from "@/components/workspace/GammaComparison";

type Mode = GammaModel | "compare";
type Volume = { kind: "sample" | "upload"; files: File[] };
type Run = { inputs: string } & ({ kind: "compare"; data: CompareResult } | { kind: "single"; data: MultimodalResult });
const SLICES = [0, 36, 73, 109, 146, 182, 219, 255];
const MODES = [{ id: "compare", label: "Compare all models" }, ...GAMMA_MODELS] as const;
const ACCEPT = "image/jpeg,image/png,image/webp";
const imageSuffix = (file: File) => file.type === "image/png" ? "png" : file.type === "image/webp" ? "webp" : "jpg";

function usePreviews(files: readonly File[]) {
  const [previews, setPreviews] = useState<{ files: readonly File[]; urls: string[] }>();
  useEffect(() => {
    if (!files.length) return;
    const urls = files.map((file) => URL.createObjectURL(file));
    const timer = window.setTimeout(() => setPreviews({ files, urls }), 0);
    return () => { window.clearTimeout(timer); urls.forEach((url) => URL.revokeObjectURL(url)); };
  }, [files]);
  return previews?.files === files ? previews.urls : [];
}
const EMPTY: File[] = [];

export default function MultimodalPage() {
  const fileInput = useId();
  const [mode, setMode] = useState<Mode>("compare");
  const [fundus, setFundus] = useState<File[]>(EMPTY);
  const [single, setSingle] = useState<File[]>(EMPTY);
  const [volume, setVolume] = useState<Volume | null>(null);
  const [explain, setExplain] = useState(true);
  const [busy, setBusy] = useState<"sample" | "analysis" | null>(null);
  const [result, setResult] = useState<Run | null>(null);
  const [error, setError] = useState("");
  const [inputError, setInputError] = useState("");
  const fundusUrl = usePreviews(fundus)[0] ?? null;
  const singleUrl = usePreviews(single)[0] ?? null;
  const volumeUrls = usePreviews(volume?.kind === "upload" ? volume.files : EMPTY);

  const needFundus = mode !== "oct";
  const needOct = mode !== "fundus";
  const canRun = !busy && (!needFundus || fundus.length > 0) && (!needOct || !!volume || single.length > 0);

  function clearResult() { setResult(null); setError(""); }

  async function loadSample() {
    setBusy("sample");
    clearResult();
    setInputError("");
    try {
      const [image, ...slices] = await Promise.all([
        urlToFile("/demo/fundus/gamma-0001.jpg", "fundus.jpg"),
        ...SLICES.map((slice) => {
          const file = String(slice).padStart(3, "0") + ".jpg";
          return urlToFile(`/oct-volume/0001/${file}`, file);
        }),
      ]);
      setFundus([image]);
      setVolume({ kind: "sample", files: slices });
      setSingle(EMPTY);
    } catch {
      setInputError("Could not load the sample eye. Try again or upload images.");
    } finally { setBusy(null); }
  }

  function setSlices(files: File[]) {
    clearResult();
    if (files.length !== 8 || files.some((file) => !ACCEPT.split(",").includes(file.type))) {
      setVolume(null);
      setSingle(EMPTY);
      setInputError("Select exactly eight JPEG, PNG, or WebP slices.");
      return;
    }
    setInputError("");
    setVolume({ kind: "upload", files: files.sort((a, b) => a.name.localeCompare(b.name, "en", { numeric: true })) });
    setSingle(EMPTY);
  }

  async function run() {
    if (!canRun) return;
    setBusy("analysis");
    clearResult();
    const form = new FormData();
    if (mode !== "compare") form.set("modality", mode);
    if (needFundus && fundus[0]) form.set("fundus", fundus[0], `fundus.${imageSuffix(fundus[0])}`);
    if (needOct && volume) volume.files.forEach((file, i) => form.append("oct_slices", file, `slice-${i}.${imageSuffix(file)}`));
    else if (needOct && single[0]) form.set("oct", single[0], `oct.${imageSuffix(single[0])}`);
    form.set("explain", String(needFundus && explain));
    const inputs = [needFundus ? "fundus" : "", needOct ? (volume ? "8 OCT slices" : "single OCT B-scan") : ""].filter(Boolean).join(" + ");
    try {
      if (mode === "compare") {
        const data = await api.compare(form);
        setResult({ kind: "compare", data, inputs });
        addRun({ module: "multimodal", title: "GAMMA comparison", result: data.models.fusion.prediction, confidence: data.models.fusion.confidence, inputs });
      } else {
        const data = await api.multimodal(form);
        setResult({ kind: "single", data, inputs });
        addRun({ module: "multimodal", title: "GAMMA grading", result: data.prediction, confidence: data.confidence, inputs });
      }
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Grading failed.");
    } finally { setBusy(null); }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Multimodal grading" eyebrow="GAMMA"
        description="Compare the fundus, OCT, and fusion models on the same eye."
        actions={<Button type="button" variant="secondary" loading={busy === "sample"} disabled={busy !== null} onClick={loadSample}>Load sample eye</Button>} />
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(255px,1fr)_minmax(0,2fr)]">
        <Panel title="Inputs">
          <div className="space-y-4">
            <label className="block text-sm text-ink-muted">Analysis mode
              <select aria-label="Analysis mode" className="mt-1 h-10 w-full rounded-md border border-line-strong bg-panel-2 px-2 text-ink"
                value={mode} disabled={!!busy} onChange={(event) => { setMode(event.target.value as Mode); clearResult(); }}>
                {MODES.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </select>
            </label>
            {needFundus && <UploadZone label="Fundus photograph" hint="JPEG, PNG, or WebP" file={fundus[0] ?? null} previewUrl={fundusUrl}
              onFile={(file) => { setFundus(file ? [file] : EMPTY); clearResult(); }} disabled={!!busy} />}
            {needOct && (
              <>
                <div className="space-y-1">
                  <label htmlFor={fileInput} className="block text-sm text-ink">OCT volume</label>
                  <input type="file" id={fileInput} accept={ACCEPT} multiple disabled={!!busy}
                    className="block w-full text-sm text-transparent file:mr-2 file:rounded-md file:border-0 file:bg-panel-2 file:px-3 file:py-2 file:text-ink"
                    onChange={(event) => {
                      const files = Array.from(event.currentTarget.files ?? []);
                      event.currentTarget.value = "";
                      if (files.length) setSlices(files);
                    }} />
                  <p className="text-xs text-ink-muted">Select eight images. The filename order sets the slice order.</p>
                </div>
                {volume ? (
                  <div className="space-y-2">
                    <p className="text-sm text-ink-muted">{volume.kind === "sample" ? "Eight slices sampled from the 256-slice volume for inference." : "Eight uploaded slices, in filename order."}</p>
                    {volume.kind === "sample"
                      ? <OCTViewer key="sample" sampleId="0001" numSlices={256} compact />
                      : volumeUrls.length === 8 && <OCTViewer key={volumeUrls[0]} sampleId="upload" label="Uploaded OCT volume" numSlices={8} sliceUrls={volumeUrls} compact />}
                    <Button type="button" variant="ghost" disabled={!!busy} onClick={() => { setVolume(null); setInputError(""); clearResult(); }}>Remove volume</Button>
                  </div>
                ) : (
                  <UploadZone label="Single OCT B-scan" hint="The model repeats this slice across its expected input." file={single[0] ?? null} previewUrl={singleUrl}
                    onFile={(file) => { setSingle(file ? [file] : EMPTY); setInputError(""); clearResult(); }} disabled={!!busy} />
                )}
              </>
            )}
            {inputError && <ErrorNote message={inputError} />}
            {needFundus && (
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={explain} disabled={!!busy} onChange={(event) => { setExplain(event.target.checked); clearResult(); }} /> Generate fundus Grad-CAM</label>
            )}
            <Button type="button" onClick={run} loading={busy === "analysis"} disabled={!canRun}>{mode === "compare" ? "Run comparison" : "Run grading"}</Button>
          </div>
        </Panel>
        <div className="min-w-0">
          {busy === "analysis" ? <Panel title="Analysing"><LoadingBlock label="Running the selected models…" /></Panel>
            : error ? <ErrorNote message={error} onRetry={canRun ? run : undefined} />
            : result?.kind === "compare" ? <GammaComparison result={result.data} fundus={fundusUrl} inputs={result.inputs} />
            : result ? <GammaSingleResult result={result.data} fundus={fundusUrl} inputs={result.inputs} />
            : <EmptyState title="No analysis yet" body="Load the sample or upload a fundus photo and OCT to compare the three models." />}
        </div>
      </div>
    </div>
  );
}
