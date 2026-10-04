# RAGBench — Active TODOs

## Version 1.0 Deployment
- [x] Master Roadmap Phases 0 through 15 are 100% COMPLETE!
- [x] Configure multi-stage Dockerfile and dynamic port binding (`${PORT:-8000}`)
- [x] Configure Render blueprint `render.yaml` with free tier settings
- [ ] Complete Render web service deployment for `ragbench-backend` and `ragbench-frontend`

---

## Version 2.0 Feature Backlog (Post-Deployment)
*Detailed specifications: [`docs/V2_ROADMAP.md`](V2_ROADMAP.md)*

### Phase 16: Interactive Visual Analytics & Pareto Frontier
- [ ] Implement Pareto Frontier scatter plot (Composite Quality vs Latency/Cost)
- [ ] Implement 6-dimensional Radar Chart comparing Candidate vs Baseline
- [ ] Add historical regression timeline chart

### Phase 17: Live Evaluation Streaming (SSE)
- [ ] Implement `POST /api/v1/experiments/stream` Server-Sent Events endpoint
- [ ] Add frontend animated progress bar showing item-by-item completion
- [ ] Render live incoming rows dynamically during evaluation execution

### Phase 18: Synthetic AI Test Dataset Generator
- [ ] Implement `POST /api/v1/datasets/generate-synthetic` using BYOK LLM
- [ ] Add raw text / documentation input panel in Datasets tab
- [ ] Implement one-click review and dataset creation flow

### Phase 19: Dataset Ingestion & Executive Report Export
- [ ] Add drag-and-drop CSV / JSONL benchmark dataset uploader
- [ ] Add column-mapping modal for custom dataset formats
- [ ] Implement "Export Executive Report" (Markdown & printable PDF/HTML)
- [ ] Add raw experiment export to JSON / CSV

### Phase 20: Agent Trajectory Visual Timeline UI
- [ ] Build interactive visual execution timeline component
- [ ] Render step-by-step tool calls, parameters, and observations
- [ ] Add automated diagnostic flags for loops, missing tools, and step optimality
