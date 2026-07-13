# AWS Architecture

## Purpose
This document defines the long-term AWS hosting, deployment, workload, and migration architecture for Atlas.

Atlas cannot be hosted exclusively by Amazon S3.

S3 is an object-storage component inside a broader application architecture.

This document is architectural direction only.

## Related Documents
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md)
- [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md)
- [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md)
- [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md)
- [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md)
- [TRUST_CHARTER.md](TRUST_CHARTER.md)
- [SECURITY.md](SECURITY.md)
- [OBSERVABILITY.md](OBSERVABILITY.md)
- [BACKUP_RECOVERY.md](BACKUP_RECOVERY.md)
- [PERFORMANCE.md](PERFORMANCE.md)
- [INTEGRATIONS.md](INTEGRATIONS.md)
- [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md)
- [AI_ASSISTANT.md](AI_ASSISTANT.md)

## Architectural Principles
- multi-tenant isolation
- least privilege
- private-by-default storage
- encryption in transit and at rest
- adapter-driven migration
- environment isolation
- deterministic processing
- idempotent background jobs
- auditable operations
- reproducible deployments
- infrastructure as code
- cost awareness
- service replaceability where practical
- no public production data buckets
- no secrets in source control
- controlled network boundaries

Customer-owned data handling and AI privacy commitments should align with [PRIVACY_AND_DATA_OWNERSHIP.md](PRIVACY_AND_DATA_OWNERSHIP.md) and [AI_PRIVACY_POLICY.md](AI_PRIVACY_POLICY.md).

The overarching trust commitments that frame deployment choices are defined in [TRUST_CHARTER.md](TRUST_CHARTER.md).

## Conceptual Workload Layers

### Edge and Delivery
Potential services:

- Route 53
- CloudFront
- AWS WAF
- certificate management

### Application Delivery
Potential options:

- ECS with Fargate
- Lambda
- EC2 where justified
- future container orchestration alternatives

Workload selection should consider:

- request shape
- background-job mix
- operational complexity
- deployment repeatability
- scaling behavior
- cost
- isolation requirements

### APIs
Potential services:

- API Gateway
- load balancers
- private service endpoints

### Relational Persistence
Potential services:

- Amazon RDS
- Amazon Aurora

Relational persistence requirements include:

- tenant keys
- transactional integrity
- backups
- migration control
- encryption
- read scaling
- connection management

### Object Storage
Amazon S3 should be used for:

- uploaded project documents
- drawings
- specifications
- exports
- reports
- portable bundles
- immutable commercial source files
- future AI-ingestion artifacts

S3 requirements include:

- private buckets
- tenant-aware keys
- object versioning
- checksums
- retention
- lifecycle policies
- temporary upload handling
- malware scanning integration point
- signed access
- audit logs

### Identity
Potential direction:

- Amazon Cognito

The final identity-provider choice remains open.

### Asynchronous Processing
Potential services:

- SQS
- EventBridge
- Step Functions where justified
- Lambda or container workers

Potential workloads:

- document ingestion
- OCR
- indexing
- report generation
- commercial imports
- integration synchronization
- AI preprocessing
- notification delivery

### Secrets and Encryption
Potential services:

- Secrets Manager
- KMS

### Monitoring
See [OBSERVABILITY.md](OBSERVABILITY.md).

Potential service:

- CloudWatch

### Backup and Recovery
See [BACKUP_RECOVERY.md](BACKUP_RECOVERY.md).

Potential service:

- AWS Backup

## Environment Model
Conceptual environments include:

- local development
- automated test
- shared development
- staging
- production
- optional isolated enterprise environments

Environment isolation should cover:

- credentials
- storage
- databases
- logs
- integrations
- AI providers
- Stripe
- QuickBooks

## Tenant Isolation
See [MULTI_TENANT_ARCHITECTURE.md](MULTI_TENANT_ARCHITECTURE.md).

AWS design should support:

- tenant identifiers on relational records
- tenant-aware object keys
- authorization enforcement
- tenant-scoped integration credentials
- tenant-scoped encryption considerations
- tenant-safe logs
- tenant-safe caches
- tenant-safe search indexes
- tenant-safe AI context
- prevention of cross-tenant exports

