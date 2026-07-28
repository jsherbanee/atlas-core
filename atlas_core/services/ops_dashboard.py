"""Lightweight operational dashboard helpers for intake/scheduler state."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


def summarize_uploads_root(uploads_root: str | Path = "outputs/uploads") -> Dict[str, Any]:
    root = Path(uploads_root)
    summary = {
        "sessions": 0,
        "jobs_total": 0,
        "jobs": {
            "queued": 0,
            "admitted": 0,
            "rejected": 0,
            "failed": 0,
            "completed": 0,
            "scheduled_retries": 0,
            "exhausted": 0,
        },
        "sessions_detail": {},
    }
    if not root.exists():
        return summary

    for session in root.iterdir():
        if not session.is_dir():
            continue
        summary["sessions"] += 1
        jobs_dir = session / ".jobs"
        if not jobs_dir.exists():
            continue
        session_counts = {k: 0 for k in summary["jobs"].keys()}
        for jf in jobs_dir.glob("*.json"):
            try:
                js = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                continue
            summary["jobs_total"] += 1
            stage = js.get("stage")
            rs = js.get("retry_state")
            if stage in session_counts:
                session_counts[stage] += 1
                summary["jobs"][stage] += 1
            else:
                # map unknown stages
                if stage == "failed":
                    summary["jobs"]["failed"] += 1
                elif stage == "completed":
                    summary["jobs"]["completed"] += 1
            if rs == "scheduled":
                session_counts["scheduled_retries"] = session_counts.get("scheduled_retries", 0) + 1
                summary["jobs"]["scheduled_retries"] += 1
            if rs == "exhausted":
                session_counts["exhausted"] = session_counts.get("exhausted", 0) + 1
                summary["jobs"]["exhausted"] += 1

        summary["sessions_detail"][session.name] = session_counts

    return summary
