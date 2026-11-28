"""REST API Endpoints for NVIDIA NeMo-compatible Guardrails, Input/Output Rails, and Colang Policies."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
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
from ragbench.providers.webhook import WebhookProvider

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


class GuardrailWebhookProbeRequest(BaseModel):
    webhook_url: str = Field(..., min_length=1, description="Custom HTTP/HTTPS RAG endpoint URL")
    prompt: str = Field(..., min_length=1, description="Prompt to send through Input Rail -> Webhook -> Output Rail")
    api_key: Optional[str] = Field(default=None, description="Optional Bearer token for webhook")
    bypass_input_block: bool = Field(
        default=False,
        description="If true, still calls the webhook even if input rail flags the prompt, to test endpoint resilience",
    )


class GuardrailWebhookProbeResponse(BaseModel):
    input_verdict: GuardrailCheckResult
    blocked_at_input: bool
    webhook_response: Optional[str] = None
    retrieved_contexts: List[str] = []
    latency_ms: float = 0.0
    output_verdict: Optional[GuardrailCheckResult] = None


@router.post(
    "/probe-webhook",
    response_model=GuardrailWebhookProbeResponse,
    status_code=status.HTTP_200_OK,
    summary="Probe Live Custom Webhook Through Input & Output Guardrails",
    description="Runs pre-execution input rails, invokes the user's custom webhook URL, and runs post-execution RAG fact-checking on its live response.",
)
async def probe_webhook_with_guardrails(
    payload: GuardrailWebhookProbeRequest,
    workspace: Workspace = Depends(get_current_workspace),
):
    """End-to-end guardrail inspection against a live custom HTTP webhook."""
    input_verdict = guardrails_engine.check_input(
        workspace_id=workspace.id,
        prompt=payload.prompt,
    )
    if not input_verdict.passed and not payload.bypass_input_block:
        return GuardrailWebhookProbeResponse(
            input_verdict=input_verdict,
            blocked_at_input=True,
            webhook_response=None,
            retrieved_contexts=[],
            latency_ms=0.0,
            output_verdict=None,
        )

    try:
        provider = WebhookProvider(
            webhook_url=payload.webhook_url.strip(),
            api_key=payload.api_key or "",
        )
        gen_res = await provider.generate(payload.prompt)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Webhook call failed: {str(exc)}")

    contexts = getattr(gen_res, "retrieved_contexts", None) or []
    output_verdict = guardrails_engine.check_output(
        workspace_id=workspace.id,
        response_text=gen_res.generated_text,
        retrieved_contexts=contexts,
    )
    return GuardrailWebhookProbeResponse(
        input_verdict=input_verdict,
        blocked_at_input=False,
        webhook_response=gen_res.generated_text,
        retrieved_contexts=contexts,
        latency_ms=round(gen_res.latency_ms, 2),
        output_verdict=output_verdict,
    )
