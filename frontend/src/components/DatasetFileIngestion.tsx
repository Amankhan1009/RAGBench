"use client";

import React, { useState, useRef } from "react";
import { ingestDataset, Dataset } from "../lib/api";

interface DatasetFileIngestionProps {
  onDatasetCreated: (datasetId: string) => void;
  showToast: (message: string, type: "loading" | "success" | "error") => void;
}

const SAMPLE_CSV = `query,expected_output,contexts,category
"What is the maximum return window?","Customers can return items within 30 days of delivery.","['Delivery receipt confirms the 30-day return eligibility window.']","returns"
"Are expedited shipping fees refundable?","No, expedited shipping fees are non-refundable once dispatched.","['Standard priority express shipping surcharges cannot be credited back.']","shipping"
"How can I track my international shipment?","Tracking numbers are sent via encrypted email upon carrier dispatch.","['Encrypted tracking codes are dispatched automatically via email.']","tracking"`;

const SAMPLE_JSONL = `{"query": "What is the maximum return window?", "expected_output": "Customers can return items within 30 days of delivery.", "contexts": ["Delivery receipt confirms the 30-day return eligibility window."], "category": "returns"}
{"query": "Are expedited shipping fees refundable?", "expected_output": "No, expedited shipping fees are non-refundable once dispatched.", "contexts": ["Standard priority express shipping surcharges cannot be credited back."], "category": "shipping"}
{"query": "How can I track my international shipment?", "expected_output": "Tracking numbers are sent via encrypted email upon carrier dispatch.", "contexts": ["Encrypted tracking codes are dispatched automatically via email."], "category": "tracking"}`;

