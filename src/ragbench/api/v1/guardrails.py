"""REST API Endpoints for NVIDIA NeMo-compatible Guardrails, Input/Output Rails, and Colang Policies."""
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.api.v1.auth import get_current_workspace
from ragbench.core.audit import record_audit_event
from ragbench.core.rbac import AuthContext, require_evaluator
from ragbench.db.session import get_db
from ragbench.guardrails.engine import guardrails_engine
from ragbench.guardrails.schemas import (
    GuardrailCheckResult,
    GuardrailPresetScenario,
    InputRailRequest,
    OutputRailRequest,
    WorkspaceGuardrailPolicy,
)
from ragbench.models.workspace import Workspace

router = APIRouter(prefix="/guardrails", tags=["AI Security & Guardrails"])


@router.post(
    "/check-input",
    response_model=GuardrailCheckResult,
    status_code=status.HTTP_200_OK,
    summary="Inspect Prompt with Pre-Execution Input Rails",
    description="Pre-execution security inspection stopping prompt injections, jailbreaks, and system prompt leaks.",
)
async def check_input_rail(
    payload: InputRailRequest,
    workspace: Workspace = Depends(get_current_workspace),
):
    """Execute pre-execution input rails on user prompt."""
    return guardrails_engine.check_input(
        workspace_id=workspace.id,
        prompt=payload.prompt,
    )


@router.post(
    "/check-output",
    response_model=GuardrailCheckResult,
    status_code=status.HTTP_200_OK,
    summary="Inspect Generated Response with Output Rails",
    description="Post-execution hallucination detection verifying model assertions against retrieved RAG contexts.",
)
async def check_output_rail(
    payload: OutputRailRequest,
    workspace: Workspace = Depends(get_current_workspace),
):
    """Execute post-execution output rails on model response."""
    return guardrails_engine.check_output(
        workspace_id=workspace.id,
        response_text=payload.response_text,
        retrieved_contexts=payload.retrieved_contexts,
    )


@router.get(
    "/policy",
    response_model=WorkspaceGuardrailPolicy,
    status_code=status.HTTP_200_OK,
    summary="Get Workspace Guardrail Policy",
    description="Retrieve the active guardrail and topical boundary configuration for the authenticated workspace.",
)
async def get_guardrail_policy(
    workspace: Workspace = Depends(get_current_workspace),
):
    """Fetch current workspace guardrail policy."""
    return guardrails_engine.get_policy(workspace.id)


@router.post(
    "/policy",
    response_model=WorkspaceGuardrailPolicy,
    status_code=status.HTTP_200_OK,
    summary="Update Workspace Guardrail Policy",
    description="Update input rail toggles, hallucination thresholds, and Colang topical domain boundaries.",
)
async def update_guardrail_policy(
    payload: WorkspaceGuardrailPolicy,
    ctx: AuthContext = Depends(require_evaluator),
    db: AsyncSession = Depends(get_db),
):
    """Save updated guardrail policy for the current workspace."""
    updated = guardrails_engine.update_policy(ctx.workspace.id, payload)
    await record_audit_event(
        db,
        workspace_id=ctx.workspace.id,
        action="GUARDRAIL_POLICY_UPDATED",
        resource_type="guardrail",
        details=payload.model_dump(),
        user_id=ctx.user_id,
        user_email=ctx.user_email,
        ip_address=ctx.client_ip,
    )
    await db.commit()
    return updated


@router.get(
    "/presets",
    response_model=List[GuardrailPresetScenario],
    status_code=status.HTTP_200_OK,
    summary="Get Preset Adversarial Scenarios",
    description="Retrieve pre-configured attack prompts and evaluation scenarios for interactive testing.",
)
async def get_preset_scenarios():
    """Return preset adversarial test cases."""
    return guardrails_engine.get_presets()
