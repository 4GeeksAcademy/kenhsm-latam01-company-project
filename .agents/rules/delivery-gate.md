# Delivery Gate Rule

## Objective

Prevent unverified or incomplete changes from being committed.

## Mandatory Pre-Commit Checklist

1. Requirement coverage confirmed.
2. Scope and impacted paths listed.
3. Self-review completed for regressions.
4. Relevant checks executed (lint/test/type-check/build where available).
5. Memory bank updated with new decisions/status.
6. PR summary prepared with verification evidence.

## Hard Stop Conditions

Do not commit if any condition is true:

1. Acceptance criteria are missing.
2. Verification commands were not run.
3. Folder placement does not match monorepo conventions.
4. Required documentation updates are missing.
