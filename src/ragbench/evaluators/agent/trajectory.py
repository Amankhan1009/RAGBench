"""Agent trajectory evaluation engine for multi-step agentic workflows."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class AgentStep(BaseModel):
    step_number: int
    thought: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    observation: Optional[str] = None


class AgentTrajectory(BaseModel):
    goal: str
    steps: List[AgentStep] = Field(default_factory=list)
    final_response: Optional[str] = None
    success: bool = True


class AgentTrajectoryReport(BaseModel):
    total_steps: int
    tool_selection_accuracy: float
    tool_precision: float
    tool_recall: float
    loop_detected: bool
    redundant_call_count: int
    efficiency_score: float
    passed: bool
    details: Dict[str, Any] = Field(default_factory=dict)


class TrajectoryEvaluator:
    """Evaluates agent tool usage, trajectory efficiency, loop detection, and accuracy."""

    def __init__(self, loop_threshold: int = 2):
        self.loop_threshold = loop_threshold

    def evaluate(
        self,
        trajectory: AgentTrajectory,
        expected_tools: Optional[List[str]] = None,
        max_optimal_steps: int = 5,
    ) -> AgentTrajectoryReport:
        tool_sequence = [s.tool_call.name for s in trajectory.steps if s.tool_call]
        executed_calls = [
            (s.tool_call.name, str(sorted(s.tool_call.arguments.items())))
            for s in trajectory.steps
            if s.tool_call
        ]

        # 1. Loop and Redundancy Detection
        seen_calls: Dict[tuple, int] = {}
        redundant_count = 0
        loop_detected = False

        for call in executed_calls:
            seen_calls[call] = seen_calls.get(call, 0) + 1
            if seen_calls[call] >= self.loop_threshold:
                loop_detected = True
            if seen_calls[call] > 1:
                redundant_count += 1

        # Check consecutive identical calls
        for i in range(len(executed_calls) - 1):
            if executed_calls[i] == executed_calls[i + 1]:
                loop_detected = True

        # 2. Tool Precision and Recall against Expected Tools
        if expected_tools:
            executed_unique = set(tool_sequence)
            expected_unique = set(expected_tools)
            common = executed_unique.intersection(expected_unique)

            precision = len(common) / len(executed_unique) if executed_unique else 0.0
            recall = len(common) / len(expected_unique) if expected_unique else 0.0
            accuracy = (
                1.0
                if tool_sequence == expected_tools
                else (len(common) / max(len(expected_tools), 1))
            )
        else:
            precision = 1.0
            recall = 1.0
            accuracy = 1.0

        # 3. Efficiency Score
        step_count = len(trajectory.steps)
        if step_count == 0 or step_count <= max_optimal_steps:
            efficiency = 1.0
        else:
            penalty = (step_count - max_optimal_steps) * 0.1
            efficiency = max(0.0, round(1.0 - penalty, 2))

        # Overall pass criteria: No infinite loop, recall >= 0.8, efficiency >= 0.5
        passed = (not loop_detected) and (recall >= 0.8) and (efficiency >= 0.5)

        return AgentTrajectoryReport(
            total_steps=step_count,
            tool_selection_accuracy=round(accuracy, 4),
            tool_precision=round(precision, 4),
            tool_recall=round(recall, 4),
            loop_detected=loop_detected,
            redundant_call_count=redundant_count,
            efficiency_score=efficiency,
            passed=passed,
            details={
                "tool_sequence": tool_sequence,
                "expected_tools": expected_tools or [],
                "loop_threshold": self.loop_threshold,
            },
        )
