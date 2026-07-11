import json

from atlas_core.services.sales_design_review_service import SalesDesignReviewService


def test_build_review_includes_required_sections_and_limits():
    summary = {
        "project_name": "MAW Demo",
        "analysis_status": "Analysis complete",
        "project_type": "Corporate Office",
        "customer": "Atlas Customer",
        "document_count": 6,
        "documents_requiring_ocr": 1,
        "high_risk_issue_count": 4,
        "recommended_next_action": "Review unresolved quantities with consultant.",
    }
    bom_rows = [
        {
            "bom_item_id": "eq-1",
            "manufacturer": "QSC",
            "model": "Core 110",
            "quantity": "1",
            "system": "Control",
            "completeness_status": "complete",
            "known_cost": 1200,
            "list_price": 1800,
            "pricing_warning": "expired vendor pricing",
        },
        {
            "bom_item_id": "eq-2",
            "manufacturer": "",
            "model": "",
            "quantity": "",
            "system": "Audio",
            "completeness_status": "missing_model",
        },
    ]
    findings = [
        {
            "finding_id": "f-1",
            "section": "Missing Scope",
            "category": "quantity_conflict",
            "severity": "high",
            "title": "Speaker quantity differs between plan and schedule",
            "estimating_impact": "Potential underbid",
            "recommended_action": "Issue RFI to confirm quantity basis.",
            "candidate_rfi_text": "Internal draft RFI: Confirm loudspeaker quantity.",
        },
        {
            "finding_id": "f-2",
            "section": "Responsibility Gaps",
            "category": "drawing_specification_mismatch",
            "severity": "critical",
            "title": "Responsibility for conduit is unclear",
            "estimating_impact": "Risk of scope overlap",
            "recommended_action": "Clarify OFCI/OFE assignment.",
        },
    ]

    review = SalesDesignReviewService().build_review(
        summary=summary,
        bom_rows=bom_rows,
        scope_findings=findings,
    )

    payload = review.to_dict()
    assert payload["project_summary"]["project_name"] == "MAW Demo"
    assert payload["project_type"] == "Corporate Office"
    assert payload["major_systems"]
    assert payload["bom_summary"]["total_lines"] == 2
    assert payload["missing_bom_detail"]
    assert payload["undeveloped_scope"]
    assert payload["major_risk_areas"]
    assert payload["responsibility_gaps"]
    assert payload["quantity_conflicts"]
    assert payload["drawing_specification_coordination_issues"]
    assert payload["product_lifecycle_warnings"]
    assert payload["preliminary_cost_coverage"]["known_cost_coverage_ratio"] == "50%"
    assert payload["labor_confidence"] in {"Low", "Medium", "High"}
    assert payload["recommended_rfis"]
    assert payload["recommended_next_actions"]
    assert 0.0 <= payload["overall_confidence"] <= 1.0
    assert any(
        "Unsupported conclusion label" in item for item in payload["limitations"]
    )


def test_export_formats_include_six_section_structure():
    review = SalesDesignReviewService().build_review(
        summary={
            "project_name": "Bid-01",
            "analysis_status": "Analysis complete",
            "project_type": "Higher Education",
            "customer": "Owner",
            "document_count": 3,
            "documents_requiring_ocr": 0,
            "high_risk_issue_count": 1,
            "recommended_next_action": "Proceed with internal review.",
        },
        bom_rows=[
            {
                "bom_item_id": "eq-a",
                "manufacturer": "A",
                "model": "M1",
                "quantity": "2",
                "system": "Video",
                "completeness_status": "complete",
            }
        ],
        scope_findings=[],
    )

    service = SalesDesignReviewService()
    markdown_text = service.to_markdown(review)
    json_text = service.to_json(review)
    html_text = service.to_html(review)

    assert "## 1. What Atlas Found" in markdown_text
    assert "## 2. What Appears Complete" in markdown_text
    assert "## 3. What Is Missing" in markdown_text
    assert "## 4. What Is Risky" in markdown_text
    assert "## 5. What Needs Clarification" in markdown_text
    assert "## 6. What Should Happen Next" in markdown_text

    payload = json.loads(json_text)
    assert payload["project_summary"]["project_name"] == "Bid-01"
    assert "limitations" in payload
    assert "What Atlas Found" in html_text
    assert "What Should Happen Next" in html_text
