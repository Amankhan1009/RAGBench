"""OpenAI-compatible AI Gateway REST API with Semantic Caching, Failover, and Budgets."""
import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.api.v1.auth import get_current_workspace
from ragbench.db.session import get_db
from ragbench.gateway.budget import budget_manager
from ragbench.gateway.cache import gateway_cache
from ragbench.gateway.router import gateway_router
from ragbench.gateway.schemas import (
    BudgetConfig,
    BudgetStatus,
    CacheStats,
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    GatewayMetadata,
    UsageInfo,
)
from ragbench.guardrails.engine import guardrails_engine
from ragbench.models.workspace import Workspace
from ragbench.sanitizer.engine import pii_sanitizer

router = APIRouter(prefix="/gateway", tags=["AI Gateway & Semantic Cache"])


def _extract_prompt_from_messages(messages: List[ChatMessage]) -> str:
    """Flatten chat messages into unified context prompt for model generation."""
    if len(messages) == 1:
        return messages[0].content

    formatted_turns = []
    for msg in messages:
        role_label = msg.role.capitalize()
        formatted_turns.append(f"{role_label}: {msg.content}")
    return "\n\n".join(formatted_turns)


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    status_code=status.HTTP_200_OK,
    summary="Universal OpenAI-Compatible Chat Completions Proxy",
    description="Drop-in OpenAI chat endpoint featuring sub-5ms semantic caching, automated provider failovers, and budget caps.",
)
async def create_chat_completion(
    payload: ChatCompletionRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Execute chat completion with transparent semantic caching and resilient multi-provider routing."""
    start_time = time.perf_counter()

    # 1. Enforce Workspace Budget Cap
    budget_manager.check_budget(workspace.id)

    prompt = _extract_prompt_from_messages(payload.messages)

    # 2. Automated PII Masking & Data Sanitization (Pre-Execution Privacy)
    pii_sanitized = False
    pii_entities_masked_count = 0
    pii_entities_detected: List[str] = []
    pii_latency_ms = 0.0
    token_map: dict = {}

    if payload.pii_sanitization_enabled:
        sanitization_res = pii_sanitizer.sanitize(prompt)
        pii_sanitized = True
        pii_entities_masked_count = len(sanitization_res.entities_found)
        pii_entities_detected = list(sanitization_res.entities_count.keys())
        pii_latency_ms = sanitization_res.latency_ms
        token_map = sanitization_res.token_map
        prompt = sanitization_res.sanitized_text

    # 3. Pre-Execution Guardrails (Input Injection, Jailbreaks, System Prompt Leak, Colang Topical Boundary)
    guardrails_applied = False
    guardrails_violations: List[str] = []
    guardrails_latency_ms = 0.0

    if payload.guardrails_enabled:
        guardrails_applied = True
        input_verdict = guardrails_engine.check_input(workspace.id, prompt)
        guardrails_latency_ms = input_verdict.execution_time_ms

        if not input_verdict.passed:
            total_latency_ms = (time.perf_counter() - start_time) * 1000.0
            guardrails_violations = input_verdict.violations
            refusal_text = input_verdict.refusal_response or input_verdict.reason

            return ChatCompletionResponse(
                model=payload.model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatMessage(role="assistant", content=refusal_text),
                        finish_reason="stop",
                    )
                ],
                usage=UsageInfo(
                    prompt_tokens=len(prompt.split()),
                    completion_tokens=len(refusal_text.split()),
                    total_tokens=len(prompt.split()) + len(refusal_text.split()),
                ),
                gateway=GatewayMetadata(
                    cached=False,
                    cache_key=None,
                    latency_ms=round(total_latency_ms, 2),
                    provider_used="NeMo Guardrails (Shield)",
                    model_used=payload.model,
                    fallback_triggered=False,
                    attempted_providers=[],
                    cost_usd=0.0,
                    cost_saved_usd=0.0,
                    guardrails_applied=True,
                    guardrails_blocked=True,
                    guardrails_violations=guardrails_violations,
                    guardrails_latency_ms=round(guardrails_latency_ms, 2),
                    pii_sanitized=pii_sanitized,
                    pii_entities_masked_count=pii_entities_masked_count,
                    pii_entities_detected=pii_entities_detected,
                    pii_latency_ms=round(pii_latency_ms, 2),
                ),
            )

    # 3. Check High-Speed Semantic / Exact Match Cache
    if payload.cache_enabled:
        cache_result = gateway_cache.get(
            workspace_id=workspace.id,
            prompt=prompt,
            model=payload.model,
            temperature=payload.temperature,
            similarity_threshold=payload.similarity_threshold,
        )

        if cache_result is not None:
            cached_entry, match_type = cache_result
            lookup_latency_ms = (time.perf_counter() - start_time) * 1000.0

            cached_text = cached_entry.response_text
            if payload.guardrails_enabled and payload.retrieved_contexts:
                output_verdict = guardrails_engine.check_output(
                    workspace.id, cached_text, payload.retrieved_contexts
                )
                guardrails_latency_ms += output_verdict.execution_time_ms
                if not output_verdict.passed:
                    guardrails_violations.extend(output_verdict.violations)
                    if output_verdict.sanitized_text:
                        cached_text = output_verdict.sanitized_text

            if payload.pii_sanitization_enabled and payload.pii_restore_response and token_map:
                cached_text = pii_sanitizer.restore(cached_text, token_map).restored_text

            return ChatCompletionResponse(
                model=cached_entry.model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatMessage(role="assistant", content=cached_text),
                        finish_reason=getattr(cached_entry, "finish_reason", "stop"),
                    )
                ],
                usage=UsageInfo(
                    prompt_tokens=cached_entry.prompt_tokens,
                    completion_tokens=cached_entry.completion_tokens,
                    total_tokens=cached_entry.prompt_tokens + cached_entry.completion_tokens,
                ),
                gateway=GatewayMetadata(
                    cached=True,
                    cache_key=f"hit_{match_type}",
                    latency_ms=round(lookup_latency_ms, 2),
                    provider_used=f"{cached_entry.provider_name} (Cached)",
                    model_used=cached_entry.model,
                    fallback_triggered=False,
                    attempted_providers=[],
                    cost_usd=0.0,
                    cost_saved_usd=cached_entry.cost_usd,
                    guardrails_applied=guardrails_applied,
                    guardrails_blocked=False,
                    guardrails_violations=guardrails_violations,
                    guardrails_latency_ms=round(guardrails_latency_ms, 2),
                    pii_sanitized=pii_sanitized,
                    pii_entities_masked_count=pii_entities_masked_count,
                    pii_entities_detected=pii_entities_detected,
                    pii_latency_ms=round(pii_latency_ms, 2),
                ),
            )

    # 4. Infer Provider & Route Through Resilient Failover Chain
    primary_provider = gateway_router.infer_provider(
        model=payload.model,
        explicit_provider=payload.provider,
    )

    provider_res, provider_used, fallback_triggered, attempted_providers = (
        await gateway_router.execute_with_fallback(
            workspace_id=workspace.id,
            prompt=prompt,
            model=payload.model,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            primary_provider=primary_provider,
            fallback_providers=payload.fallback_providers,
            direct_key=payload.api_key,
            db=db,
        )
    )

    total_latency_ms = (time.perf_counter() - start_time) * 1000.0

    # Extract finish_reason from provider metadata (e.g. 'length' if truncated, 'stop' if complete)
    finish_reason = "stop"
    if provider_res.raw_response and isinstance(provider_res.raw_response, dict):
        raw_choices = provider_res.raw_response.get("choices")
        if raw_choices and isinstance(raw_choices, list) and len(raw_choices) > 0:
            finish_reason = raw_choices[0].get("finish_reason", "stop")

    # 4. Accrue Spend to Workspace Budget
    budget_manager.record_usage(
        workspace_id=workspace.id,
        cost_usd=provider_res.cost_usd,
        tokens=provider_res.total_tokens,
    )

    # 5. Populate Cache on Cache Miss
    cache_key = None
    if payload.cache_enabled:
        cache_key = gateway_cache.set(
            workspace_id=workspace.id,
            prompt=prompt,
            model=payload.model,
            response_text=provider_res.generated_text,
            prompt_tokens=provider_res.prompt_tokens,
            completion_tokens=provider_res.completion_tokens,
            cost_usd=provider_res.cost_usd,
            latency_ms=provider_res.latency_ms,
            provider_name=provider_used,
            temperature=payload.temperature,
            finish_reason=finish_reason,
        )

    response_text = provider_res.generated_text
    if payload.guardrails_enabled and payload.retrieved_contexts:
        output_verdict = guardrails_engine.check_output(
            workspace.id, response_text, payload.retrieved_contexts
        )
        guardrails_latency_ms += output_verdict.execution_time_ms
        if not output_verdict.passed:
            guardrails_violations.extend(output_verdict.violations)
            if output_verdict.sanitized_text:
                response_text = output_verdict.sanitized_text

    if payload.pii_sanitization_enabled and payload.pii_restore_response and token_map:
        response_text = pii_sanitizer.restore(response_text, token_map).restored_text

    return ChatCompletionResponse(
        model=payload.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
                finish_reason=finish_reason,
            )
        ],
        usage=UsageInfo(
            prompt_tokens=provider_res.prompt_tokens,
            completion_tokens=provider_res.completion_tokens,
            total_tokens=provider_res.total_tokens,
        ),
        gateway=GatewayMetadata(
            cached=False,
            cache_key=cache_key[:12] if cache_key else None,
            latency_ms=round(total_latency_ms, 2),
            provider_used=provider_used,
            model_used=payload.model,
            fallback_triggered=fallback_triggered,
            attempted_providers=attempted_providers,
            cost_usd=provider_res.cost_usd,
            cost_saved_usd=0.0,
            guardrails_applied=guardrails_applied,
            guardrails_blocked=False,
            guardrails_violations=guardrails_violations,
            guardrails_latency_ms=round(guardrails_latency_ms, 2),
            pii_sanitized=pii_sanitized,
            pii_entities_masked_count=pii_entities_masked_count,
            pii_entities_detected=pii_entities_detected,
            pii_latency_ms=round(pii_latency_ms, 2),
        ),
    )


@router.get(
    "/stats",
    response_model=CacheStats,
    status_code=status.HTTP_200_OK,
    summary="Get Semantic Cache & Gateway Performance Metrics",
)
async def get_gateway_stats(
    workspace: Workspace = Depends(get_current_workspace),
):
    """Retrieve cache hit rate, cost saved, and latency saved for the active workspace."""
    return gateway_cache.get_stats(workspace.id)


@router.post(
    "/cache/purge",
    status_code=status.HTTP_200_OK,
    summary="Purge Workspace Semantic Cache",
)
async def purge_gateway_cache(
    workspace: Workspace = Depends(get_current_workspace),
):
    """Flush all cached generation results for the current workspace."""
    cleared_count = gateway_cache.purge(workspace.id)
    return {
        "status": "success",
        "message": f"Successfully purged {cleared_count} cached entries from AI Gateway.",
        "cleared_count": cleared_count,
    }


@router.get(
    "/budget",
    response_model=BudgetStatus,
    status_code=status.HTTP_200_OK,
    summary="Get Workspace Monthly Budget Usage & Limits",
)
async def get_workspace_budget(
    workspace: Workspace = Depends(get_current_workspace),
):
    """View current cumulative month-to-date spend and configured budget caps."""
    return budget_manager.get_status(workspace.id)


@router.post(
    "/budget",
    response_model=BudgetStatus,
    status_code=status.HTTP_200_OK,
    summary="Update Workspace Monthly Budget Limits",
)
async def update_workspace_budget(
    payload: BudgetConfig,
    workspace: Workspace = Depends(get_current_workspace),
):
    """Configure or adjust monthly USD spending limit and token quota for the active workspace."""
    return budget_manager.set_limits(
        workspace_id=workspace.id,
        monthly_budget_usd=payload.monthly_budget_usd,
        monthly_token_quota=payload.monthly_token_quota,
    )
