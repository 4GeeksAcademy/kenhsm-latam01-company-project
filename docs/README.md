# `docs` folder

This folder holds **cross-cutting documentation** for the monorepo: architecture guides, technical decisions, conventions, processes, and any material shared across applications, pipelines, agents, and workflows.

- **Main purpose**: provide a single place for “global” project documentation (not tied to one app or agent only).
- **Recommendation**: organize docs by topic (architecture, deployment, data, security, observability, etc.) and keep links from each component’s README to these guides.

> _Spanish version: [README.es.md](./README.es.md)._

## Guides

- [Brasaland manager agent memory design](./agent-memory/memory-design.md): architecture, privacy, consent, retention, and verified approval/rejection cycles.
- [Brasaland manager agent guardrail harness](./agent-memory/guardrail-harness.md): scope policy, injection isolation, output validation, abuse cases, and metrics.
