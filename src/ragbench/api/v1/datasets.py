"""Dataset and version management REST API endpoints with multi-tenant workspace isolation."""
import json
import os
import re
import time
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragbench.api.v1.auth import get_current_workspace
from ragbench.core.security import decrypt_api_key
from ragbench.db.session import get_db
from ragbench.models.dataset import Dataset, DatasetItem
from ragbench.models.workspace import Workspace, WorkspaceApiKey
from ragbench.providers.factory import ProviderFactory
from ragbench.schemas.dataset import (
    DatasetCreate,
    DatasetIngestRequest,
    DatasetIngestResponse,
    DatasetItemCreate,
    DatasetItemResponse,
    DatasetResponse,
    SyntheticDatasetRequest,
    SyntheticDatasetResponse,
    SyntheticItemPreview,
)
from ragbench.services.ingestion import parse_dataset_file

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    payload: DatasetCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Create a new evaluation dataset for the current workspace and optional initial items."""
    dataset = Dataset(
        name=payload.name,
        description=payload.description,
        version=payload.version,
        workspace_id=workspace.id,
    )
    db.add(dataset)
    await db.flush()

    for item_data in payload.items:
        item = DatasetItem(
            dataset_id=dataset.id,
            query=item_data.query,
            expected_output=item_data.expected_output,
            contexts=item_data.contexts,
            item_metadata=item_data.item_metadata
        )
        db.add(item)

    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.get("", response_model=List[DatasetResponse])
async def list_datasets(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """List all registered evaluation datasets belonging to the active workspace."""
    stmt = (
        select(Dataset)
        .where(Dataset.workspace_id == workspace.id)
        .order_by(Dataset.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a specific dataset by ID with its evaluation items within the active workspace."""
    stmt = select(Dataset).where(
        Dataset.id == dataset_id,
        Dataset.workspace_id == workspace.id,
    )
    result = await db.execute(stmt)
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found in current workspace"
        )
    return dataset


@router.post("/{dataset_id}/items", response_model=List[DatasetItemResponse], status_code=status.HTTP_201_CREATED)
async def bulk_add_items(
    dataset_id: uuid.UUID,
    items_data: List[DatasetItemCreate],
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Bulk import evaluation items into an existing dataset in the active workspace."""
    stmt = select(Dataset).where(
        Dataset.id == dataset_id,
        Dataset.workspace_id == workspace.id,
    )
    result = await db.execute(stmt)
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found in current workspace"
        )

    new_items = []
    for item_data in items_data:
        item = DatasetItem(
            dataset_id=dataset.id,
            query=item_data.query,
            expected_output=item_data.expected_output,
            contexts=item_data.contexts,
            item_metadata=item_data.item_metadata
        )
        db.add(item)
        new_items.append(item)

    await db.commit()
    for item in new_items:
        await db.refresh(item)
    return new_items


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Delete a dataset and all associated items belonging to the active workspace."""
    stmt = select(Dataset).where(
        Dataset.id == dataset_id,
        Dataset.workspace_id == workspace.id,
    )
    result = await db.execute(stmt)
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found in current workspace"
        )

    await db.delete(dataset)
    await db.commit()
    return None


