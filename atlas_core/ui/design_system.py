"""Atlas design-system tokens and reusable HTML/CSS primitives.

This module is intentionally framework-light: it only returns HTML/CSS strings so
Streamlit pages can reuse the same visual authority without introducing a second
UI architecture.
"""

from __future__ import annotations

from html import escape

ATLAS_TOKENS: dict[str, dict[str, str]] = {
    "color": {
        "gray": "#6b7280",
        "primary": "#004225",
        "page_bg": "#FAFAF9",
        "surface": "#FFFFFF",
        "border": "#e5e7eb",
        "hover": "#f3f4f6",
        "primary_soft": "#dce8e2",
        "primary_soft_hover": "#cfdfd8",
        "amber": "#d97706",
        "red": "#dc2626",
        "blue": "#0f4c81",
        "success": "#166534",
        "warning": "#92400e",
        "danger": "#991b1b",
        "neutral": "#334155",
    },
    "radius": {
        "sm": "8px",
        "md": "10px",
        "lg": "12px",
        "pill": "999px",
    },
    "space": {
        "xs": "0.2rem",
        "sm": "0.45rem",
        "md": "0.7rem",
        "lg": "1rem",
    },
    "elevation": {
        "subtle": "0 1px 2px rgba(15, 23, 42, 0.06)",
        "hover": "0 2px 8px rgba(15, 23, 42, 0.08)",
    },
    "layout": {
        "max_content_width": "1440px",
        "input_height": "34px",
        "control_height": "34px",
        "header_wordmark_width": "5.15rem",
        "header_transactions_width": "6.95rem",
        "header_projects_width": "5.8rem",
        "header_knowledge_width": "6.25rem",
        "header_reports_width": "5.6rem",
        "header_settings_width": "5.6rem",
        "header_search_min_width": "9.5rem",
        "header_search_max_width": "15rem",
        "header_breakpoint_compact": "960px",
        "header_breakpoint_narrow": "840px",
        "body_secondary_nav_ratio": "1.35",
        "body_main_nav_ratio": "4.65",
    },
    "typography": {
        "font_interface": "'Fira Sans', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
        "font_display": "'Inria Serif', Georgia, 'Times New Roman', serif",
        "font_mono": "'SFMono-Regular', Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
        "display_xl": "1.68rem",
        "display_l": "1.44rem",
        "heading_1": "1.26rem",
        "heading_2": "1.08rem",
        "heading_3": "0.98rem",
        "body_lg": "0.96rem",
        "body": "0.9rem",
        "body_small": "0.84rem",
        "caption": "0.78rem",
        "label": "0.72rem",
        "value": "0.95rem",
        "line_height_tight": "1.2",
        "line_height_body": "1.45",
        "line_height_relaxed": "1.6",
        "letter_spacing_display": "-0.01em",
        "letter_spacing_heading": "-0.005em",
        "letter_spacing_body": "0",
        "letter_spacing_label": "0.02em",
        "title_size": "1.26rem",
        "subtitle_size": "0.88rem",
    },
}


