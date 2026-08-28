# Technical Context

## Monorepo Model

This repository is a multi-area monorepo for AI Engineering milestones.

## Folder Responsibilities

1. `uis/`: all frontend interfaces.
2. `services/`: backend APIs and workers.
3. `data/`: datasets, pipelines, and evaluations.
4. `packages/`: shared packages and types.
5. `skills/`: product-side agent skills (not tooling config).
6. `.agents/`: coding-agent configuration (rules and skills for development workflows).

## Current UI Baseline

1. Public-facing entrypoint should live in `uis/website`.
2. Internal operations entrypoint should live in `uis/backoffice`.

## Backend Placement Rule

Any new backend service must be created under `services/<service-name>` with local documentation.

## Documentation Expectations

When adding a new app/service:

1. Add a local `README.md` in that subfolder.
2. Update the parent folder README with a short index entry.

## Quality and Verification

1. Keep changes scoped and reversible.
2. Define explicit acceptance criteria for reusable skills.
3. Capture architecture and workflow decisions in `memory-bank/current-status.md`.
