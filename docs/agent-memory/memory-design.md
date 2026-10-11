# Brasaland Manager Agent Memory

## Architecture

The manager-support agent uses **episodic, user-scoped SQLite memory** by default at `~/.local/state/brasaland/agent_memory.sqlite3`, separate from Qdrant's `brasaland_knowledge` collection and outside the source tree. Set `AGENT_MEMORY_DB_PATH` to a durable mounted volume in deployment. SQLite fits a small set of recurring location-specific facts and needs atomic pending-proposal decisions, indexed owner/category/scope updates, and an appendable audit record; semantic/vector search is unnecessary at this bounded scale. A knowledge graph is also unnecessary because the use cases are concise operational corrections, not multi-hop entity relationships. Fine-tuning is rejected because approved facts must be removable and attributable.

The agent has explicit `read_memories`, `propose_memory`, `resolve_proposal`, and `audit_log` operations through `AgentMemoryStore`. Approved notes are passed as a separate field to one structured model call; they are user-reported hints and can never override retrieved company knowledge. The RAG store remains read-only.

## Eligibility And Privacy

The model proposes memory only for durable, recurring operational corrections by location, repeated escalation causes, or stable manager communication preferences. The output must have confidence >= 0.85, one of the three supported categories, a 20-500 character fact, and a scope key. The store independently validates the category and fact before it can become pending.

The store blocks any customer/loyalty data, email addresses, and payroll/individual-compensation information in the proposed fact, source message, reason, scope, or decision message. This is conservative: customer information belongs in CRM, and compensation belongs in HR systems. One-off customer complaints and transient requests must not be remembered.

The owner ID comes from the authenticated backend JWT, never from a request field. Notes are private to that manager, are labelled as unverified hints, and are subordinate to the curated RAG corpus. Explicit user approval is required for every write. This limits poisoning to the approving manager's own notes rather than company-wide knowledge; a manager's claim is still not promoted to authoritative company policy.

## Proposal And Decision Flow

1. Authenticated agent requests load at most eight approved notes and the user's one pending proposal. `/agent/memory` and `/agent/memory/audit` are authenticated, owner-scoped, read-only views.
2. A pending proposal is classified before RAG or MCP routing. The classifier accepts a small set of explicit Spanish/English decisions and edits; it does not use substring checks such as `"sí" in message`.
3. Unclear replies are audited as `ambiguous_discard` and never become consent. A clear approval/edit can be followed by another question in the same message; that continuation proceeds through normal RAG/MCP routing.
4. A proposal is shown in the same answer as “¿Quieres que recuerde esto para la próxima vez?” or “Would you like me to remember this for next time?”. It remains pending until the next explicit user decision.
5. Only `approved` or safe `edited` proposals enter `approved_memories`; rejection and ambiguity remain in the proposal audit table without changing the memory set.

The structured answer and optional proposal are requested in one model completion. If the provider is unavailable or the JSON is invalid, no proposal is made and no second generation call is attempted. Deterministic eligibility checks suppress three examples even if the model incorrectly proposes memory: asking yesterday's average ticket in Bogotá; saying “gracias, eso resuelve mi duda”; requesting a one-off English translation for Ashley's report.

## Consolidation And Expiry

- At most one pending proposal per manager; a SQLite partial unique index enforces this atomically.
- Unanswered proposals expire after 7 days and are marked `expired` on the next memory-store operation.
- Approved notes expire after 180 days without renewal, allowing outdated supplier schedules and hours to fall away.
- Notes deduplicate by `(owner, category, scope_key)`; a new approved correction replaces the prior value for that location/topic.
- Each owner has a maximum of 50 approved notes; least-recently-used notes are removed on overflow. Each turn reads at most 8 notes.
- Decision audit records are kept for 730 days, after which cleanup removes resolved audit rows. Rejected proposals are not deleted immediately.

## Evidence

Run memory-store and agent-flow evidence with:

```bash
cd services/brasaland-api
PYTHONPATH=src:../.. uv run pytest tests/test_agent_memory.py tests/test_agent_memory_flow.py -q
```

The approval cycle in `test_approval_cycle_is_proposed_then_used_on_future_turn` verifies that the first turn only proposes, the user explicitly approves on the next turn, the audit records approval, and a later response receives the stored Tuesday delivery note. The rejection cycle in `test_rejection_cycle_keeps_audit_but_never_changes_memory` verifies that an explicit “No, gracias” leaves memory empty while preserving a rejected audit record. Tests stub the structured model output, so they prove the state/memory contract without requiring live model credentials. Additional checks cover edited facts, ambiguous topic changes, sensitive data, pending expiry, owner isolation, and the 50-note limit.

## Governance Boundary

A separate agent or approval service is not needed: proposal generation, classification, and persistence are deterministic steps around the existing single LangGraph agent. Production core-memory governance is intentionally out of scope for this learning milestone; the implemented state is personal episodic memory, not shared company policy.
