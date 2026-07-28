"""Definitions for intake processing stages and status helpers."""

from __future__ import annotations

from enum import Enum


class IntakeStage(str, Enum):
    waiting = "waiting"
    uploading = "uploading"
    validating = "validating"
    persisting = "persisting"
    deduplicating = "deduplicating"
    queued = "queued"
    extracting = "extracting"
    classifying = "classifying"
    analyzing = "analyzing"
    finalizing = "finalizing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


ALL_STAGES = tuple(item.value for item in IntakeStage)


def is_terminal(stage: str) -> bool:
    return stage in {
        IntakeStage.completed.value,
        IntakeStage.failed.value,
        IntakeStage.cancelled.value,
    }
