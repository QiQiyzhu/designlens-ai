"""File content is data. No file writes, formulas, eval, URL fetching or commands."""
import csv
import hashlib
import io
import json
from pathlib import PurePath
from datetime import datetime

from .db import now, uid
from .models import ImportRequest, SOURCE_TYPES


def parse_import(request: ImportRequest, *, preview: bool = False) -> list[dict]:
    if request.type not in SOURCE_TYPES:
        raise ValueError("Unknown source type")
    if not preview and not request.is_demo and not request.consent_confirmed:
        raise ValueError("Confirm consent and redaction before importing real research")
    if len(request.content.encode("utf-8")) > 1_000_000:
        raise ValueError("Import must be at most 1 MB UTF-8")
    suffix = PurePath(request.filename).suffix.lower()
    if suffix in (".txt", ".md", ".markdown"):
        rows = [{"content": request.content}]
    elif suffix == ".csv":
        reader = csv.DictReader(io.StringIO(request.content.lstrip("\ufeff")))
        if not reader.fieldnames or "content" not in reader.fieldnames:
            raise ValueError("CSV requires a content column")
        rows = list(reader)
    elif suffix == ".json":
        raw = json.loads(request.content)
        rows = raw if isinstance(raw, list) else raw.get("sources", [raw]) if isinstance(raw, dict) else []
    else:
        raise ValueError("Supported formats: TXT, Markdown, CSV, JSON")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 500:
        raise ValueError("Import must contain 1–500 records")
    result = []
    imported_at = now()
    digest = hashlib.sha256(request.content.encode("utf-8")).hexdigest()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or not isinstance(row.get("content"), str) or not row["content"].strip():
            raise ValueError(f"Row {index}: nonempty content required")
        if len(row["content"]) > 100_000:
            raise ValueError(f"Row {index}: content exceeds 100,000 characters")
        kind = row.get("type") or request.type
        if kind not in SOURCE_TYPES:
            raise ValueError(f"Row {index}: unknown source type")
        timestamp = row.get("timestamp") or imported_at
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("timezone required")
        except (ValueError, AttributeError):
            raise ValueError(f"Row {index}: timestamp must be ISO-8601 with timezone") from None
        metadata = row.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise ValueError(f"Row {index}: metadata must be a JSON object") from None
        if not isinstance(metadata, dict):
            raise ValueError(f"Row {index}: metadata must be an object")
        source_id = uid("src")
        result.append({"id": source_id, "source_id": source_id, "type": kind,
                       "participant": str(row.get("participant") or row.get("source") or request.participant)[:200],
                       "timestamp": timestamp, "segment": str(row.get("segment") or request.segment)[:200],
                       "content": row["content"], "is_demo": request.is_demo,
                       "metadata": {**metadata, "filename": PurePath(request.filename).name, "row": index,
                                    "import_sha256": digest, "original_source_id": row.get("source_id"),
                                    "imported_at": imported_at, "consent_confirmed": request.consent_confirmed,
                                    "timestamp_basis": "provided" if row.get("timestamp") else "import_time"}})
    return result
