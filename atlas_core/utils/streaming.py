"""Streaming helpers for safe file persistence and incremental hashing."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable


def incremental_sha1_from_bytes_iterable(chunks: Iterable[bytes]) -> str:
    """Compute SHA1 incrementally from an iterable of byte chunks."""
    digest = hashlib.sha1()
    for chunk in chunks:
        if not chunk:
            continue
        digest.update(chunk)
    return digest.hexdigest()


def incremental_sha1_from_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA1 for a file by reading it in chunks.

    This avoids building the whole file in memory.
    """
    digest = hashlib.sha1()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stream_bytes_to_file(data_iter: Iterable[bytes], destination: Path) -> None:
    """Write an iterable of bytes to destination in binary mode.

    The caller is responsible for providing chunks rather than a single big
    bytes object to avoid large memory pressure.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as fh:
        for chunk in data_iter:
            if chunk:
                fh.write(chunk)
