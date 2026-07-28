from __future__ import annotations

import time
from typing import Tuple
import math

from atlas_core.config.resource_policy import DEFAULT_POLICY


def compute_backoff(attempt: int, *, base: int | None = None, multiplier: float | None = None, max_delay: int | None = None, jitter: bool | None = None) -> Tuple[int, float]:
    """Deterministic exponential backoff calculation.

    Returns (delay_seconds, next_retry_at_timestamp).
    """
    policy = DEFAULT_POLICY
    base = base if base is not None else getattr(policy, "retry_backoff_seconds", 5)
    multiplier = multiplier if multiplier is not None else getattr(policy, "retry_backoff_multiplier", 2.0)
    max_delay = max_delay if max_delay is not None else getattr(policy, "retry_max_delay_seconds", 3600)
    jitter = jitter if jitter is not None else getattr(policy, "retry_jitter", False)

    # attempt is 1-based for backoff progression
    exp = multiplier ** max(0, attempt - 1)
    delay = int(min(max_delay, base * exp))
    # deterministic: no jitter in default tests
    if jitter:
        # simple deterministic jitter based on time (but policy default is False)
        seed = int(time.time())
        # reduce jitter to 10% of delay
        jitter_amount = int(delay * 0.1)
        delay = delay - (seed % (jitter_amount + 1))

    next_retry_at = time.time() + delay
    return delay, next_retry_at
