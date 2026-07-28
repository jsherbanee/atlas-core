from pathlib import Path

from atlas_core.utils.streaming import (
    incremental_sha1_from_file,
    incremental_sha1_from_bytes_iterable,
)


def test_incremental_sha1_matches_hashlib(tmp_path: Path) -> None:
    data = b"A" * (1024 * 1024 + 123)
    path = tmp_path / "sample.bin"
    path.write_bytes(data)

    file_hash = incremental_sha1_from_file(path)
    iter_hash = incremental_sha1_from_bytes_iterable([data[:1024], data[1024:]])

    import hashlib

    expected = hashlib.sha1(data).hexdigest()
    assert file_hash == expected
    assert iter_hash == expected
