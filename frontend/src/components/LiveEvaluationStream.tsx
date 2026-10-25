"use client";

import React, { useMemo } from "react";
import {
  StreamCompleteEvent,
  StreamSampleEvent,
  StreamStartEvent,
} from "../lib/api";

interface LiveEvaluationStreamProps {
  startData: StreamStartEvent | null;
  samples: StreamSampleEvent[];
  completeData: StreamCompleteEvent | null;
  error: string | null;
  isStreaming: boolean;
  onDismiss: () => void;
  onViewAnalytics?: () => void;
}

export default function LiveEvaluationStream({
  startData,
  samples,
  completeData,
  error,
  isStreaming,
  onDismiss,
  onViewAnalytics,
}: LiveEvaluationStreamProps) {
  const totalSamples = startData?.total_samples || samples.length || 1;
  const currentCount = samples.length;
  const progressPct = completeData
    ? 100
    : Math.min(100, Math.round((currentCount / totalSamples) * 100));

  // Dynamic ETA calculation based on rolling average latency
  const etaSeconds = useMemo(() => {
    if (!isStreaming || currentCount === 0 || currentCount >= totalSamples) {
      return 0;
    }
    const totalLatency = samples.reduce((acc, s) => acc + s.latency_ms, 0);
    const avgLatencyMs = totalLatency / currentCount;
    const remainingSamples = totalSamples - currentCount;
    return Math.max(1, Math.round((remainingSamples * avgLatencyMs) / 1000));
  }, [isStreaming, currentCount, totalSamples, samples]);

  const latestSample = samples[samples.length - 1];
  const totalCost = samples.reduce((acc, s) => acc + (s.cost_usd || 0), 0);
  const totalTokens = samples.reduce((acc, s) => acc + (s.total_tokens || 0), 0);
  const passCount = samples.filter((s) => s.passed).length;

  return (
    <div className="bg-slate-900/90 border border-indigo-500/30 rounded-2xl p-6 shadow-2xl backdrop-blur-sm space-y-6 animate-in fade-in duration-300">
      {/* ── HEADER ── */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            {isStreaming ? (
              <span className="flex h-3 w-3 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
              </span>
            ) : completeData ? (
              <span className="text-base">✅</span>
            ) : (
              <span className="text-base">⚠️</span>
            )}
            <h3 className="text-base font-bold text-slate-100">
              {isStreaming
                ? "Live Evaluation Stream (Server-Sent Events)"
                : completeData
                ? "Evaluation Completed Successfully"
                : "Evaluation Stopped"}
            </h3>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              v2.0 SSE
            </span>
          </div>

          <div className="text-xs text-slate-400">
            {startData ? (
              <>
                Experiment: <strong className="text-slate-200">{startData.experiment_name}</strong> • Provider:{" "}
                <strong className="text-slate-200 uppercase">{startData.provider_name}</strong> (
                <span className="font-mono text-indigo-300">{startData.model_name}</span>)
              </>
            ) : (
              "Initializing streaming connection..."
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {completeData && onViewAnalytics && (
            <button
              onClick={onViewAnalytics}
              className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition shadow-lg shadow-indigo-600/30"
            >
              Inspect Pareto Frontier →
            </button>
          )}
          {!isStreaming && (
            <button
              onClick={onDismiss}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
            >
              Close
            </button>
          )}
        </div>
      </div>

      {/* ── ERROR ALERT ── */}
      {error && (
        <div className="p-3.5 rounded-xl bg-rose-500/15 border border-rose-500/40 text-xs text-rose-300 flex items-start gap-2.5">
          <span className="text-base">🚨</span>
          <div>
            <strong>Streaming Error:</strong> {error}
          </div>
        </div>
      )}

      {/* ── PROGRESS BAR ── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-300 font-medium">
            {completeData
              ? `Completed all ${totalSamples} samples`
              : `Sample ${currentCount} of ${totalSamples}`}
          </span>
          <div className="flex items-center gap-3">
            {isStreaming && etaSeconds > 0 && (
              <span className="text-amber-400 font-mono text-[11px] animate-pulse">
                ETA: ~{etaSeconds}s remaining
              </span>
            )}
            <span className="font-mono font-bold text-indigo-400">{progressPct}%</span>
          </div>
        </div>

        <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden border border-slate-800 p-0.5">
          <div
            className={`h-full rounded-full transition-all duration-300 ${
              completeData
                ? "bg-emerald-500"
                : "bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400"
            }`}
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* ── LIVE KPI METERS ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 bg-slate-950 rounded-xl border border-slate-800/80">
          <div className="text-[10px] uppercase font-semibold text-slate-500">Latest Latency</div>
          <div className="text-lg font-extrabold text-slate-200 mt-0.5">
            {latestSample ? `${latestSample.latency_ms.toFixed(1)}` : "--"}{" "}
            <span className="text-[10px] text-slate-500 font-normal">ms</span>
          </div>
        </div>

        <div className="p-3 bg-slate-950 rounded-xl border border-slate-800/80">
          <div className="text-[10px] uppercase font-semibold text-slate-500">Total Tokens</div>
          <div className="text-lg font-extrabold text-indigo-400 mt-0.5">
            {totalTokens.toLocaleString()}{" "}
            <span className="text-[10px] text-slate-500 font-normal">tokens</span>
          </div>
        </div>

        <div className="p-3 bg-slate-950 rounded-xl border border-slate-800/80">
          <div className="text-[10px] uppercase font-semibold text-slate-500">Estimated Cost</div>
          <div className="text-lg font-extrabold text-emerald-400 font-mono mt-0.5">
            ${totalCost.toFixed(5)}
          </div>
        </div>

        <div className="p-3 bg-slate-950 rounded-xl border border-slate-800/80">
          <div className="text-[10px] uppercase font-semibold text-slate-500">Quality Checks</div>
          <div className="text-lg font-extrabold text-slate-200 mt-0.5">
            <span className="text-emerald-400">{passCount}</span>
            <span className="text-slate-500 text-sm"> / {currentCount || 0}</span>
          </div>
        </div>
      </div>

      {/* ── LIVE FEED OF COMPLETED SAMPLES ── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-semibold uppercase tracking-wider text-[10px]">
            Live Sample Execution Feed ({samples.length})
          </span>
          {isStreaming && (
            <span className="text-[11px] text-indigo-400 font-medium animate-pulse flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
              Streaming per-sample metrics...
            </span>
          )}
        </div>

        <div className="max-h-56 overflow-y-auto space-y-2 pr-1 rounded-xl">
          {samples.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
              Waiting for first evaluated dataset query...
            </div>
          ) : (
            samples
              .slice()
              .reverse()
              .map((s) => (
                <div
                  key={s.sample_index}
                  className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl text-xs space-y-1.5 transition hover:border-slate-700"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-300 text-[10px] font-bold flex items-center justify-center">
                        #{s.sample_index}
                      </span>
                      <span className="font-medium text-slate-200 truncate max-w-[280px] sm:max-w-md">
                        {s.query}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span className="font-mono text-[10px] text-slate-400">
                        {s.latency_ms.toFixed(0)}ms
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          s.passed
                            ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                            : "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                        }`}
                      >
                        {s.passed ? "PASS" : "WARN"}
                      </span>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-400 line-clamp-1 italic font-mono bg-slate-900/60 p-1.5 rounded border border-slate-800/60">
                    &ldquo;{s.response_snippet}&rdquo;
                  </p>
                </div>
              ))
          )}
        </div>
      </div>
    </div>
  );
}
