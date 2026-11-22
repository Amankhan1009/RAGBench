"""REST API Endpoints for AI Red-Teaming, Adversarial Fuzzing, and Security Posture Scoring."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.api.v1.auth import get_current_workspace
from ragbench.core.audit import record_audit_event
from ragbench.core.rbac import AuthContext, require_evaluator
from ragbench.db.session import get_db
from ragbench.models.workspace import Workspace
from ragbench.redteam.attacks import get_attack_catalog
from ragbench.redteam.engine import redteam_engine
from ragbench.redteam.schemas import (
    AttackCategory,
    AttackTestCase,
    RedTeamBenchmarkReport,
    RedTeamBenchmarkRequest,
)

router = APIRouter(prefix="/redteam", tags=["AI Red-Teaming & Security Posture"])


@router.post(
    "/run",
    response_model=RedTeamBenchmarkReport,
    status_code=status.HTTP_200_OK,
    summary="Run AI Red-Team Adversarial Benchmark",
    description="Fuzzes target LLM or RAG pipeline with direct injections, jailbreaks, indirect injections, and PII exfiltration.",
)
async def run_redteam_benchmark(
    payload: RedTeamBenchmarkRequest,
    ctx: AuthContext = Depends(require_evaluator),
    db: AsyncSession = Depends(get_db),
):
    """Execute adversarial fuzzing suite against target provider/model."""
    report = await redteam_engine.run_benchmark(ctx.workspace.id, payload)
    await record_audit_event(
        db,
        workspace_id=ctx.workspace.id,
        action="REDTEAM_BENCHMARK_RUN",
        resource_type="redteam",
        resource_id=report.benchmark_id,
        details={
            "provider": payload.provider,
            "security_score": report.security_posture_score,
            "grade": report.risk_grade,
            "total_attacks": report.total_attacks,
            "defended_count": report.defended_attacks,
            "breached_count": report.breached_attacks,
        },
        user_id=ctx.user_id,
        user_email=ctx.user_email,
        ip_address=ctx.client_ip,
    )
    await db.commit()
    return report


@router.get(
    "/attacks",
    response_model=List[AttackTestCase],
    status_code=status.HTTP_200_OK,
    summary="Get Adversarial Attack Catalog",
    description="Retrieve the catalog of curated prompt injection, jailbreak, and exfiltration probes.",
)
async def list_attacks(
    category: Optional[AttackCategory] = Query(default=None, description="Optional attack category filter"),
):
    """Fetch attack catalog test cases."""
    cats = [category] if category else None
    return get_attack_catalog(cats)


@router.get(
    "/reports",
    response_model=List[RedTeamBenchmarkReport],
    status_code=status.HTTP_200_OK,
    summary="Get Workspace Red-Team Audit Reports",
    description="List all historical red-team security audits and posture scores for the active workspace.",
)
async def get_workspace_reports(
    workspace: Workspace = Depends(get_current_workspace),
):
    """Fetch red-team report history."""
    return redteam_engine.get_reports(workspace.id)


@router.get(
    "/reports/{report_id}",
    response_model=RedTeamBenchmarkReport,
    status_code=status.HTTP_200_OK,
    summary="Get Red-Team Report by ID",
    description="Fetch detailed report including individual attack results, execution traces, and mitigation steps.",
)
async def get_report_details(
    report_id: str,
    workspace: Workspace = Depends(get_current_workspace),
):
    """Fetch individual red-team report by ID."""
    report = redteam_engine.get_report_by_id(workspace.id, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Red-team report '{report_id}' not found.",
        )
    return report
