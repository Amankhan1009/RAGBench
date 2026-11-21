"""Intelligent resilient routing engine with automated provider failover."""
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.core.logging import logger
from ragbench.core.security import decrypt_api_key
from ragbench.models.workspace import WorkspaceApiKey
from ragbench.providers.base import ProviderResponse
from ragbench.providers.factory import ProviderFactory


class GatewayRouter:
    """Manages provider resolution, credentials retrieval, and automated fallback execution."""

    @staticmethod
    def infer_provider(model: str, explicit_provider: Optional[str] = None) -> str:
        """Determine target provider from explicit override or model naming convention."""
        if explicit_provider and explicit_provider.strip():
            return explicit_provider.strip().lower()

        model_lower = model.strip().lower()
        if model_lower.startswith("http://") or model_lower.startswith("https://"):
            return "webhook"
        if "gpt-oss" in model_lower or "llama" in model_lower or "mixtral" in model_lower:
            return "groq"
        if "gpt-4" in model_lower or "gpt-3.5" in model_lower or "o1" in model_lower:
            return "openai"
        if "claude" in model_lower:
            return "anthropic"
        if "gemini" in model_lower:
            return "google"
        if "mock" in model_lower:
            return "mock"

        # Default fast inference engine
        return "groq"

    @staticmethod
    async def resolve_api_key(
        workspace_id: str,
        provider_name: str,
        direct_key: Optional[str],
        db: AsyncSession,
    ) -> Optional[str]:
        """Fetch API key from direct payload override, encrypted BYOK vault, or environment."""
        p_name = provider_name.lower()
        if p_name == "mock":
            return "mock-key"
        if p_name in ["webhook", "custom"]:
            return direct_key or ""

        # Direct parameter priority
        if direct_key and direct_key.strip():
            return direct_key.strip()

        # Database BYOK Vault lookup
        stmt = select(WorkspaceApiKey).where(
            WorkspaceApiKey.workspace_id == workspace_id,
            WorkspaceApiKey.provider == p_name,
        )
        record = (await db.execute(stmt)).scalar_one_or_none()
        if record:
            try:
                return decrypt_api_key(record.encrypted_key)
            except Exception as exc:
                logger.warning(
                    f"[GatewayRouter] Decryption failed for provider '{p_name}' in workspace '{workspace_id}': {exc}"
                )

        # Environment variable fallback
        env_val = os.getenv(f"{p_name.upper()}_API_KEY")
        if env_val and env_val.strip():
            return env_val.strip()

        return None

    async def execute_with_fallback(
        self,
        workspace_id: str,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        primary_provider: str,
        fallback_providers: Optional[List[str]],
        direct_key: Optional[str],
        db: AsyncSession,
    ) -> Tuple[ProviderResponse, str, bool, List[str]]:
        """Attempt primary provider with automatic failover to fallback chain on errors.

        Returns: (ProviderResponse, provider_used, fallback_triggered, attempted_providers)
        """
        # Build candidate chain avoiding duplicates
        candidates: List[str] = [primary_provider.lower()]
        if fallback_providers:
            for fb in fallback_providers:
                fb_norm = fb.strip().lower()
                if fb_norm and fb_norm not in candidates:
                    candidates.append(fb_norm)

        attempted_providers: List[str] = []
        last_error: Optional[Exception] = None

        for idx, provider_name in enumerate(candidates):
            attempted_providers.append(provider_name)
            is_fallback = (idx > 0)

            # Resolve API key
            api_key = await self.resolve_api_key(
                workspace_id=workspace_id,
                provider_name=provider_name,
                direct_key=direct_key if not is_fallback else None,
                db=db,
            )

            if not api_key and provider_name not in ["mock", "webhook", "custom"]:
                logger.info(
                    f"[GatewayRouter] Skipping provider '{provider_name}': No API key configured. Trying next fallback..."
                )
                continue

            try:
                # Instantiate provider
                provider_instance = ProviderFactory.create(
                    provider_name=provider_name,
                    api_key=api_key or "",
                    model=model,
                )

                # Execute generation
                response = await provider_instance.generate(
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                if is_fallback:
                    logger.warning(
                        f"[GatewayRouter] Automated failover SUCCESS: Request routed to '{provider_name}' after {attempted_providers[:-1]} failed."
                    )

                return response, provider_name, is_fallback, attempted_providers

            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"[GatewayRouter] Provider '{provider_name}' failed with error: {str(exc)}. Failing over to next provider..."
                )

        raise HTTPException(
            status_code=502,
            detail=(
                f"All configured gateway providers failed to process the request. "
                f"Attempted: {attempted_providers}. Last error: {str(last_error)}"
            ),
        )


# Global singleton instance
gateway_router = GatewayRouter()
