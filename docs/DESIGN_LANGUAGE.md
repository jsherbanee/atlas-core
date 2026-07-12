# Atlas Design Language

## Related Documents
- [README.md](README.md)
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)

## 1. Purpose

This document defines Atlas's visual identity and UX philosophy.

It is the visual counterpart to [DOMAIN_MODEL.md](DOMAIN_MODEL.md). The domain model defines how Atlas thinks. The design language defines how Atlas feels.

The goal of this document is not to prescribe implementation details, CSS values, or component styling. It establishes the long-term design posture that future interfaces must follow so Atlas remains coherent as the platform grows.

## 2. Design Philosophy

Atlas is an engineering instrument, a decision-support system, and a precision tool.

Atlas is not a dashboard.
Atlas is not a marketing application.
Atlas is not a consumer app.

Every visual element should exist because it improves engineering decision-making. Every pixel should justify its existence.

## 3. Engineering Philosophy

Atlas should behave like an engineering instrument rather than a reporting dashboard.

The role of Atlas is to:

- collect engineering information
- normalize engineering information
- preserve traceability
- identify conflicts
- expose relationships
- increase engineering confidence
- support human decision-making

Atlas should never attempt to replace engineering judgment.

Its purpose is to help engineers make better decisions more quickly.

## 4. Brand Personality

Atlas should feel calm, confident, precise, methodical, professional, trustworthy, purposeful, restrained, and intelligent.

Atlas should avoid flashiness, visual clutter, gaming aesthetics, science fiction styling, cyberpunk cues, gratuitous animation, and anything that makes the interface feel performative rather than dependable.

## 5. Emotional Goals

Atlas should create confidence, not excitement.

Users should feel:

- "I trust this system."
- "This software understands engineering."
- "I know where to look."
- "I can make decisions confidently."

Atlas should reduce uncertainty, help users orient quickly, and make engineering judgment feel supported rather than burdened.

## 6. Visual Inspiration

Atlas draws inspiration from engineering and industrial design disciplines, not from racing aesthetics.

Relevant references include British Racing engineering, the Aston Martin Formula One engineering environment, McLaren race engineering, Porsche Motorsport telemetry, Leica industrial design, Apple Xcode, VS Code, Bluebeam, Revit, Bloomberg Terminal, and NASA mission control.

The influence to borrow is engineering discipline: clarity under pressure, dense but legible information, and interfaces that support critical decisions. Atlas should not copy the appearance of any of these systems.

## 7. Telemetry Mindset

Atlas is informed by the engineering culture behind motorsport telemetry, not by the visual appearance of telemetry software.

The relevant ideas are engineering discipline, data integrity, traceability, confidence, relationship analysis, performance optimization, decision support, and real-time awareness.

Atlas should take the mindset of careful instrumentation and rapid analysis while remaining a platform for commercial AV, theatrical, themed entertainment, and systems integration.

Atlas should not reference or imitate specific telemetry products, software interfaces, logos, branding, or proprietary implementations.

## 8. Sprint A-04 UX Consolidation

Sprint A-04 establishes workstation-level consistency rules across Mission Control and Project Workspace pages:

- use a shared workspace section header pattern that states objective and current focus
- normalize terminology around Products (Master Library) and deterministic cost language
- group and deduplicate recommendation surfaces before rendering action tables
- keep navigation object-centric with explicit open-object actions from estimate snapshot views
- provide consistent clear-filter controls in dense review tables

Scope boundary for A-04:

- UX and consistency consolidation only
- no new D-03 capabilities and no procurement/accounting/ERP workflow expansion


## 8. Things Atlas Will Never Become

Atlas will never become a gaming UI, a cyberpunk interface, a sci-fi control panel, a glowing HUD, or a fake telemetry display.

Atlas should avoid decorative gauges, neon accents, overuse of gradients, animated backgrounds, information overload, and any design that favors appearance over function.

## 9. Color Philosophy

Atlas colors should communicate structure and state, not decoration.

