# Observability

## Purpose
This document defines future production observability for Atlas.

It covers logs, metrics, traces, alerts, health checks, dashboards, and incident support without claiming production observability is fully implemented today.

## Related Documents
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [SECURITY.md](SECURITY.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md)
- [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md)
- [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md)
- [SEARCH_ARCHITECTURE.md](SEARCH_ARCHITECTURE.md)
- [REPORTING.md](REPORTING.md)
- [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)
- [ERROR_LOGGING.md](ERROR_LOGGING.md)

## A-02 Controlled Alpha Baseline
Implemented in A-02 pt 2:
- tenant-scoped application error records with deterministic fingerprint grouping
- per-occurrence history retention for repeated failures
- sanitized message and stack-trace persistence (no raw secrets or filesystem paths)
- user-facing Error ID references for support triage
- administrator error-review workflow and sanitized diagnostics export
- alpha health-check integration with recent-error severity counts and unresolved totals

Current constraints:
- local deterministic persistence only
- no external telemetry or monitoring service integration in this sprint
- no production alert-routing claims

## Observability Goals
Atlas observability should help operators understand:
- application health
- tenant-scoped behavior
- security posture
- ingestion health
- integration health
- job processing health
- search performance
- AI retrieval and response behavior
- user-facing issues
- cost and resource usage

## Logging
Logging should include:
- application logs
- security logs
- audit logs
- job logs
- integration logs
- AI logs where appropriate

Logs should be:
- tenant-safe
- privacy-aware
- redacted where necessary
- consistent across services
- useful for support and incident response

## Metrics
Metrics should cover:
- request volume
- error rates
- latency
- queue depth
- ingestion throughput
- search latency
- graph traversal performance
- report generation duration
- AI retrieval latency
- AI cost signals
- background job success and failure rates

## Traces And Correlation
Distributed tracing should support:
- correlation IDs
- request IDs
- job IDs
- integration event IDs
- import batch IDs
- tenant-safe context propagation

Current P-03 baseline includes deterministic local correlation through project ID, job ID, and immutable audit event IDs persisted with each job record.

## Health Checks
Health checks should support:
- application readiness
- dependency reachability
- background worker health
- integration connectivity checks where appropriate
- storage and search availability

## Dashboards And Alerting
Dashboards should summarize:
- active incidents
- service health
- ingestion state
- integration failures
- search quality degradation
- job backlog
- AI retrieval anomalies
- cost hotspots

P-03 baseline dashboard candidates:
- job count by status (`queued`, `running`, `succeeded`, `failed`, `retry_scheduled`, `cancelled`)
- retry-scheduled count
- failed-job diagnostic code distribution
- average execution duration for representative import/export jobs

Alerting should support incident response without generating unnecessary noise.

## AI Monitoring
AI monitoring should distinguish:
- model latency
- retrieval latency
- retrieval freshness
- source conflicts
- prompt and response logging policy
- cost per request
- hallucination indicators where measurable

AI audit and retention signals should align with [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md).

## Production Versus Development Logging
Development logging may be more verbose.

Production logging should prioritize:
- redaction
- signal over noise
- tenant safety
- sensitive-data control
- operational usefulness

## Retention
Retention policies should be explicit for logs, metrics, traces, and audit data.

## Incident Response Support
Observability should support:
- diagnosis
- rollback decisions
- tenant impact analysis
- data-integrity investigation
- import and integration recovery

## Unresolved Decisions
- final telemetry stack remains open
- final retention windows remain policy-driven
- final alert routing remains open