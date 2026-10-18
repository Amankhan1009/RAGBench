# RAGBench v3.0 — Enterprise AI Security, Guardrails & LLM Gateway Roadmap

## Executive Summary

While **v1.0** established the core evaluation and CI/CD regression testing platform, and **v2.0** brings advanced visual analytics, streaming, and agent trajectory benchmarking, **RAGBench v3.0** elevates the platform into an **Enterprise-Grade AI Security, Guardrails, and LLM Gateway Suite**.

All security and gateway features in v3.0 are designed to be **100% free, open-source (Apache 2.0), and self-hostable**, utilizing **NVIDIA NeMo Guardrails**, the open-source **Portkey AI Gateway**, and local privacy redaction engines with zero mandatory SaaS subscription costs.

---

## Architecture Overview

```
                                 [ Production User / Client App ]
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. PORTKEY OPEN-SOURCE AI GATEWAY (Proxy Layer)                                             │
│    • Semantic Caching (In-memory / Redis — returns cached answers in <5ms at $0 cost)       │
│    • Universal Routing across 250+ LLMs (Groq, OpenAI, Anthropic, Gemini, Ollama)          │
│    • Automated Fallback & Exponential Retries (e.g. Groq 429 ➔ Gemini with 0 downtime)      │
│    • Budget Caps, Rate Limiting & Workspace Load Balancing                                  │
└───────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. PRE-EXECUTION SECURITY: PII SANITIZER & NEMO INPUT RAILS                                 │
│    • PII Redaction Pipeline (Masks SSNs, Emails, Credit Cards, API Keys into tokens)        │
│    • Prompt Injection & Jailbreak Blocker (Stops "DAN mode", "Ignore system instructions")   │
│    • Colang Topical Steering (Ensures prompts stay strictly within domain boundaries)       │
└───────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                                │ (Sanitized & Verified Prompt)
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. LLM EXECUTION LAYER (via Encrypted BYOK Vault)                                           │
│    • Groq (Llama 3.3 / GPT-OSS) • Google Gemini • OpenAI • Anthropic • Local Ollama         │
└───────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                                │ (Raw Generation)
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. POST-EXECUTION SECURITY: NEMO OUTPUT RAILS & HALLUCINATION INTERCEPTOR                   │
│    • RAG Fact-Checking (Verifies generated claims against retrieved context chunks)         │
│    • Hallucination Blocker (Replaces ungrounded claims with safe fallback responses)        │
│    • Brand Safety & Toxicity Filter (Prevents profanity, hate speech, or competitor leaks)  │
└───────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                                │
                                                ▼
                                    [ Verified Safe Output ]
```

---

## 1. NVIDIA NeMo Guardrails Integration (Open-Source Apache 2.0)

### 1.1 Objective
Embed NVIDIA's battle-tested open-source guardrails library (`nemoguardrails`) to enforce programmable runtime boundaries around user prompts, RAG context, and LLM responses.

### 1.2 Core Capabilities
1. **Input Rails (Pre-Execution Safety):**
   - Intercepts and blocks malicious prompt injections, system prompt leak attempts, and jailbreak vectors.
   - Evaluates input safety before the query consumes model tokens.
2. **Topical Rails (Programmable Colang Flows):**
   - Uses Colang definitions (`.co` files) to keep AI interactions locked to the company's designated domain.
   - Example: Off-topic questions to a technical support bot are politely declined without invoking expensive LLMs.
3. **Output Rails (Hallucination & Fact-Checking):**
   - Automatically cross-verifies model claims against retrieved RAG context passages.
   - If the model introduces external hallucinated assertions, the output rail intercepts the response and provides an approved fallback.
4. **Custom Rail Actions:**
   - Execute custom Python verification hooks within the guardrail loop.

---

## 2. Portkey Open-Source AI Gateway Integration

### 2.1 Objective
Provide an ultra-fast, universal API gateway (`/api/v1/gateway`) that simplifies multi-provider LLM management, eliminates downtime via automated failovers, and slashes latency and cost via semantic caching.

### 2.2 Core Capabilities
1. **Universal LLM Proxy (`/api/v1/gateway/chat/completions`):**
   - Drop-in OpenAI-compatible endpoint that transparently routes requests to any configured provider (Groq, Anthropic, Gemini, Mistral, Ollama).
2. **Automated Provider Failover & Smart Retries:**
   - If Provider A encounters rate-limiting (`429`) or server errors (`500/503`), the gateway automatically reroutes to Provider B with zero downtime.
