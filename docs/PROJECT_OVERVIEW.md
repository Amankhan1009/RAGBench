# RAGBench — System Overview & Value Proposition
## Executive Summary
RAGBench is an enterprise-grade LLM, RAG, and Agent Evaluation Platform designed to assess, benchmark, and regression-test AI outputs across deterministic metrics and LLM-as-a-judge criteria.
## Core Value Pillars
1. **Unified Provider Abstraction & BYOK:** Securely evaluation across Groq, OpenAI, Anthropic, and Google with AES-256 encrypted keys.
2. **Hybrid Evaluation Engine:** Combines exact math (Recall@K, MRR, Token Usage, Latency) with LLM judgment (Faithfulness, Relevancy, Hallucination, Groundedness).
3. **DeepEval Integration with Provider Isolation:** Delegates evaluation framework calls strictly through RAGBench's provider layer without bypassing security.
4. **Cloud-Only Reliability:** Uses Neon PostgreSQL with connection recycling and SSL `sslmode=require`.
5. **Observability & CI/CD Gates:** Full tracing via LangSmith and automated PR regression blocking in GitHub Actions.
