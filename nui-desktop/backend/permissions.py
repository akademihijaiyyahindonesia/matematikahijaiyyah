"""Granular Permission & Authorization Engine for CosmicTera NUI Desktop.

Enforces Section 6 of the Project Implementation Directive:
- 15 Permission Categories:
  1. INTERNET_ACCESS
  2. WEB_SEARCH
  3. WEB_READING
  4. BROWSER_AUTOMATION
  5. WEB_CODING
  6. API_ACCESS
  7. FILE_DOWNLOAD
  8. FILE_UPLOAD
  9. LOCAL_FILES
  10. REPOSITORY
  11. TERMINAL
  12. CODE_EXECUTION
  13. ACCOUNT_ACCESS
  14. WEBSITE_EDITING
  15. DEPLOYMENT
- 6 Approval Modes / Decisions:
  - ALLOW_ONCE
  - ALLOW_SESSION
  - ALWAYS_ALLOW
  - ASK_EVERY_TIME
  - DENY
  - REVOKE_ACCESS
- Target Granularity:
  - Specific domain (`docs.python.org` does NOT grant `github.com`)
  - Specific folder path prefix (access to `/Users/AMRA/project-a` does NOT grant `/Users/AMRA/project-b`)
  - Specific repository
  - Specific API endpoint
  - Specific operation (`READ`, `WRITE`, `DELETE`, `EXEC`, `DEPLOY`, etc.)
  - Expiration time & Session scope
- Production `DEPLOYMENT` ALWAYS requires an explicit final confirmation even if general coding or repository rules exist.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .storage import NUIStorage, redact_secrets

PERMISSION_CATEGORIES: dict[str, dict[str, str]] = {
    "INTERNET_ACCESS": {
        "label": "Internet Access",
        "description": "Izinkan aplikasi terhubung ke internet eksternal.",
        "default_risk": "MEDIUM",
    },
    "WEB_SEARCH": {
        "label": "Web Search",
        "description": "Izinkan pencarian informasi melalui mesin pencari web.",
        "default_risk": "LOW",
    },
    "WEB_READING": {
        "label": "Web Reading",
        "description": "Izinkan membuka dan membaca halaman web publik.",
        "default_risk": "LOW",
    },
    "BROWSER_AUTOMATION": {
        "label": "Browser Automation",
        "description": "Izinkan klik, pengisian form, dan navigasi otomatis di browser terintegrasi.",
        "default_risk": "HIGH",
    },
    "WEB_CODING": {
        "label": "Web Coding",
        "description": "Izinkan membuat, mengedit, dan menjalankan preview website lokal.",
        "default_risk": "MEDIUM",
    },
    "API_ACCESS": {
        "label": "API Access",
        "description": "Izinkan pemanggilan API eksternal dengan kredensial pengguna.",
        "default_risk": "HIGH",
    },
    "FILE_DOWNLOAD": {
        "label": "File Download",
        "description": "Izinkan mengunduh berkas dari internet ke folder lokal.",
        "default_risk": "MEDIUM",
    },
    "FILE_UPLOAD": {
        "label": "File Upload",
        "description": "Izinkan mengunggah berkas lokal ke layanan web atau API eksternal.",
        "default_risk": "HIGH",
    },
    "LOCAL_FILES": {
        "label": "Local Files",
        "description": "Izinkan membaca, membuat, mengubah, atau menghapus berkas di folder lokal.",
        "default_risk": "MEDIUM",
    },
    "REPOSITORY": {
        "label": "Repository",
        "description": "Izinkan membaca, memodifikasi, atau melakukan operasi git pada repositori kode.",
        "default_risk": "MEDIUM",
    },
    "TERMINAL": {
        "label": "Terminal",
        "description": "Izinkan menjalankan perintah shell/terminal di mesin lokal.",
        "default_risk": "HIGH",
    },
    "CODE_EXECUTION": {
        "label": "Code Execution",
        "description": "Izinkan menjalankan skrip Python, H-ISA, compiler, atau test runner.",
        "default_risk": "MEDIUM",
    },
    "ACCOUNT_ACCESS": {
        "label": "Account Access",
        "description": "Izinkan sesi login atau akses akun melalui browser/token pengguna.",
        "default_risk": "CRITICAL",
    },
    "WEBSITE_EDITING": {
        "label": "Website Editing",
        "description": "Izinkan mengubah proyek website atau CMS milik pengguna.",
        "default_risk": "HIGH",
    },
    "DEPLOYMENT": {
        "label": "Deployment",
        "description": "Izinkan build dan publikasi/deploy ke server atau produksi (wajib persetujuan final terpisah).",
        "default_risk": "CRITICAL",
    },
    # Phase 12 Internet, Dependency & Remote VPS Permission Scopes (Part H)
    "INTERNET_SEARCH": {
        "label": "Internet Search",
        "description": "Izinkan NUI mencari informasi teknis dan dokumentasi melalui provider pencarian internet.",
        "default_risk": "LOW",
    },
    "WEBSITE_ACCESS": {
        "label": "Website Access",
        "description": "Izinkan membuka dan menjelajahi situs internet nyata di Browser NUI.",
        "default_risk": "LOW",
    },
    "URL_FETCH": {
        "label": "URL Fetch",
        "description": "Izinkan mengambil halaman atau dokumentasi teknis dari URL eksternal.",
        "default_risk": "LOW",
    },
    "DEPENDENCY_INSTALL": {
        "label": "Dependency Install",
        "description": "Izinkan instalasi paket/dependency (pip, uv, npm, pnpm, yarn, cargo, brew) ke workspace/venv.",
        "default_risk": "HIGH",
    },
    "GIT_REMOTE_ACCESS": {
        "label": "Git Remote Access",
        "description": "Izinkan operasi Git jarak jauh (clone, fetch, pull, push) ke repositori remote.",
        "default_risk": "MEDIUM",
    },
    "VPS_CONNECT": {
        "label": "VPS Connect",
        "description": "Izinkan membuka koneksi SSH/SFTP terverifikasi ke server VPS pengguna.",
        "default_risk": "HIGH",
    },
    "VPS_READ": {
        "label": "VPS Read",
        "description": "Izinkan membaca direktori, berkas sumber, dan status sistem pada workspace VPS.",
        "default_risk": "MEDIUM",
    },
    "VPS_WRITE": {
        "label": "VPS Write",
        "description": "Izinkan menulis atau mengedit kode di dalam remote workspace VPS yang diotorisasi.",
        "default_risk": "HIGH",
    },
    "VPS_EXECUTE": {
        "label": "VPS Execute",
        "description": "Izinkan menjalankan build, dependency install, dan pengujian (test) pada server VPS.",
        "default_risk": "HIGH",
    },
    "VPS_DEPLOY": {
        "label": "VPS Deploy",
        "description": "Izinkan menjalankan workflow deployment pada server VPS (wajib persetujuan eksplisit).",
        "default_risk": "CRITICAL",
    },
    # Phase 8 Explicit Operational Permission Scopes (Real Internet, VPS, Domain & File Sync)
    "READ_LOCAL": {
        "label": "Read Local",
        "description": "Izinkan membaca berkas dan manifest direktori lokal untuk pemeriksaan.",
        "default_risk": "LOW",
    },
    "READ_REMOTE": {
        "label": "Read Remote",
        "description": "Izinkan membaca direktori dan manifest berkas pada remote workspace VPS.",
        "default_risk": "LOW",
    },
    "NETWORK_ACCESS": {
        "label": "Network Access",
        "description": "Izinkan diagnostik jaringan keluar (DNS, TCP, HTTP/HTTPS, TLS).",
        "default_risk": "LOW",
    },
    "SSH_CONNECT": {
        "label": "SSH Connect",
        "description": "Izinkan pengujian dan pembukaan sesi koneksi SSH terverifikasi.",
        "default_risk": "MEDIUM",
    },
    "SFTP_ACCESS": {
        "label": "SFTP Access",
        "description": "Izinkan inspeksi dan pembacaan berkas melalui SFTP pada remote workspace.",
        "default_risk": "MEDIUM",
    },
    "REMOTE_COMMAND": {
        "label": "Remote Command",
        "description": "Izinkan eksekusi perintah non-destruktif terbatas pada server remote.",
        "default_risk": "HIGH",
    },
    "UPLOAD_FILE": {
        "label": "Upload File",
        "description": "Izinkan mengunggah berkas lokal ke server VPS (memerlukan izin terpisah dari pemeriksaan status).",
        "default_risk": "HIGH",
    },
    "DOWNLOAD_FILE": {
        "label": "Download File",
        "description": "Izinkan mengunduh berkas ke area staging lokal yang terisolasi.",
        "default_risk": "MEDIUM",
    },
    "SYNC_DIRECTORY": {
        "label": "Sync Directory",
        "description": "Izinkan sinkronisasi direktori lokal dengan remote workspace VPS (rsync/SFTP).",
        "default_risk": "HIGH",
    },
    "MODIFY_REMOTE": {
        "label": "Modify Remote",
        "description": "Izinkan memodifikasi berkas atau konfigurasi di dalam remote workspace.",
        "default_risk": "HIGH",
    },
    "DEPLOY_WEBSITE": {
        "label": "Deploy Website",
        "description": "Izinkan menjalankan proses deploy website ke produksi (wajib persetujuan final eksplisit).",
        "default_risk": "CRITICAL",
    },
}

APPROVAL_DECISIONS = {
    "READ_ONLY",
    "ALLOW_ONCE",
    "ALLOW_SESSION",
    "ALWAYS_ALLOW",
    "ASK_EVERY_TIME",
    "DENY",
    "REVOKE_ACCESS",
}

READ_SAFE_OPERATIONS = {
    "READ",
    "LIST",
    "SEARCH",
    "STATUS",
    "DIFF",
    "LOG",
    "INSPECT",
    "DIAGNOSE",
    "CHECK_DOMAIN",
    "COMPARE_MANIFEST",
}

OUTBOUND_NETWORK_CATEGORIES = {
    "INTERNET_ACCESS",
    "NETWORK_ACCESS",
    "WEB_SEARCH",
    "INTERNET_SEARCH",
    "WEB_READING",
    "WEBSITE_ACCESS",
    "URL_FETCH",
    "BROWSER_AUTOMATION",
    "API_ACCESS",
    "FILE_DOWNLOAD",
    "DOWNLOAD_FILE",
    "FILE_UPLOAD",
    "UPLOAD_FILE",
    "DEPENDENCY_INSTALL",
    "GIT_REMOTE_ACCESS",
    "VPS_CONNECT",
    "SSH_CONNECT",
    "SFTP_ACCESS",
    "READ_REMOTE",
    "VPS_READ",
    "VPS_WRITE",
    "MODIFY_REMOTE",
    "SYNC_DIRECTORY",
    "VPS_EXECUTE",
    "REMOTE_COMMAND",
    "VPS_DEPLOY",
    "DEPLOY_WEBSITE",
    "DEPLOYMENT",
}


@dataclass(frozen=True)
class PermissionCheckResult:
    allowed: bool
    status: str  # "ALLOWED", "DENIED", "WAITING_FOR_APPROVAL"
    decision_source: str
    category: str
    operation: str
    target_type: str
    target_value: str
    risk_level: str
    reason: str
    request_id: str | None = None
    rule_id: str | None = None


def normalize_domain(url_or_domain: str) -> str:
    val = url_or_domain.strip().lower()
    if "://" in val:
        parsed = urlparse(val)
        return (parsed.hostname or val).lower()
    return val.split("/")[0].split(":")[0].lower()


def normalize_path_str(path_val: str) -> str:
    try:
        return str(Path(path_val).expanduser().resolve())
    except Exception:
        return path_val


class PermissionEngine:
    """Evaluates and records granular permissions with fail-closed default."""

    def __init__(self, storage: NUIStorage) -> None:
        self.storage = storage
        # Track one-time grants by (category, target_type, target_value, operation)
        self._allow_once_tokens: dict[tuple[str, str, str, str], int] = {}

    def check_or_request(
        self,
        *,
        category: str,
        operation: str,
        target_type: str,
        target_value: str,
        reason: str,
        session_id: str | None = None,
        task_id: str | None = None,
        risk_level: str | None = None,
        payload: dict[str, Any] | None = None,
        explicit_final_deploy_confirmed: bool = False,
    ) -> PermissionCheckResult:
        if category not in PERMISSION_CATEGORIES:
            return PermissionCheckResult(
                allowed=False,
                status="DENIED",
                decision_source="INVALID_CATEGORY",
                category=category,
                operation=operation,
                target_type=target_type,
                target_value=target_value,
                risk_level="CRITICAL",
                reason=f"Unknown permission category: {category}",
            )

        eff_risk = risk_level or PERMISSION_CATEGORIES[category]["default_risk"]
        norm_target = self._normalize_target(target_type, target_value)

        # Operating mode guard: in LOCAL mode, block all external internet/web/API/upload/download/VPS
        op_mode = self.storage.get_setting("operating_mode", "HYBRID")
        if op_mode == "LOCAL" and category in OUTBOUND_NETWORK_CATEGORIES:
            return PermissionCheckResult(
                allowed=False,
                status="DENIED",
                decision_source="OPERATING_MODE_LOCAL_LOCK",
                category=category,
                operation=operation,
                target_type=target_type,
                target_value=norm_target,
                risk_level=eff_risk,
                reason="Ditolak otomatis karena sistem berada dalam mode LOCAL (offline).",
            )

        # Production / VPS deployment rule: Always requires separate explicit confirmation
        if category in {"DEPLOYMENT", "VPS_DEPLOY", "DEPLOY_WEBSITE"} and not explicit_final_deploy_confirmed:
            req = self._create_pending_approval(
                session_id=session_id,
                task_id=task_id,
                category=category,
                operation=operation,
                target_type=target_type,
                target_value=norm_target,
                risk_level="CRITICAL",
                reason=f"[FINAL DEPLOYMENT APPROVAL REQUIRED] {reason}",
                payload=payload or {},
            )
            return PermissionCheckResult(
                allowed=False,
                status="WAITING_FOR_APPROVAL",
                decision_source="DEPLOYMENT_FINAL_GATE",
                category=category,
                operation=operation,
                target_type=target_type,
                target_value=norm_target,
                risk_level="CRITICAL",
                reason="Deploy ke produksi/VPS memerlukan persetujuan final terpisah dari pengguna.",
                request_id=req["request_id"],
            )

        # Check one-time token first (`ALLOW_ONCE`)
        once_key = (category, target_type, norm_target, operation)
        wildcard_once_key = (category, target_type, norm_target, "*")
        if self._allow_once_tokens.get(once_key, 0) > 0:
            self._allow_once_tokens[once_key] -= 1
            return PermissionCheckResult(
                allowed=True,
                status="ALLOWED",
                decision_source="ALLOW_ONCE",
                category=category,
                operation=operation,
                target_type=target_type,
                target_value=norm_target,
                risk_level=eff_risk,
                reason="Diizinkan satu kali (ALLOW ONCE).",
            )
        if self._allow_once_tokens.get(wildcard_once_key, 0) > 0:
            self._allow_once_tokens[wildcard_once_key] -= 1
            return PermissionCheckResult(
                allowed=True,
                status="ALLOWED",
                decision_source="ALLOW_ONCE",
                category=category,
                operation=operation,
                target_type=target_type,
                target_value=norm_target,
                risk_level=eff_risk,
                reason="Diizinkan satu kali (ALLOW ONCE).",
            )

        # Check stored rules in SQLite
        matched_rule = self._find_matching_rule(
            category=category,
            target_type=target_type,
            target_value=norm_target,
            operation=operation,
            session_id=session_id,
        )

        if matched_rule is not None:
            dec = matched_rule["decision"]
            if dec == "DENY":
                return PermissionCheckResult(
                    allowed=False,
                    status="DENIED",
                    decision_source="RULE_DENY",
                    category=category,
                    operation=operation,
                    target_type=target_type,
                    target_value=norm_target,
                    risk_level=eff_risk,
                    reason=f"Ditolak oleh aturan izin untuk {norm_target}.",
                    rule_id=matched_rule["rule_id"],
                )
            if dec == "READ_ONLY":
                if operation.upper() in READ_SAFE_OPERATIONS:
                    return PermissionCheckResult(
                        allowed=True,
                        status="ALLOWED",
                        decision_source="READ_ONLY",
                        category=category,
                        operation=operation,
                        target_type=target_type,
                        target_value=norm_target,
                        risk_level="LOW",
                        reason=f"Diizinkan oleh mode READ_ONLY untuk operasi baca ({operation}).",
                        rule_id=matched_rule["rule_id"],
                    )
                return PermissionCheckResult(
                    allowed=False,
                    status="DENIED",
                    decision_source="RULE_READ_ONLY",
                    category=category,
                    operation=operation,
                    target_type=target_type,
                    target_value=norm_target,
                    risk_level=eff_risk,
                    reason=f"Ditolak oleh mode READ_ONLY: operasi mutasi/eksekusi ({operation}) tidak diizinkan pada {norm_target}.",
                    rule_id=matched_rule["rule_id"],
                )
            if dec in {"ALWAYS_ALLOW", "ALLOW_SESSION"}:
                return PermissionCheckResult(
                    allowed=True,
                    status="ALLOWED",
                    decision_source=dec,
                    category=category,
                    operation=operation,
                    target_type=target_type,
                    target_value=norm_target,
                    risk_level=eff_risk,
                    reason=f"Diizinkan oleh aturan {dec} ({matched_rule['target_value']}).",
                    rule_id=matched_rule["rule_id"],
                )
            # If dec == "ASK_EVERY_TIME", fall through to pending approval creation

        # Phase 8 Rule: Read-only network/domain/status checks (`NETWORK_ACCESS` with READ_SAFE_OPERATIONS) are allowed in HYBRID/ONLINE unless explicitly denied
        if category == "NETWORK_ACCESS" and operation.upper() in READ_SAFE_OPERATIONS:
            return PermissionCheckResult(
                allowed=True,
                status="ALLOWED",
                decision_source="DIAGNOSTIC_NETWORK_READ",
                category=category,
                operation=operation,
                target_type=target_type,
                target_value=norm_target,
                risk_level="LOW",
                reason="Pemeriksaan diagnostik jaringan/domain read-only diizinkan tanpa memerlukan izin upload/mutasi.",
            )

        # For LOCAL_FILES / READ_LOCAL / REPOSITORY, check if path is inside an active authorized_folder
        # Note: Destructive operations (DELETE, OVERWRITE_CRITICAL) still require confirmation unless explicitly allowed by a rule
        if (
            category in {"LOCAL_FILES", "READ_LOCAL", "REPOSITORY"}
            and target_type in {"path", "folder", "repository"}
            and operation.upper() in READ_SAFE_OPERATIONS
        ):
            if self._is_within_authorized_folder(norm_target, require_write=False):
                return PermissionCheckResult(
                    allowed=True,
                    status="ALLOWED",
                    decision_source="AUTHORIZED_FOLDER_READ",
                    category=category,
                    operation=operation,
                    target_type=target_type,
                    target_value=norm_target,
                    risk_level="LOW",
                    reason="Lokasi berada di dalam folder yang telah diotorisasi pengguna (akses baca).",
                )

        if (
            category in {"LOCAL_FILES", "REPOSITORY", "WEB_CODING", "CODE_EXECUTION"}
            and target_type in {"path", "folder", "repository"}
            and operation in {"CREATE", "WRITE", "EDIT", "RENAME", "SCAFFOLD_WEBSITE", "RUN_TESTS", "EXEC"}
        ):
            if self._is_within_authorized_folder(norm_target, require_write=True):
                return PermissionCheckResult(
                    allowed=True,
                    status="ALLOWED",
                    decision_source="AUTHORIZED_FOLDER_WRITE",
                    category=category,
                    operation=operation,
                    target_type=target_type,
                    target_value=norm_target,
                    risk_level="MEDIUM",
                    reason="Lokasi berada di dalam folder READ_WRITE yang telah diotorisasi pengguna.",
                )

        # Otherwise create a pending approval request (`WAITING_FOR_APPROVAL`)
        req = self._create_pending_approval(
            session_id=session_id,
            task_id=task_id,
            category=category,
            operation=operation,
            target_type=target_type,
            target_value=norm_target,
            risk_level=eff_risk,
            reason=reason,
            payload=payload or {},
        )
        return PermissionCheckResult(
            allowed=False,
            status="WAITING_FOR_APPROVAL",
            decision_source="ASK_USER",
            category=category,
            operation=operation,
            target_type=target_type,
            target_value=norm_target,
            risk_level=eff_risk,
            reason=f"Membutuhkan persetujuan pengguna: {reason}",
            request_id=req["request_id"],
        )

    def decide_request(
        self,
        request_id: str,
        decision: str,
        expires_in_seconds: float | None = None,
    ) -> dict[str, Any]:
        if decision not in APPROVAL_DECISIONS:
            raise ValueError(f"Invalid decision {decision!r}; must be in {sorted(APPROVAL_DECISIONS)}")

        req = self.get_pending_approval(request_id)
        if not req:
            raise KeyError(f"Approval request {request_id!r} not found")

        now = time.time()
        with self.storage._lock, self.storage._conn:
            self.storage._conn.execute(
                """
                UPDATE pending_approvals
                SET status = ?, decision = ?, decided_at = ?
                WHERE request_id = ?
                """,
                (
                    "REJECTED" if decision in {"DENY", "REVOKE_ACCESS"} else "APPROVED",
                    decision,
                    now,
                    request_id,
                ),
            )

        category = req["category"]
        target_type = req["target_type"]
        target_value = req["target_value"]
        operation = req["operation"]
        session_id = req["session_id"]

        if decision == "ALLOW_ONCE":
            key = (category, target_type, target_value, operation)
            self._allow_once_tokens[key] = self._allow_once_tokens.get(key, 0) + 1
            return {
                "request_id": request_id,
                "decision": decision,
                "status": "APPROVED_ONCE",
                "target_value": target_value,
            }

        if decision == "REVOKE_ACCESS":
            self.revoke_Matching_rules(
                category=category,
                target_type=target_type,
                target_value=target_value,
            )
            return {
                "request_id": request_id,
                "decision": decision,
                "status": "REVOKED",
                "target_value": target_value,
            }

        # Create or update rule for ALLOW_SESSION, ALWAYS_ALLOW, ASK_EVERY_TIME, DENY
        expires_at = (now + expires_in_seconds) if expires_in_seconds else None
        rule = self.set_rule(
            category=category,
            target_type=target_type,
            target_value=target_value,
            operation=operation,
            decision=decision,
            session_id=session_id if decision == "ALLOW_SESSION" else None,
            expires_at=expires_at,
        )
        return {
            "request_id": request_id,
            "decision": decision,
            "status": "RULE_SAVED",
            "rule": rule,
        }

    def set_rule(
        self,
        *,
        category: str,
        target_type: str,
        target_value: str,
        operation: str = "*",
        decision: str,
        session_id: str | None = None,
        expires_at: float | None = None,
    ) -> dict[str, Any]:
        if category not in PERMISSION_CATEGORIES:
            raise ValueError(f"Unknown category {category!r}")
        if decision not in APPROVAL_DECISIONS:
            raise ValueError(f"Unknown decision {decision!r}")

        norm_target = self._normalize_target(target_type, target_value)
        now = time.time()

        if decision == "ALLOW_ONCE":
            key = (category, target_type, norm_target, operation)
            self._allow_once_tokens[key] = self._allow_once_tokens.get(key, 0) + 1
            return {
                "rule_id": f"once-{uuid.uuid4().hex[:8]}",
                "category": category,
                "target_type": target_type,
                "target_value": norm_target,
                "operation": operation,
                "decision": "ALLOW_ONCE",
                "active": 1,
            }

        if decision == "REVOKE_ACCESS":
            self.revoke_Matching_rules(
                category=category,
                target_type=target_type,
                target_value=norm_target,
            )
            return {
                "rule_id": "revoked",
                "category": category,
                "target_type": target_type,
                "target_value": norm_target,
                "operation": operation,
                "decision": "REVOKE_ACCESS",
                "active": 0,
            }

        rule_id = f"rule-{uuid.uuid4().hex[:10]}"
        with self.storage._lock, self.storage._conn:
            # Deactivate conflicting active rules for the exact same scope
            self.storage._conn.execute(
                """
                UPDATE permission_rules
                SET active = 0, updated_at = ?
                WHERE category = ? AND target_type = ? AND target_value = ? AND operation = ? AND active = 1
                """,
                (now, category, target_type, norm_target, operation),
            )
            self.storage._conn.execute(
                """
                INSERT INTO permission_rules (
                    rule_id, category, target_type, target_value, operation, decision,
                    session_id, expires_at, active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    rule_id,
                    category,
                    target_type,
                    norm_target,
                    operation,
                    decision,
                    session_id,
                    expires_at,
                    now,
                    now,
                ),
            )
            row = self.storage._conn.execute(
                "SELECT * FROM permission_rules WHERE rule_id = ?", (rule_id,)
            ).fetchone()
            return dict(row)

    def revoke_rule(self, rule_id: str) -> bool:
        now = time.time()
        with self.storage._lock, self.storage._conn:
            cur = self.storage._conn.execute(
                "UPDATE permission_rules SET active = 0, updated_at = ? WHERE rule_id = ?",
                (now, rule_id),
            )
            return cur.rowcount > 0

    def revoke_Matching_rules(
        self,
        *,
        category: str,
        target_type: str,
        target_value: str,
    ) -> int:
        norm_target = self._normalize_target(target_type, target_value)
        now = time.time()
        # Clear any allow-once tokens too
        to_delete = [
            k
            for k in self._allow_once_tokens
            if k[0] == category and k[1] == target_type and k[2] == norm_target
        ]
        for k in to_delete:
            self._allow_once_tokens.pop(k, None)

        with self.storage._lock, self.storage._conn:
            cur = self.storage._conn.execute(
                """
                UPDATE permission_rules
                SET active = 0, updated_at = ?
                WHERE category = ? AND target_type = ? AND target_value = ? AND active = 1
                """,
                (now, category, target_type, norm_target),
            )
            return cur.rowcount

    def revoke_folder_permissions(self, folder_path: str) -> int:
        """Revoke all active permission rules and one-time tokens targeting a disconnected folder or its children."""
        norm_folder = normalize_path_str(folder_path)
        prefix = norm_folder.rstrip("/") + "/"
        now = time.time()
        to_delete = [
            k
            for k in self._allow_once_tokens
            if k[2] == norm_folder or k[2].startswith(prefix)
        ]
        for k in to_delete:
            self._allow_once_tokens.pop(k, None)

        with self.storage._lock, self.storage._conn:
            cur = self.storage._conn.execute(
                """
                UPDATE permission_rules
                SET active = 0, updated_at = ?
                WHERE active = 1 AND (target_value = ? OR target_value LIKE ?)
                """,
                (now, norm_folder, prefix + "%"),
            )
            return cur.rowcount + len(to_delete)

    def list_rules(self, active_only: bool = True) -> list[dict[str, Any]]:
        with self.storage._lock:
            q = "SELECT * FROM permission_rules"
            if active_only:
                q += " WHERE active = 1"
            q += " ORDER BY updated_at DESC"
            return [dict(r) for r in self.storage._conn.execute(q).fetchall()]

    def list_pending_approvals(self, status: str = "PENDING") -> list[dict[str, Any]]:
        with self.storage._lock:
            rows = self.storage._conn.execute(
                "SELECT * FROM pending_approvals WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["payload"] = json.loads(d.pop("payload_json", "{}"))
                out.append(d)
            return out

    def get_pending_approval(self, request_id: str) -> dict[str, Any] | None:
        with self.storage._lock:
            row = self.storage._conn.execute(
                "SELECT * FROM pending_approvals WHERE request_id = ?", (request_id,)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["payload"] = json.loads(d.pop("payload_json", "{}"))
            return d

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _normalize_target(self, target_type: str, target_value: str) -> str:
        if target_type == "domain":
            return normalize_domain(target_value)
        if target_type in {"path", "folder", "repository"}:
            return normalize_path_str(target_value)
        return target_value.strip()

    def _is_within_authorized_folder(
        self, norm_path: str, require_write: bool = False
    ) -> bool:
        try:
            target_p = Path(norm_path).resolve()
        except Exception:
            return False

        for fld in self.storage.list_authorized_folders(active_only=True):
            if require_write and fld["access_mode"] == "READ_ONLY":
                continue
            try:
                fld_p = Path(fld["path"]).resolve()
                if target_p == fld_p or fld_p in target_p.parents:
                    return True
            except Exception:
                continue
        return False

    def _find_matching_rule(
        self,
        *,
        category: str,
        target_type: str,
        target_value: str,
        operation: str,
        session_id: str | None,
    ) -> dict[str, Any] | None:
        now = time.time()
        rules = self.list_rules(active_only=True)
        for r in rules:
            if r["category"] != category:
                continue
            if r["target_type"] != target_type:
                continue
            if r["expires_at"] is not None and float(r["expires_at"]) < now:
                continue
            if r["decision"] == "ALLOW_SESSION" and r["session_id"] != session_id:
                continue
            if r["operation"] not in {"*", operation}:
                continue
            if self._target_matches(
                target_type, rule_target=r["target_value"], actual_target=target_value
            ):
                return r
        return None

    @staticmethod
    def _target_matches(
        target_type: str, rule_target: str, actual_target: str
    ) -> bool:
        if rule_target == "*":
            return True
        if target_type == "domain":
            # Exact domain match or subdomain of rule_target (never cross-domain!)
            r_dom = normalize_domain(rule_target)
            a_dom = normalize_domain(actual_target)
            return a_dom == r_dom or a_dom.endswith("." + r_dom)
        if target_type in {"path", "folder", "repository"}:
            try:
                r_p = Path(rule_target).resolve()
                a_p = Path(actual_target).resolve()
                return a_p == r_p or r_p in a_p.parents
            except Exception:
                return rule_target == actual_target
        return rule_target == actual_target

    def _create_pending_approval(
        self,
        *,
        session_id: str | None,
        task_id: str | None,
        category: str,
        operation: str,
        target_type: str,
        target_value: str,
        risk_level: str,
        reason: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        request_id = f"req-{uuid.uuid4().hex[:12]}"
        now = time.time()
        safe_payload = redact_secrets(payload)
        with self.storage._lock, self.storage._conn:
            self.storage._conn.execute(
                """
                INSERT INTO pending_approvals (
                    request_id, session_id, task_id, category, operation,
                    target_type, target_value, risk_level, reason, payload_json,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
                """,
                (
                    request_id,
                    session_id,
                    task_id,
                    category,
                    operation,
                    target_type,
                    target_value,
                    risk_level,
                    reason,
                    json.dumps(safe_payload),
                    now,
                ),
            )
        return self.get_pending_approval(request_id)  # type: ignore[return-value]
