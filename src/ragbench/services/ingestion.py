"""Service for ingesting evaluation datasets from CSV, JSON, and JSONL formats."""
import csv
import io
import json
from typing import Any, Dict, List, Optional, Tuple

from ragbench.schemas.dataset import DatasetItemCreate

COMMON_QUERY_ALIASES = [
    "query", "question", "prompt", "input", "text", "instruction", "user_query", "eval_query"
]
COMMON_OUTPUT_ALIASES = [
    "expected_output", "ground_truth", "answer", "target", "reference", "gold", "response", "label"
]
COMMON_CONTEXT_ALIASES = [
    "contexts", "context", "passages", "documents", "chunks", "retrieved_contexts", "source", "evidence"
]


def detect_column(headers: List[str], candidate_aliases: List[str]) -> Optional[str]:
    """Find the best matching column name based on common alias sets."""
    lower_map = {h.strip().lower(): h for h in headers}
    for alias in candidate_aliases:
        if alias in lower_map:
            return lower_map[alias]
    return None


def parse_csv_content(
    content: str,
    column_mapping: Optional[Dict[str, str]] = None,
) -> Tuple[List[DatasetItemCreate], int, List[str]]:
    """Parse CSV text with automatic delimiter detection and column mapping."""
    if not content.strip():
        return [], 0, ["Uploaded CSV content is empty."]

    # Sniff delimiter
    first_lines = "\n".join(content.strip().splitlines()[:5])
    try:
        dialect = csv.Sniffer().sniff(first_lines, delimiters=",\t;|")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ","

    reader = csv.DictReader(io.StringIO(content.strip()), delimiter=delimiter)
    headers = reader.fieldnames or []
    if not headers:
        return [], 0, ["No column headers found in CSV."]

    # Auto-detect or use user mappings
    mapping = column_mapping or {}
    query_col = mapping.get("query") or detect_column(headers, COMMON_QUERY_ALIASES)
    output_col = mapping.get("expected_output") or detect_column(headers, COMMON_OUTPUT_ALIASES)
    context_col = mapping.get("contexts") or detect_column(headers, COMMON_CONTEXT_ALIASES)

    if not query_col:
        return [], 0, [
            f"Could not identify a Query column from headers: {headers}. "
            f"Expected one of: {COMMON_QUERY_ALIASES}"
        ]

    items: List[DatasetItemCreate] = []
    skipped = 0
    warnings: List[str] = []

    for row_idx, row in enumerate(reader, start=1):
        raw_query = row.get(query_col, "").strip() if query_col else ""
        if not raw_query:
            skipped += 1
            continue

        raw_output = row.get(output_col, "").strip() if output_col else None
        raw_contexts = []
        if context_col and row.get(context_col):
            ctx_val = row[context_col].strip()
            # If context is JSON formatted array e.g. ["chunk 1", "chunk 2"]
            if ctx_val.startswith("[") and ctx_val.endswith("]"):
                try:
                    parsed_ctx = json.loads(ctx_val)
                    if isinstance(parsed_ctx, list):
                        raw_contexts = [str(c) for c in parsed_ctx]
                    else:
                        raw_contexts = [ctx_val]
                except Exception:
                    raw_contexts = [ctx_val]
            else:
                raw_contexts = [ctx_val]

        # Remaining columns become item_metadata
        metadata: Dict[str, Any] = {}
        for h, val in row.items():
            if h not in (query_col, output_col, context_col) and val is not None and val.strip():
                metadata[h] = val.strip()

        items.append(
            DatasetItemCreate(
                query=raw_query,
                expected_output=raw_output or None,
                contexts=raw_contexts,
                item_metadata=metadata,
            )
        )

    if skipped > 0:
        warnings.append(f"Skipped {skipped} row(s) due to empty query fields.")

    return items, skipped, warnings


