# Contributing to QuickBot

## Workflow

1. Pick an open issue. Each gate (`Gx`) and phase (`Px`) issue has a procedure + pass condition.
2. Branch from `main`: `git switch -c <type>/<short-slug>` (e.g. `g3/raw-serial`).
3. Run the relevant validation script: `./tools/gX_*.sh`.
4. Capture evidence under `validation/{logs,bags,screenshots}/`.
5. Append a row to [`validation/gates.md`](validation/gates.md).
6. Open a PR. Reference the gate/phase issue with `Closes #N`.

## Branch naming

| Prefix | Use |
| --- | --- |
| `g<id>/...` | Work on a specific gate (e.g. `g3/raw-serial`). |
| `p<id>/...` | Work on a phase deliverable. |
| `docs/...` | Documentation only. |
| `chore/...` | Tooling, CI, lint. |
| `wip/...` | Exploratory branches (do not merge directly to `main`). |

## ADRs

Significant architectural or process decisions belong in `docs/adr/`. Use the existing format (status, date, context, decision, consequences, alternatives). Number monotonically. See [`docs/adr/README.md`](docs/adr/README.md).

## Commits

- Single concern per commit.
- First line `<scope>: <imperative>` (≤72 chars).
- Body explains *why*. Skip the *what* — diffs cover that.
- Reference issues with `Closes #N` or `Refs #N`.

## Adding a new gate or phase

If the master plan grows a new step:

1. Update [`docs/master-plan.md`](docs/master-plan.md) (and the vault source at `raw/papers/QuickBot_...md`).
2. Add a row to [`docs/gates.md`](docs/gates.md) and [`validation/gates.md`](validation/gates.md).
3. Open a tracking issue using the `gate` or `phase` template.
4. Add a `tools/gX_*.sh` runner if the gate has a reproducible script.

## Code style

- Python: `ruff check ws/src` (see [`pyproject.toml`](pyproject.toml)).
- Dockerfiles: `hadolint` via CI.
- YAML: `yamllint` via CI.
- No comments restating what the code does. Comment *why* when it's non-obvious.
