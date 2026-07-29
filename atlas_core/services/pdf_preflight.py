"""Lightweight PDF preflight classifier.

Does not fully parse or render PDFs. Reads small portions of the file
to estimate page count, detect encryption/linearization, and spot
large declared stream/object lengths.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Any

import atlas_core.config.resource_policy as rp

_HEADER_RE = re.compile(rb"%PDF-(?P<ver>\d\.\d)")
_ENCRYPT_RE = re.compile(rb"/Encrypt\b")
_LINEAR_RE = re.compile(rb"/Linearized\b")
_COUNT_RE = re.compile(rb"/Count\s+(\d+)")
_LENGTH_RE = re.compile(rb"/Length\s+(\d+)")


@dataclass
class PreflightResult:
    classification: str
    reasons: list[str]
    attributes: Dict[str, Any]
    confidence: float
    recommended_policy: str


def _read_head_tail(path: Path, head: int = 64 * 1024, tail: int = 64 * 1024) -> bytes:
    size = path.stat().st_size
    with path.open("rb") as fh:
        data = fh.read(min(head, size))
        if size > head:
            try:
                fh.seek(max(0, size - tail))
                data += fh.read(tail)
            except Exception:
                pass
    return data


def classify_pdf(path: Path) -> PreflightResult:
    """Classify a PDF file into standard/large/very_large/pathological.

    This is intentionally conservative and fast.
    """
    # timestamp not used; avoid unused variable
    size = path.stat().st_size
    data = _read_head_tail(path)

    reasons: list[str] = []
    attrs: Dict[str, Any] = {"size_bytes": size}

    # header
    m = _HEADER_RE.search(data)
    if not m:
        reasons.append("missing_pdf_header")

    # quick flags
    if _ENCRYPT_RE.search(data):
        reasons.append("encrypted")
        attrs["encrypted"] = True
    else:
        attrs["encrypted"] = False

    if _LINEAR_RE.search(data):
        reasons.append("linearized")
        attrs["linearized"] = True
    else:
        attrs["linearized"] = False

    # estimated page count from /Count occurrences
    counts = [int(x) for x in _COUNT_RE.findall(data)]
    page_estimate = max(counts) if counts else None
    if page_estimate:
        attrs["page_count_estimate"] = page_estimate
        if page_estimate > rp.DEFAULT_POLICY.preflight_page_count_threshold:
            reasons.append("high_page_count_estimate")

    # suspicious large declared stream lengths
    lengths = [int(x) for x in _LENGTH_RE.findall(data)]
    attrs["declared_stream_lengths_sample"] = sorted(lengths, reverse=True)[:5]
    if lengths:
        max_declared = max(lengths)
        attrs["max_declared_stream_length"] = max_declared
        # if any declared length is huge relative to file
        if max_declared > max(
            0, rp.DEFAULT_POLICY.preflight_suspicious_stream_length_ratio * size
        ):
            reasons.append("suspicious_declared_stream_length")

    # classification by size primarily, with flags
    classification = "standard"
    confidence = 0.6
    recommended_policy = "standard"

    if size > rp.DEFAULT_POLICY.very_large_file_threshold_bytes:
        classification = "very_large"
        confidence = 0.9
        recommended_policy = "very_large"
        reasons.append("size_exceeds_very_large_threshold")
    elif size > rp.DEFAULT_POLICY.large_file_threshold_bytes:
        classification = "large"
        confidence = 0.8
        recommended_policy = "large"
        reasons.append("size_exceeds_large_threshold")

    # escalate for pathological indicators
    pathological_indicators = {
        "missing_pdf_header",
        "suspicious_declared_stream_length",
    }
    if any(r in reasons for r in pathological_indicators):
        classification = "pathological"
        confidence = max(confidence, 0.95)
        recommended_policy = "pathological"
        reasons.append("escalated_to_pathological")

    return PreflightResult(
        classification=classification,
        reasons=reasons,
        attributes=attrs,
        confidence=confidence,
        recommended_policy=recommended_policy,
    )
