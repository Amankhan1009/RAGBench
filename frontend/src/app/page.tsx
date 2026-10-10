"use client";

import { useEffect, useState } from "react";
import {
  fetchHealth,
  fetchDatasets,
  createDataset,
  fetchExperiments,
  runExperiment,
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
} from "../lib/api";

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
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Core application state
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [activeTab, setActiveTab] = useState<"experiments" | "datasets" | "regression" | "api_keys">("experiments");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

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

  const showToast = (message: string, type: "loading" | "success" | "error") => {
    setStatusToast({ message, type });
    if (type !== "loading") {
      setTimeout(() => setStatusToast(null), 3000);
    }
  };

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
        }
      } catch {
        setCurrentUser(null);
      } finally {
        setAuthChecking(false);
      }
    }
    init();
  }, []);

  const loadAll = async () => {
    try {
      setErrorMsg(null);
      const h = await fetchHealth();
      setHealth(h);
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
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to connect to backend");
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
      await loadAll();
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : "Authentication failed");
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

  const handleRunExperiment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDataset) {
      alert("Please select or create a dataset first.");
      return;
    }
    setLoading(true);
    showToast("Running evaluation & scoring metrics...", "loading");
    try {
      if (runApiKey.trim() && saveRunKeyToVault && provider !== "mock") {
        await registerApiKey(provider, runApiKey.trim()).catch(() => {});
        const updatedKeys = await fetchApiKeys().catch(() => []);
        setApiKeys(updatedKeys);
      }
      await runExperiment({
        name: expName || `Benchmark Run ${experiments.length + 1}`,
        dataset_id: selectedDataset,
        provider_name: provider,
        model_name: model,
        api_key: runApiKey.trim() || undefined,
      });
      setExpName("");
      setRunApiKey("");
      await loadAll();
      showToast("Evaluation run completed successfully!", "success");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Run failed", "error");
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
            <div className="p-3 bg-rose-950/60 border border-rose-800 text-rose-200 rounded-xl text-xs">
              {authError}
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
              <label className="block text-slate-400 text-xs mb-1">Password</label>
              <input
                type="password"
                placeholder="••••••••"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                required
                minLength={6}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 outline-none focus:border-indigo-500 text-slate-200"
              />
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
                <button
                  onClick={() => {
                    setCiModal((prev) => ({ ...prev, isOpen: false }));
                    setActiveTab("regression");
                  }}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition"
                >
                  View in CI Tab →
                </button>
              )}
            </div>
          </div>
        </div>
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
        <div className="flex items-center gap-3">
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
        <div className="max-w-7xl mx-auto mt-4 p-4 bg-rose-950/60 border border-rose-800 text-rose-200 rounded-lg text-sm">
          Backend notice: {errorMsg}.
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto mt-8 flex border-b border-slate-800 gap-8">
        {(["experiments", "regression", "datasets", "api_keys"] as const).map((tab) => (
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
            {tab === "regression" && "Regression & CI Gates"}
            {tab === "datasets" && "Datasets"}
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
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 rounded-lg transition disabled:opacity-50 mt-2"
                >
                  {loading && <Spinner />}
                  {loading ? "Running Evaluation..." : "Execute Experiment"}
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
        )}

        {/* TAB 2: REGRESSION & CI GATES */}
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
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl h-fit">
              <h2 className="text-lg font-semibold mb-4 text-slate-200">Create Dataset</h2>
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
              <h2 className="text-lg font-semibold mb-4 text-slate-200">Existing Datasets ({datasets.length})</h2>
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

