"""SQLite persistence, secret redaction, Knowledge Base separation, Communication Audit Log, and macOS Keychain storage."""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(sk-[A-Za-z0-9_\-]{12,})"),
    re.compile(r"(ghp_[A-Za-z0-9]{16,})"),
    re.compile(r"(AIza[0-9A-Za-z\-_]{20,})"),
    re.compile(r"(Bearer\s+[A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE),
    re.compile(
        r"((?:api[_-]?key|token|secret|password|passwd|authorization)\s*[:=]\s*['\"]?)([^\s'\",;}{]+)",
        re.IGNORECASE,
    ),
]


def redact_secrets(value: Any) -> Any:
    """Recursively redact API keys, tokens, passwords, and Bearer headers from logs and audit records."""
    if isinstance(value, str):
        out = value
        for pat in SECRET_PATTERNS:
            if pat.groups == 2:
                out = pat.sub(r"\1[REDACTED]", out)
            else:
                out = pat.sub("[REDACTED]", out)
        return out
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for k, v in value.items():
            k_lower = str(k).lower()
            if any(
                s in k_lower
                for s in (
                    "api_key",
                    "apikey",
                    "secret",
                    "password",
                    "token",
                    "authorization",
                    "private_key",
                )
            ):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = redact_secrets(v)
        return sanitized
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


