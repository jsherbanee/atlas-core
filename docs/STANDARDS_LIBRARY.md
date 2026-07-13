# Standards Library

## Purpose
This document defines the governance and architecture for standards-oriented knowledge in Atlas.

It should be read together with [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md).

## Related Documents
- [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)
- [PRODUCT_VISION.md](PRODUCT_VISION.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [SECURITY.md](SECURITY.md)
- [MANUFACTURER_KNOWLEDGE.md](MANUFACTURER_KNOWLEDGE.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)

## Scope
The standards library should manage standards-oriented knowledge as a governed source layer rather than as free-form text.

Illustrative categories include:
- AVIXA
- BICSI
- ETCP
- ANSI
- NFPA
- NEC
- UL
- IEEE
- AES
- SMPTE
- accessibility
- networking
- lighting
- electrical
- life safety

## Standards Metadata
Each standards entry should support metadata such as:
- organization
- title
- edition
- effective date
- jurisdiction
- licensing
- access restrictions
- summary vs full text
- superseded edition links
- source verification
- citations
- regional applicability
- organization-approved editions

## Access And Licensing
The standards library should distinguish:
- summary content
- user-uploaded licensed standards
- allowed citations and references
- prohibited redistribution
- access-restricted source material

Atlas should not redistribute copyrighted standards content outside the permissions available to the organization.

## AI Usage
AI may use standards metadata, summaries, and approved source references to answer questions or explain context.

AI should not expose restricted text or imply permission beyond the approved license scope.

## Deterministic Rule Usage
Deterministic rule engines may reference standards metadata and approved edition information when evaluating checks, reminders, or project rules.

## Versioning And Supersession
The standards library should preserve:
- current edition
- superseded editions
- verification status
- review date
- confidence in applicability

## Human Verification
High-risk or regulated decisions should still require human verification, especially where local jurisdiction, authority-having-jurisdiction requirements, or project-specific requirements apply.

## Unresolved Decisions
- final storage format for standards references remains open
- final citation format remains open
- final update-review workflow remains open