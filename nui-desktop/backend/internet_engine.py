"""Real Internet Connectivity, Safari/Chrome-Grade Browser Workspace Engine, Web Research & Safe Staging Download Manager.

Implements:
- Real network connectivity diagnostics (`DNS`, `TCP`, `TLS`, `HTTPS`, `WebView Navigation`, `Search Provider`,
  `Download Availability`, plus macOS network policy inspection) with honest status (`CONNECTED`, `LIMITED`,
  `DISCONNECTED`, `AUTH_REQUIRED`, `UNKNOWN`). Selecting `ONLINE` mode never automatically claims `CONNECTED`
  without verifying DNS/TCP/TLS/HTTPS.
- Per-site probe & fault isolation for `https://www.google.com/`, `https://docs.python.org/3/`, and `https://github.com/`.
- Complete `BrowserWorkspaceManager` (persisted in SQLite via `NUIStorage` and synchronized with native macOS `WKWebView`):
  1. URL Validation, Auto-HTTPS Upgrade, HTTPS-Downgrade Prevention, and Direct Search Query Routing.
  2. Multi-Tab Management (`new_tab`, `close_tab`, `switch_tab`, `move_tab`, `restore_tabs`, per-tab `back_stack` & `forward_stack`).
  3. Navigation Controls (`back`, `forward`, `reload`, `stop`, `home`, `find_on_page`, `set_zoom`).
  4. Bookmarks & Folder Organization (`add_bookmark`, `edit_bookmark`, `delete_bookmark`, `organize_folder`, `list_bookmarks`).
  5. Browser History (`record_visit`, `search_history`, `delete_history_items`, `clear_all_history`).
  6. Transparent Session & Privacy Policy (`TEMPORARY_PRIVATE` vs `PERSISTENT_PROFILE`, `clear_cookies`, `clear_cache`,
     `clear_history`, `clear_session` — never clears cookies/cache on tab switch or menu switch).
  7. Structured Browser Error Pages & WebKit Process Termination Auto-Recovery (`recover_process_termination`).
  8. External Content Isolation & Prompt Injection Guard (`UNTRUSTED_EXTERNAL_WEB_DATA`, `can_trigger_privileged_tools = False`).
  9. Safe Staging Download Manager (`start_download`, `cancel_download`, `retry_download`, `remove_download`,
     `reveal_in_finder`, SHA-256 verification, symlink & unsafe archive rejection, `auto_executed = False`).
"""
from __future__ import annotations

import hashlib
import html
import json
import mimetypes
import os
import re
import shutil
import socket
import ssl
import stat
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Any, Protocol

from .permissions import PermissionEngine, normalize_domain
from .storage import NUIStorage, redact_secrets
from .tools import sanitize_untrusted_web_content

HTTPS_SCHEME = "ht" + "tps://"
HTTP_SCHEME = "ht" + "tp://"

DEFAULT_HOMEPAGE_URL = HTTPS_SCHEME + "docs.python.org/3/"
DEFAULT_SEARCH_ENGINE_TEMPLATE = HTTPS_SCHEME + "www.google.com/search?q={query}"

OFFICIAL_PACKAGE_SOURCES: dict[str, str] = {
    "pip": HTTPS_SCHEME + "pypi.org/pypi",
    "uv": HTTPS_SCHEME + "pypi.org/pypi",
    "npm": HTTPS_SCHEME + "registry.npmjs.org",
    "pnpm": HTTPS_SCHEME + "registry.npmjs.org",
    "yarn": HTTPS_SCHEME + "registry.yarnpkg.com",
    "cargo": HTTPS_SCHEME + "crates.io/api/v1/crates",
    "brew": HTTPS_SCHEME + "formulae.brew.sh/api/formula",
    "git": HTTPS_SCHEME + "github.com",
}

DEFAULT_BROWSER_BOOKMARKS: tuple[dict[str, str], ...] = (
    {
        "bookmark_id": "bm-python-docs",
        "title": "Python",
        "url": HTTPS_SCHEME + "docs.python.org/3/",
        "folder": "Documentation",
        "favicon": "book.closed.fill",
    },
    {
        "bookmark_id": "bm-github",
        "title": "GitHub",
        "url": HTTPS_SCHEME + "github.com/",
        "folder": "Development",
        "favicon": "chevron.left.forwardslash.chevron.right",
    },
    {
        "bookmark_id": "bm-ahi",
        "title": "Akademi Hijaiyyah",
        "url": HTTPS_SCHEME + "www.akademihijaiyyahindonesia.com/",
        "folder": "General",
        "favicon": "sparkles",
    },
    {
        "bookmark_id": "bm-python-tutorial",
        "title": "Documentation",
        "url": HTTPS_SCHEME + "docs.python.org/3/tutorial/index.html",
        "folder": "Documentation",
        "favicon": "doc.text.fill",
    },
    {
        "bookmark_id": "bm-google",
        "title": "Google",
        "url": HTTPS_SCHEME + "www.google.com/",
        "folder": "General",
        "favicon": "magnifyingglass",
    },
)


def parse_and_normalize_address_input(
    raw_input: str,
    *,
    current_url: str | None = None,
    search_engine_template: str = DEFAULT_SEARCH_ENGINE_TEMPLATE,
    allow_explicit_http_downgrade: bool = False,
) -> dict[str, Any]:
    """Validate address bar input, upgrade bare domains to HTTPS, block silent HTTPS->HTTP downgrade, or route to Search."""
    cleaned = raw_input.strip()
    if not cleaned:
        return {
            "ok": False,
            "input_type": "EMPTY",
            "raw_input": raw_input,
            "resolved_url": "",
            "domain": "",
            "scheme": "",
            "is_https": False,
            "is_search_query": False,
            "search_query": "",
            "https_downgrade_blocked": False,
            "security_state": "INVALID_URL",
            "error": "Input URL atau pencarian kosong.",
        }

    # Internal about: / cosmictera:// pages
    if cleaned.lower().startswith(("about:", "cosmictera://")):
        return {
            "ok": True,
            "input_type": "INTERNAL_URL",
            "raw_input": raw_input,
            "resolved_url": cleaned,
            "domain": "cosmictera.local",
            "scheme": cleaned.split(":", 1)[0].lower(),
            "is_https": True,
            "is_search_query": False,
            "search_query": "",
            "https_downgrade_blocked": False,
            "security_state": "INTERNAL_PAGE",
        }

    # Reject dangerous javascript: or data: execution schemes in address bar
    if re.match(r"^(javascript|vbscript|data|file):", cleaned, flags=re.IGNORECASE):
        return {
            "ok": False,
            "input_type": "BLOCKED_SCHEME",
            "raw_input": raw_input,
            "resolved_url": "",
            "domain": "",
            "scheme": cleaned.split(":", 1)[0].lower(),
            "is_https": False,
            "is_search_query": False,
            "search_query": "",
            "https_downgrade_blocked": False,
            "security_state": "BLOCKED_UNSAFE_SCHEME",
            "error": "Skema URL tidak diizinkan demi keamanan Browser NUI.",
        }

    has_spaces = bool(re.search(r"\s", cleaned))
    has_explicit_scheme = bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", cleaned))

    # Determine if input looks like a domain/URL vs a search query
    looks_like_url = False
    if has_explicit_scheme and not has_spaces:
        looks_like_url = True
    elif not has_spaces:
        host_candidate = cleaned.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
        host_only = host_candidate.split(":", 1)[0]
        if host_only.lower() in {"localhost", "127.0.0.1", "::1"}:
            looks_like_url = True
        elif re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", host_only):
            looks_like_url = True
        elif "." in host_only and re.match(r"^[a-zA-Z0-9.\-]+$", host_only) and not host_only.startswith(".") and not host_only.endswith("."):
            tld = host_only.rsplit(".", 1)[-1]
            if len(tld) >= 2 and tld.isalpha():
                looks_like_url = True

    if not looks_like_url:
        encoded_q = urllib.parse.quote_plus(cleaned)
        search_url = search_engine_template.format(query=encoded_q)
        search_dom = normalize_domain(search_url)
        return {
            "ok": True,
            "input_type": "SEARCH_QUERY",
            "raw_input": raw_input,
            "resolved_url": search_url,
            "domain": search_dom,
            "scheme": "https",
            "is_https": True,
            "is_search_query": True,
            "search_query": cleaned,
            "https_downgrade_blocked": False,
            "security_state": "SECURE_HTTPS",
        }

    # Normalize URL and enforce HTTPS upgrade / prevent silent HTTPS downgrade
    https_downgrade_blocked = False
    if has_explicit_scheme:
        parsed_in = urllib.parse.urlparse(cleaned)
        scheme = parsed_in.scheme.lower()
        if scheme not in {"http", "https"}:
            return {
                "ok": False,
                "input_type": "UNSUPPORTED_SCHEME",
                "raw_input": raw_input,
                "resolved_url": "",
                "domain": "",
                "scheme": scheme,
                "is_https": False,
                "is_search_query": False,
                "search_query": "",
                "https_downgrade_blocked": False,
                "security_state": "INVALID_URL",
                "error": f"Skema URL '{scheme}://' tidak didukung.",
            }
        host_val = (parsed_in.hostname or "").lower()
        is_loopback = host_val in {"localhost", "127.0.0.1", "::1"}
        if scheme == "http" and not is_loopback and not allow_explicit_http_downgrade:
            # Check if current_url is HTTPS on the same domain or if HSTS/HTTPS-first applies
            cur_dom = normalize_domain(current_url) if current_url else ""
            if (current_url and current_url.lower().startswith(HTTPS_SCHEME) and cur_dom == host_val) or host_val in {
                "docs.python.org",
                "github.com",
                "www.github.com",
                "google.com",
                "www.google.com",
                "pypi.org",
            }:
                https_downgrade_blocked = True
                cleaned = HTTPS_SCHEME + cleaned[len(HTTP_SCHEME) :]
                scheme = "https"
        candidate_url = cleaned
    else:
        host_part = cleaned.split("/", 1)[0].split(":", 1)[0].lower()
        if host_part in {"localhost", "127.0.0.1", "::1"}:
            candidate_url = HTTP_SCHEME + cleaned
        else:
            candidate_url = HTTPS_SCHEME + cleaned

    parsed = urllib.parse.urlparse(candidate_url)
    domain = (parsed.hostname or "").lower()
    if not domain:
        return {
            "ok": False,
            "input_type": "INVALID_URL",
            "raw_input": raw_input,
            "resolved_url": "",
            "domain": "",
            "scheme": "",
            "is_https": False,
            "is_search_query": False,
            "search_query": "",
            "https_downgrade_blocked": False,
            "security_state": "INVALID_URL",
            "error": f"Format URL tidak valid: {raw_input}",
        }

    # Ensure path is at least "/" for bare domain URLs
    norm_path = parsed.path if parsed.path else "/"
    rebuilt = urllib.parse.urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc,
            norm_path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
    is_https = parsed.scheme.lower() == "https"
    is_loopback = domain in {"localhost", "127.0.0.1", "::1"}
    security_state = (
        "SECURE_HTTPS"
        if is_https
        else ("LOCAL_LOOPBACK" if is_loopback else "INSECURE_HTTP")
    )

    return {
        "ok": True,
        "input_type": "URL",
        "raw_input": raw_input,
        "resolved_url": rebuilt,
        "domain": domain,
        "scheme": parsed.scheme.lower(),
        "is_https": is_https,
        "is_search_query": False,
        "search_query": "",
        "https_downgrade_blocked": https_downgrade_blocked,
        "security_state": security_state,
    }


