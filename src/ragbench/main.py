"""FastAPI application entrypoint using modern lifespan handlers."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import ragbench.models
from ragbench.api.v1.agent import router as agent_router
from ragbench.api.v1.auth import router as auth_router
from ragbench.api.v1.datasets import router as datasets_router
from ragbench.api.v1.experiments import router as experiments_router
from ragbench.api.v1.health import router as health_router
from ragbench.core.config import settings
from ragbench.core.logging import logger
from ragbench.db.base import Base
from ragbench.db.session import get_engine


def _migrate_schema_sync(connection):
    """Ensure multi-tenant workspace_id columns exist on legacy tables and backfill default workspace."""
    from sqlalchemy import inspect, text
    inspector = inspect(connection)

    # 1. Ensure default workspace exists
    try:
        if connection.dialect.name == "sqlite":
            connection.execute(text(
                "INSERT OR IGNORE INTO workspaces (id, name, api_key) "
                "VALUES ('default-workspace-id', 'Default Workspace', 'default-workspace-key')"
            ))
        else:
            connection.execute(text(
                "INSERT INTO workspaces (id, name, api_key) "
                "VALUES ('default-workspace-id', 'Default Workspace', 'default-workspace-key') "
                "ON CONFLICT (id) DO NOTHING"
            ))
    except Exception as exc:
        logger.warning(f"[Migration] Workspace seed check: {exc}")

    # 2. Check datasets table
    if "datasets" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("datasets")]
        if "workspace_id" not in columns:
            logger.info("[Migration] Adding missing workspace_id to datasets table...")
            connection.execute(text("ALTER TABLE datasets ADD COLUMN workspace_id VARCHAR(36) DEFAULT 'default-workspace-id'"))
            connection.execute(text("UPDATE datasets SET workspace_id = 'default-workspace-id' WHERE workspace_id IS NULL"))

    # 3. Check experiments table
    if "experiments" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("experiments")]
        if "workspace_id" not in columns:
            logger.info("[Migration] Adding missing workspace_id to experiments table...")
            connection.execute(text("ALTER TABLE experiments ADD COLUMN workspace_id VARCHAR(36) DEFAULT 'default-workspace-id'"))
            connection.execute(text("UPDATE experiments SET workspace_id = 'default-workspace-id' WHERE workspace_id IS NULL"))

    # 4. Remove unique constraint on workspaces.name to allow multiple users to have customized names
    if "workspaces" in inspector.get_table_names() and connection.dialect.name != "sqlite":
        try:
            connection.execute(text("ALTER TABLE workspaces DROP CONSTRAINT IF EXISTS workspaces_name_key"))
        except Exception as exc:
            logger.warning(f"[Migration] Drop workspaces_name_key: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{settings.APP_NAME} starting up in [{settings.ENVIRONMENT}] mode.")
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_schema_sync)
    yield
    logger.info(f"{settings.APP_NAME} shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-Grade LLM & RAG Evaluation Platform",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
        },
    )

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(datasets_router, prefix="/api/v1")
app.include_router(experiments_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs_url": "/docs"
    }
