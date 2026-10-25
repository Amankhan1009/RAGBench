"use client";

import React, { useState, useEffect } from "react";
import {
  fetchAgentScenarios,
  evaluateAgentTrajectory,
  AgentScenarioPreset,
  AgentTrajectory,
  AgentTrajectoryReport,
  AgentStep,
} from "../lib/api";

interface AgentTrajectoryInspectorProps {
  showToast: (message: string, type: "loading" | "success" | "error") => void;
}

export default function AgentTrajectoryInspector({
  showToast,
}: AgentTrajectoryInspectorProps) {
  const [scenarios, setScenarios] = useState<AgentScenarioPreset[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("optimal-research-qa");
  const [loadingScenarios, setLoadingScenarios] = useState<boolean>(true);

  // Active editable evaluation state
  const [trajectory, setTrajectory] = useState<AgentTrajectory>({
    goal: "",
    steps: [],
    final_response: "",
    success: true,
  });
  const [expectedTools, setExpectedTools] = useState<string[]>([]);
  const [maxOptimalSteps, setMaxOptimalSteps] = useState<number>(3);
  const [loopThreshold, setLoopThreshold] = useState<number>(2);

  // Report evaluation state
  const [report, setReport] = useState<AgentTrajectoryReport | null>(null);
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [newToolInput, setNewToolInput] = useState<string>("");

  // Load scenarios on mount
  useEffect(() => {
    let isMounted = true;
    async function load() {
      try {
        setLoadingScenarios(true);
        const data = await fetchAgentScenarios();
        if (isMounted) {
          setScenarios(data);
          if (data.length > 0) {
            loadScenario(data[0]);
          }
        }
      } catch (err: unknown) {
        showToast(err instanceof Error ? err.message : "Failed to load scenarios", "error");
      } finally {
        if (isMounted) setLoadingScenarios(false);
      }
    }
    load();
    return () => {
      isMounted = false;
    };
  }, [showToast]);

  const loadScenario = (s: AgentScenarioPreset) => {
    setSelectedScenarioId(s.id);
    setTrajectory(JSON.parse(JSON.stringify(s.trajectory)));
    setExpectedTools([...s.expected_tools]);
    setMaxOptimalSteps(s.max_optimal_steps);
    setLoopThreshold(s.loop_threshold);
    // Auto-evaluate
    runEvaluation(s.trajectory, s.expected_tools, s.max_optimal_steps, s.loop_threshold);
  };

  const runEvaluation = async (
    traj: AgentTrajectory,
    tools: string[],
    maxSteps: number,
    threshold: number
  ) => {
    try {
      setEvaluating(true);
      const rep = await evaluateAgentTrajectory({
        trajectory: traj,
        expected_tools: tools,
        max_optimal_steps: maxSteps,
        loop_threshold: threshold,
      });
      setReport(rep);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Evaluation failed", "error");
    } finally {
      setEvaluating(false);
    }
  };

  const handleManualReevaluate = () => {
    runEvaluation(trajectory, expectedTools, maxOptimalSteps, loopThreshold);
  };

  const handleAddExpectedTool = () => {
    if (!newToolInput.trim()) return;
    if (!expectedTools.includes(newToolInput.trim())) {
      setExpectedTools([...expectedTools, newToolInput.trim()]);
    }
    setNewToolInput("");
  };

  const handleRemoveExpectedTool = (tool: string) => {
    setExpectedTools(expectedTools.filter((t) => t !== tool));
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* ── HEADER ── */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className="text-2xl">🤖</span>
              <h2 className="text-xl font-bold text-slate-100">
                Agent Trajectory &amp; Loop Inspector
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                v2.6 Engine
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Inspect multi-step agent trajectories, detect infinite tool loops, measure step efficiency, and verify tool execution safety.
            </p>
          </div>

          <button
            type="button"
            onClick={handleManualReevaluate}
            disabled={evaluating}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-950 transition disabled:opacity-50"
          >
            {evaluating ? (
              <>
                <svg
                  className="animate-spin text-current w-3.5 h-3.5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Evaluating...</span>
              </>
            ) : (
              <>
                <span>↻ Re-Evaluate Trajectory</span>
              </>
            )}
          </button>
        </div>

        {/* ── SCENARIO PRESET CHIPS ── */}
        <div className="space-y-2 pt-2 border-t border-slate-800">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Benchmark Scenario Library:
          </div>
          <div className="flex flex-wrap gap-2.5">
            {scenarios.map((s) => {
              const isActive = selectedScenarioId === s.id;
              let badgeColor = "bg-slate-800 text-slate-300 border-slate-700 hover:border-slate-600";
              if (isActive) {
                if (s.category === "optimal") badgeColor = "bg-emerald-950 border-emerald-500 text-emerald-200 ring-1 ring-emerald-500/50";
                else if (s.category === "loop") badgeColor = "bg-rose-950 border-rose-500 text-rose-200 ring-1 ring-rose-500/50";
                else if (s.category === "security") badgeColor = "bg-amber-950 border-amber-500 text-amber-200 ring-1 ring-amber-500/50";
                else badgeColor = "bg-indigo-950 border-indigo-500 text-indigo-200 ring-1 ring-indigo-500/50";
              }

              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => loadScenario(s)}
                  className={`px-3 py-2 rounded-xl text-xs font-medium border transition flex items-center gap-2 ${badgeColor}`}
                >
                  <span>{s.name}</span>
                </button>
              );
            })}
          </div>
          {selectedScenarioId && (
            <p className="text-xs text-slate-400 italic pt-1">
              {scenarios.find((s) => s.id === selectedScenarioId)?.description}
            </p>
          )}
        </div>

        {/* ── PARAMETER CONTROLS ── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-slate-800 text-xs">
          {/* Expected Tools */}
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-slate-300 font-medium">Expected Tools Set</label>
            <div className="flex flex-wrap items-center gap-1.5 p-2 bg-slate-950 border border-slate-800 rounded-xl min-h-[38px]">
              {expectedTools.map((t) => (
                <span
                  key={t}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-indigo-950 text-indigo-300 border border-indigo-800/80 font-mono text-[11px]"
                >
                  <span>{t}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveExpectedTool(t)}
                    className="hover:text-rose-400 font-bold ml-0.5"
                  >
                    ×
                  </button>
                </span>
              ))}
              <div className="inline-flex items-center gap-1 flex-1 min-w-[120px]">
                <input
                  type="text"
                  placeholder="+ Add expected tool..."
                  value={newToolInput}
                  onChange={(e) => setNewToolInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddExpectedTool();
                    }
                  }}
                  className="bg-transparent border-none outline-none text-slate-300 font-mono text-xs w-full px-1"
                />
              </div>
            </div>
          </div>

          {/* Thresholds */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-300 font-medium mb-1.5">
                Max Optimal Steps
              </label>
              <input
                type="number"
                min={1}
                max={15}
                value={maxOptimalSteps}
                onChange={(e) => setMaxOptimalSteps(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none focus:border-indigo-500 font-mono"
              />
            </div>
            <div>
              <label className="block text-slate-300 font-medium mb-1.5">
                Loop Threshold
              </label>
              <input
                type="number"
                min={2}
                max={5}
                value={loopThreshold}
                onChange={(e) => setLoopThreshold(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 outline-none focus:border-indigo-500 font-mono"
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── DIAGNOSTIC REPORT HUD ── */}
      {report && (
        <div className="space-y-4">
          {/* Executive Verdict Card */}
          <div
            className={`p-5 rounded-2xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all duration-300 ${
              report.passed
                ? "bg-emerald-950/40 border-emerald-800/80 text-emerald-200"
                : "bg-rose-950/40 border-rose-800/80 text-rose-200"
            }`}
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-base font-bold">
                <span>{report.passed ? "✅" : "❌"}</span>
                <span>
                  {report.passed
                    ? "Agent Trajectory PASSED — Optimal Autonomous Execution"
                    : "Agent Trajectory FAILED — Diagnostic Violations Detected"}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                {report.loop_detected
                  ? "Infinite tool call cycle identified! Agent repeatedly invoked identical parameters."
                  : report.tool_recall < 0.8
                  ? "Agent bypassed required security or verification tools in the sequence."
                  : report.efficiency_score < 0.5
                  ? "Agent path severely sub-optimal, taking excess exploratory steps."
                  : "All tool invocations were accurate, efficient, and free of redundant loops."}
              </p>
            </div>

            <span
              className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider shrink-0 ${
                report.passed
                  ? "bg-emerald-600 text-white shadow-lg shadow-emerald-950"
                  : "bg-rose-600 text-white shadow-lg shadow-rose-950"
              }`}
            >
              {report.passed ? "Approved ✓" : "Blocked ✕"}
            </span>
          </div>

          {/* 4 Diagnostic Stat Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Tool Accuracy
              </span>
              <div className="text-2xl font-bold font-mono text-indigo-300">
                {(report.tool_selection_accuracy * 100).toFixed(0)}%
              </div>
              <span className="text-[10px] text-slate-500">
                Sequence match against benchmark
              </span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Precision &amp; Recall
              </span>
              <div className="text-2xl font-bold font-mono text-slate-200">
                {(report.tool_precision * 100).toFixed(0)}% / {(report.tool_recall * 100).toFixed(0)}%
              </div>
              <span className="text-[10px] text-slate-500">
                Tool specificity &amp; coverage
              </span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Loop &amp; Redundancy
              </span>
              <div
                className={`text-2xl font-bold font-mono ${
                  report.loop_detected ? "text-rose-400 animate-pulse" : "text-emerald-400"
                }`}
              >
                {report.loop_detected ? "LOOP DETECTED" : "None (Clean)"}
              </div>
              <span className="text-[10px] text-slate-500">
                {report.redundant_call_count} redundant invocation(s)
              </span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Path Efficiency
              </span>
              <div
                className={`text-2xl font-bold font-mono ${
                  report.efficiency_score >= 0.8
                    ? "text-emerald-400"
                    : report.efficiency_score >= 0.5
                    ? "text-amber-400"
                    : "text-rose-400"
                }`}
              >
                {report.efficiency_score.toFixed(2)}
              </div>
              <span className="text-[10px] text-slate-500">
                {report.total_steps} actual vs {maxOptimalSteps} optimal
              </span>
            </div>
          </div>

          {/* Missing Tools Warning Callout */}
          {report.details.missing_expected_tools && report.details.missing_expected_tools.length > 0 && (
            <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-800/80 text-amber-200 text-xs flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <span className="text-base">⚠️</span>
                <span>
                  <strong>Skipped Required Tools:</strong> The agent failed to execute:{" "}
                  <span className="font-mono underline">
                    {report.details.missing_expected_tools.join(", ")}
                  </span>
                </span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-900 text-amber-200 font-bold uppercase">
                Missing Tools
              </span>
            </div>
          )}
        </div>
      )}

      {/* ── VISUAL EXECUTION TIMELINE FLOW ── */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <span>Execution Timeline &amp; Step Trace</span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
                {trajectory.steps.length} Steps
              </span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Detailed breakdown of agent thought chains, tool input payloads, and observations.
            </p>
          </div>
        </div>

        {/* Goal Node */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-start gap-3">
          <span className="text-xl">🎯</span>
          <div className="space-y-0.5 flex-1">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Agent Goal
            </span>
            <p className="text-sm font-semibold text-slate-100">{trajectory.goal}</p>
          </div>
        </div>

        {/* Step-by-Step Connected Nodes */}
        <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 sm:before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-gradient-to-b before:from-indigo-500 before:via-indigo-500/50 before:to-slate-800">
          {trajectory.steps.map((step, idx) => {
            const stepDiag = report?.step_diagnostics?.find((d) => d.step_number === step.step_number);
            const isLoop = stepDiag?.is_loop_duplicate;
            const isRedundant = stepDiag?.is_redundant;

            return (
              <div key={idx} className="relative group">
                {/* Timeline Node Bullet */}
                <div
                  className={`absolute -left-6 sm:-left-8 top-4 w-6 h-6 rounded-full border flex items-center justify-center text-[10px] font-bold font-mono z-10 ${
                    isLoop
                      ? "bg-rose-600 border-rose-400 text-white animate-pulse"
                      : isRedundant
                      ? "bg-amber-600 border-amber-400 text-white"
                      : "bg-indigo-600 border-indigo-400 text-white shadow-md shadow-indigo-950"
                  }`}
                >
                  {step.step_number}
                </div>

                {/* Step Card */}
                <div
                  className={`p-5 rounded-2xl border transition-all duration-200 space-y-4 ${
                    isLoop
                      ? "bg-rose-950/20 border-rose-700/80 shadow-lg shadow-rose-950/20"
                      : isRedundant
                      ? "bg-amber-950/20 border-amber-700/80"
                      : "bg-slate-950/80 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  {/* Step Header */}
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-200">
                        Step {step.step_number}
                      </span>
                      {step.tool_call && (
                        <span className="px-2 py-0.5 rounded-md bg-indigo-950 border border-indigo-800 text-indigo-300 font-mono text-[11px] font-semibold">
                          ⚙️ {step.tool_call.name}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-[10px]">
                      {isLoop && (
                        <span className="px-2 py-0.5 rounded-full bg-rose-600 text-white font-bold animate-pulse">
                          🔁 REPEATED TOOL CALL (LOOP)
                        </span>
                      )}
                      {isRedundant && !isLoop && (
                        <span className="px-2 py-0.5 rounded-full bg-amber-600 text-white font-bold">
                          ⚠️ REDUNDANT
                        </span>
                      )}
                      {stepDiag?.is_expected_tool === true && (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800">
                          ✓ Expected
                        </span>
                      )}
                      {stepDiag?.is_expected_tool === false && (
                        <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                          Optional
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 1. Thought Node */}
                  {step.thought && (
                    <div className="space-y-1">
                      <div className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                        <span>🧠</span>
                        <span>Thought</span>
                      </div>
                      <p className="text-xs text-slate-300 italic bg-slate-900/60 p-3 rounded-xl border border-slate-800/60">
                        &quot;{step.thought}&quot;
                      </p>
                    </div>
                  )}

                  {/* 2. Action (Tool Call) Node */}
                  {step.tool_call && (
                    <div className="space-y-1">
                      <div className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                        <span>⚙️</span>
                        <span>Action: {step.tool_call.name}</span>
                      </div>
                      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3 font-mono text-xs text-slate-300 overflow-x-auto">
                        <pre className="text-[11px] leading-relaxed">
                          {JSON.stringify(step.tool_call.arguments, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* 3. Observation Node */}
                  {step.observation && (
                    <div className="space-y-1">
                      <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                        <span>👁️</span>
                        <span>Observation</span>
                      </div>
                      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3 font-mono text-xs text-emerald-300/90 overflow-x-auto">
                        <pre className="text-[11px] leading-relaxed whitespace-pre-wrap">
                          {step.observation}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Final Response Card */}
        <div className="p-5 rounded-2xl bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 border border-slate-800 flex items-start gap-4">
          <span className="text-2xl mt-0.5">🏁</span>
          <div className="space-y-1 flex-1">
            <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
              Final Agent Response / Resolution
            </span>
            {trajectory.final_response ? (
              <p className="text-xs text-slate-200 leading-relaxed font-medium">
                {trajectory.final_response}
              </p>
            ) : (
              <p className="text-xs text-rose-400 italic">
                No final response reached (Agent failed or aborted during loop).
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
