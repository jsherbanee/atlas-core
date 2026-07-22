# AV-00E Validation Transcript

Date: 2026-07-21

Objective: preserve concise, durable validation evidence for AV-00E non-blocking estimate-open behavior without changing runtime behavior.

## Route Validation: No-Estimate Project Path

Validated result from the no-estimate probe:

- page: Transactions
- secondary: estimates
- tertiary: add
- selected_document_id: empty
- estimate_add_project: BID-2026-0002
- query parameters: atlas_page=Transactions, atlas_transaction_family=estimates, atlas_transaction_action=add
- rerun: true

Interpretation:

- This confirms the intended non-blocking Create Estimate path.
- Initial project estimate action navigation goes directly to Transactions > Estimates > Add for no-estimate projects.

## Restricted-Run Failure and Rerun Outcome

Observed restricted-run failure:

- PermissionError when reading Atlas runtime project storage under AtlasProjects.

Interpretation:

- The error was caused by sandbox/restricted execution permissions.
- This is not an Atlas application-logic failure.

Successful rerun:

- The same probe executed successfully through a broader-access shell environment and produced the expected no-estimate route result documented above.

## Legacy Heavy-Path Performance Evidence

Recorded timing payload:

- BOM enrichment: 756232.2 ms
- resolution: 189.0 ms
- estimate build: 107.4 ms
- pricing: 828.8 ms
- priced lines: 13663

Interpretation (evidence-bound):

- The legacy estimate-open path is dominated by synchronous BOM enrichment in this measurement.
- Resolution, estimate construction, and pricing are comparatively small in the same payload.
- AV-00E behavior avoids invoking that heavy path during initial estimate navigation for the no-estimate flow.

This interpretation is limited to the measured probe results above.

## Shell Wrapper Noise Note

Observed message:

- EOF marker not found

Interpretation:

- This came from the heredoc wrapper around the profiling command.
- The profiler payload still executed and printed successfully.
- The wrapper noise does not invalidate the captured timing payload.
- A cleaner profiler wrapper can be added later if repeated profiling is needed.
