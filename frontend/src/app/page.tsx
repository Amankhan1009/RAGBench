"use client";

import { useEffect, useState, useCallback } from "react";
import {
  fetchHealth,
  pingBackend,
  wakeUpBackend,
  getApiBase,
  setCustomApiUrl,
  fetchDatasets,
  createDataset,
  fetchExperiments,
  runExperiment,
  streamExperiment,
  setBaseline,
  checkRegression,
  loginUser,
  registerUser,
  fetchCurrentUser,
  removeToken,
  fetchApiKeys,
  registerApiKey,
  ApiKeyMetadata,
  User,
  HealthStatus,
  Dataset,
  Experiment,
  RegressionReport,
  fetchParetoAnalytics,
  ParetoPoint,
  ParetoAnalyticsResponse,
  StreamStartEvent,
  StreamSampleEvent,
  StreamCompleteEvent,
} from "../lib/api";
import VisualAnalytics from "../components/VisualAnalytics";
import LiveEvaluationStream from "../components/LiveEvaluationStream";
import SyntheticDatasetGenerator from "../components/SyntheticDatasetGenerator";
import DatasetFileIngestion from "../components/DatasetFileIngestion";
import ExecutiveReportModal from "../components/ExecutiveReportModal";
import AgentTrajectoryInspector from "../components/AgentTrajectoryInspector";

function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`animate-spin text-current ${className}`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      width="14"
      height="14"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v8H4z"
      />
    </svg>
  );
}

