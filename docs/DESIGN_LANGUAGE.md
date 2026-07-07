# Atlas Design Language

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

## 3. Brand Personality

Atlas should feel calm, confident, precise, methodical, professional, trustworthy, purposeful, restrained, and intelligent.

Atlas should avoid flashiness, visual clutter, gaming aesthetics, science fiction styling, cyberpunk cues, gratuitous animation, and anything that makes the interface feel performative rather than dependable.

## 4. Emotional Goals

Atlas should create confidence, not excitement.

Users should feel:

- "I trust this system."
- "This software understands engineering."
- "I know where to look."
- "I can make decisions confidently."

Atlas should reduce uncertainty, help users orient quickly, and make engineering judgment feel supported rather than burdened.

## 5. Visual Inspiration

Atlas draws inspiration from engineering and industrial design disciplines, not from racing aesthetics.

Relevant references include British Racing engineering, the Aston Martin Formula One engineering environment, McLaren race engineering, Porsche Motorsport telemetry, Leica industrial design, Apple Xcode, VS Code, Bluebeam, Revit, Bloomberg Terminal, and NASA mission control.

The influence to borrow is engineering discipline: clarity under pressure, dense but legible information, and interfaces that support critical decisions. Atlas should not copy the appearance of any of these systems.

## 6. Things Atlas Will Never Become

Atlas will never become a gaming UI, a cyberpunk interface, a sci-fi control panel, a glowing HUD, or a fake telemetry display.

Atlas should avoid decorative gauges, neon accents, overuse of gradients, animated backgrounds, information overload, and any design that favors appearance over function.

## 7. Color Philosophy

Atlas colors should communicate structure and state, not decoration.

The conceptual palette is grounded in British Racing Green, graphite, charcoal, warm white, brushed aluminum, and muted brass.

Status colors should be reserved for state communication only:

- Healthy: steady and reassuring
- Information: neutral and informative
- Needs Review: attentive without alarm
- Critical: urgent and unmistakable
- Unknown: deliberately subdued and unresolved

Color should support confidence and orientation. It should never compete with the information itself.

## 8. Typography Philosophy

Typography should be readable, engineering-focused, professional, and timeless.

It should favor legibility in dense working environments and support long sessions without fatigue. Likely inspirations include DIN, Inter, and IBM Plex Sans, but this document does not lock implementation fonts.

Typography should establish hierarchy through weight, spacing, and scale rather than novelty.

## 9. Layout Philosophy

Layout should be intentional and predictable.

Whitespace is not empty space. It is a control mechanism that improves comprehension.

Atlas should favor hierarchy over decoration, predictable navigation, logically grouped information, and interfaces that remain readable at professional density.

Cards should be used only when they improve comprehension. Tables should remain readable and primary where structured comparison matters. The layout should support professionals who may spend hours inside Atlas.

## 10. Navigation Philosophy

Atlas is project-centric, not document-centric and not estimate-centric.

Navigation should always help answer four questions:

- Where am I?
- What project am I in?
- What object am I viewing?
- What should I do next?

Navigation should be persistent, require minimal clicks, and maintain a predictable hierarchy. The interface should feel like a workspace, not a maze.

## 11. Data Visualization

Charts should exist only when they improve engineering understanding.

Prefer tables, relationship graphs, confidence indicators, status chips, timelines, and system summaries.

Avoid decorative charts or visualizations that look impressive but do not help the user make a decision.

## 12. Motion Philosophy

Motion should communicate state.

Useful motion includes panel expansion, selection feedback, relationship highlighting, and progress indication.

Avoid animations for entertainment, large transitions, and motion that slows engineering work.

## 13. Iconography

Iconography should be simple, technical, and consistent.

Use thin line icons and avoid novelty symbols, playful illustration, or icons that imply consumer software behavior.

## 14. Component Philosophy

Atlas components should be optimized for engineering clarity.

- Cards should summarize, not distract.
- Tables should support comparison and traceability.
- Object panels should show identity, evidence, relationships, and confidence.
- Relationship badges should explain why objects are connected.
- Evidence chips should make traceability visible at a glance.
- Status indicators should be explicit and color-independent where possible.
- Navigation should remain persistent and predictable.
- Search should help users move from object discovery to decision context.
- The context panel should expose canonical values, supporting evidence, and uncertainty.

## 15. Themes

Atlas supports two long-term visual themes.

Workshop Theme: bright, clean, and suited to daily engineering work.

Control Room Theme: dark, quiet, and suited to high-focus environments.

Both themes must share the same layout, hierarchy, navigation behavior, and interaction logic. Themes are visual only.

## 16. Accessibility

Atlas should support high contrast, keyboard navigation, screen reader compatibility, scalable typography, and color-independent status communication.

Accessibility is not an add-on. It is part of engineering clarity.

## 17. Future Visual Evolution

Future features should feel like they have always belonged in Atlas.

New surfaces should preserve the same design grammar, hierarchy, and interaction logic. Avoid isolated visual styles, novelty treatments, or feature-specific experiments that break coherence.

Consistency should outrank novelty.

## 18. Design Principles

Atlas should follow these permanent design principles:

- Design for engineers.
- Show relationships before metrics.
- Prioritize decisions over dashboards.
- Information should become quieter as confidence increases.
- Color communicates state, never decoration.
- Respect the user's attention.
- Everything should feel intentional.

## 19. Relationship to the Domain Model

[DOMAIN_MODEL.md](DOMAIN_MODEL.md) defines Atlas's business architecture: the entities, lifecycle transitions, and module boundaries that make the platform durable.

This document defines Atlas's human interface: how that architecture is experienced visually and cognitively.

Together, [DOMAIN_MODEL.md](DOMAIN_MODEL.md) and this document form the long-term blueprint for Atlas.