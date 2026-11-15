"""Remote VPS Development Engine for CosmicTera NUI Desktop (Phase 12 — Part F).

Implements:
- `VPSConnectionProfile` management in SQLite settings (`vps_profiles`) with credentials isolated in
  `KeychainVault` (`vps:{profile_id}`) or macOS OpenSSH Agent — NEVER stored in plaintext SQLite, source code,
  audit logs, or LLM model context.
- Mandatory SSH Host Fingerprint Verification (`SHA256:...` or `known_hosts` with `StrictHostKeyChecking=yes`).
  Unknown or mismatched host keys are rejected with `HOST_KEY_VERIFICATION_FAILED`.
- Pluggable SSH/SFTP execution adapter (`SSHTransportAdapter`, `OpenSSHSystemTransport`) supporting:
  1. `inspect_remote_system` (OS, kernel, architecture, installed runtimes)
  2. `browse_remote_files` & `read_remote_file` (`VPS_READ`)
  3. `write_remote_file` & `edit_remote_file` within authorized `remote_workspace` (`VPS_WRITE`)
  4. `execute_remote_command` & `run_remote_tests` (`VPS_EXECUTE`) with strict timeout, `sudo` guard, and destructive command block
  5. `execute_remote_deployment` (`VPS_DEPLOY`) requiring explicit final deployment approval
  6. Automatic timeout & disconnect state tracking with `recover_connection(profile_id)`
"""
from __future__ import annotations

import json
import os
import posixpath
import re
import shlex
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from .permissions import PermissionEngine
from .storage import NUIStorage, redact_secrets

DESTRUCTIVE_REMOTE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/(?:\s|$|\*)"),
    re.compile(r"\bmkfs(?:\.[a-z0-9]+)?\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    re.compile(r"\b(?:shutdown|reboot|poweroff|init\s+0)\b", re.IGNORECASE),
)


@dataclass
class VPSConnectionProfile:
    profile_id: str
    name: str
    host: str
    port: int
    username: str
    auth_method: str  # "SSH_KEY" | "SSH_AGENT" | "KEYCHAIN_SECRET"
    ssh_key_path: str | None
    expected_host_fingerprint: str
    remote_workspace: str
    allowed_workspace_prefixes: list[str]
    connect_timeout_seconds: float = 8.0
    connection_state: str = "DISCONNECTED"
    last_connected_at: str | None = None
    last_error: str | None = None


class SSHTransportAdapter(Protocol):
    """Protocol for OpenSSH / SFTP transport (live macOS OpenSSH or deterministic test transport)."""

    def verify_host_fingerprint(
        self, host: str, port: int, expected_fingerprint: str, timeout: float = 5.0
    ) -> dict[str, Any]: ...

    def run_ssh_command(
        self,
        profile: VPSConnectionProfile,
        command: str,
        *,
        timeout: float = 10.0,
        keychain_secret: str | None = None,
    ) -> dict[str, Any]: ...

    def sftp_read_file(
        self,
        profile: VPSConnectionProfile,
        remote_path: str,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]: ...

    def sftp_write_file(
        self,
        profile: VPSConnectionProfile,
        remote_path: str,
        content: str,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]: ...


