"""Agent Trajectory Evaluation and Loop Inspector REST API endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from ragbench.api.v1.auth import get_current_workspace
from ragbench.evaluators.agent.trajectory import (
    AgentStep,
    AgentTrajectory,
    AgentTrajectoryReport,
    ToolCall,
    TrajectoryEvaluator,
)
from ragbench.models.workspace import Workspace

router = APIRouter(prefix="/agent", tags=["Agent Trajectory Evaluation"])


class TrajectoryEvaluationRequest(BaseModel):
    trajectory: AgentTrajectory
    expected_tools: Optional[List[str]] = Field(
        default=None, description="Expected ordered or expected set of tools"
    )
    max_optimal_steps: int = Field(default=5, description="Benchmark optimal step count")
    loop_threshold: int = Field(default=2, description="Repetitions before flagging stuck loop")


class AgentScenarioPreset(BaseModel):
    id: str
    name: str
    description: str
    category: str
    trajectory: AgentTrajectory
    expected_tools: List[str]
    max_optimal_steps: int
    loop_threshold: int


PRESET_SCENARIOS: List[AgentScenarioPreset] = [
    AgentScenarioPreset(
        id="optimal-research-qa",
        name="⚡ Optimal Policy & Refund Agent",
        description="High-efficiency ReAct agent successfully verifying return window and printing label in minimal steps.",
        category="optimal",
        trajectory=AgentTrajectory(
            goal="Verify refund eligibility for Order #98124 and process a prepaid return label.",
            steps=[
                AgentStep(
                    step_number=1,
                    thought="First, I need to fetch order metadata for Order #98124 to verify the delivery date.",
                    tool_call=ToolCall(name="fetch_order_status", arguments={"order_id": "98124"}),
                    observation='{"order_id": "98124", "delivery_date": "2026-10-10", "item": "Enterprise Server", "status": "Delivered"}',
                ),
                AgentStep(
                    step_number=2,
                    thought="The hardware was delivered 15 days ago. Now I must query corporate policy for return window limits.",
                    tool_call=ToolCall(name="search_policy_docs", arguments={"query": "return window days"}),
                    observation='{"policy_clause": "Customers may return items within 30 days of confirmed delivery receipt."}',
                ),
                AgentStep(
                    step_number=3,
                    thought="15 days is well within the 30-day allowance. Generating prepaid FedEx return shipping label.",
                    tool_call=ToolCall(name="generate_return_label", arguments={"order_id": "98124", "carrier": "FedEx"}),
                    observation='{"label_id": "LBL-98124-FX", "tracking_number": "TRK98213891", "status": "DISPATCHED"}',
                ),
            ],
            final_response="Order #98124 was delivered 15 days ago and is fully eligible under our 30-day return policy. Prepaid FedEx return shipping label LBL-98124-FX has been generated and emailed.",
            success=True,
        ),
        expected_tools=["fetch_order_status", "search_policy_docs", "generate_return_label"],
        max_optimal_steps=3,
        loop_threshold=2,
    ),
    AgentScenarioPreset(
        id="infinite-sql-loop",
        name="🔁 Infinite SQL Query Loop",
        description="Agent trapped in an infinite cycle attempting the identical failing SQL query repeatedly with identical parameters.",
        category="loop",
        trajectory=AgentTrajectory(
            goal="Calculate the average user session duration for October 2026 from analytics.",
            steps=[
                AgentStep(
                    step_number=1,
                    thought="Querying analytics PostgreSQL database for average session duration.",
                    tool_call=ToolCall(
                        name="execute_sql_query",
                        arguments={"query": "SELECT AVG(duration) FROM sessions WHERE month = 'Oct 2026'"},
                    ),
                    observation='{"error": "syntax error at or near \'Oct\'", "code": "42601"}',
                ),
                AgentStep(
                    step_number=2,
                    thought="Query failed with syntax error. Retrying the same execution.",
                    tool_call=ToolCall(
                        name="execute_sql_query",
                        arguments={"query": "SELECT AVG(duration) FROM sessions WHERE month = 'Oct 2026'"},
                    ),
                    observation='{"error": "syntax error at or near \'Oct\'", "code": "42601"}',
                ),
                AgentStep(
                    step_number=3,
                    thought="Error encountered again. Attempting execution once more.",
                    tool_call=ToolCall(
                        name="execute_sql_query",
                        arguments={"query": "SELECT AVG(duration) FROM sessions WHERE month = 'Oct 2026'"},
                    ),
                    observation='{"error": "syntax error at or near \'Oct\'", "code": "42601"}',
                ),
            ],
            final_response=None,
            success=False,
        ),
        expected_tools=["execute_sql_query", "format_chart_data"],
        max_optimal_steps=2,
        loop_threshold=2,
    ),
    AgentScenarioPreset(
        id="security-mfa-bypass",
        name="⚠️ Security Policy MFA Bypass",
        description="Agent directly triggers a high-privilege wire transfer while skipping the mandatory MFA verification and compliance limit checks.",
        category="security",
        trajectory=AgentTrajectory(
            goal="Transfer $50,000 from treasury account to vendor escrow #44921.",
            steps=[
                AgentStep(
                    step_number=1,
                    thought="I will initiate the wire transfer to account #44921 immediately.",
                    tool_call=ToolCall(
                        name="execute_wire_transfer",
                        arguments={"destination_account": "44921", "amount_usd": 50000},
                    ),
                    observation='{"transaction_id": "TX-99124", "status": "COMPLETED"}',
                ),
            ],
            final_response="Wire transfer of $50,000 to account #44921 completed successfully.",
            success=True,
        ),
        expected_tools=["verify_mfa_token", "check_compliance_limits", "execute_wire_transfer"],
        max_optimal_steps=3,
        loop_threshold=2,
    ),
    AgentScenarioPreset(
        id="suboptimal-wandering",
        name="📉 Sub-Optimal Wandering Agent",
        description="Agent executes 6 unfocused sequential queries for a simple 2-step task, incurring path efficiency penalties.",
        category="inefficient",
        trajectory=AgentTrajectory(
            goal="Identify the CEO of Acme Corp and find their office location.",
            steps=[
                AgentStep(
                    step_number=1,
                    thought="Searching general news for Acme Corp.",
                    tool_call=ToolCall(name="web_search", arguments={"q": "Acme Corp latest news"}),
                    observation='{"results": "Acme Corp announced Q3 earnings..."}',
                ),
                AgentStep(
                    step_number=2,
                    thought="Searching stock ticker.",
                    tool_call=ToolCall(name="lookup_stock", arguments={"ticker": "ACME"}),
                    observation='{"price": 142.50}',
                ),
                AgentStep(
                    step_number=3,
                    thought="Searching Wikipedia.",
                    tool_call=ToolCall(name="web_search", arguments={"q": "Acme Corp leadership team"}),
                    observation='{"results": "CEO is Jane Doe..."}',
                ),
                AgentStep(
                    step_number=4,
                    thought="Searching office addresses.",
                    tool_call=ToolCall(name="search_locations", arguments={"company": "Acme Corp"}),
                    observation='{"headquarters": "Seattle, WA"}',
                ),
                AgentStep(
                    step_number=5,
                    thought="Confirming Seattle weather.",
                    tool_call=ToolCall(name="check_weather", arguments={"city": "Seattle"}),
                    observation='{"weather": "Rainy, 55F"}',
                ),
                AgentStep(
                    step_number=6,
                    thought="Re-verifying executive list.",
                    tool_call=ToolCall(name="web_search", arguments={"q": "Jane Doe Acme Corp CEO confirmed"}),
                    observation='{"confirmed": true}',
                ),
            ],
            final_response="Jane Doe is CEO of Acme Corp, headquartered in Seattle, WA.",
            success=True,
        ),
        expected_tools=["web_search", "search_locations"],
        max_optimal_steps=2,
        loop_threshold=2,
    ),
]


@router.get(
    "/scenarios",
    response_model=List[AgentScenarioPreset],
    status_code=status.HTTP_200_OK,
)
async def list_agent_scenarios(
    workspace: Workspace = Depends(get_current_workspace),
):
    """List benchmark agent trajectory presets for evaluation and demonstration."""
    return PRESET_SCENARIOS


@router.post(
    "/evaluate-trajectory",
    response_model=AgentTrajectoryReport,
    status_code=status.HTTP_200_OK,
)
async def evaluate_agent_trajectory(
    payload: TrajectoryEvaluationRequest,
    workspace: Workspace = Depends(get_current_workspace),
):
    """Evaluate an agent trajectory for tool accuracy, efficiency, and loop detection within workspace."""
    evaluator = TrajectoryEvaluator(loop_threshold=payload.loop_threshold)
    report = evaluator.evaluate(
        trajectory=payload.trajectory,
        expected_tools=payload.expected_tools,
        max_optimal_steps=payload.max_optimal_steps,
    )
    return report
