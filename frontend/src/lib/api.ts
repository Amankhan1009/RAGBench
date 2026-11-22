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
  contexts?: string[];
  metadata?: Record<string, unknown>;
  item_metadata?: Record<string, unknown>;
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
  created_at?: string;
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

export interface SyntheticItemPreview {
  query: string;
  expected_output: string;
  contexts: string[];
  difficulty: "factual" | "reasoning" | "adversarial" | string;
  source_snippet?: string;
}

export interface SyntheticDatasetRequest {
  raw_text: string;
  num_samples?: number;
  difficulty?: "factual" | "reasoning" | "adversarial" | "mixed";
  provider_name?: string;
  model_name?: string;
  api_key?: string;
}

export interface SyntheticDatasetResponse {
  items: SyntheticItemPreview[];
  total_generated: number;
  provider_used: string;
  model_used: string;
  latency_ms: number;
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

export async function generateSyntheticDataset(
  payload: SyntheticDatasetRequest
): Promise<SyntheticDatasetResponse> {
  const res = await fetch(`${getApiBase()}/datasets/generate-synthetic`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to generate synthetic dataset");
  }
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
  webhook_url?: string;
  response_path?: string;
  contexts_path?: string;
  headers?: Record<string, string>;
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
    webhook_url?: string;
    response_path?: string;
    contexts_path?: string;
    headers?: Record<string, string>;
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

export interface DatasetIngestPayload {
  name: string;
  description?: string;
  version?: string;
  file_format: "csv" | "jsonl" | "json";
  content: string;
  column_mapping?: Record<string, string>;
}

export interface DatasetIngestResponse {
  dataset: Dataset;
  total_ingested: number;
  skipped_rows: number;
  warnings: string[];
}

export async function ingestDataset(
  payload: DatasetIngestPayload
): Promise<DatasetIngestResponse> {
  const res = await fetch(`${getApiBase()}/datasets/ingest`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to ingest dataset");
  }
  return res.json();
}

export function getExportUrl(
  experimentId: string,
  format: "markdown" | "csv" | "jsonl"
): string {
  return `${getApiBase()}/experiments/${experimentId}/export/${format}`;
}

export async function fetchExperimentMarkdown(experimentId: string): Promise<string> {
  const res = await fetch(`${getApiBase()}/experiments/${experimentId}/export/markdown`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch markdown export");
  }
  return res.text();
}

export async function downloadExperimentExport(
  experimentId: string,
  format: "csv" | "jsonl" | "markdown",
  filename?: string
): Promise<void> {
  const res = await fetch(`${getApiBase()}/experiments/${experimentId}/export/${format}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to download ${format} export`);
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const ext = format === "markdown" ? "md" : format;
  a.download = filename || `ragbench_experiment_${experimentId}.${ext}`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
}

export interface AgentStep {
  step_number: number;
  thought?: string;
  tool_call?: ToolCall;
  observation?: string;
}

export interface AgentTrajectory {
  goal: string;
  steps: AgentStep[];
  final_response?: string | null;
  success?: boolean;
}

export interface StepDiagnostic {
  step_number: number;
  tool_name?: string;
  is_loop_duplicate: boolean;
  is_redundant: boolean;
  is_expected_tool?: boolean | null;
}

export interface AgentTrajectoryReport {
  total_steps: number;
  tool_selection_accuracy: number;
  tool_precision: number;
  tool_recall: number;
  loop_detected: boolean;
  redundant_call_count: number;
  efficiency_score: number;
  passed: boolean;
  step_diagnostics: StepDiagnostic[];
  details: {
    tool_sequence?: string[];
    expected_tools?: string[];
    missing_expected_tools?: string[];
    loop_threshold?: number;
    max_optimal_steps?: number;
  };
}

export interface AgentScenarioPreset {
  id: string;
  name: string;
  description: string;
  category: "optimal" | "loop" | "security" | "inefficient" | string;
  trajectory: AgentTrajectory;
  expected_tools: string[];
  max_optimal_steps: number;
  loop_threshold: number;
}

export interface TrajectoryEvaluationRequest {
  trajectory: AgentTrajectory;
  expected_tools?: string[];
  max_optimal_steps?: number;
  loop_threshold?: number;
}

export async function fetchAgentScenarios(): Promise<AgentScenarioPreset[]> {
  const res = await fetch(`${getApiBase()}/agent/scenarios`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch agent trajectory scenarios");
  return res.json();
}

export async function evaluateAgentTrajectory(
  payload: TrajectoryEvaluationRequest
): Promise<AgentTrajectoryReport> {
  const res = await fetch(`${getApiBase()}/agent/evaluate-trajectory`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to evaluate agent trajectory");
  }
  return res.json();
}

// ==========================================
// AI Gateway & Semantic Cache (Milestone v3.1)
// ==========================================

export interface GatewayChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface GatewayCompletionRequest {
  model: string;
  messages: GatewayChatMessage[];
  temperature?: number;
  max_tokens?: number;
  provider?: string;
  fallback_providers?: string[];
  cache_enabled?: boolean;
  similarity_threshold?: number;
  api_key?: string;
  guardrails_enabled?: boolean;
  retrieved_contexts?: string[];
  pii_sanitization_enabled?: boolean;
  pii_restore_response?: boolean;
}

export interface GatewayMetadata {
  cached: boolean;
  cache_key?: string;
  latency_ms: number;
  provider_used: string;
  model_used: string;
  fallback_triggered: boolean;
  attempted_providers: string[];
  cost_usd: number;
  cost_saved_usd: number;
  guardrails_applied?: boolean;
  guardrails_blocked?: boolean;
  guardrails_violations?: string[];
  guardrails_latency_ms?: number;
  pii_sanitized?: boolean;
  pii_entities_masked_count?: number;
  pii_entities_detected?: string[];
  pii_latency_ms?: number;
}

export interface GatewayCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: {
    index: number;
    message: GatewayChatMessage;
    finish_reason: string;
  }[];
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  gateway: GatewayMetadata;
}

export interface CacheStats {
  workspace_id: string;
  total_requests: number;
  cache_hits: number;
  cache_misses: number;
  hit_rate: number;
  total_cost_saved_usd: number;
  total_latency_saved_ms: number;
  cached_entries_count: number;
}

export interface BudgetStatus {
  workspace_id: string;
  current_month_cost_usd: number;
  current_month_tokens: number;
  monthly_budget_usd?: number | null;
  monthly_token_quota?: number | null;
  cost_usage_percentage: number;
  token_usage_percentage: number;
  budget_exceeded: boolean;
}

export interface BudgetConfig {
  monthly_budget_usd?: number | null;
  monthly_token_quota?: number | null;
}

export async function fetchGatewayStats(): Promise<CacheStats> {
  const res = await fetch(`${getApiBase()}/gateway/stats`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch gateway cache statistics");
  return res.json();
}

export async function purgeGatewayCache(): Promise<{ status: string; message: string; cleared_count: number }> {
  const res = await fetch(`${getApiBase()}/gateway/cache/purge`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to purge gateway cache");
  return res.json();
}

export async function fetchGatewayBudget(): Promise<BudgetStatus> {
  const res = await fetch(`${getApiBase()}/gateway/budget`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch gateway budget status");
  return res.json();
}

export async function updateGatewayBudget(payload: BudgetConfig): Promise<BudgetStatus> {
  const res = await fetch(`${getApiBase()}/gateway/budget`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to update gateway budget");
  return res.json();
}

export async function callGatewayChatCompletions(
  payload: GatewayCompletionRequest
): Promise<GatewayCompletionResponse> {
  const res = await fetch(`${getApiBase()}/gateway/chat/completions`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || `Gateway request failed [${res.status}]`);
  }
  return res.json();
}

// ==========================================
// AI Security & Guardrails (Milestone v3.2)
// ==========================================

export interface GuardrailCheckResult {
  passed: boolean;
  action: "allow" | "block" | "rewrite" | "flag";
  violations: string[];
  confidence: number;
  sanitized_text?: string | null;
  refusal_response?: string | null;
  reason: string;
  execution_time_ms: number;
}

export interface TopicalRailConfig {
  domain_name: string;
  allowed_topics: string[];
  disallowed_topics: string[];
  refusal_message: string;
}

export interface WorkspaceGuardrailPolicy {
  workspace_id: string;
  input_rails_enabled: boolean;
  jailbreak_blocker_enabled: boolean;
  system_prompt_protection: boolean;
  topical_rails_enabled: boolean;
  output_rails_enabled: boolean;
  hallucination_threshold: number;
  topical_config: TopicalRailConfig;
}

export interface GuardrailPresetScenario {
  id: string;
  name: string;
  category: string;
  description: string;
  test_input: string;
  contexts?: string[] | null;
  expected_violation: string;
  expected_action: string;
}

export interface InputRailRequest {
  prompt: string;
  check_jailbreaks?: boolean;
  check_prompt_injection?: boolean;
  check_system_leak?: boolean;
}

export interface OutputRailRequest {
  response_text: string;
  retrieved_contexts: string[];
  hallucination_threshold?: number;
}

export async function fetchGuardrailPresets(): Promise<GuardrailPresetScenario[]> {
  const res = await fetch(`${getApiBase()}/guardrails/presets`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch guardrail preset scenarios");
  return res.json();
}

export async function fetchGuardrailPolicy(): Promise<WorkspaceGuardrailPolicy> {
  const res = await fetch(`${getApiBase()}/guardrails/policy`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch workspace guardrail policy");
  return res.json();
}

export async function updateGuardrailPolicy(
  payload: WorkspaceGuardrailPolicy
): Promise<WorkspaceGuardrailPolicy> {
  const res = await fetch(`${getApiBase()}/guardrails/policy`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to update workspace guardrail policy");
  return res.json();
}

export async function checkInputRail(
  payload: InputRailRequest
): Promise<GuardrailCheckResult> {
  const res = await fetch(`${getApiBase()}/guardrails/check-input`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to inspect prompt with input rails");
  }
  return res.json();
}

export async function checkOutputRail(
  payload: OutputRailRequest
): Promise<GuardrailCheckResult> {
  const res = await fetch(`${getApiBase()}/guardrails/check-output`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to verify output grounding with output rails");
  }
  return res.json();
}

// ==========================================
// Automated PII Masking & Data Sanitization (Milestone v3.3)
// ==========================================

export interface PIIEntityMatch {
  entity_type: string;
  text: string;
  start: number;
  end: number;
  replacement: string;
  confidence: number;
}

export interface PIISanitizerConfig {
  strategy?: "token" | "redact" | "hash";
  mask_email?: boolean;
  mask_phone?: boolean;
  mask_ssn?: boolean;
  mask_credit_card?: boolean;
  mask_api_key?: boolean;
  mask_ip_address?: boolean;
}

export interface PIISanitizationResult {
  original_text: string;
  sanitized_text: string;
  entities_found: PIIEntityMatch[];
  entities_count: Record<string, number>;
  token_map: Record<string, string>;
  latency_ms: number;
}

export interface PIIRestoreResult {
  restored_text: string;
  tokens_restored_count: number;
  latency_ms: number;
}

export interface PIILeakageCheckResult {
  leaked: boolean;
  leakage_score: number;
  leaked_entities: PIIEntityMatch[];
  total_context_pii_count: number;
  total_leaked_count: number;
  reason: string;
  latency_ms: number;
}

export interface PIIPresetScenario {
  id: string;
  title: string;
  description: string;
  sample_text: string;
  sample_context?: string | null;
  expected_entities: string[];
}

export async function maskPII(
  text: string,
  config?: PIISanitizerConfig
): Promise<PIISanitizationResult> {
  const res = await fetch(`${getApiBase()}/sanitizer/mask`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ text, config }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to sanitize text PII");
  }
  return res.json();
}

export async function unmaskPII(
  sanitizedText: string,
  tokenMap: Record<string, string>
): Promise<PIIRestoreResult> {
  const res = await fetch(`${getApiBase()}/sanitizer/unmask`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ sanitized_text: sanitizedText, token_map: tokenMap }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to restore sanitized PII tokens");
  }
  return res.json();
}

export async function detectPII(
  text: string,
  config?: PIISanitizerConfig
): Promise<PIIEntityMatch[]> {
  const res = await fetch(`${getApiBase()}/sanitizer/detect`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ text, config }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to detect PII entities");
  }
  return res.json();
}

export async function evaluatePIILeakage(
  contextChunks: string[],
  generatedText: string
): Promise<PIILeakageCheckResult> {
  const res = await fetch(`${getApiBase()}/sanitizer/evaluate-leakage`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ context_chunks: contextChunks, generated_text: generatedText }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to audit PII leakage");
  }
  return res.json();
}

export async function fetchPIIPresets(): Promise<PIIPresetScenario[]> {
  const res = await fetch(`${getApiBase()}/sanitizer/presets`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch PII presets");
  return res.json();
}

// ==========================================
// AI Red-Teaming & Adversarial Benchmark (Milestone v3.4)
// ==========================================

export interface AttackTestCase {
  id: string;
  category: "direct_injection" | "jailbreak" | "indirect_injection" | "system_extraction" | "topical_evasion" | "pii_leakage";
  severity: "low" | "medium" | "high" | "critical";
  name: string;
  description: string;
  prompt: string;
  context_passage?: string | null;
  breach_indicator_patterns: string[];
  refusal_indicator_patterns: string[];
  mitigation_recommendation: string;
}

export interface AttackExecutionResult {
  test_case: AttackTestCase;
  status: "defended" | "breached" | "error";
  model_output: string;
  latency_ms: number;
  cost_usd: number;
  guardrails_intercepted: boolean;
  breach_reason?: string | null;
  mitigation_recommendation: string;
}

export interface RedTeamBenchmarkRequest {
  provider: string;
  model: string;
  api_key?: string;
  categories?: string[];
  guardrails_enabled?: boolean;
  pii_sanitization_enabled?: boolean;
}

export interface RedTeamBenchmarkReport {
  benchmark_id: string;
  target_provider: string;
  target_model: string;
  total_attacks: number;
  defended_attacks: number;
  breached_attacks: number;
  security_posture_score: number;
  risk_grade: string;
  defense_rate_by_category: Record<string, number>;
  critical_vulnerabilities_count: number;
  guardrails_intercepted_count: number;
  attack_results: AttackExecutionResult[];
  executive_summary: string;
  created_at: string;
  latency_ms: number;
}

export async function fetchAttackCatalog(
  category?: string
): Promise<AttackTestCase[]> {
  const url = category
    ? `${getApiBase()}/redteam/attacks?category=${encodeURIComponent(category)}`
    : `${getApiBase()}/redteam/attacks`;
  const res = await fetch(url, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch attack catalog");
  return res.json();
}

export async function runRedTeamBenchmark(
  payload: RedTeamBenchmarkRequest
): Promise<RedTeamBenchmarkReport> {
  const res = await fetch(`${getApiBase()}/redteam/run`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to run AI red-team benchmark");
  }
  return res.json();
}

export async function fetchRedTeamReports(): Promise<RedTeamBenchmarkReport[]> {
  const res = await fetch(`${getApiBase()}/redteam/reports`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch red-team reports");
  return res.json();
}

export async function fetchRedTeamReportDetails(
  id: string
): Promise<RedTeamBenchmarkReport> {
  const res = await fetch(`${getApiBase()}/redteam/reports/${encodeURIComponent(id)}`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch red-team report details");
  return res.json();
}

// ==========================================
// Phase 26: Enterprise RBAC & Tamper-Evident Audit Logging (v3.5)
// ==========================================

export interface WorkspaceMember {
  id: string;
  email: string;
  name: string | null;
  role: "admin" | "evaluator" | "viewer" | string;
  workspace_id: string;
  created_at: string | null;
}

export interface AuditLogItem {
  id: string;
  workspace_id: string;
  user_id: string | null;
  user_email: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, any> | null;
  ip_address: string | null;
  created_at: string;
  prev_hash: string | null;
  record_hash: string;
}

export interface AuditVerificationReport {
  total_records: number;
  verified_records: number;
  is_valid: boolean;
  tampered_records: Array<{
    record_id: string;
    index: number;
    action: string;
    prev_hash_matches: boolean;
    hash_matches: boolean;
    expected_hash: string;
    recorded_hash: string;
  }>;
  chain_status: "SECURE" | "COMPROMISED" | string;
  message: string;
  verified_at: string;
}

export interface AuditStats {
  total_events: number;
  events_by_action: Record<string, number>;
  events_by_resource: Record<string, number>;
  unique_users: number;
  latest_event_at: string | null;
  chain_status: string;
}

export interface AuditLogListResponse {
  items: AuditLogItem[];
  total: number;
  page: number;
  limit: number;
}

export async function fetchWorkspaceMembers(): Promise<WorkspaceMember[]> {
  const res = await fetch(`${getApiBase()}/workspaces/members`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch workspace members");
  }
  return res.json();
}

export async function addWorkspaceMember(payload: {
  email: string;
  name?: string;
  role: string;
  password?: string;
}): Promise<WorkspaceMember> {
  const res = await fetch(`${getApiBase()}/workspaces/members`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to add workspace member");
  }
  return res.json();
}

export async function updateWorkspaceMemberRole(
  userId: string,
  role: string
): Promise<WorkspaceMember> {
  const res = await fetch(`${getApiBase()}/workspaces/members/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    headers: getAuthHeaders(),
    body: JSON.stringify({ role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update member role");
  }
  return res.json();
}

export async function removeWorkspaceMember(userId: string): Promise<void> {
  const res = await fetch(`${getApiBase()}/workspaces/members/${encodeURIComponent(userId)}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to remove workspace member");
  }
}

export async function fetchAuditLogs(params?: {
  action?: string;
  resource_type?: string;
  user_email?: string;
  page?: number;
  limit?: number;
}): Promise<AuditLogListResponse> {
  const query = new URLSearchParams();
  if (params?.action && params.action !== "ALL") query.append("action", params.action);
  if (params?.resource_type) query.append("resource_type", params.resource_type);
  if (params?.user_email) query.append("user_email", params.user_email);
  if (params?.page) query.append("page", params.page.toString());
  if (params?.limit) query.append("limit", params.limit.toString());

  const queryString = query.toString() ? `?${query.toString()}` : "";
  const res = await fetch(`${getApiBase()}/audit/logs${queryString}`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch audit logs");
  }
  return res.json();
}

export async function verifyAuditIntegrity(): Promise<AuditVerificationReport> {
  const res = await fetch(`${getApiBase()}/audit/verify`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to run cryptographic audit verification");
  }
  return res.json();
}

export async function fetchAuditStats(): Promise<AuditStats> {
  const res = await fetch(`${getApiBase()}/audit/stats`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch audit statistics");
  }
  return res.json();
}


