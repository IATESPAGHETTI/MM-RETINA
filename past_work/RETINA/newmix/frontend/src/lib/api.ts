/** Typed client for the unified backend. All network access goes through here. */

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    return await parse<T>(await fetch(`${API_URL}${path}`, init));
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError(0, "Cannot reach the analysis service. Start the backend and try again.");
  }
}

// ---- types -----------------------------------------------------------------------------------------
export type Probs = Record<string, number>;

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
    if (file) fd.append("file", file);
    fd.append("clinical_json", JSON.stringify(clinical));
    fd.append("explain", String(explain));
    return request<AssessResult>("/api/glaucoma/assess", { method: "POST", body: fd });
  },

  diabetesAnalyze(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    return request<DiabetesResult>("/api/diabetes/analyze", { method: "POST", body: fd });
  },

  multimodal(form: FormData) {
    return request<MultimodalResult>("/api/glaucoma/multimodal", { method: "POST", body: form });
  },
};

export async function urlToFile(url: string, name: string): Promise<File> {
  const blob = await (await fetch(url)).blob();
  return new File([blob], name, { type: blob.type || "image/jpeg" });
}
