export const DEFAULT_PROD_API = "https://ragbench-backend.onrender.com/api/v1";
export const DEFAULT_LOCAL_API = "http://localhost:8000/api/v1";

export function cleanApiBase(url?: string): string {
  if (!url) {
    if (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
      return DEFAULT_PROD_API;
    }
    return DEFAULT_LOCAL_API;
  }
  let clean = url.trim().replace(/\/+$/, "");
  if (!clean.endsWith("/api/v1")) {
    clean = `${clean}/api/v1`;
  }
  return clean;
}

export function getApiBase(): string {
  if (typeof window !== "undefined") {
    const isRemote = window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1";
    const custom = localStorage.getItem("ragbench_api_url");
    if (custom) {
      if (isRemote && (custom.includes("localhost") || custom.includes("127.0.0.1"))) {
        localStorage.removeItem("ragbench_api_url");
      } else {
        return cleanApiBase(custom);
      }
    }

    if (isRemote) {
      const envUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!envUrl || envUrl.includes("localhost") || envUrl.includes("127.0.0.1")) {
        return DEFAULT_PROD_API;
      }
    }
  }
  return cleanApiBase(process.env.NEXT_PUBLIC_API_URL);
}

export function setCustomApiUrl(url: string) {
  if (typeof window !== "undefined") {
    if (!url.trim()) {
      localStorage.removeItem("ragbench_api_url");
    } else {
      localStorage.setItem("ragbench_api_url", cleanApiBase(url));
    }
  }
}


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
  const res = await fetch(`${getApiBase()}/auth/register`, {
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
  const res = await fetch(`${getApiBase()}/auth/login`, {
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
  const res = await fetch(`${getApiBase()}/auth/me`, {
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

export interface ParetoPoint {
  experiment_id: string;
  name: string;
  model_name: string;
  provider_name: string;
  composite_score: number;
  latency_ms: number;
  cost_usd: number;
  total_tokens: number;
  metrics: Record<string, number>;
  is_pareto_optimal: boolean;
  is_baseline: boolean;
  created_at: string;
}

export interface RadarDimension {
  dimension: string;
  candidate_score: number;
  baseline_score: number;
}

export interface TrendPoint {
  experiment_id: string;
  name: string;
  timestamp: string;
  composite_score: number;
  latency_ms: number;
  is_baseline: boolean;
}

export interface ParetoAnalyticsResponse {
  total_experiments: number;
  points: ParetoPoint[];
  pareto_frontier: ParetoPoint[];
  radar_comparison?: RadarDimension[] | null;
  candidate_name?: string | null;
  baseline_name?: string | null;
  trends: TrendPoint[];
}

export interface StreamStartEvent {
  experiment_id: string;
  experiment_name: string;
  total_samples: number;
  provider_name: string;
  model_name: string;
  dataset_name?: string;
}

export interface StreamSampleEvent {
  sample_index: number;
  total_samples: number;
  query: string;
  response_snippet: string;
  latency_ms: number;
  total_tokens: number;
  cost_usd: number;
  metrics: Record<string, number>;
  passed: boolean;
  progress_pct: number;
}

export interface StreamCompleteEvent {
  experiment_id: string;
  experiment_name: string;
  total_samples: number;
  successful_samples: number;
  failed_samples: number;
  composite_score: number;
  avg_latency_ms: number;
  avg_tokens: number;
  total_cost_usd: number;
  status: string;
}

export interface StreamErrorEvent {
  error_message: string;
  sample_index?: number;
  experiment_id?: string;
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${getApiBase()}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error("Backend offline");
  return res.json();
}

export async function pingBackend(timeoutMs = 12000): Promise<boolean> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${getApiBase()}/health`, {
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return res.ok;
  } catch {
    clearTimeout(timeoutId);
    return false;
  }
}

export async function wakeUpBackend(
  onProgress?: (attempt: number, maxAttempts: number) => void
): Promise<boolean> {
  const maxAttempts = 25; // 25 attempts * 2.5s = ~65s max
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    if (onProgress) onProgress(attempt, maxAttempts);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);
    try {
      const res = await fetch(`${getApiBase()}/health`, {
        cache: "no-store",
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (res.ok) {
        return true;
      }
    } catch {
      clearTimeout(timeoutId);
      // In flight or instance still spinning up
    }
    await new Promise((resolve) => setTimeout(resolve, 2500));
  }
  return false;
}

export async function fetchDatasets(): Promise<Dataset[]> {
  const res = await fetch(`${getApiBase()}/datasets`, {
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
  const res = await fetch(`${getApiBase()}/datasets`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to create dataset");
  return res.json();
}

export async function fetchExperiments(): Promise<Experiment[]> {
  const res = await fetch(`${getApiBase()}/experiments`, {
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
  const res = await fetch(`${getApiBase()}/experiments`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to run experiment");
  return res.json();
}

export async function streamExperiment(
  payload: {
    name: string;
    dataset_id: string;
    provider_name: string;
    model_name?: string;
    api_key?: string;
  },
  callbacks: {
    onStart?: (data: StreamStartEvent) => void;
    onSample?: (data: StreamSampleEvent) => void;
    onComplete?: (data: StreamCompleteEvent) => void;
    onError?: (error: string) => void;
  },
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${getApiBase()}/experiments/stream`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
    signal,
  });

  if (!res.ok) {
    let errDetail = "Failed to start streaming evaluation";
    try {
      const errJson = await res.json();
      errDetail = errJson.detail || errDetail;
    } catch {
      errDetail = await res.text();
    }
    throw new Error(errDetail);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("ReadableStream not supported by browser");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";

    for (const block of lines) {
      if (!block.trim()) continue;
      const eventMatch = block.match(/^event:\s*(\w+)/m);
      const dataMatch = block.match(/^data:\s*(.+)$/m);

      if (eventMatch && dataMatch) {
        const eventType = eventMatch[1];
        try {
          const parsed = JSON.parse(dataMatch[1]);
          if (eventType === "started" && callbacks.onStart) {
            callbacks.onStart(parsed);
          } else if (eventType === "sample_completed" && callbacks.onSample) {
            callbacks.onSample(parsed);
          } else if (eventType === "completed" && callbacks.onComplete) {
            callbacks.onComplete(parsed);
          } else if (eventType === "error" && callbacks.onError) {
            callbacks.onError(parsed.error_message || "Unknown streaming error");
          }
        } catch (e) {
          console.error("Error parsing SSE event data:", e, block);
        }
      }
    }
  }
}

export async function setBaseline(experimentId: string): Promise<Experiment> {
  const res = await fetch(`${getApiBase()}/experiments/${experimentId}/set-baseline`, {
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
    `${getApiBase()}/experiments/${experimentId}/check-regression?tolerance=${tolerance}`,
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

export async function fetchParetoAnalytics(candidateId?: string): Promise<ParetoAnalyticsResponse> {
  let url = `${getApiBase()}/experiments/analytics/pareto`;
  if (candidateId) {
    url += `?candidate_id=${encodeURIComponent(candidateId)}`;
  }
  const res = await fetch(url, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch Pareto analytics");
  return res.json();
}

export interface ApiKeyMetadata {
  id: string;
  provider: string;
  key_preview: string;
  created_at: string;
}

export async function fetchApiKeys(): Promise<ApiKeyMetadata[]> {
  const res = await fetch(`${getApiBase()}/auth/keys`, {
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
  const res = await fetch(`${getApiBase()}/auth/keys`, {
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
