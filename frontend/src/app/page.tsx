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
  HealthStatus,
  Dataset,
  Experiment,
  RegressionReport,
} from "@/lib/api";

export default function Dashboard() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [activeTab, setActiveTab] = useState<"experiments" | "datasets" | "regression">("experiments");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // New Experiment Form
  const [expName, setExpName] = useState("");
  const [selectedDataset, setSelectedDataset] = useState("");
  const [provider, setProvider] = useState("mock");
  const [model, setModel] = useState("mock-model");

  // New Dataset Form
  const [dsName, setDsName] = useState("");
  const [dsQuery, setDsQuery] = useState("");
  const [dsOutput, setDsOutput] = useState("");

  // Regression report state
  const [regressionReport, setRegressionReport] = useState<{
    expId: string;
    report: RegressionReport;
  } | null>(null);

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
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to connect to backend");
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleRunExperiment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDataset) {
      alert("Please select or create a dataset first.");
      return;
    }
    setLoading(true);
    try {
      await runExperiment({
        name: expName || `Benchmark Run ${experiments.length + 1}`,
        dataset_id: selectedDataset,
        provider_name: provider,
        model_name: model,
      });
      setExpName("");
      await loadAll();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Run failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSetBaseline = async (id: string) => {
    try {
      await setBaseline(id);
      await loadAll();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to set baseline");
    }
  };

  const handleCheckRegression = async (id: string) => {
    try {
      const rep = await checkRegression(id);
      setRegressionReport({ expId: id, report: rep });
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Regression check failed");
    }
  };

  const handleCreateDataset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dsName || !dsQuery) return;
    setLoading(true);
    try {
      await createDataset({
        name: dsName,
        items: [{ query: dsQuery, expected_output: dsOutput }],
      });
      setDsName("");
      setDsQuery("");
      setDsOutput("");
      await loadAll();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Dataset creation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      {/* Header */}
      <header className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between pb-8 border-b border-slate-800 gap-4">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
            RAGBench Platform
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Production-Grade LLM, RAG & Agent Evaluation Platform
          </p>
        </div>

        {/* Health status badge */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-4 py-2 rounded-lg text-sm">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                health?.status === "healthy" ? "bg-emerald-400" : "bg-rose-500"
              }`}
            />
            <span>API: {health?.status || "Connecting..."}</span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-400">DB: {health?.database || "..."}</span>
          </div>
          <button
            onClick={loadAll}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs transition"
          >
            Refresh
          </button>
        </div>
      </header>

      {errorMsg && (
        <div className="max-w-7xl mx-auto mt-4 p-4 bg-rose-950/60 border border-rose-800 text-rose-200 rounded-lg text-sm">
          Backend notice: {errorMsg}. (Make sure FastAPI backend is running on http://localhost:8000).
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto mt-8 flex border-b border-slate-800 gap-8">
        {(["experiments", "regression", "datasets"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-3 text-sm font-medium transition capitalize ${
              activeTab === tab
                ? "text-blue-400 border-b-2 border-blue-400"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab === "experiments" && "Experiments & Runs"}
            {tab === "regression" && "Regression & CI Gates"}
            {tab === "datasets" && "Datasets"}
          </button>
        ))}
      </div>

      <main className="max-w-7xl mx-auto mt-8">
        {/* TAB 1: EXPERIMENTS */}
        {activeTab === "experiments" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* New Experiment Form */}
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl h-fit">
              <h2 className="text-lg font-semibold mb-4 text-slate-200">Run New Evaluation</h2>
              <form onSubmit={handleRunExperiment} className="space-y-4 text-sm">
                <div>
                  <label className="block text-slate-400 mb-1">Experiment Name</label>
                  <input
                    type="text"
                    placeholder="e.g. GPT-4o Candidate v1"
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
                      else setModel("mock-model");
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 focus:border-blue-500 outline-none"
                  >
                    <option value="mock">Mock Provider (Deterministic)</option>
                    <option value="groq">Groq (Live API)</option>
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="google">Google</option>
                  </select>
                </div>
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
                  className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 rounded-lg transition disabled:opacity-50 mt-2"
                >
                  {loading ? "Running Evaluation..." : "Execute Experiment"}
                </button>
              </form>
            </div>

            {/* Experiment Table */}
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
                      {experiments.map((exp) => (
                        <tr key={exp.id} className="hover:bg-slate-950/40">
                          <td className="py-4 font-medium">
                            <div className="flex items-center gap-2">
                              <span>{exp.name}</span>
                              {exp.is_baseline && (
                                <span className="bg-indigo-900/60 text-indigo-300 text-xs px-2 py-0.5 rounded border border-indigo-700">
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
                                onClick={() => handleSetBaseline(exp.id)}
                                className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-xs rounded transition"
                              >
                                Set Baseline
                              </button>
                            )}
                            <button
                              onClick={() => handleCheckRegression(exp.id)}
                              className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-xs rounded transition text-white"
                            >
                              Check CI
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: REGRESSION & CI GATES */}
        {activeTab === "regression" && (
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl">
            <h2 className="text-lg font-semibold mb-2 text-slate-200">CI/CD Automated Regression Gates</h2>
            <p className="text-sm text-slate-400 mb-6">
              Compare candidate experiments against the active baseline within a ±2% tolerance budget.
            </p>

            {regressionReport ? (
              <div className="space-y-6">
                <div
                  className={`p-4 rounded-lg border ${
                    regressionReport.report.has_regression
                      ? "bg-rose-950/40 border-rose-800 text-rose-200"
                      : "bg-emerald-950/40 border-emerald-800 text-emerald-200"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-base">
                      {regressionReport.report.has_regression
                        ? "❌ Regression Detected — CI Gate FAILED"
                        : "✅ Zero Regression Detected — CI Gate PASSED"}
                    </span>
                    <span className="text-xs bg-slate-950 px-2.5 py-1 rounded border border-slate-800">
                      Tolerance: {regressionReport.report.tolerance * 100}%
                    </span>
                  </div>
                  {regressionReport.report.has_regression && (
                    <div className="text-xs mt-2">
                      Regressed Metrics: {regressionReport.report.regressed_metrics.join(", ")}
                    </div>
                  )}
                </div>

                {/* Breakdown table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        <th className="pb-3">Metric</th>
                        <th className="pb-3">Candidate Score</th>
                        <th className="pb-3">Baseline Score</th>
                        <th className="pb-3">Delta</th>
                        <th className="pb-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {Object.entries(regressionReport.report.details || {}).map(([metric, d]) => (
                        <tr key={metric}>
                          <td className="py-3 font-medium text-slate-300">{metric}</td>
                          <td className="py-3 text-slate-200">{d.candidate_score.toFixed(4)}</td>
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
                              className={`text-xs px-2 py-0.5 rounded border ${
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
                  className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 rounded-lg transition disabled:opacity-50"
                >
                  Create Dataset
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
      </main>
    </div>
  );
}