# Settings Architecture

This document defines the reusable Settings workspace foundation and scope boundaries introduced in Sprint T-04 and extended in Sprint P-01.

Sprint P-05 extends Settings with deterministic document-template management for commercial document generation.

Sprint S-01 extends Settings to complete the alpha baseline for organization controls and integration metadata governance.

Sprint C-03 extends Settings with organization-scoped commercial defaults used by catalog pricing/tax behaviors.

## Purpose

Provide a deterministic, tenant-aware settings surface for organization controls and user preferences while preserving existing runtime and numbering guarantees.

## Scope (T-04)

Active sections:
- Organization Settings
- Personal Preferences

Visible but future-scoped sections:
- Billing
- Advanced

Out of scope:
- identity and auth provider implementation
- billing-provider integrations
- external accounting sync configuration

P-01 extension:
- deterministic roles and permissions administration foundation is now active under Organization Settings
- tenant-scoped role assignment and effective-access evaluation are now supported
- project-scoped access overrides are now supported

P-05 extension:
- tenant-scoped document templates with version lineage and scoped assignment (transaction, project, customer, tenant default)
- explicit default-template assignment for tenant-level templates
- precedence-aware template resolution and runtime export/replace synchronization

S-01 extension:
- organization profile management (identity, contact, locale, branding reference, tax ID secret reference)
- taxes and surcharges deterministic rule engine with decimal-safe preview
- integrations metadata hooks with secret-reference-only credential pointers
- security policy metadata controls for MFA/session/policy references
- terms document family expansion to Return Orders and Customer Invoices
- document template duplication and preview controls

C-03 extension:
- organization commercial defaults (`default_pricing_policy`, `default_markup_percent`, `default_margin_percent`, `default_tax_nexus`, `currency`, `rounding_policy`)
- deterministic validation for commercial default policy values and rounding/currency constraints

## Navigation Contract

Settings uses the shared secondary/tertiary contract architecture.

Primary routing behavior:
- public workspace label is `Settings`
- compatibility route key remains `Administration`

Secondary sections:
- `organization_settings`
- `personal_preferences`
- `integrations`
- `security`
- `billing`
- `advanced`

Organization tertiary actions:
- `overview`
- `organization_profile`
- `commercial_numbering`
- `taxes_surcharges`
- `terms_and_conditions`
- `document_templates`
- `roles_permissions`
- `audit`

Personal tertiary actions:
- `profile`
- `display`

Integrations tertiary actions:
- `connections`

Security tertiary actions:
- `policy`

## Tenant and User Scope Model

Settings state is modeled in two explicit scope layers:

- Organization settings
  - scoped by tenant and organization
  - authoritative for tenant-governed controls
  - includes commercial document numbering policies
  - includes organization profile, tax/surcharge rules, integration connection metadata, and security policy metadata
  - includes organization commercial defaults consumed by catalog line pricing/tax flows

- Personal preferences
  - scoped by tenant, organization, and user
  - user-adjustable defaults for workspace ergonomics
  - must not override tenant-governed controls

## Commercial Numbering Preferences

Numbering policy configuration is managed per commercial document family.

Supported template tokens:
- `{PREFIX}`
- `{TYPE}`
- `{YEAR}`
- `{MONTH}`
- `{PROJECT_CODE}`
- `{SEQUENCE}`
- `{SUFFIX}`

Policy controls:
- syntax template
- prefix
- suffix
- separator
- sequence padding
- starting sequence
- reset policy (`never`, `year`, `month`)

Deterministic behavior requirements preserved:
- preview operations are non-consuming
- allocation consumes sequence only through the existing numbering service
- no number reuse
- no mutation of already allocated numbers after policy edits
- tenant isolation remains enforced

Validation rules:
- templates must include `{SEQUENCE}`
- token usage must align to enabled policy flags
- duplicate family signatures that could collide are rejected

## Personal Preferences Model

Initial preference fields:
- landing workspace
- interface density
- table page size
- date format
- timezone
- reduced motion

Boundary rules:
- preferences are user-scoped defaults
- preferences cannot override organization numbering controls
- preferences cannot override tenant security/billing/integration governance

## State Persistence

Settings state participates in workspace snapshot and restore so navigation and settings continuity are preserved across app state transitions.

Persisted areas:
- settings workspace navigation state
- organization numbering policies
- organization terms and conditions blocks
- organization tax and surcharge rules
- organization integration connection metadata (secret references only)
- organization security policy metadata
- personal preference values
- settings audit events

## Service Layer

`SettingsService` is the authority for:
- organization numbering policy list/update/replace/export
- organization terms and conditions block create/edit/version/assign-default/archive/restore/resolve/export
- organization profile read/update
- organization commercial defaults read/update
- tax and surcharge rule create/list/update/preview
- integration connection list/upsert with secret-reference validation
- security policy read/update
- numbering previews
- personal preference defaults and updates
- settings audit event recording

`PermissionsService` is the authority for:
- system role catalog and permission catalog
- tenant policy state and deterministic serialization
- role assignment and revocation
- project-level allow/deny overrides
- permission and action evaluation with deny-by-default behavior
- permission change event recording

Transactions integration:
- transactions workspace service is initialized from serialized numbering policies supplied by settings
- numbering policy updates that occur during transaction operations are synchronized back into settings state
- Return Orders and Credit Memos consume the same tenant-scoped numbering policy infrastructure as other commercial documents
- Customer Invoices consume the same tenant-scoped numbering policy infrastructure and retain non-reuse guarantees for issued invoice numbering

## Testing Expectations

T-04 validation includes:
- numbering preview non-consumption behavior
- allocation/no-reuse behavior continuity
- policy serialization and restoration
- tenant/user isolation boundaries
- personal preference restriction enforcement
- settings navigation contract and state-default behavior

## Terms and Conditions Settings (T-05 Amendment)

Tenant-scoped Terms and Conditions content blocks are now supported for:
- `estimate`
- `sales_order`
- `return_order`
- `customer_invoice`

Block fields:
- title
- document family
- status (`draft` or `active`)
- content (safe formatted text)
- version
- effective date
- expiration date
- default flag
- optional customer override scope
- optional project override scope
- optional transaction override scope
- created/updated audit fields
- archived state

Behavior:
- one active tenant-level default block is enforced per document family
- overrides are explicit and scope-aware (transaction > project > customer > tenant default)
- settings updates do not silently replace document snapshots
- issued documents retain captured terms snapshots immutably
- draft documents refresh terms only via explicit user action

T-05 revision/export interaction:
- revisions preserve terms reference fields (block ID/version/source) and content snapshot history
- later settings edits do not mutate historical revision terms content
- document export and future email metadata are transaction-level controls, not settings-side transport behavior

## Roles and Permissions Foundation (P-01)

Settings now includes Organization -> Roles and Permissions with:

- system-role visibility
- permissions-by-role visibility
- tenant-scoped role assignment controls
- placeholder-member assignment support for local development while user administration remains in progress
- effective-access preview with reasoned allow or deny decisions
- project-level override controls and audit logging

Scope boundaries remain:

- no authentication implementation
- no invitation workflow
- no SSO or cloud identity provider integration
