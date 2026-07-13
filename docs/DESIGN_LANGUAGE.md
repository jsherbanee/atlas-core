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

Atlas is a commercial operations instrument, a decision-support system, and a precision tool.

Atlas is not a dashboard.
Atlas is not a marketing application.
Atlas is not a consumer app.

Atlas is not a generic business app.

Atlas should feel purpose-built for systems integrators that need calm, professional, information-dense, responsive, deterministic, and low-friction software.

Every visual element should exist because it improves engineering decision-making. Every pixel should justify its existence.

## 3. Engineering Philosophy

Atlas should behave like an operational control surface rather than a reporting dashboard.

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

Its broader purpose is to help an integration organization coordinate lifecycle work without visual or workflow friction.

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

Atlas draws inspiration from engineering, product-operations, and industrial design disciplines, not from racing aesthetics.

Relevant references include Autodesk Fusion, Linear, Notion, Arc Browser, Figma, Formula 1 telemetry dashboards, Leica industrial design, Apple Xcode, VS Code, Bluebeam, Revit, Bloomberg Terminal, and NASA mission control.

The influence to borrow is engineering discipline: clarity under pressure, dense but legible information, and interfaces that support critical decisions. Atlas should not copy the appearance of any of these systems.

## 7. Telemetry Mindset

Atlas is informed by the engineering culture behind motorsport telemetry, not by the visual appearance of telemetry software.

The relevant ideas are engineering discipline, data integrity, traceability, confidence, relationship analysis, performance optimization, decision support, and real-time awareness.

Atlas should take the mindset of careful instrumentation and rapid analysis while remaining a platform for commercial AV, theatrical, themed entertainment, and systems integration.

Atlas should also feel like software that can scale across the full lifecycle of an integration business without becoming visually noisy or generic.

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

## 8.1 Sprint A-05 and X-01 Workflow Hardening Posture

Completed hardening sprints (A-05 and X-01) apply usability validation to existing workflows and keep the same scope boundaries:

- no new engineering features
- no Commercial Intelligence, Sell Pricing, or Proposal Generation implementation
- no post-D-03 epic starts

Hardening priorities:

- recommendation clarity, prioritization, and direct navigation affordances
- table/form consistency and reduced click depth for common workflows
- explicit preview/apply/dismiss semantics where deterministic write actions are involved

Remaining non-blocking UX debt:

- table density and pagination consistency across high-volume workflows
- progressive disclosure opportunities in long evidence tables
- smaller-screen ergonomics for dense engineering review contexts

## 8.2 Sprint X-05 Navigation Consolidation Posture

X-05 continues product hardening with a top-header primary navigation model and preserves the same scope boundaries:

- no new product capabilities
- no Epic E implementation start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or proposal-generation workflows

X-05 focus is navigation clarity and terminology consistency:

- move primary navigation into the header rather than a left-column rail
- expose Administration publicly as Settings from an upper-right hamburger menu
- replace Home recent activity with a deterministic Recent Projects list

## 8.3 Sprint X-06 Responsive Shell Posture

X-06 continues product hardening without architecture expansion:

- no new product capabilities
- no Epic E implementation start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or proposal-generation workflows

X-06 focus is workstation-style responsiveness and shell simplification:

- Atlas is the sole Home action
- remove the public Home navigation tab from the shell
- simplify the global Search control to a label-free input with the Search placeholder
- expose Settings only as a dropdown option behind an icon-only menu trigger
- remove the History dropdown from the global shell
- keep Home content centered within a reasonable maximum width so it remains readable on large displays
- allow header and action areas to wrap cleanly on narrower desktop and split-screen widths

Remaining responsive UX debt:

- some dense project-workspace tables still depend on wider monitor space for optimal readability
- a few lower-priority review panels may still feel dense on very narrow split-screen layouts

## 8.4 Sprint X-08 Visual System and Search Clear-State Hardening

Completion status:

- X-06 responsive shell refinement: completed
- X-07 focused search refinement: completed
- X-08 initial visual-system pass and safe clear-search remediation: completed

X-08 completed product hardening without architecture expansion:

- no new product capabilities
- no Epic E implementation start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or proposal-generation workflows

X-08 focus is visual-system consistency and runtime-safe search-state handling:

- apply a calm workstation canvas with page background #FAFAF9
- standardize primary action emphasis with Atlas green #004225
- maintain neutral card/surface treatment and compact top navigation hierarchy
- preserve focused search-results presentation while a submitted query is active
- enforce safe search clear/reset behavior through separated widget-input and submitted-query state
- ensure Clear Search exits focused search mode without widget-state mutation exceptions

