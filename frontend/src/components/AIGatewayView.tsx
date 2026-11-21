"use client";

import React, { useEffect, useState } from "react";
import MarkdownRenderer from "./MarkdownRenderer";
import {

  BudgetConfig,
  BudgetStatus,
  CacheStats,
  callGatewayChatCompletions,
  fetchGatewayBudget,
  fetchGatewayStats,
  GatewayCompletionResponse,
  purgeGatewayCache,
} from "@/lib/api";

interface AIGatewayViewProps {
  showToast: (message: string, type: "loading" | "success" | "error") => void;
}

export default function AIGatewayView({ showToast }: AIGatewayViewProps) {
  // Stats & Budget State
  const [stats, setStats] = useState<CacheStats | null>(null);
  const [budget, setBudget] = useState<BudgetStatus | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [purging, setPurging] = useState(false);

  // Budget Edit State
  const [budgetUsdInput, setBudgetUsdInput] = useState<string>("");
  const [tokenQuotaInput, setTokenQuotaInput] = useState<string>("");
  const [savingBudget, setSavingBudget] = useState(false);

  // Playground State
  const [prompt, setPrompt] = useState("What are the key architectural benefits of Retrieval-Augmented Generation?");
  const [model, setModel] = useState("openai/gpt-oss-120b");
  const [provider, setProvider] = useState("groq");
  const [fallbackProvider, setFallbackProvider] = useState("mock");
  const [cacheEnabled, setCacheEnabled] = useState(true);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.95);
  const [guardrailsEnabled, setGuardrailsEnabled] = useState(true);
  const [maxTokens, setMaxTokens] = useState<number>(2500);
  const [sendingRequest, setSendingRequest] = useState(false);

  const [gatewayResponse, setGatewayResponse] = useState<GatewayCompletionResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Response Display Controls
  const [responseViewMode, setResponseViewMode] = useState<"rendered" | "raw">("rendered");
  const [copiedResponse, setCopiedResponse] = useState(false);

  const handleCopyResponse = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedResponse(true);
    showToast("Assistant response copied to clipboard!", "success");
    setTimeout(() => setCopiedResponse(false), 2000);
  };


  const loadData = async () => {
    setLoadingStats(true);
    try {
      const [statsData, budgetData] = await Promise.all([
        fetchGatewayStats().catch(() => null),
        fetchGatewayBudget().catch(() => null),
      ]);
      if (statsData) setStats(statsData);
      if (budgetData) {
        setBudget(budgetData);
        setBudgetUsdInput(budgetData.monthly_budget_usd ? String(budgetData.monthly_budget_usd) : "");
        setTokenQuotaInput(budgetData.monthly_token_quota ? String(budgetData.monthly_token_quota) : "");
      }
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handlePurgeCache = async () => {
    setPurging(true);
    showToast("Purging AI Gateway semantic cache...", "loading");
    try {
      const res = await purgeGatewayCache();
      showToast(res.message, "success");
      await loadData();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to purge cache", "error");
    } finally {
      setPurging(false);
    }
  };

  const handleSaveBudget = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingBudget(true);
    showToast("Updating workspace budget limits...", "loading");
    try {
      const config: BudgetConfig = {
        monthly_budget_usd: budgetUsdInput.trim() ? parseFloat(budgetUsdInput) : null,
        monthly_token_quota: tokenQuotaInput.trim() ? parseInt(tokenQuotaInput, 10) : null,
      };
      const updated = await import("@/lib/api").then((m) => m.updateGatewayBudget(config));
      setBudget(updated);
      showToast("Workspace budget updated successfully!", "success");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to update budget", "error");
    } finally {
      setSavingBudget(false);
    }
  };

  const handleSendRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setSendingRequest(true);
    setErrorMsg(null);
    try {
      const res = await callGatewayChatCompletions({
        model,
        messages: [{ role: "user", content: prompt.trim() }],
        provider,
        fallback_providers: fallbackProvider ? [fallbackProvider] : ["mock"],
        cache_enabled: cacheEnabled,
        similarity_threshold: similarityThreshold,
        guardrails_enabled: guardrailsEnabled,
        max_tokens: maxTokens,
      });

      setGatewayResponse(res);
      showToast(
        res.gateway.cached
          ? `⚡ Cache Hit! Served in ${res.gateway.latency_ms.toFixed(1)}ms ($0 cost)`
          : `Live completion via ${res.gateway.provider_used} in ${res.gateway.latency_ms.toFixed(0)}ms`,
        "success"
      );
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Gateway request failed";
      setErrorMsg(msg);
      showToast(msg, "error");
    } finally {
      setSendingRequest(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-2xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">⚡</span>
            <h1 className="text-xl font-bold text-slate-100">AI Gateway & Semantic Cache</h1>
            <span className="bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 text-xs px-2.5 py-0.5 rounded-full font-semibold">
              Milestone v3.1
            </span>
          </div>
          <p className="text-sm text-slate-400">
            OpenAI-compatible high-throughput gateway featuring sub-5ms semantic caching, automated provider failovers, and workspace budget caps.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={loadingStats}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition"
          >
            {loadingStats ? "Refreshing..." : "↻ Refresh Stats"}
          </button>
          <button
            onClick={handlePurgeCache}
            disabled={purging}
            className="px-3 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-medium rounded-lg border border-rose-500/30 transition flex items-center gap-1.5"
          >
            <span>🗑️</span>
            <span>{purging ? "Purging..." : "Purge Cache"}</span>
          </button>
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Cache Hit Rate */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>Cache Hit Rate</span>
            <span className="text-emerald-400 font-mono text-[11px]">⚡ Sub-5ms</span>
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {stats ? `${(stats.hit_rate * 100).toFixed(1)}%` : "0.0%"}
          </div>
          <div className="mt-2 text-xs text-slate-500">
            {stats ? `${stats.cache_hits} hits / ${stats.total_requests} requests` : "No traffic yet"}
          </div>
        </div>

        {/* Card 2: Cost Saved */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>LLM Cost Saved</span>
            <span className="text-emerald-400 font-mono text-[11px]">Zero-Cost</span>
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            ${stats ? stats.total_cost_saved_usd.toFixed(5) : "0.00000"}
          </div>
          <div className="mt-2 text-xs text-slate-500">
            Saved by returning cached generations
          </div>
        </div>

        {/* Card 3: Latency Slashed */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>Latency Slashed</span>
            <span className="text-indigo-400 font-mono text-[11px]">Time Saved</span>
          </div>
          <div className="text-2xl font-bold text-indigo-300 font-mono">
            {stats ? `${stats.total_latency_saved_ms.toFixed(0)} ms` : "0 ms"}
          </div>
          <div className="mt-2 text-xs text-slate-500">
            Cumulative compute latency avoided
          </div>
        </div>

        {/* Card 4: Active Cache Entries */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>Active Cache Entries</span>
            <span className="text-blue-400 font-mono text-[11px]">TTL 1h</span>
          </div>
          <div className="text-2xl font-bold text-blue-300 font-mono">
            {stats ? stats.cached_entries_count : 0}
          </div>
          <div className="mt-2 text-xs text-slate-500">
            Semantic & exact hashes in memory
          </div>
        </div>
      </div>

      {/* Main Grid: Interactive Playground + Budget & Quickstart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Interactive Playground (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
                <span>🎮</span> Gateway Interactive Playground
              </h2>
              <span className="text-xs text-slate-400 font-mono">POST /api/v1/gateway/chat/completions</span>
            </div>

            <form onSubmit={handleSendRequest} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">User Prompt</label>
                <textarea
                  rows={3}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Enter a prompt to dispatch through the AI Gateway..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 outline-none focus:border-indigo-500 font-mono"
                  required
                />
              </div>

              {/* Provider, Model, Fallback, and Max Tokens Controls */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Primary Provider</label>
                  <select
                    value={provider}
                    onChange={(e) => {
                      setProvider(e.target.value);
                      if (e.target.value === "groq") setModel("openai/gpt-oss-120b");
                      else if (e.target.value === "mock") setModel("mock-model");
                      else if (e.target.value === "openai") setModel("gpt-4o-mini");
                      else if (e.target.value === "google") setModel("gemini-1.5-flash");
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500"
                  >
                    <option value="groq">Groq LPU (Ultra-Fast)</option>
                    <option value="mock">Mock Provider (Deterministic)</option>
                    <option value="openai">OpenAI (GPT-4o Mini)</option>
                    <option value="google">Google Gemini (1.5 Flash)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">Model Identifier</label>
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">Automated Fallback</label>
                  <select
                    value={fallbackProvider}
                    onChange={(e) => setFallbackProvider(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500"
                  >
                    <option value="mock">Fallback to Mock (Guaranteed)</option>
                    <option value="google">Fallback to Gemini</option>
                    <option value="groq">Fallback to Groq</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">Max Tokens Limit</label>
                  <select
                    value={maxTokens}
                    onChange={(e) => setMaxTokens(parseInt(e.target.value, 10))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 font-mono"
                  >
                    <option value={1000}>1,000 tokens (Short)</option>
                    <option value={2000}>2,000 tokens (Standard)</option>
                    <option value={2500}>2,500 tokens (Recommended)</option>
                    <option value={4000}>4,000 tokens (Detailed &amp; Tables)</option>
                    <option value={8000}>8,000 tokens (Max Capacity)</option>
                  </select>
                </div>
              </div>


              {/* Cache Controls */}
              <div className="flex flex-wrap items-center justify-between gap-4 p-3 bg-slate-950 rounded-lg border border-slate-800">
                <div className="flex flex-wrap items-center gap-4">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={cacheEnabled}
                      onChange={(e) => setCacheEnabled(e.target.checked)}
                      className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                    />
                    <span className="text-xs text-slate-300 font-medium">Enable Sub-5ms Semantic Cache</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={guardrailsEnabled}
                      onChange={(e) => setGuardrailsEnabled(e.target.checked)}
                      className="rounded bg-slate-900 border-slate-700 text-emerald-500 focus:ring-0"
                    />
                    <span className="text-xs text-emerald-400 font-medium flex items-center gap-1">
                      <span>🛡️</span> NeMo Guardrails Shield
                    </span>
                  </label>
                </div>

                {cacheEnabled && (
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-slate-400">Similarity Threshold:</span>
                    <input
                      type="number"
                      min={0.5}
                      max={1.0}
                      step={0.05}
                      value={similarityThreshold}
                      onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
                      className="w-16 bg-slate-900 border border-slate-800 rounded px-1.5 py-0.5 text-xs text-slate-200 font-mono outline-none text-center"
                    />
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={sendingRequest}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20"
              >
                {sendingRequest ? (
                  <>
                    <span className="animate-spin text-sm">↻</span>
                    <span>Routing through AI Gateway...</span>
                  </>
                ) : (
                  <>
                    <span>⚡ Send Request to Gateway</span>
                  </>
                )}
              </button>
            </form>

            {errorMsg && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-300">
                ❌ {errorMsg}
              </div>
            )}

            {/* Gateway Response View */}
            {gatewayResponse && (
              <div className="mt-4 p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                  <div className="flex items-center gap-2">
                    {gatewayResponse.gateway.guardrails_blocked ? (
                      <span className="bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[11px] px-2 py-0.5 rounded font-mono font-bold flex items-center gap-1">
                        <span>🚫</span> GUARDRAILS INTERCEPTED
                      </span>
                    ) : gatewayResponse.gateway.guardrails_applied ? (
                      <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[11px] px-2 py-0.5 rounded font-mono font-semibold flex items-center gap-1">
                        <span>🛡️</span> GUARDRAILS PASSED
                      </span>
                    ) : null}

                    {gatewayResponse.gateway.cached ? (
                      <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[11px] px-2 py-0.5 rounded font-mono font-bold flex items-center gap-1">
                        <span>⚡</span> CACHE HIT
                      </span>
                    ) : (
                      <span className="bg-blue-500/20 text-blue-300 border border-blue-500/30 text-[11px] px-2 py-0.5 rounded font-mono font-bold flex items-center gap-1">
                        <span>🌐</span> LIVE INFERENCE
                      </span>
                    )}

                    {gatewayResponse.gateway.fallback_triggered && (
                      <span className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[11px] px-2 py-0.5 rounded font-mono font-semibold">
                        ⚠ Failover Triggered
                      </span>
                    )}

                    {gatewayResponse.choices[0]?.finish_reason === "length" && (
                      <span className="bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[11px] px-2 py-0.5 rounded font-mono font-semibold flex items-center gap-1">
                        <span>⚠️</span> Output Truncated (Hit Max Tokens)
                      </span>
                    )}
                  </div>


                  <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
                    <span>
                      Latency:{" "}
                      <strong className={gatewayResponse.gateway.cached ? "text-emerald-400" : "text-slate-200"}>
                        {gatewayResponse.gateway.latency_ms.toFixed(1)} ms
                      </strong>
                    </span>
                    <span>•</span>
                    <span>Tokens: <strong className="text-slate-200">{gatewayResponse.usage.total_tokens}</strong></span>
                    <span>•</span>
                    <span>
                      Cost:{" "}
                      <strong className="text-slate-200">
                        ${gatewayResponse.gateway.cost_usd.toFixed(6)}
                      </strong>
                    </span>
                  </div>
                </div>

                {gatewayResponse.choices[0]?.finish_reason === "length" && (
                  <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-base">💡</span>
                      <span>The answer was cut off because it reached the current token limit ({gatewayResponse.usage.completion_tokens} tokens).</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setMaxTokens(4000);
                        showToast("Max Tokens set to 4,000. Click Send Request to regenerate full answer!", "success");
                      }}
                      className="px-3 py-1 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-[11px] text-amber-200 font-semibold rounded-lg transition whitespace-nowrap shadow-sm"
                    >
                      Set to 4,000 Tokens &amp; Retry
                    </button>
                  </div>
                )}

                <div className="space-y-2">

                  <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                    <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                      <span>🤖</span> Assistant Response
                    </span>
                    <div className="flex items-center gap-2">
                      <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-0.5 text-[11px]">
                        <button
                          type="button"
                          onClick={() => setResponseViewMode("rendered")}
                          className={`px-2.5 py-0.5 rounded font-medium transition ${
                            responseViewMode === "rendered"
                              ? "bg-indigo-600 text-white shadow-sm"
                              : "text-slate-400 hover:text-slate-200"
                          }`}
                        >
                          Formatted
                        </button>
                        <button
                          type="button"
                          onClick={() => setResponseViewMode("raw")}
                          className={`px-2.5 py-0.5 rounded font-medium transition ${
                            responseViewMode === "raw"
                              ? "bg-indigo-600 text-white shadow-sm"
                              : "text-slate-400 hover:text-slate-200"
                          }`}
                        >
                          Raw Markdown
                        </button>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleCopyResponse(gatewayResponse.choices[0]?.message?.content || "")}
                        className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[11px] text-slate-300 rounded-lg transition flex items-center gap-1 font-medium"
                      >
                        {copiedResponse ? (
                          <>
                            <span className="text-emerald-400">✓</span>
                            <span className="text-emerald-400 font-semibold">Copied!</span>
                          </>
                        ) : (
                          <>
                            <span>📋</span>
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {responseViewMode === "rendered" ? (
                    <div className="p-4 bg-slate-900/90 rounded-xl border border-slate-800/80 text-slate-200 leading-relaxed shadow-inner">
                      <MarkdownRenderer content={gatewayResponse.choices[0]?.message?.content || ""} />
                    </div>
                  ) : (
                    <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 text-xs text-slate-200 leading-relaxed font-mono whitespace-pre-wrap max-h-96 overflow-y-auto">
                      {gatewayResponse.choices[0]?.message?.content}
                    </div>
                  )}
                </div>


                <div className="text-[11px] text-slate-500 flex flex-wrap gap-4 pt-1">
                  <span>Provider: <code className="text-slate-300">{gatewayResponse.gateway.provider_used}</code></span>
                  <span>Model: <code className="text-slate-300">{gatewayResponse.gateway.model_used}</code></span>
                  {gatewayResponse.gateway.cached && (
                    <span className="text-emerald-400 font-medium">
                      ✓ $0.00 Cost Incurred (Saved ${gatewayResponse.gateway.cost_saved_usd.toFixed(5)})
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Workspace Budget Manager & Integration (1 col) */}
        <div className="space-y-6">
          {/* Budget Manager Card */}
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <span>💰</span> Workspace Budget Caps
              </h3>
              {budget?.budget_exceeded && (
                <span className="bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] px-1.5 py-0.5 rounded font-semibold">
                  Exceeded
                </span>
              )}
            </div>

            {budget && (
              <div className="space-y-3">
                {/* Spend Meter */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Monthly Spending:</span>
                    <span className="font-mono text-slate-200">
                      ${budget.current_month_cost_usd.toFixed(4)} / {budget.monthly_budget_usd ? `$${budget.monthly_budget_usd.toFixed(2)}` : "∞"}
                    </span>
                  </div>
                  <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                    <div
                      className={`h-full transition-all duration-500 ${
                        budget.cost_usage_percentage >= 100
                          ? "bg-rose-500"
                          : budget.cost_usage_percentage >= 80
                          ? "bg-amber-500"
                          : "bg-indigo-500"
                      }`}
                      style={{ width: `${Math.min(100, budget.cost_usage_percentage || 0)}%` }}
                    />
                  </div>
                </div>

                {/* Token Meter */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Monthly Tokens:</span>
                    <span className="font-mono text-slate-200">
                      {budget.current_month_tokens.toLocaleString()} / {budget.monthly_token_quota ? budget.monthly_token_quota.toLocaleString() : "∞"}
                    </span>
                  </div>
                  <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                    <div
                      className={`h-full transition-all duration-500 ${
                        budget.token_usage_percentage >= 100
                          ? "bg-rose-500"
                          : budget.token_usage_percentage >= 80
                          ? "bg-amber-500"
                          : "bg-blue-500"
                      }`}
                      style={{ width: `${Math.min(100, budget.token_usage_percentage || 0)}%` }}
                    />
                  </div>
                </div>
              </div>
            )}

            <form onSubmit={handleSaveBudget} className="space-y-3 pt-2 border-t border-slate-800/80">
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Monthly Budget Limit ($ USD)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="e.g. 50.00 (leave blank for unlimited)"
                  value={budgetUsdInput}
                  onChange={(e) => setBudgetUsdInput(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Monthly Token Ceiling</label>
                <input
                  type="number"
                  min="0"
                  placeholder="e.g. 1000000 (leave blank for unlimited)"
                  value={tokenQuotaInput}
                  onChange={(e) => setTokenQuotaInput(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono outline-none focus:border-indigo-500"
                />
              </div>

              <button
                type="submit"
                disabled={savingBudget}
                className="w-full py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition"
              >
                {savingBudget ? "Saving..." : "Save Budget Limits"}
              </button>
            </form>
          </div>

          {/* OpenAI Drop-In Integration Guide */}
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl space-y-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <span>🔌</span> Drop-In OpenAI SDK Usage
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Use RAGBench AI Gateway in your Python or Node.js codebase simply by setting the base URL:
            </p>
            <pre className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-indigo-300 font-mono overflow-x-auto">
{`from openai import OpenAI

client = OpenAI(
  base_url="https://ragbench.io/api/v1/gateway",
  api_key="your-workspace-token"
)

res = client.chat.completions.create(
  model="openai/gpt-oss-120b",
  messages=[{"role": "user", "content": "Hi"}]
)`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
