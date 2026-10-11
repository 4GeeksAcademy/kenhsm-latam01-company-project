from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

MEMORABLE_CATEGORIES = {
    "operational_correction",
    "escalation_context",
    "communication_preference",
}
MAX_FACTS_PER_USER = 50
FACT_TTL_DAYS = 180
PENDING_TTL_DAYS = 7
AUDIT_RETENTION_DAYS = 730

_FORBIDDEN_PATTERNS = (
    r"\b(?:brasa\s*points|loyalty\s+card|tarjeta\s+de\s+fidelidad)\b",
    r"\b(?:cliente|customer)\b",
    r"\b(?:email|e-mail|correo)\s*[:=]?\s*[\w.+-]+@[\w.-]+\.[a-z]{2,}\b",
    r"\b(?:payroll|n[oó]mina|salario|sueldo|compensaci[oó]n|salary|wage)\b",
    r"\b(?:employee|empleado|staff member)\b.{0,60}\b(?:salary|wage|salario|sueldo|pay|compensaci[oó]n)\b",
)


@dataclass(frozen=True)
class MemoryDecision:
    intent: Literal["approve", "reject", "edit", "ambiguous"]
    confidence: float
    continuation: str
    edited_fact: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char)).strip()


def is_safe_memory_fact(fact: str, category: str) -> bool:
    normalized = _normalize(fact)
    if category not in MEMORABLE_CATEGORIES or not 20 <= len(fact.strip()) <= 500:
        return False
    return not _contains_forbidden_content(normalized)


def is_ephemeral_interaction(message: str) -> bool:
    normalized = _normalize(message)
    return any(
        re.search(pattern, normalized, re.IGNORECASE)
        for pattern in (
            r"\b(?:ticket promedio|average ticket)\b.*\b(?:ayer|hoy|yesterday|today)\b",
            r"^(?:gracias|thank you|thanks)\b",
            r"\b(?:traducir|traduce|translate|translation)\b.*\b(?:ingles|english|reporte|report)\b",
        )
    )


def _contains_forbidden_content(value: str) -> bool:
    normalized = _normalize(value)
    return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _FORBIDDEN_PATTERNS)


def classify_memory_decision(message: str) -> MemoryDecision:
    """Classify explicit leading decisions; ambiguous replies never imply consent."""
    raw = message.strip()
    normalized = _normalize(raw)
    edit_match = re.match(
        r"^(?:edita|corrige|cambia|modifica)\s+(?:la propuesta|lo que recordar[aá]s|the proposal|what you will remember)\s+(?:por|a|to|with)\s*:\s*(.+)$",
        raw,
        re.IGNORECASE,
    )
    if edit_match:
        return MemoryDecision("edit", 0.99, "", edit_match.group(1).strip())

    decision_phrases = {
        "approve": (
            "yes, remember this", "yes, save it", "yes please", "yes", "approved", "approve",
            "confirmo", "aprobado", "aprobada", "de acuerdo", "guarda esto", "recuerda esto",
            "si, recuerdalo", "si, guardalo", "si", "dale",
        ),
        "reject": (
            "no, do not remember this", "no, don't remember this", "no, do not save it", "no, don't save it",
            "no, thanks", "no thanks", "no, gracias", "no gracias", "no lo recuerdes", "no lo guardes",
            "rechazo", "rechazada", "rechazado", "no",
        ),
    }
    for intent, phrases in decision_phrases.items():
        for phrase in sorted(phrases, key=len, reverse=True):
            normalized_phrase = _normalize(phrase)
            if normalized == normalized_phrase:
                return MemoryDecision(intent, 0.99, "")
            if normalized.startswith(normalized_phrase) and len(raw) > len(phrase):
                boundary = raw[len(phrase):len(phrase) + 1]
                if boundary and boundary in ",;:!.?":
                    continuation = raw[len(phrase) + 1:].strip()
                    if intent == "approve" and re.match(
                        r"^(?:but|pero|however|except|change|edit|replace|correct|cambia|corrige|edita)\b",
                        _normalize(continuation),
                    ):
                        return MemoryDecision("ambiguous", 0.0, raw)
                    continuation = re.sub(
                        r"^(?:(?:thanks|gracias)\b[,.]?\s*)?(?:(?:and|y|also|tambien)\b\s*)?",
                        "",
                        continuation,
                        flags=re.IGNORECASE,
                    )
                    return MemoryDecision(intent, 0.96, continuation)
                if boundary.isspace() and intent == "approve" and normalized_phrase in {"yes", "si"}:
                    continuation_text = raw[len(phrase):].strip()
                    connector = re.match(r"^(?:and|y|also|tambien)\b\s*", _normalize(continuation_text))
                    if connector:
                        continuation_text = continuation_text[connector.end():].strip()
                        return MemoryDecision(intent, 0.93, continuation_text)

    return MemoryDecision("ambiguous", 0.0, raw)