def atlas_stylesheet() -> str:
    """Return the canonical stylesheet for Atlas app shell components.

    Font loading is centralized here so typography remains deterministic across
    all pages that call _inject_styles. If enterprise deployments require no
    external font fetches, replace the Google Fonts import below with
    self-hosted equivalents and keep token names unchanged.
    """

    c = ATLAS_TOKENS["color"]
    r = ATLAS_TOKENS["radius"]
    s = ATLAS_TOKENS["space"]
    e = ATLAS_TOKENS["elevation"]
    layout = ATLAS_TOKENS["layout"]
    t = ATLAS_TOKENS["typography"]
    return f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fira+Sans:wght@400;500;600&family=Inria+Serif:wght@500;600;700&display=swap');
        :root {{
            --atlas-gray: {c['gray']};
            --atlas-primary: {c['primary']};
            --atlas-page-bg: {c['page_bg']};
            --atlas-surface: {c['surface']};
            --atlas-border: {c['border']};
            --atlas-hover: {c['hover']};
            --atlas-primary-soft: {c['primary_soft']};
            --atlas-primary-soft-hover: {c['primary_soft_hover']};
            --atlas-amber: {c['amber']};
            --atlas-red: {c['red']};
            --atlas-blue: {c['blue']};
            --atlas-success: {c['success']};
            --atlas-warning: {c['warning']};
            --atlas-danger: {c['danger']};
            --atlas-neutral: {c['neutral']};
            --atlas-radius-sm: {r['sm']};
            --atlas-radius-md: {r['md']};
            --atlas-radius-lg: {r['lg']};
            --atlas-radius-pill: {r['pill']};
            --atlas-space-xs: {s['xs']};
            --atlas-space-sm: {s['sm']};
            --atlas-space-md: {s['md']};
            --atlas-space-lg: {s['lg']};
            --atlas-elevation-subtle: {e['subtle']};
            --atlas-elevation-hover: {e['hover']};
            --atlas-max-content-width: {layout['max_content_width']};
            --atlas-control-height: {layout['control_height']};
            --atlas-input-height: {layout['input_height']};
            --atlas-header-wordmark-width: {layout['header_wordmark_width']};
            --atlas-header-transactions-width: {layout['header_transactions_width']};
            --atlas-header-projects-width: {layout['header_projects_width']};
            --atlas-header-knowledge-width: {layout['header_knowledge_width']};
            --atlas-header-reports-width: {layout['header_reports_width']};
            --atlas-header-settings-width: {layout['header_settings_width']};
            --atlas-header-search-min-width: {layout['header_search_min_width']};
            --atlas-header-search-max-width: {layout['header_search_max_width']};
            --atlas-header-breakpoint-compact: {layout['header_breakpoint_compact']};
            --atlas-header-breakpoint-narrow: {layout['header_breakpoint_narrow']};
            --atlas-font-interface: {t['font_interface']};
            --atlas-font-display: {t['font_display']};
            --atlas-font-mono: {t['font_mono']};
            --atlas-display-xl-size: {t['display_xl']};
            --atlas-display-l-size: {t['display_l']};
            --atlas-heading-1-size: {t['heading_1']};
            --atlas-heading-2-size: {t['heading_2']};
            --atlas-heading-3-size: {t['heading_3']};
            --atlas-body-lg-size: {t['body_lg']};
            --atlas-body-size: {t['body']};
            --atlas-caption-size: {t['caption']};
            --atlas-title-size: {t['title_size']};
            --atlas-subtitle-size: {t['subtitle_size']};
            --atlas-label-size: {t['label']};
            --atlas-value-size: {t['value']};
            --atlas-body-small-size: {t['body_small']};
            --atlas-line-height-tight: {t['line_height_tight']};
            --atlas-line-height-body: {t['line_height_body']};
            --atlas-line-height-relaxed: {t['line_height_relaxed']};
            --atlas-letter-spacing-display: {t['letter_spacing_display']};
            --atlas-letter-spacing-heading: {t['letter_spacing_heading']};
            --atlas-letter-spacing-body: {t['letter_spacing_body']};
            --atlas-letter-spacing-label: {t['letter_spacing_label']};
        }}
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
            background: var(--atlas-page-bg) !important;
            font-family: var(--atlas-font-interface) !important;
            font-size: var(--atlas-body-size);
            line-height: var(--atlas-line-height-body);
            letter-spacing: var(--atlas-letter-spacing-body);
        }}
        [data-testid="stAppViewContainer"] p,
        [data-testid="stAppViewContainer"] li,
        [data-testid="stAppViewContainer"] label,
        [data-testid="stAppViewContainer"] input,
        [data-testid="stAppViewContainer"] textarea,
        [data-testid="stAppViewContainer"] button,
        [data-testid="stAppViewContainer"] select {{
            font-family: var(--atlas-font-interface);
        }}
        .material-icons,
        .material-symbols-rounded,
        .material-symbols-outlined {{
            letter-spacing: normal;
        }}
        [data-testid="stIconMaterial"] {{
            font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
            font-style: normal;
            letter-spacing: normal !important;
            font-feature-settings: "liga";
        }}
        code,
        pre,
        kbd,
        samp,
        .stCode,
        .stMarkdown code {{
            font-family: var(--atlas-font-mono) !important;
        }}
        [data-testid="stMarkdownContainer"] h1,
        [data-testid="stMarkdownContainer"] h2,
        [data-testid="stMarkdownContainer"] h3,
        [data-testid="stMarkdownContainer"] h4 {{
            font-family: var(--atlas-font-display) !important;
            font-weight: 600;
            line-height: var(--atlas-line-height-tight);
            letter-spacing: var(--atlas-letter-spacing-heading);
            color: #0f172a;
            margin-top: 0;
            margin-bottom: 0.35rem;
        }}
        [data-testid="stMarkdownContainer"] h1 {{
            font-size: var(--atlas-heading-1-size);
        }}
        [data-testid="stMarkdownContainer"] h2 {{
            font-size: var(--atlas-heading-2-size);
        }}
        [data-testid="stMarkdownContainer"] h3,
        [data-testid="stMarkdownContainer"] h4 {{
            font-size: var(--atlas-heading-3-size);
        }}
        .atlas-title {{
            font-family: var(--atlas-font-display);
            font-size: var(--atlas-heading-1-size);
            font-weight: 600;
            letter-spacing: var(--atlas-letter-spacing-display);
            line-height: var(--atlas-line-height-tight);
            margin-bottom: 0.1rem;
        }}
        .atlas-muted {{
            color: var(--atlas-gray);
            font-size: var(--atlas-caption-size);
            line-height: var(--atlas-line-height-body);
        }}
        .atlas-page-header {{
            margin: 0.15rem 0 0.9rem 0;
            padding-bottom: 0.55rem;
            border-bottom: 1px solid var(--atlas-border);
        }}
        .atlas-page-subtitle {{
            color: #4b5563;
            font-size: var(--atlas-subtitle-size);
            line-height: var(--atlas-line-height-relaxed);
            margin: 0;
        }}
        .atlas-card {{
            border: 1px solid var(--atlas-border);
            border-radius: var(--atlas-radius-md);
            padding: var(--atlas-space-sm) 0.6rem;
            margin-bottom: 0.4rem;
            background: var(--atlas-surface);
            box-shadow: var(--atlas-elevation-subtle);
        }}
        .atlas-card-title {{
            color: #4b5563;
            font-size: var(--atlas-label-size);
            letter-spacing: var(--atlas-letter-spacing-label);
            text-transform: uppercase;
            margin-bottom: 0.15rem;
        }}
        .atlas-card-value {{
            font-size: var(--atlas-body-lg-size);
            font-weight: 600;
            line-height: var(--atlas-line-height-tight);
        }}
        .atlas-action-row,
        .atlas-toolbar,
        .atlas-responsive-control-group {{
            display: grid;
            gap: var(--atlas-space-sm);
            margin-bottom: var(--atlas-space-sm);
        }}
        .atlas-content-section {{
            border: 1px solid var(--atlas-border);
            border-radius: var(--atlas-radius-lg);
            background: var(--atlas-surface);
            padding: var(--atlas-space-md);
            margin: 0.35rem 0 0.65rem 0;
            box-shadow: var(--atlas-elevation-subtle);
        }}
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        .main .block-container {{
            overflow-x: clip;
        }}
        .atlas-content-section h3,
        .atlas-content-section h4 {{
            margin-top: 0;
            margin-bottom: 0.3rem;
        }}
        .main .block-container {{
            max-width: 1440px;
            width: min(calc(100% - 2rem), 1440px);
            margin: 0 auto;
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 0.55rem;
        }}
        .atlas-statusbar {{
            border-top: 1px solid var(--atlas-border);
            margin-top: 1rem;
            padding-top: 0.45rem;
        }}
        .atlas-chip {{
            border-radius: var(--atlas-radius-pill);
            padding: 2px 8px;
            border: 1px solid var(--atlas-border);
            font-size: var(--atlas-caption-size);
            display: inline-block;
            margin-right: 4px;
            margin-top: 2px;
            background: var(--atlas-surface);
        }}
        .atlas-status-badge {{
            border-radius: var(--atlas-radius-pill);
            display: inline-block;
            font-size: var(--atlas-caption-size);
            font-weight: 600;
            letter-spacing: var(--atlas-letter-spacing-label);
            line-height: 1;
            padding: 0.3rem 0.5rem;
            border: 1px solid transparent;
            margin-right: 0.3rem;
        }}
        .atlas-status-badge--success {{
            background: color-mix(in srgb, var(--atlas-success) 12%, white);
            border-color: color-mix(in srgb, var(--atlas-success) 38%, white);
            color: var(--atlas-success);
        }}
        .atlas-status-badge--warning {{
            background: color-mix(in srgb, var(--atlas-warning) 12%, white);
            border-color: color-mix(in srgb, var(--atlas-warning) 36%, white);
            color: var(--atlas-warning);
        }}
        .atlas-status-badge--danger {{
            background: color-mix(in srgb, var(--atlas-danger) 12%, white);
            border-color: color-mix(in srgb, var(--atlas-danger) 36%, white);
            color: var(--atlas-danger);
        }}
        .atlas-status-badge--neutral {{
            background: #eef2f7;
            border-color: #d5dde8;
            color: var(--atlas-neutral);
        }}
        .atlas-notice-panel {{
            border-radius: var(--atlas-radius-md);
            border: 1px solid var(--atlas-border);
            background: #f7faf9;
            padding: 0.55rem 0.75rem;
            margin: 0.35rem 0 0.65rem 0;
            color: #0f172a;
            font-size: var(--atlas-body-size);
            line-height: var(--atlas-line-height-relaxed);
        }}
        .atlas-notice-panel strong {{
            color: #0b3f2a;
        }}
        .atlas-lifecycle-timeline {{
            display: flex;
            gap: 0.6rem;
            overflow-x: auto;
            padding: 0.2rem 0 0.5rem 0;
            margin: 0.35rem 0 0.7rem 0;
        }}
        .atlas-lifecycle-stage-wrap {{
            min-width: 150px;
            flex: 0 0 auto;
        }}
        .atlas-lifecycle-stage {{
            border: 1px solid var(--atlas-border);
            border-radius: var(--atlas-radius-md);
            background: var(--atlas-surface);
            padding: 0.55rem 0.65rem;
            box-shadow: var(--atlas-elevation-subtle);
        }}
        .atlas-lifecycle-stage--current {{
            box-shadow: 0 0 0 1px color-mix(in srgb, var(--atlas-primary) 45%, white);
        }}
        .atlas-lifecycle-stage--selected {{
            border-color: color-mix(in srgb, var(--atlas-primary) 55%, white);
            background: #fcfcfb;
        }}
        .atlas-lifecycle-stage--complete {{
            background: color-mix(in srgb, var(--atlas-success) 10%, white);
            border-color: color-mix(in srgb, var(--atlas-success) 32%, white);
        }}
        .atlas-lifecycle-stage--active {{
            background: color-mix(in srgb, var(--atlas-primary) 10%, white);
            border-color: color-mix(in srgb, var(--atlas-primary) 30%, white);
        }}
        .atlas-lifecycle-stage--available {{
            background: #f7faf9;
            border-color: #cfd8e3;
        }}
        .atlas-lifecycle-stage--blocked {{
            background: color-mix(in srgb, var(--atlas-danger) 10%, white);
            border-color: color-mix(in srgb, var(--atlas-danger) 34%, white);
        }}
        .atlas-lifecycle-stage--skipped {{
            background: color-mix(in srgb, var(--atlas-warning) 10%, white);
            border-color: color-mix(in srgb, var(--atlas-warning) 30%, white);
        }}
        .atlas-lifecycle-stage--archived {{
            background: #f3f4f6;
            border-color: #d1d5db;
        }}
        .atlas-lifecycle-stage-title {{
            font-size: var(--atlas-body-size);
            font-weight: 600;
            line-height: var(--atlas-line-height-tight);
            color: #0f172a;
            margin-bottom: 0.18rem;
        }}
        .atlas-lifecycle-stage-status {{
            font-size: var(--atlas-caption-size);
            color: #475569;
            letter-spacing: var(--atlas-letter-spacing-label);
            text-transform: uppercase;
        }}
        .atlas-table-shell [data-testid="stDataFrame"] {{
            margin-top: 0.15rem;
        }}
        .atlas-object-card,
        .atlas-empty-state,
        .atlas-search-row {{
            border: 1px solid var(--atlas-border);
            border-radius: var(--atlas-radius-lg);
            padding: 0.55rem 0.7rem;
            margin-bottom: 0.45rem;
            background: var(--atlas-surface);
            transition: all 120ms ease-in-out;
        }}
        .atlas-search-row:hover {{
            border-color: #cbd5e1;
            background: #fcfcfb;
            box-shadow: var(--atlas-elevation-hover);
        }}
        .atlas-object-header {{
            font-size: var(--atlas-body-small-size);
            color: #334155;
            font-weight: 600;
            letter-spacing: var(--atlas-letter-spacing-label);
            text-transform: uppercase;
            margin-bottom: 0.15rem;
        }}
        .atlas-project-header {{
            position: sticky;
            top: 0;
            z-index: 10;
            border: 1px solid var(--atlas-border);
            background: var(--atlas-surface);
            border-radius: var(--atlas-radius-lg);
            padding: 0.7rem 0.85rem;
            margin: 0.35rem 0 0.55rem 0;
        }}
        .atlas-project-name {{
            font-family: var(--atlas-font-display);
            font-size: var(--atlas-display-l-size);
            font-weight: 600;
            line-height: var(--atlas-line-height-tight);
            letter-spacing: var(--atlas-letter-spacing-display);
            color: #0f172a;
            margin-bottom: 0.05rem;
        }}
        .atlas-project-customer {{
            color: #334155;
            font-size: var(--atlas-body-size);
            margin-bottom: 0.3rem;
        }}
        .atlas-project-meta {{
            color: #475569;
            font-size: var(--atlas-caption-size);
            margin-top: 0.25rem;
        }}
        .atlas-workspace-context {{
            border: 1px solid var(--atlas-border);
            border-radius: var(--atlas-radius-md);
            background: #fcfcfb;
            padding: 0.45rem 0.65rem;
            margin: 0.2rem 0 0.75rem 0;
            color: #475569;
            font-size: var(--atlas-body-small-size);
            line-height: var(--atlas-line-height-relaxed);
        }}
        .atlas-empty-title {{
            font-family: var(--atlas-font-display);
            font-size: var(--atlas-heading-2-size);
            font-weight: 600;
            letter-spacing: var(--atlas-letter-spacing-heading);
            color: #0f172a;
            margin-bottom: 0.2rem;
        }}
        .atlas-empty-copy {{
            color: #475569;
            font-size: var(--atlas-body-size);
            line-height: var(--atlas-line-height-relaxed);
            margin: 0;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.35rem;
            padding-bottom: 0.35rem;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: var(--atlas-radius-sm);
            border: 1px solid var(--atlas-border);
            background: #f8f8f7;
            color: #1f2937;
            height: var(--atlas-control-height);
            padding: 0 0.7rem;
            font-weight: 500;
            font-size: var(--atlas-body-small-size);
        }}
        .stTabs [data-baseweb="tab"][aria-selected="true"] {{
            border-color: var(--atlas-primary);
            background: var(--atlas-primary-soft);
            color: var(--atlas-primary);
        }}
        .stButton > button[kind="primary"] {{
            background: var(--atlas-primary) !important;
            border-color: var(--atlas-primary) !important;
            color: #ffffff !important;
            border-radius: var(--atlas-radius-sm) !important;
            font-weight: 600 !important;
            font-size: var(--atlas-body-small-size) !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            background: #00351e !important;
            border-color: #00351e !important;
        }}
        .stButton > button[kind="secondary"] {{
            border-radius: var(--atlas-radius-sm) !important;
            border-color: var(--atlas-border) !important;
            background: var(--atlas-surface) !important;
            color: #111827 !important;
            font-size: var(--atlas-body-small-size) !important;
            font-weight: 500 !important;
        }}
        .stButton > button[kind="secondary"]:hover {{
            background: var(--atlas-hover) !important;
        }}
        .stTextInput input,
        .stSelectbox div[data-baseweb="select"] > div,
        .stTextArea textarea,
        .stNumberInput input {{
            border-radius: var(--atlas-radius-sm) !important;
            border-color: var(--atlas-border) !important;
            background: var(--atlas-surface) !important;
            min-height: var(--atlas-input-height) !important;
        }}
        .stTextInput input:focus,
        .stTextInput input:focus-visible,
        .stTextArea textarea:focus,
        .stTextArea textarea:focus-visible,
        .stSelectbox div[data-baseweb="select"] > div:focus,
        .stSelectbox div[data-baseweb="select"] > div:focus-visible,
        .stButton > button:focus,
        .stButton > button:focus-visible {{
            border-color: var(--atlas-primary) !important;
            box-shadow: 0 0 0 1px var(--atlas-primary) !important;
            outline: none !important;
        }}
        [data-testid="stDataFrame"] {{
            border: 1px solid var(--atlas-border);
            border-radius: var(--atlas-radius-md);
            max-width: 100%;
            overflow-x: auto;
            overflow-y: hidden;
            background: var(--atlas-surface);
        }}
        [data-testid="stDataFrame"] [role="columnheader"] {{
            font-size: var(--atlas-label-size);
            font-weight: 600;
            letter-spacing: var(--atlas-letter-spacing-label);
            text-transform: uppercase;
        }}
        [data-testid="stDataFrame"] [role="gridcell"] {{
            font-size: var(--atlas-body-small-size);
            line-height: var(--atlas-line-height-body);
        }}
        [class*="st-key-atlas_header_nav_"] button,
        [class*="st-key-atlas_top_nav_"] button {{
            border: 1px solid var(--atlas-border) !important;
            box-shadow: none !important;
            background: var(--atlas-surface) !important;
            color: #111827 !important;
            min-width: 0 !important;
            padding: 0.18rem 0.3rem !important;
            font-weight: 600 !important;
            line-height: 1.1 !important;
            border-radius: var(--atlas-radius-sm) !important;
            font-size: 0.79rem !important;
            min-height: 2rem !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }}
        [class*="st-key-atlas_header_nav_"] button:hover,
        [class*="st-key-atlas_top_nav_"] button:hover {{
            background: var(--atlas-hover) !important;
        }}
        [class*="st-key-atlas_header_nav_"] button:focus,
        [class*="st-key-atlas_header_nav_"] button:focus-visible,
        [class*="st-key-atlas_top_nav_"] button:focus,
        [class*="st-key-atlas_top_nav_"] button:focus-visible {{
            outline: 2px solid var(--atlas-primary) !important;
            outline-offset: 2px !important;
        }}
        [class*="st-key-atlas_header_nav_"] button[kind="primary"],
        [class*="st-key-atlas_top_nav_"] button[kind="primary"] {{
            background: var(--atlas-primary-soft) !important;
            border-color: color-mix(in srgb, var(--atlas-primary) 30%, white) !important;
            color: var(--atlas-primary) !important;
        }}
        [class*="st-key-atlas_header_nav_"] button[kind="primary"]:hover,
        [class*="st-key-atlas_top_nav_"] button[kind="primary"]:hover {{
            background: var(--atlas-primary-soft-hover) !important;
        }}
        .st-key-atlas_header_nav_Atlas button {{
            width: var(--atlas-header-wordmark-width) !important;
            max-width: var(--atlas-header-wordmark-width) !important;
            min-width: var(--atlas-header-wordmark-width) !important;
        }}
        .st-key-atlas_header_nav_Atlas button p {{
            font-family: var(--atlas-font-display) !important;
            font-size: var(--atlas-heading-3-size) !important;
            font-weight: 700 !important;
            letter-spacing: var(--atlas-letter-spacing-display) !important;
            line-height: var(--atlas-line-height-tight) !important;
        }}
        .st-key-atlas_header_nav_Transactions button {{
            width: var(--atlas-header-transactions-width) !important;
            max-width: var(--atlas-header-transactions-width) !important;
            min-width: var(--atlas-header-transactions-width) !important;
        }}
        .st-key-atlas_header_nav_Projects button {{
            width: var(--atlas-header-projects-width) !important;
            max-width: var(--atlas-header-projects-width) !important;
            min-width: var(--atlas-header-projects-width) !important;
        }}
        .st-key-atlas_header_nav_Knowledge button {{
            width: var(--atlas-header-knowledge-width) !important;
            max-width: var(--atlas-header-knowledge-width) !important;
            min-width: var(--atlas-header-knowledge-width) !important;
        }}
        .st-key-atlas_header_nav_Reports button {{
            width: var(--atlas-header-reports-width) !important;
            max-width: var(--atlas-header-reports-width) !important;
            min-width: var(--atlas-header-reports-width) !important;
        }}
        .st-key-atlas_header_nav_Settings button {{
            width: var(--atlas-header-settings-width) !important;
            max-width: var(--atlas-header-settings-width) !important;
            min-width: var(--atlas-header-settings-width) !important;
        }}
        [class*="st-key-atlas_global_search_input_"] input {{
            width: 100% !important;
            min-width: var(--atlas-header-search-min-width) !important;
            max-width: var(--atlas-header-search-max-width) !important;
        }}
        .stButton > button {{
            white-space: nowrap;
        }}
        @media (max-width: 1280px) {{
            .main .block-container {{
                width: min(calc(100% - 1.5rem), var(--atlas-max-content-width));
                padding-left: 0.75rem;
                padding-right: 0.75rem;
            }}
            .atlas-action-row,
            .atlas-toolbar,
            .atlas-responsive-control-group {{
                gap: var(--atlas-space-xs);
            }}
            [class*="st-key-atlas_global_search_input_"] input {{
                max-width: 12.5rem !important;
            }}
        }}
        @media (max-width: 960px) {{
            [class*="st-key-atlas_header_nav_"] button {{
                padding-left: 0.24rem !important;
                padding-right: 0.24rem !important;
            }}
            [class*="st-key-atlas_global_search_input_"] input {{
                max-width: 11rem !important;
            }}
            .atlas-content-section {{
                padding: var(--atlas-space-sm);
            }}
        }}
        @media (max-width: 840px) {{
            [class*="st-key-atlas_global_search_input_"] input {{
                max-width: 9.5rem !important;
            }}
        }}
        </style>
    """


def render_metric_card_html(title: str, value: str) -> str:
    return (
        "<div class='atlas-card'>"
        f"<div class='atlas-card-title'>{escape(title)}</div>"
        f"<div class='atlas-card-value'>{escape(value)}</div>"
        "</div>"
    )


def render_empty_state_html(message: str) -> str:
    return (
        "<div class='atlas-empty-state'>"
        "<div class='atlas-empty-title'>Nothing to show yet</div>"
        f"<p class='atlas-empty-copy'>{escape(message)}</p>"
        "</div>"
    )


def render_guided_empty_state_html(
    *,
    why_empty: str,
    action_to_populate: str,
    next_location: str,
) -> str:
    return (
        "<div class='atlas-empty-state'>"
        "<div class='atlas-empty-title'>No data available</div>"
        f"<p class='atlas-empty-copy'>{escape(why_empty)}</p>"
        f"<p class='atlas-empty-copy'><strong>Next action:</strong> {escape(action_to_populate)}</p>"
        f"<p class='atlas-empty-copy'><strong>Go to:</strong> {escape(next_location)}</p>"
        "</div>"
    )


def render_workspace_context_html(
    *,
    workspace: str,
    objective: str,
    current_focus: str,
) -> str:
    return (
        "<div class='atlas-workspace-context'>"
        f"<strong>{escape(workspace)}</strong>"
        f" · Objective: {escape(objective)}"
        f" · Focus: {escape(current_focus)}"
        "</div>"
    )


def render_notice_panel_html(title: str, body: str) -> str:
    return (
        "<div class='atlas-notice-panel'>"
        f"<strong>{escape(title)}</strong><br/>"
        f"{escape(body)}"
        "</div>"
    )


def render_status_badge_html(label: str, tone: str = "neutral") -> str:
    normalized = tone.strip().lower()
    allowed = {"success", "warning", "danger", "neutral"}
    if normalized not in allowed:
        normalized = "neutral"
    return (
        "<span class='atlas-status-badge "
        f"atlas-status-badge--{normalized}'>{escape(label)}</span>"
    )