Remaining visual UX debt:

- some data-dense tables still need progressive disclosure refinement for smaller split-screen use
- additional width API alignment may continue across older or less frequently used UI surfaces

## 8.5 Sprint X-09 Design System Foundation and Reusable Components

Completion status:

- X-09 design-system foundation and reusable-components migration: completed and closed

X-09 continues product hardening without architecture expansion:

- no new product capabilities
- no Epic E implementation start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or proposal-generation workflows

X-09 focus is reusable UI authority and visual consistency hardening:

- establish a shared token authority for color, spacing, radius, typography, layout widths, and control heights
- centralize shell/page CSS into a single reusable design-system source
- define reusable UI primitives for section headings, notice panels, status badges, metric cards, tables, and responsive control groups
- migrate representative pages (Home, Projects, Knowledge, and Reports) onto shared primitives without changing product behavior

Post-X-09 migration debt:

- project-workspace pages outside Home/Projects/Knowledge/Reports still contain legacy inline layout and table wrappers (for example Documents, BOM Review, Scope & Risk, Engineering Review, Estimate, Notebook, and object-detail pages)
- table hierarchy and responsive-control wrappers should continue to expand through future hardening sprints

## 8.6 Sprint X-10 Workspace Consistency and Information Density

Completion status:

- X-10 project-workspace consistency migration: completed and closed

X-10 continues product hardening without architecture expansion:

- no new product capabilities
- no Epic E implementation start
- no new estimating, commercial intelligence, procurement, execution, accounting, ERP, or proposal-generation workflows

X-10 focus is consistency completion across remaining primary project workspaces:

- migrate Overview, Documents, BOM Review, Scope & Risk, Engineering Review, Estimate, and Notebook onto shared section-title, notice-panel, table, and responsive-control wrappers
- preserve deterministic behavior, routing, and project-state contracts while increasing visual hierarchy and information density consistency
- standardize empty-state and action-zone presentation across migrated workspaces

Remaining UX debt after X-10:

- some advanced and object-detail pages still use older inline layout/table rendering patterns and should migrate in future hardening passes
- notebook discoverability still depends on project navigation patterns and can benefit from additional direct-entry affordances from core workflow pages


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
- Primary navigation and normal primary actions use Atlas primary accent #004225.
- Green indicates healthy or complete states.
- Amber indicates needs review or cautionary states.
- Gray indicates unknown, inactive, or unavailable states.

Color should support confidence and orientation. It should never compete with the information itself.

## 10. Typography Philosophy

Typography should be readable, operations-focused, professional, and timeless.

It should favor legibility in dense working environments and support long sessions without fatigue. Likely inspirations include DIN, Inter, and IBM Plex Sans, but this document does not lock implementation fonts.

Typography should establish hierarchy through weight, spacing, and scale rather than novelty.

## 11. Layout Philosophy

Layout should be intentional and predictable.

Whitespace is not empty space. It is a control mechanism that improves comprehension.

Atlas should favor hierarchy over decoration, predictable navigation, logically grouped information, and interfaces that remain readable at professional density.

Cards should be used only when they improve comprehension. Tables should remain readable and primary where structured comparison matters. The layout should support professionals who may spend hours inside Atlas.

## 12. Navigation Philosophy

Atlas is lifecycle-centric, not document-centric and not estimate-centric.

Atlas navigation uses two explicit workspace layers:
- Application Workspace for Home, project management, portfolio reporting, and administration.
- Project Workspace for project-specific review and decision pages after a project is opened.

Home remains the public application-level landing page even when a project is active.
Mission Control remains an internal compatibility route name only.

Navigation should always help answer four questions:

- Where am I?
- What project am I in?
- What object am I viewing?
- What should I do next?

Object navigation should feel model-first rather than page-first.
Core object types (equipment, drawings, specifications, systems, rooms, risks, RFIs, and evidence) should expose a consistent object identity pattern and deterministic cross-object movement from any workspace where they appear.

Global object discovery should be persistent and immediate.
Search should remain available in the header across application and project workspaces so users can move directly to objects without page-by-page navigation.
Header search executes directly on Enter and avoids separate open/close interaction modes.

Navigation should be persistent, require minimal clicks, and maintain a predictable hierarchy. The interface should feel like a workspace, not a maze.

The interface should also feel configurable, tenant-aware, and consistent across organizations.

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