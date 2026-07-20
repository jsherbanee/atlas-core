from __future__ import annotations

from atlas_core.ui.workspace_framework import (
    render_data_table,
    render_object_header,
    render_page_header,
)


class _FakeColumn:
    def __init__(self, clicked_labels: set[str] | None = None) -> None:
        self.clicked_labels = clicked_labels or set()
        self.captions: list[str] = []
        self.buttons: list[tuple[str, str]] = []

    def caption(self, message: str) -> None:
        self.captions.append(message)

    def button(
        self,
        label: str,
        *,
        key: str,
        width: str,
        disabled: bool = False,
    ) -> bool:
        _ = (key, width, disabled)
        self.buttons.append((label, key))
        return label in self.clicked_labels


class _FakeStreamlit:
    def __init__(self, clicked_labels: set[str] | None = None) -> None:
        self.subheaders: list[str] = []
        self.captions: list[str] = []
        self.markdowns: list[str] = []
        self.dataframes: list[tuple[list[dict[str, object]], dict[str, object]]] = []
        self.columns_requested: list[list[float]] = []
        self.columns_pool = [
            _FakeColumn(clicked_labels),
            _FakeColumn(clicked_labels),
            _FakeColumn(clicked_labels),
        ]

    def subheader(self, value: str) -> None:
        self.subheaders.append(value)

    def caption(self, value: str) -> None:
        self.captions.append(value)

    def markdown(self, value: str, unsafe_allow_html: bool = False) -> None:
        _ = unsafe_allow_html
        self.markdowns.append(value)

    def dataframe(self, rows: list[dict[str, object]], **kwargs: object) -> None:
        self.dataframes.append((rows, kwargs))

    def columns(self, spec: list[float]) -> list[_FakeColumn]:
        self.columns_requested.append(spec)
        return self.columns_pool


def test_render_page_header_uses_shared_shell_contract() -> None:
    st = _FakeStreamlit()

    render_page_header(st, " Knowledge ", "  Shared overview  ")

    assert st.subheaders == ["Knowledge"]
    assert st.captions == ["Shared overview"]


def test_render_data_table_stays_stretch_and_hidden_index() -> None:
    st = _FakeStreamlit()

    render_data_table(st, [{"Name": "A&B"}])

    assert st.dataframes == [
        ([{"Name": "A&B"}], {"width": "stretch", "hide_index": True})
    ]


def test_render_object_header_renders_summary_and_calls_actions() -> None:
    st = _FakeStreamlit(clicked_labels={"Open Details", "Add to Working Set"})
    calls: list[object] = []

    render_object_header(
        st,
        object_name="Object <A>",
        description="Shared header",
        badges=["Kind", "Ready"],
        recommended_action="Review",
        primary_action_label="Open Details",
        primary_action_key="primary",
        add_pin_label="Add to Working Set",
        remove_pin_label="Remove from Working Set",
        toggle_pin_key="pin",
        pinned=False,
        on_primary_action=lambda: calls.append("open"),
        on_toggle_pin=lambda should_pin: calls.append(should_pin),
    )

    assert st.markdowns[0] == "#### Object &lt;A&gt;"
    assert "`Kind` `Ready`" in st.markdowns[1]
    assert st.columns_requested == [[5.5, 2.25, 2.25]]
    assert calls == ["open", True]
