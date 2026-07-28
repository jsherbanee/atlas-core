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


def load_policy_from_env() -> ResourcePolicy:
    env = os.environ
    policy = ResourcePolicy()
    # Allow overrides via ATLAS_RESOURCE_... env vars
    try:
        if env.get("ATLAS_MAX_ACCEPTED_UPLOAD_MIB"):
            policy.max_accepted_upload_bytes = (
                int(env["ATLAS_MAX_ACCEPTED_UPLOAD_MIB"]) * 1024 * 1024
            )
    except Exception:
        pass
    return policy


DEFAULT_POLICY: ResourcePolicy = load_policy_from_env()
