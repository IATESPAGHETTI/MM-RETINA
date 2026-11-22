/** Typed client for the unified backend. All network access goes through here. */

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
export const RESEARCH_DISCLAIMER = "Research prototype. Not a medical device or a substitute for specialist assessment.";
export const STUDY_ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$/;

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function checked(res: Response): Promise<Response> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (res.status === 422) detail = "The service rejected one or more fields. Check the study ID and required inputs.";
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res;
}

async function response(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await checked(await fetch(`${API_URL}${path}`, init));
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (init?.signal?.aborted) throw e;
    throw new ApiError(0, "Cannot reach the analysis service. Start the backend and try again.");
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return (await response(path, init)).json() as Promise<T>;
}

function json(body: object): RequestInit {
  return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

function uploadName(file: File) {
  const extension = file.type === "image/png" ? "png" : file.type === "image/webp" ? "webp" : "jpg";
  return `scan.${extension}`;
}

function query(params: Record<string, string | number | undefined>) {
  const result = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") result.set(key, String(value));
  }
  return result.size ? `?${result}` : "";
}

async function download(path: string, filename: string, init?: RequestInit) {
  const blob = await (await response(path, init)).blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

export function isOffline(error: unknown) {
  return error instanceof ApiError && (error.status === 0 || error.status === 503);
}

// ---- types -----------------------------------------------------------------------------------------
export type Probs = Record<string, number>;
export type Module = "glaucoma" | "diabetes" | "multimodal";
export const MODULE_LABEL: Record<Module, string> = { glaucoma: "Glaucoma", diabetes: "Diabetes (experimental)", multimodal: "Multimodal (GAMMA)" };

export type GammaModel = "fundus" | "oct" | "fusion";
export type ModelScore = Pick<MultimodalResult, "prediction" | "confidence" | "probabilities" | "inference_time_ms" | "model_version">;
export type RiskLevel = "low" | "elevated" | "high";
export interface CompareResult {
  success: boolean;
  models: Record<GammaModel, ModelScore>;
  agreement: { all_agree: boolean; n_agree: number; majority: string | null; outliers: GammaModel[]; banner: string };
  needs_review: { flag: boolean; reasons: string[]; confidence_threshold: number };
  risk: { score: number; level: RiskLevel; basis: string; note: string };
  oct_mode: string;
  fundus_heatmap: string | null;
  caveat: string;
  disclaimer: string;
}

export interface ExplanationSummary {
  module: Module;
  prediction: string;
  confidence?: number;
  probabilities?: Probs;
  models?: Record<GammaModel, string>;
  agreement?: { all_agree: boolean };
  needs_review?: { flag: boolean; reasons: string[] };
  risk?: Pick<CompareResult["risk"], "score" | "level">;
  drivers?: { feature: string; direction: string }[];
}
export interface Explanation {
  explanation: string;
  source: "deepseek" | "template";
  model: string | null;
  disclaimer: string;
}

export interface CaseInput {
  patient_id: string;
  module: Module;
  title: string;
  result: string;
  confidence?: number;
  inputs?: string;
  detail?: Record<string, unknown>;
  explanation?: string;
}
export interface CaseRecord extends Omit<CaseInput, "confidence" | "explanation"> {
  id: number;
  created_at: string;
  confidence?: number | null;
  explanation?: string | null;
}
export interface Patient {
  study_id: string;
  case_count: number;
  last_case_at: string;
  last_result: string;
  last_module: Module;
}
export interface TrendPoint {
  at: string;
  module: Module;
  result: string;
  confidence?: number | null;
}
export interface PatientDetail {
  study_id: string;
  created_at: string;
  cases: CaseRecord[];
  trend: TrendPoint[];
}
export interface CaseReport extends CaseInput {
  probabilities?: Probs;
  flags?: string[];
  fundus_heatmap?: string;
}
export type BatchItem =
  | { study_id: string; status: "error"; error: string }
  | { study_id: string; status: "ok"; fusion_prediction: string; fusion_confidence: number; probabilities: Probs;
      fundus_prediction: string; oct_prediction: string; all_agree: boolean; needs_review: boolean; risk_level: RiskLevel };
export interface BatchResult {
  batch_id: string;
  n_cases: number;
  n_ok: number;
  n_error: number;
  items: BatchItem[];
}

export interface ServiceStatus {
  ready: boolean;
  error?: string | null;
  [k: string]: unknown;
}
export interface Health {
  status: string;
  services: {
    glaucoma_oct: ServiceStatus;
    glaucoma_clinical: ServiceStatus;
    glaucoma_multimodal: ServiceStatus & { loaded: string[] };
    diabetes: { vessels: boolean; hba1c: boolean; errors: Record<string, string>; av_classification: boolean; av_note: string };
    extras?: { store: { ready: boolean }; explain: { configured: boolean; provider: string | null; model: string | null } };
  };
}

export interface DeferInfo {
  head: "clinical" | "oct" | "fused";
  deferred: boolean;
  confidence: number;
  threshold: number;
  coverage: number;
  accuracy_if_answered: number;
  accuracy_if_deferred: number;
  reliable_head: boolean;
  action: string;
}

export interface OctResult {
  classes: string[];
  probabilities: Probs;
  prediction: string;
  confidence: number;
  p_glaucoma: number;
  inference_ms: number;
  ensemble_members: number;
  heatmap: string | null;
  input_preview?: string;
  defer?: DeferInfo | null;
}
export interface ClinicalTask {
  classes: string[];
  probabilities: Probs;
  prediction: string;
  confidence: number;
}
export interface ClinicalResult {
  fields_provided: number;
  fields_total: number;
  binary: ClinicalTask;
  multiclass: ClinicalTask;
  p_glaucoma: number;
  drivers: { feature: string; label: string; value: number; effect: number }[];
  defer?: DeferInfo | null;
}
export interface FusedResult {
  classes: string[];
  probabilities: Probs;
  prediction: string;
  confidence: number;
  p_glaucoma: number;
  weights: { oct: number; clinical: number };
  agreement: boolean;
  defer?: DeferInfo | null;
}
export interface AssessResult {
  components: ("oct" | "clinical" | "fused")[];
  oct?: OctResult;
  clinical?: ClinicalResult;
  fused?: FusedResult;
  md_rule?: { md_db: number; stage: string; rule: string; note?: string };
  disclaimer: string;
}
export interface ClinicalField {
  key: string;
  label: string;
  min: number;
  max: number;
  median: number;
}

export interface DiabetesResult {
  disclaimer: string;
  modules: {
    vessels?: { overlay: string; mask: string; vessel_density_pct: number; inference_ms: number };
    fractal?: { fractal_dimension: number; r_squared: number; log_sizes: number[]; log_counts: number[]; note: string };
    hba1c?: {
      consistent: boolean;
      consistency_note: string | null;
      binary: { label: string; probability_elevated: number; confidence: number };
      multi: { bin: number; range: string; confidence: number; probabilities: Probs };
      inference_ms: number;
      validation: string;
    };
  };
  skipped: Record<string, string>;
}

export interface MultimodalResult {
  prediction: string;
  confidence: number;
  probabilities: Probs;
  inference_time_ms: number;
  model_version: string;
  oct_mode: string;
  fundus_heatmap: string | null;
  disclaimer: string;
}

type Mean = { mean: number; sd: number };
export interface ModelsInfo {
  clinical: Record<string, Record<string, Mean | Record<string, number>> | number>;
  clinical_final: Record<string, { algo: string; cv_balanced_accuracy: number }>;
  oct: { arch: string; acc: number; acc_sd: number; bal: number; qwk: number; bin_acc: number; auc: number; seeds: number }[];
  fusion: Record<string, unknown>;
  gamma: Record<string, { folds: number; accuracy: Mean; balanced_accuracy: Mean; macro_f1: Mean; auc: Mean }> & {
    dataset?: string;
  };
  defer?: Record<string, { head: string; threshold: number; target_coverage: number; coverage_achieved: number; accuracy_answered: number; accuracy_deferred: number; n_deferred: number; n: number; table: Record<string, { accuracy: number; balanced_accuracy: number }> }>;
  paper_protocol?: { seed: number; protocol: string; n_train: number; n_test: number; test_acc: number; test_balanced_acc: number; test_images_with_sibling_in_train: number }[];
  diabetes: { validation: null; note: string };
}

export interface Audit {
  research: {
    eyes: number;
    controls: number;
    glaucoma: Record<string, number>;
    reconstructed_patients: number;
    md_rule_agreement: number;
    pachy_missing_pct: Record<string, number>;
    cft_missing_pct: Record<string, number>;
    mean_age: Record<string, number>;
  };
  sankara: null | Record<string, number>;
}

// ---- calls -----------------------------------------------------------------------------------------
export const api = {
  health: () => request<Health>("/api/health"),
  models: () => request<ModelsInfo>("/api/models"),
  audit: () => request<Audit>("/api/audit"),
  clinicalSpec: () => request<{ fields: ClinicalField[] }>("/api/glaucoma/clinical/spec"),

  assess(file: File | null, clinical: Record<string, number | null>, explain = true) {
    const fd = new FormData();
    if (file) fd.append("file", file, uploadName(file));
    fd.append("clinical_json", JSON.stringify(clinical));
    fd.append("explain", String(explain));
    return request<AssessResult>("/api/glaucoma/assess", { method: "POST", body: fd });
  },

  diabetesAnalyze(file: File) {
    const fd = new FormData();
    fd.append("file", file, uploadName(file));
    return request<DiabetesResult>("/api/diabetes/analyze", { method: "POST", body: fd });
  },

  multimodal(form: FormData) {
    return request<MultimodalResult>("/api/glaucoma/multimodal", { method: "POST", body: form });
  },
  compare: (form: FormData) => request<CompareResult>("/api/glaucoma/compare", { method: "POST", body: form }),
  cases: (filters: { patient_id?: string; q?: string; module?: Module; limit?: number; offset?: number } = {}, signal?: AbortSignal) =>
    request<{ items: CaseRecord[]; total: number }>(`/api/cases${query(filters)}`, { signal }),
  case: (id: number) => request<CaseRecord>(`/api/cases/${id}`),
  saveCase: (body: CaseInput) => request<CaseRecord>("/api/cases", json(body)),
  deleteCase: (id: number) => request<{ deleted: number }>(`/api/cases/${id}`, { method: "DELETE" }),
  patients: (q?: string, signal?: AbortSignal) => request<Patient[]>(`/api/patients${query({ q })}`, { signal }),
  patient: (id: string, signal?: AbortSignal) => request<PatientDetail>(`/api/patients/${encodeURIComponent(id)}`, { signal }),
  deletePatient: (id: string) => request<{ deleted: string; cases_deleted: number }>(`/api/patients/${encodeURIComponent(id)}`, { method: "DELETE" }),
  freshReport: (report: CaseReport) => download("/api/report.pdf", `retina-${report.patient_id}.pdf`, json(report)),
  savedReport: (id: number) => download(`/api/cases/${id}/report.pdf`, `retina-case-${id}.pdf`),
  batch(file: File, save: boolean) {
    const form = new FormData();
    form.set("file", file, "batch.zip");
    form.set("save", String(save));
    return request<BatchResult>("/api/batch", { method: "POST", body: form });
  },
  batchCsv: (id: string) => download(`/api/batch/${encodeURIComponent(id)}.csv`, `retina-${id}.csv`),
  explain: (summary: ExplanationSummary) => request<Explanation>("/api/explain", json({ summary })),
};

export async function urlToFile(url: string, name: string): Promise<File> {
  const res = await fetch(url);
  if (!res.ok || !res.headers.get("content-type")?.startsWith("image/")) throw new Error("The sample image could not be loaded.");
  const blob = await res.blob();
  return new File([blob], name, { type: blob.type || "image/jpeg" });
}
