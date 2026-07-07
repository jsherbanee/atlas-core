"""Deterministic schedule and equipment extraction helpers."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import re
from typing import Any
import zipfile
from xml.etree import ElementTree

_TAG_RE = re.compile(r"\b[A-Z]{2,6}-\d{1,4}\b")
_EQUIPMENT_KEYWORDS = {
    "speaker": "speaker",
    "loudspeaker": "speaker",
    "projector": "projector",
    "display": "display",
    "monitor": "display",
    "camera": "camera",
    "microphone": "microphone",
    "dsp": "control_processor",
    "processor": "control_processor",
    "amplifier": "amplifier",
    "rack": "rack",
}


def extract_device_schedules_from_csv_files(
    schedule_files: list[Path],
) -> tuple[list[dict[str, Any]], list[str]]:
    schedules: list[dict[str, Any]] = []
    warnings: list[str] = []

    for schedule_file in sorted(schedule_files):
        suffix = schedule_file.suffix.lower()
        if suffix == ".csv":
            schedules.append(_load_csv_schedule(schedule_file))
            continue

        if suffix == ".xlsx":
            schedules.extend(_load_xlsx_schedules(schedule_file, warnings))
            continue

        if suffix == ".xls":
            warnings.append(
                f"Schedule file {schedule_file.name} is XLS (binary Excel) and is not supported. Convert to XLSX or CSV."
            )
            continue

        if suffix == ".pdf":
            # PDF schedule parsing is handled through page text extraction.
            continue

        warnings.append(
            f"Schedule file {schedule_file.name} has unsupported format; skipping."
        )

    return schedules, warnings


def detect_schedule_like_pages(raw_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    schedules: list[dict[str, Any]] = []
    for page in raw_pages:
        text = str(page.get("text") or "")
        lower = text.lower()
        if "schedule" not in lower:
            continue

        rows: list[dict[str, str]] = []
        for line in text.splitlines():
            normalized = line.strip()
            if not normalized:
                continue

            parts = [
                part.strip()
                for part in re.split(r"\s{2,}|\t|,", normalized)
                if part.strip()
            ]
            if len(parts) < 2:
                continue

            rows.append({"tag": parts[0], "description": " ".join(parts[1:])})

        if not rows:
            continue

        source_file = str(page.get("source_file") or "schedule.pdf")
        page_number = page.get("page_number")
        schedules.append(
            {
                "schedule_id": _stable_id(
                    source_file, str(page_number or 0), "schedule"
                ),
                "source_sheet_number": None,
                "title": f"Detected schedule from {source_file} page {page_number}",
                "source_file": source_file,
                "page_number": page_number,
                "rows": rows,
            }
        )

    return schedules


def extract_equipment_candidates(
    raw_pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    for page in raw_pages:
        text = str(page.get("text") or "")
        if not text.strip():
            continue

        source_file = str(page.get("source_file") or "")
        page_number = page.get("page_number")
        for line in text.splitlines():
            lowered = line.lower()
            category_hint = _category_hint(lowered)
            if category_hint is None:
                continue

            description = " ".join(line.strip().split())
            if not description:
                continue

            tag = _tag_from_text(description)
            candidate_id = _stable_id(source_file, str(page_number or 0), description)
            if candidate_id in seen:
                continue

            seen.add(candidate_id)
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "description": description,
                    "category_hint": category_hint,
                    "tag": tag,
                    "source_ref": {
                        "source_file": source_file,
                        "page_number": page_number,
                        "text_excerpt": description[:180],
                    },
                }
            )

    return candidates


def _load_csv_schedule(path: Path) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            cleaned = {str(key): str(value or "") for key, value in row.items()}
            rows.append(cleaned)

    return {
        "schedule_id": _stable_id(path.name, "csv", "schedule"),
        "source_sheet_number": None,
        "title": path.stem.replace("_", " "),
        "source_file": path.name,
        "rows": rows,
    }


def _load_xlsx_schedules(
    path: Path,
    warnings: list[str],
) -> list[dict[str, Any]]:
    try:
        with zipfile.ZipFile(path) as archive:
            workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
            relationships = ElementTree.fromstring(
                archive.read("xl/_rels/workbook.xml.rels")
            )
            shared_strings = _xlsx_shared_strings(archive)
            rid_to_target = _xlsx_relationship_targets(relationships)
            sheets: list[dict[str, Any]] = []
            for sheet in workbook.findall(
                ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet"
            ):
                sheet_name = str(sheet.attrib.get("name") or "Schedule")
                rel_id = str(
                    sheet.attrib.get(
                        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                    )
                    or ""
                )
                target = rid_to_target.get(rel_id)
                if target is None:
                    continue

                rows = _xlsx_rows(archive, target, shared_strings)
                if not rows:
                    continue

                sheets.append(
                    {
                        "schedule_id": _stable_id(path.name, sheet_name, "xlsx"),
                        "source_sheet_number": None,
                        "title": f"{path.stem.replace('_', ' ')} - {sheet_name}",
                        "source_file": path.name,
                        "rows": rows,
                    }
                )

            if sheets:
                return sheets
    except KeyError, ElementTree.ParseError, zipfile.BadZipFile:
        warnings.append(
            f"Schedule file {path.name} could not be parsed as XLSX; convert to CSV for deterministic extraction."
        )

    return []


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        xml_bytes = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    root = ElementTree.fromstring(xml_bytes)
    values: list[str] = []
    for item in root.findall(
        ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"
    ):
        text_nodes = item.findall(
            ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
        )
        values.append("".join(node.text or "" for node in text_nodes))

    return values


def _xlsx_relationship_targets(
    relationships_root: ElementTree.Element,
) -> dict[str, str]:
    targets: dict[str, str] = {}
    for rel in relationships_root.findall(
        ".//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
    ):
        rel_id = str(rel.attrib.get("Id") or "")
        target = str(rel.attrib.get("Target") or "")
        if not rel_id or not target:
            continue

        if not target.startswith("worksheets/"):
            continue

        targets[rel_id] = f"xl/{target}"

    return targets


def _xlsx_rows(
    archive: zipfile.ZipFile,
    worksheet_path: str,
    shared_strings: list[str],
) -> list[dict[str, str]]:
    xml_bytes = archive.read(worksheet_path)
    root = ElementTree.fromstring(xml_bytes)
    rows: list[list[str]] = []
    for row in root.findall(
        ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"
    ):
        values: list[str] = []
        for cell in row.findall(
            "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"
        ):
            cell_type = str(cell.attrib.get("t") or "")
            raw_value = cell.find(
                "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v"
            )
            text_value = ""
            if raw_value is not None and raw_value.text is not None:
                text_value = raw_value.text
                if cell_type == "s":
                    index = int(text_value)
                    text_value = (
                        shared_strings[index] if index < len(shared_strings) else ""
                    )
            elif cell_type == "inlineStr":
                inline_node = cell.find(
                    ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
                )
                text_value = inline_node.text or "" if inline_node is not None else ""

            values.append(str(text_value).strip())

        if any(value for value in values):
            rows.append(values)

    if not rows:
        return []

    headers = [value or f"column_{index + 1}" for index, value in enumerate(rows[0])]
    normalized: list[dict[str, str]] = []
    for row_values in rows[1:]:
        row_payload: dict[str, str] = {}
        for index, header in enumerate(headers):
            row_payload[str(header)] = (
                row_values[index] if index < len(row_values) else ""
            )
        normalized.append(row_payload)

    return normalized


def _category_hint(lowered_line: str) -> str | None:
    for token, category in _EQUIPMENT_KEYWORDS.items():
        if token in lowered_line:
            return category

    return None


def _tag_from_text(value: str) -> str | None:
    match = _TAG_RE.search(value)
    if match is None:
        return None

    return match.group(0)


def _stable_id(*parts: str) -> str:
    value = "|".join(parts)
    return f"det-{hashlib.sha1(value.encode('utf-8')).hexdigest()[:12]}"