@router.post("/generate-synthetic", response_model=SyntheticDatasetResponse)
async def generate_synthetic_dataset(
    payload: SyntheticDatasetRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Generate high-quality synthetic RAG evaluation dataset items from unstructured source text."""
    start_time = time.time()
    effective_key = payload.api_key

    if not effective_key or (effective_key == "mock-key" and payload.provider_name.lower() != "mock"):
        if payload.provider_name.lower() == "mock":
            effective_key = "mock-key"
        else:
            key_stmt = select(WorkspaceApiKey).where(
                WorkspaceApiKey.workspace_id == workspace.id,
                WorkspaceApiKey.provider == payload.provider_name.lower(),
            )
            key_record = (await db.execute(key_stmt)).scalar_one_or_none()
            if key_record:
                try:
                    effective_key = decrypt_api_key(key_record.encrypted_key)
                except Exception:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to decrypt stored provider API key. Please re-register your key in the BYOK tab.",
                    )
            else:
                env_fallback = os.getenv(f"{payload.provider_name.upper()}_API_KEY")
                if env_fallback:
                    effective_key = env_fallback
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"No API key configured for provider '{payload.provider_name}'. Please add your API key in the 'API Keys (BYOK)' tab or pass it directly.",
                    )

    # 1. Deterministic Mock Generator for unit testing and offline demo
    if payload.provider_name.lower() == "mock":
        paragraphs = [p.strip() for p in payload.raw_text.split("\n\n") if len(p.strip()) > 30]
        if not paragraphs:
            paragraphs = [p.strip() for p in payload.raw_text.split(".") if len(p.strip()) > 20]
        if not paragraphs:
            paragraphs = [payload.raw_text[:200]]

        items: List[SyntheticItemPreview] = []
        difficulties = ["factual", "reasoning", "adversarial"] if payload.difficulty == "mixed" else [payload.difficulty]

        for i in range(payload.num_samples):
            p_idx = i % len(paragraphs)
            chosen_p = paragraphs[p_idx]
            diff = difficulties[i % len(difficulties)]

            if diff == "adversarial":
                q = f"What is the policy regarding unmentioned clause {i + 1}?"
                ans = "This policy or detail is not specified in the provided documentation."
            elif diff == "reasoning":
                q = f"How do the provisions in section {i + 1} affect user eligibility?"
                ans = f"Based on the text: {chosen_p[:120]}..."
            else:
                q = f"What are the key terms outlined in section {i + 1}?"
                ans = f"The terms state that: {chosen_p[:120]}."

            items.append(
                SyntheticItemPreview(
                    query=q,
                    expected_output=ans,
                    contexts=[chosen_p[:400]],
                    difficulty=diff,
                    source_snippet=chosen_p[:80],
                )
            )

        elapsed_ms = round((time.time() - start_time) * 1000.0, 2)
        return SyntheticDatasetResponse(
            items=items,
            total_generated=len(items),
            provider_used="mock",
            model_used=payload.model_name or "mock-model",
            latency_ms=elapsed_ms,
        )

    # 2. Live Cloud LLM Synthesis
    try:
        provider = ProviderFactory.create(
            payload.provider_name,
            api_key=effective_key,
            model=payload.model_name,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to instantiate provider: {str(exc)}")

    synthesis_prompt = f"""You are an elite RAG evaluation benchmark engineer.
Analyze the source text below and synthesize exactly {payload.num_samples} comprehensive, production-grade test cases.

Difficulty Mode: {payload.difficulty.upper()}
- "factual": Direct factual questions where the answer is explicitly stated in the context.
- "reasoning": Complex multi-hop, comparison, or synthesis questions requiring cross-referencing information.
- "adversarial": Questions asking about topics or scenarios NOT covered or forbidden by the text, where the expected answer explicitly indicates the text does not contain that information (essential for hallucination benchmarking!).
- "mixed": A balanced combination of factual, multi-hop reasoning, and adversarial/unanswerable questions.

Source Text:
\"\"\"
{payload.raw_text}
\"\"\"

CRITICAL INSTRUCTIONS:
1. Output ONLY a valid JSON array of objects.
2. Do NOT wrap in conversational preamble or closing remarks.
3. Each object MUST strictly contain:
   - "query": str (the test question)
   - "expected_output": str (the gold standard reference answer)
   - "contexts": list[str] (exact extracted reference paragraph from the text supporting the answer)
   - "difficulty": "factual" | "reasoning" | "adversarial"
   - "source_snippet": str (10-15 words excerpt from where context was sourced)
"""

    gen_res = await provider.generate(synthesis_prompt)
    raw_output = gen_res.generated_text.strip()

    # Clean markdown fences if LLM wrapped in ```json
    cleaned = raw_output
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0].strip()

    items_list: List[SyntheticItemPreview] = []
    try:
        parsed_data = json.loads(cleaned)
        if isinstance(parsed_data, list):
            for entry in parsed_data:
                if isinstance(entry, dict) and "query" in entry:
                    contexts_val = entry.get("contexts", [])
                    if isinstance(contexts_val, str):
                        contexts_val = [contexts_val]
                    elif not isinstance(contexts_val, list):
                        contexts_val = [str(contexts_val)]

                    items_list.append(
                        SyntheticItemPreview(
                            query=entry.get("query", ""),
                            expected_output=entry.get("expected_output", ""),
                            contexts=contexts_val,
                            difficulty=entry.get("difficulty", "factual"),
                            source_snippet=entry.get("source_snippet"),
                        )
                    )
    except Exception:
        # Regex fallback to extract JSON objects if JSON was slightly malformed
        matches = re.findall(r"\{[^{}]*\"query\"[^{}]*\}", cleaned)
        for m in matches:
            try:
                obj = json.loads(m)
                items_list.append(
                    SyntheticItemPreview(
                        query=obj.get("query", "Sample question"),
                        expected_output=obj.get("expected_output", "Sample answer"),
                        contexts=obj.get("contexts", [payload.raw_text[:200]]),
                        difficulty=obj.get("difficulty", "factual"),
                        source_snippet=obj.get("source_snippet"),
                    )
                )
            except Exception:
                continue

    # If still empty due to unexpected model response, fallback to rule-based chunks
    if not items_list:
        paragraphs = [p.strip() for p in payload.raw_text.split("\n\n") if len(p.strip()) > 30]
        for idx in range(min(payload.num_samples, len(paragraphs) or 1)):
            p = paragraphs[idx] if paragraphs else payload.raw_text[:200]
            items_list.append(
                SyntheticItemPreview(
                    query=f"What information is provided regarding section {idx + 1}?",
                    expected_output=p[:180],
                    contexts=[p[:400]],
                    difficulty="factual",
                    source_snippet=p[:60],
                )
            )

    elapsed_ms = round((time.time() - start_time) * 1000.0, 2)
    return SyntheticDatasetResponse(
        items=items_list,
        total_generated=len(items_list),
        provider_used=payload.provider_name,
        model_used=payload.model_name or "default",
        latency_ms=elapsed_ms,
    )


@router.post("/ingest", response_model=DatasetIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_dataset(
    payload: DatasetIngestRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    """Bulk ingest evaluation datasets from CSV, JSONL, or JSON text with column mapping."""
    parsed_items, skipped, warnings = parse_dataset_file(
        content=payload.content,
        file_format=payload.file_format,
        column_mapping=payload.column_mapping,
    )

    if not parsed_items:
        detail_msg = "Failed to ingest dataset: No valid evaluation items could be extracted."
        if warnings:
            detail_msg += f" Details: {'; '.join(warnings)}"
        raise HTTPException(
            status_code=400,
            detail=detail_msg,
        )

    dataset = Dataset(
        name=payload.name,
        description=payload.description,
        version=payload.version,
        workspace_id=workspace.id,
    )
    db.add(dataset)
    await db.flush()

    for item_data in parsed_items:
        item = DatasetItem(
            dataset_id=dataset.id,
            query=item_data.query,
            expected_output=item_data.expected_output,
            contexts=item_data.contexts,
            item_metadata=item_data.item_metadata,
        )
        db.add(item)

    await db.commit()
    await db.refresh(dataset)

    stmt = select(DatasetItem).where(DatasetItem.dataset_id == dataset.id)
    items_res = (await db.execute(stmt)).scalars().all()

    ds_response = DatasetResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        version=dataset.version,
        workspace_id=dataset.workspace_id,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
        items=[DatasetItemResponse.model_validate(it) for it in items_res],
    )

    return DatasetIngestResponse(
        dataset=ds_response,
        total_ingested=len(parsed_items),
        skipped_rows=skipped,
        warnings=warnings,
    )
