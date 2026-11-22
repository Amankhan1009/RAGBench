# RAGBench — Active TODOs

## Version 1.0 Deployment
- [x] Master Roadmap Phases 0 through 15 are 100% COMPLETE!
- [x] Configure multi-stage Dockerfile and dynamic port binding (`${PORT:-8000}`)
- [x] Configure Render blueprint `render.yaml` with free tier settings
- [ ] Complete Render web service deployment for `ragbench-backend` and `ragbench-frontend`

---

## Version 2.0 Feature Backlog (Completed)
*Detailed specifications: [`docs/V2_ROADMAP.md`](V2_ROADMAP.md)*

### Phase 16: Multi-Tenant Isolation & Workspace-Scoped Sessions
- [x] Implement multi-tenant isolation, workspace foreign keys, and private data partitions

### Phase 17: Interactive Visual Analytics & Pareto Frontier
- [x] Implement Pareto Frontier scatter plot (Composite Quality vs Latency/Cost)
- [x] Implement 5-dimensional Radar Chart comparing Candidate vs Baseline
- [x] Add historical regression timeline chart

### Phase 18: Live Evaluation Streaming (SSE)
- [x] Implement `POST /api/v1/experiments/stream` Server-Sent Events endpoint
- [x] Add frontend animated progress bar showing item-by-item completion
- [x] Render live incoming rows dynamically during evaluation execution

### Phase 19: Synthetic AI Test Dataset Generator
- [x] Implement `POST /api/v1/datasets/generate-synthetic` using BYOK LLM
- [x] Add raw text / documentation input panel in Datasets tab
- [x] Implement one-click review and dataset creation flow

### Phase 20: Dataset Ingestion & Executive Report Export
- [x] Add drag-and-drop CSV / JSONL benchmark dataset uploader
- [x] Add column-mapping modal for custom dataset formats
- [x] Implement "Export Executive Report" (Markdown & printable PDF/HTML)
- [x] Add raw experiment export to JSON / CSV

### Phase 21: Agent Trajectory Visual Timeline UI
- [x] Build interactive visual execution timeline component
- [x] Render step-by-step tool calls, parameters, and observations
- [x] Add automated diagnostic flags for loops, missing tools, and step optimality

---

## Version 3.0 Roadmap (Enterprise AI Security, Guardrails & Gateway)
*Detailed specifications: [`docs/V3_SECURITY_ROADMAP.md`](V3_SECURITY_ROADMAP.md)*

- [x] **Universal Custom HTTP Webhook Provider (v3.0.1)**
- [x] **Phase 22 — Portkey Open-Source AI Gateway & Semantic Cache (v3.1)**
- [x] **Phase 23 — NVIDIA NeMo Guardrails Engine (Input/Output/Colang) (v3.2)**
- [x] **Phase 24 — Automated PII Masking & Data Sanitization Pipeline (v3.3)**
- [x] **Phase 25 — AI Red-Teaming & Adversarial Benchmark Suite (v3.4)**
- [x] **Phase 26 — Enterprise RBAC & Tamper-Evident Audit Logging (v3.5)**
- [ ] **Phase 27 — Production Traffic Shadowing ("Golden Set Harvester") (v3.6)**
