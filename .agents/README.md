# .agents configuration

This folder configures how coding agents operate in this repository.

## Structure

```text
.agents/
├── README.md
├── rules/
│   ├── monorepo-conventions.md
│   └── delivery-gate.md
└── skills/
    └── pr-readiness-check/
        └── SKILL.md
```

## Important distinction

1. `.agents/` is for coding-agent behavior and workflows.
2. `agents/` and `skills/` at repository root are product-side project areas.