The conceptual palette is grounded in British Racing Green, graphite, charcoal, warm white, brushed aluminum, and muted brass.

Status colors should be reserved for state communication only:

- Healthy: steady and reassuring
- Information: neutral and informative
- Needs Review: attentive without alarm
- Critical: urgent and unmistakable
- Unknown: deliberately subdued and unresolved

Color assignment rules for interface actions:
- Red is reserved for critical findings, blocking issues, failed operations, and destructive actions only.
- Primary navigation and normal primary actions use the Atlas primary accent (blue family).
- Green indicates healthy or complete states.
- Amber indicates needs review or cautionary states.
- Gray indicates unknown, inactive, or unavailable states.

Color should support confidence and orientation. It should never compete with the information itself.

## 10. Typography Philosophy

Typography should be readable, engineering-focused, professional, and timeless.

It should favor legibility in dense working environments and support long sessions without fatigue. Likely inspirations include DIN, Inter, and IBM Plex Sans, but this document does not lock implementation fonts.

Typography should establish hierarchy through weight, spacing, and scale rather than novelty.

## 11. Layout Philosophy

Layout should be intentional and predictable.

Whitespace is not empty space. It is a control mechanism that improves comprehension.

Atlas should favor hierarchy over decoration, predictable navigation, logically grouped information, and interfaces that remain readable at professional density.

Cards should be used only when they improve comprehension. Tables should remain readable and primary where structured comparison matters. The layout should support professionals who may spend hours inside Atlas.

## 12. Navigation Philosophy

Atlas is project-centric, not document-centric and not estimate-centric.

Atlas navigation uses two explicit workspace layers:
- Application Workspace for Mission Control, project management, portfolio reporting, and administration.
- Project Workspace for project-specific review and decision pages after a project is opened.

Mission Control remains application-level even when a project is active.

Navigation should always help answer four questions:

- Where am I?
- What project am I in?
- What object am I viewing?
- What should I do next?

Object navigation should feel model-first rather than page-first.
Core object types (equipment, drawings, specifications, systems, rooms, risks, RFIs, and evidence) should expose a consistent object identity pattern and deterministic cross-object movement from any workspace where they appear.

Global object discovery should be persistent and immediate.
Search should remain available in the header across application and project workspaces so users can move directly to objects without page-by-page navigation.

Navigation should be persistent, require minimal clicks, and maintain a predictable hierarchy. The interface should feel like a workspace, not a maze.

Project Workspace pages should follow an action-first hierarchy:
- Recommended next action
- Primary actions
- Critical issues and blockers
- Summary metrics
- Drill-down evidence

Object detail hierarchy should follow:
- object identity and confidence context
- references and referenced-by relationships
- evidence and warnings
- recommended next navigation or review action

Project Workspace review should also provide a visible, non-blocking guided sequence (Documents, BOM, Scope and Risk, Engineering Findings, Estimate Coverage, Summary Report) so users always know progress without being forced through a wizard.

Guided steps should use explicit statuses: not started, ready, needs review, blocked, complete.

Recommended next action should target the next incomplete review step, explain why it matters, and provide direct navigation.

Desktop Project Workspace should use a consistent two-column layout:
- left navigation
- main working content

Object/evidence detail should be shown inline in the main content through tabs, expanders, drawers, slide-over patterns, or modal detail surfaces.

Do not reserve a persistent third column for context.

Breadcrumbs should remain concise and non-repetitive.

Preferred patterns:
- Atlas / Projects
- Atlas / Knowledge
- Atlas / Projects / <Project Name> / <Page>

Breadcrumbs should avoid internal route names, duplicate workspace labels, and implementation terminology.

## 13. Data Visualization

Charts should exist only when they improve engineering understanding.

Prefer tables, relationship graphs, confidence indicators, status chips, timelines, and system summaries.

Avoid decorative charts or visualizations that look impressive but do not help the user make a decision.

## 14. Motion Philosophy

Motion should communicate state.

Useful motion includes panel expansion, selection feedback, relationship highlighting, and progress indication.