def parse_jsonl_content(
    content: str,
    column_mapping: Optional[Dict[str, str]] = None,
) -> Tuple[List[DatasetItemCreate], int, List[str]]:
    """Parse JSONL text where each line is a JSON object."""
    items: List[DatasetItemCreate] = []
    skipped = 0
    warnings: List[str] = []

    lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
    if not lines:
        return [], 0, ["Uploaded JSONL content is empty."]

    # Inspect first line to determine column names if mapping not provided
    sample_keys: List[str] = []
    try:
        sample_obj = json.loads(lines[0])
        if isinstance(sample_obj, dict):
            sample_keys = list(sample_obj.keys())
    except Exception:
        pass

    mapping = column_mapping or {}
    query_col = mapping.get("query") or detect_column(sample_keys, COMMON_QUERY_ALIASES) or "query"
    output_col = mapping.get("expected_output") or detect_column(sample_keys, COMMON_OUTPUT_ALIASES) or "expected_output"
    context_col = mapping.get("contexts") or detect_column(sample_keys, COMMON_CONTEXT_ALIASES) or "contexts"

    for idx, line in enumerate(lines, start=1):
        try:
            entry = json.loads(line)
        except Exception:
            skipped += 1
            continue

        if not isinstance(entry, dict):
            skipped += 1
            continue

        query_val = entry.get(query_col) or entry.get("query") or entry.get("question") or entry.get("prompt")
        if not query_val or not str(query_val).strip():
            skipped += 1
            continue

        output_val = entry.get(output_col) or entry.get("expected_output") or entry.get("answer") or entry.get("ground_truth")
        ctx_val = entry.get(context_col) or entry.get("contexts") or entry.get("context")

        contexts_list: List[str] = []
        if isinstance(ctx_val, list):
            contexts_list = [str(c) for c in ctx_val]
        elif isinstance(ctx_val, str) and ctx_val.strip():
            contexts_list = [ctx_val.strip()]

        metadata = entry.get("metadata") or entry.get("item_metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}

        # Capture other top-level fields into metadata
        for k, v in entry.items():
            if k not in (query_col, output_col, context_col, "query", "expected_output", "contexts", "metadata", "item_metadata"):
                metadata[k] = v

        items.append(
            DatasetItemCreate(
                query=str(query_val).strip(),
                expected_output=str(output_val).strip() if output_val else None,
                contexts=contexts_list,
                item_metadata=metadata,
            )
        )

    if skipped > 0:
        warnings.append(f"Skipped {skipped} invalid or empty JSONL lines.")

    return items, skipped, warnings


def parse_json_content(
    content: str,
    column_mapping: Optional[Dict[str, str]] = None,
) -> Tuple[List[DatasetItemCreate], int, List[str]]:
    """Parse standard JSON array of objects."""
    try:
        data = json.loads(content.strip())
    except Exception as exc:
        return [], 0, [f"Invalid JSON syntax: {str(exc)}"]

    if not isinstance(data, list):
        return [], 0, ["JSON dataset must be a top-level list of item objects."]

    # Convert list of objects to pseudo-JSONL and reuse parser
    jsonl_str = "\n".join(json.dumps(obj) for obj in data if isinstance(obj, dict))
    return parse_jsonl_content(jsonl_str, column_mapping=column_mapping)


def parse_dataset_file(
    content: str,
    file_format: str,
    column_mapping: Optional[Dict[str, str]] = None,
) -> Tuple[List[DatasetItemCreate], int, List[str]]:
    """Dispatch dataset file parsing by detected format (csv, jsonl, json)."""
    fmt = file_format.lower().strip()
    if fmt == "csv":
        return parse_csv_content(content, column_mapping)
    elif fmt == "jsonl":
        return parse_jsonl_content(content, column_mapping)
    elif fmt == "json":
        return parse_json_content(content, column_mapping)
    else:
        # Heuristic detection if format unspecified
        first_char = content.strip()[:1]
        if first_char == "[":
            return parse_json_content(content, column_mapping)
        elif first_char == "{" and "\n" in content:
            return parse_jsonl_content(content, column_mapping)
        else:
            return parse_csv_content(content, column_mapping)
