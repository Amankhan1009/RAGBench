"""Agent Trajectory Evaluation REST API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from ragbench.evaluators.agent.trajectory import (
    AgentTrajectory,
    AgentTrajectoryReport,
    TrajectoryEvaluator,
)

router = APIRouter(prefix="/agent", tags=["Agent Trajectory Evaluation"])


class TrajectoryEvaluationRequest(BaseModel):
    trajectory: AgentTrajectory
    expected_tools: Optional[List[str]] = Field(
        default=None, description="Expected ordered or expected set of tools"
    )
    max_optimal_steps: int = Field(default=5, description="Benchmark optimal step count")
    loop_threshold: int = Field(default=2, description="Repetitions before flagging stuck loop")


@router.post(
    "/evaluate-trajectory",
    response_model=AgentTrajectoryReport,
    status_code=status.HTTP_200_OK,
)
async def evaluate_agent_trajectory(payload: TrajectoryEvaluationRequest):
    """Evaluate an agent trajectory for tool accuracy, efficiency, and loop detection."""
    evaluator = TrajectoryEvaluator(loop_threshold=payload.loop_threshold)
    report = evaluator.evaluate(
        trajectory=payload.trajectory,
        expected_tools=payload.expected_tools,
        max_optimal_steps=payload.max_optimal_steps,
    )
    return report