3. **Zero-Cost Semantic Cache:**
   - Caches query-response pairs using vector or exact matching.
   - Identical and semantically equivalent queries return in `<5ms` at **$0.00** LLM cost.
4. **Cost & Token Budgets:**
   - Set monthly spending limits and token quotas per workspace.

---

## 3. Automated PII Masking & Data Sanitization Pipeline

### 3.1 Objective
Ensure complete privacy compliance (GDPR, HIPAA, SOC2) by redacting personally identifiable information (PII) before prompts are transmitted to cloud LLM providers or evaluation judges.

### 3.2 Core Capabilities
1. **Multi-Entity Redactor:**
   - Detects and masks: Social Security Numbers (SSNs), Credit Card Numbers, Email Addresses, Phone Numbers, Physical Addresses, and API Keys / Credentials.
2. **Reversible Token Replacement:**
   - Replaces entities with deterministic tokens (e.g. `[EMAIL_1]`, `[SSN_1]`).
   - Re-injects the original data upon final response delivery if authorized, ensuring models never store raw PII in cache or logs.
3. **PII Leakage Evaluator:**
   - New evaluation metric checking if retrieved contexts containing private data inadvertently leak into general model outputs.

---

## 4. AI Red-Teaming & Adversarial Vulnerability Benchmark Suite

### 4.1 Objective
Expand RAGBench from testing factual accuracy to testing **adversarial resilience, safety, and security posture**.

### 4.2 Core Capabilities
1. **Automated Attack Vectors:**
   - **Direct Prompt Injection:** Automated fuzzing with known jailbreak personas and instruction overrides.
   - **Indirect Context Injection:** Simulates poisoned RAG documents containing hidden prompt injection instructions.
   - **System Prompt Extraction:** Tests resistance to revealing developer instructions.
2. **Adversarial Resilience Score:**
   - New benchmark report outputting an overall **Security Posture Score** (0% to 100% Defense Rate).
   - Detailed breakdown of vulnerabilities flagged during test suites.

---

## 5. Enterprise RBAC & Tamper-Evident Audit Logging

### 5.1 Objective
Provide institutional governance, granular access control, and full compliance audit trails for enterprise organizations.

### 5.2 Core Capabilities
1. **Role-Based Access Control (RBAC):**
   - **Admin:** Manage workspace members, billing, API keys, and workspace settings.
   - **AI Engineer / Evaluator:** Create datasets, run experiments, set baselines, and configure guardrails.
   - **Viewer / Auditor:** Read-only access to evaluation dashboards, reports, and audit logs.
2. **Tamper-Evident Audit Log:**
   - Immutable event trail recording: baseline updates, API key registrations, dataset modifications, and guardrail toggle changes.
   - Every entry is timestamped and attributed to a specific user ID and source IP address.

---

## 6. Production Traffic Shadowing ("Golden Set Harvester")

### 6.1 Objective
Bridge live production monitoring with automated offline regression testing.

### 6.2 Core Capabilities
1. **Background Traffic Sampling (`POST /api/v1/telemetry/sample`):**
   - Production applications send an asynchronous sample (e.g. 1% to 5%) of live user queries and answers to RAGBench.
2. **Edge-Case & Failure Flagging:**
   - Automatically identifies queries where the model had high latency, low confidence, or guardrail intervention.
3. **1-Click Golden Set Promotion:**
   - Convert flagged production edge cases into permanent regression benchmark items with a single click.

---

## Version 3.0 Milestone Schedule

| Phase | Milestone | Feature Description | Core Stack |
| :---: | :---: | :--- | :--- |
| **Phase 22** | **v3.1** | **Portkey Open-Source AI Gateway & Semantic Cache** | Portkey Gateway, Redis/In-Memory Cache |
| **Phase 23** | **v3.2** | **NVIDIA NeMo Guardrails Engine (Input/Output/Colang)** | `nemoguardrails`, Colang |
| **Phase 24** | **v3.3** | **Automated PII Masking & Data Sanitization Pipeline** | Python Regex Engine, Presidio/ONNX |
| **Phase 25** | **v3.4** | **AI Red-Teaming & Adversarial Benchmark Suite** | Automated Fuzzing, Security Evaluator |
| **Phase 26** | **v3.5** | **Enterprise RBAC & Tamper-Evident Audit Logging** | SQLAlchemy RBAC, Structured Audit Trail |
| **Phase 27** | **v3.6** | **Production Traffic Shadowing ("Golden Set Harvester")** | Async Telemetry Gateway, Harvester UI |