Avoid animations for entertainment, large transitions, and motion that slows engineering work.

## 15. Iconography

Iconography should be simple, technical, and consistent.

Use thin line icons and avoid novelty symbols, playful illustration, or icons that imply consumer software behavior.

## 16. Component Philosophy

Atlas components should be optimized for engineering clarity.

- Cards should summarize, not distract.
- Tables should support comparison and traceability.
- Object panels should show identity, evidence, relationships, and confidence.
- Relationship badges should explain why objects are connected.
- Evidence chips should make traceability visible at a glance.
- Status indicators should be explicit and color-independent where possible.
- Navigation should remain persistent and predictable.
- Search should help users move from object discovery to decision context.
- Search should support object-type grouping, recent context recall, and fast object handoff into related workspaces.
- Search results should show enough context to reduce ambiguity: display name, object type, secondary label, project context, status, confidence, and warnings where applicable.
- Search empty states should explain what was searched and provide a clear next action.
- Contextual object detail should expose canonical values, supporting evidence, and uncertainty through inline or on-demand detail surfaces.
- Working Set should remain compact and purposeful: a small, persistent set of active review objects, not a permanent third-column panel.
- Object workspaces should use one primary object detail view and avoid repeating the same properties across multiple simultaneous tables/panels.
- Empty states should explain why data is empty, how to populate it, and what the next step is.
- Detailed diagnostics should be discoverable through drill-down, not forced into the default page view.
- Checklist-driven review summaries should make completion state understandable at a glance.
- Internal summary reports should default to concise decision support and expose long evidence/detail through expansion, not by default verbosity.

## 17. Themes

Atlas supports two long-term visual themes.

Workshop Theme: bright, clean, and suited to daily engineering work.

Control Room Theme: dark, quiet, and suited to high-focus environments.

Both themes must share the same layout, hierarchy, navigation behavior, and interaction logic. Themes are visual only.

## 18. Accessibility

Atlas should support high contrast, keyboard navigation, screen reader compatibility, scalable typography, and color-independent status communication.

Accessibility is not an add-on. It is part of engineering clarity.

## 19. Engineering Confidence

Atlas should be designed so future architectural concepts can express engineering trust without collapsing into a single readiness score.

One future concept is the Engineering Confidence Index (ECI), an aggregate engineering confidence metric.

ECI is conceptually different from Readiness.

Readiness asks: "Can this project be estimated?"

Engineering Confidence asks: "How complete, consistent, and trustworthy is the engineering model?"

Potential future contributors to ECI include resolver confidence, Knowledge Graph completeness, drawing/specification consistency, evidence quality, RFI exposure, revision stability, labor confidence, and relationship integrity.

ECI is a documented future direction only. It is not implemented here.

## 20. Future Visual Evolution

Future features should feel like they have always belonged in Atlas.

New surfaces should preserve the same design grammar, hierarchy, and interaction logic. Avoid isolated visual styles, novelty treatments, or feature-specific experiments that break coherence.

Consistency should outrank novelty.

## 21. Design Principles

Atlas should follow these permanent design principles:

- Design for engineers.
- Atlas should always recommend the next engineering action.
- Atlas highlights decisions rather than displaying data.
- Atlas reduces engineering uncertainty.
- Relationships are more valuable than isolated metrics.
- Information should become quieter as confidence increases.
- Confidence should always be explainable.
- Every recommendation must be traceable.
- Engineers remain the final decision makers.
- Show relationships before metrics.
- Prioritize decisions over dashboards.
- Color communicates state, never decoration.
- Respect the user's attention.
- Everything should feel intentional.

## 22. Relationship to the Domain Model

[DOMAIN_MODEL.md](DOMAIN_MODEL.md) defines Atlas's business architecture: the entities, lifecycle transitions, and module boundaries that make the platform durable.

This document defines Atlas's human interface: how that architecture is experienced visually and cognitively.

Together, [DOMAIN_MODEL.md](DOMAIN_MODEL.md) and this document form the long-term blueprint for Atlas.