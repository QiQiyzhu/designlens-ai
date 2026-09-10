"""Local suggestions and review-bound source sharing. No LLM or raw-input persistence."""
from __future__ import annotations

import hashlib
import json
import re

from .db import now
from .importer import parse_import
from .models import ImportRequest


POLICY_VERSION = "local-intake-v1"
PATTERNS = (
    ("PRIVATE_TOKEN", re.compile(r"(?<![\w])(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,})")),
    ("EMAIL", re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")),
    ("PHONE", re.compile(r"(?<![\w])\+?\d[\d ()-]{6,}\d(?![\w])")),
)


def content_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clean_text(value: str, terms: list[str] | None = None) -> tuple[str, list[dict]]:
    spans = []
    for term in sorted(set(terms or []), key=len, reverse=True):
        if not isinstance(term, str) or not 2 <= len(term.strip()) <= 200:
            raise ValueError("Each manual redaction term must be 2–200 characters")
        spans.extend((m.start(), m.end(), "CUSTOM") for m in re.finditer(re.escape(term), value, re.IGNORECASE))
    for kind, pattern in PATTERNS:
        for match in pattern.finditer(value):
            if kind == "PHONE":
                digits = re.sub(r"\D", "", match.group())
                if not 7 <= len(digits) <= 15 or re.fullmatch(r"\d{4}-\d{2}-\d{2}", match.group()):
                    continue
            spans.append((match.start(), match.end(), kind))
    merged = []
    for start, end, kind in sorted(spans, key=lambda x: (x[0], -x[1])):
        if merged and start < merged[-1][1]:
            before = merged[-1]
            merged[-1] = (before[0], max(end, before[1]), before[2])
        else:
            merged.append((start, end, kind))
    output, cursor, counts = [], 0, {}
    for start, end, kind in merged:
        output.extend((value[cursor:start], f"[{kind}]"))
        cursor = end
        counts[kind] = counts.get(kind, 0) + 1
    output.append(value[cursor:])
    return "".join(output), [{"kind": kind, "count": count} for kind, count in sorted(counts.items())]


def preview_import(request: ImportRequest) -> dict:
    # Request digest binds review to raw input + cleanup settings without storing either raw input or manual terms.
    payload = request.model_dump(exclude={"privacy_review_digest"})
    digest = content_hash(json.dumps({"policy": POLICY_VERSION, "request": payload}, ensure_ascii=False, sort_keys=True))
    sources = parse_import(request, preview=True)
    changes = []
    for row, source in enumerate(sources, start=1):
        def clean(value, field):
            if isinstance(value, str):
                result, findings = clean_text(value, request.redaction_terms)
                changes.extend({"row": row, "field": field, **item} for item in findings)
                return result
            if isinstance(value, dict):
                # Raw metadata keys may themselves identify a person. Do not echo them in findings paths.
                result = {}
                for index, (key, item) in enumerate(value.items(), start=1):
                    retained_key = clean(key, f"{field}.entry[{index}].key")
                    while retained_key in result:
                        retained_key = f"{retained_key} [entry {index}]"
                    result[retained_key] = clean(item, f"{field}.entry[{index}].value")
                return result
            if isinstance(value, list):
                return [clean(v, field + "[]") for v in value]
            return value
        for field in ("content", "participant", "segment"):
            source[field] = clean(source[field], field)
        # Only import metadata is retained, never the raw file, term list or a raw-value redaction map.
        metadata = source["metadata"]
        protected = {key: metadata[key] for key in ("import_sha256", "imported_at", "row", "consent_confirmed", "timestamp_basis")}
        source["metadata"] = {**clean({k: v for k, v in metadata.items() if k not in protected}, "metadata"), **protected}
        source["privacy_review"] = {"policy_version": POLICY_VERSION,
                                    "status": "reviewed" if request.privacy_review_digest == digest else "preview",
                                    "review_digest": digest, "content_sha256": content_hash(source["content"]),
                                    "reviewed_at": now() if request.privacy_review_digest == digest else None,
                                    "raw_content_retained": False}
        source["remote_review"] = {"approved": False, "content_sha256": None, "note": None, "reviewed_at": None}
    return {"preview_digest": digest, "sources": sources, "changes": changes, "record_count": len(sources),
            "policy_version": POLICY_VERSION, "network_calls": 0, "persisted": False,
            "limitations": "Local email/phone/token patterns and manual terms are suggestions, not complete anonymization. Review names, addresses, rare attributes and metadata yourself. Only the cleaned version will be retained."}


def reviewed_import(request: ImportRequest) -> list[dict]:
    preview = preview_import(request)
    if request.privacy_review_digest and request.privacy_review_digest != preview["preview_digest"]:
        raise ValueError("Import changed after privacy review; generate and review a fresh preview")
    if not request.is_demo:
        if not request.consent_confirmed:
            raise ValueError("Confirm consent before importing real research")
        if request.privacy_review_digest != preview["preview_digest"]:
            raise ValueError("Real research needs a reviewed local cleanup preview before persistence")
    for source in preview["sources"]:
        if source["privacy_review"]["status"] == "preview":
            source["privacy_review"]["status"] = "automatic_only"
    return preview["sources"]


def ensure_remote_sources(sources: list[dict], allow_real: bool) -> None:
    for source in sources:
        if clean_text(source["content"])[1]:
            raise ValueError("Possible identifier in source; review local cleanup before remote generation")
        if source.get("is_demo") is True:
            continue
        privacy, sharing = source.get("privacy_review", {}), source.get("remote_review", {})
        digest = content_hash(source["content"])
        if not (allow_real and privacy.get("status") == "reviewed" and sharing.get("approved") is True
                and privacy.get("content_sha256") == digest and sharing.get("content_sha256") == digest):
            raise ValueError("Real evidence is local-only; current source review and explicit remote data permission are required")
