"""Deterministic drawing sheet metadata extraction helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_SHEET_NUMBER_RE = re.compile(r"([A-Z]{1,3}-?\d{1,3}(?:\.\d{1,2})?)")
_REVISION_RE = re.compile(r"\brev(?:ision)?\s*[:\-]?\s*([A-Z0-9.\-]+)", re.I)
_DATE_RE = re.compile(
    r"\b((?:\d{1,2}/\d{1,2}/\d{2,4})|(?:[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}))\b"
)


def extract_drawing_sheet_candidates(
    raw_pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()

    for page in raw_pages:
        page_number = _int_or_none(page.get("page_number"))
        text = str(page.get("text") or "")
        source_file = str(page.get("source_file") or "")
        sheet_number = _sheet_number_from_text(text) or _sheet_number_from_filename(
            source_file
        )
        if sheet_number is None:
            continue

        title = _title_from_text(text) or _title_from_filename(source_file)
        revision = _match_group(_REVISION_RE, text)
        issue_date = _match_group(_DATE_RE, text)
        marker = (sheet_number, source_file, page_number or -1)
        if marker in seen:
            continue

        seen.add(marker)
        candidates.append(
            {
                "sheet_number": sheet_number,
                "title": title or f"Sheet {sheet_number}",
                "revision": revision,
                "issue_date": issue_date,
                "source_file": source_file,
                "page_number": page_number,
                "source_excerpt": _excerpt(text),
            }
        )

    return candidates


def _sheet_number_from_text(text: str) -> str | None:
    match = _SHEET_NUMBER_RE.search(text)
    if match is None:
        return None

    return match.group(1).replace(" ", "")


def _sheet_number_from_filename(source_file: str) -> str | None:
    stem = Path(source_file).stem
    return _sheet_number_from_text(stem.upper())


def _title_from_text(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if _SHEET_NUMBER_RE.search(stripped):
            return _SHEET_NUMBER_RE.sub("", stripped).strip(" -:") or None

        lowered = stripped.lower()
        if any(token in lowered for token in ("plan", "detail", "schedule", "riser")):
            return stripped

    return None


def _title_from_filename(source_file: str) -> str | None:
    stem = Path(source_file).stem.replace("_", " ").strip()
    cleaned = _SHEET_NUMBER_RE.sub("", stem).strip(" -:")
    return cleaned or None


def _match_group(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if match is None:
        return None

    value = match.group(1).strip()
    return value or None


def _excerpt(text: str) -> str | None:
    normalized = " ".join(text.split())
    if not normalized:
        return None

    return normalized[:180]


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int):
        return value

    return None
