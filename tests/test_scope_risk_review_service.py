from atlas_core.services.scope_risk_review_service import ScopeRiskReviewService


def test_build_findings_produces_ranked_actionable_results():
    bom_rows = [
        {
            "bom_item_id": "eq-1",
            "manufacturer": "",
            "model": "",
            "description": "Display",
            "quantity": "",
            "system": "Video",
            "room_or_area": "Lobby",
            "completeness_status": "conflicting_quantity",
            "responsibility": "unknown",
            "source_documents": ["drawings/av-101.pdf"],
            "source_pages": ["1"],
            "drawing_references": ["AV-101"],
            "specification_references": [],
        },
        {
            "bom_item_id": "eq-2",
            "manufacturer": "QSC",
            "model": "Core Nano",
            "description": "Control processor",
            "quantity": "1",
            "system": "Control",
            "room_or_area": "Control Room",
            "completeness_status": "unresolved",
            "responsibility": "tbd",
            "source_documents": ["specs/27-41-26.pdf"],
            "source_pages": ["4"],
            "drawing_references": [],
            "specification_references": ["27 41 26"],
        },
    ]
    resolver_rows = [
        {
            "target_id": "equipment:eq-1",
            "field": "quantity",
            "message": "Quantity differs between sources.",
        }
    ]

    findings = ScopeRiskReviewService().build_findings(
        bom_rows=bom_rows,
        resolver_rows=resolver_rows,
        coordination_findings=[{"finding_id": "coord-1", "category": "alignment"}],
        risk_rows=[{"message": "Allowance may apply."}],
    )

    assert findings
    assert findings[0].impact_score >= findings[-1].impact_score
    categories = {item.category for item in findings}
    assert "quantity_conflict" in categories
    assert "missing_manufacturer" in categories
    assert "missing_model" in categories
    assert "missing_quantity" in categories
    assert "unclear_ofe_ofci_cfci_nic_responsibility" in categories


def test_findings_include_required_fields_and_internal_rfi_language():
    findings = ScopeRiskReviewService().build_findings(
        bom_rows=[
            {
                "bom_item_id": "eq-9",
                "manufacturer": "Atlas",
                "model": "Model-9",
                "description": "Projector",
                "quantity": "1",
                "system": "Projection",
                "room_or_area": "Auditorium",
                "completeness_status": "drawing_only",
                "responsibility": "unknown",
                "source_documents": ["drawings/av-402.pdf"],
                "source_pages": ["2"],
                "drawing_references": ["AV-402"],
                "specification_references": [],
            }
        ],
        risk_rows=[{"message": "add-alternate pricing note"}],
    )

    sample = findings[0].to_dict()
    required_fields = {
        "finding_id",
        "category",
        "severity",
        "confidence",
        "title",
        "concise_explanation",
        "affected_bom_items",
        "affected_systems",
        "affected_rooms",
        "source_references",
        "estimating_impact",
        "recommended_action",
        "likely_owner",
        "candidate_rfi_text",
    }
    assert required_fields.issubset(set(sample.keys()))
    assert all("Internal draft RFI" in item.candidate_rfi_text for item in findings)


def test_sectioned_rows_include_required_page_sections():
    findings = ScopeRiskReviewService().build_findings(
        bom_rows=[
            {
                "bom_item_id": "eq-x",
                "manufacturer": "",
                "model": "",
                "description": "DSP",
                "quantity": "",
                "system": "Control",
                "room_or_area": "Rack",
                "completeness_status": "conflicting_quantity",
                "responsibility": "unknown",
                "source_documents": ["drawings/av-501.pdf"],
                "source_pages": ["6"],
                "drawing_references": ["AV-501"],
                "specification_references": ["27 41 26"],
            }
        ],
        resolver_rows=[{"target_id": "equipment:eq-x", "field": "quantity"}],
        risk_rows=[{"message": "allowance language"}],
    )

    sections = ScopeRiskReviewService.sectioned_rows(findings)
    assert "Critical Issues" in sections
    assert "Missing Scope" in sections
    assert "Responsibility Gaps" in sections
    assert "Quantity Conflicts" in sections
    assert "Engineering Gaps" in sections
    assert "Commercial Risks" in sections
    assert "Recommended RFIs" in sections
