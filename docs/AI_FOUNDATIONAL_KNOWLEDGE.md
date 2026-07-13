# AI Foundational Knowledge

## Related Documents
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [AV_LIFECYCLE.md](AV_LIFECYCLE.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)
- [STANDARDS_LIBRARY.md](STANDARDS_LIBRARY.md)
- [MANUFACTURER_KNOWLEDGE.md](MANUFACTURER_KNOWLEDGE.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [USER_MANAGEMENT.md](USER_MANAGEMENT.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [SECURITY.md](SECURITY.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md)
- [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md)

## Purpose
Atlas AI should combine organization-provided project data with a curated foundation of publicly available, certification-based industry knowledge.

This document defines the knowledge boundaries, source hierarchy, versioning expectations, neutrality requirements, and human-authority limits for that future AI layer.

## Knowledge Model
Atlas AI should reason from two complementary sources:

- organization-provided context, including project documents and workspace records
- a curated foundation of publicly available, certification-based industry knowledge

The assistant must remain vendor-neutral and should not favor a manufacturer simply because that manufacturer has more available training content.

## Recognized Knowledge Domains
Priority knowledge domains may include publicly available material from recognized organizations such as:

- AVIXA
- BICSI
- Entertainment Services and Technology Association
- ETCP
- ANSI-accredited standards bodies
- NFPA
- IEEE
- AES
- SMPTE
- relevant electrical, accessibility, networking, and life-safety authorities

Priority manufacturer training ecosystems may include organizations such as:

- Extron
- Crestron
- QSC and Q-SYS
- ETC
- Shure
- Sennheiser
- Biamp
- Audinate
- Dante
- L-Acoustics
- Meyer Sound
- JBL Professional
- Harman Professional
- Yamaha Professional Audio
- Ross Video
- Blackmagic Design
- Panasonic Connect
- Sony Professional
- Epson
- Christie
- Barco
- Cisco
- Netgear AV
- Legrand AV
- Middle Atlantic
- Chief
- manufacturers with similarly mature professional training and technical documentation platforms

These references are illustrative and must not be treated as a permanent or exclusive vendor list.

## Certification-Based Knowledge Model
The future assistant should be designed around knowledge commonly taught in recognized industry certification programs.

Relevant knowledge areas may include:

- AVIXA CTS-level fundamentals
- AVIXA CTS-D design principles
- AVIXA CTS-I installation and implementation practices
- BICSI telecommunications distribution principles
- BICSI cabling, pathways, spaces, grounding, and bonding guidance
- ETCP entertainment electrical fundamentals
- ETCP rigging and entertainment technology safety principles
- manufacturer-certified system design practices
- manufacturer-certified programming concepts
- manufacturer-certified commissioning procedures
- manufacturer-certified troubleshooting practices
- networked AV architecture
- control system architecture
- lighting control architecture
- signal transport and distribution
- system documentation
- installation quality
- testing and verification
- service and maintenance

Atlas must distinguish between certification-informed knowledge and possession of an actual professional certification.

The assistant must never claim to be certified, licensed, factory-trained, or professionally credentialed.

## Public and Authorized Knowledge Boundary
Atlas should use only knowledge that it is legally and contractually permitted to process.

Approved foundational sources may include:

- publicly available standards summaries
- publicly available training material
- publicly available technical articles
- manufacturer installation manuals
- manufacturer design guides
- manufacturer application notes
- manufacturer product documentation
- public certification objectives
- public course descriptions
- public technical reference material
- organization-licensed content where Atlas has explicit permission
- customer-provided training resources where the customer has usage rights

Atlas must not ingest, reproduce, redistribute, or expose:

- copyrighted certification exam questions
- confidential exam-preparation material
- restricted course content
- proprietary training portals
- paid standards documents without appropriate licensing
- certification test banks
- confidential manufacturer materials
- content obtained through unauthorized scraping or access

Public availability should not be assumed merely because material is accessible online.

Future knowledge-ingestion architecture should support source licensing, usage restrictions, attribution, versioning, and retention rules.

## Knowledge Hierarchy
When answering a question, the assistant should generally prioritize:

1. Applicable laws, codes, and authority-having-jurisdiction requirements
2. Published standards and formally adopted requirements
3. Current manufacturer installation and product documentation
4. Organization-approved design standards and operating procedures
5. Project specifications, drawings, contracts, and approved submittals
6. Certification-based industry best practices
7. Historical project data
8. General industry guidance

Project requirements may supersede general best practices where they are valid, intentional, and compliant.

The assistant should identify conflicts rather than silently choosing one source.

## Knowledge Versioning
Industry standards, codes, certifications, products, firmware, and manufacturer guidance change over time.

The future AI knowledge layer should track, where available:

- source organization
- document title
- document type
- publication date
- revision number
- standard edition
- product model
- firmware version
- software version
- certification domain
- source URL or repository location
- licensing status
- date ingested
- date last verified
- superseded status

The assistant should avoid applying current guidance retroactively to historical projects without identifying that the guidance changed.

The assistant should also warn users when a source may be outdated or when a newer revision may exist.

## Manufacturer Knowledge
Manufacturer knowledge should be used to improve practical system guidance, particularly for:

- device compatibility
- supported topology
- cable limitations
- network requirements
- control integration
- power requirements
- thermal design
- licensing
- firmware dependencies
- redundancy
- commissioning
- troubleshooting
- service procedures
- product lifecycle status
- discontinued equipment
- approved accessories

Manufacturer documentation should take priority over generic assumptions for product-specific questions.

The assistant should not infer compatibility solely because products use similar connectors, protocols, or marketing terminology.

## Neutrality and Alternatives
Atlas should not operate as a manufacturer sales tool.

Where multiple valid solutions exist, the assistant should:

- explain the relevant technical criteria
- identify project constraints
- compare compatible approaches
- disclose when available evidence is manufacturer-specific
- distinguish required components from optional enhancements
- avoid presenting one brand as universally superior
- respect organization-approved manufacturer lists
- account for availability, supportability, lifecycle, and serviceability

Recommendations should be driven by project requirements and evidence rather than manufacturer prominence.

## AI Knowledge Administration
Future organization administration should support configurable knowledge policies.

Potential controls may include:

- approved manufacturers
- preferred manufacturers
- restricted manufacturers
- organization design standards
- approved product families
- preferred training sources
- standards editions in use
- regional code assumptions
- internal commissioning procedures
- internal naming conventions
- internal documentation standards
- source expiration policies
- administrator-approved knowledge libraries

An organization should be able to layer its own practices over the foundational Atlas knowledge base without changing the application's source code.

## AI Response Classification
Future AI responses should clearly distinguish among:

- code or regulatory requirement
- published standard
- manufacturer requirement
- project requirement
- organization standard
- certification-based best practice
- historical precedent
- assistant inference
- recommendation

This classification should be visible wherever the distinction materially affects risk, compliance, cost, or system performance.

## Human Authority
Atlas AI should support qualified professionals rather than replace them.

Final responsibility remains with the appropriate human stakeholders, which may include:

- licensed engineers
- certified designers
- certified technicians
- programmers
- project managers
- electrical contractors
- riggers
- safety professionals
- manufacturers
- consultants
- architects
- owners
- authorities having jurisdiction

High-risk recommendations involving electrical safety, structural loading, rigging, fire and life safety, accessibility, legal compliance, or regulated work should include an appropriate verification notice.