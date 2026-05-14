# ADR-0004: MIT license

- Status: **Accepted**
- Date: 2026-05-13
- Supersedes: initial Apache-2.0 choice in the first commit

## Context

The first commit set the project license to Apache-2.0 across `package.xml`, `setup.py`, and the README footer. Tafy Labs prefers MIT as the standard outbound license for open robotics work — short, permissive, and matches the rest of the Tafy Labs / RobotDen repos.

## Decision

License all QuickBot code and assets under **MIT**. Add a top-level [`LICENSE`](../../LICENSE) file. Update every `<license>` tag in `package.xml` and every `license=` field in `setup.py` to `MIT`.

## Consequences

- Any third-party code imported into `ws/src` must be MIT-compatible. Most ROS 2 packages are Apache-2.0 or BSD; both are compatible as dependencies (we link, we don't relicense).
- The fleet_adapter_template we'll fork in P8 is Apache-2.0. We can use it directly — our copy will retain its upstream Apache-2.0 file header, and the rest of `quickbot_rmf_adapter` is MIT. Document mixed licensing in the package README when the time comes.
- The Create 2 Open Interface specification is reference documentation, not code; no licensing implication.

## Alternatives considered

- **Apache-2.0** (original choice). Slightly more explicit patent grant; reasonable for robotics code. Rejected for consistency with the rest of the Tafy Labs portfolio.
- **BSD-3-Clause.** Functionally similar to MIT for this use case. MIT wins on terseness.
