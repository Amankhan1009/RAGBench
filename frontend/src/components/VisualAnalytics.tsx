"use client";

import React from "react";
import { ParetoAnalyticsResponse, ParetoPoint, Experiment } from "../lib/api";

interface VisualAnalyticsProps {
  analyticsData: ParetoAnalyticsResponse | null;
  loading: boolean;
  selectedCandidateId: string;
  onCandidateChange: (id: string) => void;
  selectedPoint: ParetoPoint | null;
  onSelectPoint: (point: ParetoPoint) => void;
  onRefresh: () => void;
  onNavigateToExperiments: () => void;
  experiments: Experiment[];
}

export default function VisualAnalytics({
  analyticsData,
  loading,
  selectedCandidateId,
  onCandidateChange,
  selectedPoint,
  onSelectPoint,
  onRefresh,
  onNavigateToExperiments,
  experiments,
}: VisualAnalyticsProps) {
  const [hoveredPointId, setHoveredPointId] = React.useState<string | null>(null);

  // If no experiments evaluated yet
  if (!analyticsData || analyticsData.total_experiments === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-3xl">
          📊
        </div>
        <div className="space-y-1">
          <h3 className="text-xl font-bold text-slate-100">
            Interactive Visual Analytics &amp; Pareto Frontier
          </h3>
          <p className="text-sm text-slate-400 max-w-lg mx-auto leading-relaxed">
            Run evaluation experiments in your workspace to unlock the 2D Pareto Efficiency Frontier,
            Multi-Dimensional Radar Spider Chart, and Quality Trendlines.
          </p>
        </div>
        <div className="pt-2">
          <button
            onClick={onNavigateToExperiments}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-lg shadow-indigo-600/30 transition"
          >
            Run Your First Evaluation →
          </button>
        </div>
      </div>
    );
  }

  const { points, pareto_frontier, radar_comparison, trends } = analyticsData;

  // Best model by quality
  const highestQuality = [...points].sort((a, b) => b.composite_score - a.composite_score)[0];
  // Fastest model by latency
  const lowestLatency = [...points].sort((a, b) => a.latency_ms - b.latency_ms)[0];

  // ── SCATTER PLOT MATH ──────────────────────────────────────────────────────
  const svgWidth = 620;
  const svgHeight = 300;
  const padLeft = 60;
  const padRight = 30;
  const padTop = 30;
  const padBottom = 45;
  const plotW = svgWidth - padLeft - padRight;
  const plotH = svgHeight - padTop - padBottom;

  const maxLatency = Math.max(
    1000,
    Math.ceil(Math.max(...points.map((p) => p.latency_ms || 0)) * 1.25)
  );

  const getX = (lat: number) => padLeft + (Math.max(0, lat) / maxLatency) * plotW;
  const getY = (score: number) => padTop + (1.0 - Math.max(0, Math.min(1.0, score))) * plotH;

  // Sorted Pareto frontier points for polyline
  const sortedFrontier = [...pareto_frontier].sort((a, b) => a.latency_ms - b.latency_ms);
  const frontierPolyline = sortedFrontier.map((p) => `${getX(p.latency_ms)},${getY(p.composite_score)}`).join(" ");

  // ── RADAR CHART MATH ───────────────────────────────────────────────────────
  const radarSize = 300;
  const rCenter = 150;
  const maxR = 95;
  const radarDims = radar_comparison || [];
  const numDims = radarDims.length || 5;

  const getRadarPoint = (score: number, index: number) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / numDims;
    const r = Math.max(0.05, Math.min(1.0, score)) * maxR;
    return {
      x: rCenter + r * Math.cos(angle),
      y: rCenter + r * Math.sin(angle),
    };
  };

  const getAxisEnd = (index: number) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / numDims;
    return {
      x: rCenter + maxR * Math.cos(angle),
      y: rCenter + maxR * Math.sin(angle),
      labelX: rCenter + (maxR + 24) * Math.cos(angle),
      labelY: rCenter + (maxR + 18) * Math.sin(angle),
    };
  };

  const candidatePolygon = radarDims
    .map((d, i) => {
      const pt = getRadarPoint(d.candidate_score, i);
      return `${pt.x},${pt.y}`;
    })
    .join(" ");

  const baselinePolygon = radarDims
    .map((d, i) => {
      const pt = getRadarPoint(d.baseline_score, i);
      return `${pt.x},${pt.y}`;
    })
    .join(" ");

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* ── KPI HIGHLIGHT CARDS ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col justify-between">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Total Evaluated Runs
          </div>
          <div className="flex items-baseline gap-2 mt-3">
            <span className="text-3xl font-extrabold text-slate-100">
              {analyticsData.total_experiments}
            </span>
            <span className="text-xs text-slate-500">runs in workspace</span>
          </div>
        </div>

        <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col justify-between">
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center justify-between">
            <span>Pareto Optimal Models</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          </div>
          <div className="flex items-baseline gap-2 mt-3">
            <span className="text-3xl font-extrabold text-emerald-400">
              {pareto_frontier.length}
            </span>
            <span className="text-xs text-slate-500">
              ({Math.round((pareto_frontier.length / points.length) * 100)}% efficiency rate)
            </span>
          </div>
        </div>

        <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col justify-between">
          <div className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
            Highest Quality Model
          </div>
          <div className="mt-3">
            <div className="text-sm font-bold text-slate-100 truncate" title={highestQuality?.name}>
              {highestQuality?.name || "N/A"}
            </div>
            <div className="text-xs text-indigo-400 font-semibold mt-0.5">
              {(highestQuality?.composite_score ?? 0).toFixed(4)} composite score
            </div>
          </div>
        </div>

        <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col justify-between">
          <div className="text-xs font-semibold uppercase tracking-wider text-amber-400">
            Lowest Latency Model
          </div>
          <div className="mt-3">
            <div className="text-sm font-bold text-slate-100 truncate" title={lowestLatency?.name}>
              {lowestLatency?.name || "N/A"}
            </div>
            <div className="text-xs text-amber-400 font-semibold mt-0.5">
              {(lowestLatency?.latency_ms ?? 0).toFixed(1)} ms avg response
            </div>
          </div>
        </div>
      </div>

      {/* ── PARETO FRONTIER SCATTER PLOT & INSPECTOR ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Scatter Plot View */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg">🎯</span>
                <h3 className="text-lg font-bold text-slate-100">Pareto Frontier Scatter Plot</h3>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Visualizing quality trade-offs vs. inference latency. Click any point to inspect detailed metrics.
              </p>
            </div>
            <button
              onClick={onRefresh}
              className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition self-start sm:self-auto"
            >
              ↻ Refresh Plot
            </button>
          </div>

          <div className="overflow-x-auto">
            <svg
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              className="w-full h-auto max-h-[350px] overflow-visible select-none"
            >
              <defs>
                <linearGradient id="paretoGrad" x1="0%" y1="100%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#10b981" />
                  <stop offset="100%" stopColor="#6366f1" />
                </linearGradient>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Gridlines & Y Axis */}
              {[0.0, 0.25, 0.5, 0.75, 1.0].map((val) => (
                <g key={val}>
                  <line
                    x1={padLeft}
                    y1={getY(val)}
                    x2={svgWidth - padRight}
                    y2={getY(val)}
                    stroke="#1e293b"
                    strokeDasharray={val === 0 || val === 1 ? "none" : "3 3"}
                  />
                  <text
                    x={padLeft - 10}
                    y={getY(val) + 4}
                    textAnchor="end"
                    className="text-[10px] fill-slate-500 font-mono"
                  >
                    {val.toFixed(2)}
                  </text>
                </g>
              ))}

              {/* X Axis Gridlines */}
              {[0, Math.round(maxLatency * 0.33), Math.round(maxLatency * 0.66), maxLatency].map(
                (lat) => (
                  <g key={lat}>
                    <line
                      x1={getX(lat)}
                      y1={padTop}
                      x2={getX(lat)}
                      y2={svgHeight - padBottom}
                      stroke="#1e293b"
                      strokeDasharray="3 3"
                    />
                    <text
                      x={getX(lat)}
                      y={svgHeight - padBottom + 16}
                      textAnchor="middle"
                      className="text-[10px] fill-slate-500 font-mono"
                    >
                      {lat}ms
                    </text>
                  </g>
                )
              )}

              {/* Axis Labels */}
              <text
                x={padLeft + plotW / 2}
                y={svgHeight - 8}
                textAnchor="middle"
                className="text-[11px] fill-slate-400 font-semibold"
              >
                Inference Latency (ms) [Faster ←]
              </text>
              <text
                transform={`rotate(-90) translate(-${padTop + plotH / 2}, 16)`}
                textAnchor="middle"
                className="text-[11px] fill-slate-400 font-semibold"
              >
                Composite Score [Better ↑]
              </text>

              {/* Connected Pareto Frontier Curve */}
              {sortedFrontier.length > 1 && (
                <polyline
                  points={frontierPolyline}
                  fill="none"
                  stroke="url(#paretoGrad)"
                  strokeWidth="2.5"
                  strokeDasharray="4 2"
                  filter="url(#glow)"
                />
              )}

              {/* Scatter Points */}
              {points.map((p) => {
                const cx = getX(p.latency_ms);
                const cy = getY(p.composite_score);
                const isSelected = selectedPoint?.experiment_id === p.experiment_id;
                const isHovered = hoveredPointId === p.experiment_id;

                if (p.is_baseline) {
                  const size = isSelected ? 9.5 : isHovered ? 8.5 : 7;
                  return (
                    <g
                      key={p.experiment_id}
                      onClick={() => onSelectPoint(p)}
                      onMouseEnter={() => setHoveredPointId(p.experiment_id)}
                      onMouseLeave={() => setHoveredPointId(null)}
                      className="cursor-pointer"
                    >
                      {/* Generous invisible hit target for effortless clicking */}
                      <circle cx={cx} cy={cy} r="16" fill="transparent" />
                      <polygon
                        points={`${cx},${cy - size} ${cx + size},${cy} ${cx},${cy + size} ${cx - size},${cy}`}
                        fill="#f59e0b"
                        stroke="#ffffff"
                        strokeWidth={isSelected || isHovered ? "2.5" : "1.5"}
                        className="transition-all duration-150"
                      />
                      <title>{`${p.name} (Active Baseline)\nScore: ${p.composite_score.toFixed(4)}\nLatency: ${p.latency_ms.toFixed(1)}ms`}</title>
                    </g>
                  );
                }

                if (p.is_pareto_optimal) {
                  const r = isSelected ? 9 : isHovered ? 8 : 6.5;
                  return (
                    <g
                      key={p.experiment_id}
                      onClick={() => onSelectPoint(p)}
                      onMouseEnter={() => setHoveredPointId(p.experiment_id)}
                      onMouseLeave={() => setHoveredPointId(null)}
                      className="cursor-pointer"
                    >
                      {/* Subtle breathing halo for Pareto optimality (fixed origin, pointer-events-none) */}
                      <circle
                        cx={cx}
                        cy={cy}
                        r={isSelected ? 16 : isHovered ? 14 : 12}
                        fill="rgba(16, 185, 129, 0.12)"
                        stroke="#10b981"
                        strokeWidth="1.2"
                        strokeDasharray="3 3"
                        className="pointer-events-none transition-all duration-200"
                      />
                      {/* Main solid Pareto circle */}
                      <circle
                        cx={cx}
                        cy={cy}
                        r={r}
                        fill="#10b981"
                        stroke="#ffffff"
                        strokeWidth={isSelected || isHovered ? "2.5" : "1.5"}
                        className="transition-all duration-150"
                      />
                      {/* Generous invisible hit target */}
                      <circle cx={cx} cy={cy} r="16" fill="transparent" />
                      <title>{`${p.name} (Pareto Optimal)\nScore: ${p.composite_score.toFixed(4)}\nLatency: ${p.latency_ms.toFixed(1)}ms`}</title>
                    </g>
                  );
                }

                const r = isSelected ? 7.5 : isHovered ? 6.5 : 5;
                return (
                  <g
                    key={p.experiment_id}
                    onClick={() => onSelectPoint(p)}
                    onMouseEnter={() => setHoveredPointId(p.experiment_id)}
                    onMouseLeave={() => setHoveredPointId(null)}
                    className="cursor-pointer"
                  >
                    {/* Generous invisible hit target */}
                    <circle cx={cx} cy={cy} r="14" fill="transparent" />
                    <circle
                      cx={cx}
                      cy={cy}
                      r={r}
                      fill={isHovered ? "#475569" : "#334155"}
                      stroke={isHovered ? "#ffffff" : "#94a3b8"}
                      strokeWidth={isSelected || isHovered ? "2" : "1.5"}
                      className="transition-all duration-150"
                    />
                    <title>{`${p.name}\nScore: ${p.composite_score.toFixed(4)}\nLatency: ${p.latency_ms.toFixed(1)}ms`}</title>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Chart Legend */}
          <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-slate-400 pt-3 border-t border-slate-800">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-emerald-500 border border-white" />
              <span className="text-slate-300 font-medium">Pareto Optimal Frontier</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rotate-45 bg-amber-500 border border-white" />
              <span className="text-slate-300 font-medium">Active Baseline</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-600 border border-slate-400" />
              <span>Standard Run</span>
            </div>
          </div>
        </div>

        {/* Selected Model Detailed Inspector */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl flex flex-col justify-between space-y-4">
          {selectedPoint ? (
            <div className="space-y-4">
              <div className="flex items-start justify-between gap-2 pb-3 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-base font-bold text-slate-100 truncate max-w-[200px]" title={selectedPoint.name}>
                      {selectedPoint.name}
                    </h4>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {selectedPoint.provider_name.toUpperCase()} • <span className="font-mono text-indigo-300">{selectedPoint.model_name}</span>
                  </div>
                </div>

                <div className="flex flex-col items-end gap-1">
                  {selectedPoint.is_pareto_optimal && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 border border-emerald-500/40 text-emerald-400">
                      ★ Pareto Frontier
                    </span>
                  )}
                  {selectedPoint.is_baseline && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 border border-amber-500/40 text-amber-400">
                      Active Baseline
                    </span>
                  )}
                </div>
              </div>

              {/* Metric Highlights */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-[11px] text-slate-500 uppercase font-semibold">Composite Score</div>
                  <div className="text-xl font-extrabold text-indigo-400 mt-1">
                    {selectedPoint.composite_score.toFixed(4)}
                  </div>
                </div>
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-[11px] text-slate-500 uppercase font-semibold">Avg Latency</div>
                  <div className="text-xl font-extrabold text-slate-200 mt-1">
                    {selectedPoint.latency_ms.toFixed(1)} <span className="text-xs font-normal text-slate-400">ms</span>
                  </div>
                </div>
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-[11px] text-slate-500 uppercase font-semibold">Avg Tokens</div>
                  <div className="text-base font-bold text-slate-200 mt-1">
                    {selectedPoint.total_tokens} <span className="text-xs font-normal text-slate-400">tokens</span>
                  </div>
                </div>
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-[11px] text-slate-500 uppercase font-semibold">Est Cost / Query</div>
                  <div className="text-base font-bold text-slate-200 mt-1 font-mono">
                    ${selectedPoint.cost_usd.toFixed(5)}
                  </div>
                </div>
              </div>

              {/* Detailed Metrics Breakdown */}
              <div className="space-y-2 pt-2">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Quality Dimension Breakdown
                </div>
                <div className="bg-slate-950 rounded-xl border border-slate-800 overflow-hidden divide-y divide-slate-800/80 text-xs">
                  {Object.entries(selectedPoint.metrics).length > 0 ? (
                    Object.entries(selectedPoint.metrics).map(([metric, val]) => (
                      <div key={metric} className="p-2.5 flex items-center justify-between">
                        <span className="text-slate-300 capitalize">{metric.replace(/_/g, " ")}</span>
                        <span className="font-mono font-semibold text-indigo-400">
                          {typeof val === "number" ? val.toFixed(4) : String(val)}
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="p-3 text-center text-slate-500 text-xs">
                      No per-sample metrics recorded
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center p-8 text-slate-500 text-sm">
              Select any point on the scatter plot to inspect its detailed evaluation metrics.
            </div>
          )}

          <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-500">
            Click on any circle or diamond on the scatter plot to compare efficiency.
          </div>
        </div>
      </div>

      {/* ── MULTI-DIMENSIONAL RADAR & HISTORICAL TRENDS ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Radar Spider Chart */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg">🕸️</span>
                <h3 className="text-lg font-bold text-slate-100">5-Axis Metric Radar Chart</h3>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Candidate vs. Active Baseline across 5 normalized operational dimensions.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={selectedCandidateId}
                onChange={(e) => onCandidateChange(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-200 outline-none"
              >
                <option value="">Compare Candidate...</option>
                {experiments
                  .filter((e) => !e.is_baseline)
                  .map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.name}
                    </option>
                  ))}
              </select>
            </div>
          </div>

          {radar_comparison && radar_comparison.length > 0 ? (
            <div className="flex flex-col items-center">
              <svg viewBox={`0 0 ${radarSize} ${radarSize}`} className="w-full max-w-[280px] overflow-visible">
                {/* Concentric rings */}
                {[0.33, 0.66, 1.0].map((level) => {
                  const ringPoints = Array.from({ length: numDims })
                    .map((_, i) => {
                      const angle = -Math.PI / 2 + (i * 2 * Math.PI) / numDims;
                      const r = level * maxR;
                      return `${rCenter + r * Math.cos(angle)},${rCenter + r * Math.sin(angle)}`;
                    })
                    .join(" ");
                  return (
                    <polygon
                      key={level}
                      points={ringPoints}
                      fill="none"
                      stroke="#334155"
                      strokeWidth="1"
                      strokeDasharray={level < 1 ? "2 2" : "none"}
                    />
                  );
                })}

                {/* Spokes & Axis labels */}
                {Array.from({ length: numDims }).map((_, i) => {
                  const end = getAxisEnd(i);
                  const dimName = radarDims[i]?.dimension || `Dim ${i + 1}`;
                  return (
                    <g key={i}>
                      <line x1={rCenter} y1={rCenter} x2={end.x} y2={end.y} stroke="#334155" strokeWidth="1" />
                      <text
                        x={end.labelX}
                        y={end.labelY}
                        textAnchor="middle"
                        className="text-[9px] fill-slate-400 font-semibold select-none"
                      >
                        {dimName}
                      </text>
                    </g>
                  );
                })}

                {/* Baseline Polygon (Amber, dashed outline) */}
                <polygon
                  points={baselinePolygon}
                  fill="rgba(245, 158, 11, 0.25)"
                  stroke="#f59e0b"
                  strokeWidth="2.5"
                  strokeDasharray="6 3"
                />

                {/* Candidate Polygon (Indigo, solid outline) */}
                <polygon
                  points={candidatePolygon}
                  fill="rgba(99, 102, 241, 0.30)"
                  stroke="#6366f1"
                  strokeWidth="2"
                />

                {/* Vertex Markers */}
                {radarDims.map((d, i) => {
                  const basePt = getRadarPoint(d.baseline_score, i);
                  const candPt = getRadarPoint(d.candidate_score, i);
                  return (
                    <g key={i}>
                      {/* Baseline vertex (Amber diamond) */}
                      <polygon
                        points={`${basePt.x},${basePt.y - 4} ${basePt.x + 4},${basePt.y} ${basePt.x},${basePt.y + 4} ${basePt.x - 4},${basePt.y}`}
                        fill="#f59e0b"
                        stroke="#ffffff"
                        strokeWidth="1"
                      />
                      {/* Candidate vertex (Indigo dot) */}
                      <circle
                        cx={candPt.x}
                        cy={candPt.y}
                        r="3.5"
                        fill="#6366f1"
                        stroke="#ffffff"
                        strokeWidth="1"
                      />
                    </g>
                  );
                })}
              </svg>

              {/* Legend & Scores Table */}
              <div className="w-full mt-4 space-y-3">
                {/* Identical Scores Callout if all deltas are 0 */}
                {radarDims.every((d) => Math.abs(d.candidate_score - d.baseline_score) < 0.0001) && (
                  <div className="text-center p-2 rounded-lg bg-indigo-950/60 border border-indigo-800 text-[11px] text-indigo-300">
                    ℹ️ <strong>Identical Performance</strong>: Both runs achieved 100% identical scores across all 5 dimensions (Deltas = +0.000), so the polygons overlap directly.
                  </div>
                )}

                <div className="flex items-center justify-center gap-6 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded bg-indigo-500/50 border border-indigo-400" />
                    <span className="text-slate-200 font-medium">
                      Candidate: {analyticsData.candidate_name || "Active Candidate"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rotate-45 bg-amber-500/50 border border-amber-400" />
                    <span className="text-slate-200 font-medium">
                      Baseline: {analyticsData.baseline_name || "Active Baseline"}
                    </span>
                  </div>
                </div>

                <div className="overflow-x-auto rounded-xl border border-slate-800 text-xs">
                  <table className="w-full text-left">
                    <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="p-2.5">Dimension</th>
                        <th className="p-2.5">Candidate</th>
                        <th className="p-2.5">Baseline</th>
                        <th className="p-2.5">Delta</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {radarDims.map((d) => {
                        const delta = d.candidate_score - d.baseline_score;
                        return (
                          <tr key={d.dimension}>
                            <td className="p-2.5 text-slate-300 font-medium">{d.dimension}</td>
                            <td className="p-2.5 text-indigo-400 font-mono">{d.candidate_score.toFixed(3)}</td>
                            <td className="p-2.5 text-amber-400 font-mono">{d.baseline_score.toFixed(3)}</td>
                            <td className={`p-2.5 font-mono font-semibold ${delta >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                              {delta >= 0 ? `+${delta.toFixed(3)}` : delta.toFixed(3)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl space-y-2">
              <div className="text-amber-400 font-medium text-sm">No Active Baseline Found</div>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Set one of your experiments as the baseline in the <strong>Experiments &amp; Runs</strong> tab to enable the 5-axis Radar comparison.
              </p>
            </div>
          )}
        </div>

        {/* Historical Quality Trends */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl space-y-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg">📈</span>
              <h3 className="text-lg font-bold text-slate-100">Quality Regression Trendline</h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Chronological evolution of composite quality scores across workspace runs.
            </p>
          </div>

          <div className="overflow-x-auto">
            <svg viewBox="0 0 500 240" className="w-full h-auto max-h-[260px] overflow-visible select-none">
              {/* Y Gridlines */}
              {[0.0, 0.5, 1.0].map((val) => {
                const y = 30 + (1.0 - val) * 160;
                return (
                  <g key={val}>
                    <line x1="40" y1={y} x2="480" y2={y} stroke="#1e293b" strokeDasharray="3 3" />
                    <text x="32" y={y + 3} textAnchor="end" className="text-[9px] fill-slate-500 font-mono">
                      {val.toFixed(1)}
                    </text>
                  </g>
                );
              })}

              {/* Trend Polyline */}
              {trends.length > 1 && (
                <polyline
                  points={trends
                    .map((t, idx) => {
                      const x = 50 + (idx / (trends.length - 1)) * 410;
                      const y = 30 + (1.0 - Math.max(0, Math.min(1.0, t.composite_score))) * 160;
                      return `${x},${y}`;
                    })
                    .join(" ")}
                  fill="none"
                  stroke="#38bdf8"
                  strokeWidth="2.5"
                />
              )}

              {/* Trend Dots */}
              {trends.map((t, idx) => {
                const x = trends.length === 1 ? 250 : 50 + (idx / (trends.length - 1)) * 410;
                const y = 30 + (1.0 - Math.max(0, Math.min(1.0, t.composite_score))) * 160;
                return (
                  <g key={t.experiment_id} className="cursor-pointer group">
                    <circle
                      cx={x}
                      cy={y}
                      r="5"
                      fill={t.is_baseline ? "#f59e0b" : "#38bdf8"}
                      stroke="#0f172a"
                      strokeWidth="2"
                    />
                    <text
                      x={x}
                      y={210}
                      textAnchor="middle"
                      className="text-[8px] fill-slate-500 font-mono"
                    >
                      {t.timestamp}
                    </text>
                    <title>{`${t.name}\nScore: ${t.composite_score.toFixed(4)}\nLatency: ${t.latency_ms}ms`}</title>
                  </g>
                );
              })}
            </svg>
          </div>

          <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span>Tracking quality progression over {trends.length} evaluation milestone(s).</span>
            <span className="text-cyan-400 font-medium">● Trend Curve</span>
          </div>
        </div>
      </div>
    </div>
  );
}

