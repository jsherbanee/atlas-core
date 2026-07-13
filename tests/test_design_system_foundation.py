from __future__ import annotations

from atlas_core.ui.design_system import (
    ATLAS_TOKENS,
    atlas_stylesheet,
    render_empty_state_html,
    render_guided_empty_state_html,
    render_metric_card_html,
    render_notice_panel_html,
    render_status_badge_html,
    render_workspace_context_html,
)


def test_design_tokens_include_core_visual_authority() -> None:
    assert ATLAS_TOKENS["color"]["primary"] == "#004225"
    assert ATLAS_TOKENS["color"]["page_bg"] == "#FAFAF9"
    assert ATLAS_TOKENS["layout"]["max_content_width"] == "1440px"


def test_stylesheet_contains_required_contract_rules() -> None:
    stylesheet = atlas_stylesheet()
    assert "--atlas-page-bg: #FAFAF9" in stylesheet
    assert "--atlas-primary: #004225" in stylesheet
    assert "--atlas-red: #dc2626" in stylesheet
    assert "max-width: 1440px" in stylesheet
    assert "width: min(calc(100% - 2rem), 1440px)" in stylesheet
    assert '.stButton > button[kind="primary"]' in stylesheet


def test_helper_html_renderers_escape_dynamic_content() -> None:
    metric = render_metric_card_html("A&B", "<script>")
    empty = render_empty_state_html("A&B")
    guided = render_guided_empty_state_html(
        why_empty="A&B",
        action_to_populate="Do <this>",
        next_location="Go > there",
    )
    context = render_workspace_context_html(
        workspace="Knowledge",
        objective="A&B",
        current_focus="Use <filters>",
    )
    notice = render_notice_panel_html("Title&", "Body <value>")

    assert "A&amp;B" in metric
    assert "&lt;script&gt;" in metric
    assert "A&amp;B" in empty
    assert "Do &lt;this&gt;" in guided
    assert "Go &gt; there" in guided
    assert "Use &lt;filters&gt;" in context
    assert "Body &lt;value&gt;" in notice


def test_status_badge_renderer_normalizes_tone() -> None:
    assert "atlas-status-badge--success" in render_status_badge_html("Ready", "success")
    assert "atlas-status-badge--neutral" in render_status_badge_html("Ready", "invalid")
