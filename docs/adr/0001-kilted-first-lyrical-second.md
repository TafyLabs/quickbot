# ADR-0001: Kilted first, Lyrical second

- Status: **Accepted**
- Date: 2026-05-12
- Driver: master plan §2

## Context

ROS 2 has two relevant distributions for QuickBot at project start:

- **Kilted Kaiju** — released, deb packages for Ubuntu 24.04 (Noble) on amd64 + arm64, supported through November 2026. Open-RMF lists Kilted support.
- **Lyrical Luth** — pre-release at project start; targeted GA on 2026-05-22; documentation marked as a development version; deb packages target Ubuntu 26.04 (Resolute).

The team wants a working real robot fast, with a controlled migration to the newer distribution once the stack is stable.

## Decision

**Phase A** uses Kilted Kaiju on Ubuntu 24.04 as the primary implementation + validation target. All packages, Dockerfiles, configs, and validation gates land on Kilted first.

**Phase B** migrates the same repository and validation matrix to Lyrical Luth on Ubuntu 26.04 only after Kilted gates G0–G10 pass.

## Consequences

- Kilted images are tagged and preserved; Lyrical images live in a parallel set of Dockerfiles (`docker/lyrical-base.Dockerfile`, added in Phase B).
- We minimize custom Nav2 plugin code so the Kilted → Lyrical migration is mostly a base-image swap plus param-file deltas.
- We accept that Open-RMF on Lyrical may lag binary availability; the rollback plan keeps the Kilted images functional throughout Phase B.

## Alternatives considered

- **Lyrical-only from day one.** Rejected: Lyrical is pre-GA at project start; cycle time of "wait for an upstream package, file a bug, work around it" is high. We would not have a real robot moving by the planned demo date.
- **Rolling.** Rejected for the stable target. Useful for upstream fixes (Phase C, exploration only).
