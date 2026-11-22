"use client";

import { useId, useState } from "react";
import { Badge, Button, EmptyState, ErrorNote, LoadingBlock, PageHeader, Panel } from "@/components/ui/primitives";
import { ResultDisclaimer } from "@/components/workspace/ResultActions";
import { api, type BatchItem, type BatchResult } from "@/lib/api";

const columns = [
  { key: "id", label: "Study ID" },
  { key: "status", label: "Status" },
  { key: "fusion", label: "Fusion" },
  { key: "confidence", label: "Confidence" },
  { key: "fundus", label: "Fundus" },
  { key: "oct", label: "OCT" },
  { key: "review", label: "Review" },
  { key: "risk", label: "Score band" },
] as const;
type SortKey = (typeof columns)[number]["key"];

function sortValue(item: BatchItem, key: SortKey): string | number {
  if (key === "id") return item.study_id;
  if (key === "status") return item.status;
  if (item.status === "error") return key === "confidence" ? -1 : "";
  return {
    fusion: item.fusion_prediction, confidence: item.fusion_confidence, fundus: item.fundus_prediction,
    oct: item.oct_prediction, review: item.needs_review ? 1 : 0, risk: item.risk_level,
  }[key];
}

function BatchTable({ items }: { items: BatchItem[] }) {
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: "id", desc: false });
  const rows = [...items].sort((a, b) => {
    const lhs = sortValue(a, sort.key);
    const rhs = sortValue(b, sort.key);
    const order = typeof lhs === "number" && typeof rhs === "number" ? lhs - rhs : String(lhs).localeCompare(String(rhs), undefined, { numeric: true });
    return sort.desc ? -order : order;
  });
  return (
    <div className="overflow-x-auto rounded-md border border-line" role="region" aria-label="Batch results, scroll for more columns" tabIndex={0}>
      <table className="w-full text-left text-sm">
        <thead className="bg-panel-2 text-ink-muted">
          <tr>{columns.map(({ key, label }) => (
            <th scope="col" key={key} aria-sort={sort.key === key ? (sort.desc ? "descending" : "ascending") : undefined}>
              <button type="button" className="whitespace-nowrap px-3 py-3 hover:text-ink"
                onClick={() => setSort({ key, desc: key === sort.key && !sort.desc })}>
                {label}{sort.key === key ? (sort.desc ? " ↓" : " ↑") : ""}
              </button>
            </th>
          ))}</tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((item, index) => (
            <tr key={`${item.study_id}-${index}`} className={item.status === "ok" && item.needs_review ? "bg-warn/10" : undefined}>
              <th scope="row" className="whitespace-nowrap px-3 py-2.5 font-medium">{item.study_id}</th>
              <td className="px-3 py-2.5"><Badge tone={item.status === "ok" ? "ok" : "bad"}>{item.status === "ok" ? "Analysed" : "Error"}</Badge></td>
              {item.status === "error" ? <td colSpan={6} className="min-w-56 break-words px-3 py-2.5 text-bad">{item.error}</td> : (
                <>
                  <td className="px-3 py-2.5 capitalize">{item.fusion_prediction}</td>
                  <td className="px-3 py-2.5 tabular-nums">{(item.fusion_confidence * 100).toFixed(1)}%</td>
                  <td className="px-3 py-2.5 capitalize">{item.fundus_prediction}</td>
                  <td className="px-3 py-2.5 capitalize">{item.oct_prediction}</td>
                  <td className="px-3 py-2.5">{item.needs_review ? <Badge tone="warn">Needs specialist review</Badge> : "No flag"}</td>
                  <td className="px-3 py-2.5 capitalize">{item.risk_level}</td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function BatchPage() {
  const uploadId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const [save, setSave] = useState(false);
  const [busy, setBusy] = useState<"batch" | "csv" | null>(null);
  const [result, setResult] = useState<BatchResult | null>(null);
  const [error, setError] = useState("");

  function select(files: File[]) {
    if (!files.length || busy) return;
    setResult(null);
    if (files.length !== 1 || !/\.zip$/i.test(files[0].name) || files[0].size > 150 * 1024 * 1024) {
      setFile(null);
      setError("Choose one ZIP archive up to 150 MB.");
      return;
    }
    setError("");
    setFile(files[0]);
  }

  async function run() {
    if (!file || busy) return;
    setBusy("batch");
    setError("");
    setResult(null);
    try { setResult(await api.batch(file, save)); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "Batch analysis failed."); }
    finally { setBusy(null); }
  }

  async function csv() {
    if (!result || busy) return;
    setBusy("csv");
    setError("");
    try { await api.batchCsv(result.batch_id); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "CSV unavailable."); }
    finally { setBusy(null); }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Batch analysis" description="Compare the GAMMA models for up to 100 study IDs in one ZIP archive." />
      <Panel title="Upload ZIP">
        <div className="space-y-4">
          <div className={`rounded-lg border border-dashed p-5 ${drag ? "border-accent-champagne bg-accent-champagne/5" : "border-line-strong"}`}
            onDragOver={(event) => { event.preventDefault(); if (!busy) setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(event) => { event.preventDefault(); setDrag(false); select(Array.from(event.dataTransfer.files)); }}>
            <label htmlFor={uploadId} className="block text-sm font-medium">Drop a ZIP archive here or browse</label>
            <input id={uploadId} type="file" accept=".zip,application/zip,application/x-zip-compressed" disabled={busy !== null}
              className="mt-2 block w-full text-sm text-transparent file:mr-2 file:rounded-md file:border-0 file:bg-panel-2 file:px-3 file:py-2 file:text-ink"
              onChange={(event) => { select(Array.from(event.currentTarget.files ?? [])); event.currentTarget.value = ""; }} />
            {file && <p className="mt-2 text-sm text-ink-muted" role="status">ZIP selected · {(file.size / 1024 / 1024).toFixed(1)} MB</p>}
          </div>
          <details className="rounded-md border border-line p-3 text-sm text-ink-muted">
            <summary className="cursor-pointer font-medium text-ink">Required ZIP layout</summary>
            <p className="mb-2 mt-2">Use one top-level folder per study ID, with a fundus photo and either eight ordered OCT slices or one OCT image.</p>
            <pre className="overflow-x-auto rounded bg-panel-2 p-3 text-xs">P-001/fundus.jpg<br />P-001/oct/00.jpg … 07.jpg<br />or P-001/oct.jpg</pre>
          </details>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={save} disabled={busy !== null}
            onChange={(event) => setSave(event.target.checked)} /> Save successful cases to patients</label>
          <Button type="button" onClick={run} loading={busy === "batch"} disabled={!file || busy !== null}>Run batch</Button>
          {error && <ErrorNote message={error} />}
        </div>
      </Panel>
      {busy === "batch" ? <Panel title="Analysing archive"><LoadingBlock label="Running comparisons for the submitted cases…" /></Panel>
        : result ? (
          <Panel title="Batch results" subtitle={`${result.n_cases} ${result.n_cases === 1 ? "case" : "cases"} · ${result.n_ok} successful · ${result.n_error} ${result.n_error === 1 ? "error" : "errors"}`}>
            <div className="space-y-3">
              <Button type="button" variant="secondary" loading={busy === "csv"} onClick={csv}>Download CSV</Button>
              {result.items.length > 0 ? <BatchTable items={result.items} /> : <EmptyState title="No cases returned" body="Check the folder layout and upload a new archive." />}
              <p className="text-sm text-ink-muted">Review flags use an illustrative threshold. Score bands describe model output.</p>
              <ResultDisclaimer />
            </div>
          </Panel>
        ) : <EmptyState title="No batch results yet" body="Choose a ZIP arranged by study ID and run an analysis." />}
    </div>
  );
}
