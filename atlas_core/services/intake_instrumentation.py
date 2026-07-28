"""Lightweight instrumentation helpers for intake steps.

Avoid heavy third-party deps; use stdlib where possible. This module records
timing and resident memory measurements for stages of intake so diagnostics
can be produced without changing primary behavior.
"""

from __future__ import annotations

import time
import os
from dataclasses import dataclass
from typing import Optional

try:
    import psutil  # type: ignore
except Exception:
    psutil = None


@dataclass
class StageMeasurement:
    stage: str
    pid: int
    ts_start: float
    ts_end: Optional[float] = None
    rss_start: Optional[int] = None
    rss_end: Optional[int] = None
    peak_rss: Optional[int] = None
    extra: dict = None

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "pid": self.pid,
            "ts_start": self.ts_start,
            "ts_end": self.ts_end,
            "rss_start": self.rss_start,
            "rss_end": self.rss_end,
            "peak_rss": self.peak_rss,
            "extra": dict(self.extra or {}),
        }


def _current_rss() -> int | None:
    try:
        if psutil is not None:
            return int(psutil.Process(os.getpid()).memory_info().rss)
    except Exception:
        pass
    # fallback to None when psutil not available
    return None


class instrument_stage:
    """Context manager to capture timing and RSS for a named stage.

    Usage:
        with instrument_stage("persist") as m:
            do_work()
        measurements.append(m.to_dict())
    """

    def __init__(self, stage: str, extra: dict | None = None) -> None:
        self._stage = stage
        self._measure = StageMeasurement(
            stage=stage, pid=os.getpid(), ts_start=time.time(), extra=extra or {}
        )

    def __enter__(self) -> StageMeasurement:
        self._measure.rss_start = _current_rss()
        return self._measure

    def __exit__(self, exc_type, exc, tb) -> None:
        self._measure.ts_end = time.time()
        self._measure.rss_end = _current_rss()
        # Peak RSS not available portably without psutil on some platforms;
        # if psutil is available, provide a process-level rss peak estimate.
        try:
            if psutil is not None:
                p = psutil.Process(os.getpid())
                info = p.memory_info()
                self._measure.peak_rss = int(getattr(info, "rss", info.rss))
        except Exception:
            self._measure.peak_rss = None
