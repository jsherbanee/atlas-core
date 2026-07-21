from __future__ import annotations

from atlas_core.contracts.upload_policy import (
    BID_PACKAGE_UPLOAD_ENV_VAR,
    BID_PACKAGE_UPLOAD_MAX_BYTES,
    BID_PACKAGE_UPLOAD_MAX_LABEL,
    BID_PACKAGE_UPLOAD_FORMATS_LABEL,
    bid_package_upload_policy,
)


def test_bid_package_policy_accepts_observed_maw_plan_check_size() -> None:
    policy = bid_package_upload_policy()
    result = policy.validate_file(
        name="09_Theater Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf",
        size_bytes=54_830_000,
    )

    assert result.accepted


def test_bid_package_policy_accepts_exact_limit_and_rejects_one_byte_over() -> None:
    policy = bid_package_upload_policy()

    assert policy.validate_file(
        name="limit.pdf",
        size_bytes=BID_PACKAGE_UPLOAD_MAX_BYTES,
    ).accepted

    rejected = policy.validate_file(
        name="too-large.pdf",
        size_bytes=BID_PACKAGE_UPLOAD_MAX_BYTES + 1,
    )

    assert not rejected.accepted
    assert "200.0 MB" in rejected.message
    assert f"{BID_PACKAGE_UPLOAD_MAX_BYTES + 1:,} bytes" in rejected.message
    assert BID_PACKAGE_UPLOAD_MAX_LABEL in rejected.message
    assert f"{BID_PACKAGE_UPLOAD_MAX_BYTES:,} bytes" in rejected.message


def test_bid_package_policy_rejects_json_and_help_text_matches_formats() -> None:
    policy = bid_package_upload_policy()

    assert "json" not in policy.supported_extensions
    assert not policy.validate_file(name="metadata.json", size_bytes=2).accepted
    assert policy.formats_label == BID_PACKAGE_UPLOAD_FORMATS_LABEL
    assert policy.help_text == (
        "Up to 200 MB per file • "
        "PDF, DOCX, DOC, XLSX, XLS, CSV, JPG, JPEG, PNG, TIF, TIFF, TXT, RTF, ZIP"
    )


def test_bid_package_policy_supports_positive_environment_override() -> None:
    policy = bid_package_upload_policy({BID_PACKAGE_UPLOAD_ENV_VAR: "125"})

    assert policy.max_file_size_bytes == 125_000_000
    assert policy.max_file_size_label == "125 MB per file"


def test_bid_package_policy_ignores_invalid_environment_override() -> None:
    policy = bid_package_upload_policy({BID_PACKAGE_UPLOAD_ENV_VAR: "0"})

    assert policy.max_file_size_bytes == BID_PACKAGE_UPLOAD_MAX_BYTES
