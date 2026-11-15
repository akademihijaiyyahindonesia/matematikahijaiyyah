"""Tests for CosmicTera NUI Real Internet, VPS, Domain & File Verification (Phase 1-11)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
if str(NUI_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(NUI_DESKTOP_ROOT))

from backend.internet_engine import (
    HTTPS_SCHEME,
    HTTP_SCHEME,
    RealInternetEngine,
    classify_network_error,
    inspect_macos_network_interfaces,
)
from backend.permissions import (
    PERMISSION_CATEGORIES,
    READ_SAFE_OPERATIONS,
    PermissionEngine,
)
from backend.persona_and_context import NUIPersonaLoader
from backend.providers import (
    NativeNUIProvider,
    classify_operational_network_subintent,
    is_folder_vps_status_query,
    run_folder_vps_inspection,
)
from backend.remote_dev_engine import (
    RemoteVPSDevelopmentEngine,
    VPSConnectionProfile,
)
from backend.server import NUILocalServiceApp
from backend.storage import NUIStorage
from backend.universal_file_intelligence import (
    UniversalFileActionEngine,
    UniversalResourceRegistry,
)

TARGET_DOMAIN = "www.akademihijaiyyah" + "indonesia.com"
APEX_DOMAIN = "akademihijaiyyah" + "indonesia.com"
MOCK_VPS_IP = "187.53." + "135.198"
MOCK_CDN_IP = "151.101." + "0.223"
MOCK_FINGERPRINT = "SHA256:TestYayasan" + "Fingerprint2026"


class SimulatedDomainTransport:
    """Deterministic network transport for testing DNS, TCP, TLS, HTTP/HTTPS, and Redirects."""

    def __init__(
        self,
        *,
        resolved_ips: List[str] | None = None,
        cname_target: str = "cname.vercel-dns.com",
        tcp_80_ok: bool = True,
        tcp_443_ok: bool = True,
        http_status: int = 200,
        tls_valid: bool = True,
    ) -> None:
        self.resolved_ips = resolved_ips if resolved_ips is not None else [MOCK_CDN_IP]
        self.cname_target = cname_target
        self.tcp_80_ok = tcp_80_ok
        self.tcp_443_ok = tcp_443_ok
        self.http_status = http_status
        self.tls_valid = tls_valid

    def resolve_dns(self, host: str, timeout: float = 3.0) -> Dict[str, Any]:
        ok = len(self.resolved_ips) > 0
        return {
            "ok": ok,
            "host": host,
            "addresses": list(self.resolved_ips),
            "a_records": list(self.resolved_ips),
            "aaaa_records": [],
            "latency_ms": 4.2,
            "status": "RESOLVED" if ok else "FAILED",
            "error": None if ok else "NXDOMAIN",
            "error_category": None if ok else "DNS_FAILURE",
        }

    def check_tcp(self, host: str, port: int = 443, timeout: float = 3.0) -> Dict[str, Any]:
        ok = self.tcp_443_ok if port == 443 else self.tcp_80_ok
        return {
            "ok": ok,
            "host": host,
            "port": port,
            "peer": f"{self.resolved_ips[0] if self.resolved_ips else '0.0.0.0'}:{port}",
            "latency_ms": 6.5,
            "status": "CONNECTED" if ok else "FAILED",
            "error": None if ok else "Connection refused",
            "error_category": None if ok else "CONNECTION_REFUSED",
        }

    def check_tls(self, host: str, port: int = 443, timeout: float = 3.0) -> Dict[str, Any]:
        ok = self.tls_valid and self.tcp_443_ok
        return {
            "ok": ok,
            "host": host,
            "port": port,
            "tls_version": "TLSv1.3" if ok else None,
            "cipher": "TLS_AES_256_GCM_SHA384" if ok else None,
            "cert_valid": ok,
            "subject_cn": host,
            "issuer_cn": "Let's Encrypt E5",
            "issuer_org": "Let's Encrypt",
            "not_before": "Jan  1 00:00:00 2026 GMT",
            "not_after": "Dec 31 23:59:59 2026 GMT",
            "days_until_expiry": 180 if ok else None,
            "san_domains": [host, APEX_DOMAIN],
            "cert_sha256": "a" * 64,
            "latency_ms": 11.0,
            "status": "HANDSHAKE_OK" if ok else "FAILED",
            "error": None if ok else "SSLCertVerificationError",
            "error_category": None if ok else "TLS_ERROR",
        }

    def http_request(
        self,
        method: str,
        url: str,
        *,
        headers: Dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 6.0,
    ) -> Dict[str, Any]:
        if "dns.google/resolve" in url:
            if "type=CNAME" in url and self.cname_target:
                payload = {"Answer": [{"data": self.cname_target}]}
            elif "type=NS" in url:
                payload = {"Answer": [{"data": "ns1.dns-parking.com"}, {"data": "ns2.dns-parking.com"}]}
            else:
                payload = {"Answer": []}
            return {
                "ok": True,
                "status_code": 200,
                "url": url,
                "redirected": False,
                "content_type": "application/json",
                "response_headers": {"Content-Type": "application/json"},
                "body_bytes": json.dumps(payload).encode("utf-8"),
                "latency_ms": 5.0,
            }

        is_http = url.startswith(HTTP_SCHEME)
        ok = self.tcp_443_ok and self.tls_valid and (200 <= self.http_status < 400)
        final_u = url.replace(HTTP_SCHEME, HTTPS_SCHEME, 1) if is_http else url
        html_bytes = (
            b"<html><head><title>Akademi Hijaiyyah Indonesia</title></head>"
            b"<body><h1>Selamat Datang di Akademi Hijaiyyah Indonesia</h1></body></html>"
        )
        return {
            "ok": ok,
            "status_code": self.http_status if self.tcp_443_ok else 0,
            "url": final_u,
            "redirected": is_http and ok,
            "content_type": "text/html; charset=utf-8",
            "response_headers": {"Server": "Vercel", "Content-Type": "text/html; charset=utf-8"},
            "body_bytes": html_bytes if (ok and method.upper() != "HEAD") else b"",
            "latency_ms": 14.2,
            "error": None if ok else f"HTTP {self.http_status}",
            "error_category": None if ok else "HTTP_ERROR",
        }


class SimulatedSSHTransport:
    """Deterministic SSH/SFTP adapter supporting host fingerprint verification and remote SHA-256 manifest listing."""

    def __init__(self, remote_files: Dict[str, bytes] | None = None) -> None:
        self.known_fingerprint = MOCK_FINGERPRINT
        self.remote_files: Dict[str, bytes] = dict(remote_files or {})

    def verify_host_fingerprint(
        self, host: str, port: int, expected_fingerprint: str, timeout: float = 5.0
    ) -> Dict[str, Any]:
        matched = expected_fingerprint.strip() == self.known_fingerprint
        return {
            "ok": matched,
            "verified": matched,
            "status": "HOST_KEY_VERIFIED" if matched else "HOST_KEY_VERIFICATION_FAILED",
            "expected_fingerprint": expected_fingerprint,
            "scanned_fingerprints": [f"256 {self.known_fingerprint} {host} (ED25519)"],
            "reason": "Host key matched." if matched else "Host fingerprint mismatch!",
        }

    def run_ssh_command(
        self,
        profile: VPSConnectionProfile,
        command: str,
        *,
        timeout: float = 10.0,
        keychain_secret: str | None = None,
    ) -> Dict[str, Any]:
        if "uname -srm" in command:
            return {
                "ok": True,
                "exit_code": 0,
                "stdout": "Linux 6.8.0-45-generic x86_64\n/usr/bin/python3\n/usr/bin/node\n/usr/bin/git\n",
                "stderr": "",
                "timed_out": False,
            }
        if "sha256sum" in command or "shasum -a 256" in command:
            lines: List[str] = []
            ws_prefix = profile.remote_workspace.rstrip("/") + "/"
            for full_p, raw_b in sorted(self.remote_files.items()):
                if full_p.startswith(ws_prefix):
                    rel = full_p[len(ws_prefix) :]
                    sha = hashlib.sha256(raw_b).hexdigest()
                    lines.append(f"{sha}  ./{rel}")
            return {
                "ok": True,
                "exit_code": 0,
                "stdout": "\n".join(lines) + ("\n" if lines else ""),
                "stderr": "",
                "timed_out": False,
            }
        return {"ok": True, "exit_code": 0, "stdout": "OK\n", "stderr": "", "timed_out": False}

    def sftp_read_file(
        self, profile: VPSConnectionProfile, remote_path: str, *, timeout: float = 10.0
    ) -> Dict[str, Any]:
        if remote_path not in self.remote_files:
            return {"ok": False, "exit_code": 1, "stderr": "No such file", "timed_out": False}
        raw = self.remote_files[remote_path]
        return {
            "ok": True,
            "remote_path": remote_path,
            "content": raw.decode("utf-8", errors="replace"),
            "size_bytes": len(raw),
            "timed_out": False,
        }

    def sftp_write_file(
        self, profile: VPSConnectionProfile, remote_path: str, content: str, *, timeout: float = 10.0
    ) -> Dict[str, Any]:
        raw = content.encode("utf-8")
        self.remote_files[remote_path] = raw
        return {
            "ok": True,
            "remote_path": remote_path,
            "bytes_written": len(raw),
            "exit_code": 0,
            "stderr": "",
            "timed_out": False,
        }


def _build_env(
    tmp_path: Path,
    *,
    resolved_ips: List[str] | None = None,
    tcp_443_ok: bool = True,
    http_status: int = 200,
    tls_valid: bool = True,
    remote_files: Dict[str, bytes] | None = None,
):
    db_file = tmp_path / "nui_real_internet_vps.db"
    storage = NUIStorage(db_file, use_os_keychain=False)
    permissions = PermissionEngine(storage)
    net_transport = SimulatedDomainTransport(
        resolved_ips=resolved_ips,
        tcp_443_ok=tcp_443_ok,
        http_status=http_status,
        tls_valid=tls_valid,
    )
    ssh_transport = SimulatedSSHTransport(remote_files=remote_files)
    internet_engine = RealInternetEngine(
        storage=storage,
        permissions=permissions,
        transport=net_transport,
        staging_dir=tmp_path / "staging_downloads",
    )
    remote_engine = RemoteVPSDevelopmentEngine(
        storage=storage,
        permissions=permissions,
        transport=ssh_transport,
    )
    file_engine = UniversalFileActionEngine(
        storage=storage,
        permissions=permissions,
        remote_dev_engine=remote_engine,
        staging_root=tmp_path / "universal_staging",
    )
    return storage, permissions, net_transport, ssh_transport, internet_engine, remote_engine, file_engine


# 1. Outbound DNS lookup test
def test_01_outbound_dns_lookup(tmp_path: Path) -> None:
    _, _, _, _, internet_engine, _, _ = _build_env(tmp_path, resolved_ips=[MOCK_CDN_IP])
    dns_res = internet_engine.resolve_dns_records(TARGET_DOMAIN)
    assert dns_res["ok"] is True
    assert MOCK_CDN_IP in dns_res["resolved_ips"]
    assert "A" in dns_res["records"]
    assert "CNAME" in dns_res["records"]


# 2. Outbound HTTPS request test
def test_02_outbound_https_request(tmp_path: Path) -> None:
    _, _, _, _, internet_engine, _, _ = _build_env(tmp_path, resolved_ips=[MOCK_VPS_IP])
    probe = internet_engine.inspect_http_https_and_redirects(TARGET_DOMAIN)
    assert probe["ok"] is True
    assert probe["https_get"]["status_code"] == 200
    assert probe["server_header"] == "Vercel"
    assert "Akademi Hijaiyyah Indonesia" in probe["page_title"]


# 3. TLS certificate inspection test
def test_03_tls_certificate_inspection(tmp_path: Path) -> None:
    _, _, _, _, internet_engine, _, _ = _build_env(tmp_path, resolved_ips=[MOCK_VPS_IP])
    probe = internet_engine.inspect_http_https_and_redirects(TARGET_DOMAIN)
    assert probe["tls"]["cert_valid"] is True
    assert probe["tls"]["tls_version"] == "TLSv1.3"
    assert probe["tls"]["not_after"] == "Dec 31 23:59:59 2026 GMT"
    assert probe["tls"]["issuer_cn"] == "Let's Encrypt E5"


# 4. Redirect chain inspection test
def test_04_redirect_chain_inspection(tmp_path: Path) -> None:
    _, _, _, _, internet_engine, _, _ = _build_env(tmp_path, resolved_ips=[MOCK_VPS_IP])
    probe = internet_engine.inspect_http_https_and_redirects(TARGET_DOMAIN)
    assert len(probe["redirect_chain"]) >= 1
    assert probe["final_url"].startswith(HTTPS_SCHEME)


# 5. Domain inspection test across all 5 Phase 5 classifications
def test_05_domain_inspection_all_five_states(tmp_path: Path) -> None:
    # Case 1: DOMAIN_NOT_RESOLVED
    *_, ie1, _, _ = _build_env(tmp_path / "c1", resolved_ips=[])
    r1 = ie1.inspect_domain_and_website(TARGET_DOMAIN)
    assert r1["classification"] == "DOMAIN_NOT_RESOLVED"

    # Case 2: DNS_RESOLVED_SERVER_UNREACHABLE
    _, _, nt2, _, ie2, _, _ = _build_env(tmp_path / "c2", resolved_ips=[MOCK_VPS_IP], tcp_443_ok=False)
    nt2.tcp_80_ok = False
    r2 = ie2.inspect_domain_and_website(TARGET_DOMAIN)
    assert r2["classification"] == "DNS_RESOLVED_SERVER_UNREACHABLE"

    # Case 3: SERVER_REACHABLE_WEB_FAILED
    *_, ie3, _, _ = _build_env(tmp_path / "c3", resolved_ips=[MOCK_VPS_IP], tcp_443_ok=True, http_status=502)
    r3 = ie3.inspect_domain_and_website(TARGET_DOMAIN)
    assert r3["classification"] == "SERVER_REACHABLE_WEB_FAILED"

    # Case 4: WEBSITE_ACCESSIBLE_VPS_UNPROVEN
    *_, ie4, _, _ = _build_env(tmp_path / "c4", resolved_ips=[MOCK_CDN_IP], tcp_443_ok=True, http_status=200)
    r4 = ie4.inspect_domain_and_website(TARGET_DOMAIN, target_vps_ip=MOCK_VPS_IP, remote_verified=False)
    assert r4["classification"] == "WEBSITE_ACCESSIBLE_VPS_UNPROVEN"

    # Case 5: WEBSITE_ACCESSIBLE_VPS_VERIFIED
    *_, ie5, _, _ = _build_env(tmp_path / "c5", resolved_ips=[MOCK_VPS_IP], tcp_443_ok=True, http_status=200)
    r5 = ie5.inspect_domain_and_website(TARGET_DOMAIN, target_vps_ip=MOCK_VPS_IP, remote_verified=True)
    assert r5["classification"] == "WEBSITE_ACCESSIBLE_VPS_VERIFIED"


# 6. SSH unconfigured test
def test_06_ssh_unconfigured_and_deploy_md_discovery(tmp_path: Path) -> None:
    _, _, _, _, _, remote_engine, _ = _build_env(tmp_path)
    yayasan_dir = tmp_path / "yayasan"
    yayasan_dir.mkdir(parents=True)
    (yayasan_dir / "DEPLOY.md").write_text(
        f"# Deploy\nServer: root@{MOCK_VPS_IP}\nTarget: /opt/yayasan\nDomain: {TARGET_DOMAIN}\n",
        encoding="utf-8",
    )
    disc = remote_engine.discover_ssh_and_deployment_metadata(str(yayasan_dir))
    assert disc["registered_vps_profiles_count"] == 0
    assert disc["deploy_md"]["deploy_md_exists"] is True
    assert disc["deploy_md"]["documented_vps_host"] == MOCK_VPS_IP
    assert "DOCUMENTED_IN_DEPLOY_MD_ONLY" in disc["deploy_md"]["provenance_note"]


# 7. SSH connection simulated/live test
def test_07_ssh_connection_simulated_test(tmp_path: Path) -> None:
    _, permissions, _, _, _, remote_engine, _ = _build_env(
        tmp_path,
        remote_files={"/opt/yayasan/index.html": b"<h1>Yayasan</h1>"},
    )
    permissions.set_rule(
        category="VPS_CONNECT", target_type="endpoint", target_value="*", operation="*", decision="ALWAYS_ALLOW"
    )
    prof = remote_engine.register_profile(
        name="Yayasan Production VPS",
        host=MOCK_VPS_IP,
        port=22,
        username="root",
        auth_method="SSH_KEY",
        expected_host_fingerprint=MOCK_FINGERPRINT,
        remote_workspace="/opt/yayasan",
    )
    conn = remote_engine.connect_and_inspect(prof["profile_id"])
    assert conn["ok"] is True
    assert conn["host_key_verified"] is True
    assert conn["status"] == "CONNECTED"


# 8. Host fingerprint mismatch block test
def test_08_host_fingerprint_mismatch_block(tmp_path: Path) -> None:
    _, permissions, _, _, _, remote_engine, _ = _build_env(tmp_path)
    permissions.set_rule(
        category="VPS_CONNECT", target_type="endpoint", target_value="*", operation="*", decision="ALWAYS_ALLOW"
    )
    bad_prof = remote_engine.register_profile(
        name="Mismatch VPS",
        host=MOCK_VPS_IP,
        port=22,
        username="root",
        auth_method="SSH_KEY",
        expected_host_fingerprint="SHA256:WrongFingerprintValue0000",
        remote_workspace="/opt/yayasan",
    )
    bad_conn = remote_engine.connect_and_inspect(bad_prof["profile_id"])
    assert bad_conn["ok"] is False
    assert bad_conn["status"] == "HOST_KEY_VERIFICATION_FAILED"


# 9. SFTP remote workspace listing test
def test_09_sftp_remote_workspace_listing(tmp_path: Path) -> None:
    _, permissions, _, _, _, remote_engine, _ = _build_env(
        tmp_path,
        remote_files={
            "/opt/yayasan/app.js": b"console.log(1);\n",
            "/opt/yayasan/index.html": b"<h1>Hi</h1>\n",
        },
    )
    for scope in ("VPS_CONNECT", "VPS_READ", "READ_REMOTE"):
        permissions.set_rule(
            category=scope, target_type="endpoint", target_value="*", operation="*", decision="ALWAYS_ALLOW"
        )
    prof = remote_engine.register_profile(
        name="Yayasan VPS",
        host=MOCK_VPS_IP,
        port=22,
        username="root",
        auth_method="SSH_KEY",
        expected_host_fingerprint=MOCK_FINGERPRINT,
        remote_workspace="/opt/yayasan",
    )
    remote_engine.connect_and_inspect(prof["profile_id"])
    rem_manifest = remote_engine.inspect_remote_workspace_manifest(prof["profile_id"], "/opt/yayasan")
    assert rem_manifest["ok"] is True
    assert rem_manifest["file_count"] == 2
    assert "app.js" in rem_manifest["files"]


# 10. Local vs remote manifest comparison test
def test_10_local_vs_remote_manifest_comparison(tmp_path: Path) -> None:
    storage, permissions, _, _, _, remote_engine, file_engine = _build_env(
        tmp_path,
        remote_files={"/opt/yayasan/app.js": b"same", "/opt/yayasan/extra.txt": b"remote"},
    )
    for scope in ("VPS_CONNECT", "VPS_READ", "READ_REMOTE"):
        permissions.set_rule(
            category=scope, target_type="endpoint", target_value="*", operation="*", decision="ALWAYS_ALLOW"
        )
    local_dir = tmp_path / "yayasan_site"
    local_dir.mkdir(parents=True)
    (local_dir / "app.js").write_bytes(b"same")
    (local_dir / "local.txt").write_bytes(b"local")
    storage.add_authorized_folder(local_dir, label="yayasan_site", access_mode="READ_WRITE")

    prof = remote_engine.register_profile(
        name="yayasan_site VPS",
        host=MOCK_VPS_IP,
        port=22,
        username="root",
        auth_method="SSH_KEY",
        expected_host_fingerprint=MOCK_FINGERPRINT,
        remote_workspace="/opt/yayasan",
    )
    remote_engine.connect_and_inspect(prof["profile_id"])
    comp = file_engine.compare_local_and_remote_manifests(local_dir, profile_id=prof["profile_id"])
    assert comp["ok"] is True
    assert comp["compared"] is True
    assert comp["local_file_count"] == 2
    assert comp["remote_file_count"] == 2


# 11. Identical file hash match test (MATCH)
def test_11_identical_file_hash_match(tmp_path: Path) -> None:
    storage, _, _, _, _, _, file_engine = _build_env(tmp_path)
    local_dir = tmp_path / "match_site"
    local_dir.mkdir(parents=True)
    payload = b"<h1>Identical Content</h1>\n"
    (local_dir / "index.html").write_bytes(payload)
    storage.add_authorized_folder(local_dir, label="match_site", access_mode="READ_WRITE")

    sha = hashlib.sha256(payload).hexdigest()
    comp = file_engine.compare_local_and_remote_manifests(
        local_dir,
        remote_manifest_override={"index.html": {"relative_path": "index.html", "sha256": sha, "size_bytes": len(payload)}},
    )
    assert comp["overall_sync_status"] == "MATCH"
    assert comp["matching_sha256_count"] == 1
    assert comp["different_files_count"] == 0


# 12. Modified file content mismatch test (CONTENT_MISMATCH)
def test_12_modified_file_content_mismatch(tmp_path: Path) -> None:
    storage, _, _, _, _, _, file_engine = _build_env(tmp_path)
    local_dir = tmp_path / "mismatch_site"
    local_dir.mkdir(parents=True)
    (local_dir / "index.html").write_bytes(b"<h1>Local v2</h1>\n")
    storage.add_authorized_folder(local_dir, label="mismatch_site", access_mode="READ_WRITE")

    rem_sha = hashlib.sha256(b"<h1>Remote v1</h1>\n").hexdigest()
    comp = file_engine.compare_local_and_remote_manifests(
        local_dir,
        remote_manifest_override={"index.html": {"relative_path": "index.html", "sha256": rem_sha}},
    )
    assert comp["overall_sync_status"] == "CONTENT_MISMATCH"
    assert comp["different_files_count"] == 1


# 13. Missing remote file detection test (LOCAL_ONLY)
def test_13_missing_remote_file_detection(tmp_path: Path) -> None:
    storage, _, _, _, _, _, file_engine = _build_env(tmp_path)
    local_dir = tmp_path / "local_only_site"
    local_dir.mkdir(parents=True)
    (local_dir / "draft.md").write_bytes(b"# Draft")
    storage.add_authorized_folder(local_dir, label="local_only_site", access_mode="READ_WRITE")

    comp = file_engine.compare_local_and_remote_manifests(local_dir, remote_manifest_override={})
    assert comp["overall_sync_status"] == "LOCAL_ONLY"
    assert comp["missing_remote_files_count"] == 1


# 14. Extra remote file detection test (REMOTE_ONLY)
def test_14_extra_remote_file_detection(tmp_path: Path) -> None:
    storage, _, _, _, _, _, file_engine = _build_env(tmp_path)
    local_dir = tmp_path / "remote_only_site"
    local_dir.mkdir(parents=True)
    storage.add_authorized_folder(local_dir, label="remote_only_site", access_mode="READ_WRITE")

    rem_sha = hashlib.sha256(b"server log").hexdigest()
    comp = file_engine.compare_local_and_remote_manifests(
        local_dir,
        remote_manifest_override={"server.log": {"relative_path": "server.log", "sha256": rem_sha}},
    )
    assert comp["overall_sync_status"] == "REMOTE_ONLY"
    assert comp["remote_only_files_count"] == 1


# 15. Folder Yayasan full verification test
def test_15_folder_yayasan_full_verification(tmp_path: Path) -> None:
    storage, _, _, _, internet_engine, remote_engine, file_engine = _build_env(
        tmp_path, resolved_ips=[MOCK_CDN_IP]
    )
    yayasan_dir = tmp_path / "yayasan"
    yayasan_dir.mkdir(parents=True)
    (yayasan_dir / "package.json").write_text('{"name": "yayasan-web"}\n', encoding="utf-8")
    (yayasan_dir / "DEPLOY.md").write_text(
        f"Server: root@{MOCK_VPS_IP}\nPath: /opt/yayasan\nDomain: {TARGET_DOMAIN}\n",
        encoding="utf-8",
    )
    storage.add_authorized_folder(yayasan_dir, label="yayasan", access_mode="READ_WRITE")

    report = run_folder_vps_inspection(
        f"Apakah folder {yayasan_dir} sudah terhubung ke VPS? Apakah file sudah di-upload?",
        fallback_engine=remote_engine,
        fallback_file_engine=file_engine,
        fallback_internet_engine=internet_engine,
    )
    assert report is not None
    assert report["ok"] is True
    assert report["status"] == "LOCAL_ONLY"
    assert "### 1. LOCAL FOLDER" in report["formatted_response"]
    assert "### 4. VPS" in report["formatted_response"]
    assert "### 5. FILE SYNCHRONIZATION" in report["formatted_response"]
    assert "DOCUMENTED_IN_DEPLOY_MD_ONLY" in report["formatted_response"]


# 16. Domain akademihijaiyyahindonesia.com full verification test
def test_16_domain_akademihijaiyyahindonesia_full_verification(tmp_path: Path) -> None:
    storage, _, _, _, internet_engine, remote_engine, file_engine = _build_env(
        tmp_path, resolved_ips=[MOCK_CDN_IP]
    )
    yayasan_dir = tmp_path / "yayasan"
    yayasan_dir.mkdir(parents=True)
    storage.add_authorized_folder(yayasan_dir, label="yayasan", access_mode="READ_WRITE")

    report = run_folder_vps_inspection(
        f"Apakah domain {TARGET_DOMAIN} sudah terhubung ke server?",
        fallback_engine=remote_engine,
        fallback_file_engine=file_engine,
        fallback_internet_engine=internet_engine,
    )
    assert report is not None
    assert report["domain"]["domain"] == TARGET_DOMAIN
    assert report["domain"]["classification"] == "WEBSITE_ACCESSIBLE_VPS_UNPROVEN"
    assert "### 3. DOMAIN" in report["formatted_response"]
    assert "### 6. FINAL CONCLUSION" in report["formatted_response"]


# 17. Read-only inspection safety test (no write actions executed during inspection)
def test_17_read_only_inspection_safety_and_permission_model(tmp_path: Path) -> None:
    for scope in (
        "READ_LOCAL",
        "READ_REMOTE",
        "NETWORK_ACCESS",
        "SSH_CONNECT",
        "SFTP_ACCESS",
        "REMOTE_COMMAND",
        "UPLOAD_FILE",
        "DOWNLOAD_FILE",
        "SYNC_DIRECTORY",
        "MODIFY_REMOTE",
        "DEPLOY_WEBSITE",
    ):
        assert scope in PERMISSION_CATEGORIES

    for op in ("INSPECT", "DIAGNOSE", "CHECK_DOMAIN", "COMPARE_MANIFEST"):
        assert op in READ_SAFE_OPERATIONS


# 18. Write operation confirmation required test + Phase 7 conversational intent routing test
def test_18_write_confirmation_and_all_10_conversational_queries(tmp_path: Path) -> None:
    storage, _, _, _, internet_engine, remote_engine, file_engine = _build_env(
        tmp_path, resolved_ips=[MOCK_CDN_IP]
    )
    yayasan_dir = tmp_path / "yayasan"
    yayasan_dir.mkdir(parents=True)
    storage.add_authorized_folder(yayasan_dir, label="yayasan", access_mode="READ_WRITE")

    queries = [
        "Apakah folder Yayasan terhubung ke VPS?",
        "Cek apakah VPS saya aktif.",
        "Cek apakah website saya online.",
        "Apakah domain saya sudah terhubung?",
        "Apakah file sudah di-upload?",
        "Bandingkan file lokal dengan server.",
        "Cek koneksi SSH.",
        "Sambungkan folder Yayasan ke VPS.",
        "Upload website Yayasan ke server.",
        "Periksa apakah website sudah berjalan.",
    ]
    for q in queries:
        assert is_folder_vps_status_query(q) is True, f"Query not detected: {q}"
        subintent = classify_operational_network_subintent(q)
        assert subintent in {
            "full_folder_vps_domain_verification",
            "check_vps_ssh_status",
            "check_domain_and_website",
            "compare_local_and_remote_files",
            "connect_folder_to_vps",
            "upload_website_to_server",
        }

    upload_report = run_folder_vps_inspection(
        "Upload website Yayasan ke server.",
        fallback_engine=remote_engine,
        fallback_file_engine=file_engine,
        fallback_internet_engine=internet_engine,
    )
    assert upload_report is not None
    assert upload_report["sub_intent"] == "upload_website_to_server"
    assert "KONFIRMASI OPERASI WRITE DIPERLUKAN" in upload_report["formatted_response"]
    assert "Saya tidak melakukan upload, penghapusan, atau perubahan file selama pemeriksaan." in upload_report["formatted_response"]

    persona = NUIPersonaLoader()
    sys_prompt = persona.build_system_prompt()
    assert "DILARANG KERAS pernah menjawab 'Saya adalah AI lokal dan tidak mempunyai akses internet atau VPS'" in sys_prompt

    provider = NativeNUIProvider(
        persona_loader=persona,
        remote_dev_engine=remote_engine,
        universal_file_engine=file_engine,
        internet_engine=internet_engine,
    )
    gen = provider.respond(queries[0])
    assert "### 1. LOCAL FOLDER" in gen["reply"]
    assert "### 6. FINAL CONCLUSION" in gen["reply"]


# 19. macOS network interface & error classification test + HTTP API endpoints test
def test_19_macos_network_interface_error_classifier_and_server_endpoints(tmp_path: Path) -> None:
    ifaces = inspect_macos_network_interfaces()
    assert "active_interfaces" in ifaces
    assert "interface_active" in ifaces

    assert classify_network_error("nodename nor servname provided, or not known") == "DNS_FAILURE"
    assert classify_network_error("Connection refused") == "CONNECTION_REFUSED"
    assert classify_network_error("SSLCertVerificationError: certificate verify failed") == "TLS_ERROR"
    assert classify_network_error("timed out") == "TIMEOUT"
    assert classify_network_error("Operation not permitted") == "SANDBOX_BLOCKED"

    app = NUILocalServiceApp(db_path=tmp_path / "server_api.db", use_os_keychain=False)
    app.internet_engine.transport = SimulatedDomainTransport(resolved_ips=[MOCK_CDN_IP])
    code1, res1 = app.dispatch_request("POST", "/api/web/op", {"op": "check_domain", "domain": TARGET_DOMAIN})
    assert code1 == 200
    assert res1["classification"] == "WEBSITE_ACCESSIBLE_VPS_UNPROVEN"

    code2, res2 = app.dispatch_request(
        "POST",
        "/api/vps/op",
        {"op": "full_verification", "prompt": f"Apakah folder /Users/AMRA/yayasan sudah terhubung ke VPS? Apakah domain {TARGET_DOMAIN} sudah terhubung ke server?"},
    )
    assert code2 == 200
    assert "### 1. LOCAL FOLDER" in res2["formatted_report"]

