"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button, EmptyState, ErrorNote, LoadingBlock, Panel } from "@/components/ui/primitives";
import { ResultDisclaimer } from "@/components/workspace/ResultActions";
import { api, ApiError, isOffline, MODULE_LABEL, STUDY_ID, type CaseRecord, type PatientDetail, type TrendPoint } from "@/lib/api";
import { useRuns } from "@/lib/history";

export const caseTime = (value: string | number) => new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
const detailLink = (studyId: string) => `/workspace/patients/${encodeURIComponent(studyId)}`;

function CaseReportButton({ caseId }: { caseId: number }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function download() {
    setBusy(true);
    setError("");
    try { await api.savedReport(caseId); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "Report unavailable."); }
    finally { setBusy(false); }
  }
  return (
    <div className="space-y-2">
      <Button type="button" variant="secondary" loading={busy} onClick={download}>Download PDF</Button>
      {error && <ErrorNote message={error} />}
    </div>
  );
}

export function RecentCases() {
  const [view, setView] = useState<{ items: CaseRecord[] } | { message: string } | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    api.cases({ limit: 6 }, controller.signal)
      .then(({ items }) => setView({ items }))
      .catch((failure) => {
        if (!controller.signal.aborted) setView({ message: isOffline(failure)
          ? "The case service is unavailable. Your recent browser runs are still below."
          : failure instanceof Error ? failure.message : "Could not load saved cases." });
      });
    return () => controller.abort();
  }, [attempt]);

  return (
    <Panel title="Recent saved cases" action={<Link href="/workspace/patients" className="text-sm text-accent-champagne hover:underline">Patients</Link>}>
      {!view ? <LoadingBlock label="Loading saved cases…" lines={2} />
        : "message" in view ? <ErrorNote message={view.message} onRetry={() => { setView(null); setAttempt(attempt + 1); }} />
        : view.items.length === 0 ? <EmptyState title="No saved cases" body="Save a result using a study ID to start a patient timeline." />
        : <ul className="divide-y divide-line">
          {view.items.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
              <div>
                <Link className="font-medium text-accent-champagne hover:underline" href={detailLink(item.patient_id)}>{item.patient_id}</Link>
                <p className="text-sm text-ink-muted">{MODULE_LABEL[item.module]} · {caseTime(item.created_at)}</p>
              </div>
              <p className="break-words text-sm capitalize">{item.result}</p>
            </li>
          ))}
        </ul>}
      <div className="mt-3"><ResultDisclaimer /></div>
    </Panel>
  );
}

function Trend({ points }: { points: TrendPoint[] }) {
  const values = points.flatMap((point) => typeof point.confidence === "number" && Number.isFinite(point.confidence) ? [point.confidence] : []);
  if (values.length === 0) return <p className="text-sm text-ink-muted">No confidence values yet.</p>;
  const positions = values.map((value, index) => ({
    x: values.length === 1 ? 150 : 14 + 272 * index / (values.length - 1),
    y: 76 - 62 * Math.min(1, Math.max(0, value)),
  }));
  return (
    <figure>
      <svg viewBox="0 0 300 91" className="block h-auto w-full max-w-md text-accent-champagne" role="img"
        aria-label={`Confidence across ${values.length} recorded runs. Latest ${(values.at(-1)! * 100).toFixed(1)} percent.`}>
        <path d="M14 14h272 M14 45h272 M14 76h272" stroke="currentColor" opacity=".2" />
        {positions.length > 1 && <polyline points={positions.map(({ x, y }) => `${x},${y}`).join(" ")}
          stroke="currentColor" strokeWidth="2" fill="none" vectorEffect="non-scaling-stroke" />}
        {positions.map(({ x, y }, i) => <circle key={i} cx={x} cy={y} r="3" fill="currentColor" />)}
      </svg>
      <figcaption className="text-sm text-ink-muted">Model confidence, oldest to newest. Different modules may use different scales.</figcaption>
    </figure>
  );
}

export function PatientTimeline({ studyId }: { studyId: string }) {
  const runs = useRuns();
  const [attempt, setAttempt] = useState(0);
  const [view, setView] = useState<{ data: PatientDetail } | { message: string; fallback: boolean } | null>(null);
  const valid = STUDY_ID.test(studyId);
  useEffect(() => {
    if (!valid) return;
    const controller = new AbortController();
    api.patient(studyId, controller.signal)
      .then((data) => setView({ data }))
      .catch((failure) => {
        if (controller.signal.aborted) return;
        setView({ message: failure instanceof Error ? failure.message : "Patient timeline unavailable.",
          fallback: isOffline(failure) || (failure instanceof ApiError && failure.status === 404) });
      });
    return () => controller.abort();
  }, [studyId, valid, attempt]);

  if (!valid) return <ErrorNote message="Invalid study ID. Open a patient from the study ID directory." />;
  if (!view) return <LoadingBlock label="Loading patient timeline…" />;
  if ("message" in view) {
    const local = view.fallback ? runs.filter((run) => run.patientId === studyId) : [];
    return (
      <div className="space-y-4">
        <ErrorNote message={view.message} onRetry={() => { setView(null); setAttempt(attempt + 1); }} />
        <Panel title="Browser history">
          {local.length ? <ul className="divide-y divide-line">
            {local.map((run) => <li className="py-3" key={run.id}>
              <p className="font-medium">{MODULE_LABEL[run.module]} · {run.result}</p>
              <p className="text-sm text-ink-muted">{caseTime(run.at)}</p>
            </li>)}
          </ul> : <EmptyState title="No local cases for this ID" body="Cases saved while the patient service is unavailable appear here." />}
          <div className="mt-3"><ResultDisclaimer /></div>
        </Panel>
      </div>
    );
  }

  const { trend, cases } = view.data;
  return (
    <div className="space-y-5">
      <Panel title="Confidence across saved cases"><Trend points={trend} /></Panel>
      <Panel title="Case timeline" subtitle="Most recent first">
        {cases.length === 0 ? <EmptyState title="No cases yet" body="Save a result under this study ID to add it to the timeline." /> : (
          <ol className="space-y-5 border-l border-line pl-4 sm:pl-6">
            {cases.map((record) => (
              <li key={record.id} className="space-y-2 border-b border-line pb-4 last:border-0">
                <p className="text-sm text-ink-muted">{caseTime(record.created_at)} · {MODULE_LABEL[record.module]}</p>
                <h3 className="break-words font-medium">{record.title}</h3>
                <p className="text-sm capitalize">{record.result}{typeof record.confidence === "number" && ` · ${(record.confidence * 100).toFixed(1)}% confidence`}</p>
                {record.inputs && <p className="break-words text-sm text-ink-muted">{record.inputs}</p>}
                {record.explanation && <details className="text-sm text-ink-muted">
                  <summary className="cursor-pointer">Saved explanation</summary>
                  <p className="mt-2 font-medium">AI-generated, not medical advice.</p>
                  <p className="my-2 whitespace-pre-wrap break-words">{record.explanation}</p>
                  <ResultDisclaimer />
                </details>}
                <CaseReportButton caseId={record.id} />
              </li>
            ))}
          </ol>
        )}
        <div className="mt-4"><ResultDisclaimer /></div>
      </Panel>
    </div>
  );
}
