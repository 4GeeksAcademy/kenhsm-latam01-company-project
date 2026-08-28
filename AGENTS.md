# AGENTS.md

This file defines how any coding agent must operate in this repository.

## 1) Mandatory Read Order Before Editing

Every session must read these files in order before making changes:

1. `README.md`
2. `CONTEXT.md`
3. `memory-bank/business-context.md`
4. `memory-bank/technical-context.md`
5. `memory-bank/project-rules.md`
6. All files in `.agents/rules/`

If any of these are missing or outdated, stop and update them before coding.

## 2) Delivery Flow (No Exceptions)

Before opening a PR or creating a commit, the agent must:

1. Clarify objective, scope, and impacted folders.
2. Confirm monorepo location is correct:
   - Public interfaces in `uis/`
   - Internal/business interfaces in `uis/backoffice`
   - Backend services in `services/`
3. Implement smallest safe change set.
4. Self-review for regressions and requirement coverage.
5. Update `memory-bank/` with any new decisions and current status.
6. Run project checks that apply to changed code (lint, type-check, tests, build when available).
7. Prepare PR summary with:
   - What changed
   - Why it changed
   - How it was verified
   - Risks and follow-up tasks

## 3) Stop-and-Ask Conditions

The agent must stop and ask for guidance if:

1. Requirements conflict with existing rules.
2. A change requires destructive operations or data deletion.
3. Credentials, secrets, or production configuration are needed.
4. The change touches more areas than initially scoped.

## 4) Quality Bar

All changes must be:

1. Aligned with existing folder responsibilities.
2. Documented with concise README updates when structure changes.
3. Verifiable through explicit acceptance criteria.

## 5) Rule Sources

Specific conventions live in:

- `.agents/rules/`
- `.agents/skills/`

This file is the global protocol. Folder rules and skills are the execution details.
