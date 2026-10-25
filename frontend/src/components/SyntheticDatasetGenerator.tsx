"use client";

import React, { useState } from "react";
import {
  generateSyntheticDataset,
  createDataset,
  SyntheticItemPreview,
  ApiKeyMetadata,
} from "../lib/api";

interface SyntheticDatasetGeneratorProps {
  apiKeys: ApiKeyMetadata[];
  onDatasetCreated: (datasetId: string) => void;
  onCancel?: () => void;
  showToast: (message: string, type: "loading" | "success" | "error") => void;
}

const SAMPLE_DOCUMENT = `RAGBench Global Shipping and Return Policy (v2.4)

1. Delivery Timelines & Tracking
Standard ground shipping orders are processed within 1 to 2 business days. Delivery across North America and Europe typically takes between 3 to 5 business days. Express overnight priority shipping is available for all orders placed before 2:00 PM EST, excluding national holidays and weekends. Real-time carrier tracking numbers are sent via encrypted email notification as soon as the package departs our fulfillment logistics center.

2. Return Window & Eligibility Requirements
Customers may initiate a full refund return within 30 days of confirmed delivery receipt. To be eligible for a full credit refund, items must remain in their original unworn condition, retaining all factory barcodes, authentication tags, and sealed packaging. Customized, bespoke, or personalized enterprise hardware configurations are strictly non-refundable once assembly has begun.

3. Restocking Fees & Return Shipping Labels
Standard customer-initiated returns are subject to a nominal $4.50 restocking and inspection surcharge, which will be automatically deducted from the final refund credit balance. However, if the return is caused by a manufacturer hardware defect, incorrect item shipment, or shipping transit damage verified by photo documentation, the restocking surcharge is 100% waived and RAGBench will furnish a prepaid expedited shipping return label.

4. International Customs, Duties & VAT
International shipments delivered outside North America may incur local customs duties, value-added tax (VAT), and import clearance fees assessed by local border authorities. These supplemental import assessments are the sole responsibility of the recipient customer unless "Delivered Duty Paid" (DDP) was explicitly selected during enterprise checkout.`;

