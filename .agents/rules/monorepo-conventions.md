# Monorepo Conventions Rule

## Scope

Applies to every coding-agent task in this repository.

## Activation

Always active.

## Conventions

1. Place public UI code in `uis/website`.
2. Place internal UI code in `uis/backoffice`.
3. Place backend code in `services/<service-name>`.
4. Keep product agent artifacts in `agents/` and `skills/` (not inside `.agents/`).
5. Keep `.agents/` only for coding-agent behavior configuration.

## Documentation Requirements

1. New app/service folders must include a local `README.md`.
2. Parent folder README must include a short index entry.
3. Major design decisions must be logged in `memory-bank/current-status.md`.
