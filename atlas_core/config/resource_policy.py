"""Configurable resource-safety policy for intake processing."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass
class ResourcePolicy:
    max_accepted_upload_bytes: int = 200 * 1024 * 1024  # 200 MiB
    large_file_threshold_bytes: int = 50 * 1024 * 1024  # 50 MiB
    very_large_file_threshold_bytes: int = 150 * 1024 * 1024  # 150 MiB
    max_concurrent_documents: int = 2
    max_concurrent_large_documents: int = 1
    page_processing_batch_size: int = 1
    max_page_render_resolution: int = 150  # DPI
    max_retained_page_artifacts: int = 2
    memory_warning_threshold_bytes: int = 2 * 1024 * 1024 * 1024  # 2 GiB
    memory_stop_threshold_bytes: int = 3 * 1024 * 1024 * 1024  # 3 GiB
    processing_timeout_seconds: int = 60 * 60
    temporary_storage_limit_bytes: int = 10 * 1024 * 1024 * 1024  # 10 GiB
    # Worker containment settings
    worker_memory_limit_bytes: int | None = None  # None => do not hard-limit
    worker_soft_rss_warning_bytes: int | None = 2 * 1024 * 1024 * 1024
    worker_timeout_seconds: int = 60 * 60
    worker_forced_kill_grace_seconds: int = 10
    max_retry_count: int = 2
    retry_backoff_seconds: int = 5
    standard_job_concurrency: int = 2
    very_large_job_concurrency: int = 1
    pathological_file_behavior: str = "quarantine"  # or 'reject' or 'strict'
    preflight_page_count_threshold: int = 500
    preflight_suspicious_stream_length_ratio: float = 10.0
    # reconciliation thresholds (seconds)
    reconciliation_stale_queue_seconds: int = 60 * 60 * 24  # 1 day
    reconciliation_stale_spawning_seconds: int = 60 * 10  # 10 minutes
    reconciliation_stale_running_seconds: int = 60 * 60  # 1 hour
    # retry/backoff settings
    max_retry_count: int = 2
    retry_backoff_seconds: int = 5
    retry_backoff_multiplier: float = 2.0
    retry_max_delay_seconds: int = 60 * 60  # 1 hour
    retry_jitter: bool = False


def load_policy_from_env() -> ResourcePolicy:
    env = os.environ
    policy = ResourcePolicy()
    # Allow overrides via ATLAS_RESOURCE_... env vars
    try:
        if env.get("ATLAS_MAX_ACCEPTED_UPLOAD_MIB"):
            policy.max_accepted_upload_bytes = (
                int(env["ATLAS_MAX_ACCEPTED_UPLOAD_MIB"]) * 1024 * 1024
            )
        # worker memory limit in MiB
        if env.get("ATLAS_WORKER_MEMORY_LIMIT_MIB"):
            policy.worker_memory_limit_bytes = (
                int(env["ATLAS_WORKER_MEMORY_LIMIT_MIB"]) * 1024 * 1024
            )
        if env.get("ATLAS_WORKER_TIMEOUT_SECONDS"):
            policy.worker_timeout_seconds = int(env["ATLAS_WORKER_TIMEOUT_SECONDS"])
        if env.get("ATLAS_WORKER_SOFT_RSS_WARNING_MIB"):
            policy.worker_soft_rss_warning_bytes = (
                int(env["ATLAS_WORKER_SOFT_RSS_WARNING_MIB"]) * 1024 * 1024
            )
        if env.get("ATLAS_MAX_RETRY_COUNT"):
            policy.max_retry_count = int(env["ATLAS_MAX_RETRY_COUNT"])
        if env.get("ATLAS_RETRY_BACKOFF_SECONDS"):
            policy.retry_backoff_seconds = int(env["ATLAS_RETRY_BACKOFF_SECONDS"])
    except Exception:
        pass
    return policy


DEFAULT_POLICY: ResourcePolicy = load_policy_from_env()
