# Commercial Proposal and Sales Order Workflow

CM-04 adds the workflow layer that sits on top of customer, opportunity, and estimate management.

## Responsibilities

- Create proposals from existing estimates.
- Advance proposal state through draft, ready, sent, accepted, declined, expired, and cancelled.
- Convert an accepted estimate into a sales order.
- Keep sales orders tenant-scoped and stored in the local commercial repository.
- Copy estimate line items into sales orders deterministically.

## Explicit Non-Goals

- PDF generation or e-signature.
- Inventory allocation or reservation logic.
- Procurement execution.
- Customer invoicing or vendor billing.
- QuickBooks transport.
- Reporting and dashboards.

## Conversion Rules

- An estimate must already be linked to a proposal before conversion.
- The proposal must be accepted before conversion.
- Only one sales order may be created for a given estimate.
- Sales orders preserve the originating estimate, proposal, customer, organization, and line-item identity.

## Tenant Scope

The workflow service only sees records from the active tenant-scoped repository bundle. Cross-tenant access should return no record rather than leaking data.

## Related Docs

- [Commercial MVP operating spine](COMMERCIAL_MVP_OPERATING_SPINE.md)
- [Commercial repository](COMMERCIAL_REPOSITORY.md)
- [Customer, opportunity, and estimate service](COMMERCIAL_CUSTOMER_OPPORTUNITY_ESTIMATE_SERVICE.md)
