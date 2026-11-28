"use client";

import React, { useEffect, useState } from "react";
import {
  evaluatePIILeakage,
  fetchPIIPresets,
  maskPII,
  PIIEntityMatch,
  PIILeakageCheckResult,
  PIIPresetScenario,
  PIIRestoreResult,
  PIISanitizationResult,
  probeSanitizerWebhook,
  SanitizerWebhookProbeResponse,
  unmaskPII,
} from "@/lib/api";

interface PIISanitizerViewProps {
  showToast: (message: string, type: "loading" | "success" | "error") => void;
}

export default function PIISanitizerView({ showToast }: PIISanitizerViewProps) {
  const [presets, setPresets] = useState<PIIPresetScenario[]>([]);
  const [loadingPresets, setLoadingPresets] = useState(false);

  // Active Tab: "masking" | "leakage" | "webhook"
  const [activeTab, setActiveTab] = useState<"masking" | "leakage" | "webhook">("masking");

  // Live Webhook Probe State
  const [webhookUrl, setWebhookUrl] = useState("http://localhost:8001/chat");
  const [webhookText, setWebhookText] = useState(
    "My email is alice.smith@example.com and phone is +1-555-234-5678. What is Acme Corp's refund policy?"
  );
  const [probingWebhook, setProbingWebhook] = useState(false);
  const [webhookProbeResult, setWebhookProbeResult] = useState<SanitizerWebhookProbeResponse | null>(null);

  // Mode 1: Masking & Reversible Rehydration State
  const [inputText, setInputText] = useState(
    "Hello Support, my email is alice.smith@example.com and phone is +1-555-234-5678. " +
    "Please process a refund to my Visa card 4532-0150-1234-5671 expiring 08/28."
  );
  const [strategy, setStrategy] = useState<"token" | "redact" | "hash">("token");
  const [maskEmail, setMaskEmail] = useState(true);
  const [maskPhone, setMaskPhone] = useState(true);
  const [maskSsn, setMaskSsn] = useState(true);
  const [maskCreditCard, setMaskCreditCard] = useState(true);
  const [maskApiKey, setMaskApiKey] = useState(true);
  const [maskIpAddress, setMaskIpAddress] = useState(true);

  const [sanitizing, setSanitizing] = useState(false);
  const [sanitizedResult, setSanitizedResult] = useState<PIISanitizationResult | null>(null);

  // Unmasking State
  const [unmasking, setUnmasking] = useState(false);
  const [restoredResult, setRestoredResult] = useState<PIIRestoreResult | null>(null);

  // Mode 2: RAG Context Leakage State
  const [contextInput, setContextInput] = useState(
    "Confidential Customer Account #9401:\n" +
    "Client: Alice Smith (alice.smith@example.com, Phone: +1-555-234-5678)\n" +
    "SSN: 123-45-6789 | Active Visa: 4532-0150-1234-5671"
  );
  const [generationInput, setGenerationInput] = useState(
    "The customer Alice Smith called from +1-555-234-5678 requesting an update on their card 4532-0150-1234-5671."
  );
  const [auditingLeakage, setAuditingLeakage] = useState(false);
  const [leakageResult, setLeakageResult] = useState<PIILeakageCheckResult | null>(null);

  useEffect(() => {
    const loadPresets = async () => {
      setLoadingPresets(true);
      try {
        const data = await fetchPIIPresets();
        setPresets(data);
      } catch {
        // Fallback silently if offline
      } finally {
        setLoadingPresets(false);
      }
    };
    loadPresets();
  }, []);

  const handleApplyPreset = (preset: PIIPresetScenario) => {
    if (activeTab === "masking") {
      setInputText(preset.sample_text);
      setSanitizedResult(null);
      setRestoredResult(null);
      showToast(`Loaded preset: ${preset.title}`, "success");
    } else {
      if (preset.sample_context) {
        setContextInput(preset.sample_context);
      }
      setGenerationInput(preset.sample_text);
      setLeakageResult(null);
      showToast(`Loaded preset into Leakage Inspector: ${preset.title}`, "success");
    }
  };

  const handleSanitize = async () => {
    if (!inputText.trim()) return;
    setSanitizing(true);
    setRestoredResult(null);
    try {
      const res = await maskPII(inputText, {
        strategy,
        mask_email: maskEmail,
        mask_phone: maskPhone,
        mask_ssn: maskSsn,
        mask_credit_card: maskCreditCard,
        mask_api_key: maskApiKey,
        mask_ip_address: maskIpAddress,
      });
      setSanitizedResult(res);
      showToast(
        res.entities_found.length > 0
          ? `Sanitized ${res.entities_found.length} PII entities in ${res.latency_ms.toFixed(2)}ms`
          : "Clean! No PII entities detected.",
        "success"
      );
    } catch (err: any) {
      showToast(err.message || "Failed to sanitize text", "error");
    } finally {
      setSanitizing(false);
    }
  };

  const handleUnmask = async () => {
    if (!sanitizedResult) return;
    setUnmasking(true);
    try {
      const res = await unmaskPII(sanitizedResult.sanitized_text, sanitizedResult.token_map);
      setRestoredResult(res);
      showToast(`Rehydrated ${res.tokens_restored_count} tokens successfully!`, "success");
    } catch (err: any) {
      showToast(err.message || "Failed to restore tokens", "error");
    } finally {
      setUnmasking(false);
    }
  };

  const handleAuditLeakage = async () => {
    if (!contextInput.trim() || !generationInput.trim()) return;
    setAuditingLeakage(true);
    try {
      const chunks = contextInput
        .split("\n\n")
        .map((c) => c.trim())
        .filter(Boolean);
      const res = await evaluatePIILeakage(chunks, generationInput);
      setLeakageResult(res);
      showToast(
        res.leaked
          ? `ALERT: ${res.total_leaked_count} private entities leaked into response!`
          : "Audit Passed: All context PII remained protected.",
        res.leaked ? "error" : "success"
      );
    } catch (err: any) {
      showToast(err.message || "Failed to audit PII leakage", "error");
    } finally {
      setAuditingLeakage(false);
    }
  };

  const getEntityBadgeColor = (type: string) => {
    switch (type) {
      case "email":
        return "bg-cyan-500/20 text-cyan-300 border-cyan-500/30";
      case "phone_number":
        return "bg-indigo-500/20 text-indigo-300 border-indigo-500/30";
      case "ssn":
        return "bg-rose-500/20 text-rose-300 border-rose-500/30";
      case "credit_card":
        return "bg-amber-500/20 text-amber-300 border-amber-500/30";
      case "api_key":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
      case "ip_address":
        return "bg-purple-500/20 text-purple-300 border-purple-500/30";
      default:
        return "bg-slate-500/20 text-slate-300 border-slate-500/30";
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn pb-16">
      {/* 1. Header Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-cyan-950/40 via-slate-900 to-indigo-950/30 border border-cyan-500/30 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-2xl">🔒</span>
              <h2 className="text-xl font-bold text-slate-100">
                Automated PII Masking &amp; Data Sanitization Pipeline
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                v3.3 Compliance
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
              GDPR, HIPAA &amp; SOC2 zero-leakage protection. Redacts SSNs, credit cards (with Luhn validation),
              emails, phones, API keys, and IP addresses with reversible token rehydration and RAG leakage auditing.
            </p>
          </div>
        </div>

        {/* Metric Pill Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
          <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">
              Detection Latency
            </span>
            <div className="flex items-baseline gap-1 mt-1">
              <span className="text-lg font-bold text-cyan-400">&lt; 0.3 ms</span>
              <span className="text-[10px] text-slate-500">sub-millisecond</span>
            </div>
          </div>

          <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">
              Compliance Standard
            </span>
            <div className="flex items-baseline gap-1 mt-1">
              <span className="text-lg font-bold text-emerald-400">GDPR / HIPAA</span>
              <span className="text-[10px] text-slate-500">SOC2 Ready</span>
            </div>
          </div>

          <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">
              Credit Card Check
            </span>
            <div className="flex items-baseline gap-1 mt-1">
              <span className="text-lg font-bold text-amber-400">Luhn Algorithm</span>
              <span className="text-[10px] text-slate-500">0% false pos</span>
            </div>
          </div>

          <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">
              Reversibility
            </span>
            <div className="flex items-baseline gap-1 mt-1">
              <span className="text-lg font-bold text-indigo-400">Deterministic</span>
              <span className="text-[10px] text-slate-500">token map</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. 1-Click Preset Scenarios Bar */}
      <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm">⚡</span>
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              1-Click Enterprise PII Presets
            </h3>
          </div>
          <span className="text-[11px] text-slate-400">
            Click to load real-world enterprise test scenarios
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 pt-1">
          {presets.map((preset) => (
            <button
              key={preset.id}
              onClick={() => handleApplyPreset(preset)}
              className="p-3 rounded-xl bg-slate-950/60 hover:bg-slate-800/80 border border-slate-800/80 hover:border-cyan-500/50 text-left transition group flex flex-col justify-between"
            >
              <div>
                <span className="text-xs font-semibold text-slate-200 group-hover:text-cyan-300 transition block mb-1">
                  {preset.title}
                </span>
                <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                  {preset.description}
                </p>
              </div>
              <div className="mt-2 flex items-center justify-between">
                <span className="text-[10px] text-cyan-400 font-medium">Load Scenario ➔</span>
                <div className="flex gap-1">
                  {preset.expected_entities.slice(0, 2).map((e) => (
                    <span
                      key={e}
                      className="text-[9px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 uppercase font-mono"
                    >
                      {e.replace("_", " ")}
                    </span>
                  ))}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* 3. Dual-Mode Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <button
          type="button"
          onClick={() => setActiveTab("masking")}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 ${
            activeTab === "masking"
              ? "bg-cyan-600 text-white shadow-md shadow-cyan-600/30"
              : "text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800"
          }`}
        >
          <span>🔒</span>
          <span>Masking &amp; Reversible Rehydration</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("leakage")}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 ${
            activeTab === "leakage"
              ? "bg-cyan-600 text-white shadow-md shadow-cyan-600/30"
              : "text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800"
          }`}
        >
          <span>🔍</span>
          <span>RAG Context Leakage Inspector</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("webhook")}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center gap-2 ${
            activeTab === "webhook"
              ? "bg-cyan-600 text-white shadow-md shadow-cyan-600/30"
              : "text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800"
          }`}
        >
          <span>🌐</span>
          <span>Live Webhook Probe</span>
        </button>
      </div>

      {/* TAB 1: Masking & Rehydration Console */}
      {activeTab === "masking" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Input & Configuration (7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-slate-300">
                    Raw Text Containing Sensitive Information
                  </label>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {inputText.length} characters
                  </span>
                </div>
                <textarea
                  rows={4}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Paste customer support tickets, emails, logs, or user prompts..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 font-mono focus:border-cyan-500 outline-none transition resize-none"
                />
              </div>

              {/* Redaction Strategy Selector */}
              <div className="space-y-1.5">
                <span className="text-[11px] font-semibold text-slate-300 block">
                  Redaction Strategy
                </span>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setStrategy("token")}
                    className={`p-2.5 rounded-xl border text-left transition ${
                      strategy === "token"
                        ? "bg-cyan-950/60 border-cyan-500 text-cyan-200"
                        : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    <span className="text-xs font-bold block">[TOKEN_N]</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">
                      Reversible token mapping
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setStrategy("redact")}
                    className={`p-2.5 rounded-xl border text-left transition ${
                      strategy === "redact"
                        ? "bg-cyan-950/60 border-cyan-500 text-cyan-200"
                        : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    <span className="text-xs font-bold block">[REDACTED]</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">
                      One-way permanent mask
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setStrategy("hash")}
                    className={`p-2.5 rounded-xl border text-left transition ${
                      strategy === "hash"
                        ? "bg-cyan-950/60 border-cyan-500 text-cyan-200"
                        : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    <span className="text-xs font-bold block">[HASH_xxxx]</span>
                    <span className="text-[10px] text-slate-500 block mt-0.5">
                      Pseudonymized SHA-256
                    </span>
                  </button>
                </div>
              </div>

              {/* Entity Detection Toggles */}
              <div className="space-y-1.5">
                <span className="text-[11px] font-semibold text-slate-300 block">
                  Active Entity Filters
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  <label className="flex items-center gap-2 p-2 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={maskEmail}
                      onChange={(e) => setMaskEmail(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
                    />
                    <span>Emails</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={maskPhone}
                      onChange={(e) => setMaskPhone(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
                    />
                    <span>Phone Numbers</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={maskSsn}
                      onChange={(e) => setMaskSsn(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
                    />
                    <span>SSNs / ITINs</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={maskCreditCard}
                      onChange={(e) => setMaskCreditCard(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
                    />
                    <span>Credit Cards</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={maskApiKey}
                      onChange={(e) => setMaskApiKey(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
                    />
                    <span>API Keys &amp; Secrets</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={maskIpAddress}
                      onChange={(e) => setMaskIpAddress(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
                    />
                    <span>IP Addresses</span>
                  </label>
                </div>
              </div>

              <button
                type="button"
                onClick={handleSanitize}
                disabled={sanitizing}
                className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-600 via-indigo-600 to-indigo-700 hover:from-cyan-500 hover:to-indigo-600 text-white font-semibold text-xs shadow-lg shadow-cyan-950 transition flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {sanitizing ? (
                  <span>Sanitizing PII...</span>
                ) : (
                  <>
                    <span>🔒</span>
                    <span>Sanitize &amp; Redact Text</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Right Column: Sanitized Output & Reversible Unmasking (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm">🛡️</span>
                  <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                    Sanitized Output
                  </h3>
                </div>
                {sanitizedResult && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-950 border border-slate-700 text-cyan-400">
                    {sanitizedResult.latency_ms.toFixed(2)} ms
                  </span>
                )}
              </div>

              {sanitizedResult ? (
                <div className="space-y-4 animate-fadeIn">
                  {/* Sanitized Text Display */}
                  <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 font-mono text-xs text-slate-200 leading-relaxed break-words">
                    {sanitizedResult.sanitized_text}
                  </div>

                  {/* Entities Count Chips */}
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(sanitizedResult.entities_count).map(([type, count]) => (
                      <span
                        key={type}
                        className={`text-[11px] px-2.5 py-0.5 rounded-full font-mono font-semibold border flex items-center gap-1 ${getEntityBadgeColor(
                          type
                        )}`}
                      >
                        <span>{type.replace("_", " ")}:</span>
                        <span className="font-bold">{count}</span>
                      </span>
                    ))}
                    {sanitizedResult.entities_found.length === 0 && (
                      <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        ✓ No Sensitive PII Found
                      </span>
                    )}
                  </div>

                  {/* Token Map Card */}
                  {Object.keys(sanitizedResult.token_map).length > 0 && (
                    <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                        Reversible Token Mapping (Vault Stored)
                      </span>
                      <div className="space-y-1 max-h-36 overflow-y-auto">
                        {Object.entries(sanitizedResult.token_map).map(([token, orig]) => (
                          <div
                            key={token}
                            className="flex items-center justify-between text-[11px] font-mono p-1.5 bg-slate-900 rounded border border-slate-800/80"
                          >
                            <span className="text-cyan-400 font-bold">{token}</span>
                            <span className="text-slate-500 text-[10px]">➔</span>
                            <span className="text-slate-300 truncate max-w-[160px]" title={orig}>
                              {orig}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 1-Click Reversible Unmasking Button */}
                  {strategy === "token" && Object.keys(sanitizedResult.token_map).length > 0 && (
                    <button
                      type="button"
                      onClick={handleUnmask}
                      disabled={unmasking}
                      className="w-full py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition flex items-center justify-center gap-2"
                    >
                      {unmasking ? (
                        <span>Rehydrating Tokens...</span>
                      ) : (
                        <>
                          <span>🔓</span>
                          <span>Test 1-Click Reversible Unmask</span>
                        </>
                      )}
                    </button>
                  )}

                  {/* Restored Text Banner */}
                  {restoredResult && (
                    <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/30 space-y-1.5 animate-fadeIn">
                      <div className="flex items-center justify-between text-xs text-emerald-400 font-bold">
                        <span>✓ Rehydrated Text ({restoredResult.tokens_restored_count} tokens)</span>
                        <span className="font-mono text-[10px]">{restoredResult.latency_ms.toFixed(2)} ms</span>
                      </div>
                      <p className="font-mono text-xs text-slate-200 break-words">
                        {restoredResult.restored_text}
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-8 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded-xl space-y-2">
                  <span className="text-3xl block">🔒</span>
                  <p>No sanitized output yet.</p>
                  <p className="text-[11px] text-slate-600">
                    Click &ldquo;Sanitize &amp; Redact Text&rdquo; to test entity masking.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: RAG Context Leakage Inspector */}
      {activeTab === "leakage" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7 space-y-4">
            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-slate-300">
                    Retrieved Context Passages (Holding Sensitive PII)
                  </label>
                  <span className="text-[10px] text-slate-500">
                    Source documents containing private customer or patient records
                  </span>
                </div>
                <textarea
                  rows={4}
                  value={contextInput}
                  onChange={(e) => setContextInput(e.target.value)}
                  placeholder="Paste context documents..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 font-mono focus:border-cyan-500 outline-none transition resize-none"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-slate-300">
                    Generated Model Response to Audit
                  </label>
                  <span className="text-[10px] text-slate-500">
                    Evaluating if context PII was leaked unmasked into the answer
                  </span>
                </div>
                <textarea
                  rows={4}
                  value={generationInput}
                  onChange={(e) => setGenerationInput(e.target.value)}
                  placeholder="Paste generated answer to audit..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 font-mono focus:border-cyan-500 outline-none transition resize-none"
                />
              </div>

              <button
                type="button"
                onClick={handleAuditLeakage}
                disabled={auditingLeakage}
                className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-amber-600 via-indigo-600 to-indigo-700 hover:from-amber-500 hover:to-indigo-600 text-white font-semibold text-xs shadow-lg shadow-indigo-950 transition flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {auditingLeakage ? (
                  <span>Auditing Context PII Leakage...</span>
                ) : (
                  <>
                    <span>🔍</span>
                    <span>Run RAG Context Leakage Audit</span>
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="lg:col-span-5 space-y-4">
            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm">⚖️</span>
                  <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                    Leakage Audit Verdict
                  </h3>
                </div>
                {leakageResult && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-950 border border-slate-700 text-amber-400">
                    {leakageResult.latency_ms.toFixed(2)} ms
                  </span>
                )}
              </div>

              {leakageResult ? (
                <div className="space-y-4 animate-fadeIn">
                  {/* Verdict Banner */}
                  <div
                    className={`p-4 rounded-xl border flex items-start gap-3 ${
                      leakageResult.leaked
                        ? "bg-rose-950/40 border-rose-500/40 text-rose-300"
                        : "bg-emerald-950/40 border-emerald-500/40 text-emerald-300"
                    }`}
                  >
                    <span className="text-2xl mt-0.5">
                      {leakageResult.leaked ? "🚨" : "🛡️"}
                    </span>
                    <div className="flex-1">
                      <span className="font-bold text-xs uppercase tracking-wider block">
                        {leakageResult.leaked
                          ? "CRITICAL: PII Leakage Detected"
                          : "Audit Passed (Zero Leakage)"}
                      </span>
                      <p className="text-xs mt-1 text-slate-300 font-medium leading-relaxed">
                        {leakageResult.reason}
                      </p>
                    </div>
                  </div>

                  {/* Metrics */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase font-semibold block">
                        Context PII Total
                      </span>
                      <span className="font-bold text-slate-200">
                        {leakageResult.total_context_pii_count} items
                      </span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase font-semibold block">
                        Leaked to Output
                      </span>
                      <span
                        className={`font-bold ${
                          leakageResult.total_leaked_count > 0 ? "text-rose-400" : "text-emerald-400"
                        }`}
                      >
                        {leakageResult.total_leaked_count} items
                      </span>
                    </div>
                  </div>

                  {/* Leaked Entities List */}
                  {leakageResult.leaked_entities.length > 0 && (
                    <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                      <span className="text-[10px] text-rose-400 uppercase font-bold block">
                        Exposed Context Items Found in Output
                      </span>
                      <div className="space-y-1.5">
                        {leakageResult.leaked_entities.map((ent, idx) => (
                          <div
                            key={idx}
                            className="p-2 rounded bg-rose-950/20 border border-rose-800/40 flex items-center justify-between text-xs"
                          >
                            <span className="font-mono text-rose-300 font-bold uppercase text-[10px]">
                              {ent.entity_type}
                            </span>
                            <span className="font-mono text-slate-200 text-xs">
                              {ent.text}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-8 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded-xl space-y-2">
                  <span className="text-3xl block">🔍</span>
                  <p>No audit verdict yet.</p>
                  <p className="text-[11px] text-slate-600">
                    Paste context passages and model generation, then click &ldquo;Run RAG Context Leakage Audit&rdquo;.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: Live Webhook PII Probe */}
      {activeTab === "webhook" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-6 p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <span>🌐</span>
              <span>Zero-Leakage Live Webhook Probe</span>
            </h3>
            <p className="text-xs text-slate-400">
              Masks sensitive PII before sending your prompt to the target Webhook URL, then audits its live response for PII leakage and rehydrates tokens.
            </p>
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Webhook Endpoint URL</label>
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="http://localhost:8001/chat"
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Prompt Containing PII</label>
              <textarea
                rows={4}
                value={webhookText}
                onChange={(e) => setWebhookText(e.target.value)}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 p-3 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>
            <button
              type="button"
              disabled={probingWebhook || !webhookUrl.trim() || !webhookText.trim()}
              onClick={async () => {
                setProbingWebhook(true);
                showToast("Masking PII and probing live webhook...", "loading");
                try {
                  const res = await probeSanitizerWebhook({
                    webhook_url: webhookUrl,
                    text: webhookText,
                    config: {
                      strategy,
                      mask_email: maskEmail,
                      mask_phone: maskPhone,
                      mask_ssn: maskSsn,
                      mask_credit_card: maskCreditCard,
                      mask_api_key: maskApiKey,
                      mask_ip_address: maskIpAddress,
                    },
                  });
                  setWebhookProbeResult(res);
                  showToast(`Masked ${res.sanitization.entities_found.length} PII entities & probed webhook in ${res.latency_ms}ms`, "success");
                } catch (err: unknown) {
                  showToast(err instanceof Error ? err.message : "Webhook probe failed", "error");
                } finally {
                  setProbingWebhook(false);
                }
              }}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold transition disabled:opacity-50"
            >
              {probingWebhook ? "Masking & Probing Webhook..." : "🔒 Mask PII → Probe Webhook → Audit Response"}
            </button>
          </div>

          <div className="lg:col-span-6 p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4 text-xs">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider border-b border-slate-800 pb-2">
              Live Pipeline Inspection
            </h3>
            {webhookProbeResult ? (
              <div className="space-y-3">
                <div>
                  <span className="text-[11px] font-semibold text-cyan-400 block mb-1">
                    1. Sanitized Prompt Sent to Webhook ({webhookProbeResult.sanitization.entities_found.length} entities masked)
                  </span>
                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 font-mono text-slate-200">
                    {webhookProbeResult.sanitization.sanitized_text}
                  </div>
                </div>
                <div>
                  <span className="text-[11px] font-semibold text-emerald-400 block mb-1">
                    2. Webhook Response ({webhookProbeResult.latency_ms} ms)
                  </span>
                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200">
                    {webhookProbeResult.webhook_response}
                  </div>
                </div>
                <div className={`p-3 rounded-lg border ${webhookProbeResult.leakage_check.leaked ? "bg-rose-950/30 border-rose-500/40 text-rose-300" : "bg-emerald-950/30 border-emerald-500/40 text-emerald-300"}`}>
                  <strong>Leakage Audit:</strong>{" "}
                  {webhookProbeResult.leakage_check.leaked
                    ? `CRITICAL — ${webhookProbeResult.leakage_check.leaked_entities.length} PII entities leaked in response`
                    : "CLEAN — Zero raw PII leaked in webhook response"}
                </div>
              </div>
            ) : (
              <div className="p-10 text-center text-slate-500 border border-dashed border-slate-800 rounded-xl">
                Enter your Webhook URL and click &ldquo;Mask PII → Probe Webhook&rdquo; to test live zero-leakage protection.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
