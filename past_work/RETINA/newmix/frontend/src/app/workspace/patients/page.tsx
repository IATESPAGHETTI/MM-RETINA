"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState, ErrorNote, LoadingBlock, PageHeader, Panel } from "@/components/ui/primitives";
import { caseTime } from "@/components/workspace/PatientCases";
import { ResultDisclaimer } from "@/components/workspace/ResultActions";
import { api, isOffline, MODULE_LABEL, STUDY_ID, type Patient } from "@/lib/api";
import { useRuns } from "@/lib/history";

export default function PatientsPage() {
  const [search, setSearch] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [view, setView] = useState<{ patients: Patient[] } | { message: string; offline: boolean } | null>(null);
  const runs = useRuns();
  const valid = !search || STUDY_ID.test(search);

  useEffect(() => {
    if (!valid) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api.patients(search, controller.signal)
        .then((patients) => setView({ patients }))
        .catch((failure) => {
          if (!controller.signal.aborted) setView({ message: failure instanceof Error ? failure.message : "Patient directory unavailable.", offline: isOffline(failure) });
        });
    }, 180);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [search, valid, attempt]);

  const local = new Map<string, Patient>();
  if (view && "offline" in view && view.offline) {
    for (const run of runs) {
      if (!run.patientId || !STUDY_ID.test(run.patientId) || !run.patientId.toLowerCase().includes(search.toLowerCase())) continue;
      const existing = local.get(run.patientId);
      if (existing) existing.case_count++;
      else local.set(run.patientId, { study_id: run.patientId, case_count: 1, last_case_at: new Date(run.at).toISOString(),
        last_result: run.result, last_module: run.module });
    }
  }
  const patients = view && "patients" in view ? view.patients : [...local.values()];
  return (
    <div className="space-y-6">
      <PageHeader title="Patients" description="Find a study ID and review its saved case timeline." />
      <Panel title="Study ID directory">
        <label htmlFor="patient-search" className="block text-sm text-ink-muted">Search study IDs</label>
        <input id="patient-search" type="search" value={search} autoComplete="off" maxLength={32}
          aria-invalid={!valid} placeholder="P-001" className="mb-4 mt-1 h-10 w-full max-w-sm rounded-md border border-line-strong bg-panel-2 px-3 text-sm"
          onChange={(event) => { setSearch(event.target.value); setView(null); }} />
        {!valid ? <ErrorNote message="Search using letters, numbers, underscores, or hyphens." />
          : !view ? <LoadingBlock label="Loading patients…" lines={2} />
          : <>
            {"message" in view && <ErrorNote message={view.offline ? "The patient service is unavailable. Showing matching browser cases." : view.message}
              onRetry={() => { setView(null); setAttempt(attempt + 1); }} />}
            {patients.length === 0 ? <div className="mt-3"><EmptyState title={search ? "No matching study IDs" : "No patients yet"}
              body={search ? "Try a shorter part of the study ID." : "Save an analysis under a study ID to create a timeline."} /></div> : (
                <ul className="mt-3 divide-y divide-line">
                  {patients.map((patient) => (
                    <li key={patient.study_id}>
                      <Link href={`/workspace/patients/${encodeURIComponent(patient.study_id)}`}
                        className="flex flex-wrap items-center justify-between gap-2 rounded py-3 hover:text-accent-champagne">
                        <div>
                          <p className="font-medium">{patient.study_id}</p>
                          <p className="text-sm text-ink-muted">{patient.case_count} {patient.case_count === 1 ? "case" : "cases"} · {caseTime(patient.last_case_at)}</p>
                        </div>
                        <p className="max-w-full break-words text-sm text-ink-muted">{MODULE_LABEL[patient.last_module]} · {patient.last_result}</p>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
          </>}
        <div className="mt-3"><ResultDisclaimer /></div>
      </Panel>
    </div>
  );
}