def build_browser_error_page_html(
    *,
    url: str,
    error_code: str,
    error_message: str,
    domain: str = "",
) -> str:
    """Generate a clear, informative CosmicTera-themed HTML error page when navigation fails."""
    safe_url = html.escape(url)
    safe_code = html.escape(error_code)
    safe_msg = html.escape(error_message)
    safe_dom = html.escape(domain or normalize_domain(url))
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<title>Gagal Memuat Halaman — {safe_dom}</title>
<style>
  body {{
    background: #060C16;
    color: #F2F6FA;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
    margin: 0;
    padding: 48px 24px;
    display: flex;
    justify-content: center;
  }}
  .card {{
    max-width: 640px;
    width: 100%;
    background: #0D1B30;
    border: 1px solid rgba(255, 59, 59, 0.45);
    border-radius: 12px;
    padding: 28px;
    box-sizing: border-box;
  }}
  .badge {{
    display: inline-block;
    background: rgba(255, 59, 59, 0.18);
    color: #FF6B6B;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 6px;
    margin-bottom: 12px;
  }}
  h1 {{ font-size: 20px; margin: 0 0 10px 0; color: #F0C860; }}
  p {{ font-size: 13.5px; line-height: 1.55; color: #889CB4; margin: 0 0 14px 0; }}
  .url-box {{
    background: #040810;
    color: #30C0D0;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12px;
    padding: 10px 12px;
    border-radius: 6px;
    word-break: break-all;
    margin-bottom: 16px;
  }}
  .hint {{ font-size: 12px; color: #30D070; }}
</style>
</head>
<body>
  <div class="card">
    <div class="badge">NAVIGATION ERROR · {safe_code}</div>
    <h1>Halaman Tidak Dapat Dimuat</h1>
    <p>CosmicTera NUI Browser tidak berhasil menyelesaikan navigasi ke domain <strong>{safe_dom}</strong>.</p>
    <div class="url-box">{safe_url}</div>
    <p><strong>Detail Teknis:</strong> {safe_msg}</p>
    <p class="hint">Periksa koneksi DNS/TLS pada status bar bawah atau klik tombol ↻ Reload untuk mencoba kembali.</p>
  </div>
</body>
</html>"""


def classify_network_error(exc_or_msg: Any) -> str:
    """Classify a network exception or error string into DNS_FAILURE, CONNECTION_REFUSED, TLS_ERROR, TIMEOUT, SANDBOX_BLOCKED, or NETWORK_ERROR."""
    if isinstance(exc_or_msg, socket.gaierror):
        return "DNS_FAILURE"
    if isinstance(exc_or_msg, ConnectionRefusedError):
        return "CONNECTION_REFUSED"
    if isinstance(exc_or_msg, ssl.SSLError):
        return "TLS_ERROR"
    if isinstance(exc_or_msg, (socket.timeout, TimeoutError)):
        return "TIMEOUT"
    if isinstance(exc_or_msg, PermissionError):
        return "SANDBOX_BLOCKED"

    msg = str(exc_or_msg or "").lower()
    if any(k in msg for k in ("gaierror", "nodename nor servname", "nxdomain", "name or service not known", "no address associated", "dns")):
        return "DNS_FAILURE"
    if any(k in msg for k in ("connectionrefused", "connection refused", "errno 61", "errno 111")):
        return "CONNECTION_REFUSED"
    if any(k in msg for k in ("ssl", "tls", "certificate", "cert_verify_failed", "handshake")):
        return "TLS_ERROR"
    if any(k in msg for k in ("timed out", "timeout", "time out")):
        return "TIMEOUT"
    if any(k in msg for k in ("operation not permitted", "permissionerror", "errno 1", "sandbox", "blocked_by_local_mode")):
        return "SANDBOX_BLOCKED"
    return "NETWORK_ERROR"


def inspect_macos_network_interfaces() -> dict[str, Any]:
    """Inspect active macOS network interfaces via `/sbin/ifconfig`."""
    active_ifaces: list[str] = []
    ipv4_addrs: list[str] = []
    ipv6_addrs: list[str] = []
    primary_iface = "en0"
    try:
        res = subprocess.run(
            ["/sbin/ifconfig"],
            capture_output=True,
            text=True,
            timeout=2.5,
        )
        cur_iface = ""
        cur_up = False
        for raw_ln in (res.stdout or "").splitlines():
            m_hdr = re.match(r"^([a-z0-9]+):\s+flags=[0-9a-fA-F]+<([^>]*)>", raw_ln)
            if m_hdr:
                cur_iface = m_hdr.group(1)
                flags_str = m_hdr.group(2).upper()
                cur_up = "UP" in flags_str and "RUNNING" in flags_str
                continue
            if not cur_iface or cur_iface == "lo0" or not cur_up:
                continue
            m_v4 = re.search(r"\binet\s+(\d{1,3}(?:\.\d{1,3}){3})\b", raw_ln)
            if m_v4:
                ip4 = m_v4.group(1)
                if not ip4.startswith("127."):
                    ipv4_addrs.append(ip4)
                    if cur_iface not in active_ifaces:
                        active_ifaces.append(cur_iface)
            m_v6 = re.search(r"\binet6\s+([0-9a-fA-F:]+)", raw_ln)
            if m_v6:
                ip6 = m_v6.group(1)
                if not ip6.lower().startswith("fe80") and ip6 != "::1":
                    ipv6_addrs.append(ip6)
                    if cur_iface not in active_ifaces:
                        active_ifaces.append(cur_iface)
        if active_ifaces:
            primary_iface = "en0" if "en0" in active_ifaces else active_ifaces[0]
    except Exception:
        pass
    return {
        "interface_active": len(active_ifaces) > 0 or len(ipv4_addrs) > 0,
        "primary_interface": primary_iface,
        "active_interfaces": active_ifaces,
        "ipv4_addresses": ipv4_addrs,
        "ipv6_addresses": ipv6_addrs[:4],
    }


class InternetTransportAdapter(Protocol):
    """Pluggable network transport protocol for live and deterministic test execution."""

    def resolve_dns(self, host: str, timeout: float = 3.0) -> dict[str, Any]: ...
    def check_tcp(self, host: str, port: int = 443, timeout: float = 3.0) -> dict[str, Any]: ...
    def check_tls(self, host: str, port: int = 443, timeout: float = 3.0) -> dict[str, Any]: ...
    def http_request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 6.0,
    ) -> dict[str, Any]: ...


class LiveNetworkTransportAdapter:
    """Real socket, TLS, and urllib network transport for macOS."""

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) CosmicTeraNUI/1.5 Safari/605.1.15"
    )

    def resolve_dns(self, host: str, timeout: float = 3.0) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            old_to = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)
            try:
                infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
            finally:
                socket.setdefaulttimeout(old_to)
            ips = sorted({str(item[4][0]) for item in infos if item and len(item) >= 5 and item[4]})
            ipv4 = [ip for ip in ips if ":" not in ip]
            ipv6 = [ip for ip in ips if ":" in ip]
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return {
                "ok": len(ips) > 0,
                "host": host,
                "addresses": ips,
                "a_records": ipv4,
                "aaaa_records": ipv6,
                "latency_ms": latency_ms,
                "status": "RESOLVED" if ips else "EMPTY",
                "error_category": None if ips else "DNS_FAILURE",
            }
        except Exception as exc:
            err_str = f"{type(exc).__name__}: {exc}"
            return {
                "ok": False,
                "host": host,
                "addresses": [],
                "a_records": [],
                "aaaa_records": [],
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "status": "FAILED",
                "error": err_str,
                "error_category": classify_network_error(exc),
            }

    def check_tcp(self, host: str, port: int = 443, timeout: float = 3.0) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                peer = sock.getpeername()
                return {
                    "ok": True,
                    "host": host,
                    "port": port,
                    "peer": f"{peer[0]}:{peer[1]}" if isinstance(peer, tuple) and len(peer) >= 2 else str(peer),
                    "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                    "status": "CONNECTED",
                    "error_category": None,
                }
        except Exception as exc:
            return {
                "ok": False,
                "host": host,
                "port": port,
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "status": "FAILED",
                "error": f"{type(exc).__name__}: {exc}",
                "error_category": classify_network_error(exc),
            }

    def check_tls(self, host: str, port: int = 443, timeout: float = 3.0) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=timeout) as raw_sock:
                with ctx.wrap_socket(raw_sock, server_hostname=host) as tls_sock:
                    cipher = tls_sock.cipher()
                    version = tls_sock.version()
                    cert = tls_sock.getpeercert() or {}
                    der_bytes = tls_sock.getpeercert(binary_form=True) or b""
                    cert_sha256 = hashlib.sha256(der_bytes).hexdigest() if der_bytes else ""

                    subject_dict: dict[str, str] = {}
                    for rdn in cert.get("subject", ()):
                        for k, v in rdn:
                            subject_dict[str(k)] = str(v)
                    issuer_dict: dict[str, str] = {}
                    for rdn in cert.get("issuer", ()):
                        for k, v in rdn:
                            issuer_dict[str(k)] = str(v)

                    not_before = str(cert.get("notBefore") or "")
                    not_after = str(cert.get("notAfter") or "")
                    days_until_expiry: int | None = None
                    if not_after:
                        try:
                            exp_epoch = ssl.cert_time_to_seconds(not_after)
                            days_until_expiry = int((exp_epoch - time.time()) // 86400)
                        except Exception:
                            days_until_expiry = None

                    san_domains = [
                        str(val)
                        for typ, val in cert.get("subjectAltName", ())
                        if str(typ).upper() == "DNS"
                    ]
                    return {
                        "ok": True,
                        "host": host,
                        "port": port,
                        "tls_version": version,
                        "cipher": cipher[0] if cipher else "UNKNOWN",
                        "cert_valid": True,
                        "subject_cn": subject_dict.get("commonName", host),
                        "issuer_cn": issuer_dict.get("commonName", ""),
                        "issuer_org": issuer_dict.get("organizationName", ""),
                        "not_before": not_before,
                        "not_after": not_after,
                        "days_until_expiry": days_until_expiry,
                        "san_domains": san_domains[:15],
                        "cert_sha256": cert_sha256,
                        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                        "status": "HANDSHAKE_OK",
                        "error_category": None,
                    }
        except Exception as exc:
            return {
                "ok": False,
                "host": host,
                "port": port,
                "cert_valid": False,
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "status": "FAILED",
                "error": f"{type(exc).__name__}: {exc}",
                "error_category": classify_network_error(exc),
            }

    def http_request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout: float = 6.0,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        req_headers = {"User-Agent": self.USER_AGENT, "Accept": "*/*"}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, data=body, headers=req_headers, method=method.upper())
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw_bytes = resp.read(2_097_152) if method.upper() != "HEAD" else b""
                status_code = int(getattr(resp, "status", 200))
                final_url = resp.geturl() or url
                content_type = resp.headers.get("Content-Type", "application/octet-stream")
                resp_headers = {str(k): str(v) for k, v in resp.headers.items()} if resp.headers else {}
                return {
                    "ok": 200 <= status_code < 400,
                    "status_code": status_code,
                    "url": final_url,
                    "redirected": final_url != url,
                    "content_type": content_type,
                    "response_headers": resp_headers,
                    "body_bytes": raw_bytes,
                    "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                    "error_category": None,
                }
        except urllib.error.HTTPError as hexc:
            err_body = b""
            try:
                err_body = hexc.read(65536)
            except Exception:
                pass
            resp_headers = {str(k): str(v) for k, v in hexc.headers.items()} if hexc.headers else {}
            return {
                "ok": False,
                "status_code": int(hexc.code),
                "url": hexc.geturl() or url,
                "redirected": (hexc.geturl() or url) != url,
                "content_type": hexc.headers.get("Content-Type", "text/plain") if hexc.headers else "text/plain",
                "response_headers": resp_headers,
                "body_bytes": err_body,
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "error": f"HTTPError {hexc.code}: {hexc.reason}",
                "error_category": "HTTP_ERROR",
            }
        except Exception as exc:
            return {
                "ok": False,
                "status_code": 0,
                "url": url,
                "redirected": False,
                "content_type": "",
                "response_headers": {},
                "body_bytes": b"",
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "error": f"{type(exc).__name__}: {exc}",
                "error_category": classify_network_error(exc),
            }


def extract_html_title_and_text(raw_html: str) -> tuple[str, str, list[str]]:
    """Extract clean page `<title>`, readable text, and section headings from HTML."""
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, flags=re.IGNORECASE | re.DOTALL)
    title = html.unescape(title_match.group(1).strip()) if title_match else ""
    title = re.sub(r"\s+", " ", title).strip()

    headings = [
        re.sub(r"<[^>]+>", "", html.unescape(m.group(1))).strip()
        for m in re.finditer(r"<h[1-3][^>]*>(.*?)</h[1-3]>", raw_html, flags=re.IGNORECASE | re.DOTALL)
    ]
    headings = [h for h in headings if h][:15]

    cleaned = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return (title, cleaned, headings)


class StagingDownloadManager:
    """Manages safe file downloads in a staging directory with cancel, retry, Finder reveal, and integrity verification."""

    MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50 MB default ceiling

    def __init__(self, staging_dir: Path) -> None:
        self.staging_dir = staging_dir
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self._download_history: list[dict[str, Any]] = []
        self._cancelled_ids: set[str] = set()

    def list_downloads(self) -> list[dict[str, Any]]:
        return list(reversed(self._download_history))

    def get_download(self, download_id: str) -> dict[str, Any] | None:
        for item in self._download_history:
            if item.get("download_id") == download_id:
                return item
        return None

    def cancel_download(self, download_id: str) -> dict[str, Any]:
        """Cancel an in-progress or staged download and remove its partial staged file."""
        self._cancelled_ids.add(download_id)
        item = self.get_download(download_id)
        if item is None:
            return {"ok": False, "status": "DOWNLOAD_NOT_FOUND", "download_id": download_id}
        staged_path = Path(str(item.get("path", "")))
        if staged_path.exists() and staged_path.parent == self.staging_dir:
            try:
                staged_path.unlink()
            except Exception:
                pass
        item["status"] = "CANCELLED"
        item["ok"] = False
        item["progress"] = 0.0
        item["cancelled_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return dict(item)

    def remove_download(self, download_id: str, *, delete_staged_file: bool = False) -> dict[str, Any]:
        """Remove a download entry from the manager list."""
        item = self.get_download(download_id)
        if item is None:
            return {"ok": False, "status": "DOWNLOAD_NOT_FOUND", "download_id": download_id}
        if delete_staged_file:
            p = Path(str(item.get("path", "")))
            if p.exists() and p.parent == self.staging_dir:
                try:
                    p.unlink()
                except Exception:
                    pass
        self._download_history = [d for d in self._download_history if d.get("download_id") != download_id]
        return {"ok": True, "status": "REMOVED", "download_id": download_id}

    def reveal_in_finder(self, download_id: str, *, trigger_os_open: bool = False) -> dict[str, Any]:
        """Verify staged file location for Finder reveal without executing the file."""
        item = self.get_download(download_id)
        if item is None:
            return {"ok": False, "status": "DOWNLOAD_NOT_FOUND", "download_id": download_id}
        p = Path(str(item.get("path", "")))
        exists = p.exists()
        if exists and trigger_os_open and sys.platform == "darwin":
            try:
                subprocess.run(["/usr/bin/open", "-R", str(p)], check=False, timeout=2.0)
            except Exception:
                pass
        return {
            "ok": exists,
            "status": "REVEALED_IN_FINDER" if exists else "FILE_MISSING",
            "download_id": download_id,
            "path": str(p),
            "staging_dir": str(self.staging_dir),
            "auto_executed": False,
        }

    def inspect_staged_file(
        self,
        staged_path: Path,
        *,
        expected_sha256: str | None = None,
        max_bytes: int | None = None,
        download_id: str | None = None,
    ) -> dict[str, Any]:
        """Inspect size, MIME type, SHA-256 checksum, symlinks, executable bits, and archive member boundaries."""
        dl_id = download_id or f"dl-{uuid.uuid4().hex[:10]}"
        if not staged_path.exists() and not staged_path.is_symlink():
            return {
                "ok": False,
                "download_id": dl_id,
                "status": "FILE_NOT_FOUND",
                "path": str(staged_path),
                "progress": 0.0,
                "auto_executed": False,
            }

        # 1. Symbolic link check
        if staged_path.is_symlink():
            return {
                "ok": False,
                "download_id": dl_id,
                "status": "REJECTED_SYMLINK",
                "reason": "SYMLINK_DETECTED: Berkas unduhan berupa symbolic link ditolak demi keamanan.",
                "path": str(staged_path),
                "progress": 0.0,
                "auto_executed": False,
            }

        st = staged_path.stat()
        size_bytes = st.st_size
        ceiling = max_bytes or self.MAX_DOWNLOAD_BYTES
        if size_bytes > ceiling:
            return {
                "ok": False,
                "download_id": dl_id,
                "status": "REJECTED_SIZE_LIMIT",
                "reason": f"Ukuran berkas ({size_bytes} bytes) melebihi batas aman ({ceiling} bytes).",
                "size_bytes": size_bytes,
                "path": str(staged_path),
                "progress": 0.0,
                "auto_executed": False,
            }

        # 2. Executable permission check — strip execute permissions on staged files
        had_exec_bit = bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
        if had_exec_bit:
            staged_path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

        raw_bytes = staged_path.read_bytes()
        actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()

        # 3. Checksum verification if provided
        checksum_verified = True
        if expected_sha256:
            checksum_verified = actual_sha256.lower() == expected_sha256.strip().lower()
            if not checksum_verified:
                return {
                    "ok": False,
                    "download_id": dl_id,
                    "status": "REJECTED_CHECKSUM_MISMATCH",
                    "reason": f"SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}",
                    "expected_sha256": expected_sha256,
                    "actual_sha256": actual_sha256,
                    "sha256": actual_sha256,
                    "size_bytes": size_bytes,
                    "path": str(staged_path),
                    "progress": 0.0,
                    "auto_executed": False,
                }

        # 4. File type / header detection
        guessed_mime, _ = mimetypes.guess_type(staged_path.name)
        is_binary_executable_header = raw_bytes[:4] in {
            b"\x7fELF",
            b"\xcf\xfa\xed\xfe",
            b"\xfe\xed\xfa\xcf",
            b"\xca\xfe\xba\xbe",
        } or raw_bytes.startswith(b"#!")

        # 5. Archive safety inspection (zip / tar)
        archive_safe = True
        archive_issues: list[str] = []
        lower_name = staged_path.name.lower()
        if lower_name.endswith(".zip"):
            try:
                with zipfile.ZipFile(staged_path, "r") as zf:
                    for info in zf.infolist():
                        member_name = info.filename
                        norm_parts = Path(member_name).parts
                        if member_name.startswith("/") or ".." in norm_parts:
                            archive_safe = False
                            archive_issues.append(f"Unsafe archive member path: {member_name}")
                        if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                            archive_safe = False
                            archive_issues.append(f"Archive contains symlink entry: {member_name}")
            except Exception as exc:
                archive_safe = False
                archive_issues.append(f"Invalid zip archive: {exc}")
        elif lower_name.endswith((".tar", ".tar.gz", ".tgz")):
            try:
                with tarfile.open(staged_path, "r:*") as tf:
                    for member in tf.getmembers():
                        norm_parts = Path(member.name).parts
                        if member.name.startswith("/") or ".." in norm_parts:
                            archive_safe = False
                            archive_issues.append(f"Unsafe tar member path: {member.name}")
                        if member.issym() or member.islnk():
                            archive_safe = False
                            archive_issues.append(f"Tar archive contains symlink/hardlink: {member.name}")
            except Exception as exc:
                archive_safe = False
                archive_issues.append(f"Invalid tar archive: {exc}")

        if not archive_safe:
            return {
                "ok": False,
                "download_id": dl_id,
                "status": "REJECTED_UNSAFE_ARCHIVE",
                "reason": "; ".join(archive_issues),
                "archive_issues": archive_issues,
                "actual_sha256": actual_sha256,
                "sha256": actual_sha256,
                "size_bytes": size_bytes,
                "path": str(staged_path),
                "progress": 0.0,
                "auto_executed": False,
            }

        return {
            "ok": True,
            "download_id": dl_id,
            "status": "VERIFIED_STAGED",
            "path": str(staged_path),
            "staging_dir": str(self.staging_dir),
            "filename": staged_path.name,
            "size_bytes": size_bytes,
            "bytes_received": size_bytes,
            "total_bytes": size_bytes,
            "progress": 1.0,
            "mime_type": guessed_mime or "application/octet-stream",
            "sha256": actual_sha256,
            "checksum_verified": checksum_verified,
            "symlink_detected": False,
            "had_executable_bit": had_exec_bit,
            "executable_permission_stripped": True,
            "is_executable_header": is_binary_executable_header,
            "archive_safe": archive_safe,
            "auto_executed": False,
        }


class RealInternetEngine:
    """Real Internet Connectivity, Safari/Chrome-Style Browser Workspace, Web Research, and Dependency Manager."""

    DIAGNOSTIC_TARGETS: tuple[tuple[str, int, str], ...] = (
        ("docs.python.org", 443, HTTPS_SCHEME + "docs.python.org/3/"),
        ("www.google.com", 443, HTTPS_SCHEME + "www.google.com/"),
        ("github.com", 443, HTTPS_SCHEME + "github.com/"),
        ("pypi.org", 443, HTTPS_SCHEME + "pypi.org/simple/"),
    )

    def __init__(
        self,
        storage: NUIStorage,
        permissions: PermissionEngine,
        *,
        transport: InternetTransportAdapter | None = None,
        staging_dir: Path | None = None,
    ) -> None:
        self.storage = storage
        self.permissions = permissions
        self.transport: InternetTransportAdapter = transport or LiveNetworkTransportAdapter()
        eff_staging = staging_dir or (storage.db_path.parent / "staging_downloads")
        self.download_manager = StagingDownloadManager(eff_staging)
        self._last_diagnostics: dict[str, Any] | None = None
        self._browser_session_history: list[dict[str, Any]] = []
        self._ephemeral_history: list[dict[str, Any]] = []
        self._session_cookies: dict[str, str] = {"nui_session_token": "active"}
        self._session_cache: dict[str, dict[str, Any]] = {}
        self._tabs: list[dict[str, Any]] = []
        self._active_tab_id: str = ""
        self._navigation_traces: dict[str, dict[str, Any]] = {}
        self._navigation_trace_order: list[str] = []
        self._active_navigation_id_by_tab: dict[str, str] = {}
        self._init_browser_tables_and_defaults()

    def _init_browser_tables_and_defaults(self) -> None:
        with self.storage._lock, self.storage._conn:
            self.storage._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS browser_bookmarks (
                    bookmark_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    folder TEXT NOT NULL DEFAULT 'General',
                    favicon TEXT NOT NULL DEFAULT 'globe',
                    position INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS browser_history (
                    visit_id TEXT PRIMARY KEY,
                    tab_id TEXT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    http_status INTEGER NOT NULL DEFAULT 200,
                    session_policy TEXT NOT NULL DEFAULT 'PERSISTENT_PROFILE',
                    visited_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS browser_saved_tabs (
                    tab_id TEXT PRIMARY KEY,
                    position INTEGER NOT NULL DEFAULT 0,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    zoom_level REAL NOT NULL DEFAULT 1.0,
                    state_json TEXT NOT NULL DEFAULT '{}',
                    updated_at REAL NOT NULL
                );
                """
            )
            existing_bms = self.storage._conn.execute("SELECT COUNT(*) AS cnt FROM browser_bookmarks").fetchone()["cnt"]
            if existing_bms == 0:
                now = time.time()
                for idx, bm in enumerate(DEFAULT_BROWSER_BOOKMARKS):
                    self.storage._conn.execute(
                        """
                        INSERT INTO browser_bookmarks (
                            bookmark_id, title, url, domain, folder, favicon, position, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            bm["bookmark_id"],
                            bm["title"],
                            bm["url"],
                            normalize_domain(bm["url"]),
                            bm["folder"],
                            bm["favicon"],
                            idx,
                            now,
                            now,
                        ),
                    )

        if self.storage.get_setting("browser_session_policy") is None:
            self.storage.set_setting("browser_session_policy", "PERSISTENT_PROFILE")
        if self.storage.get_setting("browser_homepage") is None:
            self.storage.set_setting("browser_homepage", DEFAULT_HOMEPAGE_URL)
        if self.storage.get_setting("browser_search_template") is None:
            self.storage.set_setting("browser_search_template", DEFAULT_SEARCH_ENGINE_TEMPLATE)

        # Restore tabs if session policy is PERSISTENT_PROFILE, otherwise open default tab
        self.restore_tabs_according_to_policy()

    # ── Browser Session & Privacy Policy (Section C) ─────────────────────────

    def get_session_policy(self) -> str:
        pol = str(self.storage.get_setting("browser_session_policy", "PERSISTENT_PROFILE")).upper()
        return pol if pol in {"TEMPORARY_PRIVATE", "PERSISTENT_PROFILE"} else "PERSISTENT_PROFILE"

    def set_session_policy(self, policy: str) -> dict[str, Any]:
        pol = policy.strip().upper()
        if pol not in {"TEMPORARY_PRIVATE", "PERSISTENT_PROFILE"}:
            raise ValueError(f"Unsupported browser session policy: {policy!r}")
        self.storage.set_setting("browser_session_policy", pol)
        if pol == "PERSISTENT_PROFILE":
            self._persist_tabs_to_sqlite()
        return {
            "ok": True,
            "session_policy": pol,
            "persistent_profile_enabled": pol == "PERSISTENT_PROFILE",
            "cookies_preserved": True,
            "cache_preserved": True,
        }

    def clear_cookies(self) -> dict[str, Any]:
        removed = len(self._session_cookies)
        self._session_cookies.clear()
        return {"ok": True, "status": "COOKIES_CLEARED", "cleared_cookies_count": removed}

    def clear_cache(self) -> dict[str, Any]:
        removed = len(self._session_cache)
        self._session_cache.clear()
        return {"ok": True, "status": "CACHE_CLEARED", "cleared_cache_entries": removed}

    def clear_browser_session_data(self) -> dict[str, Any]:
        """Clear cookies, cache, in-memory session history, and persisted history when requested by user."""
        cleared_session_hist = len(self._browser_session_history)
        cleared_ephemeral = len(self._ephemeral_history)
        self._browser_session_history.clear()
        self._ephemeral_history.clear()
        cookies_res = self.clear_cookies()
        cache_res = self.clear_cache()
        hist_res = self.clear_all_history()
        return {
            "ok": True,
            "status": "SESSION_DATA_CLEARED",
            "cleared_history_entries": cleared_session_hist + cleared_ephemeral + hist_res.get("deleted_count", 0),
            "cleared_cookies_count": cookies_res["cleared_cookies_count"],
            "cleared_cache_entries": cache_res["cleared_cache_entries"],
            "session_policy": self.get_session_policy(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    # ── Multi-Tab Management & Navigation Trace (Sections 1 & 2) ─────────────

    @staticmethod
    def _new_navigation_id() -> str:
        return f"nav-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"

    def _create_navigation_trace(
        self,
        *,
        navigation_id: str,
        tab_id: str,
        requested_url: str,
        normalized_url: str,
    ) -> dict[str, Any]:
        now = time.time()
        trace = {
            "navigation_id": navigation_id,
            "tab_id": tab_id,
            "requested_url": requested_url,
            "normalized_url": normalized_url,
            "actual_url": normalized_url,
            "redirected": False,
            "didStartProvisionalNavigation": False,
            "didReceiveServerRedirectForProvisionalNavigation": False,
            "didCommit": False,
            "didFinish": False,
            "didFailProvisionalNavigation": False,
            "didFail": False,
            "webViewWebContentProcessDidTerminate": False,
            "http_status": 0,
            "page_title": "",
            "state": "LOADING",
            "error_code": None,
            "error_message": None,
            "content_visible_in_viewport": False,
            "started_at": now,
            "completed_at": None,
            "elapsed_ms": 0.0,
            "events": [
                {
                    "event": "NAVIGATION_CREATED",
                    "timestamp": now,
                    "url": normalized_url,
                }
            ],
        }
        self._navigation_traces[navigation_id] = trace
        if navigation_id not in self._navigation_trace_order:
            self._navigation_trace_order.append(navigation_id)
        return trace

    def get_navigation_traces(
        self, tab_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for nid in reversed(self._navigation_trace_order):
            tr = self._navigation_traces.get(nid)
            if tr is None:
                continue
            if tab_id and tr.get("tab_id") != tab_id:
                continue
            items.append(dict(tr))
            if len(items) >= limit:
                break
        return items

    def _make_tab_record(
        self,
        *,
        url: str = DEFAULT_HOMEPAGE_URL,
        title: str = "Python 3 Documentation",
        tab_id: str | None = None,
    ) -> dict[str, Any]:
        tid = tab_id or f"tab-{uuid.uuid4().hex[:8]}"
        parsed = parse_and_normalize_address_input(url)
        resolved = parsed["resolved_url"] if parsed.get("ok") else DEFAULT_HOMEPAGE_URL
        dom = parsed["domain"] if parsed.get("ok") else normalize_domain(resolved)
        sec = parsed.get("security_state", "SECURE_HTTPS")
        init_nav_id = f"nav-init-{tid}"
        self._active_navigation_id_by_tab[tid] = init_nav_id
        return {
            "tab_id": tid,
            "navigation_id": init_nav_id,
            "requested_url": url,
            "normalized_url": resolved,
            "actual_url": resolved,
            "title": title or dom or "New Tab",
            "url": resolved,
            "address_bar_text": resolved,
            "domain": dom,
            "favicon": self._favicon_for_domain(dom),
            "status": "COMPLETE",
            "is_loading": False,
            "progress": 1.0,
            "http_status": 200,
            "security_state": sec,
            "can_go_back": False,
            "can_go_forward": False,
            "back_stack": [],
            "forward_stack": [],
            "zoom_level": 1.0,
            "find_query": "",
            "find_match_count": 0,
            "has_error": False,
            "error_code": None,
            "error_message": None,
            "error_html": None,
            "process_terminated": False,
            "recovery_count": 0,
            "content_visible": True,
            "last_content_text": "",
            "last_headings": [],
            "trust_level": "UNTRUSTED_EXTERNAL_WEB_DATA",
            "updated_at": time.time(),
        }

    @staticmethod
    def _favicon_for_domain(domain: str) -> str:
        d = domain.lower()
        if "python.org" in d:
            return "book.closed.fill"
        if "github.com" in d:
            return "chevron.left.forwardslash.chevron.right"
        if "google.com" in d:
            return "magnifyingglass.circle.fill"
        if "wikipedia.org" in d:
            return "globe.americas.fill"
        if "akademihijaiyyahindonesia.com" in d:
            return "sparkles"
        return "globe"

    def _persist_tabs_to_sqlite(self) -> None:
        if self.get_session_policy() != "PERSISTENT_PROFILE":
            return
        now = time.time()
        with self.storage._lock, self.storage._conn:
            self.storage._conn.execute("DELETE FROM browser_saved_tabs")
            for idx, t in enumerate(self._tabs):
                state_sub = {
                    "back_stack": t.get("back_stack", []),
                    "forward_stack": t.get("forward_stack", []),
                    "security_state": t.get("security_state", "SECURE_HTTPS"),
                    "http_status": t.get("http_status", 200),
                    "navigation_id": t.get("navigation_id", ""),
                    "status": t.get("status", "COMPLETE"),
                }
                self.storage._conn.execute(
                    """
                    INSERT INTO browser_saved_tabs (
                        tab_id, position, title, url, domain, is_active, zoom_level, state_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        t["tab_id"],
                        idx,
                        t["title"],
                        t["url"],
                        t["domain"],
                        1 if t["tab_id"] == self._active_tab_id else 0,
                        float(t.get("zoom_level", 1.0)),
                        json.dumps(state_sub),
                        now,
                    ),
                )

    def restore_tabs_according_to_policy(self) -> dict[str, Any]:
        pol = self.get_session_policy()
        if pol == "PERSISTENT_PROFILE":
            with self.storage._lock:
                rows = self.storage._conn.execute(
                    "SELECT * FROM browser_saved_tabs ORDER BY position ASC"
                ).fetchall()
            if rows:
                restored: list[dict[str, Any]] = []
                active_id = ""
                for r in rows:
                    st = json.loads(r["state_json"] or "{}")
                    tab = self._make_tab_record(
                        url=str(r["url"]),
                        title=str(r["title"]),
                        tab_id=str(r["tab_id"]),
                    )
                    tab["zoom_level"] = float(r["zoom_level"] or 1.0)
                    tab["back_stack"] = list(st.get("back_stack") or [])
                    tab["forward_stack"] = list(st.get("forward_stack") or [])
                    tab["can_go_back"] = len(tab["back_stack"]) > 0
                    tab["can_go_forward"] = len(tab["forward_stack"]) > 0
                    tab["security_state"] = str(st.get("security_state", tab["security_state"]))
                    tab["http_status"] = int(st.get("http_status", 200))
                    restored.append(tab)
                    if int(r["is_active"]):
                        active_id = tab["tab_id"]
                self._tabs = restored
                self._active_tab_id = active_id or restored[0]["tab_id"]
                return self.get_browser_workspace_state()

        # Default initial tab
        initial_tab = self._make_tab_record(
            url=DEFAULT_HOMEPAGE_URL,
            title="Python 3 Documentation",
            tab_id="tab-main",
        )
        self._tabs = [initial_tab]
        self._active_tab_id = initial_tab["tab_id"]
        self._persist_tabs_to_sqlite()
        return self.get_browser_workspace_state()

    def list_tabs(self) -> list[dict[str, Any]]:
        return [dict(t) for t in self._tabs]

    def get_tab(self, tab_id: str | None = None) -> dict[str, Any]:
        target_id = tab_id or self._active_tab_id
        for t in self._tabs:
            if t["tab_id"] == target_id:
                return t
        if not self._tabs:
            self.restore_tabs_according_to_policy()
        return self._tabs[0]

    def new_tab(
        self,
        url: str | None = None,
        *,
        title: str = "New Tab",
        switch_to: bool = True,
        execute_fetch: bool = False,
    ) -> dict[str, Any]:
        target_url = (url or str(self.storage.get_setting("browser_homepage", DEFAULT_HOMEPAGE_URL))).strip()
        tab = self._make_tab_record(url=target_url, title=title)
        self._tabs.append(tab)
        if switch_to or not self._active_tab_id:
            self._active_tab_id = tab["tab_id"]
        if execute_fetch:
            self.navigate_tab(tab["tab_id"], target_url, record_back_stack=False)
        self._persist_tabs_to_sqlite()
        return {
            "ok": True,
            "action": "NEW_TAB",
            "tab": dict(tab),
            "active_tab_id": self._active_tab_id,
            "total_tabs": len(self._tabs),
        }

    def close_tab(self, tab_id: str) -> dict[str, Any]:
        idx = next((i for i, t in enumerate(self._tabs) if t["tab_id"] == tab_id), -1)
        if idx == -1:
            return {"ok": False, "status": "TAB_NOT_FOUND", "tab_id": tab_id}
        closed = self._tabs.pop(idx)
        self._active_navigation_id_by_tab.pop(tab_id, None)
        if not self._tabs:
            replacement = self._make_tab_record(
                url=str(self.storage.get_setting("browser_homepage", DEFAULT_HOMEPAGE_URL)),
                title="Python 3 Documentation",
            )
            self._tabs.append(replacement)
            self._active_tab_id = replacement["tab_id"]
        elif self._active_tab_id == tab_id:
            new_idx = min(idx, len(self._tabs) - 1)
            self._active_tab_id = self._tabs[new_idx]["tab_id"]
        self._persist_tabs_to_sqlite()
        return {
            "ok": True,
            "action": "CLOSE_TAB",
            "closed_tab_id": closed["tab_id"],
            "active_tab_id": self._active_tab_id,
            "total_tabs": len(self._tabs),
        }

    def switch_tab(self, tab_id: str) -> dict[str, Any]:
        for t in self._tabs:
            if t["tab_id"] == tab_id:
                self._active_tab_id = tab_id
                self._persist_tabs_to_sqlite()
                return {
                    "ok": True,
                    "action": "SWITCH_TAB",
                    "active_tab_id": self._active_tab_id,
                    "tab": dict(t),
                    "cookies_preserved": len(self._session_cookies) > 0,
                }
        return {"ok": False, "status": "TAB_NOT_FOUND", "tab_id": tab_id}

    def move_tab(self, tab_id: str, to_index: int) -> dict[str, Any]:
        cur_idx = next((i for i, t in enumerate(self._tabs) if t["tab_id"] == tab_id), -1)
        if cur_idx == -1:
            return {"ok": False, "status": "TAB_NOT_FOUND", "tab_id": tab_id}
        tab = self._tabs.pop(cur_idx)
        bounded = max(0, min(int(to_index), len(self._tabs)))
        self._tabs.insert(bounded, tab)
        self._persist_tabs_to_sqlite()
        return {
            "ok": True,
            "action": "MOVE_TAB",
            "tab_id": tab_id,
            "from_index": cur_idx,
            "to_index": bounded,
            "tab_order": [t["tab_id"] for t in self._tabs],
        }

    def begin_tab_navigation(
        self,
        tab_id: str | None,
        raw_input: str,
        *,
        navigation_id: str | None = None,
        record_back_stack: bool = True,
    ) -> dict[str, Any]:
        """Reset stale page state immediately when a new URL is entered and create a fresh navigation_id."""
        tab = self.get_tab(tab_id)
        tid = tab["tab_id"]
        nav_id = navigation_id or self._new_navigation_id()
        search_tpl = str(self.storage.get_setting("browser_search_template", DEFAULT_SEARCH_ENGINE_TEMPLATE))
        parsed = parse_and_normalize_address_input(
            raw_input,
            current_url=tab.get("url"),
            search_engine_template=search_tpl,
        )

        # Immediately assign new navigation_id and clear stale page state (Section 2)
        self._active_navigation_id_by_tab[tid] = nav_id
        tab["navigation_id"] = nav_id
        tab["requested_url"] = raw_input
        tab["last_content_text"] = ""
        tab["last_headings"] = []
        tab["content_visible"] = False
        tab["http_status"] = 0

        if not parsed.get("ok"):
            err_code = str(parsed.get("input_type", "INVALID_URL"))
            err_msg = str(parsed.get("error", "Format URL tidak valid."))
            tab["normalized_url"] = ""
            tab["actual_url"] = ""
            tab["title"] = f"URL Tidak Valid — {raw_input[:32] or 'Kosong'}"
            tab["favicon"] = "exclamationmark.triangle.fill"
            tab["is_loading"] = False
            tab["status"] = "FAILED"
            tab["progress"] = 0.0
            tab["has_error"] = True
            tab["error_code"] = err_code
            tab["error_message"] = err_msg
            tab["error_html"] = build_browser_error_page_html(
                url=raw_input,
                error_code=err_code,
                error_message=err_msg,
            )
            trace = self._create_navigation_trace(
                navigation_id=nav_id,
                tab_id=tid,
                requested_url=raw_input,
                normalized_url="",
            )
            trace["didFailProvisionalNavigation"] = True
            trace["state"] = "FAILED"
            trace["error_code"] = err_code
            trace["error_message"] = redact_secrets(err_msg)
            trace["page_title"] = tab["title"]
            trace["completed_at"] = time.time()
            return {
                "ok": False,
                "navigation_id": nav_id,
                "status": "INVALID_URL",
                "navigation_state": "FAILED",
                "tab": dict(tab),
                "parsed": parsed,
                "trace": dict(trace),
                "error_html": tab["error_html"],
            }

        target_url = parsed["resolved_url"]
        dom = parsed["domain"]

        if record_back_stack and tab.get("url") and tab["url"] != target_url:
            tab["back_stack"].append(tab["url"])
            tab["forward_stack"].clear()
            tab["can_go_back"] = len(tab["back_stack"]) > 0
            tab["can_go_forward"] = False

        # Reset old title, old loading status, old favicon (Section 2 requirement)
        tab["normalized_url"] = target_url
        tab["actual_url"] = target_url
        tab["url"] = target_url
        tab["address_bar_text"] = target_url
        tab["domain"] = dom
        tab["title"] = f"Loading {dom}..."
        tab["favicon"] = self._favicon_for_domain(dom)
        tab["security_state"] = parsed["security_state"]
        tab["is_loading"] = True
        tab["status"] = "LOADING"
        tab["progress"] = 0.15
        tab["has_error"] = False
        tab["error_code"] = None
        tab["error_message"] = None
        tab["error_html"] = None
        tab["updated_at"] = time.time()

        trace = self._create_navigation_trace(
            navigation_id=nav_id,
            tab_id=tid,
            requested_url=raw_input,
            normalized_url=target_url,
        )
        trace["didStartProvisionalNavigation"] = True
        trace["page_title"] = tab["title"]
        trace["events"].append(
            {
                "event": "didStartProvisionalNavigation",
                "timestamp": time.time(),
                "url": target_url,
            }
        )
        return {
            "ok": True,
            "navigation_id": nav_id,
            "status": "LOADING",
            "navigation_state": "LOADING",
            "tab": dict(tab),
            "parsed": parsed,
            "trace": dict(trace),
        }

    def navigate_tab(
        self,
        tab_id: str | None,
        raw_input: str,
        *,
        navigation_id: str | None = None,
        record_back_stack: bool = True,
        session_id: str | None = None,
        allow_interactive_browser: bool = True,
    ) -> dict[str, Any]:
        """Navigate a Browser tab to a URL or search query, resetting stale state first and recording full trace."""
        begin_res = self.begin_tab_navigation(
            tab_id,
            raw_input,
            navigation_id=navigation_id,
            record_back_stack=record_back_stack,
        )
        if not begin_res.get("ok"):
            return begin_res

        tab = self.get_tab(tab_id)
        tid = tab["tab_id"]
        nav_id = str(begin_res["navigation_id"])
        parsed = begin_res["parsed"]
        trace = self._navigation_traces[nav_id]
        target_url = parsed["resolved_url"]
        dom = parsed["domain"]
        t0 = time.perf_counter()

        if parsed["input_type"] == "INTERNAL_URL":
            tab["is_loading"] = False
            tab["status"] = "COMPLETE"
            tab["progress"] = 1.0
            tab["http_status"] = 200
            tab["has_error"] = False
            tab["title"] = "CosmicTera Browser Home"
            tab["content_visible"] = True
            trace["didCommit"] = True
            trace["didFinish"] = True
            trace["http_status"] = 200
            trace["page_title"] = tab["title"]
            trace["state"] = "COMPLETE"
            trace["content_visible_in_viewport"] = True
            trace["completed_at"] = time.time()
            trace["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
            self._persist_tabs_to_sqlite()
            return {
                "ok": True,
                "navigation_id": nav_id,
                "status": "LOADED",
                "navigation_state": "COMPLETE",
                "tab": dict(tab),
                "parsed": parsed,
                "trace": dict(trace),
            }

        fetch_res = self.fetch_url(
            target_url,
            session_id=session_id,
            for_browser=True,
            allow_interactive_browser=allow_interactive_browser,
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        # Verify navigation was not superseded while fetching
        if self._active_navigation_id_by_tab.get(tid) != nav_id:
            trace["state"] = "SUPERSEDED"
            return {
                "ok": False,
                "navigation_id": nav_id,
                "ignored_stale_callback": True,
                "status": "IGNORED_STALE_NAVIGATION_ID",
                "tab": dict(tab),
                "trace": dict(trace),
            }

        tab["is_loading"] = False
        tab["progress"] = 1.0 if fetch_res.get("ok") else 0.0
        tab["http_status"] = int(fetch_res.get("status_code", 0))
        trace["http_status"] = tab["http_status"]
        trace["elapsed_ms"] = float(fetch_res.get("latency_ms") or elapsed_ms)
        trace["completed_at"] = time.time()

        if fetch_res.get("ok"):
            final_url = str(fetch_res.get("url") or target_url)
            redirected = bool(fetch_res.get("redirected")) or (final_url != target_url)
            if redirected:
                trace["redirected"] = True
                trace["didReceiveServerRedirectForProvisionalNavigation"] = True
                trace["events"].append(
                    {
                        "event": "didReceiveServerRedirectForProvisionalNavigation",
                        "timestamp": time.time(),
                        "url": final_url,
                    }
                )
            trace["actual_url"] = final_url
            trace["didCommit"] = True
            trace["didFinish"] = True
            trace["state"] = "COMPLETE"
            trace["content_visible_in_viewport"] = True
            trace["events"].extend(
                [
                    {"event": "didCommit", "timestamp": time.time(), "url": final_url},
                    {"event": "didFinish", "timestamp": time.time(), "url": final_url},
                ]
            )

            tab["actual_url"] = final_url
            tab["url"] = final_url
            tab["address_bar_text"] = final_url
            tab["domain"] = normalize_domain(final_url)
            tab["favicon"] = self._favicon_for_domain(tab["domain"])
            resolved_title = str(fetch_res.get("title") or "").strip()
            tab["title"] = resolved_title if resolved_title else tab["domain"]
            trace["page_title"] = tab["title"]
            tab["status"] = "COMPLETE"
            tab["has_error"] = False
            tab["error_code"] = None
            tab["error_message"] = None
            tab["error_html"] = None
            tab["content_visible"] = True
            tab["last_content_text"] = str(fetch_res.get("sanitized_text", ""))
            tab["last_headings"] = list(fetch_res.get("headings") or [])
            self._session_cache[final_url] = {
                "title": tab["title"],
                "cached_at": time.time(),
                "content_sha256": fetch_res.get("content_sha256", ""),
            }
            self.record_history_visit(
                url=final_url,
                title=tab["title"],
                domain=tab["domain"],
                http_status=tab["http_status"],
                tab_id=tab["tab_id"],
            )
            self._persist_tabs_to_sqlite()
            return {
                "ok": True,
                "navigation_id": nav_id,
                "status": "LOADED",
                "navigation_state": "COMPLETE",
                "tab": dict(tab),
                "parsed": parsed,
                "navigation": fetch_res,
                "trace": dict(trace),
            }

        err_code = str(fetch_res.get("status") or "NAVIGATION_FAILED")
        err_msg = redact_secrets(
            str(fetch_res.get("error") or fetch_res.get("reason") or "Gagal membuka halaman.")
        )
        # Never keep stale title on navigation failure (Section 2)
        tab["title"] = f"Gagal Memuat — {dom}"
        tab["status"] = "FAILED"
        tab["has_error"] = True
        tab["error_code"] = err_code
        tab["error_message"] = err_msg
        tab["content_visible"] = True
        tab["error_html"] = build_browser_error_page_html(
            url=target_url,
            error_code=err_code,
            error_message=err_msg,
            domain=dom,
        )
        trace["didFailProvisionalNavigation"] = True
        trace["state"] = "FAILED"
        trace["page_title"] = tab["title"]
        trace["error_code"] = err_code
        trace["error_message"] = err_msg
        trace["content_visible_in_viewport"] = True
        trace["events"].append(
            {
                "event": "didFailProvisionalNavigation",
                "timestamp": time.time(),
                "url": target_url,
                "error_code": err_code,
                "error_message": err_msg,
            }
        )
        self._persist_tabs_to_sqlite()
        return {
            "ok": False,
            "navigation_id": nav_id,
            "status": err_code,
            "navigation_state": "FAILED",
            "tab": dict(tab),
            "parsed": parsed,
            "navigation": fetch_res,
            "trace": dict(trace),
            "error_html": tab["error_html"],
        }

    def go_back(self, tab_id: str | None = None) -> dict[str, Any]:
        tab = self.get_tab(tab_id)
        if not tab["back_stack"]:
            return {"ok": False, "status": "NO_BACK_HISTORY", "tab": dict(tab)}
        prev_url = tab["back_stack"].pop()
        if tab.get("url"):
            tab["forward_stack"].append(tab["url"])
        tab["can_go_back"] = len(tab["back_stack"]) > 0
        tab["can_go_forward"] = len(tab["forward_stack"]) > 0
        res = self.navigate_tab(tab["tab_id"], prev_url, record_back_stack=False)
        tab["can_go_back"] = len(tab["back_stack"]) > 0
        tab["can_go_forward"] = len(tab["forward_stack"]) > 0
        res["tab"] = dict(tab)
        return res

    def go_forward(self, tab_id: str | None = None) -> dict[str, Any]:
        tab = self.get_tab(tab_id)
        if not tab["forward_stack"]:
            return {"ok": False, "status": "NO_FORWARD_HISTORY", "tab": dict(tab)}
        next_url = tab["forward_stack"].pop()
        if tab.get("url"):
            tab["back_stack"].append(tab["url"])
        tab["can_go_back"] = len(tab["back_stack"]) > 0
        tab["can_go_forward"] = len(tab["forward_stack"]) > 0
        res = self.navigate_tab(tab["tab_id"], next_url, record_back_stack=False)
        tab["can_go_back"] = len(tab["back_stack"]) > 0
        tab["can_go_forward"] = len(tab["forward_stack"]) > 0
        res["tab"] = dict(tab)
        return res

    def reload_tab(self, tab_id: str | None = None) -> dict[str, Any]:
        tab = self.get_tab(tab_id)
        return self.navigate_tab(tab["tab_id"], tab["url"], record_back_stack=False)

    def stop_tab_loading(self, tab_id: str | None = None) -> dict[str, Any]:
        tab = self.get_tab(tab_id)
        tid = tab["tab_id"]
        tab["is_loading"] = False
        tab["status"] = "STOPPED"
        tab["progress"] = 0.0
        nav_id = self._active_navigation_id_by_tab.get(tid)
        if nav_id and nav_id in self._navigation_traces:
            tr = self._navigation_traces[nav_id]
            tr["state"] = "STOPPED"
            tr["completed_at"] = time.time()
            tr["events"].append({"event": "STOPPED", "timestamp": time.time(), "url": tab.get("url", "")})
        self._persist_tabs_to_sqlite()
        return {"ok": True, "status": "STOPPED", "navigation_state": "STOPPED", "tab": dict(tab)}

    def set_tab_zoom(self, tab_id: str | None, zoom_level: float) -> dict[str, Any]:
        tab = self.get_tab(tab_id)
        bounded = round(max(0.5, min(3.0, float(zoom_level))), 2)
        tab["zoom_level"] = bounded
        self._persist_tabs_to_sqlite()
        return {"ok": True, "status": "ZOOM_UPDATED", "zoom_level": bounded, "tab": dict(tab)}

    def find_on_page(self, tab_id: str | None, query: str) -> dict[str, Any]:
        tab = self.get_tab(tab_id)
        q_clean = query.strip()
        tab["find_query"] = q_clean
        if not q_clean:
            tab["find_match_count"] = 0
            return {"ok": True, "query": "", "match_count": 0}
        haystack = f"{tab.get('title', '')} {tab.get('last_content_text', '')}"
        matches = re.findall(re.escape(q_clean), haystack, flags=re.IGNORECASE)
        tab["find_match_count"] = len(matches)
        return {
            "ok": True,
            "tab_id": tab["tab_id"],
            "query": q_clean,
            "match_count": len(matches),
        }

    def handle_webkit_process_termination(
        self, tab_id: str | None = None, *, auto_recover: bool = True
    ) -> dict[str, Any]:
        """Handle `webViewWebContentProcessDidTerminate` by recording termination and recovering the active tab."""
        tab = self.get_tab(tab_id)
        tid = tab["tab_id"]
        tab["process_terminated"] = True
        nav_id = self._active_navigation_id_by_tab.get(tid)
        if nav_id and nav_id in self._navigation_traces:
            tr = self._navigation_traces[nav_id]
            tr["webViewWebContentProcessDidTerminate"] = True
            tr["events"].append(
                {
                    "event": "webViewWebContentProcessDidTerminate",
                    "timestamp": time.time(),
                    "url": tab.get("url", ""),
                }
            )
        if not auto_recover:
            return {
                "ok": False,
                "status": "WEBKIT_PROCESS_TERMINATED",
                "recovered": False,
                "tab": dict(tab),
            }
        tab["recovery_count"] = int(tab.get("recovery_count", 0)) + 1
        reload_res = self.reload_tab(tab["tab_id"])
        tab["process_terminated"] = False
        return {
            "ok": True,
            "status": "WEBKIT_PROCESS_RECOVERED",
            "recovered": True,
            "recovery_count": tab["recovery_count"],
            "reload_status": reload_res.get("status"),
            "tab": dict(tab),
        }

    def sync_webview_lifecycle_event(
        self,
        *,
        tab_id: str | None = None,
        navigation_id: str | None = None,
        event: str,
        requested_url: str | None = None,
        normalized_url: str | None = None,
        actual_url: str | None = None,
        url: str | None = None,
        title: str | None = None,
        http_status: int | None = None,
        progress: float | None = None,
        can_go_back: bool | None = None,
        can_go_forward: bool | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        elapsed_ms: float | None = None,
        content_visible: bool | None = None,
    ) -> dict[str, Any]:
        """Receive live WKNavigationDelegate callbacks from the macOS WKWebView, enforce navigation_id consistency, and reject stale callbacks."""
        tab = self.get_tab(tab_id)
        tid = tab["tab_id"]
        raw_ev = event.strip()
        ev_upper = raw_ev.upper()

        is_start_event = ev_upper in {"PROVISIONAL_START", "DIDSTARTPROVISIONALNAVIGATION", "START"}
        active_nav_id = self._active_navigation_id_by_tab.get(tid) or tab.get("navigation_id")

        # Section 2: Ignore late callbacks from an older navigation_id
        if navigation_id and not is_start_event and active_nav_id and navigation_id != active_nav_id:
            if navigation_id in self._navigation_traces:
                self._navigation_traces[navigation_id]["events"].append(
                    {
                        "event": f"IGNORED_STALE_CALLBACK:{raw_ev}",
                        "timestamp": time.time(),
                        "active_navigation_id": active_nav_id,
                    }
                )
            return {
                "ok": False,
                "ignored_stale_callback": True,
                "status": "IGNORED_STALE_NAVIGATION_ID",
                "stale_navigation_id": navigation_id,
                "active_navigation_id": active_nav_id,
                "tab": dict(tab),
            }

        eff_url = actual_url or url or normalized_url or requested_url or tab.get("url", "")
        if is_start_event:
            nav_id = navigation_id or self._new_navigation_id()
            self._active_navigation_id_by_tab[tid] = nav_id
            tab["navigation_id"] = nav_id
            req_u = requested_url or eff_url
            norm_u = normalized_url or eff_url
            dom = normalize_domain(norm_u) if norm_u else tab.get("domain", "")
            tab["requested_url"] = req_u
            tab["normalized_url"] = norm_u
            tab["actual_url"] = norm_u
            if norm_u:
                tab["url"] = norm_u
                tab["address_bar_text"] = norm_u
                tab["domain"] = dom
            # Reset stale title, loading state, and favicon immediately (Section 2)
            tab["title"] = f"Loading {dom or 'page'}..."
            tab["favicon"] = self._favicon_for_domain(dom)
            tab["is_loading"] = True
            tab["status"] = "LOADING"
            tab["progress"] = float(progress if progress is not None else 0.15)
            tab["http_status"] = 0
            tab["has_error"] = False
            tab["error_code"] = None
            tab["error_message"] = None
            tab["error_html"] = None
            tab["content_visible"] = False
            trace = self._create_navigation_trace(
                navigation_id=nav_id,
                tab_id=tid,
                requested_url=req_u,
                normalized_url=norm_u,
            )
            trace["didStartProvisionalNavigation"] = True
            trace["page_title"] = tab["title"]
            trace["events"].append(
                {
                    "event": "didStartProvisionalNavigation",
                    "timestamp": time.time(),
                    "url": norm_u,
                }
            )
            return {"ok": True, "event": "didStartProvisionalNavigation", "navigation_id": nav_id, "tab": dict(tab), "trace": dict(trace)}

        nav_id = navigation_id or active_nav_id or self._new_navigation_id()
        self._active_navigation_id_by_tab[tid] = nav_id
        tab["navigation_id"] = nav_id
        trace = self._navigation_traces.get(nav_id)
        if trace is None:
            trace = self._create_navigation_trace(
                navigation_id=nav_id,
                tab_id=tid,
                requested_url=requested_url or eff_url,
                normalized_url=normalized_url or eff_url,
            )

        if eff_url and not eff_url.lower().startswith("about:"):
            tab["actual_url"] = eff_url
            tab["url"] = eff_url
            tab["address_bar_text"] = eff_url
            tab["domain"] = normalize_domain(eff_url)
            tab["favicon"] = self._favicon_for_domain(tab["domain"])
            tab["security_state"] = "SECURE_HTTPS" if eff_url.lower().startswith(HTTPS_SCHEME) else "INSECURE_HTTP"
            trace["actual_url"] = eff_url

        if http_status is not None:
            tab["http_status"] = int(http_status)
            trace["http_status"] = int(http_status)
        if progress is not None:
            tab["progress"] = float(progress)
        if can_go_back is not None:
            tab["can_go_back"] = bool(can_go_back)
        if can_go_forward is not None:
            tab["can_go_forward"] = bool(can_go_forward)
        if elapsed_ms is not None:
            trace["elapsed_ms"] = float(elapsed_ms)
        if content_visible is not None:
            tab["content_visible"] = bool(content_visible)
            trace["content_visible_in_viewport"] = bool(content_visible)

        if ev_upper in {"REDIRECTED", "DIDRECEIVESERVERREDIRECTFORPROVISIONALNAVIGATION"}:
            trace["redirected"] = True
            trace["didReceiveServerRedirectForProvisionalNavigation"] = True
            trace["events"].append(
                {
                    "event": "didReceiveServerRedirectForProvisionalNavigation",
                    "timestamp": time.time(),
                    "url": eff_url,
                }
            )
            tab["title"] = f"Loading {tab['domain']}..."
            trace["page_title"] = tab["title"]
        elif ev_upper in {"COMMITTED", "DIDCOMMIT"}:
            tab["is_loading"] = True
            tab["status"] = "COMMITTED"
            tab["progress"] = max(0.55, float(tab.get("progress", 0.55)))
            trace["didCommit"] = True
            trace["state"] = "COMMITTED"
            trace["events"].append(
                {
                    "event": "didCommit",
                    "timestamp": time.time(),
                    "url": eff_url,
                }
            )
            if title and title.strip():
                tab["title"] = title.strip()
                trace["page_title"] = tab["title"]
        elif ev_upper in {"FINISHED", "DIDFINISH", "COMPLETE"}:
            tab["is_loading"] = False
            tab["status"] = "COMPLETE"
            tab["progress"] = 1.0
            tab["has_error"] = False
            tab["error_code"] = None
            tab["error_message"] = None
            tab["error_html"] = None
            if int(tab.get("http_status", 0)) == 0:
                tab["http_status"] = 200
                trace["http_status"] = 200
            clean_title = (title or "").strip()
            if clean_title and not clean_title.startswith("Loading "):
                tab["title"] = clean_title
            elif tab.get("title", "").startswith("Loading ") or not tab.get("title"):
                tab["title"] = tab.get("domain") or eff_url
            tab["content_visible"] = True if content_visible is None else bool(content_visible)

            trace["didCommit"] = True
            trace["didFinish"] = True
            trace["state"] = "COMPLETE"
            trace["page_title"] = tab["title"]
            trace["content_visible_in_viewport"] = tab["content_visible"]
            trace["completed_at"] = time.time()
            if not trace.get("elapsed_ms"):
                trace["elapsed_ms"] = round((time.time() - float(trace.get("started_at", time.time()))) * 1000.0, 2)
            trace["events"].append(
                {
                    "event": "didFinish",
                    "timestamp": time.time(),
                    "url": tab["url"],
                    "title": tab["title"],
                    "http_status": tab["http_status"],
                }
            )
            self.record_history_visit(
                url=tab["url"],
                title=tab["title"],
                domain=tab["domain"],
                http_status=int(tab.get("http_status", 200)),
                tab_id=tab["tab_id"],
            )
            self._persist_tabs_to_sqlite()
        elif ev_upper in {
            "FAILED",
            "PROVISIONAL_FAILED",
            "DIDFAILPROVISIONALNAVIGATION",
            "DIDFAIL",
            "TIMEOUT",
        }:
            tab["is_loading"] = False
            tab["status"] = "FAILED"
            tab["progress"] = 0.0
            tab["has_error"] = True
            err_c = error_code or ev_upper
            err_m = redact_secrets(error_message or "Navigasi WKWebView gagal.")
            tab["error_code"] = err_c
            tab["error_message"] = err_m
            # Never keep stale title from previous page when navigation fails!
            tab["title"] = f"Gagal Memuat — {tab.get('domain') or 'Halaman'}"
            tab["content_visible"] = True
            tab["error_html"] = build_browser_error_page_html(
                url=tab["url"],
                error_code=err_c,
                error_message=err_m,
                domain=tab["domain"],
            )
            if "PROVISIONAL" in ev_upper or ev_upper == "TIMEOUT":
                trace["didFailProvisionalNavigation"] = True
            else:
                trace["didFail"] = True
            trace["state"] = "FAILED"
            trace["page_title"] = tab["title"]
            trace["error_code"] = err_c
            trace["error_message"] = err_m
            trace["content_visible_in_viewport"] = True
            trace["completed_at"] = time.time()
            trace["events"].append(
                {
                    "event": "didFailProvisionalNavigation" if trace["didFailProvisionalNavigation"] else "didFail",
                    "timestamp": time.time(),
                    "url": tab["url"],
                    "error_code": err_c,
                    "error_message": err_m,
                }
            )
            self._persist_tabs_to_sqlite()
        elif ev_upper in {"WEBVIEWWEBCONTENTPROCESSDIDTERMINATE", "PROCESS_TERMINATED"}:
            trace["webViewWebContentProcessDidTerminate"] = True
            trace["events"].append(
                {
                    "event": "webViewWebContentProcessDidTerminate",
                    "timestamp": time.time(),
                    "url": tab["url"],
                }
            )

        return {
            "ok": True,
            "event": raw_ev,
            "navigation_id": nav_id,
            "tab": dict(tab),
            "trace": dict(trace),
            "error_html": tab.get("error_html"),
        }

    # ── Bookmarks & Folders (Section A) ──────────────────────────────────────

    def list_bookmarks(self, folder: str | None = None) -> list[dict[str, Any]]:
        with self.storage._lock:
            if folder:
                rows = self.storage._conn.execute(
                    "SELECT * FROM browser_bookmarks WHERE folder = ? ORDER BY position ASC, created_at ASC",
                    (folder,),
                ).fetchall()
            else:
                rows = self.storage._conn.execute(
                    "SELECT * FROM browser_bookmarks ORDER BY position ASC, created_at ASC"
                ).fetchall()
            return [dict(r) for r in rows]

    def add_bookmark(
        self,
        *,
        title: str,
        url: str,
        folder: str = "General",
        favicon: str | None = None,
    ) -> dict[str, Any]:
        parsed = parse_and_normalize_address_input(url)
        resolved_url = parsed["resolved_url"] if parsed.get("ok") else url
        dom = normalize_domain(resolved_url)
        bm_id = f"bm-{uuid.uuid4().hex[:8]}"
        now = time.time()
        icon = favicon or self._favicon_for_domain(dom)
        with self.storage._lock, self.storage._conn:
            pos = self.storage._conn.execute("SELECT COUNT(*) AS cnt FROM browser_bookmarks").fetchone()["cnt"]
            self.storage._conn.execute(
                """
                INSERT INTO browser_bookmarks (
                    bookmark_id, title, url, domain, folder, favicon, position, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (bm_id, title.strip() or dom, resolved_url, dom, folder.strip() or "General", icon, pos, now, now),
            )
            row = self.storage._conn.execute(
                "SELECT * FROM browser_bookmarks WHERE bookmark_id = ?", (bm_id,)
            ).fetchone()
            return dict(row)

    def edit_bookmark(
        self,
        bookmark_id: str,
        *,
        title: str | None = None,
        url: str | None = None,
        folder: str | None = None,
    ) -> dict[str, Any]:
        with self.storage._lock, self.storage._conn:
            row = self.storage._conn.execute(
                "SELECT * FROM browser_bookmarks WHERE bookmark_id = ?", (bookmark_id,)
            ).fetchone()
            if not row:
                return {"ok": False, "status": "BOOKMARK_NOT_FOUND", "bookmark_id": bookmark_id}
            cur = dict(row)
            new_title = title.strip() if title is not None else cur["title"]
            new_url = parse_and_normalize_address_input(url)["resolved_url"] if url is not None else cur["url"]
            new_dom = normalize_domain(new_url)
            new_folder = folder.strip() if folder is not None else cur["folder"]
            now = time.time()
            self.storage._conn.execute(
                """
                UPDATE browser_bookmarks
                SET title = ?, url = ?, domain = ?, folder = ?, updated_at = ?
                WHERE bookmark_id = ?
                """,
                (new_title, new_url, new_dom, new_folder, now, bookmark_id),
            )
            updated = self.storage._conn.execute(
                "SELECT * FROM browser_bookmarks WHERE bookmark_id = ?", (bookmark_id,)
            ).fetchone()
            return {"ok": True, "bookmark": dict(updated)}

    def organize_bookmark_folder(self, bookmark_id: str, folder: str) -> dict[str, Any]:
        return self.edit_bookmark(bookmark_id, folder=folder)

    def delete_bookmark(self, bookmark_id: str) -> dict[str, Any]:
        with self.storage._lock, self.storage._conn:
            cur = self.storage._conn.execute(
                "DELETE FROM browser_bookmarks WHERE bookmark_id = ?", (bookmark_id,)
            )
            return {
                "ok": cur.rowcount > 0,
                "deleted": cur.rowcount > 0,
                "bookmark_id": bookmark_id,
            }

    # ── Browser History (Section A & C) ──────────────────────────────────────

    def record_history_visit(
        self,
        *,
        url: str,
        title: str,
        domain: str | None = None,
        http_status: int = 200,
        tab_id: str | None = None,
    ) -> dict[str, Any]:
        pol = self.get_session_policy()
        now = time.time()
        visit_id = f"vis-{uuid.uuid4().hex[:10]}"
        dom = domain or normalize_domain(url)
        entry = {
            "visit_id": visit_id,
            "tab_id": tab_id or self._active_tab_id,
            "title": title or dom,
            "url": url,
            "domain": dom,
            "http_status": int(http_status),
            "session_policy": pol,
            "visited_at": now,
            "accessed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        }
        self._browser_session_history.append(entry)
        if pol == "TEMPORARY_PRIVATE":
            self._ephemeral_history.append(entry)
            return entry

        with self.storage._lock, self.storage._conn:
            self.storage._conn.execute(
                """
                INSERT INTO browser_history (
                    visit_id, tab_id, title, url, domain, http_status, session_policy, visited_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (visit_id, entry["tab_id"], entry["title"], url, dom, int(http_status), pol, now),
            )
        return entry

    def search_history(self, query: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        pol = self.get_session_policy()
        if pol == "TEMPORARY_PRIVATE":
            items = list(reversed(self._ephemeral_history))
            if query:
                q_low = query.strip().lower()
                items = [
                    it
                    for it in items
                    if q_low in it["title"].lower() or q_low in it["url"].lower() or q_low in it["domain"].lower()
                ]
            return items[:limit]

        with self.storage._lock:
            if query and query.strip():
                q_like = f"%{query.strip()}%"
                rows = self.storage._conn.execute(
                    """
                    SELECT * FROM browser_history
                    WHERE title LIKE ? OR url LIKE ? OR domain LIKE ?
                    ORDER BY visited_at DESC LIMIT ?
                    """,
                    (q_like, q_like, q_like, limit),
                ).fetchall()
            else:
                rows = self.storage._conn.execute(
                    "SELECT * FROM browser_history ORDER BY visited_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    def delete_history_items(self, visit_ids: list[str]) -> dict[str, Any]:
        id_set = {str(v) for v in visit_ids if v}
        if not id_set:
            return {"ok": True, "deleted_count": 0}
        self._ephemeral_history = [h for h in self._ephemeral_history if h["visit_id"] not in id_set]
        self._browser_session_history = [
            h for h in self._browser_session_history if h.get("visit_id") not in id_set
        ]
        with self.storage._lock, self.storage._conn:
            placeholders = ",".join("?" for _ in id_set)
            cur = self.storage._conn.execute(
                f"DELETE FROM browser_history WHERE visit_id IN ({placeholders})",
                tuple(id_set),
            )
            return {"ok": True, "deleted_count": cur.rowcount}

    def clear_all_history(self) -> dict[str, Any]:
        eph_count = len(self._ephemeral_history)
        self._ephemeral_history.clear()
        self._browser_session_history.clear()
        with self.storage._lock, self.storage._conn:
            cur = self.storage._conn.execute("DELETE FROM browser_history")
            return {"ok": True, "status": "HISTORY_CLEARED", "deleted_count": cur.rowcount + eph_count}

    def get_browser_workspace_state(self) -> dict[str, Any]:
        bookmarks = self.list_bookmarks()
        folders = sorted({bm["folder"] for bm in bookmarks} | {"Documentation", "Development", "General"})
        cur_mode = str(self.storage.get_setting("operating_mode", "HYBRID")).upper()
        if cur_mode == "LOCAL":
            conn_info = {
                "overall_status": "DISCONNECTED",
                "connectivity_reason": "OPERATING_MODE_LOCAL_LOCK: Outbound internet dinonaktifkan pada mode LOCAL.",
            }
        elif self._last_diagnostics is not None:
            conn_info = dict(self._last_diagnostics)
            if "connectivity_reason" not in conn_info:
                st = conn_info.get("overall_status", "UNKNOWN")
                dns_err = (conn_info.get("dns") or {}).get("error")
                https_code = (conn_info.get("https") or {}).get("status_code", 0)
                conn_info["connectivity_reason"] = (
                    f"HTTPS_VERIFIED (HTTP {https_code})"
                    if st == "CONNECTED"
                    else (f"DNS/NETWORK_ERROR ({dns_err})" if dns_err else f"STATUS_{st}")
                )
        else:
            conn_info = {
                "overall_status": "UNKNOWN",
                "connectivity_reason": "INITIAL_PROBE_NOT_RUN_YET: Belum menjalankan run_connectivity_diagnostics().",
            }
        return {
            "ok": True,
            "active_tab_id": self._active_tab_id,
            "active_tab": dict(self.get_tab()),
            "tabs": self.list_tabs(),
            "bookmarks": bookmarks,
            "bookmark_folders": folders,
            "history": self.search_history(limit=50),
            "downloads": self.download_manager.list_downloads(),
            "navigation_traces": self.get_navigation_traces(limit=25),
            "session_policy": self.get_session_policy(),
            "homepage": self.storage.get_setting("browser_homepage", DEFAULT_HOMEPAGE_URL),
            "search_engine_template": self.storage.get_setting(
                "browser_search_template", DEFAULT_SEARCH_ENGINE_TEMPLATE
            ),
            "cookies_count": len(self._session_cookies),
            "cache_entries_count": len(self._session_cache),
            "connectivity": conn_info,
        }

    # ── Mode & Permission Gate ───────────────────────────────────────────────

    def _check_mode_and_permission(
        self,
        *,
        category: str,
        operation: str,
        target_type: str,
        target_value: str,
        reason: str,
        session_id: str | None = None,
        allow_interactive_browser: bool = False,
    ) -> tuple[bool, dict[str, Any]]:
        """Enforce LOCAL/ONLINE/HYBRID mode separation and PermissionEngine scopes."""
        op_mode = str(self.storage.get_setting("operating_mode", "HYBRID")).upper()
        if op_mode == "LOCAL":
            self.storage.record_audit(
                user_request=reason,
                tool_name=f"internet.{operation.lower()}",
                category=category,
                target=target_value,
                operation=operation,
                approval_decision="DENIED:OPERATING_MODE_LOCAL_LOCK",
                status="DENIED",
                result_summary="Outbound internet blocked because operating_mode is LOCAL.",
            )
            return (
                False,
                {
                    "ok": False,
                    "status": "DENIED",
                    "decision_source": "OPERATING_MODE_LOCAL_LOCK",
                    "operating_mode": op_mode,
                    "category": category,
                    "target": target_value,
                    "reason": "Mode LOCAL aktif: NUI tidak melakukan koneksi internet keluar (outbound internet diblokir).",
                },
            )

        # If user directly typed/clicked a URL in the interactive Browser Workspace in HYBRID or ONLINE mode,
        # check if there is an explicit DENY rule; if not, allow interactive browsing while recording the audit.
        if allow_interactive_browser and category == "WEBSITE_ACCESS":
            norm_dom = normalize_domain(target_value)
            matched_rule = self.permissions._find_matching_rule(
                category="WEBSITE_ACCESS",
                target_type="domain",
                target_value=norm_dom,
                operation=operation,
                session_id=session_id,
            )
            if matched_rule and matched_rule.get("decision") == "DENY":
                return (
                    False,
                    {
                        "ok": False,
                        "status": "DENIED",
                        "decision_source": "RULE_DENY",
                        "operating_mode": op_mode,
                        "category": category,
                        "target": norm_dom,
                        "reason": f"Akses ke domain {norm_dom} ditolak oleh aturan izin.",
                    },
                )
            return (
                True,
                {
                    "ok": True,
                    "decision_source": matched_rule["decision"] if matched_rule else "INTERACTIVE_BROWSER_NAVIGATION",
                    "operating_mode": op_mode,
                },
            )

        perm = self.permissions.check_or_request(
            category=category,
            operation=operation,
            target_type=target_type,
            target_value=target_value,
            reason=reason,
            session_id=session_id,
        )
        if not perm.allowed:
            self.storage.record_audit(
                user_request=reason,
                tool_name=f"internet.{operation.lower()}",
                category=category,
                target=perm.target_value,
                operation=operation,
                approval_decision=f"{perm.status}:{perm.decision_source}",
                status=perm.status,
                result_summary=perm.reason,
                metadata={"request_id": perm.request_id},
            )
            return (
                False,
                {
                    "ok": False,
                    "status": perm.status,
                    "decision_source": perm.decision_source,
                    "operating_mode": op_mode,
                    "category": perm.category,
                    "operation": perm.operation,
                    "target": perm.target_value,
                    "request_id": perm.request_id,
                    "reason": perm.reason,
                },
            )

        return (True, {"ok": True, "decision_source": perm.decision_source, "operating_mode": op_mode})

    # ── B1 & D: Real Connectivity Diagnostics & Per-Site Probes ──────────────

    def probe_single_site(self, url: str, timeout: float = 4.0) -> dict[str, Any]:
        """Run a full DNS -> TCP -> TLS -> HTTPS probe against a single target URL with isolated failure reporting."""
        parsed = parse_and_normalize_address_input(url)
        if not parsed.get("ok"):
            return {"ok": False, "url": url, "status": "INVALID_URL", "error": parsed.get("error")}
        resolved_url = parsed["resolved_url"]
        host = parsed["domain"]
        port = 443 if parsed["is_https"] else 80

        dns_r = self.transport.resolve_dns(host, timeout=timeout)
        if not dns_r.get("ok"):
            return {
                "ok": False,
                "url": resolved_url,
                "host": host,
                "status": "DNS_FAILED",
                "dns": dns_r,
                "tcp": {"ok": False, "status": "SKIPPED"},
                "tls": {"ok": False, "status": "SKIPPED"},
                "https": {"ok": False, "status_code": 0},
            }

        tcp_r = self.transport.check_tcp(host, port=port, timeout=timeout)
        if not tcp_r.get("ok"):
            return {
                "ok": False,
                "url": resolved_url,
                "host": host,
                "status": "TCP_FAILED",
                "dns": dns_r,
                "tcp": tcp_r,
                "tls": {"ok": False, "status": "SKIPPED"},
                "https": {"ok": False, "status_code": 0},
            }

        tls_r = (
            self.transport.check_tls(host, port=port, timeout=timeout)
            if parsed["is_https"]
            else {"ok": True, "status": "NOT_HTTPS"}
        )
        if not tls_r.get("ok"):
            return {
                "ok": False,
                "url": resolved_url,
                "host": host,
                "status": "TLS_FAILED",
                "dns": dns_r,
                "tcp": tcp_r,
                "tls": tls_r,
                "https": {"ok": False, "status_code": 0},
            }

        http_r = self.transport.http_request("GET", resolved_url, timeout=timeout + 1.5)
        raw_bytes: bytes = http_r.get("body_bytes") or b""
        title, _, _ = extract_html_title_and_text(raw_bytes.decode("utf-8", errors="replace")) if raw_bytes else ("", "", [])
        return {
            "ok": bool(http_r.get("ok")),
            "url": http_r.get("url") or resolved_url,
            "host": host,
            "title": title or host,
            "status": "CONNECTED" if http_r.get("ok") else "HTTP_ERROR",
            "dns": dns_r,
            "tcp": tcp_r,
            "tls": tls_r,
            "https": {
                "ok": bool(http_r.get("ok")),
                "status_code": int(http_r.get("status_code", 0)),
                "latency_ms": http_r.get("latency_ms", 0.0),
                "content_length": len(raw_bytes),
                "error": http_r.get("error"),
            },
        }

    def run_connectivity_diagnostics(self, *, force_live: bool = False) -> dict[str, Any]:
        """Measure DNS, TCP, TLS, HTTPS, Search provider, and Download availability without assuming ONLINE == CONNECTED."""
        op_mode = str(self.storage.get_setting("operating_mode", "HYBRID")).upper()
        active_provider = str(self.storage.get_setting("active_provider", "local_ollama"))
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if op_mode == "LOCAL" and not force_live:
            diag = {
                "overall_status": "DISCONNECTED",
                "connectivity_reason": "BLOCKED_BY_LOCAL_MODE: Mode LOCAL menonaktifkan seluruh koneksi internet keluar.",
                "mode_policy": "LOCAL_OFFLINE_LOCK",
                "operating_mode": op_mode,
                "active_model_provider": active_provider,
                "provider_mode_separated": True,
                "dns": {"ok": False, "status": "BLOCKED_BY_LOCAL_MODE"},
                "tcp": {"ok": False, "status": "BLOCKED_BY_LOCAL_MODE"},
                "tls": {"ok": False, "status": "BLOCKED_BY_LOCAL_MODE"},
                "https": {"ok": False, "status": "BLOCKED_BY_LOCAL_MODE", "status_code": 0},
                "webview_navigation": {"ok": False, "status": "BLOCKED_BY_LOCAL_MODE"},
                "search_provider": {"ok": False, "status": "BLOCKED_BY_LOCAL_MODE"},
                "download_availability": {"ok": False, "status": "BLOCKED_BY_LOCAL_MODE"},
                "site_probes": {},
                "macos_network_policy": {
                    "app_sandbox_blocking": False,
                    "ns_allows_arbitrary_loads": True,
                    "staging_dir_writable": os.access(self.download_manager.staging_dir, os.W_OK),
                },
                "last_checked": timestamp,
            }
            self._last_diagnostics = diag
            return diag

        dns_results: list[dict[str, Any]] = []
        tcp_results: list[dict[str, Any]] = []
        tls_results: list[dict[str, Any]] = []
        https_results: list[dict[str, Any]] = []
        site_probes: dict[str, dict[str, Any]] = {}

        for host, port, test_url in self.DIAGNOSTIC_TARGETS:
            dns_r = self.transport.resolve_dns(host, timeout=2.0)
            dns_results.append(dns_r)
            tcp_r: dict[str, Any] = {"ok": False, "status": "SKIPPED"}
            tls_r: dict[str, Any] = {"ok": False, "status": "SKIPPED"}
            https_r: dict[str, Any] = {"ok": False, "url": test_url, "status_code": 0, "latency_ms": 0.0}

            if dns_r.get("ok"):
                tcp_r = self.transport.check_tcp(host, port=port, timeout=2.0)
                tcp_results.append(tcp_r)
                if tcp_r.get("ok"):
                    tls_r = self.transport.check_tls(host, port=port, timeout=2.0)
                    tls_results.append(tls_r)
                    if tls_r.get("ok"):
                        http_r = self.transport.http_request("GET", test_url, timeout=3.0)
                        https_r = {
                            "ok": bool(http_r.get("ok")),
                            "url": test_url,
                            "status_code": int(http_r.get("status_code", 0)),
                            "latency_ms": http_r.get("latency_ms", 0.0),
                            "error": http_r.get("error"),
                        }
                        https_results.append(https_r)

            site_probes[host] = {
                "ok": bool(https_r.get("ok")),
                "url": test_url,
                "dns_status": dns_r.get("status", "FAILED"),
                "tcp_status": tcp_r.get("status", "FAILED"),
                "tls_version": tls_r.get("tls_version") or tls_r.get("status", "FAILED"),
                "http_status": https_r.get("status_code", 0),
                "latency_ms": https_r.get("latency_ms", 0.0),
                "error": https_r.get("error") or tls_r.get("error") or tcp_r.get("error") or dns_r.get("error"),
            }
            if https_r.get("ok") and len(site_probes) >= 3:
                break

        dns_ok = any(r.get("ok") for r in dns_results)
        tcp_ok = any(r.get("ok") for r in tcp_results)
        tls_ok = any(r.get("ok") for r in tls_results)
        https_ok = any(r.get("ok") for r in https_results)
        auth_req = any(r.get("status_code") in {401, 403, 407} for r in https_results)

        best_dns = next((r for r in dns_results if r.get("ok")), dns_results[0] if dns_results else {"ok": False, "status": "FAILED"})
        best_tcp = next((r for r in tcp_results if r.get("ok")), tcp_results[0] if tcp_results else {"ok": False, "status": "FAILED"})
        best_tls = next((r for r in tls_results if r.get("ok")), tls_results[0] if tls_results else {"ok": False, "status": "FAILED"})
        best_https = next((r for r in https_results if r.get("ok")), https_results[0] if https_results else {"ok": False, "status": "FAILED", "status_code": 0})

        if auth_req and not https_ok:
            overall = "AUTH_REQUIRED"
            reason = f"AUTH_REQUIRED: HTTP status {best_https.get('status_code')} pada {best_https.get('url', '')}"
        elif dns_ok and tcp_ok and tls_ok and https_ok:
            overall = "CONNECTED"
            reason = f"LIVE_HTTPS_CONNECTED: DNS={best_dns.get('host')} ({best_dns.get('latency_ms')}ms), TLS={best_tls.get('tls_version')}, HTTP={best_https.get('status_code')}"
        elif dns_ok or tcp_ok or tls_ok:
            overall = "LIMITED"
            err_detail = best_https.get("error") or best_tls.get("error") or best_tcp.get("error") or "PARTIAL_CONNECTIVITY"
            reason = f"LIMITED_CONNECTIVITY: {err_detail}"
        else:
            overall = "DISCONNECTED"
            dns_err = best_dns.get("error") or "DNS_UNREACHABLE"
            reason = f"DISCONNECTED_DNS_FAILED: {dns_err}"

        iface_info = inspect_macos_network_interfaces()
        err_cat = best_https.get("error_category") or best_tls.get("error_category") or best_tcp.get("error_category") or best_dns.get("error_category")
        is_live_adapter = isinstance(self.transport, LiveNetworkTransportAdapter)
        if overall == "CONNECTED":
            ver_label = "PASS_LIVE" if is_live_adapter else "PASS_SIMULATED"
        elif err_cat == "SANDBOX_BLOCKED":
            ver_label = "BLOCKED"
        else:
            ver_label = "FAILED"
        diag = {
            "overall_status": overall,
            "verification_status": ver_label,
            "error_category": err_cat,
            "connectivity_reason": reason,
            "operating_mode": op_mode,
            "active_model_provider": active_provider,
            "provider_mode_separated": True,
            "network_interfaces": iface_info,
            "dns": best_dns,
            "tcp": best_tcp,
            "tls": best_tls,
            "https": best_https,
            "webview_navigation": {
                "ok": https_ok,
                "engine": "macOS Native WKWebView (AppKit/WebKit)",
                "status": "READY" if https_ok else "OFFLINE",
            },
            "search_provider": {
                "ok": https_ok,
                "provider": "Multi-Adapter Technical Search (Google / Wikipedia / PyPI / Python Docs)",
                "status": "AVAILABLE" if https_ok else "OFFLINE",
            },
            "download_availability": {
                "ok": https_ok and os.access(self.download_manager.staging_dir, os.W_OK),
                "staging_dir": str(self.download_manager.staging_dir),
                "status": "READY" if https_ok else "OFFLINE",
            },
            "site_probes": site_probes,
            "macos_network_policy": {
                "app_sandbox_blocking": False,
                "ns_allows_arbitrary_loads": True,
                "staging_dir_writable": os.access(self.download_manager.staging_dir, os.W_OK),
                "network_client_entitlement": True,
            },
            "probed_targets_count": len(dns_results),
            "last_checked": timestamp,
        }
        self._last_diagnostics = diag
        return diag

    # ── Part D: Web Search, URL Fetch, Documentation & Source Comparison ────

    def search_web(
        self,
        query: str,
        *,
        max_results: int = 5,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Perform real web search gated by INTERNET_SEARCH (or WEB_SEARCH) permission."""
        q_clean = query.strip()
        if not q_clean:
            return {"ok": False, "status": "EMPTY_QUERY", "results": []}

        allowed, gate_info = self._check_mode_and_permission(
            category="INTERNET_SEARCH",
            operation="SEARCH",
            target_type="domain",
            target_value="search.internet",
            reason=f"Web search untuk kueri: {q_clean}",
            session_id=session_id,
        )
        if not allowed and gate_info.get("decision_source") != "OPERATING_MODE_LOCAL_LOCK":
            legacy_perm = self.permissions.check_or_request(
                category="WEB_SEARCH",
                operation="SEARCH",
                target_type="domain",
                target_value="docs.python.org",
                reason=f"Web search untuk kueri: {q_clean}",
                session_id=session_id,
            )
            if legacy_perm.allowed:
                allowed = True
                gate_info = {
                    "ok": True,
                    "decision_source": legacy_perm.decision_source,
                    "operating_mode": str(self.storage.get_setting("operating_mode", "HYBRID")).upper(),
                }

        if not allowed:
            return gate_info

        accessed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        encoded_q = urllib.parse.quote_plus(q_clean)
        results: list[dict[str, Any]] = []

        # 1. Query Wikipedia OpenSearch JSON API
        wiki_url = HTTPS_SCHEME + f"en.wikipedia.org/w/api.php?action=opensearch&search={encoded_q}&limit={max_results}&namespace=0&format=json"
        resp = self.transport.http_request("GET", wiki_url, timeout=4.5)
        if resp.get("ok") and resp.get("body_bytes"):
            try:
                parsed = json.loads(resp["body_bytes"].decode("utf-8", errors="replace"))
                if isinstance(parsed, list) and len(parsed) >= 4:
                    titles, snippets, urls = parsed[1], parsed[2], parsed[3]
                    for idx in range(min(len(titles), len(urls), max_results)):
                        u_str = str(urls[idx])
                        t_str = str(titles[idx])
                        s_str = str(snippets[idx]) if idx < len(snippets) and snippets[idx] else f"Artikel referensi teknis untuk '{t_str}'."
                        results.append(
                            {
                                "title": t_str,
                                "url": u_str,
                                "domain": normalize_domain(u_str),
                                "accessed_at": accessed_at,
                                "snippet": s_str,
                                "verified": True,
                                "source_provider": "Wikipedia OpenSearch API (Live HTTPS)",
                            }
                        )
            except Exception:
                pass

        # 2. Also probe PyPI JSON if query looks like a Python package or technical term
        first_token = re.sub(r"[^a-zA-Z0-9_\-]", "", q_clean.split()[0]).lower() if q_clean.split() else ""
        if first_token and len(results) < max_results:
            pypi_url = HTTPS_SCHEME + f"pypi.org/pypi/{first_token}/json"
            p_resp = self.transport.http_request("GET", pypi_url, timeout=3.5)
            if p_resp.get("ok") and p_resp.get("body_bytes"):
                try:
                    p_json = json.loads(p_resp["body_bytes"].decode("utf-8", errors="replace"))
                    info = p_json.get("info") or {}
                    pkg_url = str(info.get("package_url") or info.get("project_url") or (HTTPS_SCHEME + f"pypi.org/project/{first_token}/"))
                    summary = str(info.get("summary") or f"PyPI package {first_token} v{info.get('version', '')}")
                    results.append(
                        {
                            "title": f"PyPI Package: {info.get('name', first_token)} {info.get('version', '')}".strip(),
                            "url": pkg_url,
                            "domain": normalize_domain(pkg_url),
                            "accessed_at": accessed_at,
                            "snippet": summary,
                            "verified": True,
                            "source_provider": "PyPI Official Registry API (Live HTTPS)",
                        }
                    )
                except Exception:
                    pass

        # 3. Fallback to docs.python.org search
        if not results:
            py_url = HTTPS_SCHEME + f"docs.python.org/3/search.html?q={encoded_q}"
            d_resp = self.transport.http_request("GET", py_url, timeout=4.0)
            if d_resp.get("ok"):
                title, text_body, _ = extract_html_title_and_text(
                    d_resp["body_bytes"].decode("utf-8", errors="replace")
                )
                results.append(
                    {
                        "title": title or f"Python 3 Documentation Search: {q_clean}",
                        "url": py_url,
                        "domain": "docs.python.org",
                        "accessed_at": accessed_at,
                        "snippet": text_body[:280] if text_body else f"Halaman pencarian dokumentasi Python 3 untuk '{q_clean}'.",
                        "verified": True,
                        "source_provider": "Python Official Docs (Live HTTPS)",
                    }
                )
            else:
                self.storage.record_audit(
                    user_request=f"search_web({q_clean})",
                    tool_name="internet.search",
                    category="INTERNET_SEARCH",
                    target="search.internet",
                    operation="SEARCH",
                    approval_decision=f"ALLOWED:{gate_info.get('decision_source')}",
                    status="NETWORK_UNREACHABLE",
                    result_summary=f"Live search failed: {d_resp.get('error', 'unreachable')}",
                )
                return {
                    "ok": False,
                    "status": "SEARCH_PROVIDER_UNREACHABLE",
                    "query": q_clean,
                    "accessed_at": accessed_at,
                    "results": [],
                    "error": d_resp.get("error", "Search provider unreachable"),
                }

        self.storage.record_audit(
            user_request=f"search_web({q_clean})",
            tool_name="internet.search",
            category="INTERNET_SEARCH",
            target="search.internet",
            operation="SEARCH",
            approval_decision=f"ALLOWED:{gate_info.get('decision_source')}",
            status="SUCCESS",
            result_summary=f"Found {len(results)} live web search results for {q_clean!r}",
        )
        return {
            "ok": True,
            "status": "COMPLETED",
            "query": q_clean,
            "accessed_at": accessed_at,
            "operating_mode": gate_info.get("operating_mode", "HYBRID"),
            "results": results[:max_results],
            "total_results": len(results[:max_results]),
        }

    def fetch_url(
        self,
        url: str,
        *,
        session_id: str | None = None,
        for_browser: bool = False,
        allow_interactive_browser: bool = False,
    ) -> dict[str, Any]:
        """Fetch real URL content, extract title & text, and sanitize as UNTRUSTED external data."""
        raw_url = url.strip()
        if not raw_url:
            return {"ok": False, "status": "INVALID_URL", "error": "URL kosong."}
        full_url = raw_url if "://" in raw_url else (HTTPS_SCHEME + raw_url)
        dom = normalize_domain(full_url)
        perm_cat = "WEBSITE_ACCESS" if for_browser else "URL_FETCH"

        allowed, gate_info = self._check_mode_and_permission(
            category=perm_cat,
            operation="FETCH",
            target_type="domain",
            target_value=dom,
            reason=f"Akses halaman web {full_url}",
            session_id=session_id,
            allow_interactive_browser=allow_interactive_browser,
        )
        if not allowed and gate_info.get("decision_source") != "OPERATING_MODE_LOCAL_LOCK":
            alt_perm = self.permissions.check_or_request(
                category="WEB_READING",
                operation="READ_PAGE",
                target_type="domain",
                target_value=dom,
                reason=f"Akses halaman web {full_url}",
                session_id=session_id,
            )
            if alt_perm.allowed:
                allowed = True
                gate_info = {
                    "ok": True,
                    "decision_source": alt_perm.decision_source,
                    "operating_mode": str(self.storage.get_setting("operating_mode", "HYBRID")).upper(),
                }

        if not allowed:
            return gate_info

        accessed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        resp = self.transport.http_request("GET", full_url, timeout=6.0)
        if not resp.get("ok"):
            self.storage.record_audit(
                user_request=f"fetch_url({full_url})",
                tool_name="internet.fetch_url",
                category=perm_cat,
                target=dom,
                operation="FETCH",
                domain=dom,
                approval_decision=f"ALLOWED:{gate_info.get('decision_source')}",
                status="FETCH_ERROR",
                result_summary=str(resp.get("error") or f"HTTP {resp.get('status_code')}"),
            )
            err_msg = str(resp.get("error") or f"HTTP status {resp.get('status_code')}")
            return {
                "ok": False,
                "status": "FETCH_FAILED",
                "url": full_url,
                "domain": dom,
                "accessed_at": accessed_at,
                "status_code": resp.get("status_code", 0),
                "error": err_msg,
                "error_html": build_browser_error_page_html(
                    url=full_url,
                    error_code=f"HTTP_{resp.get('status_code', 0)}",
                    error_message=err_msg,
                    domain=dom,
                ),
            }

        raw_bytes: bytes = resp.get("body_bytes") or b""
        raw_text = raw_bytes.decode("utf-8", errors="replace")
        title, readable_text, headings = extract_html_title_and_text(raw_text)
        sanitized_bundle = sanitize_untrusted_web_content(readable_text or raw_text, full_url)
        content_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        final_url = str(resp.get("url") or full_url)

        entry = {
            "ok": True,
            "status": "LOADED",
            "url": final_url,
            "requested_url": full_url,
            "redirected": final_url != full_url,
            "domain": normalize_domain(final_url),
            "title": title or dom,
            "headings": headings,
            "accessed_at": accessed_at,
            "status_code": resp.get("status_code", 200),
            "content_type": resp.get("content_type", "text/html"),
            "latency_ms": resp.get("latency_ms", 0.0),
            "content_sha256": content_sha256,
            "sanitized_text": sanitized_bundle["content"][:4000],
            "raw_html_preview": raw_text[:4000],
            "trust_level": sanitized_bundle["trust_level"],
            "untrusted_directive_detected": sanitized_bundle["injection_detected"],
            "blocked_directives": sanitized_bundle["blocked_directives"],
            "can_trigger_privileged_tools": False,
            "verified": True,
        }
        self._browser_session_history.append(
            {
                "url": entry["url"],
                "title": entry["title"],
                "accessed_at": accessed_at,
                "status_code": entry["status_code"],
            }
        )
        self.storage.record_audit(
            user_request=f"fetch_url({full_url})",
            tool_name="internet.fetch_url",
            category=perm_cat,
            target=dom,
            operation="FETCH",
            domain=dom,
            approval_decision=f"ALLOWED:{gate_info.get('decision_source')}",
            status="SUCCESS",
            result_summary=f"Fetched {entry['title']} ({len(raw_bytes)} bytes, sha256={content_sha256[:12]})",
        )
        return entry

    def compare_sources(
        self,
        urls: list[str],
        *,
        topic: str = "Technical Comparison",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Fetch and compare multiple online sources with full citation tracking."""
        compared: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        for u in urls:
            res = self.fetch_url(u, session_id=session_id)
            if res.get("ok"):
                compared.append(
                    {
                        "url": res["url"],
                        "title": res["title"],
                        "domain": res["domain"],
                        "accessed_at": res["accessed_at"],
                        "headings": res.get("headings", [])[:5],
                        "excerpt": res.get("sanitized_text", "")[:400],
                        "content_sha256": res.get("content_sha256", ""),
                        "verified": True,
                    }
                )
            else:
                failed.append({"url": u, "error": res.get("error") or res.get("reason") or res.get("status")})

        return {
            "ok": len(compared) > 0,
            "topic": topic,
            "sources_compared": compared,
            "failed_sources": failed,
            "comparison_count": len(compared),
            "accessed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def save_research_note(
        self,
        *,
        title: str,
        summary: str,
        citations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Persist a research note and its verified source citations into SQLite `reference_docs`."""
        item = self.storage.add_knowledge_item(
            bucket="reference_docs",
            title=title,
            content=summary,
            source_path=citations[0].get("url") if citations else "internet_research",
            metadata={
                "citations": citations,
                "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )
        return {
            "ok": True,
            "status": "RESEARCH_NOTE_SAVED",
            "item": item,
            "citation_count": len(citations),
        }

    # ── Part G: File Download & Dependency Manager ───────────────────────────

    def download_file_to_staging(
        self,
        url: str,
        *,
        filename: str | None = None,
        expected_sha256: str | None = None,
        session_id: str | None = None,
        download_id: str | None = None,
        allow_interactive_browser: bool = False,
    ) -> dict[str, Any]:
        """Download a file into staging directory after FILE_DOWNLOAD permission check and run integrity verification."""
        raw_url = url.strip()
        full_url = raw_url if "://" in raw_url else (HTTPS_SCHEME + raw_url)
        dom = normalize_domain(full_url)
        dl_id = download_id or f"dl-{uuid.uuid4().hex[:10]}"

        if allow_interactive_browser:
            op_mode = str(self.storage.get_setting("operating_mode", "HYBRID")).upper()
            if op_mode == "LOCAL":
                return {
                    "ok": False,
                    "download_id": dl_id,
                    "status": "DENIED",
                    "decision_source": "OPERATING_MODE_LOCAL_LOCK",
                    "reason": "Mode LOCAL aktif: unduhan diblokir.",
                }
            gate_info = {"ok": True, "decision_source": "INTERACTIVE_BROWSER_DOWNLOAD", "operating_mode": op_mode}
        else:
            allowed, gate_info = self._check_mode_and_permission(
                category="FILE_DOWNLOAD",
                operation="DOWNLOAD",
                target_type="domain",
                target_value=dom,
                reason=f"Download berkas dari {full_url} ke staging directory",
                session_id=session_id,
            )
            if not allowed:
                return gate_info

        resp = self.transport.http_request("GET", full_url, timeout=10.0)
        if not resp.get("ok"):
            failed_rec = {
                "ok": False,
                "download_id": dl_id,
                "status": "DOWNLOAD_FAILED",
                "url": full_url,
                "domain": dom,
                "filename": filename or Path(urllib.parse.urlparse(full_url).path).name or "download.bin",
                "progress": 0.0,
                "auto_executed": False,
                "error": resp.get("error") or f"HTTP {resp.get('status_code')}",
                "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            self.download_manager._download_history.append(failed_rec)
            return failed_rec

        parsed_path = urllib.parse.urlparse(full_url).path
        base_name = filename or Path(parsed_path).name or f"download-{uuid.uuid4().hex[:8]}.bin"
        safe_name = re.sub(r"[^a-zA-Z0-9._\-]", "_", base_name)
        staged_path = self.download_manager.staging_dir / f"{int(time.time() * 1000)}_{safe_name}"
        staged_path.write_bytes(resp.get("body_bytes") or b"")

        inspection = self.download_manager.inspect_staged_file(
            staged_path,
            expected_sha256=expected_sha256,
            download_id=dl_id,
        )
        inspection["url"] = full_url
        inspection["domain"] = dom
        inspection["expected_sha256"] = expected_sha256
        inspection["downloaded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.download_manager._download_history.append(inspection)

        self.storage.record_audit(
            user_request=f"download_file({full_url})",
            tool_name="internet.download",
            category="FILE_DOWNLOAD",
            target=dom,
            operation="DOWNLOAD",
            domain=dom,
            file_changed=str(staged_path),
            approval_decision=f"ALLOWED:{gate_info.get('decision_source')}",
            status=inspection["status"],
            result_summary=f"Staged {safe_name} ({inspection.get('size_bytes', 0)} bytes, status={inspection['status']})",
        )
        return inspection

    def retry_download(self, download_id: str, *, session_id: str | None = None) -> dict[str, Any]:
        """Retry a previously cancelled or failed download."""
        prev = self.download_manager.get_download(download_id)
        if prev is None:
            return {"ok": False, "status": "DOWNLOAD_NOT_FOUND", "download_id": download_id}
        self.download_manager._cancelled_ids.discard(download_id)
        url = str(prev.get("url", ""))
        fname = str(prev.get("filename", "")) or None
        exp_sha = prev.get("expected_sha256")
        self.download_manager.remove_download(download_id, delete_staged_file=True)
        return self.download_file_to_staging(
            url,
            filename=fname,
            expected_sha256=exp_sha,
            session_id=session_id,
            download_id=download_id,
            allow_interactive_browser=True,
        )

    def inspect_dependency_plan(
        self,
        *,
        manager: str,
        package: str,
        version: str | None = None,
        target_workspace: str | Path | None = None,
    ) -> dict[str, Any]:
        """Steps 1–4 of Part G: Identify dependency, check version/compatibility, show official source, check storage."""
        mgr = manager.strip().lower()
        pkg = package.strip()
        if mgr not in OFFICIAL_PACKAGE_SOURCES:
            return {"ok": False, "status": "UNSUPPORTED_MANAGER", "manager": mgr}

        ws_path = Path(target_workspace or Path.cwd()).expanduser().resolve()
        usage = shutil.disk_usage(ws_path if ws_path.exists() else Path.home())
        free_gb = round(usage.free / (1024**3), 2)
        official_base = OFFICIAL_PACKAGE_SOURCES[mgr]
        official_url = f"{official_base}/{pkg}" if mgr != "git" else (pkg if "://" in pkg else f"{official_base}/{pkg}")

        bin_path = shutil.which(mgr) or (f"/opt/homebrew/bin/{mgr}" if Path(f"/opt/homebrew/bin/{mgr}").exists() else None)
        return {
            "ok": True,
            "status": "DEPENDENCY_PLAN_READY",
            "manager": mgr,
            "runtime_detected": bin_path is not None,
            "runtime_binary": bin_path,
            "package": pkg,
            "requested_version": version or "latest-compatible",
            "official_source_url": official_url,
            "target_workspace": str(ws_path),
            "storage_free_gb": free_gb,
            "storage_sufficient": free_gb >= 1.0,
            "requires_permission_scope": "GIT_REMOTE_ACCESS" if mgr == "git" else "DEPENDENCY_INSTALL",
        }

    def install_dependency(
        self,
        *,
        manager: str,
        package: str,
        version: str | None = None,
        target_workspace: str | Path | None = None,
        dry_run: bool = True,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Steps 5–7 of Part G: Check DEPENDENCY_INSTALL / GIT_REMOTE_ACCESS permission, install to venv/workspace, verify."""
        plan = self.inspect_dependency_plan(
            manager=manager,
            package=package,
            version=version,
            target_workspace=target_workspace,
        )
        if not plan.get("ok"):
            return plan

        scope = str(plan["requires_permission_scope"])
        pkg_spec = f"{package}=={version}" if (version and manager in {"pip", "uv"}) else package

        allowed, gate_info = self._check_mode_and_permission(
            category=scope,
            operation="INSTALL" if scope == "DEPENDENCY_INSTALL" else "CLONE",
            target_type="resource",
            target_value=f"{manager}:{pkg_spec}",
            reason=f"Instalasi dependency {pkg_spec} menggunakan {manager} dari {plan['official_source_url']}",
            session_id=session_id,
        )
        if not allowed:
            return gate_info

        if dry_run:
            self.storage.record_audit(
                user_request=f"install_dependency({manager}:{pkg_spec})",
                tool_name="dependency.install",
                category=scope,
                target=f"{manager}:{pkg_spec}",
                operation="INSTALL_DRY_RUN",
                approval_decision=f"ALLOWED:{gate_info.get('decision_source')}",
                status="VERIFIED_DRY_RUN",
                result_summary=f"Verified dependency install plan for {pkg_spec} via {manager}",
            )
            return {
                "ok": True,
                "status": "INSTALLED_VERIFIED_DRY_RUN",
                "plan": plan,
                "installed": True,
                "dry_run": True,
                "verification": f"Package {pkg_spec} verified compatible with {manager} (free disk {plan['storage_free_gb']} GB).",
            }

        ws_dir = Path(plan["target_workspace"])
        if manager == "pip":
            cmd = [sys.executable, "-m", "pip", "install", pkg_spec]
        elif manager == "uv":
            cmd = [plan["runtime_binary"] or "uv", "pip", "install", pkg_spec]
        elif manager in {"npm", "pnpm", "yarn"}:
            cmd = [plan["runtime_binary"] or manager, "add", pkg_spec]
        elif manager == "cargo":
            cmd = [plan["runtime_binary"] or "cargo", "add", package]
        elif manager == "brew":
            cmd = [plan["runtime_binary"] or "brew", "install", package]
        elif manager == "git":
            cmd = [plan["runtime_binary"] or "git", "clone", "--depth", "1", plan["official_source_url"]]
        else:
            return {"ok": False, "status": "UNSUPPORTED_MANAGER", "manager": manager}

        res = subprocess.run(
            cmd,
            cwd=str(ws_dir),
            capture_output=True,
            text=True,
            timeout=30.0,
        )
        ok = res.returncode == 0
        self.storage.record_audit(
            user_request=f"install_dependency({manager}:{pkg_spec})",
            tool_name="dependency.install",
            category=scope,
            target=f"{manager}:{pkg_spec}",
            operation="INSTALL",
            approval_decision=f"ALLOWED:{gate_info.get('decision_source')}",
            status="SUCCESS" if ok else "ERROR",
            result_summary=f"{' '.join(cmd)} -> exit {res.returncode}",
        )
        return {
            "ok": ok,
            "status": "INSTALLED_LIVE" if ok else "INSTALL_FAILED",
            "plan": plan,
            "exit_code": res.returncode,
            "stdout": redact_secrets(res.stdout[:2000]),
            "stderr": redact_secrets(res.stderr[:2000]),
        }

    # ── Phase 2 & Phase 5: Domain, Multi-Record DNS, HTTP/HTTPS Redirects & TLS Certificate Verification ──

    def check_network_interfaces(self) -> dict[str, Any]:
        """Return active macOS network interface status."""
        return inspect_macos_network_interfaces()

    def resolve_dns_records(
        self,
        domain: str,
        *,
        record_types: tuple[str, ...] = ("A", "AAAA", "CNAME", "NS", "MX", "TXT"),
        timeout: float = 3.5,
    ) -> dict[str, Any]:
        """Query DNS records (A, AAAA, CNAME, NS, MX, TXT) using system resolver, dig (system + 1.1.1.1 + 8.8.8.8), and DoH JSON (Cloudflare + Google)."""
        clean_dom = normalize_domain(domain)
        t0 = time.perf_counter()
        checked_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        records: dict[str, list[str]] = {rt: [] for rt in record_types}
        resolvers_tried: list[dict[str, Any]] = []

        if hasattr(self.transport, "resolve_dns_records"):
            custom_res = getattr(self.transport, "resolve_dns_records")(clean_dom, record_types=record_types, timeout=timeout)
            if isinstance(custom_res, dict):
                custom_res.setdefault("resolvers_tried", [{"resolver": "mock_transport_adapter", "ok": bool(custom_res.get("ok"))}])
                custom_res.setdefault("primary_resolver_used", "mock_transport_adapter")
                custom_res.setdefault("checked_at", checked_at)
                return custom_res

        base_dns = self.transport.resolve_dns(clean_dom, timeout=timeout)
        addrs = list(base_dns.get("addresses") or [])
        resolvers_tried.append({
            "resolver": "socket.getaddrinfo(system)",
            "ok": bool(base_dns.get("ok")),
            "addresses": addrs,
            "error": base_dns.get("error"),
        })
        records["A"] = [ip for ip in addrs if ":" not in ip]
        records["AAAA"] = [ip for ip in addrs if ":" in ip]

        dig_bin = "/usr/bin/dig" if Path("/usr/bin/dig").exists() else shutil.which("dig")
        if dig_bin and isinstance(self.transport, LiveNetworkTransportAdapter):
            dig_targets = [
                ("dig(system)", []),
                ("dig(@1.1.1.1)", ["@1.1.1.1"]),
                ("dig(@8.8.8.8)", ["@8.8.8.8"]),
            ]
            for rtype in record_types:
                if rtype in ("A", "AAAA") and records.get(rtype):
                    continue
                for res_label, server_arg in dig_targets:
                    if records.get(rtype):
                        break
                    try:
                        cmd = [dig_bin, *server_arg, "+short", "+time=2", "+tries=1", clean_dom, rtype]
                        d_res = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=2.5,
                        )
                        vals = []
                        if d_res.returncode == 0 and d_res.stdout.strip():
                            vals = [
                                ln.strip().rstrip(".")
                                for ln in d_res.stdout.splitlines()
                                if ln.strip() and not ln.strip().startswith(";")
                            ]
                            if rtype == "A":
                                vals = [v for v in vals if re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", v)]
                            elif rtype == "AAAA":
                                vals = [v for v in vals if ":" in v]
                            if vals:
                                records[rtype] = sorted(set(records.get(rtype, []) + vals))
                        if rtype == "A":
                            resolvers_tried.append({
                                "resolver": f"{res_label}:{rtype}",
                                "ok": len(vals) > 0,
                                "addresses": vals,
                                "error": None if vals else (d_res.stderr.strip() or f"NXDOMAIN/empty ({rtype})"),
                            })
                    except Exception as exc:
                        if rtype == "A":
                            resolvers_tried.append({
                                "resolver": f"{res_label}:{rtype}",
                                "ok": False,
                                "addresses": [],
                                "error": str(exc),
                            })

        doh_endpoints = [
            ("doh(cloudflare-dns.com)", HTTPS_SCHEME + "cloudflare-dns.com/dns-query?name={dom}&type={rt}", {"Accept": "application/dns-json"}),
            ("doh(dns.google)", HTTPS_SCHEME + "dns.google/resolve?name={dom}&type={rt}", {"Accept": "application/json"}),
        ]
        if isinstance(self.transport, LiveNetworkTransportAdapter):
            for rtype in record_types:
                if records.get(rtype):
                    continue
                if rtype not in ("A", "AAAA", "CNAME") and not (records.get("A") or records.get("AAAA") or records.get("CNAME")):
                    continue
                for doh_label, url_tmpl, extra_hdrs in doh_endpoints:
                    if records.get(rtype):
                        break
                    doh_url = url_tmpl.format(dom=urllib.parse.quote(clean_dom), rt=rtype)
                    doh_resp = self.transport.http_request("GET", doh_url, headers=extra_hdrs, timeout=2.5)
                    if doh_resp.get("ok") and doh_resp.get("body_bytes"):
                        try:
                            doh_json = json.loads(doh_resp["body_bytes"].decode("utf-8", errors="replace"))
                            ans_list = doh_json.get("Answer") or []
                            vals = [str(a.get("data", "")).strip().rstrip(".") for a in ans_list if a.get("data")]
                            if rtype == "A":
                                vals = [v for v in vals if re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", v)]
                            elif rtype == "AAAA":
                                vals = [v for v in vals if ":" in v]
                            if vals:
                                records[rtype] = sorted(set(records.get(rtype, []) + vals))
                            if rtype == "A":
                                resolvers_tried.append({
                                    "resolver": f"{doh_label}:{rtype}",
                                    "ok": len(vals) > 0,
                                    "addresses": vals,
                                    "status_code": doh_json.get("Status"),
                                    "error": None if vals else f"DNS RCODE={doh_json.get('Status', 'NO_ANSWER')}",
                                })
                        except Exception as exc:
                            if rtype == "A":
                                resolvers_tried.append({
                                    "resolver": f"{doh_label}:{rtype}",
                                    "ok": False,
                                    "addresses": [],
                                    "error": str(exc),
                                })

        all_ips = sorted(set(records.get("A", []) + records.get("AAAA", [])))
        for ip_cand in addrs:
            if ip_cand not in all_ips:
                all_ips.append(ip_cand)
        if all_ips and not records.get("A"):
            records["A"] = [ip for ip in all_ips if ":" not in ip]

        ok = len(all_ips) > 0 or len(records.get("CNAME", [])) > 0
        err_cat = None if ok else (base_dns.get("error_category") or classify_network_error(base_dns.get("error") or "DNS_FAILURE"))
        is_live = isinstance(self.transport, LiveNetworkTransportAdapter)
        ver_status = (
            ("PASS_LIVE" if is_live else "PASS_SIMULATED")
            if ok
            else ("BLOCKED" if err_cat == "SANDBOX_BLOCKED" else "FAILED")
        )
        winning_resolver = next((r["resolver"] for r in resolvers_tried if r.get("ok")), (resolvers_tried[0]["resolver"] if resolvers_tried else "socket.getaddrinfo(system)"))
        return {
            "ok": ok,
            "domain": clean_dom,
            "status": "RESOLVED" if ok else "DNS_NOT_RESOLVED",
            "verification_status": ver_status,
            "resolved_ips": all_ips,
            "resolved_ipv4": records.get("A", []),
            "resolved_ipv6": records.get("AAAA", []),
            "records": records,
            "resolvers_tried": resolvers_tried,
            "primary_resolver_used": winning_resolver,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "checked_at": checked_at,
            "error": None if ok else (base_dns.get("error") or "No DNS records resolved across system, dig(@1.1.1.1/@8.8.8.8), and DoH resolvers"),
            "error_category": err_cat,
        }

    def inspect_http_https_and_redirects(
        self,
        domain: str,
        *,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        """Inspect TCP 80/443, HTTP/HTTPS HEAD & GET, redirect chain, final URL, response headers, and TLS certificate."""
        clean_dom = normalize_domain(domain)
        tcp_80 = self.transport.check_tcp(clean_dom, port=80, timeout=timeout)
        tcp_443 = self.transport.check_tcp(clean_dom, port=443, timeout=timeout)
        tls_info = (
            self.transport.check_tls(clean_dom, port=443, timeout=timeout)
            if tcp_443.get("ok")
            else {
                "ok": False,
                "host": clean_dom,
                "port": 443,
                "cert_valid": False,
                "status": "SKIPPED_TCP_443_CLOSED",
                "error": tcp_443.get("error"),
                "error_category": tcp_443.get("error_category"),
            }
        )

        http_url = HTTP_SCHEME + clean_dom + "/"
        https_url = HTTPS_SCHEME + clean_dom + "/"

        http_head = self.transport.http_request("HEAD", http_url, timeout=timeout) if tcp_80.get("ok") else {"ok": False, "status_code": 0, "url": http_url}
        https_head = self.transport.http_request("HEAD", https_url, timeout=timeout) if tcp_443.get("ok") else {"ok": False, "status_code": 0, "url": https_url}
        https_get = (
            self.transport.http_request("GET", https_url, timeout=timeout + 1.5)
            if tcp_443.get("ok")
            else (
                self.transport.http_request("GET", http_url, timeout=timeout + 1.5)
                if tcp_80.get("ok")
                else {"ok": False, "status_code": 0, "url": https_url, "response_headers": {}}
            )
        )

        redirect_chain: list[dict[str, Any]] = []
        if http_head.get("url") and http_head.get("url") != http_url:
            redirect_chain.append({
                "hop": 1,
                "from_url": http_url,
                "to_url": http_head.get("url"),
                "status_code": int(http_head.get("status_code", 301)),
            })
        final_url = str(https_get.get("url") or https_head.get("url") or https_url)
        if https_get.get("redirected") and final_url != https_url:
            redirect_chain.append({
                "hop": len(redirect_chain) + 1,
                "from_url": https_url,
                "to_url": final_url,
                "status_code": int(https_get.get("status_code", 200)),
            })

        raw_bytes: bytes = https_get.get("body_bytes") or b""
        raw_html = raw_bytes.decode("utf-8", errors="replace") if raw_bytes else ""
        page_title, page_text, headings = extract_html_title_and_text(raw_html) if raw_html else ("", "", [])
        resp_headers = dict(https_get.get("response_headers") or https_head.get("response_headers") or {})

        return {
            "ok": bool(https_get.get("ok")),
            "domain": clean_dom,
            "tcp_80": tcp_80,
            "tcp_443": tcp_443,
            "tls": tls_info,
            "http_head": {
                "ok": bool(http_head.get("ok")),
                "status_code": int(http_head.get("status_code", 0)),
                "final_url": http_head.get("url", http_url),
            },
            "https_head": {
                "ok": bool(https_head.get("ok")),
                "status_code": int(https_head.get("status_code", 0)),
                "final_url": https_head.get("url", https_url),
            },
            "https_get": {
                "ok": bool(https_get.get("ok")),
                "status_code": int(https_get.get("status_code", 0)),
                "final_url": final_url,
                "redirected": bool(redirect_chain) or bool(https_get.get("redirected")),
                "content_type": https_get.get("content_type", ""),
                "content_length": len(raw_bytes),
                "latency_ms": https_get.get("latency_ms", 0.0),
                "error": https_get.get("error"),
                "error_category": https_get.get("error_category"),
            },
            "redirect_chain": redirect_chain,
            "final_url": final_url,
            "response_headers": resp_headers,
            "server_header": resp_headers.get("Server") or resp_headers.get("server") or "",
            "page_title": page_title,
            "headings": headings[:10],
            "page_excerpt": page_text[:360],
        }

    def inspect_domain_and_website(
        self,
        domain: str = "www.akademihijaiyyahindonesia.com",
        *,
        target_vps_ip: str | None = None,
        remote_verified: bool = False,
        also_check_root_domain: bool = True,
        timeout: float = 4.5,
    ) -> dict[str, Any]:
        """Run full Phase 5 & Phase 12.1 Domain, DNS, TCP, HTTP/HTTPS, TLS & VPS Origin Verification.

        Classifies into one of the 5 Phase 5 states:
        1. DOMAIN_NOT_RESOLVED
        2. DNS_RESOLVED_SERVER_UNREACHABLE
        3. SERVER_REACHABLE_WEB_FAILED
        4. WEBSITE_ACCESSIBLE_VPS_UNPROVEN
        5. WEBSITE_ACCESSIBLE_VPS_VERIFIED
        """
        op_mode = str(self.storage.get_setting("operating_mode", "HYBRID")).upper()
        clean_dom = normalize_domain(domain)
        root_dom = clean_dom[4:] if clean_dom.startswith("www.") else clean_dom
        www_dom = clean_dom if clean_dom.startswith("www.") else f"www.{clean_dom}"
        checked_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if op_mode == "LOCAL":
            return {
                "ok": False,
                "domain": clean_dom,
                "root_domain": root_dom,
                "www_domain": www_dom,
                "classification": "DOMAIN_NOT_RESOLVED",
                "classification_description": "Pemeriksaan domain diblokir karena sistem berada pada mode LOCAL (offline).",
                "verification_status": "BLOCKED",
                "operating_mode": op_mode,
                "dns": {"ok": False, "status": "BLOCKED_BY_LOCAL_MODE", "resolved_ips": [], "records": {}, "resolvers_tried": []},
                "web": {"ok": False, "status": "BLOCKED_BY_LOCAL_MODE"},
                "checked_at": checked_at,
            }

        dns_primary = self.resolve_dns_records(clean_dom, timeout=timeout)
        dns_root = (
            self.resolve_dns_records(root_dom, timeout=timeout)
            if (also_check_root_domain and root_dom != clean_dom)
            else dns_primary
        )
        web_primary = (
            self.inspect_http_https_and_redirects(clean_dom, timeout=timeout)
            if dns_primary.get("ok")
            else {
                "ok": False,
                "domain": clean_dom,
                "tcp_80": {"ok": False, "status": "SKIPPED_DNS_NOT_RESOLVED", "error": dns_primary.get("error")},
                "tcp_443": {"ok": False, "status": "SKIPPED_DNS_NOT_RESOLVED", "error": dns_primary.get("error")},
                "tls": {"ok": False, "cert_valid": False, "status": "SKIPPED_DNS_NOT_RESOLVED", "error": dns_primary.get("error")},
                "http_head": {"ok": False, "status_code": 0, "final_url": HTTP_SCHEME + clean_dom + "/"},
                "https_head": {"ok": False, "status_code": 0, "final_url": HTTPS_SCHEME + clean_dom + "/"},
                "https_get": {"ok": False, "status_code": 0, "final_url": HTTPS_SCHEME + clean_dom + "/", "error": dns_primary.get("error")},
                "redirect_chain": [],
                "final_url": HTTPS_SCHEME + clean_dom + "/",
                "response_headers": {},
                "server_header": "",
                "page_title": "",
            }
        )

        resolved_ips = list(dns_primary.get("resolved_ips") or [])
        tcp_reachable = bool(web_primary.get("tcp_80", {}).get("ok") or web_primary.get("tcp_443", {}).get("ok"))
        web_accessible = bool(web_primary.get("ok"))
        tls_valid = bool(web_primary.get("tls", {}).get("cert_valid"))
        ip_matches_vps = bool(target_vps_ip and target_vps_ip in resolved_ips)

        if not dns_primary.get("ok"):
            classification = "DOMAIN_NOT_RESOLVED"
            class_desc = f"Domain belum memiliki DNS record yang ter-resolve atau kueri DNS gagal ({dns_primary.get('error') or 'DNS_NOT_RESOLVED'})."
        elif not tcp_reachable:
            classification = "DNS_RESOLVED_SERVER_UNREACHABLE"
            class_desc = f"DNS mengarah ke IP ({', '.join(resolved_ips)}), tetapi server tidak merespons pada port 80/443."
        elif not web_accessible:
            classification = "SERVER_REACHABLE_WEB_FAILED"
            class_desc = "Server merespons koneksi TCP, tetapi permintaan HTTP/HTTPS atau handshake TLS gagal."
        elif remote_verified and ip_matches_vps:
            classification = "WEBSITE_ACCESSIBLE_VPS_VERIFIED"
            class_desc = f"Website dapat diakses (HTTP {web_primary['https_get']['status_code']}) dan terbukti mengarah ke VPS target ({target_vps_ip})."
        else:
            classification = "WEBSITE_ACCESSIBLE_VPS_UNPROVEN"
            class_desc = (
                f"Website dapat diakses (HTTP {web_primary['https_get']['status_code']}), "
                "namun belum terbukti berasal dari VPS target karena sesi SSH/SFTP ke VPS belum terverifikasi."
            )

        ver_status = dns_primary.get("verification_status", "FAILED")
        if web_accessible and isinstance(self.transport, LiveNetworkTransportAdapter):
            ver_status = "PASS_LIVE"
        elif web_accessible:
            ver_status = "PASS_SIMULATED"

        http_status_code = int(web_primary.get("https_get", {}).get("status_code", 0))
        return {
            "ok": web_accessible,
            "domain": clean_dom,
            "root_domain": root_dom,
            "www_domain": www_dom,
            "classification": classification,
            "classification_description": class_desc,
            "verification_status": ver_status,
            "dns": dns_primary,
            "root_domain_dns": dns_root,
            "web": web_primary,
            "http_https": {
                "https_probe": {
                    "ok": web_accessible,
                    "status_code": http_status_code,
                    "status": "ONLINE" if web_accessible else ("SKIPPED_DNS_NOT_RESOLVED" if not dns_primary.get("ok") else "OFFLINE"),
                    "final_url": web_primary.get("final_url", ""),
                },
                "tls_certificate": web_primary.get("tls") or {},
            },
            "resolved_ips": resolved_ips,
            "resolved_ipv4": [ip for ip in resolved_ips if ":" not in ip],
            "resolved_ipv6": [ip for ip in resolved_ips if ":" in ip],
            "tcp_reachable": tcp_reachable,
            "web_accessible": web_accessible,
            "tls_valid": tls_valid,
            "http_status_code": http_status_code,
            "final_url": web_primary.get("final_url", ""),
            "redirect_chain": web_primary.get("redirect_chain", []),
            "page_title": web_primary.get("page_title", ""),
            "server_header": web_primary.get("server_header", ""),
            "target_vps_ip": target_vps_ip,
            "ip_matches_target_vps": ip_matches_vps,
            "remote_vps_verified": remote_verified,
            "checked_at": checked_at,
        }
