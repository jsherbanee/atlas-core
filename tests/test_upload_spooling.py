from atlas_core.utils.upload_spool import spool_upload_to_tempfile


class FakeUploaded:
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    def read(self, size: int = -1):
        if size is None or size < 0:
            size = len(self._data) - self._pos
        if self._pos >= len(self._data):
            return b""
        start = self._pos
        end = min(len(self._data), self._pos + size)
        self._pos = end
        return self._data[start:end]

    def getvalue(self):
        raise RuntimeError("getvalue must not be called")


def test_spool_does_not_call_getvalue(tmp_path):
    data = b"x" * (1024 * 10)
    f = FakeUploaded(data)
    ref = spool_upload_to_tempfile(
        f, project_id="p1", session_id="s1", original_filename="a.pdf"
    )
    assert ref.size_bytes == len(data)
    assert ref.temporary_path.exists()
    # cleanup
    ref.temporary_path.unlink()
