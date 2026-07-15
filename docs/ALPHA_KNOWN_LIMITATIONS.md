# Alpha Known Limitations

## Purpose
Provide explicit transparency for known alpha constraints that are non-blocking for controlled alpha usage.

## Ready With Known Limitations
- Background jobs are local deterministic only; no cloud queue/worker runtime is active.
- Attachment security does not yet include malware scanning/quarantine engine integration.
- Tenant manager provisioning is local sandbox path provisioning only (no hosted infrastructure automation).
- Navigation/manual viewport validation evidence is contract- and regression-led in this release candidate; broader exploratory UX sweeps continue in follow-through hardening.

## Deferred Beyond Alpha (Intentional)
- SSO/Cognito/invitation lifecycle and production IAM controls.
- Billing/subscription and self-service tenant onboarding.
- Live QuickBooks transport execution and reconciliation workers.
- Inventory/procurement workflow activation.
- Cloud deployment hardening milestones (distributed workers, production observability topology, platform secrets ops).

## Risk Notes
- Current alpha recommendation assumes controlled operator usage and platform-admin-managed sandbox boundaries.
- Multi-tenant boundary hardening is enforced in audited paths, but enterprise-scale cloud controls remain roadmap work.

## Tracking
- Primary readiness source: `ALPHA_READINESS.md`
- Validation evidence: `ALPHA_TEST_PLAN.md`
- Operator procedures: `ALPHA_SANDBOX_GUIDE.md`
