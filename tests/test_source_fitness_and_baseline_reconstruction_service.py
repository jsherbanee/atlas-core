from __future__ import annotations

from types import SimpleNamespace

from atlas_core.domain.document_intake import DocumentIntakeSnapshot
from atlas_core.services.evidence_baseline_reconstruction_service import (
    EvidenceBaselineReconstructionService,
)
from atlas_core.services.source_fitness_service import SourceFitnessService


def _snapshot() -> DocumentIntakeSnapshot:
    return DocumentIntakeSnapshot(
        snapshot_id="snapshot-001",
        package_path="/tmp/maw",
        metadata={"project_id": "BID-2026-0002"},
        discovered_files={
            "drawings": [
                "08_Audio Visual Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf"
            ],
            "specifications": ["Div 27 Communications.pdf"],
            "reports": ["2025.12.15 MAW 100DD Acoustics Narrative by Kirkegaard.pdf"],
            "schedules": ["Div 11 Equipment.pdf"],
        },
        raw_pages=[
            {
                "source_file": "08_Audio Visual Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf",
                "page_number": 1,
                "text": "AV-101 plan drawing with no signal flow, rack topology, or cable identification.",
                "sheet_number": "AV-101",
            },
            {
                "source_file": "Div 27 Communications.pdf",
                "page_number": 42,
                "text": (
                    "APPENDIX A: BASE EQUIPMENT SCHEDULE\n"
                    "A.2 SPECIFIED EQUIPMENT, BASE SYSTEM\n"
                    "Performance Space\n"
                    "Description Device Type Make Model Qty\n"
                    "LOUDSPEAKERS\n"
                    "Loudspeaker Mains S-01 K-Array GH4A 15\n"
                    "Digital Mixing Console Yamaha DM7 1\n"
                    "Intercom base station Clear-Com Arcadia-X4-16P 1\n"
                ),
            },
            {
                "source_file": "Div 27 Communications.pdf",
                "page_number": 44,
                "text": (
                    "Pre-function\n"
                    "Description Device Type Make Model Qty\n"
                    "AUDIO\n"
                    "Pendant Distributed Audio Loudspeaker S-06 QSC AD-P6T 3\n"
                    "VIDEO\n"
                    "Digital Signage Display Samsung QB55C 1\n"
                ),
            },
            {
                "source_file": "Div 27 Communications.pdf",
                "page_number": 45,
                "text": (
                    "Dressing Rooms (Typical of 3)\n"
                    "Description Device Type Make Model Qty\n"
                    "AUDIO\n"
                    "In-ceiling Distributed Audio Loudspeaker S-07 QSC NL-C4 PoE+ 2\n"
                ),
            },
            {
                "source_file": "2025.12.15 MAW 100DD Acoustics Narrative by Kirkegaard.pdf",
                "page_number": 1,
                "text": "Acoustics narrative and design narrative for coordination review.",
            },
            {
                "source_file": "Div 11 Equipment.pdf",
                "page_number": 10,
                "text": "11 61 11 - 4 by a licensed electrician and conform to construction shall reflect.",
            },
        ],
        raw_sections=[
            {
                "source_file": "Div 27 Communications.pdf",
                "page_number": 42,
                "section_number": "27 41 00",
                "title": "A1",
                "source_excerpt": "A1",
            }
        ],
        raw_device_schedules=[
            {
                "source_file": "Div 11 Equipment.pdf",
                "page_number": 10,
                "schedule_id": "det-noise-001",
                "title": "Detected schedule from Div 11 Equipment.pdf page 10",
                "rows": [
                    {
                        "tag": "1. Control system is a unified control architecture",
                        "description": "and user interface that is programmable logic",
                    }
                ],
            }
        ],
        equipment_candidates=[],
    )


def _review() -> SimpleNamespace:
    readiness = SimpleNamespace(readiness_score=0.53)
    return SimpleNamespace(
        readiness=readiness,
        equipment=[],
        rooms=[],
        cross_references=[],
        specification_sections=[],
        rfi_candidates=[],
        reconciliation_issues=[],
        scope_gaps=[],
    )


def test_source_fitness_ranks_content_over_document_type() -> None:
    snapshot = _snapshot()
    result = SourceFitnessService().assess_snapshot(snapshot)
    by_file = {
        assessment.source_file: assessment for assessment in result.document_assessments
    }

    assert (
        by_file["Div 27 Communications.pdf"].fitness_status
        == "strong_baseline_evidence"
    )
    assert (
        by_file[
            "08_Audio Visual Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf"
        ].fitness_score
        < by_file["Div 27 Communications.pdf"].fitness_score
    )
    assert (
        by_file[
            "2025.12.15 MAW 100DD Acoustics Narrative by Kirkegaard.pdf"
        ].fitness_status
        == "supplemental_evidence"
    )


def test_incomplete_drawings_rank_below_detailed_specifications() -> None:
    snapshot = _snapshot()
    result = SourceFitnessService().assess_snapshot(snapshot)
    by_file = {
        assessment.source_file: assessment for assessment in result.document_assessments
    }

    assert (
        by_file["Div 27 Communications.pdf"].fitness_score
        > by_file[
            "08_Audio Visual Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf"
        ].fitness_score
    )
    assert (
        by_file[
            "08_Audio Visual Music Academy of the West 80_ CD Plan Check 2026.05.29.pdf"
        ].fitness_status
        == "governing_but_incomplete"
    )


def test_baseline_reconstruction_uses_appendix_pages_and_dedupes_rows() -> None:
    snapshot = _snapshot()
    result = EvidenceBaselineReconstructionService().build(snapshot, review=_review())

    assert len(result.major_system_components) > 0
    assert len(result.baseline_equipment) <= len(result.major_system_components)
    assert len(result.room_inventory) > 0
    assert any(row.page_number == 42 for row in result.major_system_components)
    assert any(row.page_number == 44 for row in result.major_system_components)


def test_source_deficiencies_separate_noise_from_drawing_gaps() -> None:
    snapshot = _snapshot()
    result = EvidenceBaselineReconstructionService().build(snapshot, review=_review())

    deficiency_types = {row.deficiency_type for row in result.source_deficiencies}
    assert "extraction_noise" in deficiency_types
    assert "drawing deficiency" in deficiency_types
    assert all(
        row.source_file in snapshot.discovered_files["drawings"]
        or row.source_file in snapshot.discovered_files["specifications"]
        or row.source_file in snapshot.discovered_files["reports"]
        or row.source_file in snapshot.discovered_files["schedules"]
        for row in result.source_deficiencies
    )


def test_rfi_consolidation_groups_root_issues() -> None:
    snapshot = _snapshot()
    result = EvidenceBaselineReconstructionService().build(snapshot, review=_review())

    root_issues = [row.root_issue for row in result.consolidated_rfis]
    assert len(root_issues) == len(set(root_issues))
    assert len(result.consolidated_rfis) < len(result.major_system_components)


def test_deterministic_output_and_no_cross_project_contamination() -> None:
    snapshot = _snapshot()
    service = EvidenceBaselineReconstructionService()
    first = service.build(snapshot, review=_review())
    second = service.build(snapshot, review=_review())

    assert [row.to_dict() for row in first.major_system_components] == [
        row.to_dict() for row in second.major_system_components
    ]
    assert [row.to_dict() for row in first.baseline_equipment] == [
        row.to_dict() for row in second.baseline_equipment
    ]
    assert {
        assessment.source_file
        for assessment in first.source_fitness.document_assessments
    } <= {
        file_name for files in snapshot.discovered_files.values() for file_name in files
    }
