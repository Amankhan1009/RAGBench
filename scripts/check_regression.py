"""
RAGBench Standalone CI/CD Regression Gate Script.
Queries the RAGBench candidate vs baseline comparison and exits with 0 (PASS) or 1 (FAIL).
"""
import sys
from ragbench.evaluators.regression import RegressionDetector


def run_ci_regression_check(
    candidate_metrics: dict[str, float],
    baseline_metrics: dict[str, float],
    tolerance: float = 0.02
) -> int:
    print(f"\n[INFO] Executing RAGBench CI Regression Check [Tolerance: {tolerance}]...")
    detector = RegressionDetector(tolerance=tolerance)
    report = detector.detect_regression(candidate_metrics, baseline_metrics)

    print("\n--- METRIC EVALUATION DELTAS ---")
    for metric, data in report.details.items():
        status_str = "❌ REGRESSED" if data["regressed"] else "✅ OK"
        print(f"  [{status_str}] {metric:20s} | Candidate: {data['candidate_score']:.4f} | Baseline: {data['baseline_score']:.4f} | Delta: {data['delta']:+.4f}")

    if report.has_regression:
        print(f"\n[FAIL] Quality regression detected in metrics: {report.regressed_metrics}")
        print("       CI Gate failed. Pull request blocked.")
        return 1
    else:
        print("\n[PASS] Zero quality regression detected. CI Gate passed successfully.")
        return 0


if __name__ == "__main__":
    cand = {"exact_match": 0.95, "hit_rate": 1.0, "performance_budget": 1.0}
    base = {"exact_match": 0.90, "hit_rate": 1.0, "performance_budget": 1.0}
    sys.exit(run_ci_regression_check(cand, base))
