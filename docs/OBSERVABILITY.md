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