export default function SyntheticDatasetGenerator({
  apiKeys,
  onDatasetCreated,
  onCancel,
  showToast,
}: SyntheticDatasetGeneratorProps) {
  const [rawText, setRawText] = useState("");
  const [numSamples, setNumSamples] = useState(3);
  const [difficulty, setDifficulty] = useState<"mixed" | "factual" | "reasoning" | "adversarial">("mixed");
  const [provider, setProvider] = useState(() => (apiKeys.length > 0 ? apiKeys[0].provider : "groq"));
  const [model, setModel] = useState("openai/gpt-oss-120b");
  const [customKey, setCustomKey] = useState("");

  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generatedItems, setGeneratedItems] = useState<SyntheticItemPreview[]>([]);
  const [generationMeta, setGenerationMeta] = useState<{
    provider: string;
    model: string;
    latency_ms: number;
  } | null>(null);

  // Form for saving as a dataset
  const [datasetName, setDatasetName] = useState("");
  const [datasetDesc, setDatasetDesc] = useState("");

  const handleLoadSample = () => {
    setRawText(SAMPLE_DOCUMENT);
    setDatasetName("Corporate Return & Shipping Policy Benchmark");
    setDatasetDesc("AI-synthesized evaluation benchmark generated from RAGBench shipping and refund terms.");
    showToast("Sample policy document loaded!", "success");
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawText.trim() || rawText.trim().length < 50) {
      alert("Please provide at least 50 characters of source document text.");
      return;
    }

    setGenerating(true);
    showToast("Synthesizing test questions, context chunks & answers...", "loading");

    try {
      const res = await generateSyntheticDataset({
        raw_text: rawText.trim(),
        num_samples: numSamples,
        difficulty,
        provider_name: provider,
        model_name: model || undefined,
        api_key: customKey.trim() || undefined,
      });

      setGeneratedItems(res.items);
      setGenerationMeta({
        provider: res.provider_used,
        model: res.model_used,
        latency_ms: res.latency_ms,
      });

      if (!datasetName) {
        setDatasetName(`Synthetic Benchmark (${new Date().toLocaleDateString()})`);
      }

      showToast(`Successfully generated ${res.items.length} synthetic evaluation samples!`, "success");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Generation failed", "error");
    } finally {
      setGenerating(false);
    }
  };

  const handleItemChange = (index: number, field: "query" | "expected_output", value: string) => {
    setGeneratedItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, [field]: value } : item))
    );
  };

  const handleDeleteItem = (index: number) => {
    setGeneratedItems((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSaveAsDataset = async () => {
    if (!datasetName.trim()) {
      alert("Please specify a dataset name.");
      return;
    }
    if (generatedItems.length === 0) {
      alert("No generated items to save.");
      return;
    }

    setSaving(true);
    showToast("Saving synthesized benchmark dataset...", "loading");

    try {
      const dataset = await createDataset({
        name: datasetName.trim(),
        description: datasetDesc.trim() || undefined,
        items: generatedItems.map((item) => ({
          query: item.query,
          expected_output: item.expected_output,
          contexts: item.contexts,
          context: item.contexts,
          item_metadata: {
            difficulty: item.difficulty,
            synthesized_by: generationMeta?.provider || provider,
            source_snippet: item.source_snippet,
          },
          metadata: {
            difficulty: item.difficulty,
            synthesized_by: generationMeta?.provider || provider,
            source_snippet: item.source_snippet,
          },
        })),
      });

      showToast(`Dataset "${dataset.name}" created with ${generatedItems.length} items!`, "success");
      onDatasetCreated(dataset.id);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to create dataset", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-8 animate-in fade-in duration-300">
      {/* ── HEADER ── */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">✨</span>
            <h3 className="text-lg font-bold text-slate-100">
              Synthetic AI Test Dataset Generator
            </h3>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              v2.4 Engine
            </span>
          </div>
          <p className="text-xs text-slate-400 max-w-2xl">
            Paste any product guide, API doc, FAQ, or policy text. RAGBench uses your BYOK LLM to
            synthesize diverse test questions, ground-truth context passages, and gold-standard answers.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleLoadSample}
            className="px-3 py-1.5 rounded-xl bg-indigo-950/60 hover:bg-indigo-900/60 border border-indigo-800 text-indigo-300 text-xs font-medium transition"
          >
            📋 Load Sample Policy
          </button>
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* ── GENERATOR FORM ── */}
      <form onSubmit={handleGenerate} className="space-y-6">
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Source Document Text (Markdown / Text / FAQ)
            </label>
            <span className="text-[11px] font-mono text-slate-500">
              {rawText.length.toLocaleString()} characters
            </span>
          </div>

          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            rows={7}
            placeholder="Paste your source text here (minimum 50 characters)... e.g. Customer return policies, technical manuals, internal employee handbooks, product specifications..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs font-mono text-slate-200 outline-none focus:border-indigo-500 transition leading-relaxed"
          />
        </div>

        {/* Configuration Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Sample Count ({numSamples})
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={numSamples}
              onChange={(e) => setNumSamples(Number(e.target.value))}
              className="w-full accent-indigo-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
              <span>1 test</span>
              <span className="text-indigo-400 font-bold">{numSamples} samples</span>
              <span>10 max</span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Difficulty Distribution
            </label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value as any)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-indigo-500"
            >
              <option value="mixed">Mixed (Factual + Reasoning + Adversarial)</option>
              <option value="factual">Factual Only (Direct single-hop)</option>
              <option value="reasoning">Reasoning Only (Multi-hop analysis)</option>
              <option value="adversarial">Adversarial Only (Hallucination traps)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              LLM Provider (BYOK)
            </label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-indigo-500"
            >
              <option value="groq">Groq (Ultra-Fast)</option>
              <option value="openai">OpenAI (GPT-4o / Mini)</option>
              <option value="anthropic">Anthropic (Claude 3.5)</option>
              <option value="google">Google (Gemini 1.5)</option>
              <option value="mock">Mock Engine (Offline Demo)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Model Identifier
            </label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="e.g. openai/gpt-oss-120b"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-indigo-500 font-mono"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={generating || rawText.trim().length < 50}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium text-xs shadow-lg shadow-indigo-600/30 transition disabled:opacity-50 flex items-center gap-2"
          >
            {generating ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Synthesizing Test Set with AI...</span>
              </>
            ) : (
              <>
                <span>✨ Synthesize Test Dataset</span>
                <span className="text-white/60">({numSamples} cases)</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* ── INTERACTIVE REVIEW & EDIT TABLE ── */}
      {generatedItems.length > 0 && (
        <div className="space-y-6 pt-6 border-t border-slate-800 animate-in fade-in duration-300">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h4 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <span>🎯 Synthesized Test Cases</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  {generatedItems.length} samples
                </span>
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                Review and refine your test cases inline. Edit questions and answers before saving.
              </p>
            </div>

            {generationMeta && (
              <div className="text-[11px] font-mono text-slate-400 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
                Generated via <strong className="text-slate-200">{generationMeta.provider.toUpperCase()}</strong> in{" "}
                <span className="text-emerald-400 font-bold">{generationMeta.latency_ms.toFixed(0)}ms</span>
              </div>
            )}
          </div>

          <div className="space-y-4">
            {generatedItems.map((item, idx) => (
              <div
                key={idx}
                className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3 relative group hover:border-slate-700 transition"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-300 text-[10px] font-bold flex items-center justify-center font-mono">
                      #{idx + 1}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                        item.difficulty === "adversarial"
                          ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                          : item.difficulty === "reasoning"
                          ? "bg-purple-500/15 text-purple-400 border border-purple-500/30"
                          : "bg-blue-500/15 text-blue-400 border border-blue-500/30"
                      }`}
                    >
                      {item.difficulty}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleDeleteItem(idx)}
                    className="text-slate-500 hover:text-rose-400 text-xs px-2 py-1 rounded hover:bg-slate-900 transition"
                    title="Remove item"
                  >
                    ✕ Remove
                  </button>
                </div>

                {/* Editable Question */}
                <div>
                  <label className="block text-[10px] uppercase font-semibold text-slate-500 mb-1">
                    Evaluation Query / Question
                  </label>
                  <input
                    type="text"
                    value={item.query}
                    onChange={(e) => handleItemChange(idx, "query", e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500"
                  />
                </div>

                {/* Editable Expected Output */}
                <div>
                  <label className="block text-[10px] uppercase font-semibold text-slate-500 mb-1">
                    Expected Reference Answer (Ground Truth)
                  </label>
                  <textarea
                    value={item.expected_output}
                    onChange={(e) => handleItemChange(idx, "expected_output", e.target.value)}
                    rows={2}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500"
                  />
                </div>

                {/* Extracted Context Preview */}
                {item.contexts && item.contexts.length > 0 && (
                  <div className="pt-1">
                    <div className="text-[10px] uppercase font-semibold text-slate-500 mb-1">
                      Extracted Ground-Truth Context Paragraph
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80 text-[11px] text-slate-400 font-mono italic line-clamp-2">
                      &ldquo;{item.contexts[0]}&rdquo;
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* ── SAVE AS BENCHMARK DATASET PANEL ── */}
          <div className="p-5 bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950/40 border border-indigo-500/30 rounded-xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h5 className="text-sm font-bold text-slate-100">
                  Save as Production Benchmark Dataset
                </h5>
                <p className="text-xs text-slate-400">
                  Store these {generatedItems.length} synthesized items into your workspace for automated
                  evaluations, CI regression testing, and Pareto analysis.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Dataset Name
                </label>
                <input
                  type="text"
                  value={datasetName}
                  onChange={(e) => setDatasetName(e.target.value)}
                  placeholder="e.g. Return Policy Synthetic Benchmark"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Description (Optional)
                </label>
                <input
                  type="text"
                  value={datasetDesc}
                  onChange={(e) => setDatasetDesc(e.target.value)}
                  placeholder="e.g. Synthesized via Groq from official terms"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={handleSaveAsDataset}
                disabled={saving || !datasetName.trim() || generatedItems.length === 0}
                className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs shadow-lg shadow-emerald-600/30 transition disabled:opacity-50 flex items-center gap-2"
              >
                {saving ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Saving to Workspace Database...</span>
                  </>
                ) : (
                  <>
                    <span>💾 Save &amp; Assemble Dataset</span>
                    <span className="text-emerald-200">({generatedItems.length} items)</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