class AgentMemoryStore:
    """SQLite episodic memory and audit log, separate from the company RAG index."""

    def __init__(self, path: str | Path | None = None):
        if path is None:
            default_path = Path.home() / ".local" / "state" / "brasaland" / "agent_memory.sqlite3"
            path = os.getenv("AGENT_MEMORY_DB_PATH", str(default_path))
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_proposals (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    scope_key TEXT NOT NULL,
                    proposed_fact TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    source_message TEXT NOT NULL,
                    status TEXT NOT NULL,
                    decision_message TEXT,
                    decision_confidence REAL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    expires_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_pending_memory_per_owner
                    ON memory_proposals(owner_id) WHERE status = 'pending';
                CREATE INDEX IF NOT EXISTS memory_proposals_owner_created
                    ON memory_proposals(owner_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS approved_memories (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    scope_key TEXT NOT NULL,
                    fact TEXT NOT NULL,
                    approval_proposal_id TEXT NOT NULL,
                    approved_at TEXT NOT NULL,
                    last_used_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    UNIQUE(owner_id, category, scope_key),
                    FOREIGN KEY(approval_proposal_id) REFERENCES memory_proposals(id)
                );
                CREATE INDEX IF NOT EXISTS approved_memories_owner_expiry
                    ON approved_memories(owner_id, expires_at);
                """
            )

    def _cleanup(self, connection: sqlite3.Connection) -> None:
        now = _now()
        connection.execute(
            "UPDATE memory_proposals SET status='expired', resolved_at=?, decision_message='[expired]' "
            "WHERE status='pending' AND expires_at <= ?",
            (_iso(now), _iso(now)),
        )
        connection.execute(
            "DELETE FROM approved_memories WHERE expires_at <= ?",
            (_iso(now),),
        )
        audit_before = _iso(now - timedelta(days=AUDIT_RETENTION_DAYS))
        connection.execute(
            "DELETE FROM memory_proposals WHERE status!='pending' AND resolved_at <= ?",
            (audit_before,),
        )

    def read_memories(self, owner_id: str, *, limit: int = 8) -> list[dict]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._cleanup(connection)
            rows = connection.execute(
                "SELECT category, scope_key, fact, approved_at FROM approved_memories "
                "WHERE owner_id=? AND expires_at>? ORDER BY last_used_at DESC LIMIT ?",
                (owner_id, _iso(), min(max(limit, 1), MAX_FACTS_PER_USER)),
            ).fetchall()
            if rows:
                connection.execute(
                    "UPDATE approved_memories SET last_used_at=? WHERE owner_id=? AND id IN "
                    "(SELECT id FROM approved_memories WHERE owner_id=? AND expires_at>? ORDER BY last_used_at DESC LIMIT ?)",
                    (_iso(), owner_id, owner_id, _iso(), min(max(limit, 1), MAX_FACTS_PER_USER)),
                )
            connection.commit()
        return [dict(row) for row in rows]

    def get_pending_proposal(self, owner_id: str) -> dict | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._cleanup(connection)
            row = connection.execute(
                "SELECT * FROM memory_proposals WHERE owner_id=? AND status='pending' ORDER BY created_at LIMIT 1",
                (owner_id,),
            ).fetchone()
            connection.commit()
        return dict(row) if row else None

    def propose_memory(
        self,
        owner_id: str,
        *,
        fact: str,
        category: str,
        scope_key: str,
        reason: str,
        source_message: str,
    ) -> dict | None:
        fact = fact.strip()
        category = category.strip()
        scope_key = scope_key.strip()[:100] or "global"
        if (
            not is_safe_memory_fact(fact, category)
            or not owner_id
            or _contains_forbidden_content(reason)
            or _contains_forbidden_content(source_message)
            or _contains_forbidden_content(scope_key)
        ):
            return None
        now = _now()
        proposal_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._cleanup(connection)
            pending = connection.execute(
                "SELECT id FROM memory_proposals WHERE owner_id=? AND status='pending'",
                (owner_id,),
            ).fetchone()
            if pending:
                connection.rollback()
                return None
            connection.execute(
                "INSERT INTO memory_proposals "
                "(id, owner_id, category, scope_key, proposed_fact, reason, source_message, status, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
                (
                    proposal_id,
                    owner_id,
                    category,
                    scope_key,
                    fact,
                    reason.strip()[:250],
                    source_message.strip()[:1000],
                    _iso(now),
                    _iso(now + timedelta(days=PENDING_TTL_DAYS)),
                ),
            )
            connection.commit()
        return {
            "id": proposal_id,
            "fact": fact,
            "category": category,
            "scope_key": scope_key,
            "reason": reason.strip()[:250],
            "status": "pending",
        }

    def resolve_proposal(
        self,
        owner_id: str,
        proposal_id: str,
        *,
        decision: MemoryDecision,
        decision_message: str,
    ) -> dict | None:
        now = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._cleanup(connection)
            row = connection.execute(
                "SELECT * FROM memory_proposals WHERE id=? AND owner_id=? AND status='pending'",
                (proposal_id, owner_id),
            ).fetchone()
            if row is None:
                connection.rollback()
                return None
            status = {
                "approve": "approved",
                "reject": "rejected",
                "edit": "edited",
                "ambiguous": "ambiguous_discard",
            }[decision.intent]
            fact = decision.edited_fact if decision.intent == "edit" else row["proposed_fact"]
            if decision.intent == "edit" and not is_safe_memory_fact(fact or "", row["category"]):
                status = "unsafe_edit_rejected"
                fact = None
            safe_decision_message = (
                "[redacted-sensitive-content]"
                if _contains_forbidden_content(decision_message)
                else decision_message.strip()[:1000]
            )
            connection.execute(
                "UPDATE memory_proposals SET status=?, decision_message=?, decision_confidence=?, resolved_at=? WHERE id=?",
                (status, safe_decision_message, decision.confidence, _iso(now), proposal_id),
            )
            if status in {"approved", "edited"} and fact:
                connection.execute(
                    "INSERT INTO approved_memories "
                    "(id, owner_id, category, scope_key, fact, approval_proposal_id, approved_at, last_used_at, expires_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(owner_id, category, scope_key) DO UPDATE SET "
                    "fact=excluded.fact, approval_proposal_id=excluded.approval_proposal_id, "
                    "approved_at=excluded.approved_at, last_used_at=excluded.last_used_at, expires_at=excluded.expires_at",
                    (
                        str(uuid.uuid4()), owner_id, row["category"], row["scope_key"], fact,
                        proposal_id, _iso(now), _iso(now), _iso(now + timedelta(days=FACT_TTL_DAYS)),
                    ),
                )
                overflow = connection.execute(
                    "SELECT id FROM approved_memories WHERE owner_id=? ORDER BY last_used_at DESC LIMIT -1 OFFSET ?",
                    (owner_id, MAX_FACTS_PER_USER),
                ).fetchall()
                if overflow:
                    connection.executemany("DELETE FROM approved_memories WHERE id=?", [(item["id"],) for item in overflow])
            connection.commit()
        return {"status": status, "fact": fact, "proposal_id": proposal_id}

    def audit_log(self, owner_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, owner_id, category, scope_key, proposed_fact, source_message, status, decision_message, "
                "decision_confidence, created_at, resolved_at FROM memory_proposals "
                "WHERE owner_id=? ORDER BY created_at",
                (owner_id,),
            ).fetchall()
        return [dict(row) for row in rows]
