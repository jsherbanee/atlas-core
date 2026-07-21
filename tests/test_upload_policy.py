from __future__ import annotations

from atlas_core.contracts.upload_policy import (
    BID_PACKAGE_UPLOAD_ENV_VAR,
    BID_PACKAGE_UPLOAD_FORMATS_LABEL,
    BID_PACKAGE_UPLOAD_MAX_BATCH_BYTES,
    BID_PACKAGE_UPLOAD_MAX_FILE_BYTES,
    BID_PACKAGE_UPLOAD_MAX_FILE_LABEL,
    BID_PACKAGE_UPLOAD_MAX_FILES,
    MIB,
    UploadBatchFile,
    bid_package_upload_policy,
)


def test_bid_package_policy_accepts_observed_maw_plan_check_size() -> None:
    policy = bid_package_upload_policy()
    result = policy.validate_file(
        name="09_Theater Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf",
        size_bytes=54_830_000,
    )

    assert result.accepted


def test_bid_package_policy_accepts_exact_file_limit_and_rejects_one_byte_over() -> (
    None
):
    policy = bid_package_upload_policy()

    assert policy.validate_file(
        name="limit.pdf",
        size_bytes=BID_PACKAGE_UPLOAD_MAX_FILE_BYTES,
    ).accepted

    rejected = policy.validate_file(
        name="too-large.pdf",
        size_bytes=BID_PACKAGE_UPLOAD_MAX_FILE_BYTES + 1,
    )

    assert not rejected.accepted
    assert "200 MiB" in rejected.message
    assert f"{BID_PACKAGE_UPLOAD_MAX_FILE_BYTES + 1:,} bytes" in rejected.message
    assert BID_PACKAGE_UPLOAD_MAX_FILE_LABEL in rejected.message
    assert f"{BID_PACKAGE_UPLOAD_MAX_FILE_BYTES:,} bytes" in rejected.message


def test_bid_package_policy_rejects_json_and_help_text_matches_formats() -> None:
    policy = bid_package_upload_policy()

    assert "json" not in policy.supported_extensions
    assert not policy.validate_file(name="metadata.json", size_bytes=2).accepted
    assert policy.formats_label == BID_PACKAGE_UPLOAD_FORMATS_LABEL
    assert policy.max_file_size_bytes == 209_715_200
    assert policy.max_batch_size_bytes == 1_073_741_824
    assert policy.max_files_per_batch == 50
    assert policy.help_text == (
        "Up to 200 MiB per file • 1 GiB per batch • 50 files maximum • "
        "PDF, DOCX, DOC, XLSX, XLS, CSV, JPG, JPEG, PNG, TIF, TIFF, TXT, RTF, ZIP"
    )


def test_bid_package_policy_supports_positive_environment_override_in_mib() -> None:
    policy = bid_package_upload_policy({BID_PACKAGE_UPLOAD_ENV_VAR: "125"})

    assert policy.max_file_size_bytes == 125 * MIB
    assert policy.max_file_size_label == "125 MiB"


def test_bid_package_policy_ignores_invalid_environment_override() -> None:
    policy = bid_package_upload_policy({BID_PACKAGE_UPLOAD_ENV_VAR: "0"})

    assert policy.max_file_size_bytes == BID_PACKAGE_UPLOAD_MAX_FILE_BYTES


def test_bid_package_batch_exactly_one_gib_is_accepted() -> None:
    policy = bid_package_upload_policy()

    result = policy.validate_batch(
        [
            UploadBatchFile("part-1.pdf", 200 * MIB, "1"),
            UploadBatchFile("part-2.pdf", 200 * MIB, "2"),
            UploadBatchFile("part-3.pdf", 200 * MIB, "3"),
            UploadBatchFile("part-4.pdf", 200 * MIB, "4"),
            UploadBatchFile("part-5.pdf", 200 * MIB, "5"),
            UploadBatchFile("part-6.pdf", 24 * MIB, "6"),
        ]
    )

    assert result.accepted
    assert result.accepted_size_bytes == BID_PACKAGE_UPLOAD_MAX_BATCH_BYTES
    assert result.selected_summary_label == "6 files selected · 1 GiB of 1 GiB"


