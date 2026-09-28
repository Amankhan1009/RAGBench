# RAGBench — Evaluation Metric Engine Specification
## Deterministic Metrics
- **Exact Match:** Exact string parity normalized for whitespace/case.
- **Recall@K & Precision@K:** Retrieval overlap against ground truth contexts.
- **MRR & Hit Rate:** Rank order accuracy of first relevant context piece.
- **Context Overlap:** Token/n-gram jaccard similarity.
- **Latency & Token Usage:** Execution time (ms), prompt tokens, completion tokens, USD cost.
## LLM-as-a-Judge Metrics
- **Faithfulness:** Claim extraction and verification against context.
- **Answer Relevancy:** Query-response semantic alignment score (0.0 - 1.0).
- **Groundedness:** Detection of ungrounded model assertions.
- **Hallucination Rate:** Percentage of non-factual statements generated.
