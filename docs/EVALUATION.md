# RAGBench — Evaluation Metric Engine & Analytics Specification

This document defines the mathematical foundations, evaluator gates, and analytical formulas used by RAGBench to compute model performance, the 5-axis Radar Comparison, and the Pareto Efficiency Frontier.

---

## 1. Core Evaluator Gates

RAGBench operates a two-tiered evaluation engine combining fast deterministic checks with semantic LLM-as-a-judge scorers:

### 1.1 Deterministic Evaluators
- **Exact Match (`exact_match`):** Binary string parity normalized for whitespace and lowercasing:
  $$\text{score} = \begin{cases} 1.0 & \text{if } \text{clean}(\text{pred}) = \text{clean}(\text{gold}) \\ 0.0 & \text{otherwise} \end{cases}$$
- **Hit Rate (`hit_rate`):** Binary retrieval gate verifying if at least one retrieved context snippet matches ground-truth context:
  $$\text{score} = \begin{cases} 1.0 & \text{if } |\text{retrieved} \cap \text{ground\_truth}| > 0 \\ 0.0 & \text{otherwise} \end{cases}$$
- **Performance Budget (`performance_budget`):** Verification whether query execution satisfied standard latency SLA ($\le 2000\text{ ms}$):
  $$\text{score} = \begin{cases} 1.0 & \text{if } \text{latency} \le 2000\text{ ms} \\ 0.0 & \text{otherwise} \end{cases}$$

### 1.2 LLM-as-a-Judge Evaluators
- **Faithfulness:** Claim extraction and factual verification against retrieved context (0.0 to 1.0).
- **Answer Relevancy:** Query-to-response semantic alignment score (0.0 to 1.0).
- **Hallucination Rate:** Percentage of non-factual or ungrounded assertions generated ($1.0 - \text{Faithfulness}$).

---

## 2. Analytics & Visual Radar Mathematical Formulas

Located in `src/ragbench/evaluators/analytics.py`.

### 2.1 Composite Quality Score
The aggregate quality of an experiment across all non-latency, non-cost quality gates:
$$\text{Composite Score} = \frac{1}{|K|}\sum_{k \in K} \text{score}_k$$
*Where $K$ represents all evaluated quality metric dimensions (e.g., Exact Match, Hit Rate, Performance Budget, Faithfulness, Relevancy).*

### 2.2 Latency Efficiency Normalization
In quality charts, higher is always better (1.0 = best, 0.0 = worst). To map raw latency (milliseconds) onto this scale, RAGBench normalizes against a standard **2,000 ms SLA budget**:

$$\text{Latency Efficiency Score} = \operatorname{round}\left(\max\left(0.0, \min\left(1.0, 1.0 - \frac{\text{latency}_{\text{ms}}}{2000.0}\right)\right), 3\right)$$

- If $\text{latency} = 0\text{ ms} \implies \text{Score} = 1.000$ (Instant response, 100% efficient)
- If $\text{latency} = 1000\text{ ms} \implies \text{Score} = 0.500$ (50% budget utilized)
- If $\text{latency} \ge 2000\text{ ms} \implies \text{Score} = 0.000$ (Budget exhausted)

### 2.3 Cost Efficiency Normalization
To map financial token costs onto the 0.0 – 1.0 scale, RAGBench normalizes against a **\$0.005 (half a cent) budget ceiling** per query:

$$\text{Cost Efficiency Score} = \operatorname{round}\left(\max\left(0.0, \min\left(1.0, 1.0 - \frac{\text{cost}_{\text{USD}}}{\$0.005}\right)\right), 3\right)$$

- If $\text{cost} = \$0.00000 \implies \text{Score} = 1.000$ (Free / 100% budget preserved)
- If $\text{cost} = \$0.00250 \implies \text{Score} = 0.500$ (50% budget preserved)
- If $\text{cost} \ge \$0.00500 \implies \text{Score} = 0.000$ (Budget ceiling exceeded)

### 2.4 Candidate vs. Baseline Delta
$$\text{Delta} = \text{Score}_{\text{Candidate}} - \text{Score}_{\text{Baseline}}$$
- **Positive Delta ($+$):** Candidate improved upon the baseline standard (rendered in **green**).
- **Negative Delta ($-$):** Candidate regressed or proved more resource-intensive (rendered in **red**).

---

## 3. Mathematical Pareto Non-Dominated Frontier

An evaluation run $P$ is plotted at coordinate $(\text{Latency}(P), \text{Composite}(P))$.

A candidate model $P$ is **dominated** by another model $Q$ if and only if:
1. $Q.\text{composite\_score} \ge P.\text{composite\_score}$
2. $Q.\text{latency\_ms} \le P.\text{latency\_ms}$
3. At least one of the above inequalities is strict ($>$ or $<$).

A model $P$ is defined as **Pareto-Optimal** if no other evaluated run in the workspace dominates it:
$$\text{Pareto}(P) \iff \nexists Q \in \text{Workspace} : Q \succ P$$

---

## 4. Worked Numerical Example (Production Run)