def test_bid_package_batch_one_byte_above_one_gib_rejects_only_offending_file() -> None:
    policy = bid_package_upload_policy()

    result = policy.validate_batch(
        [
            UploadBatchFile("part-1.pdf", 200 * MIB, "1"),
            UploadBatchFile("part-2.pdf", 200 * MIB, "2"),
            UploadBatchFile("part-3.pdf", 200 * MIB, "3"),
            UploadBatchFile("part-4.pdf", 200 * MIB, "4"),
            UploadBatchFile("part-5.pdf", 200 * MIB, "5"),
            UploadBatchFile("part-6.pdf", 24 * MIB, "6"),
            UploadBatchFile("overflow.pdf", 1, "7"),
        ]
    )

    assert not result.accepted
    assert len(result.accepted_files) == 6
    rejected = result.rejected_files[0]
    assert rejected.name == "overflow.pdf"
    assert "batch_size_limit" in rejected.reason_codes


def test_bid_package_batch_limit_message_reports_projected_binary_size() -> None:
    policy = bid_package_upload_policy()

    result = policy.validate_batch(
        [
            UploadBatchFile("part-1.pdf", 200 * MIB, "1"),
            UploadBatchFile("part-2.pdf", 200 * MIB, "2"),
            UploadBatchFile("part-3.pdf", 200 * MIB, "3"),
            UploadBatchFile("part-4.pdf", 200 * MIB, "4"),
            UploadBatchFile("part-5.pdf", 200 * MIB, "5"),
            UploadBatchFile("overflow.pdf", 106 * MIB, "6"),
        ]
    )

    assert "This file would increase the batch to 1.08 GiB." in (
        result.rejected_files[0].message
    )
    assert "The maximum batch size is 1 GiB." in result.rejected_files[0].message


def test_bid_package_batch_accepts_50_files_and_rejects_51st() -> None:
    policy = bid_package_upload_policy()

    accepted = policy.validate_batch(
        [UploadBatchFile(f"file-{index}.txt", 1, str(index)) for index in range(50)]
    )
    rejected = policy.validate_batch(
        [UploadBatchFile(f"file-{index}.txt", 1, str(index)) for index in range(51)]
    )

    assert accepted.accepted
    assert accepted.accepted_file_count == BID_PACKAGE_UPLOAD_MAX_FILES
    assert not rejected.accepted
    assert rejected.accepted_file_count == BID_PACKAGE_UPLOAD_MAX_FILES
    assert rejected.rejected_files[0].name == "file-50.txt"
    assert "batch_file_count" in rejected.rejected_files[0].reason_codes


def test_bid_package_batch_rejects_201_mib_file_while_accepting_valid_files() -> None:
    policy = bid_package_upload_policy()

    result = policy.validate_batch(
        [
            UploadBatchFile("valid-1.pdf", 10 * MIB, "1"),
            UploadBatchFile("too-large.pdf", 201 * MIB, "2"),
            UploadBatchFile("valid-2.pdf", 10 * MIB, "3"),
        ]
    )

    assert [item.name for item in result.accepted_files] == [
        "valid-1.pdf",
        "valid-2.pdf",
    ]
    assert result.rejected_files[0].name == "too-large.pdf"
    assert "per_file_limit" in result.rejected_files[0].reason_codes


def test_bid_package_batch_accepts_multiple_valid_files_below_one_gib() -> None:
    policy = bid_package_upload_policy()

    result = policy.validate_batch(
        [
            UploadBatchFile("drawings.pdf", 200 * MIB, "1"),
            UploadBatchFile("specs.docx", 25 * MIB, "2"),
            UploadBatchFile("schedule.xlsx", 12 * MIB, "3"),
        ]
    )

    assert result.accepted
    assert result.selected_summary_label == "3 files selected · 237 MiB of 1 GiB"
    assert result.remaining_capacity_label == "787 MiB remaining in this batch"
