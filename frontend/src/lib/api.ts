const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface HealthStatus {
  status: string;
  app_name: string;
  environment: string;
  database: string;
}

export interface DatasetItem {
  query: string;
  expected_output?: string;
  context?: string[];
  metadata?: Record<string, unknown>;
}

export interface Dataset {
  id: string;
  name: string;
  description?: string;
  version: number;
  items?: DatasetItem[];
  created_at: string;
}

export interface Experiment {
  id: string;
  name: string;
  dataset_id: string;
  provider_name: string;
  model_name?: string;
  is_baseline: boolean;
  status: string;
  summary_metrics: Record<string, number>;
  created_at: string;
}

export interface RegressionReport {
  has_regression: boolean;
  regressed_metrics: string[];
  tolerance: number;
  details: Record<
    string,
    {
      candidate_score: number;
      baseline_score: number;
      delta: number;
      regressed: boolean;
    }
  >;
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error("Backend offline");
  return res.json();
}

export async function fetchDatasets(): Promise<Dataset[]> {
  const res = await fetch(`${API_BASE}/datasets`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch datasets");
  return res.json();
}

export async function createDataset(payload: {
  name: string;
  description?: string;
  items: DatasetItem[];
}): Promise<Dataset> {
  const res = await fetch(`${API_BASE}/datasets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create dataset");
  return res.json();
}

export async function fetchExperiments(): Promise<Experiment[]> {
  const res = await fetch(`${API_BASE}/experiments`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch experiments");
  return res.json();
}

export async function runExperiment(payload: {
  name: string;
  dataset_id: string;
  provider_name: string;
  model_name?: string;
}): Promise<Experiment> {
  const res = await fetch(`${API_BASE}/experiments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to run experiment");
  return res.json();
}

export async function setBaseline(experimentId: string): Promise<Experiment> {
  const res = await fetch(`${API_BASE}/experiments/${experimentId}/set-baseline`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to set baseline");
  return res.json();
}

export async function checkRegression(
  experimentId: string,
  tolerance = 0.02
): Promise<RegressionReport> {
  const res = await fetch(
    `${API_BASE}/experiments/${experimentId}/check-regression?tolerance=${tolerance}`,
    { cache: "no-store" }
  );
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to check regression");
  }
  return res.json();
}