# Skill: PR Readiness Check

## Purpose

Run a consistent pre-PR validation workflow and produce a verification report.

## When To Use

Use this skill before any commit or pull request.

## Inputs

1. `task_summary`: one paragraph describing the implemented change.
2. `changed_paths`: list of modified files/folders.
3. `verification_commands`: list of commands that apply to the modified areas.
4. `acceptance_criteria`: explicit requirement checklist.

## Procedure

1. Confirm every changed path belongs to the correct monorepo area.
2. Run each verification command and capture exit code/output summary.
3. Validate each acceptance criterion with direct evidence.
4. Check that `memory-bank/current-status.md` was updated if decisions changed.
5. Produce a final PR readiness report.

## Output Format

Return a Markdown report with:

1. `Scope`: task summary + changed paths.
2. `Checks`: each command, result (`PASS`/`FAIL`), and key evidence.
3. `Criteria Validation`: each criterion and evidence.
4. `Risks`: unresolved concerns or follow-up actions.
5. `Final Status`: `READY` or `NOT READY`.

## Acceptance Criteria (Verifiable)

This skill is valid only if all items are true:

1. Every command in `verification_commands` was executed and reported.
2. At least one evidence line is attached per acceptance criterion.
3. Final status is `READY` only when all checks and criteria pass.
4. If one check fails, final status must be `NOT READY` and include next action.

## Example Invocation

```md
task_summary: Added website and backoffice initial entrypoints.
changed_paths:
  - uis/website/index.html
  - uis/backoffice/index.html
verification_commands:
  - ls uis/website
  - ls uis/backoffice
acceptance_criteria:
  - Website entrypoint exists
  - Backoffice entrypoint exists
```
