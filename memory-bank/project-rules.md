# Project Rules

## Global Working Rules

1. Read `AGENTS.md` and `.agents/rules/*.md` before coding.
2. Use minimal, requirement-driven changes.
3. Keep feature code in the correct monorepo folder.
4. Do not move product agent code (`agents/`, `skills/`) into `.agents/`.

## Delivery Rules

1. No commit/PR without self-review and verification notes.
2. Any structure change must update relevant README files.
3. Any recurring process should become a reusable skill when possible.

## Memory Update Rule

After each meaningful task:

1. Update `memory-bank/current-status.md`.
2. Record decisions that future sessions must not rediscover.