This document does not prescribe physical database-per-tenant architecture at this stage.

Possible isolation models may include:

- shared infrastructure with tenant-aware partitioning
- isolated data partitions with shared compute
- more isolated enterprise deployments where justified

Selection criteria should consider scale, compliance, cost, operational complexity, and support model.

## Repository Adapter Migration
See [PROJECT_REPOSITORY.md](PROJECT_REPOSITORY.md).

Future adapters may include:

- S3 document repository
- relational project repository
- relational workspace repository
- relational review repository
- relational knowledge repository
- audit/history event store

Cloud migration should replace adapters and persistence wiring rather than duplicate business logic.

## Deployment Stages

### Stage 0: Current local-first development
- filesystem repository
- local Streamlit application
- deterministic local workflows

### Stage 1: Cloud-compatible boundaries
- repository contract review
- tenant identifiers
- configuration isolation
- background-job contracts
- deployment packaging
- secrets abstraction

### Stage 2: Hosted internal pilot
- controlled hosted environment
- limited users
- non-public pilot
- monitoring and recovery validation
- no unsupported production claims

### Stage 3: Hosted multi-tenant beta
- tenant isolation
- authentication
- user administration
- subscriptions
- integration credentials
- operational monitoring

### Stage 4: Commercial production SaaS
- production security controls
- backup validation
- incident procedures
- deployment rollback
- billing reliability
- tenant support tooling

### Stage 5: Enterprise hardening
- SSO
- advanced audit
- data residency considerations
- enterprise support
- optional isolation models
- larger tenant scaling

## Document Processing Architecture
See [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md).

Future cloud ingestion should remain asynchronous where appropriate.

Conceptual stages include:

- temporary upload
- validation
- quarantine
- malware inspection
- hashing
- classification
- extraction
- OCR
- normalization
- indexing
- final storage
- diagnostics
- status update

## Integration Architecture
See [INTEGRATIONS.md](INTEGRATIONS.md).

Integration architecture should include:

- tenant-scoped credentials
- webhook ingress
- signature validation
- queues
- retries
- dead-letter handling
- reconciliation
- rate-limit management
- audit records

## AI Workload Direction
See [AI_ASSISTANT.md](AI_ASSISTANT.md).

Possible cloud responsibilities include:

- document preprocessing
- chunking
- embeddings
- retrieval indexes
- provider gateway
- model request audit
- source provenance
- cost monitoring
- tenant filtering

This document does not select a vector database or model provider.

## Security Boundaries
See [SECURITY.md](SECURITY.md).

AWS architecture should support:

- IAM least privilege
- private networking where appropriate
- production access controls
- secrets rotation
- encryption
- logging
- vulnerability management
- dependency scanning
- secure uploads
- environment separation
- incident access procedures

## Reliability
See [BACKUP_RECOVERY.md](BACKUP_RECOVERY.md), [OBSERVABILITY.md](OBSERVABILITY.md), and [PERFORMANCE.md](PERFORMANCE.md).

Reliability should account for:

- retries
- idempotency
- health checks
- queue durability
- graceful degradation
- deployment rollback
- restoration testing
- dependency failure handling

This document does not invent SLA, RTO, or RPO commitments.

## Cost Governance
Cost governance should consider:

- environment budgets
- storage lifecycle management
- log retention
- background-worker scaling
- AI usage cost controls
- tagging
- per-tenant usage visibility
- alerts for unexpected spend
- avoidance of premature infrastructure complexity

## Non-Goals
This document does not:

- implement AWS services
- create Terraform or CloudFormation
- select final instance sizes
- define final regions
- guarantee availability levels
- replace security or recovery policies
- require immediate cloud migration
- authorize Epic E or later lifecycle implementation

## Current Status
The current application remains local-first.

No production AWS environment is documented as implemented.

No authentication or multi-tenant production deployment exists.

AWS remains a staged architectural direction.

## Open Decisions
Open questions include:

- compute model
- relational engine
- tenancy isolation model
- deployment region strategy
- container vs serverless workload allocation
- search infrastructure
- graph persistence
- AI retrieval infrastructure
- infrastructure-as-code tooling
- CI/CD platform
- data residency
- enterprise isolation options