export default function Dashboard() {
  // Authentication state
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authChecking, setAuthChecking] = useState(true);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authName, setAuthName] = useState("");
  const [showAuthPassword, setShowAuthPassword] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Core application state
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "sleeping" | "waking">("checking");
  const [wakeProgress, setWakeProgress] = useState<{ attempt: number; maxAttempts: number } | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [activeTab, setActiveTab] = useState<"experiments" | "analytics" | "regression" | "datasets" | "agent" | "api_keys">("experiments");
  const [datasetMode, setDatasetMode] = useState<"synthetic" | "ingest" | "manual">("synthetic");
  const [exportModalExp, setExportModalExp] = useState<Experiment | null>(null);
  const [analyticsData, setAnalyticsData] = useState<ParetoAnalyticsResponse | null>(null);
  const [selectedCandidateForAnalytics, setSelectedCandidateForAnalytics] = useState<string>("");
  const [selectedParetoPoint, setSelectedParetoPoint] = useState<ParetoPoint | null>(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Live Streaming (Phase 18 SSE) State
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamStart, setStreamStart] = useState<StreamStartEvent | null>(null);
  const [streamSamples, setStreamSamples] = useState<StreamSampleEvent[]>([]);
  const [streamComplete, setStreamComplete] = useState<StreamCompleteEvent | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);

  // BYOK API Keys State
  const [apiKeys, setApiKeys] = useState<ApiKeyMetadata[]>([]);
  const [keyProvider, setKeyProvider] = useState("groq");
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [savingKey, setSavingKey] = useState(false);
  const [showKeySecret, setShowKeySecret] = useState(false);

  // Per-action visual loading states
  const [checkingCI, setCheckingCI] = useState<string | null>(null);
  const [settingBaseline, setSettingBaseline] = useState<string | null>(null);

  // Global toast notification state
  const [statusToast, setStatusToast] = useState<{
    message: string;
    type: "loading" | "success" | "error";
  } | null>(null);

  const showToast = useCallback((message: string, type: "loading" | "success" | "error") => {
    setStatusToast({ message, type });
    if (type !== "loading") {
      setTimeout(() => setStatusToast(null), 3000);
    }
  }, []);

  // CI Evaluation Modal State
  const [ciModal, setCiModal] = useState<{
    isOpen: boolean;
    expId: string;
    expName: string;
    stage: number;
    report: RegressionReport | null;
    error: string | null;
  }>({
    isOpen: false,
    expId: "",
    expName: "",
    stage: 1,
    report: null,
    error: null,
  });

  // Forms
  const [expName, setExpName] = useState("");
  const [selectedDataset, setSelectedDataset] = useState("");
  const [provider, setProvider] = useState("groq");
  const [model, setModel] = useState("openai/gpt-oss-120b");
  const [runApiKey, setRunApiKey] = useState("");
  const [saveRunKeyToVault, setSaveRunKeyToVault] = useState(true);

  const [dsName, setDsName] = useState("");
  const [dsQuery, setDsQuery] = useState("");
  const [dsOutput, setDsOutput] = useState("");

  const [selectedCandidateForCI, setSelectedCandidateForCI] = useState("");
  const [regressionReport, setRegressionReport] = useState<{
    expId: string;
    expName: string;
    timestamp: string;
    report: RegressionReport;
  } | null>(null);

  // Initial Auth & Data Load
  useEffect(() => {
    document.title = "RAGBench";
    async function init() {
      try {
        const u = await fetchCurrentUser();
        setCurrentUser(u);
        if (u) {
          await loadAll();
          setBackendStatus("online");
        } else {
          const isOnline = await pingBackend();
          setBackendStatus(isOnline ? "online" : "sleeping");
        }
      } catch {
        setCurrentUser(null);
        const isOnline = await pingBackend();
        setBackendStatus(isOnline ? "online" : "sleeping");
      } finally {
        setAuthChecking(false);
      }
    }
    init();
  }, []);

  const handleWakeUpBackend = async () => {
    setBackendStatus("waking");
    setWakeProgress({ attempt: 1, maxAttempts: 25 });
    setAuthError(null);
    showToast("Waking up Render backend service...", "loading");
    const success = await wakeUpBackend((attempt, max) => {
      setWakeProgress({ attempt, maxAttempts: max });
    });
    if (success) {
      setBackendStatus("online");
      setWakeProgress(null);
      setAuthError(null);
      showToast("Backend is online and ready!", "success");
      if (currentUser) {
        await loadAll();
      }
    } else {
      setBackendStatus("sleeping");
      setWakeProgress(null);
      showToast("Backend wake-up timed out. Please try again.", "error");
    }
  };

  const handleCheckBackend = async () => {
    setBackendStatus("checking");
    const isOnline = await pingBackend();
    setBackendStatus(isOnline ? "online" : "sleeping");
    if (isOnline) {
      showToast("Backend is online and responsive!", "success");
      setAuthError(null);
    } else {
      showToast("Backend is sleeping or unreachable.", "error");
    }
  };

  const loadAll = async () => {
    try {
      setErrorMsg(null);
      const h = await fetchHealth();
      setHealth(h);
      setBackendStatus("online");
      const ds = await fetchDatasets();
      setDatasets(ds);
      if (ds.length > 0 && !selectedDataset) setSelectedDataset(ds[0].id);
      const exps = await fetchExperiments();
      setExperiments(exps);
      if (exps.length > 0 && !selectedCandidateForCI) {
        const candidate = exps.find((e) => !e.is_baseline);
        if (candidate) setSelectedCandidateForCI(candidate.id);
      }
      const keys = await fetchApiKeys().catch(() => []);
      setApiKeys(keys);

      const analytics = await fetchParetoAnalytics().catch(() => null);
      if (analytics) {
        setAnalyticsData(analytics);
        if (analytics.points.length > 0) {
          setSelectedParetoPoint((prev) => {
            if (!prev) return analytics.pareto_frontier[0] || analytics.points[0];
            const found = analytics.points.find((p) => p.experiment_id === prev.experiment_id);
            return found || analytics.pareto_frontier[0] || analytics.points[0];
          });
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to backend";
      setErrorMsg(msg);
      if (
        msg.toLowerCase().includes("failed to fetch") ||
        msg.toLowerCase().includes("offline") ||
        msg.toLowerCase().includes("network")
      ) {
        setBackendStatus("sleeping");
      }
    }
  };

  const handleCandidateAnalyticsChange = async (candId: string) => {
    setSelectedCandidateForAnalytics(candId);
    setLoadingAnalytics(true);
    try {
      const data = await fetchParetoAnalytics(candId || undefined);
      setAnalyticsData(data);
      if (data.points.length > 0) {
        setSelectedParetoPoint((prev) => {
          if (!prev) return data.pareto_frontier[0] || data.points[0];
          const found = data.points.find((p) => p.experiment_id === prev.experiment_id);
          return found || data.pareto_frontier[0] || data.points[0];
        });
      }
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to load analytics", "error");
    } finally {
      setLoadingAnalytics(false);
    }
  };

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      let resp;
      if (authMode === "register") {
        resp = await registerUser(authEmail, authPassword, authName || undefined);
        showToast("Account created successfully!", "success");
      } else {
        resp = await loginUser(authEmail, authPassword);
        showToast("Welcome back!", "success");
      }
      setCurrentUser(resp.user);
      setBackendStatus("online");
      await loadAll();
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Authentication failed";
      if (
        errMsg.toLowerCase().includes("failed to fetch") ||
        errMsg.toLowerCase().includes("networkerror") ||
        errMsg.toLowerCase().includes("network error") ||
        errMsg.toLowerCase().includes("load failed")
      ) {
        const isOnline = await pingBackend();
        if (!isOnline) {
          setBackendStatus("sleeping");
          setAuthError(
            "Failed to fetch: Backend instance is sleeping (Render Free Tier). Click 'Wake Up Backend' below to start the server."
          );
        } else {
          setBackendStatus("online");
          setAuthError(
            `Unable to complete ${authMode === "register" ? "registration" : "login"}: ${errMsg}. If you already created an account, please switch to 'Sign In'.`
          );
        }
      } else {
        setAuthError(errMsg);
      }
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    removeToken();
    setCurrentUser(null);
    setDatasets([]);
    setExperiments([]);
    setApiKeys([]);
    setRegressionReport(null);
    showToast("Logged out successfully", "success");
  };

  const handleRegisterApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKeyInput.trim()) return;
    setSavingKey(true);
    showToast("Encrypting & securely saving API key...", "loading");
    try {
      await registerApiKey(keyProvider, apiKeyInput.trim());
      setApiKeyInput("");
      const updatedKeys = await fetchApiKeys();
      setApiKeys(updatedKeys);
      showToast(`AES-256 encrypted ${keyProvider.toUpperCase()} key stored successfully!`, "success");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to store API key", "error");
    } finally {
      setSavingKey(false);
    }
  };

  const handleDismissStream = () => {
    setIsStreaming(false);
    setStreamStart(null);
    setStreamSamples([]);
    setStreamComplete(null);
    setStreamError(null);
  };

  const handleRunExperiment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDataset) {
      alert("Please select or create a dataset first.");
      return;
    }
    setLoading(true);
    setIsStreaming(true);
    setStreamStart(null);
    setStreamSamples([]);
    setStreamComplete(null);
    setStreamError(null);
    showToast("Launching live evaluation stream...", "loading");

    try {
      if (runApiKey.trim() && saveRunKeyToVault && provider !== "mock") {
        await registerApiKey(provider, runApiKey.trim()).catch(() => {});
        const updatedKeys = await fetchApiKeys().catch(() => []);
        setApiKeys(updatedKeys);
      }

      await streamExperiment(
        {
          name: expName || `Benchmark Run ${experiments.length + 1}`,
          dataset_id: selectedDataset,
          provider_name: provider,
          model_name: model,
          api_key: runApiKey.trim() || undefined,
        },
        {
          onStart: (data) => {
            setStreamStart(data);
          },
          onSample: (data) => {
            setStreamSamples((prev) => [...prev, data]);
          },
          onComplete: async (data) => {
            setStreamComplete(data);
            setIsStreaming(false);
            setExpName("");
            setRunApiKey("");
            await loadAll();
            showToast(
              `Evaluation completed! Composite Score: ${data.composite_score.toFixed(4)}`,
              "success"
            );
          },
          onError: (errMsg) => {
            setStreamError(errMsg);
            setIsStreaming(false);
            showToast(errMsg, "error");
          },
        }
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Run failed";
      setStreamError(msg);
      setIsStreaming(false);
      showToast(msg, "error");
    } finally {
      setLoading(false);
    }
  };

  const handleSetBaseline = async (id: string, name: string) => {
    setSettingBaseline(id);
    showToast(`Setting "${name}" as baseline...`, "loading");
    try {
      await Promise.all([
        setBaseline(id),
        new Promise((resolve) => setTimeout(resolve, 600)),
      ]);
      await loadAll();
      showToast(`"${name}" is now the active baseline!`, "success");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to set baseline", "error");
    } finally {
      setSettingBaseline(null);
    }
  };

  const handleCheckRegression = async (id: string, name: string) => {
    setCheckingCI(id);
    setCiModal({
      isOpen: true,
      expId: id,
      expName: name,
      stage: 1,
      report: null,
      error: null,
    });

    try {
      await new Promise((r) => setTimeout(r, 450));
      setCiModal((prev) => ({ ...prev, stage: 2 }));

      const [rep] = await Promise.all([
        checkRegression(id),
        new Promise((r) => setTimeout(r, 550)),
      ]);

      setCiModal((prev) => ({
        ...prev,
        stage: 3,
        report: rep,
      }));

      setRegressionReport({
        expId: id,
        expName: name,
        timestamp: new Date().toLocaleTimeString(),
        report: rep,
      });
      showToast(`CI evaluation finished for "${name}"!`, "success");
    } catch (err: unknown) {
      setCiModal((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : "CI Regression Check Failed",
      }));
      showToast(err instanceof Error ? err.message : "Regression check failed", "error");
    } finally {
      setCheckingCI(null);
    }
  };

  const handleCreateDataset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dsName || !dsQuery) return;
    setLoading(true);
    showToast(`Creating dataset "${dsName}"...`, "loading");
    try {
      await createDataset({
        name: dsName,
        items: [{ query: dsQuery, expected_output: dsOutput }],
      });
      setDsName("");
      setDsQuery("");
      setDsOutput("");
      await loadAll();
      showToast(`Dataset "${dsName}" created!`, "success");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Dataset creation failed", "error");
    } finally {
      setLoading(false);
    }
  };

  // ── LOADING INITIAL AUTH ───────────────────────────────────────────────────
  if (authChecking) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <div className="flex items-center gap-3 text-sm">
          <Spinner className="w-5 h-5 text-indigo-400" />
          <span>Initializing secure session...</span>
        </div>
      </div>
    );
  }

  // ── LOGIN / REGISTER VIEW (UNAUTHENTICATED) ────────────────────────────────
  if (!currentUser) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
        {statusToast && (
          <div
            className={`fixed top-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl border text-sm backdrop-blur-md transition-all duration-300 ${
              statusToast.type === "loading"
                ? "bg-slate-900 border-indigo-500 text-indigo-200"
                : statusToast.type === "success"
                ? "bg-emerald-950 border-emerald-500 text-emerald-200"
                : "bg-rose-950 border-rose-500 text-rose-200"
            }`}
          >
            {statusToast.type === "loading" && <Spinner />}
            {statusToast.type === "success" && <span>✓</span>}
            {statusToast.type === "error" && <span>✕</span>}
            <span className="font-medium">{statusToast.message}</span>
          </div>
        )}

        <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-8 space-y-6">
          <div className="text-center space-y-2">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
              RAGBench Platform
            </h1>
            <p className="text-sm text-slate-400">
              Sign in to access your multi-tenant evaluations &amp; datasets
            </p>
          </div>

          {/* Backend Health & Wake-Up Status Widget */}
          <div className="rounded-xl p-3 border transition-all duration-300 text-xs flex flex-col gap-2.5 bg-slate-950/70 border-slate-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-slate-400 font-medium">Backend:</span>
                {backendStatus === "online" && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-semibold text-emerald-400 bg-emerald-950/80 border border-emerald-800/80">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Online
                  </span>
                )}
                {backendStatus === "sleeping" && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-semibold text-amber-400 bg-amber-950/80 border border-amber-800/80">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    Asleep (Render Free Tier)
                  </span>
                )}
                {backendStatus === "checking" && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-medium text-slate-300 bg-slate-800">
                    <Spinner className="w-3 h-3 text-indigo-400" />
                    Checking...
                  </span>
                )}
                {backendStatus === "waking" && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-semibold text-indigo-300 bg-indigo-950/80 border border-indigo-700">
                    <Spinner className="w-3 h-3 text-indigo-400" />
                    Waking Up...
                  </span>
                )}
              </div>

              {backendStatus === "online" && (
                <button
                  type="button"
                  onClick={handleCheckBackend}
                  className="text-[11px] text-slate-400 hover:text-slate-200 hover:underline flex items-center gap-1 transition"
                  title="Check connection"
                >
                  ↻ Check
                </button>
              )}
            </div>

            {/* Sleeping Banner */}
            {backendStatus === "sleeping" && (
              <div className="pt-2 border-t border-slate-800/60 flex flex-col gap-2">
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Render spins down inactive instances. Click below to boot the container (~30–50s boot time).
                </p>
                <button
                  type="button"
                  onClick={handleWakeUpBackend}
                  className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-gradient-to-r from-amber-500 via-indigo-600 to-indigo-700 hover:from-amber-400 hover:to-indigo-500 text-white font-semibold text-xs shadow-lg shadow-indigo-950 transition hover:scale-[1.01] active:scale-[0.99]"
                >
                  <span>⚡ Wake Up Backend</span>
                </button>
              </div>
            )}

            {/* Waking Progress Bar */}
            {backendStatus === "waking" && (
              <div className="pt-2 border-t border-slate-800/60 flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-[11px] text-indigo-300 font-medium">
                  <span>Waking up container...</span>
                  <span>
                    Attempt {wakeProgress?.attempt ?? 1} / {wakeProgress?.maxAttempts ?? 25}
                  </span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-500 h-full transition-all duration-300 rounded-full"
                    style={{
                      width: `${Math.min(
                        100,
                        (((wakeProgress?.attempt ?? 1) / (wakeProgress?.maxAttempts ?? 25)) * 100)
                      )}%`,
                    }}
                  />
                </div>
                <span className="text-[10px] text-slate-500">
                  Render cold start in progress (~30-50s). The page will auto-activate when ready.
                </span>
              </div>
            )}

            {/* Active API URL info & config */}
            <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500">
              <span className="truncate max-w-[280px]" title={typeof window !== "undefined" ? getApiBase() : ""}>
                API: {typeof window !== "undefined" ? getApiBase() : "https://ragbench-backend.onrender.com/api/v1"}
              </span>
              <button
                type="button"
                onClick={() => {
                  const current = getApiBase();
                  const updated = prompt("Enter Backend API Base URL:", current);
                  if (updated !== null) {
                    setCustomApiUrl(updated);
                    handleCheckBackend();
                  }
                }}
                className="text-indigo-400 hover:text-indigo-300 underline ml-2 whitespace-nowrap"
              >
                Config
              </button>
            </div>
          </div>

          <div className="flex border border-slate-800 rounded-xl bg-slate-950 p-1">
            <button
              onClick={() => {
                setAuthMode("login");
                setAuthError(null);
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition ${
                authMode === "login"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => {
                setAuthMode("register");
                setAuthError(null);
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition ${
                authMode === "register"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Create Account
            </button>
          </div>

          {authError && (
            <div className="p-3.5 bg-rose-950/70 border border-rose-800 text-rose-200 rounded-xl text-xs space-y-2">
              <div className="flex items-start gap-2">
                <span className="text-rose-400 text-sm mt-0.5">⚠️</span>
                <div className="flex-1 space-y-2">
                  <p className="font-semibold text-rose-100">{authError}</p>
                  {(authError.toLowerCase().includes("fetch") ||
                    authError.toLowerCase().includes("render") ||
                    backendStatus === "sleeping") &&
                    backendStatus !== "waking" && (
                      <button
                        type="button"
                        onClick={handleWakeUpBackend}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition shadow-md"
                      >
                        <span>⚡ Wake Up Backend Now</span>
                      </button>
                    )}
                </div>
              </div>
            </div>
          )}

          <form onSubmit={handleAuthSubmit} className="space-y-4 text-sm">
            {authMode === "register" && (
              <div>
                <label className="block text-slate-400 text-xs mb-1">Your Name</label>
                <input
                  type="text"
                  placeholder="e.g. Aman Khan"
                  value={authName}
                  onChange={(e) => setAuthName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 outline-none focus:border-indigo-500 text-slate-200"
                />
              </div>
            )}
            <div>
              <label className="block text-slate-400 text-xs mb-1">Email Address</label>
              <input
                type="email"
                placeholder="developer@company.com"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 outline-none focus:border-indigo-500 text-slate-200"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-slate-400 text-xs">Password</label>
                <button
                  type="button"
                  onClick={() => setShowAuthPassword(!showAuthPassword)}
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-medium transition"
                >
                  {showAuthPassword ? "Hide" : "Show"}
                </button>
              </div>
              <div className="relative">
                <input
                  type={showAuthPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 pr-10 outline-none focus:border-indigo-500 text-slate-200 font-mono text-sm"
                />
                <button
                  type="button"
                  onClick={() => setShowAuthPassword(!showAuthPassword)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 p-1 rounded transition"
                  title={showAuthPassword ? "Hide password" : "Show password"}
                >
                  {showAuthPassword ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={authLoading}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2.5 rounded-xl transition disabled:opacity-50 mt-2 shadow-lg shadow-indigo-600/30"
            >
              {authLoading && <Spinner />}
              {authLoading
                ? "Authenticating..."
                : authMode === "login"
                ? "Sign In"
                : "Create Account"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // ── MAIN AUTHENTICATED DASHBOARD ───────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      {statusToast && (
        <div
          className={`fixed top-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl border text-sm backdrop-blur-md transition-all duration-300 ${
            statusToast.type === "loading"
              ? "bg-slate-900 border-indigo-500 text-indigo-200"
              : statusToast.type === "success"
              ? "bg-emerald-950 border-emerald-500 text-emerald-200"
              : "bg-rose-950 border-rose-500 text-rose-200"
          }`}
        >
          {statusToast.type === "loading" && <Spinner />}
          {statusToast.type === "success" && <span>✓</span>}
          {statusToast.type === "error" && <span>✕</span>}
          <span className="font-medium">{statusToast.message}</span>
        </div>
      )}

      {/* CI REGRESSION GATE VISUAL EVALUATION MODAL */}
      {ciModal.isOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
              <div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-indigo-500 animate-pulse" />
                  <h3 className="text-lg font-bold text-slate-100">
                    CI Regression Gate Evaluation
                  </h3>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Testing candidate: <strong className="text-slate-200">{ciModal.expName}</strong>
                </p>
              </div>
              <button
                onClick={() => setCiModal((prev) => ({ ...prev, isOpen: false }))}
                className="text-slate-400 hover:text-slate-200 p-2 rounded-lg hover:bg-slate-800 transition"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-6">
              <div className="space-y-3 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Evaluation Pipeline
                </div>

                <div className="flex items-center gap-3 text-sm">
                  {ciModal.stage > 1 ? (
                    <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold">
                      ✓
                    </span>
                  ) : (
                    <Spinner className="w-5 h-5 text-indigo-400" />
                  )}
                  <span className={ciModal.stage >= 1 ? "text-slate-200" : "text-slate-500"}>
                    Step 1: Extract candidate quality metrics (faithfulness, relevancy, precision)
                  </span>
                </div>

                <div className="flex items-center gap-3 text-sm">
                  {ciModal.stage > 2 ? (
                    <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold">
                      ✓
                    </span>
                  ) : ciModal.stage === 2 ? (
                    <Spinner className="w-5 h-5 text-indigo-400" />
                  ) : (
                    <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-500 flex items-center justify-center text-xs">
                      2
                    </span>
                  )}
                  <span className={ciModal.stage >= 2 ? "text-slate-200" : "text-slate-500"}>
                    Step 2: Compare candidate vs active baseline within ±2.0% tolerance budget
                  </span>
                </div>

                <div className="flex items-center gap-3 text-sm">
                  {ciModal.stage === 3 ? (
                    <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold">
                      ✓
                    </span>
                  ) : (
                    <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-500 flex items-center justify-center text-xs">
                      3
                    </span>
                  )}
                  <span className={ciModal.stage === 3 ? "text-slate-200" : "text-slate-500"}>
                    Step 3: Verification &amp; automated gate decision verdict
                  </span>
                </div>
              </div>

              {ciModal.error && (
                <div className="p-4 bg-rose-950/60 border border-rose-800 text-rose-200 rounded-xl text-sm">
                  <div className="font-semibold mb-1">Evaluation Error</div>
                  <div>{ciModal.error}</div>
                </div>
              )}

              {ciModal.report && (
                <div className="space-y-4">
                  <div
                    className={`p-4 rounded-xl border flex items-center justify-between ${
                      ciModal.report.has_regression
                        ? "bg-rose-950/40 border-rose-800 text-rose-200"
                        : "bg-emerald-950/40 border-emerald-800 text-emerald-200"
                    }`}
                  >
                    <div>
                      <div className="text-base font-bold">
                        {ciModal.report.has_regression ? "❌ Regression Detected" : "✅ CI Gate Passed"}
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">
                        {ciModal.report.has_regression
                          ? `Regressed metrics: ${ciModal.report.regressed_metrics.join(", ")}`
                          : "All metrics meet or exceed the active production baseline."}
                      </div>
                    </div>
                    <span
                      className={`text-xs px-2.5 py-1 rounded-full font-semibold uppercase ${
                        ciModal.report.has_regression
                          ? "bg-rose-500 text-white"
                          : "bg-emerald-500 text-white"
                      }`}
                    >
                      {ciModal.report.has_regression ? "Blocked" : "Approved"}
                    </span>
                  </div>

                  <div className="overflow-x-auto rounded-xl border border-slate-800">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="p-3">Metric</th>
                          <th className="p-3">Candidate</th>
                          <th className="p-3">Baseline</th>
                          <th className="p-3">Delta</th>
                          <th className="p-3">Verdict</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800">
                        {Object.entries(ciModal.report.details || {}).map(([metric, d]) => (
                          <tr key={metric}>
                            <td className="p-3 font-medium text-slate-200">{metric}</td>
                            <td className="p-3 text-slate-300">{d.candidate_score.toFixed(4)}</td>
                            <td className="p-3 text-slate-400">{d.baseline_score.toFixed(4)}</td>
                            <td
                              className={`p-3 font-semibold ${
                                d.delta < 0 ? "text-rose-400" : "text-emerald-400"
                              }`}
                            >
                              {d.delta >= 0 ? `+${d.delta.toFixed(4)}` : d.delta.toFixed(4)}
                            </td>
                            <td className="p-3">
                              <span
                                className={`px-2 py-0.5 rounded border text-[11px] ${
                                  d.regressed
                                    ? "bg-rose-950 border-rose-800 text-rose-300"
                                    : "bg-emerald-950 border-emerald-800 text-emerald-300"
                                }`}
                              >
                                {d.regressed ? "Regressed" : "Pass"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-slate-800 bg-slate-950/50 flex justify-end gap-3">
              <button
                onClick={() => setCiModal((prev) => ({ ...prev, isOpen: false }))}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition"
              >
                Close
              </button>
              {ciModal.stage === 3 && (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      const exp = experiments.find((e) => e.id === ciModal.expId);
                      if (exp) {
                        setCiModal((prev) => ({ ...prev, isOpen: false }));
                        setExportModalExp(exp);
                      }
                    }}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium transition flex items-center gap-1.5"
                  >
                    <span>📊</span>
                    <span>Export PR Report</span>
                  </button>
                  <button
                    onClick={() => {
                      setCiModal((prev) => ({ ...prev, isOpen: false }));
                      setActiveTab("regression");
                    }}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition"
                  >
                    View in CI Tab →
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* EXECUTIVE REPORT EXPORT MODAL */}
      {exportModalExp && (
        <ExecutiveReportModal
          experiment={exportModalExp}
          onClose={() => setExportModalExp(null)}
          showToast={showToast}
        />
      )}

      {/* Header */}
      <header className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between pb-8 border-b border-slate-800 gap-4">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
            RAGBench Platform
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Production-Grade LLM, RAG &amp; Agent Evaluation Platform
          </p>
        </div>

        {/* User Info & Actions */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Backend Status Pill */}
          <div className="bg-slate-900 border border-slate-800 px-3 py-2 rounded-xl text-xs flex items-center gap-2">
            {backendStatus === "online" ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-emerald-400 font-medium">Backend Online</span>
                <button
                  onClick={handleCheckBackend}
                  className="text-slate-500 hover:text-slate-300 ml-1"
                  title="Check connectivity"
                >
                  ↻
                </button>
              </>
            ) : backendStatus === "waking" ? (
              <>
                <Spinner className="w-3 h-3 text-indigo-400" />
                <span className="text-indigo-300 font-medium">
                  Waking... ({wakeProgress?.attempt}/25)
                </span>
              </>
            ) : backendStatus === "checking" ? (
              <>
                <Spinner className="w-3 h-3 text-slate-400" />
                <span className="text-slate-400">Checking backend...</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-amber-400" />
                <span className="text-amber-300 font-medium">Backend Sleeping</span>
                <button
                  onClick={handleWakeUpBackend}
                  className="ml-1 text-[11px] px-2 py-0.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition"
                >
                  ⚡ Wake Up
                </button>
              </>
            )}
          </div>

          <div className="bg-slate-900 border border-slate-800 px-3.5 py-2 rounded-xl text-xs flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="font-medium text-slate-200">{currentUser.email}</span>
            <span className="text-slate-600">|</span>
            <span className="text-indigo-400 font-medium">{currentUser.workspace_name}</span>
          </div>

          <button
            onClick={handleLogout}
            className="px-3 py-2 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 rounded-xl text-xs transition"
          >
            Logout
          </button>
        </div>
      </header>

      {errorMsg && (
        <div className="max-w-7xl mx-auto mt-4 p-4 bg-rose-950/60 border border-rose-800 text-rose-200 rounded-lg text-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <span className="font-semibold">Backend Notice:</span> {errorMsg}
          </div>
          <div className="flex items-center gap-2">
            {backendStatus !== "online" && (
              <button
                onClick={handleWakeUpBackend}
                disabled={backendStatus === "waking"}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition disabled:opacity-50"
              >
                {backendStatus === "waking" ? "Waking Up..." : "⚡ Wake Up Backend"}
              </button>
            )}
            <button
              onClick={loadAll}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition"
            >
              ↻ Retry
            </button>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto mt-8 flex flex-wrap border-b border-slate-800 gap-8">
        {(["experiments", "analytics", "regression", "datasets", "agent", "api_keys"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-3 text-sm font-medium transition capitalize flex items-center gap-2 ${
              activeTab === tab
                ? "text-blue-400 border-b-2 border-blue-400"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab === "experiments" && "Experiments & Runs"}
            {tab === "analytics" && (
              <>
                <span>Analytics &amp; Pareto Frontier</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30">
                  v2.0
                </span>
              </>
            )}
            {tab === "regression" && "Regression & CI Gates"}
            {tab === "datasets" && (
              <>
                <span>Datasets</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30">
                  AI &amp; Ingestion
                </span>
              </>
            )}
            {tab === "agent" && (
              <>
                <span>Agent Trajectories</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-purple-500/20 text-purple-300 font-semibold border border-purple-500/30">
                  v2.6
                </span>
              </>
            )}
            {tab === "api_keys" && (
              <>
                <span>API Keys (BYOK)</span>
                {apiKeys.length > 0 && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold border border-emerald-500/30">
                    {apiKeys.length} active
                  </span>
                )}
              </>
            )}
          </button>
        ))}
      </div>

      <main className="max-w-7xl mx-auto mt-8">
        {/* TAB 1: EXPERIMENTS */}
        {activeTab === "experiments" && (
          <div className="space-y-8">
            {(isStreaming || streamComplete || streamError || streamSamples.length > 0) && (
              <LiveEvaluationStream
                startData={streamStart}
                samples={streamSamples}
                completeData={streamComplete}
                error={streamError}
                isStreaming={isStreaming}
                onDismiss={handleDismissStream}
                onViewAnalytics={() => setActiveTab("analytics")}
              />
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl h-fit">
              <h2 className="text-lg font-semibold mb-4 text-slate-200">Run New Evaluation</h2>
              <form onSubmit={handleRunExperiment} className="space-y-4 text-sm">
                <div>
                  <label className="block text-slate-400 mb-1">Experiment Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Groq GPT-OSS Evaluation"
                    value={expName}
                    onChange={(e) => setExpName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 focus:border-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Dataset</label>
                  <select
                    value={selectedDataset}
                    onChange={(e) => setSelectedDataset(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 focus:border-blue-500 outline-none"
                  >
                    {datasets.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} (v{d.version})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Provider</label>
                  <select
                    value={provider}
                    onChange={(e) => {
                      setProvider(e.target.value);
                      if (e.target.value === "groq") setModel("openai/gpt-oss-120b");
                      else if (e.target.value === "openai") setModel("gpt-4o-mini");
                      else if (e.target.value === "anthropic") setModel("claude-3-5-sonnet-20241022");
                      else if (e.target.value === "google") setModel("gemini-1.5-flash");
                      else setModel("mock-model");
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 focus:border-blue-500 outline-none"
                  >
                    <option value="mock">Mock Provider (Deterministic)</option>
                    <option value="groq">Groq (openai/gpt-oss-120b)</option>
                    <option value="openai">OpenAI (GPT-4o Mini)</option>
                    <option value="anthropic">Anthropic (Claude 3.5 Sonnet)</option>
                    <option value="google">Google Gemini (Gemini 1.5 Flash)</option>
                  </select>
                </div>

                {/* DIRECT BYOK API KEY INPUT IN EXPERIMENT RUN CARD */}
                {provider !== "mock" && (
                  <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="block text-xs font-semibold text-slate-300">
                        🔑 {provider.toUpperCase()} API Key (BYOK)
                      </label>
                      <button
                        type="button"
                        onClick={() => setActiveTab("api_keys")}
                        className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium"
                      >
                        Manage Vault ({apiKeys.filter((k) => k.provider.toLowerCase() === provider.toLowerCase()).length}) →
                      </button>
                    </div>

                    <input
                      type="password"
                      placeholder={
                        apiKeys.some((k) => k.provider.toLowerCase() === provider.toLowerCase())
                          ? "•••••••••••• (Using saved vault key)"
                          : provider === "groq"
                          ? "Enter Groq key (gsk_...)"
                          : provider === "openai"
                          ? "Enter OpenAI key (sk-...)"
                          : provider === "anthropic"
                          ? "Enter Anthropic key (sk-ant-...)"
                          : "Enter Gemini key (AIza...)"
                      }
                      value={runApiKey}
                      onChange={(e) => setRunApiKey(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 focus:border-indigo-500 outline-none font-mono text-xs text-slate-200"
                    />

                    <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                      {apiKeys.some((k) => k.provider.toLowerCase() === provider.toLowerCase()) ? (
                        <span className="text-emerald-400 font-medium">
                          ✓ Key configured in vault (leave blank to reuse)
                        </span>
                      ) : (
                        <span className="text-amber-400 font-medium">
                          ⚠ Key required to execute live model
                        </span>
                      )}

                      {runApiKey && (
                        <label className="flex items-center gap-1.5 cursor-pointer text-slate-300 select-none">
                          <input
                            type="checkbox"
                            checked={saveRunKeyToVault}
                            onChange={(e) => setSaveRunKeyToVault(e.target.checked)}
                            className="rounded bg-slate-900 border-slate-700 text-indigo-600"
                          />
                          <span>Save to vault</span>
                        </label>
                      )}
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-slate-400 mb-1">Model Identifier</label>
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 focus:border-blue-500 outline-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || isStreaming}
                  className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 rounded-lg transition disabled:opacity-50 mt-2"
                >
                  {(loading || isStreaming) && <Spinner />}
                  {isStreaming
                    ? "Streaming Evaluation..."
                    : loading
                    ? "Executing..."
                    : "Execute Experiment"}
                </button>
              </form>
            </div>

            <div className="lg:col-span-2 bg-slate-900 border border-slate-800 p-6 rounded-xl">
              <h2 className="text-lg font-semibold mb-4 text-slate-200">
                Evaluation Runs ({experiments.length})
              </h2>
              {experiments.length === 0 ? (
                <div className="text-slate-500 text-center py-12">No experiments executed yet.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        <th className="pb-3">Experiment</th>
                        <th className="pb-3">Provider / Model</th>
                        <th className="pb-3">Metrics</th>
                        <th className="pb-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {experiments.map((exp) => {
                        const isChecking = checkingCI === exp.id;
                        const isSettingBase = settingBaseline === exp.id;
                        return (
                          <tr
                            key={exp.id}
                            className={`transition-colors ${
                              isChecking
                                ? "bg-indigo-950/40 border-l-2 border-indigo-500"
                                : "hover:bg-slate-950/40"
                            }`}
                          >
                            <td className="py-4 font-medium text-slate-200">
                              <div className="flex items-center gap-2">
                                <span>{exp.name}</span>
                                {exp.is_baseline && (
                                  <span className="bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[10px] px-2 py-0.5 rounded-full font-semibold">
                                    Baseline
                                  </span>
                                )}
                              </div>
                              <span className="text-xs text-slate-500">{exp.id.slice(0, 8)}...</span>
                            </td>
                            <td className="py-4 text-slate-300">
                              <div>{exp.provider_name}</div>
                              <span className="text-xs text-slate-500">{exp.model_name || "default"}</span>
                            </td>
                            <td className="py-4">
                              <div className="flex flex-wrap gap-2 text-xs">
                                {Object.entries(exp.summary_metrics || {}).map(([k, v]) => (
                                  <span key={k} className="bg-slate-950 border border-slate-800 px-2 py-1 rounded">
                                    {k}: <strong className="text-slate-200">{Number(v).toFixed(2)}</strong>
                                  </span>
                                ))}
                              </div>
                            </td>
                            <td className="py-4 text-right space-x-2">
                              {!exp.is_baseline && (
                                <button
                                  onClick={() => handleSetBaseline(exp.id, exp.name)}
                                  disabled={isSettingBase || isChecking}
                                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs rounded-lg transition disabled:opacity-50 text-slate-200 font-medium min-w-[110px] justify-center"
                                >
                                  {isSettingBase ? (
                                    <>
                                      <Spinner />
                                      <span>Setting...</span>
                                    </>
                                  ) : (
                                    "Set Baseline"
                                  )}
                                </button>
                              )}
                              <button
                                onClick={() => handleCheckRegression(exp.id, exp.name)}
                                disabled={isChecking || isSettingBase}
                                className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg transition font-medium min-w-[115px] justify-center text-white ${
                                  isChecking
                                    ? "bg-indigo-700 ring-2 ring-indigo-400 animate-pulse"
                                    : "bg-indigo-600 hover:bg-indigo-500 shadow-sm shadow-indigo-500/20"
                                } disabled:opacity-60`}
                              >
                                {isChecking ? (
                                  <>
                                    <Spinner />
                                    <span>Checking CI...</span>
                                  </>
                                ) : (
                                  "Check CI"
                                )}
                              </button>
                              <button
                                type="button"
                                onClick={() => setExportModalExp(exp)}
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs rounded-lg transition text-slate-300 hover:text-white font-medium border border-slate-700"
                                title="Export Executive Summary & Execution Logs"
                              >
                                <span>📊</span>
                                <span>Export</span>
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

        {/* TAB 2: VISUAL ANALYTICS & PARETO FRONTIER (v2.0) */}
        {activeTab === "analytics" && (
          <VisualAnalytics
            analyticsData={analyticsData}
            loading={loadingAnalytics}
            selectedCandidateId={selectedCandidateForAnalytics}
            onCandidateChange={handleCandidateAnalyticsChange}
            selectedPoint={selectedParetoPoint}
            onSelectPoint={(p) => setSelectedParetoPoint(p)}
            onRefresh={() => handleCandidateAnalyticsChange(selectedCandidateForAnalytics)}
            onNavigateToExperiments={() => setActiveTab("experiments")}
            experiments={experiments}
          />
        )}

        {/* TAB 3: REGRESSION & CI GATES */}
        {activeTab === "regression" && (
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl space-y-6">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-200">CI/CD Automated Regression Gates</h2>
                <p className="text-sm text-slate-400">
                  Compare candidate experiments against the active baseline within a ±2% tolerance budget.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <select
                  value={selectedCandidateForCI}
                  onChange={(e) => setSelectedCandidateForCI(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 outline-none"
                >
                  <option value="">Select Candidate...</option>
                  {experiments
                    .filter((e) => !e.is_baseline)
                    .map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.name}
                      </option>
                    ))}
                </select>
                <button
                  onClick={() => {
                    if (!selectedCandidateForCI) return;
                    const c = experiments.find((e) => e.id === selectedCandidateForCI);
                    if (c) handleCheckRegression(c.id, c.name);
                  }}
                  disabled={!selectedCandidateForCI || checkingCI !== null}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition disabled:opacity-50"
                >
                  Run CI Gate
                </button>
              </div>
            </div>

            {regressionReport ? (
              <div className="space-y-6">
                <div
                  className={`p-4 rounded-xl border flex items-center justify-between ${
                    regressionReport.report.has_regression
                      ? "bg-rose-950/40 border-rose-800 text-rose-200"
                      : "bg-emerald-950/40 border-emerald-800 text-emerald-200"
                  }`}
                >
                  <div>
                    <div className="text-base font-bold">
                      {regressionReport.report.has_regression
                        ? "❌ Regression Gate Triggered: Quality Regressed"
                        : "✅ Regression Gate Passed: Candidate Safe for Production"}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      Evaluated candidate &quot;{regressionReport.expName}&quot; against baseline at {regressionReport.timestamp}.
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => {
                        const exp = experiments.find((e) => e.name === regressionReport.expName || e.id === selectedCandidateForCI);
                        if (exp) setExportModalExp(exp);
                      }}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium transition flex items-center gap-1.5"
                    >
                      <span>📊</span>
                      <span>Export PR Report</span>
                    </button>
                    <span
                      className={`text-xs px-3 py-1 rounded-full font-bold uppercase ${
                        regressionReport.report.has_regression
                          ? "bg-rose-500 text-white"
                          : "bg-emerald-500 text-white"
                      }`}
                    >
                      {regressionReport.report.has_regression ? "Blocked" : "Approved"}
                    </span>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        <th className="pb-3">Metric</th>
                        <th className="pb-3">Candidate</th>
                        <th className="pb-3">Baseline</th>
                        <th className="pb-3">Delta</th>
                        <th className="pb-3">Verdict</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {Object.entries(regressionReport.report.details || {}).map(([metric, d]) => (
                        <tr key={metric}>
                          <td className="py-3 font-medium text-slate-200">{metric}</td>
                          <td className="py-3 text-slate-300">{d.candidate_score.toFixed(4)}</td>
                          <td className="py-3 text-slate-400">{d.baseline_score.toFixed(4)}</td>
                          <td
                            className={`py-3 font-semibold ${
                              d.delta < 0 ? "text-rose-400" : "text-emerald-400"
                            }`}
                          >
                            {d.delta >= 0 ? `+${d.delta.toFixed(4)}` : d.delta.toFixed(4)}
                          </td>
                          <td className="py-3">
                            <span
                              className={`px-2 py-0.5 rounded border text-xs ${
                                d.regressed
                                  ? "bg-rose-950 border-rose-800 text-rose-300"
                                  : "bg-emerald-950 border-emerald-800 text-emerald-300"
                              }`}
                            >
                              {d.regressed ? "Regressed" : "Pass"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500">
                Select an experiment from the <strong>Experiments</strong> tab and click <strong>Check CI</strong> to inspect regression status.
              </div>
            )}
          </div>
        )}

        {/* TAB 3: DATASETS */}
        {activeTab === "datasets" && (
          <div className="space-y-8 animate-in fade-in duration-300">
            {/* Mode Switch Header */}
            <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-2xl">
              <div>
                <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <span>Dataset Management</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30">
                    v2.5 Ingestion &amp; Synthesis
                  </span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Import CSV/JSONL files, synthesize test suites with BYOK LLMs, or assemble test cases manually.
                </p>
              </div>

              <div className="flex items-center bg-slate-950 border border-slate-800 p-1 rounded-xl text-xs gap-1">
                <button
                  type="button"
                  onClick={() => setDatasetMode("synthetic")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
                    datasetMode === "synthetic"
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <span>✨</span>
                  <span>AI Synthetic</span>
                </button>
                <button
                  type="button"
                  onClick={() => setDatasetMode("ingest")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
                    datasetMode === "ingest"
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <span>📁</span>
                  <span>Bulk Ingestion</span>
                </button>
                <button
                  type="button"
                  onClick={() => setDatasetMode("manual")}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
                    datasetMode === "manual"
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <span>📝</span>
                  <span>Manual Entry</span>
                </button>
              </div>
            </div>

            {/* Mode Content */}
            {datasetMode === "synthetic" && (
              <SyntheticDatasetGenerator
                apiKeys={apiKeys}
                onDatasetCreated={async (datasetId) => {
                  await loadAll();
                  setSelectedDataset(datasetId);
                }}
                showToast={showToast}
              />
            )}

            {datasetMode === "ingest" && (
              <DatasetFileIngestion
                onDatasetCreated={async (datasetId) => {
                  await loadAll();
                  setSelectedDataset(datasetId);
                }}
                showToast={showToast}
              />
            )}

            {datasetMode === "manual" && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl h-fit">
                  <h2 className="text-lg font-semibold mb-4 text-slate-200">Create Dataset Manually</h2>
                  <form onSubmit={handleCreateDataset} className="space-y-4 text-sm">
                    <div>
                      <label className="block text-slate-400 mb-1">Dataset Name</label>
                      <input
                        type="text"
                        placeholder="e.g. Production QA Suite"
                        value={dsName}
                        onChange={(e) => setDsName(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 outline-none focus:border-blue-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-slate-400 mb-1">Sample Query</label>
                      <textarea
                        rows={2}
                        placeholder="User question or prompt"
                        value={dsQuery}
                        onChange={(e) => setDsQuery(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 outline-none focus:border-blue-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-slate-400 mb-1">Expected Output (Optional)</label>
                      <textarea
                        rows={2}
                        placeholder="Ground truth answer"
                        value={dsOutput}
                        onChange={(e) => setDsOutput(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 outline-none focus:border-blue-500"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 rounded-lg transition disabled:opacity-50"
                    >
                      {loading && <Spinner />}
                      {loading ? "Creating..." : "Create Dataset"}
                    </button>
                  </form>
                </div>

                <div className="lg:col-span-2 bg-slate-900 border border-slate-800 p-6 rounded-xl">
                  <h2 className="text-lg font-semibold mb-4 text-slate-200">Workspace Datasets ({datasets.length})</h2>
                  {datasets.length === 0 ? (
                    <div className="text-slate-500 text-center py-12">No datasets created yet.</div>
                  ) : (
                    <div className="space-y-4">
                      {datasets.map((d) => (
                        <div key={d.id} className="p-4 bg-slate-950 border border-slate-800 rounded-lg flex justify-between items-center">
                          <div>
                            <div className="font-medium text-slate-200">{d.name}</div>
                            <div className="text-xs text-slate-500">
                              ID: {d.id} | Version: v{d.version} | Items: {d.items?.length || 0}
                            </div>
                          </div>
                          <span className="text-xs bg-slate-800 text-slate-300 px-2 py-1 rounded">
                            Ready
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* In Synthetic and Ingest modes, also display the Active Datasets list at the bottom for quick overview & selection */}
            {datasetMode !== "manual" && (
              <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-base font-semibold text-slate-200">
                      Active Workspace Datasets ({datasets.length})
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      All datasets ready for live multi-model benchmarking experiments.
                    </p>
                  </div>
                  <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 font-mono">
                    {datasets.reduce((acc, d) => acc + (d.items?.length || 0), 0)} total evaluation samples
                  </span>
                </div>
                {datasets.length === 0 ? (
                  <div className="text-slate-500 text-center py-8 text-sm">
                    No benchmark datasets exist yet. Use the generator above or switch to manual entry!
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {datasets.map((d) => (
                      <div
                        key={d.id}
                        className={`p-4 bg-slate-950 border rounded-xl transition ${
                          selectedDataset === d.id
                            ? "border-indigo-500 ring-1 ring-indigo-500/50"
                            : "border-slate-800 hover:border-slate-700"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-medium text-slate-200 text-sm truncate" title={d.name}>
                            {d.name}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-indigo-300 font-mono shrink-0">
                            v{d.version}
                          </span>
                        </div>
                        {d.description && (
                          <p className="text-xs text-slate-400 line-clamp-2 mt-1">
                            {d.description}
                          </p>
                        )}
                        <div className="flex items-center justify-between text-xs text-slate-500 mt-3 pt-2 border-t border-slate-800/80">
                          <span>{d.items?.length || 0} sample(s)</span>
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedDataset(d.id);
                              showToast(`Selected "${d.name}" for experiments`, "success");
                            }}
                            className={`text-xs px-2 py-0.5 rounded transition ${
                              selectedDataset === d.id
                                ? "bg-indigo-600/30 text-indigo-300 font-semibold"
                                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                            }`}
                          >
                            {selectedDataset === d.id ? "Selected ✓" : "Select"}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* TAB: AGENT BENCHMARK & TRAJECTORIES (v2.6) */}
        {activeTab === "agent" && (
          <AgentTrajectoryInspector showToast={showToast} />
        )}

        {/* TAB 4: API KEYS (BYOK) */}
        {activeTab === "api_keys" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Form */}
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl h-fit">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-base">🔐</span>
                <h2 className="text-lg font-semibold text-slate-200">Store API Key (BYOK)</h2>
              </div>
              <p className="text-xs text-slate-400 mb-5">
                Bring Your Own Key: Store provider credentials securely to run live benchmarks.
              </p>

              <form onSubmit={handleRegisterApiKey} className="space-y-4 text-sm">
                <div>
                  <label className="block text-slate-400 mb-1">Provider</label>
                  <select
                    value={keyProvider}
                    onChange={(e) => setKeyProvider(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 outline-none focus:border-indigo-500 text-slate-200"
                  >
                    <option value="groq">Groq (Llama 3, Mixtral - Ultra Fast)</option>
                    <option value="openai">OpenAI (GPT-4o, GPT-4o-mini)</option>
                    <option value="anthropic">Anthropic (Claude 3.5 Sonnet)</option>
                    <option value="google">Google Gemini (Gemini 1.5 Pro/Flash)</option>
                  </select>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-slate-400">Secret API Key</label>
                    <button
                      type="button"
                      onClick={() => setShowKeySecret(!showKeySecret)}
                      className="text-xs text-indigo-400 hover:text-indigo-300 transition"
                    >
                      {showKeySecret ? "Hide" : "Show"}
                    </button>
                  </div>
                  <input
                    type={showKeySecret ? "text" : "password"}
                    placeholder={
                      keyProvider === "groq"
                        ? "gsk_..."
                        : keyProvider === "openai"
                        ? "sk-..."
                        : keyProvider === "anthropic"
                        ? "sk-ant-..."
                        : "AIzaSy..."
                    }
                    value={apiKeyInput}
                    onChange={(e) => setApiKeyInput(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 outline-none focus:border-indigo-500 font-mono text-xs text-slate-200"
                    required
                  />
                </div>

                <div className="p-3 bg-slate-950/80 border border-slate-800/80 rounded-lg space-y-1.5 text-xs text-slate-400">
                  <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                    <span>🛡️</span>
                    <span>AES-256 Fernet Encryption</span>
                  </div>
                  <p className="leading-relaxed">
                    Keys are encrypted at the application boundary prior to database storage. Plaintext secrets are never logged or exposed via API.
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={savingKey || !apiKeyInput.trim()}
                  className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2 rounded-lg transition disabled:opacity-50"
                >
                  {savingKey && <Spinner className="w-4 h-4" />}
                  {savingKey ? "Encrypting & Saving..." : "Save Key to Vault"}
                </button>
              </form>
            </div>

            {/* Configured Keys Vault */}
            <div className="lg:col-span-2 space-y-6">
              <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-200">
                      Configured Vault Keys ({apiKeys.length})
                    </h2>
                    <p className="text-xs text-slate-400">
                      Keys registered in your workspace (<strong className="text-slate-300">{currentUser.workspace_name}</strong>)
                    </p>
                  </div>
                  <button
                    onClick={async () => {
                      const keys = await fetchApiKeys().catch(() => []);
                      setApiKeys(keys);
                      showToast("Key vault refreshed", "success");
                    }}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs transition"
                  >
                    Refresh
                  </button>
                </div>

                {apiKeys.length === 0 ? (
                  <div className="p-12 text-center border border-dashed border-slate-800 rounded-xl space-y-2">
                    <div className="text-2xl">🔑</div>
                    <div className="text-slate-300 font-medium text-sm">No API Keys in Vault</div>
                    <div className="text-slate-500 text-xs max-w-sm mx-auto">
                      Add your Groq, OpenAI, Anthropic, or Google API key using the form on the left to start running evaluations against live models.
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {apiKeys.map((k) => (
                      <div
                        key={k.id}
                        className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex flex-col justify-between hover:border-slate-700 transition"
                      >
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-semibold text-sm uppercase tracking-wider text-indigo-400">
                              {k.provider}
                            </span>
                            <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 font-medium flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              Active
                            </span>
                          </div>
                          <div className="font-mono text-xs text-slate-400 bg-slate-900 px-2.5 py-1.5 rounded border border-slate-800/80 mb-2">
                            {k.key_preview || "••••••••••••••••"}
                          </div>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-900">
                          <span>Encrypted AES-256</span>
                          <span>{new Date(k.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Explainer / Documentation card */}
              <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-xl space-y-2 text-xs text-slate-400">
                <div className="font-semibold text-slate-300 flex items-center gap-2">
                  <span>💡</span>
                  <span>How BYOK Works in RAGBench</span>
                </div>
                <ul className="list-disc list-inside space-y-1 text-slate-400">
                  <li>Keys are stored per workspace and encrypted using AES-256 Fernet.</li>
                  <li>When you select a provider in the <strong>Experiments</strong> tab, RAGBench automatically resolves and decrypts the registered key during execution.</li>
                  <li>You never need to re-type or expose keys in team dashboards or CI scripts.</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

