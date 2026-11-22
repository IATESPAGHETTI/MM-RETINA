"use client";

import { useEffect, useId, useState } from "react";
import { Badge, Button, ErrorNote, Panel } from "@/components/ui/primitives";
import { api, isOffline, RESEARCH_DISCLAIMER, STUDY_ID, type CaseInput, type CaseReport, type Explanation, type ExplanationSummary } from "@/lib/api";
import { addRun, useRuns } from "@/lib/history";

export function ResultDisclaimer({ text }: { text?: string | null }) {
  return <p className="text-sm leading-relaxed text-ink-muted">{text || RESEARCH_DISCLAIMER}</p>;
}

export function ResultActions({ result, summary, disclaimer, report }: {
  result: Omit<CaseInput, "patient_id" | "explanation">;
  summary: ExplanationSummary;
  disclaimer: string;
  report?: Pick<CaseReport, "probabilities" | "flags" | "fundus_heatmap">;
}) {
  const id = useId();
  const runs = useRuns();
  const [studyId, setStudyId] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [busy, setBusy] = useState<"save" | "pdf" | null>(null);
  const [saved, setSaved] = useState<{ id: string; local: boolean; persisted: boolean } | null>(null);
  const [error, setError] = useState("");
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [explainError, setExplainError] = useState("");
  const valid = STUDY_ID.test(studyId);

  useEffect(() => {
    if (studyId && !valid) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api.patients(studyId, controller.signal)
        .then((patients) => setSuggestions(patients.map((patient) => patient.study_id)))
        .catch(() => { if (!controller.signal.aborted) setSuggestions([]); });
    }, 200);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [studyId, valid]);

  const options = [...new Set([...suggestions, ...runs.flatMap((run) => run.patientId ? [run.patientId] : [])])]
    .filter((candidate) => STUDY_ID.test(candidate) && candidate.toLowerCase().includes(studyId.toLowerCase()))
    .slice(0, 12);

  async function explain() {
    setExplaining(true);
    setExplainError("");
    try { setExplanation(await api.explain(summary)); }
    catch (failure) { setExplainError(failure instanceof Error ? failure.message : "Explanation unavailable."); }
    finally { setExplaining(false); }
  }

  async function act(action: "save" | "pdf") {
    if (!valid || busy) return;
    setBusy(action);
    setError("");
    const body: CaseInput = { ...result, patient_id: studyId, explanation: explanation?.explanation };
    try {
      if (action === "pdf") await api.freshReport({ ...body, ...report });
      else {
        await api.saveCase(body);
        setSaved({ id: studyId, local: false, persisted: true });
      }
    } catch (failure) {
      if (action === "save" && isOffline(failure)) {
        if (saved?.id === studyId && saved.local) {
          setError("The patient service is still unavailable. The browser copy is available.");
          return;
        }
        const persisted = addRun({ patientId: studyId, module: result.module, title: result.title,
          result: result.result, confidence: result.confidence, inputs: result.inputs || "" });
        setSaved({ id: studyId, local: true, persisted });
      } else {
        setError(failure instanceof Error ? failure.message : "The request failed.");
      }
    } finally { setBusy(null); }
  }

  return (
    <>
      <Panel title="Explain this result">
        <div className="space-y-3">
          <p className="text-sm text-ink-muted">AI-generated, not medical advice. The service can use a template when a model is unavailable.</p>
          <Button type="button" variant="secondary" loading={explaining} onClick={explain}>
            {explaining ? "Generating explanation…" : "Explain in plain language"}
          </Button>
          {explainError && <ErrorNote message={explainError} />}
          {explanation && (
            <div className="space-y-3" aria-live="polite">
              <Badge tone="info">{explanation.source === "deepseek" ? "DeepSeek" : "Template"}</Badge>
              <p className="whitespace-pre-wrap break-words text-sm leading-relaxed text-ink">{explanation.explanation}</p>
            </div>
          )}
          <ResultDisclaimer text={explanation?.disclaimer || disclaimer} />
        </div>
      </Panel>
      <Panel title="Save to patient or download a report" subtitle="Use an assigned study ID.">
        <div className="space-y-3">
          <div>
            <label htmlFor={id} className="mb-1 block text-sm text-ink">Study ID</label>
            <input id={id} list={`${id}-studies`} autoComplete="off" spellCheck={false} maxLength={32}
              placeholder="P-001" value={studyId} disabled={busy !== null}
              aria-invalid={!!studyId && !valid} aria-describedby={`${id}-hint`}
              onChange={(event) => { setStudyId(event.target.value); setError(""); }}
              className="h-10 w-full max-w-xs rounded-md border border-line-strong bg-panel-2 px-3 text-sm focus:border-accent-champagne focus:outline-none" />
            <datalist id={`${id}-studies`}>{options.map((option) => <option value={option} key={option} />)}</datalist>
            <p id={`${id}-hint`} className={`mt-1 text-sm ${studyId && !valid ? "text-bad" : "text-ink-muted"}`}>
              Start with a letter or number. Use up to 32 letters, numbers, underscores, or hyphens.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" loading={busy === "save"} disabled={!valid || busy !== null || saved?.id === studyId} onClick={() => act("save")}>Save to patient</Button>
            <Button type="button" variant="secondary" loading={busy === "pdf"} disabled={!valid || busy !== null} onClick={() => act("pdf")}>Download PDF</Button>
            {saved?.local && saved.id === studyId && (
              <Button type="button" variant="secondary" disabled={busy !== null} onClick={() => act("save")}>Retry server save</Button>
            )}
          </div>
          {error && <ErrorNote message={error} />}
          {saved?.id === studyId && (
            <p role="status" className="text-sm text-ink-muted">
              {saved.local ? (saved.persisted ? "Saved in this browser. The patient service was unavailable." : "Saved for this session. Browser storage was unavailable.") : "Saved to the patient timeline."}{" "}
              <a className="text-accent-champagne hover:underline" href={`/workspace/patients/${studyId}`}>Open {studyId}</a>
            </p>
          )}
          <ResultDisclaimer text={disclaimer} />
        </div>
      </Panel>
    </>
  );
}
