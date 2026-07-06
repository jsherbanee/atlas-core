# Codex Workflow

## Development Style
- One feature per prompt.
- Run full quality gate for each completed feature:
   - black .
   - ruff check .
   - mypy .
   - pytest
- Commit only after all checks pass.
- Keep commits small and focused.
- No unrelated refactors in feature prompts.
- No use of personal names in program logic.

## Scope Discipline
Until Phase 2 Bid Intelligence is complete:
- Focus only on bid analysis and estimating-readiness capabilities.
- Defer non-Phase-2 product lifecycle features.

## Prompt-to-Commit Loop
1. Implement only requested feature scope.
2. Add/update tests for the feature.
3. Run black, ruff, mypy, pytest.
4. Fix issues until checks are green.
5. Commit with a clear scoped message.
