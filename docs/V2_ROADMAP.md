# RAGBench v2.0 — Product & Technical Roadmap

## Executive Summary
Following the production deployment of **RAGBench v1.0** on Render, the **v2.0 Milestone** evolves RAGBench from a core benchmarking MVP into an **enterprise-grade evaluation and observability platform**.

This document outlines the architecture, data contracts, UI components, and implementation plan for the **5 major features** planned for v2.0.

---

## 1. Interactive Visual Analytics & Pareto Frontier

### 1.1 Objective
Provide data-driven, interactive visualizations that allow engineering teams to instantly identify optimal model trade-offs between **Quality**, **Latency**, and **Inference Cost**.

### 1.2 Key Components
1. **Pareto Frontier Scatter Plot (Quality vs. Cost/Latency):**
   - **X-Axis:** Latency (ms) or Token Cost ($ per 1,000 queries).
   - **Y-Axis:** Composite Evaluation Score (0.0 to 1.0).
   - **Frontier Curve:** Dynamically draws the Pareto efficiency boundary, highlighting models that offer the highest quality per dollar or millisecond (e.g., `openai/gpt-oss-120b` vs `gpt-4o-mini`).
2. **Metric Radar Chart (Spider Chart):**
   - Side-by-side polygon comparison comparing **Candidate Model** against **Baseline Model** across 6 core dimensions:
     - Faithfulness
     - Answer Relevancy
     - Groundedness / Context Overlap
     - Retrieval Hit Rate
     - Latency Budget Compliance
     - Cost Budget Compliance
3. **Historical Regression Trend Lines:**
   - Time-series tracking of metric scores across git commits, dataset versions, and evaluation dates.

### 1.3 Technical Architecture
- **Frontend:** Lightweight SVG / Recharts data visualization components embedded into the `Experiments & Runs` and `Regression & CI Gates` tabs.
- **Backend API:** `GET /api/v1/experiments/analytics/pareto` returning aggregated latency, cost, and metric averages per model.

---

## 2. Real-Time Streaming & Live Evaluation Progress (SSE)

### 2.1 Objective
Eliminate static waiting spinners during large benchmark runs. Deliver real-time, per-sample progress updates with live latency, token speed, and metric streaming.

### 2.2 Key Components
1. **Server-Sent Events (SSE) Endpoint:**
   - Replace or augment blocking `POST /api/v1/experiments` with `POST /api/v1/experiments/stream`.
   - Protocol: `text/event-stream` emitting structured JSON payloads as each dataset sample finishes evaluation.
2. **Live Animated Progress Bar:**
   - Shows current execution status: `Evaluating item 4 of 25... [openai/gpt-oss-120b | Latency: 185ms | Faithfulness: 0.96]`.
   - Calculates live estimated time remaining (ETA).
3. **Live Table Row Rendering:**
   - Table rows appear and animate into view dynamically as they complete, rather than waiting for the entire batch to complete.

### 2.3 Data Contract (SSE Stream Event)
```json
{
  "event": "sample_completed",
  "data": {
    "sample_index": 4,
    "total_samples": 25,
    "query": "What is the return policy?",
    "latency_ms": 185.4,
    "tokens": 42,
    "cost_usd": 0.00003,
    "metrics": {
      "faithfulness": 0.96,
      "relevancy": 1.0,
      "exact_match": 0.0
    }
  }
}
```

---

## 3. Synthetic AI Test Dataset Generator

### 3.1 Objective
Solve the primary bottleneck in production RAG development: **the scarcity of high-quality evaluation datasets**. Allow developers to generate comprehensive test sets directly from unstructured documentation in seconds.

### 3.2 Key Components
1. **Raw Document Ingestion Input:**
   - UI panel in the `Datasets` tab allowing users to paste raw text, product manuals, FAQs, or markdown articles.
2. **AI-Powered Generation Engine:**
   - Uses the user's active BYOK cloud LLM (Groq, OpenAI, Anthropic, or Google) to synthesize:
     - **Diverse Query Types:** Factual queries, multi-hop reasoning questions, negative/out-of-domain queries, and adversarial questions.
     - **Extracted Ground-Truth Contexts:** Key passages extracted from the source material.
     - **Reference Expected Answers:** Gold-standard ground truth answers for evaluation judges.
3. **One-Click Dataset Assembly:**
   - Generated items can be reviewed, edited inline, and saved into a versioned dataset collection (e.g., `KnowledgeBase-Benchmark v1.0.0`).

### 3.3 Backend API Endpoint
- `POST /api/v1/datasets/generate-synthetic`
  - **Inputs:** `raw_text`, `provider`, `model`, `num_samples`, `difficulty_distribution`.
  - **Output:** Array of generated `DatasetItemCreate` schemas.

---

## 4. One-Click Ingestion (CSV / JSONL) & Executive Report Export

### 4.1 Objective
Enable seamless interoperability with existing industry datasets and provide shareable executive reports for engineering leadership and CI/CD releases.

### 4.2 Key Components
1. **File Drag-and-Drop Uploader:**
   - Ingest CSV, JSON, and JSONL files matching standard benchmark formats (e.g., HuggingFace datasets, RAGBench format, SQuAD-like formats).
   - Automated column mapping modal (map `query`, `contexts`, `expected_output`).
2. **Executive Benchmark Export Engine:**
   - **Markdown Export:** Clean, GitHub-formatted report ready to paste into Pull Requests or issue trackers.
   - **PDF / Printable Report:** Structured summary including:
     - Executive verdict (Pass / Regressed).
     - Candidate vs Baseline delta tables with color-coded badges.
     - Latency, token count, and USD cost summaries.
     - Detailed failure analysis for samples that regressed below threshold.
3. **Raw Data Export:**
   - Export full experiment execution logs to CSV or JSONL for downstream data science analysis in Jupyter or Pandas.

---

## 5. Dedicated Agent Trajectory & Loop Inspector UI

### 5.1 Objective
Expand RAGBench from pure RAG evaluation into **Agentic AI Benchmarking**, offering a visual timeline and automated diagnostic suite for multi-step agent workflows.

### 5.2 Key Components
1. **Visual Execution Timeline (Graph / Flow):**
   - Renders step-by-step agent trajectories: `Thought -> Action (Tool Call) -> Observation (Output) -> Final Answer`.
   - Inspect tool input parameters and returned outputs at each step.
2. **Automated Diagnostic Badges:**
   - 🔁 **Infinite Loop Warning:** Flags when an agent repeats identical tool calls with identical arguments exceeding the loop threshold.
   - ⚠️ **Missing Expected Tools:** Highlights when an agent failed to call required validation or retrieval tools.
   - 📉 **Sub-optimal Path Alert:** Measures total step count against the benchmark optimal trajectory.
3. **Agent Benchmark Hub:**
   - Dedicated tab or sub-view in the dashboard for running and comparing multi-step agent tasks.

---

## Implementation Roadmap & Milestones

| Phase | Feature Description | Complexity | Target Release |
| :--- | :--- | :--- | :--- |
| **Phase 16** | Interactive Visual Analytics & Pareto Frontier | Medium | v2.1 |
| **Phase 17** | Real-Time SSE Streaming & Live Progress Bar | Medium | v2.2 |
| **Phase 18** | Synthetic AI Test Dataset Generator | Medium-High | v2.3 |
| **Phase 19** | Dataset Ingestion (CSV/JSONL) & Report Export | Medium | v2.4 |
| **Phase 20** | Agent Trajectory Visualization & Loop Inspector UI | High | v2.5 |
