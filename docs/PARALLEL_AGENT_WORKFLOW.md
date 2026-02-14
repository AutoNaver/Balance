# Parallel Agent Workflow

This repository is expected to have multiple agents committing concurrently.

## Mandatory Setup

- Each agent must use its own git worktree.
- Each worktree must use exactly one feature branch.
- Agents must not develop directly on `main`.
- Hooks must be enabled once per clone:

```powershell
pwsh scripts/enable_agent_hooks.ps1
```

Use:

```powershell
pwsh scripts/agent_worktree_start.ps1 -Agent <agent_id> -Feature <short_feature_name>
```

## Feature Completion and Push Policy

When a feature is complete, publish immediately:

```powershell
pwsh scripts/agent_publish_feature.ps1
```

Or use the one-command completion flow:

```powershell
pwsh scripts/agent_complete_feature.ps1 -CommitMessage "feat: <short message>"
```

This script:
- validates the working tree is clean
- runs tests (unless `-SkipTests`)
- ensures push to `main` is fast-forward only
- pushes `HEAD` to `origin/main`

Pre-push hook guard:
- pushes to refs other than `refs/heads/main` are rejected
- this enforces "publish completed features directly to main"

No squash/rewrite logic is performed by the script. If not fast-forward, rebase on `origin/main` and re-run.

## Conflict-Reduction Rules

- Work in narrow files only; avoid broad refactors unless requested.
- Prefer additive changes over rewriting shared files.
- Keep one feature per branch.
- If creating new artifacts (docs, requests, data), use unique filenames.
- Use `requests/` for new feature proposals to avoid editing a single shared backlog file.
- Avoid frequent edits to shared hotspot files (`README.md`) unless necessary.

## Suggested Branch Naming

- `feature/<area>-<short-description>`
- Example: `feature/model-hullwhite`

## Ownership Hints

- `src/models/`: model-specific logic
- `src/products/`: product pricing logic
- `src/engine/`: orchestration and aggregation
- `src/io_layer/`: loaders and serializers
- `tests/`: validation

Keep interfaces stable when possible (`Product`, `InterestRateModel`, `ScenarioGenerator`, `ValuationEngine`).
