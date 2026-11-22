"use client";

import React, { useEffect, useState } from "react";
import MarkdownRenderer from "./MarkdownRenderer";
import {
  AttackExecutionResult,
  AttackTestCase,
  fetchAttackCatalog,
  fetchRedTeamReports,
  RedTeamBenchmarkReport,
  runRedTeamBenchmark,
} from "@/lib/api";

interface RedTeamViewProps {
  showToast: (message: string, type: "loading" | "success" | "error") => void;
}

export default function RedTeamView({ showToast }: RedTeamViewProps) {
  // Catalog & History State
  const [attacks, setAttacks] = useState<AttackTestCase[]>([]);
  const [reports, setReports] = useState<RedTeamBenchmarkReport[]>([]);
  const [loadingInitial, setLoadingInitial] = useState(false);

  // Configuration State
  const [targetProvider, setTargetProvider] = useState("groq");
  const [targetModel, setTargetModel] = useState("openai/gpt-oss-120b");
  const [guardrailsEnabled, setGuardrailsEnabled] = useState(true);
  const [piiEnabled, setPiiEnabled] = useState(true);

  // Selected Categories
  const [selectedCategories, setSelectedCategories] = useState<string[]>([
    "direct_injection",
    "jailbreak",
    "indirect_injection",
    "system_extraction",
    "topical_evasion",
    "pii_leakage",
  ]);

  // Execution State
  const [runningBenchmark, setRunningBenchmark] = useState(false);
  const [activeReport, setActiveReport] = useState<RedTeamBenchmarkReport | null>(null);

  // Filter State in Results Matrix
  const [statusFilter, setStatusFilter] = useState<"all" | "defended" | "breached">("all");
  const [expandedAttackId, setExpandedAttackId] = useState<string | null>(null);

  const categoryLabels: Record<string, { label: string; icon: string }> = {
    direct_injection: { label: "Direct Prompt Injection", icon: "💉" },
    jailbreak: { label: "Adversarial Jailbreaks", icon: "🚨" },
    indirect_injection: { label: "Indirect Context Poisoning", icon: "☣️" },
    system_extraction: { label: "System Prompt Extraction", icon: "🔓" },
    topical_evasion: { label: "Topical Domain Evasion", icon: "🎮" },
    pii_leakage: { label: "PII & Data Leakage", icon: "🔒" },
  };

  const loadData = async () => {
    setLoadingInitial(true);
    try {
      const [catalogData, reportsData] = await Promise.all([
        fetchAttackCatalog().catch(() => []),
        fetchRedTeamReports().catch(() => []),
      ]);
      setAttacks(catalogData);
      setReports(reportsData);
      if (reportsData.length > 0 && !activeReport) {
        setActiveReport(reportsData[0]);
      }
    } catch {
      showToast("Failed to load red-team catalog", "error");
    } finally {
      setLoadingInitial(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const toggleCategory = (cat: string) => {
    if (selectedCategories.includes(cat)) {
      if (selectedCategories.length === 1) {
        showToast("At least one attack category must be selected", "error");
        return;
      }
      setSelectedCategories(selectedCategories.filter((c) => c !== cat));
    } else {
      setSelectedCategories([...selectedCategories, cat]);
    }
  };

  const handleRunBenchmark = async () => {
    setRunningBenchmark(true);
    try {
      const report = await runRedTeamBenchmark({
        provider: targetProvider,
        model: targetModel,
        categories: selectedCategories,
        guardrails_enabled: guardrailsEnabled,
        pii_sanitization_enabled: piiEnabled,
      });
      setActiveReport(report);
      setReports([report, ...reports.filter((r) => r.benchmark_id !== report.benchmark_id)]);
      showToast(
        `Red-team benchmark completed: ${report.security_posture_score}% defense score!`,
        report.security_posture_score >= 80 ? "success" : "error"
      );
    } catch (err: any) {
      showToast(err.message || "Failed to run red-team benchmark", "error");
    } finally {
      setRunningBenchmark(false);
    }
  };

  const filteredResults = activeReport?.attack_results.filter((res) => {
    if (statusFilter === "defended") return res.status === "defended";
    if (statusFilter === "breached") return res.status === "breached";
    return true;
  });

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-emerald-400";
    if (score >= 75) return "text-blue-400";
    if (score >= 60) return "text-amber-400";
    return "text-rose-400";
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case "critical":
        return "bg-rose-500/20 text-rose-300 border-rose-500/30";
      case "high":
        return "bg-amber-500/20 text-amber-300 border-amber-500/30";
      case "medium":
        return "bg-indigo-500/20 text-indigo-300 border-indigo-500/30";
      default:
        return "bg-slate-500/20 text-slate-300 border-slate-500/30";
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn pb-16">
      {/* 1. Header Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-rose-950/40 via-slate-900 to-indigo-950/30 border border-rose-500/30 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-rose-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-2xl">⚔️</span>
              <h2 className="text-xl font-bold text-slate-100">
                AI Red-Teaming &amp; Adversarial Benchmark Suite
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                v3.4 Automated Fuzzing
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
              Automated adversarial testing across 6 vulnerability classes: Direct Injections, DAN Jailbreaks,
              Poisoned Contexts, System Prompt Exfiltration, Topical Evasion, and PII Leaks.
            </p>
          </div>

          <button
            onClick={loadData}
            disabled={loadingInitial}
            className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 flex items-center gap-2 transition self-start md:self-auto"
          >
            <span>↻</span>
            <span>Refresh Attacks</span>
          </button>
        </div>

        {/* Quick Stats Pill Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
          <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">
              Attack Catalog
            </span>
            <div className="flex items-baseline gap-1 mt-1">
              <span className="text-lg font-bold text-rose-400">{attacks.length || 24}</span>
              <span className="text-[10px] text-slate-500">curated probes</span>
            </div>
          </div>

          <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">
              Vulnerability Classes
            </span>
            <div className="flex items-baseline gap-1 mt-1">
              <span className="text-lg font-bold text-indigo-400">6 Categories</span>
              <span className="text-[10px] text-slate-500">end-to-end</span>
            </div>
          </div>

          <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">
              Active Defense
            </span>
            <div className="flex items-baseline gap-1 mt-1">
              <span className="text-lg font-bold text-emerald-400">Guardrails + PII</span>
              <span className="text-[10px] text-slate-500">shielded</span>
            </div>
          </div>

          <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">
              Security Grade
            </span>
            <div className="flex items-baseline gap-1 mt-1">
              <span className="text-lg font-bold text-amber-400">
                {activeReport?.risk_grade.split(" ")[0] || "A+"}
              </span>
              <span className="text-[10px] text-slate-500">posture rating</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Benchmark Configuration Console */}
      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <span className="text-sm">🎯</span>
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
              Target Model &amp; Fuzzing Configuration
            </h3>
          </div>
          <span className="text-[11px] text-slate-400">
            Test any configured provider against automated adversarial probes
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          <div>
            <label className="block text-slate-400 mb-1 font-medium">Provider</label>
            <select
              value={targetProvider}
              onChange={(e) => {
                setTargetProvider(e.target.value);
                if (e.target.value === "groq") setTargetModel("openai/gpt-oss-120b");
                if (e.target.value === "google") setTargetModel("gemini-2.5-flash");
                if (e.target.value === "openai") setTargetModel("gpt-4o-mini");
                if (e.target.value === "mock") setTargetModel("mock-model");
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 outline-none focus:border-rose-500"
            >
              <option value="groq">Groq LPU (Ultra-Fast)</option>
              <option value="google">Google Gemini</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic Claude</option>
              <option value="webhook">Custom RAG Webhook</option>
              <option value="mock">Mock Provider (Local Simulation)</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 mb-1 font-medium">Target Model Identifier</label>
            <input
              type="text"
              value={targetModel}
              onChange={(e) => setTargetModel(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 outline-none focus:border-rose-500 font-mono text-[11px]"
            />
          </div>

          <div className="sm:col-span-2 flex flex-col justify-end">
            <div className="flex flex-wrap items-center gap-4 p-2.5 bg-slate-950 rounded-lg border border-slate-800">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={guardrailsEnabled}
                  onChange={(e) => setGuardrailsEnabled(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-emerald-500 focus:ring-0"
                />
                <span className="text-xs text-slate-300 font-medium">
                  🛡️ NeMo Guardrails Shield
                </span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={piiEnabled}
                  onChange={(e) => setPiiEnabled(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0"
                />
                <span className="text-xs text-slate-300 font-medium">
                  🔒 PII Sanitizer Pipeline
                </span>
              </label>
            </div>
          </div>
        </div>

        {/* Attack Category Selector Chips */}
        <div className="space-y-2 pt-2 border-t border-slate-800/80">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-300">Selected Attack Categories:</span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setSelectedCategories(Object.keys(categoryLabels))}
                className="text-[11px] text-indigo-400 hover:underline"
              >
                Select All
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
            {Object.entries(categoryLabels).map(([cat, info]) => {
              const active = selectedCategories.includes(cat);
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => toggleCategory(cat)}
                  className={`p-2.5 rounded-xl border text-left transition flex flex-col justify-between ${
                    active
                      ? "bg-rose-950/40 border-rose-500/60 text-rose-200"
                      : "bg-slate-950/40 border-slate-800 text-slate-500 hover:border-slate-700"
                  }`}
                >
                  <span className="text-base">{info.icon}</span>
                  <span className="text-[11px] font-semibold mt-1 truncate" title={info.label}>
                    {info.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <button
          type="button"
          onClick={handleRunBenchmark}
          disabled={runningBenchmark}
          className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-rose-600 via-indigo-600 to-indigo-700 hover:from-rose-500 hover:to-indigo-600 text-white font-bold text-xs shadow-lg shadow-rose-950 transition flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {runningBenchmark ? (
            <>
              <span className="animate-spin text-sm">↻</span>
              <span>Executing Adversarial Red-Team Fuzzing Suite...</span>
            </>
          ) : (
            <>
              <span>🚀</span>
              <span>Launch AI Red-Team Benchmark ({selectedCategories.length} Categories)</span>
            </>
          )}
        </button>
      </div>

      {/* 3. Executive Security Posture Report */}
      {activeReport && (
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-6 animate-fadeIn">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">📊</span>
                <h3 className="text-base font-bold text-slate-100">
                  Security Posture Audit: {activeReport.target_model}
                </h3>
              </div>
              <span className="text-[11px] text-slate-400 font-mono mt-0.5 block">
                Benchmark ID: {activeReport.benchmark_id} • Executed in {activeReport.latency_ms.toFixed(0)}ms
              </span>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                  Security Posture Score
                </span>
                <span className={`text-2xl font-black ${getScoreColor(activeReport.security_posture_score)}`}>
                  {activeReport.security_posture_score.toFixed(1)}%
                </span>
              </div>
              <div className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs font-bold text-slate-200">
                {activeReport.risk_grade}
              </div>
            </div>
          </div>

          {/* Metric Stats Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                Total Attacks Tested
              </span>
              <span className="text-xl font-bold text-slate-200 mt-1 block">
                {activeReport.total_attacks}
              </span>
            </div>

            <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800">
              <span className="text-[10px] text-emerald-400 uppercase font-semibold block">
                Attacks Defended
              </span>
              <span className="text-xl font-bold text-emerald-400 mt-1 block">
                {activeReport.defended_attacks}
              </span>
            </div>

            <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800">
              <span className="text-[10px] text-rose-400 uppercase font-semibold block">
                Security Breaches
              </span>
              <span className="text-xl font-bold text-rose-400 mt-1 block">
                {activeReport.breached_attacks}
              </span>
            </div>

            <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800">
              <span className="text-[10px] text-cyan-400 uppercase font-semibold block">
                Shield Intercepted
              </span>
              <span className="text-xl font-bold text-cyan-400 mt-1 block">
                {activeReport.guardrails_intercepted_count}
              </span>
            </div>
          </div>

          {/* Category Defense Rate Bars */}
          <div className="space-y-3 p-4 bg-slate-950 rounded-xl border border-slate-800">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
              Resilience by Attack Category
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(activeReport.defense_rate_by_category).map(([cat, rate]) => (
                <div key={cat} className="p-2.5 rounded-lg bg-slate-900 border border-slate-800/80 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-medium capitalize">
                      {categoryLabels[cat]?.icon || "🛡️"} {cat.replace("_", " ")}
                    </span>
                    <span className={`font-bold font-mono ${getScoreColor(rate)}`}>
                      {rate.toFixed(0)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        rate >= 90
                          ? "bg-emerald-500"
                          : rate >= 75
                          ? "bg-blue-500"
                          : rate >= 60
                          ? "bg-amber-500"
                          : "bg-rose-500"
                      }`}
                      style={{ width: `${rate}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Executive Summary */}
          <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1.5">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">
              Executive Findings &amp; Summary
            </span>
            <p className="text-xs text-slate-300 leading-relaxed font-sans">
              {activeReport.executive_summary}
            </p>
          </div>

          {/* 4. Detailed Attack Trace Matrix */}
          <div className="space-y-3 pt-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                Adversarial Attack Traces ({filteredResults?.length || 0})
              </span>
              <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
                {(["all", "defended", "breached"] as const).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setStatusFilter(filter)}
                    className={`px-2.5 py-1 rounded text-[11px] font-semibold transition capitalize ${
                      statusFilter === filter
                        ? "bg-slate-800 text-slate-100 shadow"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {filter}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              {filteredResults?.map((res) => {
                const isExpanded = expandedAttackId === res.test_case.id;
                return (
                  <div
                    key={res.test_case.id}
                    className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2 transition"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[9px] px-2 py-0.5 rounded font-bold uppercase ${getSeverityBadge(
                            res.test_case.severity
                          )}`}
                        >
                          {res.test_case.severity}
                        </span>
                        <span className="text-xs font-bold text-slate-200">
                          {res.test_case.name}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          ({res.test_case.category.replace("_", " ")})
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {res.guardrails_intercepted && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-semibold font-mono">
                            🛡️ Guardrail Intercepted
                          </span>
                        )}

                        <span
                          className={`text-xs px-2.5 py-0.5 rounded font-bold uppercase font-mono ${
                            res.status === "defended"
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                              : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                          }`}
                        >
                          {res.status === "defended" ? "✓ DEFENDED" : "✕ BREACHED"}
                        </span>

                        <button
                          type="button"
                          onClick={() => setExpandedAttackId(isExpanded ? null : res.test_case.id)}
                          className="text-[11px] text-slate-400 hover:text-slate-200 px-2 py-0.5 rounded bg-slate-900 border border-slate-800"
                        >
                          {isExpanded ? "Hide Trace ▲" : "View Trace ▼"}
                        </button>
                      </div>
                    </div>

                    {/* Expandable Trace Details */}
                    {isExpanded && (
                      <div className="pt-3 border-t border-slate-800/80 space-y-3 text-xs animate-fadeIn">
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">
                            Attack Prompt Injected
                          </span>
                          <p className="font-mono text-[11px] p-2.5 bg-slate-900 rounded-lg text-rose-300 border border-rose-900/30">
                            {res.test_case.prompt}
                          </p>
                        </div>

                        {res.test_case.context_passage && (
                          <div>
                            <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">
                              Context Passage Provided
                            </span>
                            <p className="font-mono text-[11px] p-2.5 bg-slate-900 rounded-lg text-slate-300 border border-slate-800">
                              {res.test_case.context_passage}
                            </p>
                          </div>
                        )}

                        <div>
                          <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">
                            Target Model Response
                          </span>
                          <div className="font-mono text-[11px] p-2.5 bg-slate-900 rounded-lg text-slate-200 border border-slate-800">
                            <MarkdownRenderer content={res.model_output} />
                          </div>
                        </div>

                        {res.breach_reason && (
                          <div className="p-2.5 rounded-lg bg-rose-950/30 border border-rose-500/30 text-rose-200">
                            <span className="font-bold block text-[11px]">Breach Analysis:</span>
                            <p className="text-[11px] mt-0.5">{res.breach_reason}</p>
                          </div>
                        )}

                        <div className="p-2.5 rounded-lg bg-indigo-950/30 border border-indigo-500/30 text-indigo-200">
                          <span className="font-bold block text-[11px]">Recommended Remediation:</span>
                          <p className="text-[11px] mt-0.5">{res.mitigation_recommendation}</p>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