class KeychainVault:
    """macOS Keychain integration via `/usr/bin/security` with isolated memory fallback for tests."""

    SERVICE_PREFIX = "com.cosmictera.nui.desktop"

    def __init__(self, use_os_keychain: bool = True) -> None:
        self.use_os_keychain = use_os_keychain
        self._memory_vault: dict[str, str] = {}

    def set_secret(self, account: str, secret: str) -> bool:
        self._memory_vault[account] = secret
        if not self.use_os_keychain:
            return True
        try:
            subprocess.run(
                [
                    "/usr/bin/security",
                    "add-generic-password",
                    "-U",
                    "-s",
                    self.SERVICE_PREFIX,
                    "-a",
                    account,
                    "-w",
                    secret,
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=3,
            )
            return True
        except Exception:
            return True

    def get_secret(self, account: str) -> str | None:
        if account in self._memory_vault:
            return self._memory_vault[account]
        if not self.use_os_keychain:
            return None
        try:
            res = subprocess.run(
                [
                    "/usr/bin/security",
                    "find-generic-password",
                    "-s",
                    self.SERVICE_PREFIX,
                    "-a",
                    account,
                    "-w",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=3,
            )
            val = res.stdout.strip()
            if val:
                self._memory_vault[account] = val
                return val
        except Exception:
            pass
        return None

    def delete_secret(self, account: str) -> bool:
        self._memory_vault.pop(account, None)
        if not self.use_os_keychain:
            return True
        try:
            subprocess.run(
                [
                    "/usr/bin/security",
                    "delete-generic-password",
                    "-s",
                    self.SERVICE_PREFIX,
                    "-a",
                    account,
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
            )
        except Exception:
            pass
        return True


class NUIStorage:
    """Thread-safe SQLite storage for CosmicTera NUI Desktop."""

    def __init__(self, db_path: str | Path, use_os_keychain: bool = True) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.keychain = KeychainVault(use_os_keychain=use_os_keychain)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    mode TEXT NOT NULL DEFAULT 'HYBRID',
                    provider TEXT NOT NULL DEFAULT 'native_nui',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    request_id TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS communication_logs (
                    request_id TEXT PRIMARY KEY,
                    response_id TEXT,
                    session_id TEXT NOT NULL,
                    user_message_id TEXT,
                    assistant_message_id TEXT,
                    ui_handler TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    http_status INTEGER NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT,
                    execution_status TEXT NOT NULL,
                    ui_state TEXT NOT NULL,
                    response_time_ms REAL NOT NULL,
                    user_message TEXT NOT NULL,
                    response_preview TEXT NOT NULL,
                    error TEXT,
                    timestamp REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    steps_json TEXT NOT NULL DEFAULT '[]',
                    result_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS permission_rules (
                    rule_id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_value TEXT NOT NULL,
                    operation TEXT NOT NULL DEFAULT '*',
                    decision TEXT NOT NULL,
                    session_id TEXT,
                    expires_at REAL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pending_approvals (
                    request_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    task_id TEXT,
                    category TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_value TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    decision TEXT,
                    decided_at REAL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS authorized_folders (
                    folder_id TEXT PRIMARY KEY,
                    path TEXT UNIQUE NOT NULL,
                    label TEXT NOT NULL,
                    access_mode TEXT NOT NULL DEFAULT 'READ_WRITE',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS api_connectors (
                    connector_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    auth_type TEXT NOT NULL DEFAULT 'BEARER',
                    keychain_account TEXT NOT NULL,
                    allowed_endpoints_json TEXT NOT NULL DEFAULT '["*"]',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    item_id TEXT PRIMARY KEY,
                    bucket TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source_path TEXT,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_logs (
                    audit_id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    user_request TEXT NOT NULL,
                    task_id TEXT,
                    tool_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    target TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    domain TEXT,
                    file_changed TEXT,
                    hardware_command TEXT,
                    approval_decision TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_summary TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                """
            )
            # Ensure request_id column exists if upgrading an existing messages table
            cols = [
                r["name"]
                for r in self._conn.execute("PRAGMA table_info(messages)").fetchall()
            ]
            if "request_id" not in cols:
                self._conn.execute("ALTER TABLE messages ADD COLUMN request_id TEXT")

        if self.get_setting("operating_mode") is None:
            self.set_setting("operating_mode", "HYBRID")
        if self.get_setting("active_provider") is None:
            self.set_setting("active_provider", "native_nui")
        if self.get_setting("service_port") is None:
            self.set_setting("service_port", 8848)

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self._conn.execute(
                "SELECT value_json FROM settings WHERE key = ?", (key,)
            ).fetchone()
            if not row:
                return default
            return json.loads(row["value_json"])

    def set_setting(self, key: str, value: Any) -> None:
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO settings (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at
                """,
                (key, json.dumps(value), now),
            )

    def get_all_settings(self) -> dict[str, Any]:
        with self._lock:
            rows = self._conn.execute("SELECT key, value_json FROM settings").fetchall()
            return {r["key"]: json.loads(r["value_json"]) for r in rows}

    # ── Sessions & Messages ──────────────────────────────────────────────────

    def create_session(
        self,
        title: str = "Sesi Baru CosmicTera NUI",
        mode: str | None = None,
        provider: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        sid = session_id or f"sess-{uuid.uuid4().hex[:12]}"
        now = time.time()
        eff_mode = mode or self.get_setting("operating_mode", "HYBRID")
        eff_provider = provider or self.get_setting("active_provider", "native_nui")
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO sessions (session_id, title, mode, provider, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (sid, title, eff_mode, eff_provider, now, now),
            )
        return self.get_session(sid)  # type: ignore[return-value]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if not row:
                return None
            msgs = self.list_messages(session_id)
            data = dict(row)
            data["messages"] = msgs
            return data

    def list_sessions(self, query: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if query:
                q = f"%{query}%"
                rows = self._conn.execute(
                    """
                    SELECT DISTINCT s.* FROM sessions s
                    LEFT JOIN messages m ON s.session_id = m.session_id
                    WHERE s.title LIKE ? OR m.content LIKE ?
                    ORDER BY s.updated_at DESC
                    """,
                    (q, q),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM sessions ORDER BY updated_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def rename_session(self, session_id: str, new_title: str) -> dict[str, Any] | None:
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE session_id = ?",
                (new_title, now, session_id),
            )
        return self.get_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cur = self._conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            return cur.rowcount > 0

    def export_session_markdown(self, session_id: str) -> str | None:
        sess = self.get_session(session_id)
        if not sess:
            return None
        lines = [
            f"# {sess['title']}",
            f"- **Session ID**: `{sess['session_id']}`",
            f"- **Mode**: `{sess['mode']}` | **Provider**: `{sess['provider']}`",
            "",
        ]
        for m in sess["messages"]:
            role = m["role"].upper()
            lines.append(f"## {role}")
            lines.append(m["content"])
            lines.append("")
        return "\n".join(lines)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        message_id: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        msg_id = message_id or f"msg-{uuid.uuid4().hex[:12]}"
        now = time.time()
        safe_meta = redact_secrets(metadata or {})
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO messages (message_id, session_id, request_id, role, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (msg_id, session_id, request_id, role, content, json.dumps(safe_meta), now),
            )
            self._conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
        return {
            "message_id": msg_id,
            "session_id": session_id,
            "request_id": request_id,
            "role": role,
            "content": content,
            "metadata": safe_meta,
            "created_at": now,
        }

    def list_messages(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC, rowid ASC",
                (session_id,),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d.pop("metadata_json", "{}"))
                out.append(d)
            return out

    def prune_for_edit_and_resend(
        self, session_id: str, target_message_id: str
    ) -> dict[str, Any]:
        """Remove `target_message_id` and any messages after it in `session_id` so an edited user message can be resent cleanly without duplicating stale responses."""
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT rowid, * FROM messages WHERE session_id = ? AND message_id = ?",
                (session_id, target_message_id),
            ).fetchone()
            if not row:
                return {"ok": False, "pruned_count": 0, "reason": "MESSAGE_NOT_FOUND"}
            target_rowid = row["rowid"]
            original_content = row["content"]
            cur = self._conn.execute(
                "DELETE FROM messages WHERE session_id = ? AND rowid >= ?",
                (session_id, target_rowid),
            )
            self._conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (time.time(), session_id),
            )
            return {
                "ok": True,
                "pruned_count": cur.rowcount,
                "original_message_id": target_message_id,
                "original_content": original_content,
                "remaining_messages": self.list_messages(session_id),
            }

    def pop_last_assistant_for_regenerate(
        self, session_id: str, assistant_message_id: str | None = None
    ) -> dict[str, Any]:
        """Find the user prompt corresponding to the last (or specified) assistant message, remove the assistant message and the trailing user message so `handle_chat_turn` can re-run cleanly."""
        with self._lock, self._conn:
            msgs = self._conn.execute(
                "SELECT rowid, * FROM messages WHERE session_id = ? ORDER BY created_at ASC, rowid ASC",
                (session_id,),
            ).fetchall()
            if not msgs:
                return {"ok": False, "reason": "EMPTY_SESSION"}

            target_user_row = None
            for idx in range(len(msgs) - 1, -1, -1):
                if msgs[idx]["role"] == "user":
                    target_user_row = msgs[idx]
                    break

            if target_user_row is None:
                return {"ok": False, "reason": "NO_USER_MESSAGE_FOUND"}

            user_meta = json.loads(target_user_row["metadata_json"] or "{}")
            user_prompt = str(target_user_row["content"])
            attachments = list(user_meta.get("attachments") or [])
            target_rowid = target_user_row["rowid"]

            cur = self._conn.execute(
                "DELETE FROM messages WHERE session_id = ? AND rowid >= ?",
                (session_id, target_rowid),
            )
            return {
                "ok": True,
                "user_message": user_prompt,
                "attachments": attachments,
                "removed_count": cur.rowcount,
            }

    def record_message_feedback(
        self,
        session_id: str,
        message_id: str,
        rating: str,
        note: str = "",
    ) -> dict[str, Any]:
        """Store user feedback (`THUMBS_UP` / `THUMBS_DOWN` + optional note) on a specific message."""
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT * FROM messages WHERE session_id = ? AND message_id = ?",
                (session_id, message_id),
            ).fetchone()
            if not row:
                return {"ok": False, "reason": "MESSAGE_NOT_FOUND"}
            meta = json.loads(row["metadata_json"] or "{}")
            meta["user_feedback"] = {
                "rating": rating,
                "note": note,
                "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            self._conn.execute(
                "UPDATE messages SET metadata_json = ? WHERE session_id = ? AND message_id = ?",
                (json.dumps(redact_secrets(meta)), session_id, message_id),
            )
            return {
                "ok": True,
                "session_id": session_id,
                "message_id": message_id,
                "rating": rating,
                "note": note,
                "feedback": meta["user_feedback"],
            }

    def save_session_draft(self, session_id: str, draft_text: str) -> dict[str, Any]:
        key = f"chat_draft:{session_id or 'default'}"
        self.set_setting(key, draft_text)
        return {"ok": True, "session_id": session_id or "default", "draft": draft_text}

    def get_session_draft(self, session_id: str) -> str:
        key = f"chat_draft:{session_id or 'default'}"
        val = self.get_setting(key, "")
        return str(val) if val is not None else ""

    # ── Communication Audit Logs (Section 3 & 4) ─────────────────────────────

    def record_communication_log(
        self,
        *,
        request_id: str,
        response_id: str | None,
        session_id: str,
        user_message_id: str | None,
        assistant_message_id: str | None,
        ui_handler: str,
        endpoint: str,
        http_status: int,
        provider: str,
        model: str | None,
        execution_status: str,
        ui_state: str,
        response_time_ms: float,
        user_message: str,
        response_preview: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        now = time.time()
        safe_user = str(redact_secrets(user_message))
        safe_preview = str(redact_secrets(response_preview))[:500]
        safe_err = str(redact_secrets(error)) if error else None
        record = {
            "request_id": request_id,
            "response_id": response_id,
            "session_id": session_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
            "ui_handler": ui_handler,
            "endpoint": endpoint,
            "http_status": http_status,
            "provider": provider,
            "model": model,
            "execution_status": execution_status,
            "ui_state": ui_state,
            "response_time_ms": round(response_time_ms, 3),
            "user_message": safe_user,
            "response_preview": safe_preview,
            "error": safe_err,
            "timestamp": now,
        }
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO communication_logs (
                    request_id, response_id, session_id, user_message_id, assistant_message_id,
                    ui_handler, endpoint, http_status, provider, model, execution_status,
                    ui_state, response_time_ms, user_message, response_preview, error, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    response_id,
                    session_id,
                    user_message_id,
                    assistant_message_id,
                    ui_handler,
                    endpoint,
                    http_status,
                    provider,
                    model,
                    execution_status,
                    ui_state,
                    record["response_time_ms"],
                    safe_user,
                    safe_preview,
                    safe_err,
                    now,
                ),
            )
        try:
            jsonl_path = self.db_path.parent / "communication_audit.jsonl"
            with jsonl_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return record

    def list_communication_logs(
        self, session_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        with self._lock:
            if session_id:
                rows = self._conn.execute(
                    "SELECT * FROM communication_logs WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (session_id, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM communication_logs ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    # ── Tasks ────────────────────────────────────────────────────────────────

    def create_task(
        self,
        title: str,
        steps: list[dict[str, Any]],
        session_id: str | None = None,
        status: str = "QUEUED",
    ) -> dict[str, Any]:
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO tasks (task_id, session_id, title, status, steps_json, result_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, '{}', ?, ?)
                """,
                (task_id, session_id, title, status, json.dumps(steps), now, now),
            )
        return self.get_task(task_id)  # type: ignore[return-value]

    def update_task(
        self,
        task_id: str,
        status: str | None = None,
        steps: list[dict[str, Any]] | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any] | None:
        cur_task = self.get_task(task_id)
        if not cur_task:
            return None
        now = time.time()
        new_status = status if status is not None else cur_task["status"]
        new_steps = steps if steps is not None else cur_task["steps"]
        new_result = redact_secrets(result) if result is not None else cur_task["result"]
        new_error = error if error is not None else cur_task["error"]
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE tasks
                SET status = ?, steps_json = ?, result_json = ?, error = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (
                    new_status,
                    json.dumps(new_steps),
                    json.dumps(new_result),
                    new_error,
                    now,
                    task_id,
                ),
            )
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["steps"] = json.loads(d.pop("steps_json", "[]"))
            d["result"] = json.loads(d.pop("result_json", "{}"))
            return d

    def list_tasks(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM tasks ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["steps"] = json.loads(d.pop("steps_json", "[]"))
                d["result"] = json.loads(d.pop("result_json", "{}"))
                out.append(d)
            return out

    # ── Authorized Folders ───────────────────────────────────────────────────

    def add_authorized_folder(
        self, path: str | Path, label: str | None = None, access_mode: str = "READ_WRITE"
    ) -> dict[str, Any]:
        resolved = str(Path(path).expanduser().resolve())
        folder_id = f"fld-{uuid.uuid4().hex[:10]}"
        now = time.time()
        lbl = label or Path(resolved).name or resolved
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO authorized_folders (folder_id, path, label, access_mode, active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(path) DO UPDATE SET active = 1, access_mode = excluded.access_mode, label = excluded.label
                """,
                (folder_id, resolved, lbl, access_mode, now),
            )
            row = self._conn.execute(
                "SELECT * FROM authorized_folders WHERE path = ?", (resolved,)
            ).fetchone()
            return dict(row)

    def get_authorized_folder(self, folder_id_or_path: str) -> dict[str, Any] | None:
        raw = str(folder_id_or_path).strip()
        if not raw:
            return None
        resolved = str(Path(raw).expanduser().resolve()) if "/" in raw else raw
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM authorized_folders WHERE folder_id = ? OR path = ?",
                (raw, resolved),
            ).fetchone()
            return dict(row) if row else None

    def disconnect_authorized_folder(
        self,
        folder_id_or_path: str,
        *,
        in_use_folders: set[str] | None = None,
    ) -> dict[str, Any]:
        """Disconnect a Connected Folder by folder_id (or path) without deleting physical files."""
        rec = self.get_authorized_folder(folder_id_or_path)
        if rec is None:
            return {
                "ok": False,
                "disconnected": False,
                "status": "FOLDER_NOT_FOUND",
                "folder_id": str(folder_id_or_path),
                "reason": f"Folder '{folder_id_or_path}' tidak ditemukan dalam daftar Connected Folders.",
            }

        fid = str(rec["folder_id"])
        fpath = str(rec["path"])
        flabel = str(rec["label"])

        if not int(rec.get("active", 0)):
            return {
                "ok": False,
                "disconnected": False,
                "status": "ALREADY_DISCONNECTED",
                "folder_id": fid,
                "path": fpath,
                "label": flabel,
                "physical_files_intact": Path(fpath).exists(),
                "reason": f"Folder '{flabel}' ({fid}) sudah diputuskan sebelumnya.",
            }

        busy_set = in_use_folders or set()
        if fid in busy_set or fpath in busy_set:
            return {
                "ok": False,
                "disconnected": False,
                "status": "FOLDER_IN_USE",
                "folder_id": fid,
                "path": fpath,
                "label": flabel,
                "physical_files_intact": Path(fpath).exists(),
                "reason": (
                    f"Folder '{flabel}' sedang digunakan oleh proses aktif. "
                    "Tunggu proses selesai sebelum memutus koneksi folder agar operasi tetap konsisten."
                ),
            }

        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE authorized_folders SET active = 0 WHERE folder_id = ?",
                (fid,),
            )

        updated = self.get_authorized_folder(fid) or rec
        return {
            "ok": True,
            "disconnected": True,
            "status": "DISCONNECTED",
            "folder_id": fid,
            "path": fpath,
            "label": flabel,
            "access_mode": rec.get("access_mode", "READ_WRITE"),
            "active": int(updated.get("active", 0)),
            "physical_files_intact": Path(fpath).exists(),
            "notification": f"Koneksi folder '{flabel}' berhasil diputuskan dari NUI (berkas fisik di Mac tetap utuh).",
        }

    def reconnect_authorized_folder(
        self,
        folder_id_or_path: str,
        *,
        label: str | None = None,
        access_mode: str | None = None,
    ) -> dict[str, Any]:
        """Reconnect a previously disconnected folder by folder_id or path."""
        rec = self.get_authorized_folder(folder_id_or_path)
        if rec is not None:
            fid = str(rec["folder_id"])
            eff_label = label or str(rec["label"])
            eff_mode = access_mode or str(rec["access_mode"])
            with self._lock, self._conn:
                self._conn.execute(
                    "UPDATE authorized_folders SET active = 1, label = ?, access_mode = ? WHERE folder_id = ?",
                    (eff_label, eff_mode, fid),
                )
            updated = self.get_authorized_folder(fid) or rec
            updated["status"] = "RECONNECTED"
            updated["reconnected"] = True
            updated["notification"] = f"Folder '{eff_label}' berhasil dihubungkan kembali ke NUI ({eff_mode})."
            return updated

        if "/" in str(folder_id_or_path):
            added = self.add_authorized_folder(
                folder_id_or_path,
                label=label,
                access_mode=access_mode or "READ_WRITE",
            )
            added["status"] = "CONNECTED"
            added["reconnected"] = True
            added["notification"] = f"Folder '{added['label']}' berhasil dihubungkan ke NUI ({added['access_mode']})."
            return added

        return {
            "ok": False,
            "reconnected": False,
            "status": "FOLDER_NOT_FOUND",
            "folder_id": str(folder_id_or_path),
            "reason": f"Folder ID '{folder_id_or_path}' tidak ditemukan untuk dihubungkan kembali.",
        }

    def revoke_authorized_folder(self, path_or_id: str) -> bool:
        res = self.disconnect_authorized_folder(path_or_id)
        return bool(res.get("disconnected", False))

    def list_authorized_folders(self, active_only: bool = True) -> list[dict[str, Any]]:
        with self._lock:
            q = "SELECT * FROM authorized_folders"
            if active_only:
                q += " WHERE active = 1"
            q += " ORDER BY created_at ASC"
            return [dict(r) for r in self._conn.execute(q).fetchall()]

    # ── API Connectors (Secrets in Keychain, never plaintext in SQLite) ──────

    def register_api_connector(
        self,
        name: str,
        base_url: str,
        secret: str,
        auth_type: str = "BEARER",
        allowed_endpoints: list[str] | None = None,
    ) -> dict[str, Any]:
        connector_id = f"api-{uuid.uuid4().hex[:10]}"
        keychain_account = f"connector:{connector_id}"
        self.keychain.set_secret(keychain_account, secret)
        now = time.time()
        endpoints = allowed_endpoints or ["*"]
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO api_connectors (
                    connector_id, name, base_url, auth_type, keychain_account, allowed_endpoints_json, active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    connector_id,
                    name,
                    base_url,
                    auth_type,
                    keychain_account,
                    json.dumps(endpoints),
                    now,
                ),
            )
        return self.get_api_connector(connector_id)  # type: ignore[return-value]

    def get_api_connector(self, connector_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM api_connectors WHERE connector_id = ?", (connector_id,)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["allowed_endpoints"] = json.loads(d.pop("allowed_endpoints_json", '["*"]'))
            d["has_secret_in_keychain"] = (
                self.keychain.get_secret(d["keychain_account"]) is not None
            )
            return d

    def list_api_connectors(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM api_connectors ORDER BY created_at DESC"
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["allowed_endpoints"] = json.loads(
                    d.pop("allowed_endpoints_json", '["*"]')
                )
                d["has_secret_in_keychain"] = (
                    self.keychain.get_secret(d["keychain_account"]) is not None
                )
                out.append(d)
            return out

    # ── Separated Knowledge Base Buckets ─────────────────────────────────────

    VALID_KNOWLEDGE_BUCKETS = {
        "conversation_memory",
        "reference_docs",
        "project_knowledge",
    }

    def add_knowledge_item(
        self,
        bucket: str,
        title: str,
        content: str,
        source_path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if bucket not in self.VALID_KNOWLEDGE_BUCKETS:
            raise ValueError(
                f"Invalid knowledge bucket {bucket!r}; must be one of {sorted(self.VALID_KNOWLEDGE_BUCKETS)}"
            )
        item_id = f"kb-{uuid.uuid4().hex[:10]}"
        now = time.time()
        safe_meta = redact_secrets(metadata or {})
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO knowledge_items (item_id, bucket, title, source_path, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    bucket,
                    title,
                    source_path,
                    content,
                    json.dumps(safe_meta),
                    now,
                ),
            )
        return {
            "item_id": item_id,
            "bucket": bucket,
            "title": title,
            "source_path": source_path,
            "content": content,
            "metadata": safe_meta,
            "created_at": now,
        }

    def list_knowledge_items(
        self, bucket: str | None = None, query: str | None = None
    ) -> list[dict[str, Any]]:
        with self._lock:
            clauses = []
            params: list[Any] = []
            if bucket:
                clauses.append("bucket = ?")
                params.append(bucket)
            if query:
                clauses.append("(title LIKE ? OR content LIKE ?)")
                params.extend([f"%{query}%", f"%{query}%"])
            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            rows = self._conn.execute(
                f"SELECT * FROM knowledge_items {where_sql} ORDER BY created_at DESC",
                tuple(params),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d.pop("metadata_json", "{}"))
                out.append(d)
            return out

    # ── Audit Logging (Always Redacted) ──────────────────────────────────────

    def record_audit(
        self,
        *,
        user_request: str,
        tool_name: str,
        category: str,
        target: str,
        operation: str,
        approval_decision: str,
        status: str,
        result_summary: str,
        task_id: str | None = None,
        domain: str | None = None,
        file_changed: str | None = None,
        hardware_command: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        audit_id = f"aud-{uuid.uuid4().hex[:12]}"
        now = time.time()
        safe_req = str(redact_secrets(user_request))
        safe_target = str(redact_secrets(target))
        safe_summary = str(redact_secrets(result_summary))
        safe_meta = redact_secrets(metadata or {})
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO audit_logs (
                    audit_id, timestamp, user_request, task_id, tool_name, category, target,
                    operation, domain, file_changed, hardware_command, approval_decision,
                    status, result_summary, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    now,
                    safe_req,
                    task_id,
                    tool_name,
                    category,
                    safe_target,
                    operation,
                    domain,
                    file_changed,
                    hardware_command,
                    approval_decision,
                    status,
                    safe_summary,
                    json.dumps(safe_meta),
                ),
            )
        return {
            "audit_id": audit_id,
            "timestamp": now,
            "user_request": safe_req,
            "task_id": task_id,
            "tool_name": tool_name,
            "category": category,
            "target": safe_target,
            "operation": operation,
            "domain": domain,
            "file_changed": file_changed,
            "hardware_command": hardware_command,
            "approval_decision": approval_decision,
            "status": status,
            "result_summary": safe_summary,
            "metadata": safe_meta,
        }

    def list_audit_logs(
        self, limit: int = 100, category: str | None = None
    ) -> list[dict[str, Any]]:
        with self._lock:
            if category:
                rows = self._conn.execute(
                    "SELECT * FROM audit_logs WHERE category = ? ORDER BY timestamp DESC LIMIT ?",
                    (category, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d.pop("metadata_json", "{}"))
                out.append(d)
            return out