| Dimension | Raw Candidate (Groq 120B) | Raw Baseline (Fast Baseline) | Normalized Candidate | Normalized Baseline | Delta | Formula Used |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Faithfulness** | 0.3333 composite | 0.3333 composite | `0.333` | `0.333` | `+0.000` | Composite fallback $(0.0 + 0.0 + 1.0)/3$ |
| **Answer Relevancy** | 0.3333 composite | 0.3333 composite | `0.333` | `0.333` | `+0.000` | Composite fallback $(0.0 + 0.0 + 1.0)/3$ |
| **Exact Match** | 0.0 match | 0.0 match | `0.000` | `0.000` | `+0.000` | Exact string gate score |
| **Latency Efficiency** | 1035.1 ms | 0.0 ms | `0.482` | `1.000` | `-0.518` | $1.0 - (1035.1 / 2000)$ |
| **Cost Efficiency** | \$0.00028 USD | \$0.00001 USD | `0.944` | `0.998` | `-0.054` | $1.0 - (0.00028 / 0.005)$ |

---

## 5. Agent Trajectory & Loop Inspector Mathematical Specification

Located in `src/ragbench/evaluators/agent/trajectory.py` and exposed via `/api/v1/agent/evaluate-trajectory`.

### 5.1 Comprehensive Pass / Fail Gate Formula
An autonomous agent trajectory is granted an **Approved (PASS)** verdict if and only if all three diagnostic conditions are satisfied:

$$\text{Verdict} = \text{PASS} \iff (\neg \text{loop\_detected}) \land (\text{Tool Recall} \ge 0.80) \land (\text{Efficiency Score} \ge 0.50)$$

If an infinite loop occurs, or if mandatory security tools are skipped ($\text{Recall} < 0.80$), or if the agent wanders taking $\ge 6$ excess steps ($\text{Efficiency} < 0.50$), the verdict is strictly **`BLOCKED (FAILED)`**.

---

### 5.2 Infinite Tool Call Loop & Redundancy Detection
To prevent agents from burning LLM tokens in repetitive failure cycles, RAGBench computes an exact signature for each tool call:

$$\text{sig}(t) = \left( t.\text{name}, \text{canonical\_json}(t.\text{arguments}) \right)$$

1. **Consecutive Invocation Rule:**
   $$\text{loop}_{\text{consecutive}} \iff \exists i \in [1, N-1] : \text{sig}(t_i) = \text{sig}(t_{i+1})$$

2. **Frequency Threshold Rule:**
   $$\text{loop}_{\text{frequency}} \iff \max_{s \in \text{Signatures}} \text{count}(s) \ge \text{loop\_threshold} \quad (\text{default} = 2)$$

$$\text{loop\_detected} = \text{loop}_{\text{consecutive}} \lor \text{loop}_{\text{frequency}}$$

Redundant invocations are tracked per step:
$$\text{Redundant Count} = \sum_{s \in \text{Signatures}} \max(0, \text{count}(s) - 1)$$

---

### 5.3 Tool Precision, Recall & Selection Accuracy
When a set of required or expected tools $\mathcal{T}_{\text{expected}}$ is defined (such as authentication, KYC, or specific API lookups):

1. **Tool Coverage (Recall):**
   $$\text{Tool Recall} = \begin{cases} 1.0 & \text{if } |\mathcal{T}_{\text{expected}}| = 0 \\ \frac{|\mathcal{T}_{\text{invoked}} \cap \mathcal{T}_{\text{expected}}|}{|\mathcal{T}_{\text{expected}}|} & \text{otherwise} \end{cases}$$
   *If $\text{Tool Recall} < 0.80$, the agent fails due to missing critical security or workflow tools.*

2. **Tool Specificity (Precision):**
   $$\text{Tool Precision} = \begin{cases} 1.0 & \text{if } |\mathcal{T}_{\text{invoked}}| = 0 \\ \frac{|\mathcal{T}_{\text{invoked}} \cap \mathcal{T}_{\text{expected}}|}{|\mathcal{T}_{\text{invoked}}|} & \text{otherwise} \end{cases}$$

3. **Tool Selection Accuracy:**
   The proportion of actual step executions that invoked an expected benchmark tool:
   $$\text{Accuracy} = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}(t_i.\text{name} \in \mathcal{T}_{\text{expected}})$$

---

### 5.4 Path Efficiency & Wandering Penalization
Measures whether the agent solved the user goal along an optimal path or wasted execution latency wandering through irrelevant queries:

$$\text{Step Penalty} = \max\left(0, N_{\text{actual}} - M_{\text{optimal}}\right) \times 0.10$$

$$\text{Path Efficiency Score} = \max\left(0.0, \operatorname{round}\left(1.0 - \text{Step Penalty}, 2\right)\right)$$

* **Optimal:** $N_{\text{actual}} \le M_{\text{optimal}} \implies \text{Score} = 1.00$
* **Sub-optimal:** $N_{\text{actual}} = M_{\text{optimal}} + 4 \implies \text{Score} = 0.60$ (Sub-optimal, yellow warning)
* **Critical Inefficiency (FAIL):** $N_{\text{actual}} \ge M_{\text{optimal}} + 6 \implies \text{Score} \le 0.40 < 0.50 \implies \mathbf{BLOCKED}$

