"use client";

import React, { useState, useEffect } from "react";
import {
  fetchExperimentMarkdown,
  downloadExperimentExport,
  Experiment,
} from "../lib/api";

interface ExecutiveReportModalProps {
  experiment: Experiment;
  onClose: () => void;
  showToast: (message: string, type: "loading" | "success" | "error") => void;
}

export default function ExecutiveReportModal({
  experiment,
  onClose,
  showToast,
}: ExecutiveReportModalProps) {
  const [markdown, setMarkdown] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function loadMarkdown() {
      try {
        setLoading(true);
        const md = await fetchExperimentMarkdown(experiment.id);
        if (isMounted) setMarkdown(md);
      } catch (err: unknown) {
        showToast(err instanceof Error ? err.message : "Failed to load report", "error");
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadMarkdown();
    return () => {
      isMounted = false;
    };
  }, [experiment.id, showToast]);

  const handleCopyMarkdown = async () => {
    if (!markdown) return;
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      showToast("Markdown report copied to clipboard!", "success");
      setTimeout(() => setCopied(false), 2500);
    } catch {
      showToast("Failed to copy to clipboard", "error");
    }
  };

  const handleDownload = async (format: "csv" | "jsonl" | "markdown") => {
    setDownloading(format);
    try {
      const ext = format === "markdown" ? "md" : format;
      await downloadExperimentExport(
        experiment.id,
        format,
        `ragbench_report_${experiment.name.replace(/\s+/g, "_")}.${ext}`
      );
      showToast(`Downloaded ${format.toUpperCase()} report!`, "success");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Download failed", "error");
    } finally {
      setDownloading(null);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* ── MODAL HEADER ── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/90 shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📊</span>
            <div>
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <span>Executive Evaluation Report</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-mono">
                  {experiment.provider_name.toUpperCase()}
                </span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {experiment.name} • ID: {experiment.id.slice(0, 8)}...
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            ✕
          </button>
        </div>

        {/* ── ACTION BAR ── */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-3 border-b border-slate-800 bg-slate-950/60 shrink-0 text-xs">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopyMarkdown}
              disabled={loading || !markdown}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
                copied
                  ? "bg-emerald-600 text-white"
                  : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm"
              }`}
            >
              <span>{copied ? "✓" : "📋"}</span>
              <span>{copied ? "Copied to Clipboard!" : "Copy Markdown for PR"}</span>
            </button>

            <button
              type="button"
              onClick={handlePrint}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              <span>🖨️</span>
              <span>Print / PDF</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-500 font-mono text-[11px]">Download:</span>
            <button
              type="button"
              onClick={() => handleDownload("markdown")}
              disabled={downloading !== null}
              className="px-2.5 py-1.5 rounded-lg font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            >
              .MD
            </button>
            <button
              type="button"
              onClick={() => handleDownload("csv")}
              disabled={downloading !== null}
              className="px-2.5 py-1.5 rounded-lg font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            >
              .CSV
            </button>
            <button
              type="button"
              onClick={() => handleDownload("jsonl")}
              disabled={downloading !== null}
              className="px-2.5 py-1.5 rounded-lg font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            >
              .JSONL
            </button>
          </div>
        </div>

        {/* ── REPORT CONTENT (PRINTABLE) ── */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-950 font-mono text-xs text-slate-300 leading-relaxed select-text print:bg-white print:text-black">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3 text-slate-500">
              <svg
                className="animate-spin text-indigo-400 w-6 h-6"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <span>Compiling executive report...</span>
            </div>
          ) : (
            <pre className="whitespace-pre-wrap font-sans text-xs sm:text-sm bg-slate-900 border border-slate-800/80 p-5 rounded-xl print:border-none print:bg-transparent">
              {markdown}
            </pre>
          )}
        </div>

        {/* ── MODAL FOOTER ── */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-slate-800 bg-slate-900/90 text-xs text-slate-500 shrink-0">
          <span>Ready to paste directly into GitHub PR descriptions or release notes.</span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
