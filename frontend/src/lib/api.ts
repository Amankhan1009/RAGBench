const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface User {
  id: string;
  email: string;
  name?: string;
  workspace_id: string;
  workspace_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("ragbench_jwt_token");
}

export function setToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("ragbench_jwt_token", token);
  }
}

export function removeToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("ragbench_jwt_token");
  }
}

export function getAuthHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function registerUser(
  email: string,
  password: string,
  name?: string
): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Registration failed");
  }
  const data: AuthResponse = await res.json();
  setToken(data.access_token);
  return data;
}

export async function loginUser(
  email: string,
  password: string
): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Invalid email or password");
  }
  const data: AuthResponse = await res.json();
  setToken(data.access_token);
  return data;
}

export async function fetchCurrentUser(): Promise<User | null> {
  const token = getToken();
  if (!token) return null;
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) {
    removeToken();
    return null;
  }
  return res.json();
}

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
  const res = await fetch(`${API_BASE}/datasets`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
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
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create dataset");
  return res.json();
}

export async function fetchExperiments(): Promise<Experiment[]> {
  const res = await fetch(`${API_BASE}/experiments`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch experiments");
  return res.json();
}

export async function runExperiment(payload: {
  name: string;
  dataset_id: string;
  provider_name: string;
  model_name?: string;
  api_key?: string;
}): Promise<Experiment> {
  const res = await fetch(`${API_BASE}/experiments`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to run experiment");
  return res.json();
}

export async function setBaseline(experimentId: string): Promise<Experiment> {
  const res = await fetch(`${API_BASE}/experiments/${experimentId}/set-baseline`, {
    method: "POST",
    headers: getAuthHeaders(),
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
    {
      headers: getAuthHeaders(),
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to check regression");
  }
  return res.json();
}

export interface ApiKeyMetadata {
  id: string;
  provider: string;
  key_preview: string;
  created_at: string;
}

export async function fetchApiKeys(): Promise<ApiKeyMetadata[]> {
  const res = await fetch(`${API_BASE}/auth/keys`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch API keys");
  return res.json();
}

export async function registerApiKey(
  provider: string,
  apiKey: string
): Promise<ApiKeyMetadata> {
  const res = await fetch(`${API_BASE}/auth/keys`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ provider, api_key: apiKey }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to register API key");
  }
  return res.json();
}
