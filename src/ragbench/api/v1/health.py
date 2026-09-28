"""System and database health check endpoint."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ragbench.core.config import settings
from ragbench.db.session import get_db

router = APIRouter()


@router.get("/health", tags=["System"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health endpoint validating FastAPI and Neon PostgreSQL connectivity."""
    try:
        result = await db.execute(text("SELECT 1"))
        db_healthy = (result.scalar() == 1)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity check failed: {str(exc)}"
        )

    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_healthy else "disconnected"
    }