export default function DatasetFileIngestion({
  onDatasetCreated,
  showToast,
}: DatasetFileIngestionProps) {
  const [file, setFile] = useState<File | null>(null);
  const [fileContent, setFileContent] = useState<string>("");
  const [fileFormat, setFileFormat] = useState<"csv" | "jsonl" | "json">("csv");
  const [detectedHeaders, setDetectedHeaders] = useState<string[]>([]);
  const [previewRows, setPreviewRows] = useState<Record<string, string>[]>([]);

  // Column mapping states
  const [queryCol, setQueryCol] = useState<string>("");
  const [outputCol, setOutputCol] = useState<string>("");
  const [contextCol, setContextCol] = useState<string>("");

  // Dataset metadata
  const [datasetName, setDatasetName] = useState<string>("");
  const [datasetDesc, setDatasetDesc] = useState<string>("");
  const [ingesting, setIngesting] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDownloadSample = (format: "csv" | "jsonl") => {
    const content = format === "csv" ? SAMPLE_CSV : SAMPLE_JSONL;
    const blob = new Blob([content], { type: format === "csv" ? "text/csv" : "application/x-ndjson" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ragbench_sample_template.${format}`;
    document.body.appendChild(a);
    a.click();
    URL.revokeObjectURL(url);
    document.body.removeChild(a);
    showToast(`Sample ${format.toUpperCase()} template downloaded!`, "success");
  };

  const processFile = (selectedFile: File) => {
    const ext = selectedFile.name.split(".").pop()?.toLowerCase() || "";
    let fmt: "csv" | "jsonl" | "json" = "csv";
    if (ext === "jsonl") fmt = "jsonl";
    else if (ext === "json") fmt = "json";
    else fmt = "csv";

    setFileFormat(fmt);
    setFile(selectedFile);

    const baseName = selectedFile.name.replace(/\.[^/.]+$/, "").replace(/[_-]/g, " ");
    const formattedName = baseName.charAt(0).toUpperCase() + baseName.slice(1);
    setDatasetName(formattedName);
    setDatasetDesc(`Ingested from ${selectedFile.name} (${(selectedFile.size / 1024).toFixed(1)} KB)`);

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = (e.target?.result as string) || "";
      setFileContent(text);
      inspectContent(text, fmt);
    };
    reader.readAsText(selectedFile);
  };

  const inspectContent = (text: string, fmt: "csv" | "jsonl" | "json") => {
    if (!text.trim()) return;

    if (fmt === "csv") {
      const lines = text.trim().split("\n");
      if (lines.length > 0) {
        // Simple CSV splitter handling quoted cells
        const parseRow = (line: string) => {
          const re = /(?:,|\n|^)("(?:(?:"")*[^"]*)*"|[^",\n]*|(?:\n|$))/g;
          const row: string[] = [];
          let match: RegExpExecArray | null;
          while ((match = re.exec(line)) !== null) {
            let val = match[1] || "";
            if (val.startsWith('"') && val.endsWith('"')) {
              val = val.substring(1, val.length - 1).replace(/""/g, '"');
            }
            row.push(val.trim());
            if (re.lastIndex >= line.length) break;
          }
          return row;
        };

        const headers = parseRow(lines[0]);
        setDetectedHeaders(headers);

        const previews: Record<string, string>[] = [];
        for (let i = 1; i < Math.min(lines.length, 5); i++) {
          if (!lines[i].trim()) continue;
          const vals = parseRow(lines[i]);
          const rowObj: Record<string, string> = {};
          headers.forEach((h, idx) => {
            rowObj[h] = vals[idx] || "";
          });
          previews.push(rowObj);
        }
        setPreviewRows(previews);

        // Auto-detect matches
        const lowerHeaders = headers.map((h) => h.toLowerCase().trim());
        const qIdx = lowerHeaders.findIndex((h) =>
          ["query", "question", "prompt", "input", "text"].includes(h)
        );
        if (qIdx !== -1) setQueryCol(headers[qIdx]);
        else if (headers.length > 0) setQueryCol(headers[0]);

        const oIdx = lowerHeaders.findIndex((h) =>
          ["expected_output", "ground_truth", "answer", "target", "reference", "gold"].includes(h)
        );
        if (oIdx !== -1) setOutputCol(headers[oIdx]);

        const cIdx = lowerHeaders.findIndex((h) =>
          ["contexts", "context", "passages", "documents", "chunks"].includes(h)
        );
        if (cIdx !== -1) setContextCol(headers[cIdx]);
      }
    } else {
      // JSON or JSONL
      let sampleObj: Record<string, unknown> | null = null;
      if (fmt === "jsonl") {
        const firstLine = text.trim().split("\n")[0];
        try {
          sampleObj = JSON.parse(firstLine);
        } catch {}
      } else {
        try {
          const arr = JSON.parse(text);
          if (Array.isArray(arr) && arr.length > 0) sampleObj = arr[0];
        } catch {}
      }

      if (sampleObj && typeof sampleObj === "object") {
        const keys = Object.keys(sampleObj);
        setDetectedHeaders(keys);

        const lowerKeys = keys.map((k) => k.toLowerCase().trim());
        const qIdx = lowerKeys.findIndex((k) =>
          ["query", "question", "prompt", "input", "text"].includes(k)
        );
        if (qIdx !== -1) setQueryCol(keys[qIdx]);
        else if (keys.length > 0) setQueryCol(keys[0]);

        const oIdx = lowerKeys.findIndex((k) =>
          ["expected_output", "ground_truth", "answer", "target", "reference", "gold"].includes(k)
        );
        if (oIdx !== -1) setOutputCol(keys[oIdx]);

        const cIdx = lowerKeys.findIndex((k) =>
          ["contexts", "context", "passages", "documents", "chunks"].includes(k)
        );
        if (cIdx !== -1) setContextCol(keys[cIdx]);
      }
    }
  };

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fileContent.trim()) {
      alert("Please select or drop a valid file first.");
      return;
    }
    if (!datasetName.trim()) {
      alert("Please specify a dataset name.");
      return;
    }
    if (!queryCol) {
      alert("Please map the required Query column.");
      return;
    }

    setIngesting(true);
    showToast(`Ingesting ${file?.name || "dataset"}...`, "loading");

    try {
      const mapping: Record<string, string> = {
        query: queryCol,
      };
      if (outputCol) mapping.expected_output = outputCol;
      if (contextCol) mapping.contexts = contextCol;

      const res = await ingestDataset({
        name: datasetName.trim(),
        description: datasetDesc.trim() || undefined,
        file_format: fileFormat,
        content: fileContent,
        column_mapping: mapping,
      });

      showToast(
        `Successfully ingested "${res.dataset.name}" with ${res.total_ingested} items!`,
        "success"
      );
      onDatasetCreated(res.dataset.id);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Ingestion failed", "error");
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-8 animate-in fade-in duration-300">
      {/* ── HEADER ── */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">📁</span>
            <h3 className="text-lg font-bold text-slate-100">
              Bulk Dataset Ingestion (CSV / JSONL)
            </h3>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              v2.5 Engine
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Import existing enterprise evaluation suites, HuggingFace datasets, or SQuAD-like benchmarks in one click.
          </p>
        </div>

        {/* Template Download Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => handleDownloadSample("csv")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            title="Download reference CSV template"
          >
            <span>📄</span>
            <span>Sample CSV</span>
          </button>
          <button
            type="button"
            onClick={() => handleDownloadSample("jsonl")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            title="Download reference JSONL template"
          >
            <span>📜</span>
            <span>Sample JSONL</span>
          </button>
        </div>
      </div>

      <form onSubmit={handleIngest} className="space-y-6">
        {/* ── DRAG & DROP ZONE ── */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
              processFile(e.dataTransfer.files[0]);
            }
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`cursor-pointer border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-200 ${
            isDragging
              ? "border-emerald-500 bg-emerald-950/20"
              : file
              ? "border-indigo-500/60 bg-indigo-950/10 hover:border-indigo-400"
              : "border-slate-800 bg-slate-950/50 hover:border-slate-700 hover:bg-slate-950"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.jsonl,.json,text/csv,application/json"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                processFile(e.target.files[0]);
              }
            }}
          />

          {file ? (
            <div className="flex flex-col items-center gap-2">
              <span className="text-3xl">📄</span>
              <div className="text-sm font-semibold text-slate-200">{file.name}</div>
              <div className="text-xs text-slate-400">
                {(file.size / 1024).toFixed(1)} KB • Detected Format:{" "}
                <span className="font-mono text-indigo-300 uppercase">{fileFormat}</span>
              </div>
              <span className="text-[11px] text-indigo-400 hover:underline mt-1">
                Click or drop another file to replace
              </span>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2.5">
              <span className="text-4xl text-slate-500">📥</span>
              <div className="text-sm font-medium text-slate-300">
                Drag and drop your benchmark file here, or{" "}
                <span className="text-indigo-400 hover:underline">browse</span>
              </div>
              <p className="text-xs text-slate-500 max-w-md">
                Supports <span className="text-slate-400 font-mono">.csv</span>,{" "}
                <span className="text-slate-400 font-mono">.jsonl</span>, and{" "}
                <span className="text-slate-400 font-mono">.json</span> files up to 25MB.
              </p>
            </div>
          )}
        </div>

        {/* ── COLUMN MAPPING SECTION (IF HEADERS DETECTED) ── */}
        {detectedHeaders.length > 0 && (
          <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-xs font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                  <span>🗺️</span>
                  <span>Column Field Mapping</span>
                </h4>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Confirm which file columns correspond to RAGBench evaluation dimensions.
                </p>
              </div>
              <span className="text-[11px] text-emerald-400 bg-emerald-950/50 border border-emerald-800/60 px-2 py-0.5 rounded-full">
                Auto-Detected ✓
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              {/* Query Mapping */}
              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium flex items-center justify-between">
                  <span>Query / Prompt *</span>
                  <span className="text-[10px] text-rose-400 font-normal">Required</span>
                </label>
                <select
                  value={queryCol}
                  onChange={(e) => setQueryCol(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                  required
                >
                  <option value="">-- Select Column --</option>
                  {detectedHeaders.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </div>

              {/* Expected Output Mapping */}
              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium flex items-center justify-between">
                  <span>Expected Output (Ground Truth)</span>
                  <span className="text-[10px] text-slate-500 font-normal">Optional</span>
                </label>
                <select
                  value={outputCol}
                  onChange={(e) => setOutputCol(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                >
                  <option value="">-- None (Leave empty) --</option>
                  {detectedHeaders.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </div>

              {/* Contexts Mapping */}
              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium flex items-center justify-between">
                  <span>Context / Documents</span>
                  <span className="text-[10px] text-slate-500 font-normal">Optional</span>
                </label>
                <select
                  value={contextCol}
                  onChange={(e) => setContextCol(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 outline-none focus:border-indigo-500 font-mono"
                >
                  <option value="">-- None (Leave empty) --</option>
                  {detectedHeaders.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Quick Preview Table */}
            {previewRows.length > 0 && (
              <div className="pt-3 border-t border-slate-800 space-y-2">
                <div className="text-[11px] font-semibold text-slate-400">
                  Data Preview (First {previewRows.length} rows):
                </div>
                <div className="overflow-x-auto rounded-lg border border-slate-800">
                  <table className="w-full text-[11px] text-left text-slate-300">
                    <thead className="bg-slate-900 text-slate-400 font-mono border-b border-slate-800">
                      <tr>
                        {detectedHeaders.map((h) => (
                          <th key={h} className="px-3 py-2">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-sans">
                      {previewRows.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-900/40">
                          {detectedHeaders.map((h) => (
                            <td key={h} className="px-3 py-2 truncate max-w-[200px]" title={row[h]}>
                              {row[h] || <span className="text-slate-600 italic">empty</span>}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── DATASET DETAILS ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Dataset Name *
            </label>
            <input
              type="text"
              placeholder="e.g. Finance QA Benchmark (v1)"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 outline-none focus:border-indigo-500"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Description (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. Ingested from enterprise support tickets"
              value={datasetDesc}
              onChange={(e) => setDatasetDesc(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* ── ACTION BUTTON ── */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={ingesting || !fileContent}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950 transition disabled:opacity-50"
          >
            {ingesting ? (
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
                <span>Ingesting Dataset...</span>
              </>
            ) : (
              <>
                <span>📥 Ingest &amp; Assemble Dataset</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

