import os
from pathlib import Path
import json

from atlas_core.services.pdf_preflight import classify_pdf
from atlas_core.config.resource_policy import ResourcePolicy


def write_fixture(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_classify_standard(tmp_path):
    p = tmp_path / "standard.pdf"
    # minimal PDF header + body
    write_fixture(p, b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer\n%%EOF\n")
    r = classify_pdf(p)
    assert r.classification in {"standard", "large"}
    assert "missing_pdf_header" not in r.reasons


def test_classify_encrypted_and_pathological(tmp_path, monkeypatch):
    p = tmp_path / "enc.pdf"
    # craft content with /Encrypt and huge /Length
    content = b"%PDF-1.7\n/Encrypt true\n/Linearized true\n1 0 obj<</Length 999999999>>endobj\n%%EOF\n"
    write_fixture(p, content)
    r = classify_pdf(p)
    assert r.attributes.get("encrypted") is True
    assert r.classification == "pathological"


def test_classify_size_thresholds(tmp_path, monkeypatch):
    p = tmp_path / "big.pdf"
    # create a file of 200KB
    big = b"%PDF-1.4\n" + b"0" * 200_000 + b"\n%%EOF\n"
    write_fixture(p, big)
    # monkeypatch policy thresholds to make this "large"
    monkeypatch.setattr("atlas_core.config.resource_policy.DEFAULT_POLICY", ResourcePolicy(large_file_threshold_bytes=100*1024, very_large_file_threshold_bytes=500*1024))
    r = classify_pdf(p)
    assert r.classification == "large"
*** End Patch