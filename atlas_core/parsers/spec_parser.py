"""Deterministic specification section extraction helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_SECTION_RE = re.compile(r"(\d{2})[\s_\-]?(\d{2})[\s_\-]?(\d{2})")


def extract_specification_section_candidates(
    raw_pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()

    for page in raw_pages:
        text = str(page.get("text") or "")
        source_file = str(page.get("source_file") or "")
        page_number = _int_or_none(page.get("page_number"))

        section_number = _section_number_from_text(
            text
        ) or _section_number_from_filename(source_file)
        if section_number is None:
            continue

        marker = (section_number, source_file, page_number or -1)
        if marker in seen:
            continue

        seen.add(marker)
        title = _title_from_text(text, section_number) or _title_from_filename(
            source_file,
            section_number,
        )
        sections.append(
            {
                "section_number": section_number,
                "title": title or f"Section {section_number}",
                "source_file": source_file,
                "page_number": page_number,
                "source_excerpt": _excerpt(text),
            }
        )

    return sections


def _section_number_from_text(text: str) -> str | None:
    match = _SECTION_RE.search(text)
    if match is None:
        return None

    return f"{match.group(1)} {match.group(2)} {match.group(3)}"


def _section_number_from_filename(source_file: str) -> str | None:
    stem = Path(source_file).stem
    return _section_number_from_text(stem)


def _title_from_text(text: str, section_number: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if section_number in stripped:
            candidate = stripped.replace(section_number, "").strip(" -:")
            return candidate or None

    return None


def _title_from_filename(source_file: str, section_number: str) -> str | None:
    stem = Path(source_file).stem.replace("_", " ").strip()
    candidate = stem.replace(section_number, "").strip(" -:")
    return candidate or None


def _excerpt(text: str) -> str | None:
    normalized = " ".join(text.split())
    if not normalized:
        return None

    return normalized[:180]


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, int):
        return value

    return None
