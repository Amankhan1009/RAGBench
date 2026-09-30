"""FastAPI application entrypoint using modern lifespan handlers."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from ragbench.api.v1.datasets import router as datasets_router
from ragbench.api.v1.experiments import router as experiments_router
from ragbench.api.v1.health import router as health_router
from ragbench.core.config import settings
from ragbench.core.logging import logger
from ragbench.db.base import Base
from ragbench.db.session import get_engine
import ragbench.models


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"{settings.APP_NAME} starting up in [{settings.ENVIRONMENT}] mode.")
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info(f"{settings.APP_NAME} shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-Grade LLM & RAG Evaluation Platform",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(datasets_router, prefix="/api/v1")
app.include_router(experiments_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs_url": "/docs"
    }
