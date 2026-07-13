# Performance

## Purpose
This document defines performance principles and future targets for Atlas.

It avoids unsupported numeric guarantees while still documenting the behaviors the platform should optimize for.

## Related Documents
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ENGINEERING_ROADMAP.md](ENGINEERING_ROADMAP.md)
- [SEARCH_ARCHITECTURE.md](SEARCH_ARCHITECTURE.md)
- [OBJECT_GRAPH.md](OBJECT_GRAPH.md)
- [IMPORT_PIPELINE.md](IMPORT_PIPELINE.md)
- [REPORTING.md](REPORTING.md)
- [OBSERVABILITY.md](OBSERVABILITY.md)
- [AI_FOUNDATIONAL_KNOWLEDGE.md](AI_FOUNDATIONAL_KNOWLEDGE.md)
- [AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)

## Performance Principles
Atlas should remain:
- deterministic
- responsive
- predictable under load
- resource-aware
- tenant-fair
- graceful when degraded

## Key Performance Areas
- deterministic engine performance
- UI responsiveness
- large project packages
- large document sets
- search
- graph traversal
- ingestion
- cost and estimate calculations
- report generation
- AI latency
- background jobs

## Engineering Goals
Performance work should focus on:
- avoiding unnecessary recomputation
- minimizing expensive repeated parsing
- keeping hot paths deterministic
- reducing blocking work in the UI thread
- using background jobs where appropriate
- controlling memory growth on large projects

## Caching
Caching should be used carefully and should preserve determinism.

Cache boundaries should be explicit for:
- parsed documents
- search indexes
- graph traversal results
- report snapshots
- AI retrieval artifacts when appropriate

## Pagination And Streaming
Large result sets should use:
- pagination
- incremental rendering
- streaming where practical
- progressive disclosure for dense UI surfaces

## Concurrency
Concurrent work should respect:
- tenant fairness
- job isolation
- retry safety
- resource limits
- deterministic outputs where required

## Load Testing
Performance validation should include realistic project size, document volume, and search/ingestion usage patterns.

## Rate Limiting
Rate limiting may be necessary for:
- public APIs
- integrations
- background jobs
- AI-assisted workflows

## Performance Budgets
Budgets should exist for major workflows, but specific numeric thresholds remain future implementation policy rather than current documented commitments.

## Unresolved Decisions
- final benchmark suite remains open
- final performance budget targets remain open
- final caching strategy remains open