"""Workspace budget tracking and quota enforcement for RAGBench AI Gateway."""
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import HTTPException

from ragbench.core.logging import logger
from ragbench.gateway.schemas import BudgetStatus


class WorkspaceBudgetRecord:
    """Stores cumulative monthly spending and quota configurations."""
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self.year_month = datetime.now(timezone.utc).strftime("%Y-%m")
        self.cost_usd = 0.0
        self.total_tokens = 0
        self.monthly_budget_usd: Optional[float] = None
        self.monthly_token_quota: Optional[int] = None

    def check_and_reset_month(self):
        """Automatically roll over counters at the start of a new calendar month."""
        current_ym = datetime.now(timezone.utc).strftime("%Y-%m")
        if current_ym != self.year_month:
            logger.info(
                f"[BudgetManager] Rolling over budget for workspace '{self.workspace_id}' from {self.year_month} to {current_ym}"
            )
            self.year_month = current_ym
            self.cost_usd = 0.0
            self.total_tokens = 0



class BudgetManager:
    """Manages workspace-scoped spending limits and enforces budget caps."""

    def __init__(self):
        self._records: Dict[str, WorkspaceBudgetRecord] = {}

    def _get_record(self, workspace_id: str) -> WorkspaceBudgetRecord:
        if workspace_id not in self._records:
            self._records[workspace_id] = WorkspaceBudgetRecord(workspace_id)
        record = self._records[workspace_id]
        record.check_and_reset_month()
        return record

    def check_budget(self, workspace_id: str) -> None:
        """Verify whether workspace has exceeded its monthly spending or token limits."""
        record = self._get_record(workspace_id)

        # Check USD Budget Cap
        if record.monthly_budget_usd is not None and record.monthly_budget_usd > 0.0:
            if record.cost_usd >= record.monthly_budget_usd:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"Workspace monthly budget limit of ${record.monthly_budget_usd:.2f} has been reached "
                        f"(current usage: ${record.cost_usd:.4f}). Increase your budget in the AI Gateway tab to continue."
                    ),
                )

        # Check Token Quota
        if record.monthly_token_quota is not None and record.monthly_token_quota > 0:
            if record.total_tokens >= record.monthly_token_quota:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"Workspace monthly token quota of {record.monthly_token_quota:,} tokens has been reached "
                        f"(current usage: {record.total_tokens:,}). Increase your token ceiling in the AI Gateway tab to continue."
                    ),
                )

    def record_usage(self, workspace_id: str, cost_usd: float, tokens: int) -> None:
        """Accrue cost and tokens to the workspace's monthly total."""
        record = self._get_record(workspace_id)
        record.cost_usd += max(0.0, cost_usd)
        record.total_tokens += max(0, tokens)

    def set_limits(
        self,
        workspace_id: str,
        monthly_budget_usd: Optional[float] = None,
        monthly_token_quota: Optional[int] = None,
    ) -> BudgetStatus:
        """Update workspace monthly budget and token limits."""
        record = self._get_record(workspace_id)
        record.monthly_budget_usd = monthly_budget_usd
        record.monthly_token_quota = monthly_token_quota
        return self.get_status(workspace_id)

    def get_status(self, workspace_id: str) -> BudgetStatus:
        """Retrieve current cumulative usage status for a workspace."""
        record = self._get_record(workspace_id)

        cost_pct = 0.0
        if record.monthly_budget_usd and record.monthly_budget_usd > 0:
            cost_pct = round((record.cost_usd / record.monthly_budget_usd) * 100.0, 1)

        token_pct = 0.0
        if record.monthly_token_quota and record.monthly_token_quota > 0:
            token_pct = round((record.total_tokens / record.monthly_token_quota) * 100.0, 1)

        exceeded = False
        if record.monthly_budget_usd and record.cost_usd >= record.monthly_budget_usd:
            exceeded = True
        if record.monthly_token_quota and record.total_tokens >= record.monthly_token_quota:
            exceeded = True

        return BudgetStatus(
            workspace_id=workspace_id,
            current_month_cost_usd=round(record.cost_usd, 4),
            current_month_tokens=record.total_tokens,
            monthly_budget_usd=record.monthly_budget_usd,
            monthly_token_quota=record.monthly_token_quota,
            cost_usage_percentage=cost_pct,
            token_usage_percentage=token_pct,
            budget_exceeded=exceeded,
        )


# Global singleton instance
budget_manager = BudgetManager()