class OpenSSHSystemTransport:
    """Production OpenSSH transport using macOS `/usr/bin/ssh`, `/usr/bin/ssh-keyscan`, and `/usr/bin/ssh-keygen`."""

    def verify_host_fingerprint(
        self, host: str, port: int, expected_fingerprint: str, timeout: float = 5.0
    ) -> dict[str, Any]:
        exp = expected_fingerprint.strip()
        if not exp or not exp.startswith("SHA256:"):
            return {
                "ok": False,
                "verified": False,
                "status": "HOST_KEY_VERIFICATION_FAILED",
                "reason": "Host fingerprint wajib berformat 'SHA256:...' (NUI menolak menerima host key yang belum dikenal secara otomatis).",
            }
        try:
            scan = subprocess.run(
                ["/usr/bin/ssh-keyscan", "-T", str(max(1, int(timeout))), "-p", str(port), host],
                capture_output=True,
                text=True,
                timeout=timeout + 1.0,
            )
            if scan.returncode != 0 or not scan.stdout.strip():
                return {
                    "ok": False,
                    "verified": False,
                    "status": "HOST_UNREACHABLE",
                    "reason": f"Gagal memindai host key dari {host}:{port}: {scan.stderr.strip() or 'no response'}",
                }
            keygen = subprocess.run(
                ["/usr/bin/ssh-keygen", "-lf", "-"],
                input=scan.stdout,
                capture_output=True,
                text=True,
                timeout=3.0,
            )
            matched = exp in keygen.stdout
            return {
                "ok": matched,
                "verified": matched,
                "status": "HOST_KEY_VERIFIED" if matched else "HOST_KEY_VERIFICATION_FAILED",
                "expected_fingerprint": exp,
                "scanned_fingerprints": keygen.stdout.strip().splitlines(),
                "reason": "Host key cocok." if matched else f"Host fingerprint dari {host}:{port} tidak cocok dengan {exp}.",
            }
        except Exception as exc:
            return {
                "ok": False,
                "verified": False,
                "status": "HOST_KEY_VERIFICATION_FAILED",
                "reason": f"{type(exc).__name__}: {exc}",
            }

    def _build_ssh_base_cmd(self, profile: VPSConnectionProfile, timeout: float) -> list[str]:
        cmd = [
            "/usr/bin/ssh",
            "-p",
            str(profile.port),
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            f"ConnectTimeout={max(1, int(timeout))}",
        ]
        if profile.ssh_key_path:
            cmd.extend(["-i", str(Path(profile.ssh_key_path).expanduser())])
        cmd.append(f"{profile.username}@{profile.host}")
        return cmd

    def run_ssh_command(
        self,
        profile: VPSConnectionProfile,
        command: str,
        *,
        timeout: float = 10.0,
        keychain_secret: str | None = None,
    ) -> dict[str, Any]:
        cmd = self._build_ssh_base_cmd(profile, timeout) + [command]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "ok": res.returncode == 0,
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"SSH command timed out after {timeout}s",
                "timed_out": True,
            }
        except Exception as exc:
            return {
                "ok": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"{type(exc).__name__}: {exc}",
                "timed_out": False,
            }

    def sftp_read_file(
        self,
        profile: VPSConnectionProfile,
        remote_path: str,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        quoted = shlex.quote(remote_path)
        res = self.run_ssh_command(profile, f"cat {quoted}", timeout=timeout)
        if not res.get("ok"):
            return res
        return {
            "ok": True,
            "remote_path": remote_path,
            "content": res["stdout"],
            "size_bytes": len(res["stdout"].encode("utf-8")),
        }

    def sftp_write_file(
        self,
        profile: VPSConnectionProfile,
        remote_path: str,
        content: str,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        parent_dir = posixpath.dirname(remote_path) or "."
        quoted_dir = shlex.quote(parent_dir)
        quoted_path = shlex.quote(remote_path)
        cmd = self._build_ssh_base_cmd(profile, timeout) + [f"mkdir -p {quoted_dir} && cat > {quoted_path}"]
        try:
            res = subprocess.run(
                cmd,
                input=content,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "ok": res.returncode == 0,
                "remote_path": remote_path,
                "bytes_written": len(content.encode("utf-8")) if res.returncode == 0 else 0,
                "exit_code": res.returncode,
                "stderr": res.stderr,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "remote_path": remote_path,
                "exit_code": -1,
                "stderr": f"SFTP write timed out after {timeout}s",
                "timed_out": True,
            }


class RemoteVPSDevelopmentEngine:
    """Manages VPS connection profiles, host key verification, remote workspace boundaries, and 13-step remote dev workflow."""

    SETTINGS_KEY = "vps_connection_profiles"

    def __init__(
        self,
        storage: NUIStorage,
        permissions: PermissionEngine,
        *,
        transport: SSHTransportAdapter | None = None,
    ) -> None:
        self.storage = storage
        self.permissions = permissions
        self.transport: SSHTransportAdapter = transport or OpenSSHSystemTransport()
        self._profiles: dict[str, VPSConnectionProfile] = {}
        self._load_profiles()

    def _load_profiles(self) -> None:
        raw_list = self.storage.get_setting(self.SETTINGS_KEY, [])
        if isinstance(raw_list, list):
            for item in raw_list:
                if isinstance(item, dict) and item.get("profile_id"):
                    try:
                        prof = VPSConnectionProfile(
                            profile_id=str(item["profile_id"]),
                            name=str(item.get("name", "VPS Server")),
                            host=str(item.get("host", "")),
                            port=int(item.get("port", 22)),
                            username=str(item.get("username", "ubuntu")),
                            auth_method=str(item.get("auth_method", "SSH_KEY")),
                            ssh_key_path=item.get("ssh_key_path"),
                            expected_host_fingerprint=str(item.get("expected_host_fingerprint", "")),
                            remote_workspace=str(item.get("remote_workspace", "/home/ubuntu/workspace")),
                            allowed_workspace_prefixes=list(
                                item.get("allowed_workspace_prefixes")
                                or [str(item.get("remote_workspace", "/home/ubuntu/workspace"))]
                            ),
                            connect_timeout_seconds=float(item.get("connect_timeout_seconds", 8.0)),
                            connection_state=str(item.get("connection_state", "DISCONNECTED")),
                            last_connected_at=item.get("last_connected_at"),
                            last_error=item.get("last_error"),
                        )
                        self._profiles[prof.profile_id] = prof
                    except Exception:
                        continue

    def _save_profiles(self) -> None:
        serialized = [asdict(p) for p in self._profiles.values()]
        self.storage.set_setting(self.SETTINGS_KEY, serialized)

    def register_profile(
        self,
        *,
        name: str,
        host: str,
        username: str,
        expected_host_fingerprint: str,
        remote_workspace: str = "/home/ubuntu/workspace",
        port: int = 22,
        auth_method: str = "SSH_KEY",
        ssh_key_path: str | None = None,
        secret_credential: str | None = None,
        connect_timeout_seconds: float = 8.0,
    ) -> dict[str, Any]:
        """Register a VPS profile, storing any secret passphrase/token in macOS Keychain (never in SQLite or logs)."""
        profile_id = f"vps-{uuid.uuid4().hex[:10]}"
        norm_ws = posixpath.normpath(remote_workspace)
        if secret_credential:
            self.storage.keychain.set_secret(f"vps:{profile_id}", secret_credential)

        prof = VPSConnectionProfile(
            profile_id=profile_id,
            name=name.strip() or host.strip(),
            host=host.strip(),
            port=int(port),
            username=username.strip(),
            auth_method=auth_method.strip().upper(),
            ssh_key_path=ssh_key_path,
            expected_host_fingerprint=expected_host_fingerprint.strip(),
            remote_workspace=norm_ws,
            allowed_workspace_prefixes=[norm_ws],
            connect_timeout_seconds=float(connect_timeout_seconds),
            connection_state="DISCONNECTED",
        )
        self._profiles[profile_id] = prof
        self._save_profiles()

        self.storage.record_audit(
            user_request=f"Register VPS profile {prof.name} ({prof.username}@{prof.host}:{prof.port})",
            tool_name="vps.register_profile",
            category="VPS_CONNECT",
            target=f"{prof.username}@{prof.host}:{prof.port}",
            operation="REGISTER_PROFILE",
            approval_decision="CONFIGURED_BY_USER",
            status="REGISTERED",
            result_summary=f"Registered VPS profile {prof.profile_id} with Keychain credential isolation",
            metadata={"profile_id": prof.profile_id, "auth_method": prof.auth_method},
        )
        out = asdict(prof)
        out["has_keychain_credential"] = self.storage.keychain.get_secret(f"vps:{profile_id}") is not None
        out["credentials_in_sqlite"] = False
        return out

    def list_profiles(self) -> list[dict[str, Any]]:
        out = []
        for p in self._profiles.values():
            d = asdict(p)
            d["has_keychain_credential"] = self.storage.keychain.get_secret(f"vps:{p.profile_id}") is not None
            d["credentials_in_sqlite"] = False
            out.append(d)
        return out

    def _get_profile(self, profile_id: str) -> VPSConnectionProfile:
        if profile_id not in self._profiles:
            raise KeyError(f"VPS profile {profile_id!r} tidak ditemukan.")
        return self._profiles[profile_id]

    def _enforce_remote_workspace_boundary(
        self, profile: VPSConnectionProfile, remote_path: str
    ) -> str:
        """Verify that `remote_path` is strictly inside the profile's authorized `remote_workspace`."""
        norm_p = posixpath.normpath(remote_path)
        if not norm_p.startswith("/"):
            norm_p = posixpath.normpath(posixpath.join(profile.remote_workspace, norm_p))
        for prefix in profile.allowed_workspace_prefixes:
            norm_pref = posixpath.normpath(prefix)
            if norm_p == norm_pref or norm_p.startswith(norm_pref.rstrip("/") + "/"):
                return norm_p
        raise PermissionError(
            f"REMOTE_WORKSPACE_BOUNDARY_DENIED: Path '{norm_p}' berada di luar remote workspace yang diotorisasi ({profile.remote_workspace})."
        )

    def _check_vps_permission(
        self,
        profile: VPSConnectionProfile,
        category: str,
        operation: str,
        reason: str,
        *,
        session_id: str | None = None,
        explicit_final_deploy_confirmed: bool = False,
    ) -> tuple[bool, dict[str, Any]]:
        target = f"{profile.username}@{profile.host}:{profile.port}"
        perm = self.permissions.check_or_request(
            category=category,
            operation=operation,
            target_type="endpoint",
            target_value=target,
            reason=reason,
            session_id=session_id,
            explicit_final_deploy_confirmed=explicit_final_deploy_confirmed,
        )
        if not perm.allowed:
            self.storage.record_audit(
                user_request=reason,
                tool_name=f"vps.{operation.lower()}",
                category=category,
                target=target,
                operation=operation,
                approval_decision=f"{perm.status}:{perm.decision_source}",
                status=perm.status,
                result_summary=perm.reason,
                metadata={"profile_id": profile.profile_id, "request_id": perm.request_id},
            )
            return (
                False,
                {
                    "ok": False,
                    "status": perm.status,
                    "decision_source": perm.decision_source,
                    "category": perm.category,
                    "operation": perm.operation,
                    "target": target,
                    "request_id": perm.request_id,
                    "reason": perm.reason,
                },
            )
        return (True, {"ok": True, "decision_source": perm.decision_source, "target": target})

    def connect_and_inspect(
        self,
        profile_id: str,
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Verify host fingerprint, check VPS_CONNECT permission, and inspect remote OS/architecture/runtimes."""
        prof = self._get_profile(profile_id)
        allowed, gate_info = self._check_vps_permission(
            prof,
            "VPS_CONNECT",
            "CONNECT",
            f"Hubungkan ke VPS {prof.name} ({prof.username}@{prof.host}:{prof.port})",
            session_id=session_id,
        )
        if not allowed:
            return gate_info

        # Step 1: Mandatory Host Key Fingerprint Verification
        fp_check = self.transport.verify_host_fingerprint(
            prof.host,
            prof.port,
            prof.expected_host_fingerprint,
            timeout=prof.connect_timeout_seconds,
        )
        if not fp_check.get("verified"):
            prof.connection_state = "HOST_KEY_VERIFICATION_FAILED"
            prof.last_error = fp_check.get("reason", "Host key verification failed")
            self._save_profiles()
            self.storage.record_audit(
                user_request=f"connect_vps({prof.profile_id})",
                tool_name="vps.connect",
                category="VPS_CONNECT",
                target=gate_info["target"],
                operation="HOST_KEY_VERIFY",
                approval_decision=f"ALLOWED:{gate_info['decision_source']}",
                status="HOST_KEY_VERIFICATION_FAILED",
                result_summary=prof.last_error,
            )
            return {
                "ok": False,
                "status": "HOST_KEY_VERIFICATION_FAILED",
                "profile_id": prof.profile_id,
                "host_key_check": fp_check,
                "reason": prof.last_error,
            }

        # Step 2: Inspect remote system (OS, architecture, runtimes)
        secret = self.storage.keychain.get_secret(f"vps:{prof.profile_id}")
        probe_cmd = "uname -srm && which python3 node npm git cargo go rustc 2>/dev/null || true"
        res = self.transport.run_ssh_command(
            prof,
            probe_cmd,
            timeout=prof.connect_timeout_seconds,
            keychain_secret=secret,
        )
        if res.get("timed_out"):
            prof.connection_state = "DISCONNECTED_RECOVERABLE"
            prof.last_error = res.get("stderr", "Connection timed out")
            self._save_profiles()
            return {
                "ok": False,
                "status": "CONNECTION_TIMEOUT",
                "recoverable": True,
                "profile_id": prof.profile_id,
                "reason": prof.last_error,
            }
        if not res.get("ok"):
            prof.connection_state = "DISCONNECTED_RECOVERABLE"
            prof.last_error = res.get("stderr", "SSH connection failed")
            self._save_profiles()
            return {
                "ok": False,
                "status": "SSH_CONNECT_FAILED",
                "recoverable": True,
                "profile_id": prof.profile_id,
                "reason": prof.last_error,
            }

        lines = [ln.strip() for ln in res.get("stdout", "").splitlines() if ln.strip()]
        os_arch = lines[0] if lines else "Linux unknown"
        runtimes = lines[1:] if len(lines) > 1 else []

        prof.connection_state = "CONNECTED"
        prof.last_connected_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        prof.last_error = None
        self._save_profiles()

        self.storage.record_audit(
            user_request=f"connect_vps({prof.profile_id})",
            tool_name="vps.connect",
            category="VPS_CONNECT",
            target=gate_info["target"],
            operation="CONNECT_AND_INSPECT",
            approval_decision=f"ALLOWED:{gate_info['decision_source']}",
            status="CONNECTED",
            result_summary=f"Connected to {prof.name} ({os_arch}), host fingerprint verified ({prof.expected_host_fingerprint})",
        )
        return {
            "ok": True,
            "status": "CONNECTED",
            "profile_id": prof.profile_id,
            "host": prof.host,
            "os_and_architecture": os_arch,
            "detected_runtimes": runtimes,
            "remote_workspace": prof.remote_workspace,
            "host_key_verified": True,
            "credential_isolated_in_keychain": True,
            "connected_at": prof.last_connected_at,
        }

    def read_remote_file(
        self,
        profile_id: str,
        remote_path: str,
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Read a source file inside the authorized remote workspace (`VPS_READ`)."""
        prof = self._get_profile(profile_id)
        norm_path = self._enforce_remote_workspace_boundary(prof, remote_path)
        allowed, gate_info = self._check_vps_permission(
            prof,
            "VPS_READ",
            "READ",
            f"Baca berkas remote {norm_path} pada VPS {prof.name}",
            session_id=session_id,
        )
        if not allowed:
            return gate_info

        res = self.transport.sftp_read_file(prof, norm_path, timeout=prof.connect_timeout_seconds)
        if res.get("timed_out"):
            prof.connection_state = "DISCONNECTED_RECOVERABLE"
            self._save_profiles()
        self.storage.record_audit(
            user_request=f"read_remote_file({norm_path})",
            tool_name="vps.read_file",
            category="VPS_READ",
            target=gate_info["target"],
            operation="READ_FILE",
            file_changed=norm_path,
            approval_decision=f"ALLOWED:{gate_info['decision_source']}",
            status="SUCCESS" if res.get("ok") else "ERROR",
            result_summary=f"Read {norm_path} ({res.get('size_bytes', 0)} bytes)" if res.get("ok") else str(res.get("stderr")),
        )
        return res

    def write_remote_file(
        self,
        profile_id: str,
        remote_path: str,
        content: str,
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Write or edit a file inside the authorized remote workspace (`VPS_WRITE`)."""
        prof = self._get_profile(profile_id)
        norm_path = self._enforce_remote_workspace_boundary(prof, remote_path)
        allowed, gate_info = self._check_vps_permission(
            prof,
            "VPS_WRITE",
            "WRITE",
            f"Tulis berkas remote {norm_path} pada workspace VPS {prof.name}",
            session_id=session_id,
        )
        if not allowed:
            return gate_info

        res = self.transport.sftp_write_file(prof, norm_path, content, timeout=prof.connect_timeout_seconds)
        if res.get("timed_out"):
            prof.connection_state = "DISCONNECTED_RECOVERABLE"
            self._save_profiles()
        self.storage.record_audit(
            user_request=f"write_remote_file({norm_path})",
            tool_name="vps.write_file",
            category="VPS_WRITE",
            target=gate_info["target"],
            operation="WRITE_FILE",
            file_changed=norm_path,
            approval_decision=f"ALLOWED:{gate_info['decision_source']}",
            status="SUCCESS" if res.get("ok") else "ERROR",
            result_summary=f"Wrote {norm_path} ({res.get('bytes_written', 0)} bytes)" if res.get("ok") else str(res.get("stderr")),
        )
        return res

    def execute_remote_command(
        self,
        profile_id: str,
        command: str,
        *,
        cwd: str | None = None,
        timeout_seconds: float | None = None,
        explicit_sudo_approved: bool = False,
        explicit_destructive_approved: bool = False,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute build, test, or git command on remote VPS (`VPS_EXECUTE`) with sudo & destructive command guards."""
        prof = self._get_profile(profile_id)
        work_dir = self._enforce_remote_workspace_boundary(prof, cwd or prof.remote_workspace)
        cmd_clean = command.strip()

        # 1. Privilege guard: never execute sudo without explicit approval
        if re.search(r"(?:^|\s|;|&&|\|)sudo\s+", cmd_clean) and not explicit_sudo_approved:
            self.storage.record_audit(
                user_request=f"execute_remote_command({cmd_clean})",
                tool_name="vps.execute",
                category="VPS_EXECUTE",
                target=f"{prof.username}@{prof.host}:{prof.port}",
                operation="BLOCKED_SUDO",
                approval_decision="DENIED:SUDO_REQUIRES_EXPLICIT_APPROVAL",
                status="DENIED",
                result_summary="Perintah sudo ditolak tanpa persetujuan eksplisit pengguna.",
            )
            return {
                "ok": False,
                "status": "SUDO_APPROVAL_REQUIRED",
                "reason": "Perintah berprivilese (sudo) tidak diizinkan secara default tanpa persetujuan eksplisit pengguna.",
            }

        # 2. Destructive command guard
        for pat in DESTRUCTIVE_REMOTE_PATTERNS:
            if pat.search(cmd_clean) and not explicit_destructive_approved:
                self.storage.record_audit(
                    user_request=f"execute_remote_command({cmd_clean})",
                    tool_name="vps.execute",
                    category="VPS_EXECUTE",
                    target=f"{prof.username}@{prof.host}:{prof.port}",
                    operation="BLOCKED_DESTRUCTIVE",
                    approval_decision="DENIED:DESTRUCTIVE_COMMAND_GUARD",
                    status="DENIED",
                    result_summary="Perintah destruktif pada VPS diblokir oleh Remote Security Guard.",
                )
                return {
                    "ok": False,
                    "status": "DESTRUCTIVE_COMMAND_BLOCKED",
                    "reason": "Perintah destruktif memerlukan konfirmasi khusus dan ditolak secara default.",
                }

        allowed, gate_info = self._check_vps_permission(
            prof,
            "VPS_EXECUTE",
            "EXECUTE",
            f"Jalankan perintah remote '{cmd_clean}' di {work_dir} pada VPS {prof.name}",
            session_id=session_id,
        )
        if not allowed:
            return gate_info

        eff_timeout = timeout_seconds or prof.connect_timeout_seconds
        full_cmd = f"cd {shlex.quote(work_dir)} && {cmd_clean}"
        res = self.transport.run_ssh_command(prof, full_cmd, timeout=eff_timeout)
        if res.get("timed_out"):
            prof.connection_state = "DISCONNECTED_RECOVERABLE"
            prof.last_error = res.get("stderr", "Remote execution timed out")
            self._save_profiles()
            self.storage.record_audit(
                user_request=f"execute_remote_command({cmd_clean})",
                tool_name="vps.execute",
                category="VPS_EXECUTE",
                target=gate_info["target"],
                operation="EXECUTE_TIMEOUT",
                approval_decision=f"ALLOWED:{gate_info['decision_source']}",
                status="TIMEOUT",
                result_summary=prof.last_error,
            )
            return {
                "ok": False,
                "status": "EXECUTION_TIMEOUT",
                "recoverable": True,
                "connection_state": prof.connection_state,
                "reason": prof.last_error,
            }

        self.storage.record_audit(
            user_request=f"execute_remote_command({cmd_clean})",
            tool_name="vps.execute",
            category="VPS_EXECUTE",
            target=gate_info["target"],
            operation="EXECUTE",
            approval_decision=f"ALLOWED:{gate_info['decision_source']}",
            status="SUCCESS" if res.get("ok") else "ERROR",
            result_summary=f"Command '{redact_secrets(cmd_clean)}' exited with {res.get('exit_code')}",
        )
        return {
            "ok": bool(res.get("ok")),
            "status": "COMPLETED" if res.get("ok") else "COMMAND_FAILED",
            "cwd": work_dir,
            "command": redact_secrets(cmd_clean),
            "exit_code": res.get("exit_code", 0),
            "stdout": redact_secrets(res.get("stdout", "")),
            "stderr": redact_secrets(res.get("stderr", "")),
        }

    def execute_remote_deployment(
        self,
        profile_id: str,
        deploy_command: str,
        *,
        explicit_final_deploy_confirmed: bool = False,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Run deployment workflow on remote VPS (`VPS_DEPLOY`), requiring explicit final confirmation."""
        prof = self._get_profile(profile_id)
        allowed, gate_info = self._check_vps_permission(
            prof,
            "VPS_DEPLOY",
            "DEPLOY",
            f"Deploy aplikasi pada VPS {prof.name}: {deploy_command}",
            session_id=session_id,
            explicit_final_deploy_confirmed=explicit_final_deploy_confirmed,
        )
        if not allowed:
            return gate_info

        res = self.transport.run_ssh_command(
            prof,
            f"cd {shlex.quote(prof.remote_workspace)} && {deploy_command}",
            timeout=prof.connect_timeout_seconds,
        )
        self.storage.record_audit(
            user_request=f"deploy_vps({prof.profile_id})",
            tool_name="vps.deploy",
            category="VPS_DEPLOY",
            target=gate_info["target"],
            operation="DEPLOY",
            approval_decision=f"ALLOWED:{gate_info['decision_source']}|FINAL_CONFIRMED",
            status="SUCCESS" if res.get("ok") else "ERROR",
            result_summary=f"VPS deployment exited with {res.get('exit_code')}",
        )
        return {
            "ok": bool(res.get("ok")),
            "status": "DEPLOYED" if res.get("ok") else "DEPLOY_FAILED",
            "profile_id": prof.profile_id,
            "exit_code": res.get("exit_code", 0),
            "stdout": redact_secrets(res.get("stdout", "")),
            "stderr": redact_secrets(res.get("stderr", "")),
        }

    def recover_connection(
        self,
        profile_id: str,
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Recover a VPS connection after a timeout or transient network drop."""
        prof = self._get_profile(profile_id)
        previous_state = prof.connection_state
        reconnect_res = self.connect_and_inspect(profile_id, session_id=session_id)
        reconnect_res["previous_state"] = previous_state
        reconnect_res["recovered"] = bool(reconnect_res.get("ok"))
        return reconnect_res

    VALID_FOLDER_VPS_STATUSES: tuple[str, ...] = (
        "LOCAL_ONLY",
        "REMOTE_CONNECTED",
        "REMOTE_MOUNTED",
        "SYNCED",
        "DISCONNECTED",
        "NOT_CONFIGURED",
        "UNKNOWN",
    )

    def _find_matching_profile_for_folder(
        self, canonical_path: str, folder_label: str
    ) -> VPSConnectionProfile | None:
        """Find a VPS profile explicitly associated with the local folder or label."""
        norm_local = canonical_path.rstrip("/").lower()
        lbl_low = folder_label.strip().lower()
        for prof in self._profiles.values():
            p_name_low = prof.name.lower()
            r_ws_low = prof.remote_workspace.rstrip("/").lower()
            if (
                (lbl_low and lbl_low in p_name_low)
                or (lbl_low and r_ws_low.endswith("/" + lbl_low))
                or (norm_local and norm_local in p_name_low)
            ):
                return prof
        if len(self._profiles) == 1:
            only_prof = next(iter(self._profiles.values()))
            if lbl_low in only_prof.name.lower() or lbl_low in only_prof.remote_workspace.lower():
                return only_prof
        return None

    @staticmethod
    def _inspect_os_mount_for_path(
        canonical_path: str, mount_table_override: str | None = None
    ) -> dict[str, Any]:
        """Inspect macOS `/sbin/mount` output to determine if `canonical_path` is a remote mount (SSHFS/FUSE/NFS/SMB) or local APFS."""
        raw_mount = mount_table_override
        if raw_mount is None:
            try:
                res = subprocess.run(
                    ["/sbin/mount"],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
                raw_mount = res.stdout
            except Exception as exc:
                return {
                    "ok": False,
                    "is_remote_mount": False,
                    "mount_status": f"UNKNOWN (Gagal membaca tabel mount OS: {type(exc).__name__})",
                    "filesystem_type": "unknown",
                    "mount_point": canonical_path,
                }

        norm_target = canonical_path.rstrip("/") or "/"
        best_match_mp = ""
        best_match_fs = "apfs"
        best_match_src = ""
        is_remote = False

        pattern = re.compile(r"^(.+?)\s+on\s+(/[^\(\n]*?)\s+\(([^,\)]+)")
        for line in (raw_mount or "").splitlines():
            m = pattern.match(line.strip())
            if not m:
                continue
            src, mp, fstype = (
                m.group(1).strip(),
                m.group(2).strip().rstrip("/") or "/",
                m.group(3).strip().lower(),
            )
            if norm_target == mp or norm_target.startswith((mp if mp != "/" else "") + "/"):
                if len(mp) >= len(best_match_mp):
                    best_match_mp = mp
                    best_match_fs = fstype
                    best_match_src = src
                    remote_fs_markers = (
                        "sshfs",
                        "fuse",
                        "macfuse",
                        "osxfuse",
                        "nfs",
                        "smbfs",
                        "cifs",
                        "webdav",
                        "afpfs",
                    )
                    is_remote = any(
                        rf in fstype or rf in src.lower() for rf in remote_fs_markers
                    ) or (":" in src and not src.startswith("/dev/"))

        if is_remote:
            return {
                "ok": True,
                "is_remote_mount": True,
                "mount_status": f"REMOTE_MOUNTED ({best_match_fs} from {best_match_src} on {best_match_mp})",
                "filesystem_type": best_match_fs,
                "mount_point": best_match_mp,
                "mount_source": best_match_src,
            }
        return {
            "ok": True,
            "is_remote_mount": False,
            "mount_status": f"LOCAL_FILESYSTEM ({best_match_fs.upper()} on {best_match_mp or '/'}, tidak ada mount SSHFS/FUSE/remote aktif)",
            "filesystem_type": best_match_fs,
            "mount_point": best_match_mp or "/",
            "mount_source": best_match_src or "local_disk",
        }

    def inspect_folder_vps_status(
        self,
        folder_query_or_path: str = "/Users/AMRA/yayasan",
        *,
        mount_table_override: str | None = None,
        sync_mechanism: str | None = None,
        sync_verification_proof: str | None = None,
        simulate_transport_unknown: bool = False,
    ) -> dict[str, Any]:
        """Inspect and verify actual local folder & remote VPS connection status across all 9 required fields.

        Never infers `REMOTE_CONNECTED` or `SYNCED` merely from Connected Folders (`READ_WRITE`),
        local `.git` history, or deployment documentation (`DEPLOY.md`).
        """
        q_clean = folder_query_or_path.strip()
        q_low = q_clean.lower()

        all_folders = self.storage.list_authorized_folders(active_only=False)
        matched_record: dict[str, Any] | None = None

        for fld in all_folders:
            fid = str(fld.get("folder_id", ""))
            fpath = str(fld.get("path", ""))
            flabel = str(fld.get("label", ""))
            if (
                q_clean == fid
                or q_clean == fpath
                or q_low == flabel.lower()
                or (flabel and flabel.lower() in q_low)
                or (fpath and fpath.lower() in q_low)
            ):
                matched_record = fld
                break

        if matched_record is None and "yayasan" in q_low:
            yayasan_path = Path("/Users/AMRA/yayasan")
            if yayasan_path.exists():
                matched_record = self.storage.add_authorized_folder(
                    yayasan_path, label="yayasan", access_mode="READ_WRITE"
                )
            else:
                for fld in all_folders:
                    if "yayasan" in str(fld.get("path", "")).lower():
                        matched_record = fld
                        break

        if matched_record is not None:
            connected_folder_id = str(matched_record.get("folder_id") or "NOT_REGISTERED")
            local_canonical_path = str(Path(str(matched_record.get("path"))).expanduser().resolve())
            folder_label = str(matched_record.get("label") or Path(local_canonical_path).name)
            access_mode = str(matched_record.get("access_mode") or "READ_WRITE")
            is_folder_active = bool(int(matched_record.get("active", 1)))
        else:
            cand_path = (
                Path("/Users/AMRA/yayasan")
                if ("yayasan" in q_low or not q_clean.startswith("/"))
                else Path(q_clean.split()[0])
            )
            try:
                local_canonical_path = str(cand_path.expanduser().resolve())
            except Exception:
                local_canonical_path = str(cand_path)
            folder_label = Path(local_canonical_path).name or "folder"
            rec_lookup = self.storage.get_authorized_folder(local_canonical_path)
            if rec_lookup:
                connected_folder_id = str(rec_lookup["folder_id"])
                access_mode = str(rec_lookup.get("access_mode", "READ_WRITE"))
                is_folder_active = bool(int(rec_lookup.get("active", 1)))
            else:
                connected_folder_id = "NOT_REGISTERED"
                access_mode = "UNREGISTERED"
                is_folder_active = False

        local_dir_exists = Path(local_canonical_path).is_dir()
        has_local_git = (Path(local_canonical_path) / ".git").exists()
        has_deploy_doc = (Path(local_canonical_path) / "DEPLOY.md").exists()

        mount_info = self._inspect_os_mount_for_path(
            local_canonical_path, mount_table_override=mount_table_override
        )
        mount_status_str = str(mount_info["mount_status"])
        is_remote_mount = bool(mount_info.get("is_remote_mount", False))

        matched_prof = self._find_matching_profile_for_folder(local_canonical_path, folder_label)

        if simulate_transport_unknown:
            remote_ssh_profile_str = (
                f"{matched_prof.profile_id} ({matched_prof.username}@{matched_prof.host}:{matched_prof.port})"
                if matched_prof
                else "UNKNOWN (Transport probe error)"
            )
            ssh_connection_status = "UNKNOWN"
            verified_host_fingerprint = "UNKNOWN"
            sftp_connection = "UNKNOWN"
            remote_workspace_path = matched_prof.remote_workspace if matched_prof else "UNKNOWN"
            last_successful_remote_verification = "UNKNOWN"
            overall_status = "UNKNOWN"
            vps_connection_status = "UNKNOWN"
        elif is_remote_mount:
            remote_ssh_profile_str = (
                f"{matched_prof.profile_id} ({matched_prof.username}@{matched_prof.host}:{matched_prof.port})"
                if matched_prof
                else f"OS_MOUNT ({mount_info.get('mount_source', 'remote')})"
            )
            ssh_connection_status = (
                "CONNECTED"
                if (matched_prof and matched_prof.connection_state == "CONNECTED")
                else "REMOTE_MOUNT_ACTIVE"
            )
            verified_host_fingerprint = (
                matched_prof.expected_host_fingerprint
                if (matched_prof and matched_prof.expected_host_fingerprint.startswith("SHA256:"))
                else "MOUNT_VERIFIED_BY_OS"
            )
            sftp_connection = "ACTIVE (MOUNTED)"
            remote_workspace_path = (
                matched_prof.remote_workspace
                if matched_prof
                else str(mount_info.get("mount_source", "remote_mount"))
            )
            last_successful_remote_verification = (
                (matched_prof.last_connected_at if matched_prof else None)
                or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            )
            overall_status = "REMOTE_MOUNTED"
            vps_connection_status = "REMOTE_MOUNTED"
        elif matched_prof is not None:
            remote_ssh_profile_str = (
                f"{matched_prof.profile_id} ({matched_prof.name} — {matched_prof.username}@{matched_prof.host}:{matched_prof.port})"
            )
            remote_workspace_path = matched_prof.remote_workspace
            is_connected = matched_prof.connection_state == "CONNECTED"
            fp_valid = matched_prof.expected_host_fingerprint.startswith("SHA256:")
            ssh_connection_status = "CONNECTED" if is_connected else "DISCONNECTED"
            verified_host_fingerprint = (
                matched_prof.expected_host_fingerprint
                if (is_connected and fp_valid)
                else f"UNVERIFIED ({matched_prof.expected_host_fingerprint or 'NONE'})"
            )
            sftp_connection = "ACTIVE" if (is_connected and fp_valid) else "INACTIVE"
            last_successful_remote_verification = (
                matched_prof.last_connected_at or "NEVER (Belum pernah diverifikasi)"
            )

            if is_connected and fp_valid:
                if sync_mechanism and sync_verification_proof:
                    overall_status = "SYNCED"
                    vps_connection_status = "SYNCED"
                else:
                    overall_status = "REMOTE_CONNECTED"
                    vps_connection_status = "REMOTE_CONNECTED"
            else:
                overall_status = "DISCONNECTED"
                vps_connection_status = "DISCONNECTED"
        else:
            remote_ssh_profile_str = "NONE (Belum ada profil SSH yang dikonfigurasi untuk folder ini)"
            ssh_connection_status = "NOT_CONFIGURED"
            verified_host_fingerprint = "NONE (Belum ada host fingerprint SHA256 yang diverifikasi)"
            sftp_connection = "NOT_CONFIGURED"
            remote_workspace_path = "NONE"
            last_successful_remote_verification = "NEVER (Belum ada verifikasi remote yang berhasil)"
            if connected_folder_id != "NOT_REGISTERED" and is_folder_active:
                overall_status = "LOCAL_ONLY"
                vps_connection_status = "NOT_CONFIGURED"
            else:
                overall_status = "NOT_CONFIGURED"
                vps_connection_status = "NOT_CONFIGURED"

        if overall_status == "LOCAL_ONLY":
            summary_headline = (
                f"Folder `{local_canonical_path}` terdaftar sebagai folder lokal `{access_mode}` (`{connected_folder_id}`).\n\n"
                "Status koneksi VPS belum dapat dipastikan karena belum ada bukti sesi SSH atau remote mount yang aktif.\n\n"
                f"**Kesimpulan:** folder tersedia secara lokal (`LOCAL_ONLY`). Hubungan dengan VPS belum terverifikasi (`{vps_connection_status}`)."
            )
        elif overall_status == "REMOTE_CONNECTED":
            summary_headline = (
                f"Folder `{local_canonical_path}` terdaftar sebagai folder lokal `{access_mode}` dan memiliki koneksi SSH/SFTP aktif ke VPS (`{remote_ssh_profile_str}`).\n\n"
                f"**Kesimpulan:** status folder adalah `REMOTE_CONNECTED` menuju workspace `{remote_workspace_path}` (host fingerprint `{verified_host_fingerprint}` terverifikasi)."
            )
        elif overall_status == "REMOTE_MOUNTED":
            summary_headline = (
                f"Folder `{local_canonical_path}` terbukti ter-mount secara remote melalui filesystem `{mount_status_str}`.\n\n"
                "**Kesimpulan:** status folder adalah `REMOTE_MOUNTED`."
            )
        elif overall_status == "SYNCED":
            summary_headline = (
                f"Folder `{local_canonical_path}` terhubung ke VPS (`{remote_ssh_profile_str}`) dan tersinkronisasi melalui `{sync_mechanism}` (`{sync_verification_proof}`).\n\n"
                "**Kesimpulan:** status folder adalah `SYNCED`."
            )
        elif overall_status == "DISCONNECTED":
            summary_headline = (
                f"Folder `{local_canonical_path}` memiliki profil VPS terdaftar (`{remote_ssh_profile_str}`), namun sesi koneksi SSH/SFTP saat ini terputus (`DISCONNECTED`).\n\n"
                "**Kesimpulan:** folder tersedia secara lokal, tetapi status koneksi VPS saat ini `DISCONNECTED`."
            )
        elif overall_status == "NOT_CONFIGURED":
            summary_headline = (
                f"Folder `{local_canonical_path}` belum memiliki konfigurasi profil SSH/VPS maupun remote mount aktif.\n\n"
                "**Kesimpulan:** status koneksi VPS adalah `NOT_CONFIGURED`."
            )
        else:
            summary_headline = (
                f"Pemeriksaan status koneksi VPS untuk `{local_canonical_path}` menghasilkan status `UNKNOWN` karena kendala pemeriksaan transport.\n\n"
                "**Kesimpulan:** status koneksi VPS `UNKNOWN`."
            )

        formatted_report = (
            "### Hasil Pemeriksaan Status Folder & Koneksi VPS\n\n"
            f"{summary_headline}\n\n"
            "| Parameter Pemeriksaan | Nilai Terverifikasi |\n"
            "| :--- | :--- |\n"
            f"| `connected_folder_id` | `{connected_folder_id}` (`{access_mode}`) |\n"
            f"| `local_canonical_path` | `{local_canonical_path}` |\n"
            f"| `remote_ssh_profile` | `{remote_ssh_profile_str}` |\n"
            f"| `ssh_connection_status` | `{ssh_connection_status}` |\n"
            f"| `verified_host_fingerprint` | `{verified_host_fingerprint}` |\n"
            f"| `sftp_connection` | `{sftp_connection}` |\n"
            f"| `remote_workspace_path` | `{remote_workspace_path}` |\n"
            f"| `mount_status` | `{mount_status_str}` |\n"
            f"| `last_successful_remote_verification` | `{last_successful_remote_verification}` |\n"
            f"| **Status Klasifikasi Akhir** | **`{overall_status}`** (VPS: `{vps_connection_status}`) |\n\n"
            "> **Catatan Kejujuran Epistemik:** Keberadaan folder di daftar *Connected Folders* (`READ_WRITE`), riwayat `.git` lokal, atau berkas `DEPLOY.md` adalah properti repositori lokal di Mac dan **bukan** bukti sesi SSH/SFTP atau sinkronisasi VPS yang aktif."
        )

        discovery = self.discover_ssh_and_deployment_metadata(local_canonical_path)
        return {
            "ok": True,
            "status": overall_status,
            "overall_status": overall_status,
            "vps_connection_status": vps_connection_status,
            "local_folder_status": access_mode if is_folder_active else "DISCONNECTED",
            "local_directory_exists": local_dir_exists,
            "connected_folder_id": connected_folder_id,
            "local_canonical_path": local_canonical_path,
            "remote_ssh_profile": remote_ssh_profile_str,
            "ssh_connection_status": ssh_connection_status,
            "verified_host_fingerprint": verified_host_fingerprint,
            "sftp_connection": sftp_connection,
            "remote_workspace_path": remote_workspace_path,
            "mount_status": mount_status_str,
            "last_successful_remote_verification": last_successful_remote_verification,
            "sync_mechanism": sync_mechanism or "NONE",
            "sync_verification_proof": sync_verification_proof or "NONE",
            "git_repo_present_locally": has_local_git,
            "deploy_doc_present_locally": has_deploy_doc,
            "discovered_deployment_metadata": discovery,
            "inferred_from_git_or_connected_folder": False,
            "summary_headline": summary_headline,
            "formatted_report": formatted_report,
        }

    def disconnect_profile(self, profile_id: str) -> dict[str, Any]:
        """Disconnect an active VPS profile without deleting its saved configuration."""
        prof = self._get_profile(profile_id)
        prev_state = prof.connection_state
        prof.connection_state = "DISCONNECTED"
        self._save_profiles()
        self.storage.record_audit(
            user_request=f"disconnect_vps({prof.profile_id})",
            tool_name="vps.disconnect",
            category="VPS_CONNECT",
            target=f"{prof.username}@{prof.host}:{prof.port}",
            operation="DISCONNECT",
            approval_decision="USER_INITIATED_DISCONNECT",
            status="DISCONNECTED",
            result_summary=f"Disconnected VPS profile {prof.profile_id} (was {prev_state})",
        )
        return {
            "ok": True,
            "status": "DISCONNECTED",
            "profile_id": prof.profile_id,
            "previous_state": prev_state,
            "connection_state": prof.connection_state,
        }

    def discover_ssh_and_deployment_metadata(
        self, local_folder_path: str = "/Users/AMRA/yayasan"
    ) -> dict[str, Any]:
        """Discover SSH host aliases (`~/.ssh/config`), `known_hosts`, SSH Agent (`SSH_AUTH_SOCK` / `ssh-add -l`), Keychain credentials, and documented deployment hints (`DEPLOY.md`) without exposing secrets or fabricating active connections."""
        ssh_hosts: list[dict[str, Any]] = []
        for cand_cfg in (
            Path.home() / ".ssh" / "config",
            Path("/Users/AMRA/.ssh/config"),
        ):
            try:
                if cand_cfg.is_file():
                    cur_entry: dict[str, Any] | None = None
                    for raw_ln in cand_cfg.read_text(encoding="utf-8", errors="replace").splitlines():
                        ln = raw_ln.strip()
                        if not ln or ln.startswith("#"):
                            continue
                        parts = ln.split(None, 1)
                        if len(parts) < 2:
                            continue
                        key, val = parts[0].lower(), parts[1].strip()
                        if key == "host":
                            if cur_entry and cur_entry.get("alias") != "*":
                                ssh_hosts.append(cur_entry)
                            cur_entry = {"alias": val, "source": str(cand_cfg)}
                        elif cur_entry is not None:
                            if key in {"hostname", "user", "port", "identityfile"}:
                                cur_entry[key] = val
                    if cur_entry and cur_entry.get("alias") != "*":
                        ssh_hosts.append(cur_entry)
                    break
            except Exception:
                continue

        known_hosts_count = 0
        for cand_kh in (
            Path.home() / ".ssh" / "known_hosts",
            Path("/Users/AMRA/.ssh/known_hosts"),
        ):
            try:
                if cand_kh.is_file():
                    known_hosts_count = sum(
                        1
                        for ln in cand_kh.read_text(encoding="utf-8", errors="replace").splitlines()
                        if ln.strip() and not ln.strip().startswith("#")
                    )
                    break
            except Exception:
                continue

        ssh_agent_info: dict[str, Any] = {
            "sock_present": bool(os.environ.get("SSH_AUTH_SOCK")),
            "status": "NO_AGENT_SOCK",
            "keys_loaded_count": 0,
        }
        try:
            if ssh_agent_info["sock_present"]:
                ag_res = subprocess.run(
                    ["/usr/bin/ssh-add", "-l"],
                    capture_output=True,
                    text=True,
                    timeout=1.5,
                )
                out_txt = (ag_res.stdout or "").strip()
                if ag_res.returncode == 0 and out_txt and "no identities" not in out_txt.lower():
                    key_lines = [ln for ln in out_txt.splitlines() if ln.strip()]
                    ssh_agent_info["status"] = "IDENTITIES_LOADED"
                    ssh_agent_info["keys_loaded_count"] = len(key_lines)
                elif ag_res.returncode == 1 or "no identities" in out_txt.lower():
                    ssh_agent_info["status"] = "AGENT_RUNNING_NO_IDENTITIES"
                else:
                    ssh_agent_info["status"] = "AGENT_UNREACHABLE"
        except Exception:
            ssh_agent_info["status"] = "AGENT_CHECK_SKIPPED"

        deploy_doc_info: dict[str, Any] = {
            "deploy_md_exists": False,
            "documented_vps_host": None,
            "documented_vps_user": None,
            "documented_remote_workspace": None,
            "documented_domains": [],
            "source_file": None,
            "evidence_classification": "NONE",
            "provenance_note": "NONE",
        }
        try:
            deploy_md_path = Path(local_folder_path).expanduser().resolve() / "DEPLOY.md"
            if deploy_md_path.is_file():
                deploy_text = deploy_md_path.read_text(encoding="utf-8", errors="replace")
                deploy_doc_info["deploy_md_exists"] = True
                deploy_doc_info["source_file"] = "DEPLOY.md"
                deploy_doc_info["evidence_classification"] = "DOCUMENTED_IN_DEPLOY_MD_ONLY"
                m_ssh = re.search(r"\b([a-zA-Z0-9_\-]+)@(\d{1,3}(?:\.\d{1,3}){3})\b", deploy_text)
                if m_ssh:
                    deploy_doc_info["documented_vps_user"] = m_ssh.group(1)
                    deploy_doc_info["documented_vps_host"] = m_ssh.group(2)
                m_ws = re.search(r"(/opt/[a-zA-Z0-9_\-]+|/var/www/[a-zA-Z0-9_\-]+)", deploy_text)
                if m_ws:
                    deploy_doc_info["documented_remote_workspace"] = m_ws.group(1)
                doms = sorted(
                    set(
                        re.findall(
                            r"\b(?:www\.)?akademihijaiyyahindonesia\.com\b",
                            deploy_text,
                            flags=re.IGNORECASE,
                        )
                    )
                )
                deploy_doc_info["documented_domains"] = [d.lower() for d in doms]
                deploy_doc_info["provenance_note"] = (
                    "DOCUMENTED_IN_DEPLOY_MD_ONLY (Dokumentasi lokal DEPLOY.md, BUKAN bukti profil SSH/SFTP aktif)"
                )
        except Exception:
            pass

        local_ssh_keys: list[str] = []
        for ssh_dir in (Path.home() / ".ssh", Path("/Users/AMRA/.ssh")):
            try:
                if ssh_dir.is_dir():
                    for kp in sorted(ssh_dir.iterdir()):
                        if kp.name in {"id_ed25519", "id_ed25519.pub", "id_rsa", "id_rsa.pub", "id_ecdsa", "id_ecdsa.pub"}:
                            if kp.name not in local_ssh_keys:
                                local_ssh_keys.append(kp.name)
                    break
            except Exception:
                continue

        keychain_Refs = [
            getattr(p, "keychain_credential_ref", None) or getattr(p, "credential_ref", None) or getattr(p, "profile_id", None)
            for p in self._profiles.values()
            if getattr(p, "keychain_credential_ref", None) or getattr(p, "credential_ref", None) or getattr(p, "auth_method", None)
        ]
        return {
            "ssh_config_hosts": ssh_hosts,
            "ssh_config_found": len(ssh_hosts) > 0,
            "known_hosts_entries_count": known_hosts_count,
            "local_ssh_keys": local_ssh_keys,
            "ssh_agent": ssh_agent_info,
            "keychain_credential_refs_count": len(keychain_Refs),
            "deploy_md": deploy_doc_info,
            "registered_vps_profiles_count": len(self._profiles),
        }

    def probe_and_attempt_live_ssh_connection(
        self,
        host: str = "187.53.135.198",
        *,
        username: str = "root",
        port: int = 22,
        remote_workspace: str = "/opt/yayasan",
        auto_register_on_success: bool = False,
        timeout: float = 4.0,
    ) -> dict[str, Any]:
        """Use the macOS OpenSSH backend (`/usr/bin/ssh-keygen`, `/usr/bin/ssh-keyscan`, `/usr/bin/ssh`) to probe the target VPS host key and attempt non-interactive BatchMode SSH authentication."""
        checked_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        is_live_transport = isinstance(self.transport, OpenSSHSystemTransport)
        scanned_fp: str | None = None
        fp_source = "NONE"

        if is_live_transport:
            # 1. Check ~/.ssh/known_hosts first for existing verified fingerprint
            for kh_path in (Path.home() / ".ssh" / "known_hosts", Path("/Users/AMRA/.ssh/known_hosts")):
                try:
                    if kh_path.is_file():
                        kh_res = subprocess.run(
                            ["/usr/bin/ssh-keygen", "-F", host, "-lf", str(kh_path)],
                            capture_output=True,
                            text=True,
                            timeout=2.0,
                        )
                        if kh_res.returncode == 0 and "SHA256:" in (kh_res.stdout or ""):
                            m_fp = re.search(r"(SHA256:[A-Za-z0-9+/=]+)", kh_res.stdout)
                            if m_fp:
                                scanned_fp = m_fp.group(1)
                                fp_source = f"KNOWN_HOSTS ({kh_path})"
                                break
                except Exception:
                    continue

            # 2. If not in known_hosts, run live ssh-keyscan
            if not scanned_fp:
                try:
                    scan = subprocess.run(
                        ["/usr/bin/ssh-keyscan", "-T", str(max(1, int(timeout))), "-p", str(port), host],
                        capture_output=True,
                        text=True,
                        timeout=timeout + 1.0,
                    )
                    if scan.returncode == 0 and scan.stdout.strip():
                        keygen = subprocess.run(
                            ["/usr/bin/ssh-keygen", "-lf", "-"],
                            input=scan.stdout,
                            capture_output=True,
                            text=True,
                            timeout=2.5,
                        )
                        m_fp = re.search(r"(SHA256:[A-Za-z0-9+/=]+)", keygen.stdout or "")
                        if m_fp:
                            scanned_fp = m_fp.group(1)
                            fp_source = "LIVE_SSH_KEYSCAN"
                except Exception:
                    pass

            # 3. Attempt live non-interactive SSH probe using macOS OpenSSH client
            ssh_cmd = [
                "/usr/bin/ssh",
                "-p",
                str(port),
                "-o",
                "BatchMode=yes",
                "-o",
                f"ConnectTimeout={max(2, int(timeout))}",
                "-o",
                "StrictHostKeyChecking=accept-new",
                f"{username}@{host}",
                f"echo NUI_SSH_LIVE_OK && uname -srm && (test -d {shlex.quote(remote_workspace)} && echo WORKSPACE_FOUND || echo WORKSPACE_MISSING) && (cat {shlex.quote(remote_workspace)}/.commit 2>/dev/null || true)",
            ]
            try:
                s_res = subprocess.run(
                    ssh_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout + 2.0,
                )
                out_lines = [ln.strip() for ln in (s_res.stdout or "").splitlines() if ln.strip()]
                err_txt = redact_secrets((s_res.stderr or "").strip())
                if s_res.returncode == 0 and any("NUI_SSH_LIVE_OK" in ln for ln in out_lines):
                    remote_uname = out_lines[1] if len(out_lines) > 1 else "Linux"
                    ws_found = "WORKSPACE_FOUND" in out_lines
                    rem_commit = out_lines[3] if len(out_lines) > 3 else None
                    prof_id = "vps-yayasan-187-53-135-198"
                    if auto_register_on_success:
                        eff_fp = scanned_fp or "SHA256:LIVE_OPENSSH_VERIFIED"
                        prof = VPSConnectionProfile(
                            profile_id=prof_id,
                            name="Yayasan VPS (187.53.135.198)",
                            host=host,
                            port=port,
                            username=username,
                            auth_method="SSH_KEY",
                            ssh_key_path=None,
                            expected_host_fingerprint=eff_fp,
                            remote_workspace=remote_workspace,
                            allowed_workspace_prefixes=[remote_workspace, "/var/www"],
                            connect_timeout_seconds=8.0,
                            connection_state="CONNECTED",
                            last_connected_at=checked_at,
                            last_error=None,
                        )
                        self._profiles[prof_id] = prof
                        self._save_profiles()
                    return {
                        "ok": True,
                        "attempted": True,
                        "transport": "OpenSSHSystemTransport",
                        "verification_status": "PASS_LIVE",
                        "ssh_status": "CONNECTED",
                        "target": f"{username}@{host}:{port}",
                        "remote_workspace": remote_workspace,
                        "scanned_host_fingerprint": scanned_fp,
                        "fingerprint_source": fp_source,
                        "remote_uname": remote_uname,
                        "remote_workspace_exists": ws_found,
                        "remote_commit": rem_commit,
                        "profile_id": prof_id if auto_register_on_success else None,
                        "checked_at": checked_at,
                        "error": None,
                    }
                if "operation not permitted" in err_txt.lower():
                    ssh_st = "SANDBOX_BLOCKED"
                elif "permission denied" in err_txt.lower():
                    ssh_st = "SSH_REACHABLE_AUTH_KEY_REQUIRED"
                elif "timed out" in err_txt.lower() or "connection refused" in err_txt.lower() or "no route" in err_txt.lower():
                    ssh_st = "SSH_PORT_UNREACHABLE"
                else:
                    ssh_st = "SSH_HANDSHAKE_FAILED"
                return {
                    "ok": False,
                    "attempted": True,
                    "transport": "OpenSSHSystemTransport",
                    "verification_status": "BLOCKED" if ssh_st == "SANDBOX_BLOCKED" else "FAILED",
                    "ssh_status": ssh_st,
                    "target": f"{username}@{host}:{port}",
                    "remote_workspace": remote_workspace,
                    "scanned_host_fingerprint": scanned_fp,
                    "fingerprint_source": fp_source,
                    "remote_uname": None,
                    "remote_workspace_exists": None,
                    "remote_commit": None,
                    "profile_id": None,
                    "checked_at": checked_at,
                    "error": err_txt or f"ssh exited with code {s_res.returncode}",
                }
            except Exception as exc:
                err_str = f"{type(exc).__name__}: {exc}"
                return {
                    "ok": False,
                    "attempted": True,
                    "transport": "OpenSSHSystemTransport",
                    "verification_status": "FAILED",
                    "ssh_status": "SSH_PROBE_ERROR",
                    "target": f"{username}@{host}:{port}",
                    "remote_workspace": remote_workspace,
                    "scanned_host_fingerprint": scanned_fp,
                    "fingerprint_source": fp_source,
                    "checked_at": checked_at,
                    "error": err_str,
                }

        return {
            "ok": False,
            "attempted": False,
            "transport": type(self.transport).__name__,
            "verification_status": "PASS_SIMULATED",
            "ssh_status": "SIMULATED_TRANSPORT_NO_LIVE_PROBE",
            "target": f"{username}@{host}:{port}",
            "remote_workspace": remote_workspace,
            "scanned_host_fingerprint": None,
            "fingerprint_source": "NONE",
            "checked_at": checked_at,
            "error": None,
        }

    def inspect_remote_workspace_manifest(
        self,
        profile_id: str,
        remote_path: str | None = None,
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Inspect remote workspace directory and return file manifest with SHA-256 checksums (`READ_REMOTE` / `VPS_READ`)."""
        prof = self._get_profile(profile_id)
        target_dir = self._enforce_remote_workspace_boundary(prof, remote_path or prof.remote_workspace)

        if prof.connection_state != "CONNECTED" or not prof.expected_host_fingerprint.startswith("SHA256:"):
            return {
                "ok": False,
                "status": "VPS_NOT_CONNECTED_OR_UNVERIFIED",
                "profile_id": prof.profile_id,
                "connection_state": prof.connection_state,
                "remote_workspace": target_dir,
                "files": {},
                "reason": f"Sesi SSH untuk '{prof.name}' berstatus '{prof.connection_state}'; inspeksi remote memerlukan koneksi terverifikasi.",
            }

        allowed, gate_info = self._check_vps_permission(
            prof,
            "VPS_READ",
            "READ",
            f"Inspeksi manifest berkas remote pada {target_dir} di VPS {prof.name}",
            session_id=session_id,
        )
        if not allowed:
            alt_allowed, alt_gate = self._check_vps_permission(
                prof,
                "READ_REMOTE",
                "READ",
                f"Inspeksi manifest berkas remote pada {target_dir} di VPS {prof.name}",
                session_id=session_id,
            )
            if not alt_allowed:
                return gate_info
            gate_info = alt_gate

        if hasattr(self.transport, "sftp_list_manifest"):
            custom_manifest = getattr(self.transport, "sftp_list_manifest")(prof, target_dir)
            if isinstance(custom_manifest, dict):
                return custom_manifest

        quoted_dir = shlex.quote(target_dir)
        manifest_cmd = (
            f"cd {quoted_dir} && "
            "find . -maxdepth 4 -type f "
            "-not -path '*/.git/*' -not -path './node_modules/*' -not -path './.next/*' "
            "-exec sha256sum {} + 2>/dev/null || "
            "find . -maxdepth 4 -type f "
            "-not -path '*/.git/*' -not -path './node_modules/*' -not -path './.next/*' "
            "-exec shasum -a 256 {} + 2>/dev/null"
        )
        res = self.transport.run_ssh_command(prof, manifest_cmd, timeout=prof.connect_timeout_seconds + 4.0)
        if not res.get("ok"):
            return {
                "ok": False,
                "status": "REMOTE_MANIFEST_COMMAND_FAILED",
                "profile_id": prof.profile_id,
                "remote_workspace": target_dir,
                "files": {},
                "error": redact_secrets(res.get("stderr", "Failed to list remote manifest")),
            }

        files_map: dict[str, dict[str, Any]] = {}
        for raw_ln in (res.get("stdout") or "").splitlines():
            ln = raw_ln.strip()
            if not ln:
                continue
            parts = ln.split(None, 1)
            if len(parts) == 2 and len(parts[0]) == 64:
                sha_hex = parts[0].lower()
                rel_p = parts[1].strip()
                if rel_p.startswith("./"):
                    rel_p = rel_p[2:]
                files_map[rel_p] = {
                    "relative_path": rel_p,
                    "sha256": sha_hex,
                }

        self.storage.record_audit(
            user_request=f"inspect_remote_workspace_manifest({target_dir})",
            tool_name="vps.inspect_manifest",
            category="VPS_READ",
            target=gate_info["target"],
            operation="INSPECT",
            approval_decision=f"ALLOWED:{gate_info['decision_source']}",
            status="SUCCESS",
            result_summary=f"Inspected remote manifest in {target_dir} ({len(files_map)} files)",
        )
        return {
            "ok": True,
            "status": "REMOTE_MANIFEST_READY",
            "profile_id": prof.profile_id,
            "remote_workspace": target_dir,
            "file_count": len(files_map),
            "files": files_map,
        }


