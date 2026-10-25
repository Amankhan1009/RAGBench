"""Pareto frontier calculation, radar dimensions, and quality analytics engine."""
import uuid
from typing import Dict, List, Optional, Tuple

from ragbench.models.experiment import Experiment
from ragbench.schemas.analytics import (
    ParetoAnalyticsResponse,
    ParetoPoint,
    RadarDimension,
    TrendPoint,
)


def _compute_experiment_metrics(exp: Experiment) -> Tuple[float, float, float, int, Dict[str, float]]:
    """Extract composite score, latency, cost, tokens, and detailed metric averages for an experiment."""
    if not exp.items:
        return 0.0, 0.0, 0.0, 0, {}

    total_latency = 0.0
    total_cost = 0.0
    total_tokens = 0
    metric_sums: Dict[str, float] = {}
    metric_counts: Dict[str, int] = {}

    for item in exp.items:
        total_latency += getattr(item, "latency_ms", 0.0) or 0.0
        total_cost += getattr(item, "cost_usd", 0.0) or 0.0
        total_tokens += getattr(item, "total_tokens", 0) or 0

        raw_metrics = getattr(item, "metrics", {}) or {}
        for k, v in raw_metrics.items():
            score = v.get("score") if isinstance(v, dict) else v
            if isinstance(score, (int, float)):
                metric_sums[k] = metric_sums.get(k, 0.0) + float(score)
                metric_counts[k] = metric_counts.get(k, 0) + 1

    count = len(exp.items)
    avg_latency = round(total_latency / count, 2)
    avg_cost = round(total_cost / count, 6)
    avg_tokens = int(total_tokens / count)

    avg_metrics = {
        k: round(metric_sums[k] / metric_counts[k], 4)
        for k in metric_sums
        if metric_counts[k] > 0
    }

    # Compute composite quality score (average of standard quality metrics)
    quality_keys = [k for k in avg_metrics if "latency" not in k.lower() and "token" not in k.lower() and "cost" not in k.lower()]
    if quality_keys:
        composite = round(sum(avg_metrics[k] for k in quality_keys) / len(quality_keys), 4)
    else:
        composite = 0.0

    return composite, avg_latency, avg_cost, avg_tokens, avg_metrics


def calculate_pareto_frontier(
    experiments: List[Experiment],
    candidate_id: Optional[uuid.UUID] = None
) -> ParetoAnalyticsResponse:
    """Analyze evaluation experiments and compute Pareto efficiency frontier and comparative analytics."""
    points: List[ParetoPoint] = []
    baseline_exp: Optional[Experiment] = None
    candidate_exp: Optional[Experiment] = None

    for exp in experiments:
        if exp.is_baseline and baseline_exp is None:
            baseline_exp = exp
        if candidate_id and exp.id == candidate_id:
            candidate_exp = exp

        composite, latency, cost, tokens, metrics = _compute_experiment_metrics(exp)
        points.append(
            ParetoPoint(
                experiment_id=exp.id,
                name=exp.name,
                model_name=exp.model_name,
                provider_name=exp.provider_name,
                composite_score=composite,
                latency_ms=latency,
                cost_usd=cost,
                total_tokens=tokens,
                metrics=metrics,
                is_pareto_optimal=False,
                is_baseline=exp.is_baseline,
                created_at=exp.created_at,
            )
        )

    # If no candidate specifically requested, pick the latest non-baseline experiment
    if not candidate_exp and points:
        for exp in reversed(experiments):
            if not exp.is_baseline:
                candidate_exp = exp
                break

    # 1. Determine Pareto Frontier Points
    # A point P is dominated if another point Q has Q.score >= P.score and Q.latency <= P.latency
    # with at least one strict inequality.
    pareto_frontier: List[ParetoPoint] = []
    for i, p in enumerate(points):
        is_dominated = False
        for j, q in enumerate(points):
            if i == j:
                continue
            better_or_equal_score = q.composite_score >= p.composite_score
            better_or_equal_latency = q.latency_ms <= p.latency_ms
            strictly_better = (q.composite_score > p.composite_score) or (q.latency_ms < p.latency_ms)

            if better_or_equal_score and better_or_equal_latency and strictly_better:
                is_dominated = True
                break

        if not is_dominated:
            p.is_pareto_optimal = True
            pareto_frontier.append(p)

    # Sort Pareto frontier by latency ascending (fastest to most accurate)
    pareto_frontier.sort(key=lambda p: (p.latency_ms, -p.composite_score))

    # 2. Compute Radar Dimensions (Candidate vs Baseline)
    radar_comparison: Optional[List[RadarDimension]] = None
    if baseline_exp and candidate_exp:
        c_comp, c_lat, c_cost, c_tokens, c_met = _compute_experiment_metrics(candidate_exp)
        b_comp, b_lat, b_cost, b_tokens, b_met = _compute_experiment_metrics(baseline_exp)

        # Normalized latency score (lower latency = higher score up to 2000ms budget)
        c_lat_score = round(max(0.0, min(1.0, 1.0 - (c_lat / 2000.0))), 3)
        b_lat_score = round(max(0.0, min(1.0, 1.0 - (b_lat / 2000.0))), 3)

        # Normalized cost score (lower cost = higher score up to $0.005 budget)
        c_cost_score = round(max(0.0, min(1.0, 1.0 - (c_cost / 0.005))), 3)
        b_cost_score = round(max(0.0, min(1.0, 1.0 - (b_cost / 0.005))), 3)

        radar_comparison = [
            RadarDimension(
                dimension="Faithfulness",
                candidate_score=c_met.get("faithfulness", c_comp),
                baseline_score=b_met.get("faithfulness", b_comp),
            ),
            RadarDimension(
                dimension="Answer Relevancy",
                candidate_score=c_met.get("answer_relevancy", c_met.get("relevancy", c_comp)),
                baseline_score=b_met.get("answer_relevancy", b_met.get("relevancy", b_comp)),
            ),
            RadarDimension(
                dimension="Exact Match / Accuracy",
                candidate_score=c_met.get("exact_match", c_comp),
                baseline_score=b_met.get("exact_match", b_comp),
            ),
            RadarDimension(
                dimension="Latency Efficiency",
                candidate_score=c_lat_score,
                baseline_score=b_lat_score,
            ),
            RadarDimension(
                dimension="Cost Efficiency",
                candidate_score=c_cost_score,
                baseline_score=b_cost_score,
            ),
        ]

    # 3. Compute Historical Trends
    trends = [
        TrendPoint(
            experiment_id=p.experiment_id,
            name=p.name,
            timestamp=p.created_at.strftime("%b %d, %H:%M"),
            composite_score=p.composite_score,
            latency_ms=p.latency_ms,
            is_baseline=p.is_baseline,
        )
        for p in sorted(points, key=lambda x: x.created_at)
    ]

    return ParetoAnalyticsResponse(
        total_experiments=len(points),
        points=points,
        pareto_frontier=pareto_frontier,
        radar_comparison=radar_comparison,
        candidate_name=candidate_exp.name if candidate_exp else None,
        baseline_name=baseline_exp.name if baseline_exp else None,
        trends=trends,
    )

