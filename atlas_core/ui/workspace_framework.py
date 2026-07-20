"""Shared workspace shell helpers for Atlas pages.

This module centralizes reusable page-header, data-table, and object-summary
rendering so workspace surfaces can share the same interaction grammar without
duplicating Streamlit layout code in the app shell.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from html import escape
from typing import Any

from .design_system import (
    render_empty_state_html,
    render_guided_empty_state_html,
    render_metric_card_html,
    render_notice_panel_html,
    render_status_badge_html,
    render_workspace_context_html,
)


def _safe_text(value: Any, default: str = "Unknown") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or default
    return str(value)


def render_page_header(st: Any, title: str, subtitle: str) -> None:
    resolved_title = _safe_text(title, "")
    if resolved_title:
        st.subheader(resolved_title)
    resolved_subtitle = _safe_text(subtitle, "")
    if resolved_subtitle:
        st.caption(resolved_subtitle)


def render_data_table(st: Any, rows: list[dict[str, Any]]) -> None:
    st.dataframe(rows, width="stretch", hide_index=True)


def render_empty_state(st: Any, message: str) -> None:
    st.markdown(render_empty_state_html(message), unsafe_allow_html=True)


def render_guided_empty_state(
    st: Any,
    *,
    why_empty: str,
    action_to_populate: str,
    next_location: str,
) -> None:
    st.markdown(
        render_guided_empty_state_html(
            why_empty=why_empty,
            action_to_populate=action_to_populate,
            next_location=next_location,
        ),
        unsafe_allow_html=True,
    )


def render_workspace_context(
    st: Any,
    *,
    workspace: str,
    objective: str,
    current_focus: str,
) -> None:
    st.markdown(
        render_workspace_context_html(
            workspace=workspace,
            objective=objective,
            current_focus=current_focus,
        ),
        unsafe_allow_html=True,
    )


def render_notice_panel(st: Any, title: str, body: str) -> None:
    st.markdown(render_notice_panel_html(title, body), unsafe_allow_html=True)


def render_status_badge(st: Any, label: str, tone: str = "neutral") -> None:
    st.markdown(render_status_badge_html(label, tone), unsafe_allow_html=True)


def render_metric_cards(st: Any, cards: Sequence[tuple[str, str]]) -> None:
    columns = st.columns(len(cards)) if cards else []
    for column, (label, value) in zip(columns, cards):
        column.markdown(render_metric_card_html(label, value), unsafe_allow_html=True)


def render_section_title(st: Any, title: str) -> None:
    st.markdown(f"### {escape(_safe_text(title, 'Section'))}")


def render_object_action_bar(
    st: Any,
    actions: Sequence[dict[str, Any]],
    *,
    key_prefix: str,
) -> None:
    visible_actions = [item for item in actions if bool(item.get("visible", True))]
    if not visible_actions:
        st.caption("No actions available.")
        return

    columns = st.columns(min(3, max(1, len(visible_actions))))
    for index, action in enumerate(visible_actions[:6]):
        label = _safe_text(action.get("label"), "Action")
        enabled = bool(action.get("enabled", True))
        column = columns[index % len(columns)]
        if (
            column.button(
                label,
                key=f"{key_prefix}_{_safe_text(action.get('action_key'), 'action')}_{index}",
                width="stretch",
                disabled=not enabled,
            )
            and enabled
        ):
            callback = action.get("on_click")
            if callable(callback):
                callback()
        if not enabled:
            column.caption(
                _safe_text(action.get("disabled_reason"), "Action unavailable")
            )


def render_object_header(
    st: Any,
    *,
    object_name: str,
    description: str,
    badges: Sequence[str],
    recommended_action: str,
    primary_action_label: str,
    primary_action_key: str,
    add_pin_label: str,
    remove_pin_label: str,
    toggle_pin_key: str,
    pinned: bool,
    on_primary_action: Callable[[], None] | None = None,
    on_toggle_pin: Callable[[bool], None] | None = None,
) -> None:
    st.markdown(f"#### {escape(_safe_text(object_name, 'Object'))}")
    resolved_description = _safe_text(description, "")
    if resolved_description:
        st.caption(resolved_description)

    resolved_badges = [
        escape(_safe_text(badge, "")) for badge in badges if _safe_text(badge, "")
    ]
    if resolved_badges:
        st.markdown(" ".join([f"`{badge}`" for badge in resolved_badges]))

    header_cols = st.columns([5.5, 2.25, 2.25])
    header_cols[0].caption(
        f"Recommended action: {_safe_text(recommended_action, 'Action')}"
    )
    if header_cols[1].button(
        _safe_text(primary_action_label, "Open"),
        key=primary_action_key,
        width="stretch",
    ):
        if on_primary_action is not None:
            on_primary_action()

    pin_label = remove_pin_label if pinned else add_pin_label
    if header_cols[2].button(
        pin_label,
        key=toggle_pin_key,
        width="stretch",
    ):
        if on_toggle_pin is not None:
            on_toggle_pin(not pinned)
