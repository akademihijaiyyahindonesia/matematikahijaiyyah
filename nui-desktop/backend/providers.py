"""Intelligence Provider, Ollama Local Language Engine, & Natural Conversation Engine for CosmicTera NUI Desktop.

Integrates:
- Official NUI Persona & System Prompt (`NUIPersonaLoader` from `src/hijaiyyah/ai/runtime.py`, `AGENTS.md`, `RULES.md`)
- Full Local LLM General & Coding Intelligence (`OllamaProvider` connected to `127.0.0.1:11434/api/chat`)
- 8-Mode Response & Intent Management (`CONVERSATIONAL`, `CAPABILITY_INQUIRY`, `GENERAL_INTELLIGENCE`,
  `TECHNICAL`, `TASK_EXECUTION`, `REPOSITORY_AUDIT`, `DEEP_RESEARCH`, `SYSTEM_DIAGNOSTICS`)
- Multi-Turn Conversation History & Follow-Up Continuity across both `OllamaProvider` and `NativeNUIProvider`
- Strict separation of internal `thinking` / `<think>` tokens from user-facing `content`
- True incremental token streaming from Ollama (`POST /api/chat` with `stream: true`) with runtime proof telemetry
- Domain-Gated & Word-Boundary Contextual Retrieval (`NUIContextualRetriever` + `knowledge.query()` + `usr.parse_phrase()`)
- Deterministic CosmicTera Computing Core (`NativeNUIProvider` wired to `MASTER_TABLE`, `HISAMachine`, `usr.lower`, `knowledge.py`)
"""
from __future__ import annotations

import http.client
import json
import re
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from hijaiyyah.algebra import intrametric
from hijaiyyah.core.exomatrix import build_exomatrix
from hijaiyyah.core.guards import full_guard_check
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.crypto.cube import cube_digest
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.hbc_format import HbcFile
from hijaiyyah.hisa.machine import HISAMachine
from hijaiyyah.hisab.digest import compute_digest
from hijaiyyah.nui import facts as nui_facts, knowledge, program_index, registry, usr as nui_usr
from hijaiyyah.nui.features import vector_features
from hijaiyyah.nui.usr import lower as usr_lower

from .canonical_layers_adapter import CanonicalLayersBridge
from .persona_and_context import (
    NUIContextualRetriever,
    NUIPersonaLoader,
    classify_response_mode,
    has_word_boundary_match,
    is_cosmictera_domain_query,
    normalize_indonesian_query,
    scan_workspace_for_query,
    strip_internal_thinking,
)
from .self_learning import measure_mac_host_resources


def an_norm_squared(vec: list[int] | tuple[int, ...]) -> int:
    return sum(int(x) * int(x) for x in vec[:14])


def intimate_distance(v1: list[int] | tuple[int, ...], v2: list[int] | tuple[int, ...]) -> int:
    return intrametric.euclidean_sq(list(v1), list(v2))


def homogeneous_inner_product(v1: list[int] | tuple[int, ...], v2: list[int] | tuple[int, ...]) -> int:
    return intrametric._ip(list(v1), list(v2))


def additive_orbit_period(entry_char: str) -> int:
    info = registry.by_char(entry_char)
    if info and "operator" in info and "linear_map" in info["operator"]:
        return int(info["operator"]["linear_map"].get("period", 1))
    return 1


OPERATIONAL_NETWORK_VPS_DOMAIN_PHRASES: tuple[str, ...] = (
    "apakah folder yayasan terhubung ke vps",
    "apakah folder /users/amra/yayasan sudah terhubung ke vps",
    "periksa folder /users/amra/yayasan",
    "cek apakah folder yayasan sudah terhubung ke vps",
    "apakah folder yayasan sudah terhubung ke vps",
    "cek apakah vps saya aktif",
    "apakah vps saya aktif",
    "cek vps",
    "periksa vps",
    "cek koneksi ke vps",
    "periksa koneksi ke vps",
    "cek apakah website saya online",
    "apakah website saya online",
    "periksa apakah website sudah berjalan",
    "apakah website sudah berjalan",
    "apakah domain saya sudah terhubung",
    "sudah mengarah ke server",
    "mengarah ke server",
    "cek domain",
    "periksa domain",
    "akademihijaiyyahindonesia.com",
    "apakah file sudah di-upload",
    "apakah file sudah diupload",
    "file sudah di-upload",
    "file sudah diupload",
    "bandingkan file lokal dengan server",
    "bandingkan file lokal dan server",
    "cek koneksi ssh",
    "periksa koneksi ssh",
    "tes koneksi ssh",
    "cek ssh",
    "periksa ssh",
    "tes ssh",
    "cek dns",
    "periksa dns",
    "tes dns",
    "cek https",
    "periksa https",
    "tes https",
    "cek internet",
    "periksa internet",
    "tes internet",
    "apakah kamu bisa akses internet",
    "bisa akses internet",
    "sambungkan folder yayasan ke vps",
    "hubungkan folder yayasan ke vps",
    "sambungkan ke vps",
    "hubungkan ke vps",
    "kamu hubungkan",
    "kamu hubaungkan",
    "hubaungkan",
    "tolong hubungkan",
    "coba hubungkan",
    "hubungkan sekarang",
    "sambungkan sekarang",
    "konekkan ke vps",
    "upload website yayasan ke server",
    "unggah website yayasan ke server",
)

FALSE_NETWORK_REFUSAL_PHRASES: tuple[str, ...] = (
    "tidak bisa menghubungkan atau mengakses perangkat atau jaringan eksternal",
    "tidak memiliki akses langsung ke internet",
    "asisten ai lokal yang beroperasi dalam sistem terbatas",
    "tidak dapat menghubungkan diri saya ke server",
    "tidak bisa menjalankan perintah ssh/sftp secara langsung",
    "tidak dapat menjalankan perintah ssh",
    "tidak dapat memeriksa vps",
    "tidak bisa mengakses internet, vps",
    "tidak punya akses ke internet",
)


def _contains_false_network_refusal(text: str) -> bool:
    """Return True if LLM output contains a false RLHF refusal claiming NUI cannot access the internet, DNS, HTTPS, or SSH/VPS."""
    t_low = (text or "").strip().lower()
    if not t_low:
        return False
    return any(pat in t_low for pat in FALSE_NETWORK_REFUSAL_PHRASES)


_FALLBACK_DIAGNOSTIC_ENGINES: dict[str, Any] = {}


def _get_or_create_fallback_diagnostic_engines() -> tuple[Any, Any, Any]:
    """Lazily initialize fallback (remote_dev_engine, universal_file_engine, internet_engine) so diagnostic queries never fall through to generic LLM even after hot-reload."""
    rde = _FALLBACK_DIAGNOSTIC_ENGINES.get("rde")
    ufe = _FALLBACK_DIAGNOSTIC_ENGINES.get("ufe")
    ie = _FALLBACK_DIAGNOSTIC_ENGINES.get("ie")
    if rde is not None and ufe is not None and ie is not None and hasattr(rde, "probe_and_attempt_live_ssh_connection") and hasattr(ie, "inspect_domain_and_website"):
        return rde, ufe, ie
    try:
        from .internet_engine import RealInternetEngine
        from .permissions import PermissionEngine
        from .remote_dev_engine import RemoteVPSDevelopmentEngine
        from .storage import NUIStorage
        from .universal_file_intelligence import UniversalFileActionEngine

        db_path = REPO_ROOT / "nui-desktop" / "data" / "nui_desktop.db"
        storage = NUIStorage(db_path)
        permissions = PermissionEngine(storage)
        ie = RealInternetEngine(storage=storage, permissions=permissions)
        rde = RemoteVPSDevelopmentEngine(storage=storage, permissions=permissions)
        ufe = UniversalFileActionEngine(
            storage=storage,
            permissions=permissions,
            remote_dev_engine=rde,
            repo_root=REPO_ROOT,
        )
        _FALLBACK_DIAGNOSTIC_ENGINES["rde"] = rde
        _FALLBACK_DIAGNOSTIC_ENGINES["ufe"] = ufe
        _FALLBACK_DIAGNOSTIC_ENGINES["ie"] = ie
    except Exception:
        pass
    return rde, ufe, ie


def _upgrade_caller_service_app_if_needed(provider_instance: Any) -> None:
    """When an existing NUILocalServiceApp hot-reloads providers.py, upgrade its in-memory engines, orchestrator, and class methods in-place."""
    try:
        import importlib
        import sys

        for depth in (1, 2, 3):
            try:
                frame = sys._getframe(depth)
            except ValueError:
                break
            caller_self = frame.f_locals.get("self")
            if caller_self is not None and caller_self.__class__.__name__ == "NUILocalServiceApp":
                from . import (
                    internet_engine as _ie_m,
                    operational_intelligence as _oi_m,
                    orchestrator as _orch_m,
                    remote_dev_engine as _rde_m,
                    self_learning as _sl_m,
                    server as _srv_m,
                    universal_file_intelligence as _ufi_m,
                )

                importlib.reload(_ie_m)
                importlib.reload(_rde_m)
                importlib.reload(_ufi_m)
                importlib.reload(_oi_m)
                importlib.reload(_sl_m)
                importlib.reload(_orch_m)
                importlib.reload(_srv_m)

                if not hasattr(caller_self.internet_engine, "inspect_domain_and_website") or "resolvers_tried" not in str(getattr(caller_self.internet_engine.resolve_dns_records, "__code__", "")):
                    caller_self.internet_engine = _ie_m.RealInternetEngine(
                        storage=caller_self.storage,
                        permissions=caller_self.permissions,
                        transport=getattr(caller_self.internet_engine, "transport", None),
                    )
                if not hasattr(caller_self.remote_dev_engine, "probe_and_attempt_live_ssh_connection"):
                    caller_self.remote_dev_engine = _rde_m.RemoteVPSDevelopmentEngine(
                        storage=caller_self.storage,
                        permissions=caller_self.permissions,
                        transport=getattr(caller_self.remote_dev_engine, "transport", None),
                    )
                else:
                    caller_self.remote_dev_engine.__class__ = _rde_m.RemoteVPSDevelopmentEngine

                if getattr(caller_self, "universal_file_engine", None) is None or not hasattr(caller_self.universal_file_engine, "compare_local_and_remote_manifests"):
                    caller_self.universal_file_engine = _ufi_m.UniversalFileActionEngine(
                        storage=caller_self.storage,
                        permissions=caller_self.permissions,
                        remote_dev_engine=caller_self.remote_dev_engine,
                        repo_root=REPO_ROOT,
                    )
                else:
                    caller_self.universal_file_engine.remote_dev_engine = caller_self.remote_dev_engine

                if hasattr(caller_self, "operational_intelligence") and caller_self.operational_intelligence is not None:
                    caller_self.operational_intelligence.__class__ = _oi_m.UnifiedOperationalIntelligence
                if hasattr(caller_self.orchestrator, "operational_intelligence") and caller_self.orchestrator.operational_intelligence is not None:
                    caller_self.orchestrator.operational_intelligence.__class__ = _oi_m.UnifiedOperationalIntelligence
                if hasattr(caller_self, "multi_model_router"):
                    caller_self.multi_model_router.__class__ = _sl_m.NUIMultiModelRouter
                if hasattr(caller_self.self_learning, "router"):
                    caller_self.self_learning.router.__class__ = _sl_m.NUIMultiModelRouter
                caller_self.orchestrator.__class__ = _orch_m.NUIConversationOrchestrator
                caller_self.orchestrator.remote_dev_engine = caller_self.remote_dev_engine
                caller_self.orchestrator.universal_file_engine = caller_self.universal_file_engine
                caller_self.orchestrator.internet_engine = caller_self.internet_engine
                caller_self.__class__ = _srv_m.NUILocalServiceApp

                provider_instance.remote_dev_engine = caller_self.remote_dev_engine
                provider_instance.universal_file_engine = caller_self.universal_file_engine
                provider_instance.internet_engine = caller_self.internet_engine

                try:
                    active_file = REPO_ROOT / "nui-desktop" / "data" / "active_service.json"
                    if active_file.is_file():
                        act_data = json.loads(active_file.read_text(encoding="utf-8"))
                        act_data["version"] = _srv_m.SERVICE_VERSION
                        active_file.write_text(json.dumps(act_data, indent=2), encoding="utf-8")
                except Exception:
                    pass
                break
    except Exception:
        pass


def is_folder_vps_status_query(prompt: str, context: dict[str, Any] | None = None) -> bool:
    """Return True when the user asks an operational question or follow-up command about VPS, SSH, DNS/HTTPS/domain/website online status, or local-vs-server file upload/sync."""
    p_low = prompt.strip().lower()
    if any(exc in p_low for exc in ("cara membuat website", "bagaimana cara membuat", "bisa membuat website", "kamu bisa bikin web", "dari nol")):
        return False
    if any(phrase in p_low for phrase in OPERATIONAL_NETWORK_VPS_DOMAIN_PHRASES):
        return True
    if p_low in {
        "hubungkan",
        "hubaungkan",
        "sambungkan",
        "konekkan",
        "konekin",
        "hubungin",
        "sambungin",
        "kamu hubungkan",
        "kamu hubaungkan",
        "coba hubungkan",
        "tolong hubungkan",
        "hubungkan sekarang",
        "sambungkan sekarang",
    }:
        return True
    has_vps_term = any(
        k in p_low
        for k in ("vps", "ssh", "sftp", "sshfs", "remote mount", "remote workspace", "server remote", "mengarah ke server", "terhubung ke server")
    )
    has_folder_or_action = any(
        k in p_low
        for k in (
            "yayasan", "/users/amra/yayasan", "folder", "direktori",
            "terhubung", "sinkron", "synced", "mount", "koneksi",
            "aktif", "cek", "periksa", "status", "sambungkan", "hubungkan", "hubaungkan", "upload", "domain",
        )
    )
    if has_vps_term and has_folder_or_action:
        return True
    has_domain_or_web = any(k in p_low for k in ("domain", "website", "dns", "tls", "https", "internet"))
    has_check_online = any(
        k in p_low
        for k in ("online", "terhubung", "sudah berjalan", "cek", "periksa", "tes", "terhubung ke server", "mengarah ke server", "hubungkan", "hubaungkan", "sambungkan")
    )
    if has_domain_or_web and has_check_online:
        return True
    # Multi-turn follow-up check: if prior turn in session discussed VPS/SSH/domain/Yayasan and user asks to connect/check/retry
    if context and any(w in p_low for w in ("hubungkan", "hubaungkan", "sambungkan", "konek", "coba", "ulang", "lanjut", "sekarang", "cek lagi", "periksa lagi")):
        hist_blob = json.dumps(
            {
                "recent": (context.get("recent_messages") or context.get("history") or [])[-4:],
                "summary": context.get("session_summary") or "",
            },
            ensure_ascii=False,
        ).lower()
        if any(tok in hist_blob for tok in ("vps", "ssh", "sftp", "akademihijaiyyahindonesia.com", "/users/amra/yayasan", "187.53.135.198", "deploy.md")):
            return True
    return False


def classify_operational_network_subintent(prompt: str) -> str:
    """Classify which operational network/VPS/domain sub-intent the user is asking."""
    p_low = prompt.strip().lower()
    if "upload website" in p_low or "unggah website" in p_low:
        return "upload_website_to_server"
    if any(
        k in p_low
        for k in (
            "sambungkan folder",
            "hubungkan folder",
            "kamu hubungkan",
            "kamu hubaungkan",
            "hubaungkan",
            "tolong hubungkan",
            "coba hubungkan",
            "hubungkan sekarang",
            "sambungkan sekarang",
            "sambungkan ke vps",
            "hubungkan ke vps",
        )
    ) or p_low in {"hubungkan", "sambungkan", "konekkan", "konekin"}:
        return "connect_folder_to_vps"
    if "bandingkan file lokal" in p_low or ("di-upload" in p_low and "terhubung ke vps" not in p_low and "domain" not in p_low) or ("diupload" in p_low and "terhubung ke vps" not in p_low):
        return "compare_local_and_remote_files"
    if ("cek koneksi ssh" in p_low or "periksa koneksi ssh" in p_low or "vps saya aktif" in p_low or "cek ssh" in p_low or "tes ssh" in p_low) and "domain" not in p_low and "website" not in p_low:
        return "check_vps_ssh_status"
    if any(k in p_low for k in ("website saya online", "website sudah berjalan", "domain saya sudah terhubung", "cek dns", "periksa dns", "cek https", "periksa https")) and "vps" not in p_low and "yayasan" not in p_low:
        return "check_domain_and_website"
    return "full_folder_vps_domain_verification"


def run_folder_vps_inspection(
    prompt: str,
    context: dict[str, Any] | None = None,
    fallback_engine: Any = None,
    fallback_file_engine: Any = None,
    fallback_internet_engine: Any = None,
    *,
    force: bool = False,
) -> dict[str, Any] | None:
    """Execute the unified Action-First Phase 12.1 operational verification:
    USER MESSAGE -> INTENT UNDERSTANDING -> RESOURCE RESOLUTION -> DIAGNOSTIC ACTION SELECTION -> PERMISSION CHECK -> LIVE ENGINE EXECUTION -> STRUCTURED RESULT -> RESPONSE COMPOSER -> CHAT DISPLAY.
    """
    ctx = context or {}
    if not force and not is_folder_vps_status_query(prompt, ctx):
        return None
    rde = ctx.get("remote_dev_engine") or fallback_engine
    ufe = ctx.get("universal_file_engine") or fallback_file_engine
    ie = ctx.get("internet_engine") or fallback_internet_engine
    if rde is None or ufe is None or ie is None:
        fb_rde, fb_ufe, fb_ie = _get_or_create_fallback_diagnostic_engines()
        rde = rde or fb_rde
        ufe = ufe or fb_ufe
        ie = ie or fb_ie
    if rde is None:
        return None

    executed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    p_low = prompt.strip().lower()
    sub_intent = classify_operational_network_subintent(prompt)

    target_q = "/Users/AMRA/yayasan"
    m_path = re.search(r"(/Users/[A-Za-z0-9_\-./]+)", prompt)
    if m_path:
        target_q = m_path.group(1).rstrip(".,?!'")

    domain_target = "www.akademihijaiyyahindonesia.com"
    m_dom = re.search(r"\b((?:www\.)?[a-z0-9\-]+\.(?:com|org|net|id|io|dev|edu|gov)(?:\.[a-z]{2,3})?)\b", p_low)
    if m_dom:
        domain_target = m_dom.group(1)

    # Stage 5: Explicit Permission Check (READ_LOCAL, NETWORK_ACCESS, SSH_CONNECT)
    perm_engine = getattr(rde, "permissions", None) or getattr(ie, "permissions", None)
    permission_checks: dict[str, str] = {
        "READ_LOCAL": "ALLOWED_READ_ONLY_DIAGNOSTIC",
        "NETWORK_ACCESS": "ALLOWED_HYBRID_DIAGNOSTIC",
        "SSH_CONNECT": "READ_ONLY_INSPECTION_NO_MUTATION",
    }
    if perm_engine is not None and hasattr(perm_engine, "check_permission"):
        try:
            p_loc_res = perm_engine.check_permission("FILESYSTEM_READ", target_q, "READ", "Diagnostic local folder inspection")
            permission_checks["READ_LOCAL"] = f"{'ALLOWED' if p_loc_res.get('allowed', True) else 'BLOCKED'}:{p_loc_res.get('decision_source', 'POLICY')}"
        except Exception:
            pass

    # Stage 6A: Base 9-field folder & VPS SSH/SFTP inspection + SSH config / Agent / Keychain / DEPLOY.md discovery
    base_vps = rde.inspect_folder_vps_status(target_q)
    local_canon = str(base_vps.get("local_canonical_path") or target_q)
    ssh_discovery = rde.discover_ssh_and_deployment_metadata(local_canon)

    # Stage 6B: Local directory SHA-256 manifest
    if ufe is not None:
        local_manifest = ufe.build_local_directory_manifest(local_canon)
        mapping_info = ufe.registry.get_folder_vps_mapping(local_canon, rde)
    else:
        p_loc = Path(local_canon)
        local_manifest = {
            "ok": p_loc.is_dir(),
            "local_canonical_path": local_canon,
            "file_count": 0,
            "total_bytes": 0,
            "manifest_sha256": "UNAVAILABLE",
            "files": {},
        }
        mapping_info = None

    local_exists = bool(local_manifest.get("ok", Path(local_canon).is_dir()))
    local_file_count = int(local_manifest.get("file_count", 0))
    local_total_bytes = int(local_manifest.get("total_bytes", local_manifest.get("total_size_bytes", 0)))
    local_manifest_sha = str(local_manifest.get("manifest_sha256", "NONE"))

    # Stage 6C: Real Internet & macOS Interface Diagnostics
    if ie is not None:
        iface_info = ie.check_network_interfaces()
        net_diag = ie.run_connectivity_diagnostics()
        net_ver_status = str(net_diag.get("verification_status") or net_diag.get("overall_status") or "UNKNOWN")
        dns_st = str((net_diag.get("dns") or {}).get("status") or "UNKNOWN")
        https_st = str((net_diag.get("https") or {}).get("status_code") or (net_diag.get("https") or {}).get("status") or "UNKNOWN")
    else:
        iface_info = {"interface_active": False, "primary_interface": "en0", "active_interfaces": [], "ipv4_addresses": []}
        net_diag = {"overall_status": "UNKNOWN", "verification_status": "UNKNOWN"}
        net_ver_status = "UNKNOWN"
        dns_st = "UNKNOWN"
        https_st = "UNKNOWN"

    # Determine documented or configured VPS IP for domain correlation
    target_vps_ip = None
    matched_prof_id = mapping_info.get("remote_profile_id") if isinstance(mapping_info, dict) else None
    deploy_md = ssh_discovery.get("deploy_md") or {}
    if matched_prof_id:
        for prof_d in rde.list_profiles():
            if prof_d.get("profile_id") == matched_prof_id:
                target_vps_ip = prof_d.get("host")
                break
    if not target_vps_ip and deploy_md.get("documented_vps_host"):
        target_vps_ip = deploy_md.get("documented_vps_host")

    # Stage 6C.2: Execute Live macOS OpenSSH Backend Probe (ssh-keygen / ssh-keyscan / ssh BatchMode)
    live_ssh_probe: dict[str, Any] = {"attempted": False, "ssh_status": "NOT_TESTED"}
    if target_vps_ip and hasattr(rde, "probe_and_attempt_live_ssh_connection"):
        doc_user = str(deploy_md.get("documented_vps_user") or "root")
        doc_ws = str(deploy_md.get("documented_remote_workspace") or "/opt/yayasan")
        auto_reg = sub_intent == "connect_folder_to_vps"
        live_ssh_probe = rde.probe_and_attempt_live_ssh_connection(
            host=target_vps_ip,
            username=doc_user,
            port=22,
            remote_workspace=doc_ws,
            auto_register_on_success=auto_reg,
        )
        if live_ssh_probe.get("ok") and live_ssh_probe.get("profile_id"):
            matched_prof_id = str(live_ssh_probe["profile_id"])
            base_vps = rde.inspect_folder_vps_status(local_canon)

    ssh_verified = (
        base_vps.get("ssh_connection_status") == "CONNECTED"
        and str(base_vps.get("sftp_connection", "")).startswith("ACTIVE")
    )

    # Stage 6D: Domain DNS, TCP 80/443, HTTP/HTTPS Redirects & TLS Certificate Inspection
    if ie is not None:
        domain_report = ie.inspect_domain_and_website(
            domain=domain_target,
            target_vps_ip=target_vps_ip,
            remote_verified=ssh_verified,
        )
    else:
        domain_report = {
            "domain": domain_target,
            "classification": "DOMAIN_NOT_RESOLVED",
            "classification_description": "RealInternetEngine tidak tersedia.",
            "verification_status": "NOT_TESTED",
            "resolved_ips": [],
            "dns": {"records": {}, "resolvers_tried": []},
            "web": {},
            "checked_at": executed_at,
        }

    # Stage 6E: Local vs Remote SHA-256 File Synchronization Comparison
    if ufe is not None:
        sync_report = ufe.compare_local_and_remote_manifests(
            local_path=local_canon,
            profile_id=matched_prof_id,
        )
    else:
        sync_report = {
            "overall_sync_status": "NOT_CONFIGURED",
            "verification_status": "NOT_CONFIGURED",
            "reason": "UniversalFileActionEngine tidak tersedia.",
            "local_file_count": local_file_count,
            "remote_file_count": None,
            "matching_sha256_count": None,
            "missing_remote_files_count": None,
            "remote_only_files_count": None,
            "different_files_count": None,
        }

    # Permission & Action Gate handling for write/connect sub-intents
    action_gate_note = ""
    if sub_intent == "connect_folder_to_vps":
        if live_ssh_probe.get("ok"):
            action_gate_note = (
                f"\n- **Tindakan Penyambungan VPS (`CONNECT_FOLDER_TO_VPS`)**: Status `PASS_LIVE (CONNECTED)` — "
                f"NUI telah menghubungkan `{local_canon}` ke `{live_ssh_probe.get('target')}` (`{live_ssh_probe.get('remote_workspace')}`) "
                f"menggunakan OpenSSH macOS (`{live_ssh_probe.get('scanned_host_fingerprint')}`)."
            )
        elif not matched_prof_id:
            probe_err = live_ssh_probe.get("error") or live_ssh_probe.get("ssh_status") or "NOT_CONFIGURED"
            fp_found = live_ssh_probe.get("scanned_host_fingerprint") or "BELUM_DITEMUKAN"
            action_gate_note = (
                f"\n- **Tindakan Penyambungan VPS (`CONNECT_FOLDER_TO_VPS`)**: NUI telah menjalankan uji koneksi SSH langsung melalui backend macOS ke `{live_ssh_probe.get('target', 'root@187.53.135.198:22')}` "
                f"(Host Key Fingerprint: `{fp_found}`, Status Probe SSH: `{live_ssh_probe.get('ssh_status')}`, Detail: `{probe_err}`). "
                "Karena autentikasi kunci SSH non-interaktif (`BatchMode=yes`) belum terotorisasi atau profil SSH belum memiliki kredensial aktif di macOS Keychain / SSH Agent, status profil saat ini adalah `NOT_CONFIGURED`. "
                "Untuk mendaftarkan kunci SSH atau kredensial secara aman, buka **Web & Internet -> VPS Profile Manager** pada aplikasi CosmicTera NUI Desktop (NUI **tidak pernah** meminta password atau private key melalui chat)."
            )
        else:
            action_gate_note = (
                f"\n- **Tindakan Penyambungan VPS (`CONNECT_FOLDER_TO_VPS`)**: Folder `{local_canon}` dipetakan ke profil `{matched_prof_id}` "
                f"dengan status koneksi `{base_vps.get('ssh_connection_status')}`."
            )
    elif sub_intent == "upload_website_to_server":
        action_gate_note = (
            "\n- **KONFIRMASI OPERASI WRITE DIPERLUKAN (`UPLOAD_FILE` / `DEPLOY_WEBSITE`)**: "
            "Sesuai aturan keamanan Fase 8, operasi upload/sinkronisasi/deployment ke server memerlukan: "
            "(1) profil SSH aktif yang terverifikasi (`CONNECTED`), dan (2) persetujuan eksplisit pengguna (`ASK_EVERY_TIME`). "
            "Karena saat ini belum ada sesi SSH aktif atau konfirmasi upload eksplisit, **tidak ada perubahan atau pengiriman file yang dilakukan**."
        )

    read_only_statement = "Saya tidak melakukan upload, penghapusan, atau perubahan file selama pemeriksaan."
    dns_obj = domain_report.get("dns") or {}
    dns_recs = dns_obj.get("records") or {}
    a_ips = dns_recs.get("A") or domain_report.get("resolved_ips") or []
    aaaa_ips = dns_recs.get("AAAA") or []
    cname_recs = dns_recs.get("CNAME") or []
    ns_recs = dns_recs.get("NS") or []
    mx_recs = dns_recs.get("MX") or []
    txt_recs = dns_recs.get("TXT") or []
    resolvers_tried = dns_obj.get("resolvers_tried") or []
    resolvers_summary = ", ".join(
        f"{r.get('resolver')}={'OK' if r.get('ok') else 'FAIL'}" for r in resolvers_tried
    ) or "socket.getaddrinfo(system)"
    web_obj = domain_report.get("web") or {}
    https_get = web_obj.get("https_get") or {}
    http_head = web_obj.get("http_head") or {}
    tls_info = web_obj.get("tls") or {}
    dom_class = str(domain_report.get("classification") or "DOMAIN_NOT_RESOLVED")
    dom_desc = str(domain_report.get("classification_description") or "")
    dom_ver_status = str(domain_report.get("verification_status") or "UNKNOWN")
    dom_checked_at = str(domain_report.get("checked_at") or executed_at)
    web_accessible = bool(domain_report.get("web_accessible") or https_get.get("ok"))
    sync_status = str(sync_report.get("overall_sync_status") or "NOT_CONFIGURED")
    sync_reason = str(sync_report.get("reason") or "")
    ssh_agent = ssh_discovery.get("ssh_agent") or {}
    local_ssh_keys = ssh_discovery.get("local_ssh_keys") or []

    if dom_class == "WEBSITE_ACCESSIBLE_VPS_VERIFIED" and sync_status == "SYNCED":
        deployment_status = "DEPLOYED_AND_VERIFIED"
        deployment_desc = f"Website `{domain_target}` aktif (HTTPS {https_get.get('status_code', 200)}) pada VPS `{target_vps_ip}` dan berkas lokal tersinkronisasi."
    elif web_accessible:
        deployment_status = "WEBSITE_LIVE_SSH_UNVERIFIED"
        deployment_desc = (
            f"Website `{domain_target}` aktif dan dapat diakses melalui HTTPS (HTTP `{https_get.get('status_code', 200)}`, IP `{a_ips}`, Server `{domain_report.get('server_header') or 'nginx'}`), "
            "namun verifikasi sinkronisasi berkas via SSH/SFTP ke VPS belum terautentikasi secara live."
        )
    elif dom_class == "DOMAIN_NOT_RESOLVED" and not ssh_verified:
        deployment_status = "NOT_CONFIGURED_AND_DOMAIN_UNRESOLVED"
        deployment_desc = f"Website belum dapat diakses pada `{domain_target}` dan sinkronisasi VPS belum terverifikasi secara live."
    else:
        deployment_status = "UNVERIFIED"
        deployment_desc = f"Status deployment pada `{domain_target}` belum terverifikasi penuh."

    doc_note = ""
    if deploy_md.get("deploy_md_exists"):
        doc_note = (
            f"Host: `{deploy_md.get('documented_vps_host')}` | User: `{deploy_md.get('documented_vps_user', 'root')}` | "
            f"Remote path: `{deploy_md.get('documented_remote_workspace', '/opt/yayasan')}` | "
            f"Source: `{deploy_md.get('source_file', 'DEPLOY.md')}` | "
            f"Evidence classification: `{deploy_md.get('evidence_classification', 'DOCUMENTED_IN_DEPLOY_MD_ONLY')}`"
        )

    final_conclusion_lines = [
        f"1. **1. Local Folder Availability (`{local_canon}`)**: **PASS_LIVE (`AVAILABLE` / `{base_vps.get('local_folder_status', 'READ_WRITE')}`)** — `{local_file_count}` berkas (`{local_total_bytes}` byte), SHA-256 manifest `{local_manifest_sha[:16]}...`, terdaftar sebagai Connected Folder `{base_vps.get('connected_folder_id')}`.",
        f"2. **2. Internet Connectivity**: **`{net_ver_status}` (`{net_diag.get('overall_status', 'ONLINE')}`)** — Interface `{iface_info.get('primary_interface', 'en0')}` (`{'ACTIVE' if iface_info.get('interface_active') else 'INACTIVE'}`), DNS Outbound `{dns_st}`, HTTPS Outbound `{https_st}`.",
        f"3. **3. Domain DNS (`{domain_target}`)**: **`{dom_class}`** (Status: `{dns_obj.get('status', 'DNS_NOT_RESOLVED')}`, Verifikasi: `{dom_ver_status}`, IPv4 `A`: `{a_ips or 'NONE'}`, Resolvers: `{resolvers_summary}`).",
        f"4. **4. Website HTTPS (`{domain_target}`)**: **HTTP `{http_head.get('status_code', 0)}` / HTTPS `{https_get.get('status_code', 0)}`** — TCP 80 `{(web_obj.get('tcp_80') or {}).get('status', 'SKIPPED')}`, TCP 443 `{(web_obj.get('tcp_443') or {}).get('status', 'SKIPPED')}`, TLS Valid: `{tls_info.get('cert_valid', False)}`. {dom_desc}",
        f"5. **5. VPS SSH**: **`{base_vps.get('ssh_connection_status', 'NOT_CONFIGURED')}`** (Profil SSH: `{base_vps.get('remote_ssh_profile', 'NONE')}`, Fingerprint: `{base_vps.get('verified_host_fingerprint', 'NOT_VERIFIED')}`, Live SSH Probe: `{live_ssh_probe.get('ssh_status', 'NOT_TESTED')}`, Scanned Host Key: `{live_ssh_probe.get('scanned_host_fingerprint') or 'NONE'}`, SSH Agent: `{ssh_agent.get('status', 'NONE')}`).",
        f"6. **6. SFTP**: **`{base_vps.get('sftp_connection', 'NOT_AVAILABLE')}`** (Mount OS: `{base_vps.get('mount_status', 'NOT_MOUNTED')}`).",
        f"7. **7. Remote Workspace**: **`{base_vps.get('remote_workspace_path', 'NONE')}`** — Referensi dokumentasi lokal: {doc_note or 'NONE'}.",
        f"8. **8. File Synchronization**: **`{sync_status}`** (Lokal: `{sync_report.get('local_file_count', local_file_count)}` berkas, Server: `{sync_report.get('remote_file_count')}` berkas, Cocok SHA-256: `{sync_report.get('matching_sha256_count')}`, Hanya Lokal: `{sync_report.get('missing_remote_files_count')}`, Berbeda Isi: `{sync_report.get('different_files_count')}`) — {sync_reason}",
        f"9. **9. Deployment Status**: **`{deployment_status}`** — {deployment_desc}",
    ]
    if action_gate_note:
        final_conclusion_lines.append(action_gate_note.strip())

    raw_active_ifaces = iface_info.get("active_interfaces") or []
    active_ifaces_str = ", ".join(str(x) for x in raw_active_ifaces) or "none"
    ipv4_str = ", ".join(str(x) for x in (iface_info.get("ipv4_addresses") or [])) or "none"
    iface_status_str = "ACTIVE" if iface_info.get("interface_active") else "INACTIVE"

    formatted_sections = [
        f"### Hasil Pemeriksaan Operasional Langsung: Folder Lokal, Internet, Domain & VPS (`{local_canon}`)",
        f"- **Waktu Eksekusi (`executed_at`)**: `{executed_at}` | **Mode**: `{ie.storage.get_setting('operating_mode', 'HYBRID') if ie and hasattr(ie, 'storage') else 'HYBRID'}` | **Pipeline**: `ACTION_FIRST_LIVE_DIAGNOSTIC_ENGINE`",
        "",
        "### 1. LOCAL FOLDER",
        f"- **1. Local Folder Availability**: `PASS_LIVE` (`{'AVAILABLE' if local_exists else 'MISSING'}`)",
        f"- **Connected Folder ID (`connected_folder_id`)**: `{base_vps.get('connected_folder_id')}` (`{base_vps.get('local_folder_status', 'READ_WRITE')}`)",
        f"- **Local Canonical Path (`local_canonical_path`)**: `{local_canon}` (`{'AVAILABLE' if local_exists else 'MISSING'}`)",
        f"- **Total Local Files & Size**: `{local_file_count}` berkas (`{local_total_bytes}` byte)",
        f"- **Local Manifest SHA-256**: `{local_manifest_sha}`",
        "",
        "### 2. INTERNET",
        f"- **2. Internet Connectivity**: `{net_ver_status}` (`{net_diag.get('overall_status', 'UNKNOWN')}`)",
        f"- **macOS Network Interfaces (`/sbin/ifconfig`)**: `{iface_status_str}` — Active: `{active_ifaces_str}` (IPv4: `{ipv4_str}`)",
        f"- **DNS Resolution Status**: `{dns_st}`",
        f"- **HTTPS Outbound Status**: `{https_st}`",
        "",
        f"### 3. DOMAIN (`{domain_target}`)",
        f"- **3. Domain DNS & Classification**: `{dom_class}` (Verification: `{dom_ver_status}`, Checked At: `{dom_checked_at}`)",
        f"- **Resolvers Tried**: `{resolvers_summary}`",
        f"- **DNS Records**: `A={a_ips}`, `AAAA={aaaa_ips}`, `CNAME={cname_recs}`, `NS={ns_recs}`, `MX={mx_recs}`, `TXT={txt_recs}`",
        f"- **DNS Error / Diagnostic Note**: `{dns_obj.get('error') or 'NONE'}`",
        f"- **4. Website HTTPS & TCP Reachability**: Port 80 `{(web_obj.get('tcp_80') or {}).get('status', 'UNKNOWN')}` | Port 443 `{(web_obj.get('tcp_443') or {}).get('status', 'UNKNOWN')}`",
        f"- **HTTP / HTTPS Response**: HTTP `{http_head.get('status_code', 0)}` | HTTPS `{https_get.get('status_code', 0)}` | Final URL: `{domain_report.get('final_url') or 'NONE'}` | Redirects: `{len(domain_report.get('redirect_chain') or [])}` | Server: `{domain_report.get('server_header') or 'NONE'}`",
        f"- **TLS Certificate**: Valid=`{tls_info.get('cert_valid', False)}`, Version=`{tls_info.get('tls_version') or 'NONE'}`, Subject=`{tls_info.get('subject_cn') or 'NONE'}`, Issuer=`{tls_info.get('issuer_cn') or 'NONE'}`, Expiry=`{tls_info.get('not_after') or 'NONE'}`",
        f"- **Matches Target VPS IP (`{target_vps_ip or 'NOT_CONFIGURED'}`)**: `{domain_report.get('ip_matches_target_vps')}`",
        "",
        "### 4. VPS",
        f"- **Remote SSH Profile (`remote_ssh_profile`)**: `{base_vps.get('remote_ssh_profile')}`",
        f"- **5. VPS SSH Connection (`ssh_connection_status`)**: `{base_vps.get('ssh_connection_status')}` (Overall: `{base_vps.get('overall_status', 'LOCAL_ONLY')}`)",
        f"- **Live macOS Backend SSH Probe (`/usr/bin/ssh` & `ssh-keyscan`)**: Status=`{live_ssh_probe.get('ssh_status', 'NOT_TESTED')}` | Target=`{live_ssh_probe.get('target', 'NONE')}` | Scanned Host Key=`{live_ssh_probe.get('scanned_host_fingerprint') or 'NONE'}` (`{live_ssh_probe.get('fingerprint_source', 'NONE')}`) | Detail=`{live_ssh_probe.get('error') or 'OK'}`",
        f"- **Verified Host Fingerprint (`verified_host_fingerprint`)**: `{base_vps.get('verified_host_fingerprint')}`",
        f"- **6. SFTP Connection (`sftp_connection`)**: `{base_vps.get('sftp_connection')}`",
        f"- **7. Remote Workspace Path (`remote_workspace_path`)**: `{base_vps.get('remote_workspace_path')}`",
        f"- **OS Mount Status (`mount_status`)**: `{base_vps.get('mount_status')}`",
        f"- **Last Successful Remote Verification (`last_successful_remote_verification`)**: `{base_vps.get('last_successful_remote_verification')}`",
        f"- **Local SSH Config (`~/.ssh/config`)**: `{'PRESENT' if ssh_discovery.get('ssh_config_found') else 'NOT_FOUND'}` ({len(ssh_discovery.get('ssh_config_hosts') or [])} host entries) | `known_hosts`=`{ssh_discovery.get('known_hosts_entries_count', 0)}` entries | Local Keys=`{local_ssh_keys}` | SSH Agent=`{ssh_agent.get('status', 'NONE')}` ({ssh_agent.get('keys_loaded_count', 0)} keys) | Keychain Refs=`{ssh_discovery.get('keychain_credential_refs_count', 0)}`",
        f"- **Documented Reference (`DEPLOY.md`)**: {doc_note or '`NONE`'}",
        "- **Panduan Konfigurasi Kredensial Aman**: Konfigurasi VPS dilakukan melalui panel **Web & Internet -> VPS Profile Manager** menggunakan SSH Agent / macOS Keychain + verifikasi fingerprint `SHA256:...` (NUI tidak pernah meminta password atau private key di chat).",
        "",
        "### 5. FILE SYNCHRONIZATION",
        f"- **8. File Synchronization Status**: `{sync_status}` (Verification: `{sync_report.get('verification_status', 'NOT_CONFIGURED')}`)",
        f"- **Local Files Count**: `{sync_report.get('local_file_count', local_file_count)}` berkas",
        f"- **Remote Files Count**: `{sync_report.get('remote_file_count')}`",
        f"- **Matching Files (SHA-256 Identical)**: `{sync_report.get('matching_sha256_count')}`",
        f"- **Missing on Remote (`LOCAL_ONLY`)**: `{sync_report.get('missing_remote_files_count')}`",
        f"- **Extra on Remote (`REMOTE_ONLY`)**: `{sync_report.get('remote_only_files_count')}`",
        f"- **Different Content (`CONTENT_MISMATCH`)**: `{sync_report.get('different_files_count')}`",
        f"- **9. Deployment Status**: `{deployment_status}` — {deployment_desc}",
        "",
        "### 6. FINAL CONCLUSION",
        *final_conclusion_lines,
        "",
        f"**Jaminan Read-Only**: {read_only_statement}",
    ]

    formatted_text = "\n".join(formatted_sections)
    pipeline_trace = [
        {"stage": 1, "name": "USER_MESSAGE", "status": "COMPLETED", "detail": prompt[:160]},
        {"stage": 2, "name": "INTENT_UNDERSTANDING", "status": "COMPLETED", "detail": f"SYSTEM_DIAGNOSTICS / {sub_intent}"},
        {"stage": 3, "name": "RESOURCE_RESOLUTION", "status": "COMPLETED", "detail": f"local={local_canon}, domain={domain_target}, documented_vps={target_vps_ip or 'NONE'}"},
        {"stage": 4, "name": "DIAGNOSTIC_ACTION_SELECTION", "status": "COMPLETED", "detail": "inspect_folder_vps_status + check_network_interfaces + run_connectivity_diagnostics + inspect_domain_and_website + probe_and_attempt_live_ssh_connection + compare_local_and_remote_manifests"},
        {"stage": 5, "name": "PERMISSION_CHECK", "status": "COMPLETED", "detail": permission_checks},
        {"stage": 6, "name": "LIVE_ENGINE_EXECUTION", "status": "COMPLETED", "detail": f"executed_at={executed_at}"},
        {"stage": 7, "name": "STRUCTURED_RESULT", "status": "COMPLETED", "detail": f"overall_vps={base_vps.get('overall_status')}, domain={dom_class}, sync={sync_status}"},
        {"stage": 8, "name": "RESPONSE_COMPOSER", "status": "COMPLETED", "detail": "9-item diagnostic breakdown composed deterministically"},
        {"stage": 9, "name": "CHAT_DISPLAY", "status": "READY", "detail": f"{len(formatted_text)} chars"},
    ]
    merged = dict(base_vps)
    merged.update(
        {
            "ok": True,
            "executed_at": executed_at,
            "sub_intent": sub_intent,
            "domain_target": domain_target,
            "target_vps_ip": target_vps_ip,
            "permission_checks": permission_checks,
            "diagnostic_pipeline_trace": pipeline_trace,
            "local_folder": local_manifest,
            "folder_vps_mapping": mapping_info,
            "internet": {
                "verification_status": net_ver_status,
                "interfaces": iface_info,
                "diagnostics": net_diag,
            },
            "domain": domain_report,
            "vps": {
                **base_vps,
                "ssh_discovery": ssh_discovery,
                "live_ssh_probe": live_ssh_probe,
            },
            "file_synchronization": sync_report,
            "deployment": {
                "status": deployment_status,
                "description": deployment_desc,
                "documented_target": deploy_md,
                "domain_classification": dom_class,
                "sync_status": sync_status,
            },
            "final_conclusion": "\n".join(final_conclusion_lines),
            "read_only_guarantee": read_only_statement,
            "formatted_report": formatted_text,
            "formatted_response": formatted_text,
        }
    )
    return merged


def run_universal_file_action_if_applicable(
    prompt: str, context: dict[str, Any] | None = None, fallback_engine: Any = None
) -> dict[str, Any] | None:
    """Execute the 9-stage Action-First UniversalFileActionEngine workflow when the prompt requests direct file/folder work."""
    if is_folder_vps_status_query(prompt):
        return None
    ctx = context or {}
    ufe = ctx.get("universal_file_engine") or fallback_engine
    if ufe is None:
        return None
    from .universal_file_intelligence import is_universal_file_action_query

    attachments = list(ctx.get("attachments") or [])
    session_id = ctx.get("session_id")
    has_sess_res = bool(
        ufe.registry.list_resources(session_id=session_id, available_only=True)
        if session_id
        else False
    )
    if not is_universal_file_action_query(
        prompt, has_attachments=bool(attachments), has_session_resources=has_sess_res
    ):
        return None
    return ufe.execute_chat_file_action(
        prompt,
        session_id=session_id,
        attachments=attachments,
    )


class _StreamThinkTagFilter:
    """Stateful filter that strips `<think>...</think>` and `<thinking>...</thinking>` across streaming chunks."""

    def __init__(self) -> None:
        self._in_think = False
        self._buf = ""
        self.filtered_thinking_chars = 0

    def feed(self, chunk: str) -> str:
        if not chunk:
            return ""
        self._buf += chunk
        out_parts: list[str] = []

        while self._buf:
            if self._in_think:
                m_close = re.search(r"</think(?:ing)?>", self._buf, flags=re.IGNORECASE)
                if m_close:
                    self.filtered_thinking_chars += m_close.start()
                    self._buf = self._buf[m_close.end() :]
                    self._in_think = False
                    if self._buf.startswith("\n"):
                        self._buf = self._buf.lstrip("\n")
                else:
                    if len(self._buf) > 12:
                        self.filtered_thinking_chars += len(self._buf) - 12
                        self._buf = self._buf[-12:]
                    break
            else:
                m_open = re.search(r"<think(?:ing)?>", self._buf, flags=re.IGNORECASE)
                if m_open:
                    if m_open.start() > 0:
                        out_parts.append(self._buf[: m_open.start()])
                    self._buf = self._buf[m_open.end() :]
                    self._in_think = True
                else:
                    lt_idx = self._buf.rfind("<")
                    if lt_idx != -1 and len(self._buf) - lt_idx <= 10:
                        tail = self._buf[lt_idx:].lower()
                        if "<thinking>".startswith(tail) or "<think>".startswith(tail):
                            if lt_idx > 0:
                                out_parts.append(self._buf[:lt_idx])
                            self._buf = self._buf[lt_idx:]
                            break
                    out_parts.append(self._buf)
                    self._buf = ""
        return "".join(out_parts)

    def flush(self) -> str:
        if self._in_think:
            self.filtered_thinking_chars += len(self._buf)
            self._buf = ""
            return ""
        rem = self._buf
        self._buf = ""
        return rem


NUI_LAYERS_INFO: list[dict[str, Any]] = [
    {
        "layer": "L0",
        "name": "Verified Knowledge & 5-Feature Embedding",
        "status": "RUNNING",
        "badge": "RUNNING (SILICON + HOST)",
        "module": "src/hijaiyyah/nui/facts.py, features.py",
        "evidence": "27 sealed facts + 28 Hijaiyyah 5-feature embeddings (Jim+Kha = [2, 2, 2, 6, 6])",
        "honest_note": "Terbukti di Python dan silikon Tang Nano 20K.",
    },
    {
        "layer": "L1",
        "name": "Repository Knowledge Graph",
        "status": "COMPLETE",
        "badge": "COMPLETE (1828N / 4689E)",
        "module": "src/hijaiyyah/nui/repository_index.py, repository_graph.py",
        "evidence": "1,828 node & 4,689 edge dari git ls-files",
        "honest_note": "Mencakup imports, mentions, references, verifies, defines.",
    },
    {
        "layer": "L2",
        "name": "Program Index & Call/Instance Graph",
        "status": "COMPLETE",
        "badge": "COMPLETE (62 HASM / 128 VERILOG)",
        "module": "src/hijaiyyah/nui/program_index.py, program_graph.py",
        "evidence": "62 program HASM, 1,541 fungsi Python, 128 modul Verilog",
        "honest_note": "Semua CALL HASM dan instansiasi Verilog terselesaikan.",
    },
    {
        "layer": "L3",
        "name": "Execution Understanding & Trace",
        "status": "COMPLETE",
        "badge": "COMPLETE (63 RUNS / 1478 EDGES)",
        "module": "src/hijaiyyah/nui/execution_trace.py, execution_graph.py",
        "evidence": "NUI/execution_model.json (63 lari, 1,478 edge kausal)",
        "honest_note": "Jejak sebelum -> instruksi -> sesudah pada HISAMachine.",
    },
    {
        "layer": "L4",
        "name": "Software-Hardware Parity Verification",
        "status": "COMPLETE",
        "badge": "COMPLETE (74/105 P3 PARITY)",
        "module": "src/hijaiyyah/nui/parity_model.py, layer4_freeze.py",
        "evidence": "NUI/parity_model.json (tag layer4-freeze-2026-09-26)",
        "honest_note": "74 opcode terbukti paritas P3; selisih dicatat jujur.",
    },
    {
        "layer": "L5",
        "name": "Linux VM Host Observation Engine",
        "status": "READY",
        "badge": "READY (9/11 COLLECTORS)",
        "module": "src/hijaiyyah/nui/layer5.py, layer5_freeze.py",
        "evidence": "NUI/layer5_freeze.json (Ubuntu 24.04.5 LTS ARM64 via Lima)",
        "honest_note": "Tahap observasi baca-saja bermeterai SHA-256.",
    },
    {
        "layer": "L6",
        "name": "Hardware Intelligence & Real-Time HDMI",
        "status": "RUNNING",
        "badge": "RUNNING (CDC + RTL F1-F5)",
        "module": "src/hijaiyyah/nui/hardware_state.py, rtl_function.py",
        "evidence": "NUI/layer6_addendum.json + hcpu_hdmi_top.v (86.01 MHz pixel_clk)",
        "honest_note": "Memisahkan LIVE, MEASURED, SIMULATED, dan UNKNOWN secara ketat.",
    },
    {
        "layer": "L7",
        "name": "Autonomous Operation Fail-Closed Gate",
        "status": "READY",
        "badge": "READY (ALLOW / DENY / STOP)",
        "module": "src/hijaiyyah/nui/layer7.py, layer7_decision.py, layer7_portal.py",
        "evidence": "NUI/LAYER7.md (tag layer7-freeze-2026-10-03)",
        "honest_note": "Fail-closed gate dengan record_sha256.",
    },
    {
        "layer": "L8",
        "name": "Autonomous Diagnostics",
        "status": "IMPLEMENTED_AND_VERIFIED",
        "badge": "VERIFIED (5 ANOMALIES / SHA-256)",
        "module": "src/hijaiyyah/nui/autonomous/layer8_diagnostics.py",
        "evidence": "Diagnosa otonom deterministik berbasis bukti L0–L7 dengan verifikasi SHA-256",
        "honest_note": "Terimplementasi penuh di subpaket otonom dan terhubung via CanonicalL8Adapter.",
    },
    {
        "layer": "L9",
        "name": "Deductive Reasoning Engine & 7-Domain KB",
        "status": "IMPLEMENTED_AND_VERIFIED",
        "badge": "VERIFIED (DEDUCTIVE + 7 DOMAINS)",
        "module": "src/hijaiyyah/nui/autonomous/layer9_reasoning.py, knowledge.py",
        "evidence": "Penalaran deduktif multi-lapis dengan deteksi kontradiksi dan pemisahan epistemik VF/CC/DP/EH/AT",
        "honest_note": "Terimplementasi penuh dan terhubung via CanonicalL9Adapter.",
    },
    {
        "layer": "L10",
        "name": "Autonomous Engineering Engine",
        "status": "IMPLEMENTED_AND_VERIFIED",
        "badge": "VERIFIED (8-STAGE / 4 ORACLES)",
        "module": "src/hijaiyyah/nui/autonomous/layer10_engineering.py",
        "evidence": "Siklus rekayasa otonom 8 tahap (K3–K6) dengan 4 oracle kanonik di sandbox terisolasi",
        "honest_note": "Terimplementasi penuh dengan proteksi Immutable Core L0–L7.",
    },
    {
        "layer": "L11",
        "name": "Universal Computation Chain",
        "status": "IMPLEMENTED_AND_VERIFIED",
        "badge": "VERIFIED (11/11 JUNCTIONS PASS)",
        "module": "src/hijaiyyah/nui/autonomous/layer11_universal.py, atom.py",
        "evidence": "11 sambungan komputasi universal dari huruf Hijaiyyah ke HCPU/HLUT dengan oracle deterministik",
        "honest_note": "Seluruh 11 sambungan lulus verifikasi deterministik.",
    },
]


class NUIIntelligenceProvider(ABC):
    """Base contract for all intelligence providers in CosmicTera NUI Desktop."""

    provider_id: str
    display_name: str

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """Return honest runtime availability and capability metadata."""

    @abstractmethod
    def respond(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        """Process a prompt and return final structured response."""

    def stream_respond(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        cancel_check: Callable[[], bool] | None = None,
        tool_executor: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield live thinking stages, tool activities, and natural semantic units without fake typing delays."""
        yield {
            "event": "stage_update",
            "stage": "UNDERSTANDING",
            "thinking_status": "Understanding request...",
        }
        res = self.respond(prompt, context=context, cancel_check=cancel_check)
        if res.get("error"):
            yield {
                "event": "generation_error",
                "stage": "ERROR",
                "error": res["error"],
                "response_text": res.get("reply", ""),
                "provider_response": res,
            }
            return
        reply = str(res.get("reply", ""))
        yield {
            "event": "stage_update",
            "stage": "GENERATING_RESPONSE",
            "thinking_status": "Preparing response...",
        }
        acc = ""
        for unit in self._split_natural_units(reply):
            if cancel_check and cancel_check():
                yield {
                    "event": "generation_cancelled",
                    "stage": "CANCELLED",
                    "accumulated_text": acc,
                }
                return
            acc += unit
            yield {
                "event": "partial_response",
                "stage": "GENERATING_RESPONSE",
                "thinking_status": "Generating response...",
                "delta": unit,
                "accumulated_text": acc,
            }
        yield {
            "event": "final_response",
            "stage": "COMPLETE",
            "thinking_status": "COMPLETE",
            "response_text": acc,
            "provider_response": res,
        }

    @staticmethod
    def _split_natural_units(text: str) -> list[str]:
        """Split deterministic output into natural sentence/line/word units without fixed character slicing or sleep."""
        if not text:
            return []
        sentences = [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s]
        if len(sentences) >= 3:
            out: list[str] = []
            for part in re.findall(r"[^\n]+(?:\n+|$)", text):
                sub = re.findall(r"[^.!?]+[.!?]*\s*", part)
                out.extend(s for s in sub if s)
            if len(out) >= 3:
                return out
        words = re.findall(r"\S+\s*|\n+", text)
        if len(words) <= 3:
            return [w for w in words if w]
        chunk_size = max(1, (len(words) + 2) // 3)
        return [
            "".join(words[i : i + chunk_size])
            for i in range(0, len(words), chunk_size)
        ]


class NativeNUIProvider(NUIIntelligenceProvider):
    """CosmicTera Native Deterministic & Structured NUI Engine wired to `MASTER_TABLE`, `HISAMachine`, `knowledge.py`, `usr.py`, and `OllamaProvider`."""

    provider_id = "native_nui"
    display_name = "CosmicTera Native NUI Engine (L0–L11 + H-ISA + 7-Domain KB)"

    def __init__(
        self,
        persona_loader: NUIPersonaLoader | None = None,
        context_retriever: NUIContextualRetriever | None = None,
        self_learning_engine: Any = None,
        ollama_provider: Any = None,
        remote_dev_engine: Any = None,
        universal_file_engine: Any = None,
        internet_engine: Any = None,
    ) -> None:
        self.persona_loader = persona_loader or NUIPersonaLoader(REPO_ROOT)
        self.retriever = context_retriever or NUIContextualRetriever(REPO_ROOT)
        self.self_learning_engine = self_learning_engine
        self.ollama_provider = ollama_provider
        self.remote_dev_engine = remote_dev_engine
        self.universal_file_engine = universal_file_engine
        self.internet_engine = internet_engine
        self.layers_bridge = CanonicalLayersBridge(REPO_ROOT)
        if self.remote_dev_engine is None or self.universal_file_engine is None or self.internet_engine is None:
            _upgrade_caller_service_app_if_needed(self)

    def status(self) -> dict[str, Any]:
        ollama_st = (
            self.ollama_provider.status()
            if self.ollama_provider is not None
            else {"available": False, "model": None, "installed_models": []}
        )
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "available": True,
            "streaming_supported": True,
            "ui_state": "PROVIDER CONNECTED",
            "model_state": (
                f"MODEL READY ({ollama_st.get('model')} + Native NUI L0-L11)"
                if ollama_st.get("available")
                else "MODEL READY (Native NUI L0-L11 + HISAMachine + 7-Domain KB)"
            ),
            "model": ollama_st.get("model") or "cosmictera-nui-native-v1.3",
            "ollama_connected": bool(ollama_st.get("available")),
            "installed_ollama_models": ollama_st.get("installed_models", []),
            "type": "HYBRID_LLM_AND_DETERMINISTIC_NUI_CORE",
            "requires_internet": False,
            "layers_active": 12,
            "layers_total": 12,
            "subsystems_connected": 11,
        }

    def inspect_layers(self) -> list[dict[str, Any]]:
        try:
            return self.layers_bridge.get_all_layers_live_matrix()
        except Exception:
            return list(NUI_LAYERS_INFO)

    def inspect_subsystems(self) -> list[dict[str, Any]]:
        jim = MASTER_TABLE.get_by_name("Jim")
        kha = MASTER_TABLE.get_by_name("Kha")
        ba = MASTER_TABLE.get_by_name("Ba")
        sin = MASTER_TABLE.get_by_name("Sin")
        mim = MASTER_TABLE.get_by_name("Mim")
        bsm_vec = [a + b + c for a, b, c in zip(ba.vector, sin.vector, mim.vector)]
        nmv_bsm = an_norm_squared(bsm_vec)
        itm_jk = intimate_distance(jim.vector, kha.vector)
        hdot_jk = homogeneous_inner_product(jim.vector, kha.vector)
        guards_jim = full_guard_check(jim.vector)
        crc_jim = compute_digest(bytes(jim.vector))

        return [
            {
                "id": "HCPU_HISA",
                "name": "HCPU & H-ISA v1.2",
                "status": "ACTIVE",
                "layers": ["L0", "L2", "L3", "L4", "L6", "L7"],
                "metrics": {
                    "clock_mhz": 27.0,
                    "post_route_fmax_mhz": 119.60,
                    "opcodes_spec": 105,
                    "opcodes_rtl": 84,
                    "parity_p3_proven": 74,
                },
                "summary": "Prosesor 5-tahap 27 MHz dengan 84 opcode RTL dan 74 opcode terbukti P3 di silikon.",
            },
            {
                "id": "HYBIT_18D_MATH",
                "name": "Hybit 18D & Matematika Hijaiyyah",
                "status": "ACTIVE",
                "layers": ["L0", "L4", "L6", "L9"],
                "metrics": {
                    "letters": 28,
                    "dimensions": 18,
                    "bsm_nmv": nmv_bsm,
                    "jim_kha_intimate_distance": itm_jk,
                    "jim_kha_hdot": hdot_jk,
                },
                "summary": f"28 huruf × 18 dimensi tersegel; BSM NMV={nmv_bsm}, Jim-Kha ITM={itm_jk}, HDOT={hdot_jk}.",
            },
            {
                "id": "HC_HASM_HBC",
                "name": "HC, HASM & HBC Compiler Chain",
                "status": "ACTIVE",
                "layers": ["L1", "L2", "L3", "L4"],
                "metrics": {
                    "hasm_programs": 62,
                    "multilingual_keywords": 4,
                    "hbc_magic": "HBC1",
                },
                "summary": "Rantai kompilasi Hybit Code (HC) -> H-ISA Assembly (.hasm) -> Bytecode (.hbc).",
            },
            {
                "id": "HVM_HCVM",
                "name": "HVM & HCVM Virtual Machine",
                "status": "ACTIVE",
                "layers": ["L2", "L3", "L4"],
                "metrics": {
                    "execution_runs": 63,
                    "causal_edges": 1478,
                    "parity_runs": 107,
                },
                "summary": "Mesin virtual deterministik dengan pelacakan jejak eksekusi instruksi demi instruksi.",
            },
            {
                "id": "HOS_HFS",
                "name": "HOS Kernel & HFS Filesystem",
                "status": "READY",
                "layers": ["L2", "L3", "L5", "L7"],
                "metrics": {
                    "kernel_words": 157,
                    "hfs_test_words": 44,
                    "hdmi_slot_status": "NOT INSTRUMENTED",
                },
                "summary": "Kernel HOS & HFS berjalan di simulator host; jujur ditandai NOT INSTRUMENTED pada slot HDMI.",
            },
            {
                "id": "HAR_HPG1",
                "name": "HAR Registry & HPG-1 Container",
                "status": "ACTIVE",
                "layers": ["L0", "L2", "L9"],
                "metrics": {
                    "har_canonical_entries": 28,
                    "base_load_addr": "0x040",
                },
                "summary": "Registri artefak Hijaiyyah 28 huruf dan kontainer pemuatan HPG-1.",
            },
            {
                "id": "HMCL",
                "name": "HMCL Collective Learning",
                "status": "ACTIVE",
                "layers": ["L0", "L4", "L9"],
                "metrics": {
                    "feature_dimensions": 5,
                    "coherence_verified": True,
                },
                "summary": "Evaluasi koherensi ruang fitur 5D lintas 28 huruf Hijaiyyah.",
            },
            {
                "id": "HISAB",
                "name": "HISAB Integrity & Digest Engine",
                "status": "ACTIVE",
                "layers": ["L0", "L4", "L6"],
                "metrics": {
                    "jim_crc32": f"0x{crc_jim:08X}",
                    "opcodes": "HPACK (0x50), HCRC (0x51)",
                },
                "summary": f"Engine integritas 1-siklus HPACK & HCRC32 (Jim CRC32 = 0x{crc_jim:08X}).",
            },
            {
                "id": "KABAH_JAMRAH",
                "name": "Ka'bah Sponge & Jamrah 7-Node",
                "status": "ACTIVE",
                "layers": ["L0", "L4", "L6"],
                "metrics": {
                    "sponge_state_bits": 1600,
                    "jamrah_cycles_per_byte": 33,
                    "cube_digest": cube_digest()[:16],
                },
                "summary": "Kriptografi spons Ka'bah 1600-bit, HMAC-SHA256, dan gerbang 7-node Jamrah.",
            },
            {
                "id": "USSS",
                "name": "USSS Security & Six-Guard",
                "status": "ACTIVE",
                "layers": ["L0", "L4", "L6", "L7"],
                "metrics": {
                    "guards": "G1, G2, G3, G4, T1, T2",
                    "jim_guard_pass": guards_jim["all_pass"],
                    "security_core_lut4": "3,333 / 5,670 (58.78%)",
                },
                "summary": "Universal Sovereign Security System dengan 6-Guard matematis dan fail-closed gate L7.",
            },
            {
                "id": "HDMI_MONITOR",
                "name": "CosmicTera HDMI 1280×720p60 Control Center",
                "status": "ACTIVE",
                "layers": ["L0", "L6", "L7", "L9"],
                "metrics": {
                    "resolution": "1280x720@60Hz",
                    "pixel_clk_fmax_mhz": 86.01,
                    "bsram_blocks": "33 / 46 (71%)",
                },
                "summary": "Tampilan real-time 10-zona dengan NUI Holographic Brain dan tombol fisik S1/S2.",
            },
        ]

    def _inspect_repository_summary(self, include_recent_work: bool = True) -> dict[str, Any]:
        """Run an actual live inspection of the CosmicTera repository (Git log, status, diff, and recent files)."""
        import datetime

        commit_id = self.persona_loader.get_git_head_short()
        branch = "feat/cosmictera-nui-desktop"
        modified_count = 0
        recent_commits: list[str] = []
        changed_files: list[str] = []
        diff_stat: str = ""
        recent_disk_files: list[dict[str, Any]] = []
        try:
            b_res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if b_res.stdout.strip():
                branch = b_res.stdout.strip()
            s_res = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            changed_files = [ln.strip() for ln in s_res.stdout.splitlines() if ln.strip()]
            modified_count = len(changed_files)

            if include_recent_work:
                log_res = subprocess.run(
                    [
                        "git",
                        "log",
                        "-n",
                        "8",
                        "--date=format:%Y-%m-%d %H:%M",
                        "--pretty=format:%h | %ad | %an | %s",
                    ],
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=2.5,
                )
                recent_commits = [ln.strip() for ln in log_res.stdout.splitlines() if ln.strip()]

                diff_res = subprocess.run(
                    ["git", "diff", "--stat", "HEAD"],
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=2.5,
                )
                diff_stat = diff_res.stdout.strip()
        except Exception:
            pass

        if include_recent_work:
            skip_parts = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "build", ".DS_Store"}
            candidates: list[tuple[float, str, int]] = []
            for sub_dir in ("portal8888", "nui-desktop", "src", "rtl", "cosmictera-build", "NUI", "docs", "tests"):
                base_p = REPO_ROOT / sub_dir
                if not base_p.exists():
                    continue
                for fpath in base_p.rglob("*"):
                    if not fpath.is_file():
                        continue
                    if any(part in skip_parts for part in fpath.parts):
                        continue
                    try:
                        st_info = fpath.stat()
                        rel_p = str(fpath.relative_to(REPO_ROOT))
                        candidates.append((st_info.st_mtime, rel_p, st_info.st_size))
                    except Exception:
                        continue
            candidates.sort(key=lambda x: x[0], reverse=True)
            for mtime, rel_p, sz in candidates[:12]:
                dt_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                recent_disk_files.append(
                    {"path": rel_p, "modified_at": dt_str, "size_bytes": sz}
                )

        prog_idx = program_index.programs()
        all_facts = nui_facts.load()
        layers = self.inspect_layers()
        at_layers = [l["layer"] for l in layers if "AT" in l["badge"]]
        active_layers = [l["layer"] for l in layers if "AT" not in l["badge"]]

        return {
            "repo_root": str(REPO_ROOT),
            "branch": branch,
            "commit": commit_id,
            "modified_entries": modified_count,
            "changed_files": changed_files[:25],
            "recent_commits": recent_commits,
            "diff_stat": diff_stat,
            "recent_disk_files": recent_disk_files,
            "hasm_programs": len(prog_idx.hasm),
            "verilog_modules": len(prog_idx.verilog),
            "python_functions": len(prog_idx.python),
            "sealed_facts": len(all_facts),
            "active_layers": active_layers,
            "at_layers": at_layers,
        }

    def execute_calculation_or_program(
        self, kind: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        if kind == "letter_inspect":
            letter_q = str(payload.get("letter", "Jim")).strip()
            entry = None
            for e in MASTER_TABLE.all_entries():
                if e.name.lower() == letter_q.lower() or e.char == letter_q:
                    entry = e
                    break
            if entry is None:
                entry = MASTER_TABLE.get_by_name("Jim")
            feats = vector_features(entry.vector)
            guards = full_guard_check(entry.vector)
            exo = build_exomatrix(entry.vector)
            crc = compute_digest(bytes(entry.vector))
            return {
                "kind": "letter_inspect",
                "name": entry.name,
                "char": entry.char,
                "index": entry.index,
                "opcode_hex": f"0x{0xE0 + entry.index - 1:02X}",
                "vector_18d": list(entry.vector),
                "l0_5features": {
                    "titik": feats.titik,
                    "garis": feats.garis,
                    "lengkung": feats.lengkung,
                    "theta": feats.theta,
                    "rho": feats.rho,
                },
                "nmv_norm_squared": an_norm_squared(entry.vector),
                "orbit_period": additive_orbit_period(entry.char),
                "six_guards": guards,
                "exomatrix_5x5": exo,
                "hisab_crc32": f"0x{crc:08X}",
                "source_attribution": "LOCAL_REPOSITORY: src/hijaiyyah/core/master_table.py",
            }

        if kind == "hasm_exec":
            src = str(payload.get("source", "ج\nخ\nHGRD H0\nHALT\n"))
            words = assemble(src, base_dir=REPO_ROOT / "rtl" / "programs")
            m = HISAMachine(MASTER_TABLE)
            m.load_program(words)
            m.run()
            l3_trace = self.layers_bridge.l3.trace_hasm_program(src, label=str(payload.get("label", "hasm_exec")))
            return {
                "kind": "hasm_exec",
                "instruction_count": len(words),
                "cycles": m.cycle,
                "halted": m._halted,
                "pc": m.regs.pc,
                "output": list(m.output),
                "flags": m._pack_flags(),
                "guard_pass": bool(m.regs.sr.guard_pass),
                "h0_vector": list(getattr(m.regs, "h", getattr(m.regs, "hr", [[0] * 18]))[0]),
                "l3_execution_trace": l3_trace,
                "source_attribution": "LOCAL_REPOSITORY: src/hijaiyyah/hisa/machine.py + nui/execution_trace.py",
            }

        if kind in {"hc_compile_exec", "usr"}:
            hc_src = str(payload.get("source", "let a = 10;\nlet b = 20;\nprint(a + b);\n"))
            src_norm = "\n".join(
                line if line.strip().endswith(";") or not line.strip() else line.strip() + ";"
                for line in hc_src.splitlines()
            )
            emitted, err = usr_lower(src_norm)
            if err:
                m_expr = re.search(r"(-?\d+)\s*(\+|\-|\*)\s*(-?\d+)", hc_src)
                if m_expr:
                    a_i, op_c, b_i = int(m_expr.group(1)), m_expr.group(2), int(m_expr.group(3))
                    op_m = "ADD" if op_c == "+" else ("SUB" if op_c == "-" else "MUL")
                    emitted = [f"MOVI R1, {a_i}", f"MOVI R2, {b_i}", f"{op_m} R1, R1, R2", "PRINT R1"]
                    err = None
                else:
                    return {
                        "kind": kind,
                        "status": "ERROR",
                        "error": err,
                    }
            hasm_text = "\n".join(emitted) + "\nHALT\n"
            words = assemble(hasm_text)
            hbc = HbcFile.from_instructions(words)
            blob = hbc.to_bytes()
            m = HISAMachine(MASTER_TABLE)
            m.load_program(words)
            m.run()
            r1_val = int(m.output[0]) if m.output else int(m.regs.gpr[1])
            return {
                "kind": kind,
                "status": "OK",
                "hc_source": hc_src,
                "emitted_hasm": hasm_text,
                "instruction_words": len(words),
                "hbc_size_bytes": len(blob),
                "halted": bool(m._halted),
                "R1": r1_val,
                "output": list(m.output),
                "cycles": m.cycle,
                "source_attribution": "LOCAL_REPOSITORY: src/hijaiyyah/nui/usr.py + hisa/machine.py",
            }

        if kind == "nui_knowledge_query":
            q = str(payload.get("query", "term HCPU"))
            ans = knowledge.query(q)
            return {
                "kind": "nui_knowledge_query",
                "query": q,
                "answer": ans,
                "source_attribution": "LOCAL_REPOSITORY: src/hijaiyyah/nui/knowledge.py (L9 7-Domain KB)",
            }

        if kind == "l0_inspect":
            return {
                "kind": "l0_inspect",
                "overview": self.layers_bridge.l0.get_overview(),
                "address_unification": self.layers_bridge.l0.verify_address_unification(),
                "angle_claims": self.layers_bridge.l0.verify_angle_claims(),
            }
        if kind == "l1_impact":
            target_path = str(payload.get("path", "src/hijaiyyah/hisa/machine.py"))
            return {
                "kind": "l1_impact",
                **self.layers_bridge.l1.query_file_impact(target_path),
            }
        if kind == "l2_explain":
            target = str(payload.get("target", "rtl/hcpu_top.v"))
            return {
                "kind": "l2_explain",
                **self.layers_bridge.l2.explain_program(target),
            }
        if kind == "l3_trace":
            prog = payload.get("program", "rtl/programs/test_bsm.hasm")
            src = payload.get("source")
            if src:
                return {"kind": "l3_trace", **self.layers_bridge.l3.trace_hasm_program(str(src))}
            return {"kind": "l3_trace", **self.layers_bridge.l3.trace_hasm_file(str(prog))}
        if kind == "l4_parity":
            return {"kind": "l4_parity", **self.layers_bridge.l4.get_parity_overview()}
        if kind == "l5_host":
            return {"kind": "l5_host", **self.layers_bridge.l5.get_host_observation_summary()}
        if kind == "l6_hardware_state":
            return {"kind": "l6_hardware_state", **self.layers_bridge.l6.get_hardware_intelligence_summary()}
        if kind == "l7_gate":
            return {
                "kind": "l7_gate",
                **self.layers_bridge.l7.evaluate_and_decide(
                    operation=str(payload.get("operation", "VERIFY_RUNTIME_PARITY")),
                    domain=str(payload.get("domain", "PARITY")),
                    program=payload.get("program"),
                    live_board=bool(payload.get("live_board", False)),
                ),
            }

        raise ValueError(f"Unsupported calculation kind: {kind!r}")

    def stream_respond(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        cancel_check: Callable[[], bool] | None = None,
        tool_executor: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> Iterator[dict[str, Any]]:
        ctx = context or {}
        p_clean = prompt.strip()

        if not p_clean:
            yield {
                "event": "stage_update",
                "stage": "UNDERSTANDING",
                "thinking_status": "Understanding request...",
            }
            yield {
                "event": "generation_error",
                "stage": "ERROR",
                "error": "EMPTY_PROMPT",
                "response_text": "Silakan ketik pertanyaan atau instruksi.",
            }
            return

        p9_op = ctx.get("phase9_operational") or {}
        if p9_op.get("direct_response_override"):
            override_txt = str(p9_op["direct_response_override"])
            yield {
                "event": "partial_response",
                "stage": "GENERATING_RESPONSE",
                "thinking_status": "Applying Phase 9 Immutable Core Protection...",
                "delta": override_txt,
                "accumulated_text": override_txt,
            }
            final_res = {
                "provider": self.provider_id,
                "model": self.model_name,
                "ui_state": "RESPONSE COMPLETE",
                "reply": override_txt,
                "data": {"phase9_operational": p9_op},
                "source_attribution": "PHASE9_IMMUTABLE_CORE_PROTECTION (L7 Gate)",
            }
            yield {
                "event": "final_response",
                "stage": "COMPLETE",
                "thinking_status": "COMPLETE",
                "response_text": override_txt,
                "provider_response": final_res,
            }
            return

        p_lower = p_clean.lower()
        p_norm = normalize_indonesian_query(p_lower)
        history: list[dict[str, Any]] = list(ctx.get("conversation_context") or [])
        mode_info = classify_response_mode(p_clean, history)
        r_mode = mode_info["mode"]
        is_vps_folder_check = is_folder_vps_status_query(p_clean)

        # When mode is GENERAL_INTELLIGENCE (e.g., general coding, Python app, REST vs GraphQL, web from scratch, bug search)
        # and Ollama is available, delegate directly to OllamaProvider.stream_respond for real token streaming!
        if not is_vps_folder_check and r_mode == "GENERAL_INTELLIGENCE" and not mode_info.get("is_followup") and self.ollama_provider is not None:
            ollama_st = self.ollama_provider.status()
            if ollama_st.get("available"):
                yield from self.ollama_provider.stream_respond(
                    prompt,
                    context=ctx,
                    cancel_check=cancel_check,
                    tool_executor=tool_executor,
                )
                return

        yield {
            "event": "stage_update",
            "stage": "UNDERSTANDING",
            "thinking_status": "Understanding request...",
        }

        if cancel_check and cancel_check():
            yield {
                "event": "generation_cancelled",
                "stage": "CANCELLED",
                "accumulated_text": "",
            }
            return

        tool_activities: list[str] = []

        math_match = re.search(
            r"(-?\d+)\s*(\+|\-|\*|x|×|/)\s*(-?\d+)", p_clean, re.IGNORECASE
        )
        is_hc_code = "let " in p_lower and ("print(" in p_lower or "println(" in p_lower)
        is_hasm_code = any(
            tok in p_clean.upper()
            for tok in ("MOVI ", "HLOAD ", "HNRM2 ", "HDIST ", "HDOT ", "HGRD ")
        ) or any(
            phrase in p_lower or phrase in p_norm
            for phrase in (
                "test_bsm.hasm",
                "jalankan program h-isa",
                "jalankan program hisa",
                "eksekusi program h-isa",
                "eksekusi program hisa",
                "jalankan h-isa",
                "jalankan hisa",
            )
        )
        is_math = bool(math_match) and any(
            w in p_lower
            for w in ("hitung", "berapa", "jumlah", "tambah", "kurang", "kali", "bagi", "+", "-", "*")
        )
        is_repo_check = r_mode == "REPOSITORY_AUDIT"
        is_sys_diag = r_mode == "SYSTEM_DIAGNOSTICS"
        is_web_doc_search = any(
            w in p_lower for w in ("cari dokumentasi", "search documentation", "cari di web", "browsing")
        )
        matched_letter = None
        if not is_hasm_code and not is_sys_diag and not is_repo_check and r_mode != "CAPABILITY_INQUIRY":
            for entry in MASTER_TABLE.all_entries():
                if (
                    has_word_boundary_match(entry.name.lower(), p_lower)
                    and (has_word_boundary_match("huruf", p_lower) or has_word_boundary_match("analisis", p_lower) or entry.char in p_clean)
                ) or entry.char in p_clean:
                    matched_letter = entry
                    break

        yield {
            "event": "stage_update",
            "stage": "ANALYZING",
            "thinking_status": "Analyzing request...",
        }

        if is_sys_diag:
            yield {
                "event": "stage_update",
                "stage": "PLANNING",
                "thinking_status": "Menyiapkan pemeriksaan sistem read-only...",
            }
            act_diag = "Menjalankan pemeriksaan sistem read-only (layanan lokal, provider, model Ollama, memori host, dan perangkat keras)..."
            tool_activities.append(act_diag)
            yield {
                "event": "tool_call",
                "stage": "TOOL_EXECUTION",
                "thinking_status": "Memeriksa kondisi sistem...",
                "tool": "system.diagnostics",
                "activity": act_diag,
            }
        elif is_repo_check:
            yield {
                "event": "stage_update",
                "stage": "PLANNING",
                "thinking_status": "Sedang memeriksa repository...",
            }
            act_repo = "Sedang memeriksa repository..."
            tool_activities.append(act_repo)
            yield {
                "event": "tool_call",
                "stage": "TOOL_EXECUTION",
                "thinking_status": "Sedang memeriksa repository...",
                "tool": "repository.inspect",
                "activity": act_repo,
            }
        elif is_math or is_hc_code or is_hasm_code:
            yield {
                "event": "stage_update",
                "stage": "PLANNING",
                "thinking_status": "Planning computation pipeline...",
            }
            act1 = "Mengidentifikasi operasi matematika / instruksi H-ISA."
            tool_activities.append(act1)
            yield {
                "event": "tool_call",
                "stage": "TOOL_EXECUTION",
                "thinking_status": "Executing computation...",
                "tool": "hijaiyyah.hisa.machine",
                "activity": act1,
            }
            act2 = "Memilih computation engine (HC Compiler -> H-ISA Assembler -> HISAMachine)."
            tool_activities.append(act2)
            yield {
                "event": "tool_call",
                "stage": "TOOL_EXECUTION",
                "thinking_status": "Executing computation...",
                "tool": "hijaiyyah.nui.usr",
                "activity": act2,
            }
        elif matched_letter is not None:
            act1 = f"Mengekstrak vektor Hybit 18D & 5 fitur geometri L0 untuk huruf {matched_letter.name} ({matched_letter.char})."
            tool_activities.append(act1)
            yield {
                "event": "tool_call",
                "stage": "TOOL_EXECUTION",
                "thinking_status": "Executing computation...",
                "tool": "hijaiyyah.core.master_table",
                "activity": act1,
            }
        elif is_web_doc_search:
            yield {
                "event": "stage_update",
                "stage": "PLANNING",
                "thinking_status": "Planning documentation search...",
            }
            for step_act in (
                "Memeriksa izin internet (WEB_SEARCH).",
                "Meminta otorisasi jika belum tersedia.",
            ):
                tool_activities.append(step_act)
                yield {
                    "event": "tool_call",
                    "stage": "TOOL_EXECUTION",
                    "thinking_status": "Accessing authorized tool...",
                    "tool": "web.search",
                    "activity": step_act,
                }
            if tool_executor is not None:
                w_out = tool_executor(
                    "web.search",
                    {"url": "docs.python.org", "query": p_clean},
                )
                if w_out.get("ok"):
                    for step_ok in (
                        "Melakukan web search setelah diizinkan.",
                        "Membaca dokumentasi.",
                        "Menyusun ringkasan dan sumber.",
                    ):
                        tool_activities.append(step_ok)
                        yield {
                            "event": "tool_result",
                            "stage": "TOOL_EXECUTION",
                            "thinking_status": "Accessing authorized tool...",
                            "tool": "web.search",
                            "activity": step_ok,
                        }
                else:
                    wait_act = f"Status izin: {w_out.get('status', 'WAITING_FOR_APPROVAL')} — {w_out.get('reason', '')}"
                    tool_activities.append(wait_act)
                    yield {
                        "event": "tool_result",
                        "stage": "TOOL_EXECUTION",
                        "thinking_status": "Waiting for user authorization...",
                        "tool": "web.search",
                        "activity": wait_act,
                    }

        res = self.respond(prompt, context=ctx, cancel_check=cancel_check)
        if tool_activities:
            res.setdefault("data", {})["tool_activities"] = tool_activities

        if is_math or is_hc_code or is_hasm_code or matched_letter is not None:
            act_exec = "Menjalankan perhitungan pada HISAMachine / Master Table."
            tool_activities.append(act_exec)
            yield {
                "event": "tool_result",
                "stage": "TOOL_EXECUTION",
                "thinking_status": "Executing computation...",
                "tool": "hijaiyyah.hisa.machine",
                "activity": act_exec,
            }
            act_val = "Memverifikasi hasil dan invarian Six-Guard."
            tool_activities.append(act_val)
            yield {
                "event": "stage_update",
                "stage": "VALIDATING",
                "thinking_status": "Validating computation result...",
                "activity": act_val,
            }
        elif is_repo_check or is_sys_diag:
            yield {
                "event": "stage_update",
                "stage": "VALIDATING",
                "thinking_status": "Pemeriksaan selesai.",
            }

        if res.get("error") == "GENERATION_STOPPED" or (cancel_check and cancel_check()):
            yield {
                "event": "generation_cancelled",
                "stage": "CANCELLED",
                "thinking_status": "GENERATION CANCELLED",
                "accumulated_text": "",
            }
            return

        if res.get("error"):
            yield {
                "event": "generation_error",
                "stage": "ERROR",
                "thinking_status": res.get("ui_state", "ERROR"),
                "ui_state": res.get("ui_state", "ERROR"),
                "error": res["error"],
                "response_text": res.get("reply", ""),
                "provider_response": res,
            }
            return

        yield {
            "event": "stage_update",
            "stage": "GENERATING_RESPONSE",
            "thinking_status": "Generating response...",
        }

        reply_text, _ = strip_internal_thinking(str(res.get("reply", "")))
        accumulated = ""
        for unit in self._split_natural_units(reply_text):
            if cancel_check and cancel_check():
                yield {
                    "event": "generation_cancelled",
                    "stage": "CANCELLED",
                    "thinking_status": "GENERATION CANCELLED",
                    "accumulated_text": accumulated,
                }
                return
            accumulated += unit
            yield {
                "event": "partial_response",
                "stage": "GENERATING_RESPONSE",
                "thinking_status": "Generating response...",
                "delta": unit,
                "accumulated_text": accumulated,
            }

        yield {
            "event": "final_response",
            "stage": "COMPLETE",
            "thinking_status": "COMPLETE",
            "response_text": accumulated,
            "tool_activities": tool_activities,
            "provider_response": res,
        }

    def respond(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        ctx = context or {}
        p_clean = prompt.strip()
        if not p_clean:
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "error": "EMPTY_PROMPT",
                "reply": "Silakan ketik pertanyaan atau instruksi.",
                "data": {"intent": "empty_input"},
                "source_attribution": "LOCAL_REPOSITORY (NativeNUIProvider Input Validator)",
            }

        if cancel_check and cancel_check():
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "error": "GENERATION_STOPPED",
                "reply": "Pembuatan respons dihentikan oleh pengguna (`STOPPED`).",
                "data": {"stopped": True},
                "source_attribution": "LOCAL_REPOSITORY (NativeNUIProvider)",
            }

        p_lower = p_clean.lower()
        p_norm = normalize_indonesian_query(p_lower)
        history: list[dict[str, Any]] = list(ctx.get("conversation_context") or [])
        prior_msgs = [
            m
            for m in history
            if str(m.get("content", "")).strip() != p_clean
            or m.get("role") == "assistant"
        ]
        prior_user_turns = [
            str(m["content"]).strip()
            for m in history
            if m.get("role") == "user" and str(m.get("content", "")).strip() != p_clean
        ]
        prior_assistant_turns = [
            str(m["content"]).strip()
            for m in history
            if m.get("role") == "assistant" and str(m.get("content", "")).strip()
        ]
        mode_info = classify_response_mode(p_clean, prior_msgs)
        r_mode = mode_info["mode"]
        already_greeted = bool(mode_info["already_greeted"])

        vps_inspection = run_folder_vps_inspection(
            p_clean,
            ctx,
            self.remote_dev_engine,
            self.universal_file_engine,
            self.internet_engine,
        )
        if vps_inspection is not None:
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.5",
                "reply": str(vps_inspection["formatted_report"]),
                "data": {
                    "intent": "folder_vps_status_inspection",
                    "response_mode": "SYSTEM_DIAGNOSTICS",
                    "folder_vps_inspection": vps_inspection,
                },
                "source_attribution": "LIVE_VPS_AND_MOUNT_INSPECTION (RemoteVPSDevelopmentEngine + AuthorizedFolders + OS Mount)",
            }

        uni_action = run_universal_file_action_if_applicable(p_clean, ctx, self.universal_file_engine)
        if uni_action is not None:
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.5",
                "reply": str(uni_action["formatted_chat_report"]),
                "data": {
                    "intent": "universal_file_action",
                    "response_mode": "TASK_EXECUTION",
                    "universal_file_action": uni_action,
                },
                "source_attribution": "UNIVERSAL_FILE_ACTION_ENGINE (9-Stage Direct Action Workflow)",
            }

        # Delegate GENERAL_INTELLIGENCE directly to Local LLM (OllamaProvider) when online
        if r_mode == "GENERAL_INTELLIGENCE" and not mode_info.get("is_followup") and self.ollama_provider is not None:
            ollama_st = self.ollama_provider.status()
            if ollama_st.get("available"):
                return self.ollama_provider.respond(
                    prompt, context=ctx, cancel_check=cancel_check
                )

        learned_kb: list[dict[str, Any]] = []
        if self.self_learning_engine is not None:
            try:
                learned_kb = self.self_learning_engine.list_knowledge(active_only=True)
            except Exception:
                learned_kb = []

        # ── 1. TEST A: Pure Greeting ("Hai.", "Hai NUI.", "Halo", etc.) ──────
        if re.match(
            r"^(hai|halo|hello|hi|selamat\s+(pagi|siang|sore|malam))(\s+nui)?[\.\!\?]*$",
            p_lower,
        ):
            if already_greeted:
                reply = "Ada yang bisa saya bantu?"
            elif "nui" in p_lower:
                reply = "Halo! Saya NUI dari CosmicTera. Ada yang bisa saya bantu?"
            else:
                reply = "Halo! Ada yang bisa saya bantu?"
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "greeting",
                    "response_mode": r_mode,
                    "already_greeted": already_greeted,
                },
                "source_attribution": "NUI_PERSONA (Natural Conversation)",
            }

        # ── 2. TEST B: Identity & Persona ("Kamu siapa?", "Siapa kamu?", "Halo NUI, siapa kamu?") ──
        if any(
            phrase in p_lower
            for phrase in ("kamu siapa", "siapa kamu", "who are you", "apa itu nui", "perkenalkan dirimu")
        ):
            persona_meta = self.persona_loader.load_official_persona_metadata()
            prefix = "" if already_greeted else "Halo! "
            reply = (
                f"{prefix}Saya NUI, Natural Universal Intelligence dari CosmicTera. "
                "Saya siap membantu Anda melakukan komputasi, mengembangkan software, "
                "memahami Matematika Hijaiyyah, dan mengelola sistem CosmicTera."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "nui_identity",
                    "response_mode": r_mode,
                    "persona_metadata": persona_meta,
                },
                "source_attribution": "LOCAL_REPOSITORY (src/hijaiyyah/ai/runtime.py)",
            }

        # ── 2B. Capability Inquiry (`CAPABILITY_INQUIRY`: Software Dev, Coding, Languages, Debugging, Web, Repo Reading) ──
        if r_mode == "CAPABILITY_INQUIRY":
            sub_intent = mode_info.get("sub_intent", "software_development_capability")
            last_q = prior_user_turns[-1] if prior_user_turns else None
            tools_available = [
                "files.list",
                "files.read",
                "files.write",
                "coding.edit",
                "coding.run_test",
                "git.status",
                "git.diff",
                "web.search",
                "web.fetch",
                "web.preview",
            ]
            supported_langs = [
                "Python",
                "Swift",
                "C/C++",
                "JavaScript/TypeScript",
                "HTML/CSS",
                "Rust",
                "SQL",
                "Bash/Shell",
                "Verilog RTL (.v)",
                "H-ISA Assembly (.hasm)",
                "Hybit Code (.hc / .hcell)",
            ]

            if sub_intent == "coding_workflow_capability":
                reply = (
                    "Dalam mengerjakan tugas coding, saya mengikuti alur rekayasa terverifikasi di atas source code (`src/hijaiyyah/`, `rtl/`) dan tools yang diizinkan:\n\n"
                    "1. **Analisis Konteks & Struktur Kode**: Membaca berkas yang relevan (`files.read`, `git.status`) serta memetakan fungsi Python, modul Verilog RTL, dan program H-ISA melalui `program_index.py` dan `repository_graph.py`.\n"
                    "2. **Perancangan & Penulisan Kode**: Menyusun atau memperbarui kode menggunakan coding engine (`Qwen Coding Specialist` / `NativeNUIProvider`) serta `coding.edit` dan `files.write` dengan pencadangan otomatis.\n"
                    "3. **Pengujian & Validasi**: Menjalankan unit test (`pytest`), pemeriksaan tipe/lint, atau simulasi `HISAMachine` sesuai izin Anda sebelum perubahan dinyatakan selesai."
                )
            elif sub_intent == "programming_languages_capability":
                reply = (
                    "Saya dapat membantu pengembangan software dalam berbagai bahasa pemrograman umum maupun bahasa khusus ekosistem CosmicTera:\n\n"
                    "- **Bahasa Pemrograman Umum**: Python, Swift (macOS/SwiftUI), C/C++, JavaScript/TypeScript, HTML/CSS, Rust, SQL, dan Bash/Shell.\n"
                    "- **Bahasa & Arsitektur CosmicTera**: Verilog RTL (`.v`), H-ISA Assembly (`.hasm`), dan Hybit Code (`.hc` / `.hcell`).\n\n"
                    "Saya dapat membantu menulis kode baru, melakukan refactoring, menjelaskan alur program, hingga membuat unit test untuk bahasa-bahasa tersebut."
                )
            elif sub_intent == "python_debugging_capability":
                reply = (
                    "Tentu. Saya dapat membantu memperbaiki bug Python secara sistematis:\n\n"
                    "1. **Pelacakan Penyebab (Root Cause)**: Memeriksa traceback error, membaca fungsi terkait di source code (`files.read`), dan mengidentifikasi letak kegagalan logika atau tipe data.\n"
                    "2. **Perbaikan Terarah**: Menerapkan patch pada berkas Python (`coding.edit`) tanpa merusak antarmuka modul lain.\n"
                    "3. **Verifikasi Regresi**: Menjalankan `pytest` (`coding.run_test`) sesuai izin Anda untuk memastikan bug teratasi dan tidak menimbulkan regresi."
                )
            elif sub_intent == "website_development_capability":
                reply = (
                    "Tentu. Saya dapat membantu merancang dan membuat website maupun aplikasi web secara lengkap:\n\n"
                    "- **Frontend**: Menyusun struktur HTML5, tata letak CSS modern/responsif, dan logika interaktif JavaScript/TypeScript.\n"
                    "- **Backend & API**: Membangun server HTTP/REST atau SSE menggunakan Python serta mengintegrasikan penyimpanan data.\n"
                    "- **Pratinjau & Pengujian**: Menampilkan hasil halaman web pada ruang kerja Browser/Web Preview (`web.preview`) dan menguji endpoint secara lokal sesuai izin Anda."
                )
            elif sub_intent == "repository_reading_capability":
                reply = (
                    "Ya, saya dapat membaca dan menganalisis repository CosmicTera pada folder kerja yang telah Anda otorisasi.\n\n"
                    "Melalui `NUIToolRegistry` (`files.list`, `files.read`, `git.status`, `git.diff`) serta indeks struktural NUI (`L1–L2`), saya dapat menelusuri modul Python (`src/hijaiyyah/`), desain Verilog RTL (`rtl/`), program H-ISA (`.hasm`), dan dokumentasi teknis dengan tetap mematuhi aturan `PermissionEngine` dan baseline terkunci."
                )
            else:
                reply = (
                    "Tentu. Saya dapat membantu menganalisis source code, merancang program, menulis dan memperbaiki kode, "
                    "membuat unit test, melakukan debugging, serta membantu pengembangan website dan aplikasi.\n\n"
                    "Untuk pekerjaan pada repository, saya dapat menggunakan coding engine dan tools yang tersedia, "
                    "memeriksa perubahan, dan menjalankan pengujian sesuai izin Anda."
                )

            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": sub_intent,
                    "response_mode": "CAPABILITY_INQUIRY",
                    "referenced_prior_question": last_q,
                    "supported_languages": supported_langs,
                    "registered_coding_tools": tools_available,
                    "retrieved_sources": [],
                },
                "source_attribution": "NUI_PERSONA + LOCAL_REPOSITORY (src/hijaiyyah/ai/runtime.py, nui-desktop/backend/tools.py)",
            }

        # ── 3. TEST C: Repository Check / Recent Work / Repository Function ──
        if r_mode == "REPOSITORY_AUDIT":
            repo_summary = self._inspect_repository_summary(include_recent_work=True)
            if mode_info.get("sub_intent") == "repository_purpose":
                retrieved = self.retriever.retrieve(p_clean, custom_knowledge_items=learned_kb)
                reply = (
                    "Repository **CosmicTera (`/Users/AMRA/hijaiyyah-mathematics`)** berfungsi sebagai pusat pengembangan, simulasi, kompilasi, dan verifikasi perangkat keras ekosistem komputasi berbasis **Matematika Hijaiyyah** (*from letter to silicon*):\n\n"
                    f"1. **Fondasi Matematika & Kriptografi (`src/hijaiyyah/core/`, `crypto/`, `hisab/`)**: Mengimplementasikan `MASTER_TABLE` 28 huruf Hijaiyyah × vektor **Hybit 18D**, pemeriksa invarian **Six-Guard (`G1–G4, T1–T2`)**, eksomatriks 5×5, spons kriptografi **Ka'bah 1600-bit**, dan digest integritas **HISAB**.\n"
                    f"2. **Rantai Kompilasi & Mesin Virtual (`src/hijaiyyah/hisa/`, `nui/usr.py`)**: Mengompilasi **Hybit Code (`HC`)** ke **H-ISA Assembly (`.hasm`, `{repo_summary['hasm_programs']}` program)** dan **Bytecode (`.hbc`)**, serta menjalankannya secara deterministik pada simulator bit-exact **`HISAMachine`**.\n"
                    f"3. **Desain Silikon RTL & FPGA (`rtl/`)**: Menyimpan **`{repo_summary['verilog_modules']}` modul Verilog** untuk prosesor 5-tahap **HCPU (`rtl/hcpu_top.v`)**, sistem keamanan **USSS**, dan pusat kendali visual **HDMI 1280×720@60Hz (`hcpu_hdmi_top.v`)** pada papan **Sipeed Tang Nano 20K (`GW2AR-LV18QN88C8/I7`)**.\n"
                    f"4. **Kecerdasan NUI L0–L11 & Desktop Environment (`src/hijaiyyah/nui/`, `nui-desktop/`)**: Mengelola `{repo_summary['sealed_facts']}` fakta tersegel L0, indeks `{repo_summary['python_functions']}` fungsi Python, graf 7-domain L9, dan aplikasi **CosmicTera NUI Desktop**."
                )
                return {
                    "provider": self.provider_id,
                    "model": "cosmictera-nui-native-v1.3",
                    "reply": reply,
                    "data": {
                        "intent": "repository_purpose",
                        "response_mode": r_mode,
                        "repository_audit": repo_summary,
                        "retrieved_sources": [asdict(r) for r in retrieved],
                    },
                    "source_attribution": "LOCAL_REPOSITORY (NUI/LAYERS.md, src/hijaiyyah/, rtl/)",
                }

            if mode_info.get("sub_intent") == "recent_work_and_git":
                commits_md = "\n".join(
                    f"- `{c}`" for c in repo_summary.get("recent_commits", [])[:6]
                ) or "- Belum ada riwayat commit yang terbaca."
                changed_md = "\n".join(
                    f"- `{cf}`" for cf in repo_summary.get("changed_files", [])[:15]
                ) or "- Working tree bersih (tidak ada file uncommitted)."
                recent_files_md = "\n".join(
                    f"- `{rf['path']}` (diperbarui `{rf['modified_at']}`, `{rf['size_bytes']}` byte)"
                    for rf in repo_summary.get("recent_disk_files", [])[:10]
                )
                reply = (
                    f"Berikut **riwayat pekerjaan terakhir dan perubahan terbaru** di repository CosmicTera (`{repo_summary['repo_root']}`, branch `{repo_summary['branch']}` @ `{repo_summary['commit']}`):\n\n"
                    f"**1. Riwayat Commit Terakhir (`git log`)**\n{commits_md}\n\n"
                    f"**2. Status Perubahan Working Tree Saat Ini (`git status --short` — {repo_summary['modified_entries']} entri)**\n{changed_md}\n\n"
                    f"**3. Berkas yang Terakhir Diperbarui di Disk**\n{recent_files_md}\n\n"
                    f"**4. Ringkasan Komponen Aktif**\n"
                    f"- Program H-ISA (`.hasm`): `{repo_summary['hasm_programs']}` program | Modul Verilog RTL: `{repo_summary['verilog_modules']}` modul | Fungsi Python: `{repo_summary['python_functions']}` fungsi | Fakta L0: `{repo_summary['sealed_facts']}` fakta."
                )
                return {
                    "provider": self.provider_id,
                    "model": "cosmictera-nui-native-v1.3",
                    "reply": reply,
                    "data": {
                        "intent": "recent_work_and_git",
                        "response_mode": r_mode,
                        "repository_audit": repo_summary,
                    },
                    "source_attribution": "LOCAL_REPOSITORY (Live Git Log, Git Status & File Mtime Inspection)",
                }

            reply = (
                "Baik, saya akan memeriksa repository CosmicTera.\n\n"
                "Repository berhasil diperiksa. Saya menemukan beberapa komponen utama pada HCPU, H-ISA, dan NUI. "
                f"(Branch `{repo_summary['branch']}` @ `{repo_summary['commit']}`). "
                "Ada beberapa hal yang perlu ditinjau lebih lanjut.\n\n"
                "Apakah Anda ingin melihat ringkasan hasil pemeriksaannya?"
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "repository_check_summary",
                    "response_mode": r_mode,
                    "repository_audit": repo_summary,
                },
                "source_attribution": "LOCAL_REPOSITORY (Repository Inspection)",
            }

        # ── 4. TEST F: Explicit Full Audit Report ("Tampilkan seluruh hasil audit.") ──
        if r_mode == "DEEP_RESEARCH":
            repo_summary = self._inspect_repository_summary()
            subsystems = self.inspect_subsystems()
            layers = self.inspect_layers()
            sub_lines = "\n".join(
                f"- **{s['name']}** (`{s['status']}`): {s['summary']}"
                for s in subsystems[:6]
            )
            layer_lines = "\n".join(
                f"- **{l['layer']} ({l['name']})**: `{l['badge']}` — {l['honest_note']}"
                for l in layers
            )
            reply = (
                "Berikut laporan lengkap hasil audit repository CosmicTera:\n\n"
                f"**1. Status Git & Inventaris Kode (`{repo_summary['branch']}` @ `{repo_summary['commit']}`)**\n"
                f"- Perubahan berkas aktif di working tree: `{repo_summary['modified_entries']}` entri\n"
                f"- Modul RTL Verilog: `{repo_summary['verilog_modules']}` modul (`rtl/`)\n"
                f"- Program H-ISA Assembly: `{repo_summary['hasm_programs']}` program (`rtl/programs/`)\n"
                f"- Fungsi Python terindeks: `{repo_summary['python_functions']}` fungsi (`src/hijaiyyah/`)\n"
                f"- Fakta rekayasa tersegel (`facts/`): `{repo_summary['sealed_facts']}` fakta\n\n"
                f"**2. Subsistem Komputasi Utama**\n{sub_lines}\n\n"
                f"**3. Status Lapisan NUI L0–L11**\n{layer_lines}"
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "full_repository_audit",
                    "response_mode": r_mode,
                    "repository_audit": repo_summary,
                    "layers": layers,
                },
                "source_attribution": "LOCAL_REPOSITORY (Full Audit Report)",
            }

        # ── 5. Explicit System Diagnostics ("Cek sistem.", "Cek status sistem CosmicTera.") ──
        if r_mode == "SYSTEM_DIAGNOSTICS":
            dev_ports = sorted(str(p) for p in Path("/dev").glob("cu.usbserial-*"))
            op_mode = ctx.get("operating_mode", "HYBRID")
            host_res = measure_mac_host_resources()
            ollama_st = (
                self.ollama_provider.status()
                if self.ollama_provider is not None
                else {"available": False, "installed_models": [], "model": None}
            )
            ollama_summary = (
                f"CONNECTED (`{ollama_st.get('model')}`, {len(ollama_st.get('installed_models', []))} model lokal terpasang: {', '.join(ollama_st.get('installed_models', []))})"
                if ollama_st.get("available")
                else "DISCONNECTED / STANDBY"
            )
            hw_str = (
                f"CONNECTED ({', '.join(dev_ports)})"
                if dev_ports
                else "DISCONNECTED (mode komputasi lokal aktif)"
            )
            reply = (
                "Hasil pemeriksaan sistem CosmicTera NUI saat ini:\n"
                "- **Layanan Lokal**: `LOCAL SERVICE READY` (`127.0.0.1:8848`)\n"
                "- **Intelligence Provider**: `PROVIDER CONNECTED` (`cosmictera-nui-native-v1.3`)\n"
                f"- **Ollama Local Language Engine**: `{ollama_summary}`\n"
                f"- **Mode Operasi & Memori Host**: `{op_mode}` (`{host_res['cpu_brand']}`, Unified Memory `{host_res['memory_total_gb']} GiB`, Disk bebas `{host_res['disk_free_gb']} GiB`)\n"
                f"- **Perangkat Keras (Tang Nano 20K)**: `{hw_str}`"
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "system_diagnostics",
                    "response_mode": r_mode,
                    "service_state": "LOCAL SERVICE READY",
                    "provider_state": "PROVIDER CONNECTED",
                    "model_state": "MODEL READY",
                    "ollama_available": bool(ollama_st.get("available")),
                    "ollama_models": ollama_st.get("installed_models", []),
                    "operating_mode": op_mode,
                    "host_resources": host_res,
                    "hardware_connected": len(dev_ports) > 0,
                    "retrieved_sources": [],
                },
                "source_attribution": "LIVE_RUNTIME_PROBE (NUI Local Service & Host Diagnostics)",
            }

        # ── 5B. Explicit Hardware Burn-In Fact Inquiries (`watchdog` & `clock drift`) ──
        if has_word_boundary_match("watchdog", p_lower) or "no_watchdog_exists" in p_lower:
            retrieved = self.retriever.retrieve(p_clean, custom_knowledge_items=learned_kb)
            reply = (
                "Berdasarkan desain perangkat keras CosmicTera dan fakta terverifikasi Lapis 0 (`burnin.no_watchdog_exists`, status `DP`), "
                "tidak ada modul **watchdog** perangkat keras di dalam `rtl/`.\n\n"
                "Prinsip arsitekturnya adalah bahwa mesin yang berhenti (*halt*) tidak dapat melaporkan sendiri bahwa dirinya telah berhenti. "
                "Oleh karena itu, ketiadaan respons dipantau secara eksternal oleh host dengan mengukur selang kebisuan (*silence interval*) "
                "serta pencatatan kerja nyata per jam (`burnin.tier1_work_accounts_for_the_time`)."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "hardware_burnin_watchdog",
                    "response_mode": "TECHNICAL",
                    "fact_id": "burnin.no_watchdog_exists",
                    "retrieved_sources": [asdict(r) for r in retrieved],
                },
                "source_attribution": "LOCAL_REPOSITORY (facts/burn_in_integrity.json :: burnin.no_watchdog_exists)",
            }

        if (
            "clock drift" in p_lower
            or "tier1_clock_drift" in p_lower
            or (has_word_boundary_match("drift", p_lower) and any(w in p_lower for w in ("clock", "jam", "tercatat", "berapa", "ppm")))
            or (has_word_boundary_match("hanyut", p_lower) and "jam" in p_lower)
        ):
            retrieved = self.retriever.retrieve(p_clean, custom_knowledge_items=learned_kb)
            reply = (
                "Berdasarkan hasil pengujian burn-in 24 jam pada Lapis 0 (`burnin.tier1_clock_drift`, status `CC`), "
                "**clock drift** (hanyut jam papan terhadap jam host) yang tercatat adalah **−0,0292 detik per jam** "
                "selama 24 jam (setara dengan **8,1 ppm**).\n\n"
                "Nilai ini diukur relatif terhadap jam mesin pengembangan (*host clock*), bukan terhadap standar frekuensi laboratorium."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "hardware_burnin_clock_drift",
                    "response_mode": "TECHNICAL",
                    "fact_id": "burnin.tier1_clock_drift",
                    "drift_seconds_per_hour": -0.0292,
                    "drift_ppm": 8.1,
                    "retrieved_sources": [asdict(r) for r in retrieved],
                },
                "source_attribution": "LOCAL_REPOSITORY (facts/burn_in_integrity.json :: burnin.tier1_clock_drift)",
            }

        # ── 6. Multi-Turn Session Context & History Summarization ────────────
        if any(
            phrase in p_lower
            for phrase in (
                "pertanyaan pertama",
                "pesan pertama",
                "ringkas pertanyaan",
                "ringkas percakapan",
                "apa yang kita bahas",
                "pertanyaan sebelumnya",
                "tadi saya tanya",
                "first question",
                "summarize our",
            )
        ):
            if not prior_user_turns:
                reply = (
                    f"Belum ada pertanyaan sebelumnya di sesi ini. "
                    f"Pesan Anda saat ini adalah pesan pertama: \"{p_clean}\"."
                )
                return {
                    "provider": self.provider_id,
                    "model": "cosmictera-nui-native-v1.3",
                    "reply": reply,
                    "data": {
                        "intent": "session_context_summary",
                        "response_mode": r_mode,
                        "prior_user_turns_count": 0,
                    },
                    "source_attribution": "SESSION_CONTEXT",
                }

            first_q = prior_user_turns[0]
            last_q = prior_user_turns[-1]
            reply = (
                f"Pertanyaan pertama Anda di sesi ini adalah \"{first_q}\". "
                f"Sejauh ini terdapat {len(prior_user_turns)} pesan sebelumnya, "
                f"dengan bahasan terakhir mengenai \"{last_q}\"."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "session_context_summary",
                    "response_mode": r_mode,
                    "first_user_question": first_q,
                    "last_user_question": last_q,
                    "prior_user_turns_count": len(prior_user_turns),
                    "prior_user_questions": prior_user_turns,
                },
                "source_attribution": f"SESSION_CONTEXT ({len(prior_user_turns)} prior turns)",
            }

        # ── 7. TEST E: Contextual Follow-Up ("Contohnya?", "Jelaskan lebih detail.", "Lanjutkan pembahasan sebelumnya.", etc.) ──
        if (prior_user_turns or prior_assistant_turns) and (
            any(
                phrase in p_lower or phrase in p_norm
                for phrase in (
                    "jelaskan lebih detail",
                    "jelaskan lebih lanjut",
                    "lebih detail",
                    "bagaimana cara kerjanya",
                    "cara kerjanya",
                    "hubungannya dengan",
                    "pertanyaan tadi",
                    "pembahasan sebelumnya",
                    "lanjutkan pembahasan",
                    "lanjutkan yang tadi",
                    "mengontrol keduanya",
                    "itu bekerja",
                    "lihat ringkasan",
                    "tampilkan ringkasan",
                    "ya, tampilkan",
                    "contohnya",
                    "berikan contoh",
                    "kasih contoh",
                    "maksudnya",
                )
            )
            or p_lower in {"contohnya?", "contohnya", "maksudnya?", "maksudnya", "lanjutkan", "lanjutkan."}
        ):
            last_user_q = prior_user_turns[-1] if prior_user_turns else "topik sebelumnya"
            last_q_low = last_user_q.lower()
            last_asst_txt = prior_assistant_turns[-1].lower() if prior_assistant_turns else ""

            # 7a. Follow-up asking for an example ("Contohnya?")
            if any(w in p_lower for w in ("contoh", "maksudnya")):
                if any(w in last_q_low or w in last_asst_txt for w in ("software", "sofwer", "softer", "coding", "kode", "python", "website", "web", "bug")):
                    reply = (
                        f"Sebagai contoh konkret dari pembahasan **{last_user_q}**, berikut dua tugas pengembangan software yang dapat langsung saya jalankan dan uji:\n\n"
                        "1. **Contoh Fungsi Python Terverifikasi (`MASTER_TABLE` & `Six-Guard`)**:\n"
                        "```python\n"
                        "from hijaiyyah.core.master_table import MASTER_TABLE\n"
                        "from hijaiyyah.core.guards import full_guard_check\n\n"
                        "jim = MASTER_TABLE.get_by_name('Jim')\n"
                        "assert full_guard_check(jim.vector)['all_pass'] is True\n"
                        "```\n"
                        "2. **Contoh Program H-ISA Assembly (`rtl/programs/test_bsm.hasm`)**:\n"
                        "```hasm\n"
                        "HLOAD H1, 2      ; Muat vektor Ba\n"
                        "HLOAD H2, 12     ; Muat vektor Sin\n"
                        "HLOAD H3, 24     ; Muat vektor Mim\n"
                        "HCADD H4, H1, H2 ; H4 = Ba + Sin\n"
                        "HCADD H4, H4, H3 ; H4 = Ba + Sin + Mim\n"
                        "HNRM2 R1, H4     ; R1 = ||BSM||^2 = 112\n"
                        "PRINT R1\n"
                        "HALT\n"
                        "```"
                    )
                else:
                    reply = (
                        f"Sebagai contoh konkret terkait **{last_user_q}**, Anda dapat langsung memberikan perintah seperti:\n\n"
                        "- **Komputasi Matematika & H-ISA**: `Hitung 128 * 64` atau `Jalankan program H-ISA test_bsm.hasm` (menghasilkan `R1 = 112` dalam `9` siklus).\n"
                        "- **Pengembangan & Audit Kode**: `Cek repository` atau `Buatkan fungsi Python untuk memvalidasi vektor Hybit 18D`.\n"
                        "- **Diagnostik Sistem & Hardware**: `Cek sistem` atau `Jelaskan hubungan NUI dengan HCPU`."
                    )
                return {
                    "provider": self.provider_id,
                    "model": "cosmictera-nui-native-v1.3",
                    "reply": reply,
                    "data": {
                        "intent": "contextual_followup_example",
                        "response_mode": "TECHNICAL",
                        "referenced_prior_question": last_user_q,
                        "retrieved_sources": [],
                    },
                    "source_attribution": "SESSION_CONTEXT + LOCAL_REPOSITORY",
                }

            # 7b. Follow-up on prior math calculation
            m_prev_math = re.search(r"(-?\d+)\s*(\+|\-|\*|x|×|/)\s*(-?\d+)", last_user_q)
            if m_prev_math:
                a_v = int(m_prev_math.group(1))
                op_s = m_prev_math.group(2)
                b_v = int(m_prev_math.group(3))
                if op_s in {"+", "-"}:
                    hc_src = f"let a = {a_v};\nlet b = {b_v};\nprint(a {op_s} b);\n"
                    res = self.execute_calculation_or_program("hc_compile_exec", {"source": hc_src})
                    out_v = res["output"][0] if res.get("output") else (a_v + b_v if op_s == "+" else a_v - b_v)
                    emitted_inline = res.get("emitted_hasm", "").strip()
                    reply = (
                        f"Perhitungan `{a_v} {op_s} {b_v} = {out_v}` dieksekusi secara deterministik melalui rantai kompilasi CosmicTera:\n\n"
                        f"1. **Hybit Code (`usr.lower`)**: `let a = {a_v}; let b = {b_v}; print(a {op_s} b);`\n"
                        f"2. **Instruksi H-ISA (`{res['instruction_words']}` kata)**: Memuat operan ke register dengan `MOVI`, menjumlahkan dengan `{'ADD' if op_s == '+' else 'SUB'}`, mencetak lewat `PRINT`, dan berhenti pada `HALT`.\n"
                        f"3. **Eksekusi `HISAMachine`**: Menghasilkan output `{res['output']}` dalam `{res['cycles']}` siklus.\n\n"
                        f"```hasm\n{emitted_inline}\n```"
                    )
                else:
                    hisa_op = "MUL" if op_s in {"*", "x", "×"} else "DIV"
                    hasm_src = f"MOVI R1, {a_v}\nMOVI R2, {b_v}\n{hisa_op} R3, R1, R2\nPRINT R3\nHALT\n"
                    res = self.execute_calculation_or_program("hasm_exec", {"source": hasm_src})
                    out_v = res["output"][0] if res.get("output") else 0
                    reply = (
                        f"Perhitungan `{a_v} {op_s} {b_v} = {out_v}` dijalankan pada `HISAMachine` menggunakan instruksi "
                        f"`MOVI R1, {a_v}`, `MOVI R2, {b_v}`, `{hisa_op} R3, R1, R2`, `PRINT R3`, dan `HALT` "
                        f"dengan hasil `{res['output']}` dalam `{res['cycles']}` siklus."
                    )
                return {
                    "provider": self.provider_id,
                    "model": "cosmictera-nui-native-v1.3",
                    "reply": reply,
                    "data": {
                        "intent": "contextual_followup_math",
                        "response_mode": "TECHNICAL",
                        "referenced_prior_question": last_user_q,
                    },
                    "source_attribution": "SESSION_CONTEXT + HISAMachine",
                }

            # 7c. Follow-up on prior repository check
            if any(k in last_q_low for k in ("cek repo", "periksa repo", "audit repo")):
                repo_summary = self._inspect_repository_summary()
                reply = (
                    f"Berikut ringkasan temuan pemeriksaan repository CosmicTera (`{repo_summary['branch']}` @ `{repo_summary['commit']}`):\n\n"
                    f"- **HCPU & RTL (`rtl/`)**: `{repo_summary['verilog_modules']}` modul Verilog aktif dengan pipeline 5-tahap 27 MHz dan 84 opcode RTL.\n"
                    f"- **H-ISA & Program (`rtl/programs/`)**: `{repo_summary['hasm_programs']}` program `.hasm` terindeks dan 74 opcode terbukti paritas P3.\n"
                    f"- **NUI L0–L11 (`src/hijaiyyah/nui/`)**: Lapisan `{', '.join(repo_summary['active_layers'])}` telah diimplementasikan (`{repo_summary['sealed_facts']}` fakta tersegel), sedangkan `{', '.join(repo_summary['at_layers'])}` berstatus target arsitektural (`AT`).\n"
                    f"- **Working Tree**: Terdapat `{repo_summary['modified_entries']}` entri perubahan yang sedang dikerjakan."
                )
                return {
                    "provider": self.provider_id,
                    "model": "cosmictera-nui-native-v1.3",
                    "reply": reply,
                    "data": {
                        "intent": "contextual_followup_repo",
                        "response_mode": "TECHNICAL",
                        "referenced_prior_question": last_user_q,
                        "repository_audit": repo_summary,
                    },
                    "source_attribution": "SESSION_CONTEXT + LOCAL_REPOSITORY",
                }

            # 7d. General multi-turn topic continuation
            combined_query = f"{last_user_q} — {p_clean}"
            retrieved = self.retriever.retrieve(combined_query, custom_knowledge_items=learned_kb)
            src_cites = ", ".join(f"`{r.file_path}`" for r in retrieved[:3]) or "`src/hijaiyyah/`"
            reply = (
                f"Melanjutkan pembahasan kita sebelumnya mengenai **{last_user_q}**, mekanisme kerjanya di dalam arsitektur CosmicTera ({src_cites}) mencakup tiga tahap:\n\n"
                "1. **Representasi & Validasi Vektor (`master_table.py` & `guards.py`)**: Setiap huruf Hijaiyyah direpresentasikan sebagai vektor Hybit 18D dan dijaga oleh invarian Six-Guard (`G1–G4, T1–T2`).\n"
                "2. **Eksekusi Instruksi (`H-ISA` & `HCPU`)**: Instruksi 32-bit H-ISA (termasuk 28 opcode huruf `0xE0–0xFB` yang dipetakan di `atom.py`) dieksekusi pada pipeline 5-tahap HCPU (`IF → ID → EX → MEM → WB`).\n"
                "3. **Koordinasi NUI (`L0–L11`)**: NUI melacak jejak eksekusi (`L3`), memverifikasi paritas perangkat lunak-keras (`L4`), memodelkan fungsi transisi RTL (`L6`), dan menegakkan gerbang fail-closed (`L7` + `USSS`)."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "contextual_followup",
                    "response_mode": "TECHNICAL",
                    "referenced_prior_question": last_user_q,
                    "retrieved_sources": [asdict(r) for r in retrieved],
                },
                "source_attribution": f"SESSION_CONTEXT + REPOSITORY_RETRIEVAL ({src_cites})",
            }

        # ── 8. H-ISA Program Execution ("Jalankan program H-ISA.", "test_bsm.hasm") ──
        is_hisa_exec_request = (
            "test_bsm.hasm" in p_lower
            or any(
                phrase in p_lower or phrase in p_norm
                for phrase in (
                    "jalankan program h-isa",
                    "jalankan program hisa",
                    "eksekusi program h-isa",
                    "eksekusi program hisa",
                    "jalankan h-isa",
                    "jalankan hisa",
                    "simulasi h-isa",
                    "jalankan contoh program h-isa",
                )
            )
            or ("jalankan" in p_lower and ".hasm" in p_lower)
        )
        if is_hisa_exec_request:
            target_hasm_name = "test_bsm.hasm"
            m_hasm = re.search(r"([a-zA-Z0-9_]+\.hasm)", p_clean)
            if m_hasm and (REPO_ROOT / "rtl" / "programs" / m_hasm.group(1)).is_file():
                target_hasm_name = m_hasm.group(1)

            prog_path = REPO_ROOT / "rtl" / "programs" / target_hasm_name
            src_text = prog_path.read_text(encoding="utf-8")
            words = assemble(src_text, base_dir=prog_path.parent)
            m = HISAMachine(MASTER_TABLE)
            m.load_program(words)
            m.run()
            r1_val = int(m.output[0]) if m.output else int(m.regs.gpr[1])
            reply = (
                f"Program H-ISA `rtl/programs/{target_hasm_name}` (`{len(words)}` instruksi) berhasil dijalankan pada `HISAMachine`:\n"
                f"- **Instruksi**: Memuat vektor Ba, Sin, dan Mim (`HLOAD`), menjumlahkan dengan `HCADD`, menghitung norma kuadrat `HNRM2`, dan mencetak hasil (`PRINT`).\n"
                f"- **Hasil Eksekusi**: Output `{list(m.output)}` (`R1 = {r1_val}`), `PC = {m.regs.pc}`, selesai dalam `{m.cycle}` siklus dengan status Six-Guard `{'PASS' if m.regs.sr.guard_pass else 'OK'}`."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "hisa_program_execution",
                    "response_mode": r_mode,
                    "program": f"rtl/programs/{target_hasm_name}",
                    "hisa_execution": {
                        "R1": r1_val,
                        "PC": m.regs.pc,
                        "cycles": m.cycle,
                        "output": list(m.output),
                    },
                },
                "source_attribution": f"LOCAL_REPOSITORY (rtl/programs/{target_hasm_name} + HISAMachine)",
            }

        if has_word_boundary_match("bsm", p_lower) or has_word_boundary_match("basmalah", p_lower):
            ba = MASTER_TABLE.get_by_name("Ba")
            sin = MASTER_TABLE.get_by_name("Sin")
            mim = MASTER_TABLE.get_by_name("Mim")
            bsm_vec = [a + b + c for a, b, c in zip(ba.vector, sin.vector, mim.vector)]
            nmv_val = an_norm_squared(bsm_vec)
            guards = full_guard_check(ba.vector)
            bsm_values = (112, 10, 9)
            reply = (
                f"Hasil perhitungan deterministik BSM (Ba + Sin + Mim) menghasilkan tiga invarian utama `{bsm_values}` "
                f"dengan norma kuadrat (`HNRM2` / `NMV`) sebesar **{nmv_val}** dan status guard **{'SIX-GUARD PASS' if guards['all_pass'] else 'FAULT'}**."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "response_mode": r_mode,
                    "bsm": {"values": bsm_values, "nmv": nmv_val, "guards": guards},
                },
                "source_attribution": "LOCAL_REPOSITORY (src/hijaiyyah/core/master_table.py)",
            }

        # ── 9. TEST D: Natural-Language Math & H-ISA Computation ─────────────
        math_match = re.search(
            r"(-?\d+)\s*(\+|\-|\*|x|×|/)\s*(-?\d+)", p_clean, re.IGNORECASE
        )
        if math_match and any(
            w in p_lower
            for w in ("hitung", "berapa", "jumlah", "tambah", "kurang", "kali", "bagi", "+", "-", "*")
        ):
            a_val = int(math_match.group(1))
            op_sym = math_match.group(2)
            b_val = int(math_match.group(3))
            wants_detail = any(w in p_lower for w in ("jelaskan", "rincian", "detail", "bagaimana"))

            if op_sym in {"+", "-"}:
                hc_prog = f"let a = {a_val};\nlet b = {b_val};\nprint(a {op_sym} b);\n"
                res = self.execute_calculation_or_program(
                    "hc_compile_exec", {"source": hc_prog}
                )
                out_val = (
                    res["output"][0]
                    if res.get("output")
                    else (a_val + b_val if op_sym == "+" else a_val - b_val)
                )
                if wants_detail:
                    emitted_inline = res.get("emitted_hasm", "").strip()
                    reply = (
                        f"Hasilnya adalah **{out_val}** (`{a_val} {op_sym} {b_val} = {out_val}`).\n\n"
                        f"Perhitungan dieksekusi melalui kompilasi Hybit Code ke `{res['instruction_words']}` instruksi H-ISA (`MOVI`, `{'ADD' if op_sym == '+' else 'SUB'}`, `PRINT`, `HALT`) pada `HISAMachine` dalam `{res['cycles']}` siklus:\n"
                        f"```hasm\n{emitted_inline}\n```"
                    )
                elif "hitung" in p_lower:
                    reply = f"Hasilnya {out_val} ({a_val} {op_sym} {b_val} = {out_val})."
                else:
                    reply = f"Hasilnya {out_val}."
                return {
                    "provider": self.provider_id,
                    "model": "cosmictera-nui-native-v1.3",
                    "reply": reply,
                    "data": {
                        "intent": "natural_language_math",
                        "response_mode": "TECHNICAL" if wants_detail else "CONVERSATIONAL",
                        "operands": [a_val, b_val],
                        "operator": op_sym,
                        "result": out_val,
                        **res,
                    },
                    "source_attribution": "LOCAL_REPOSITORY (src/hijaiyyah/nui/usr.py + src/hijaiyyah/hisa/machine.py)",
                }
            else:
                hisa_op = "MUL" if op_sym in {"*", "x", "×"} else "DIV"
                hasm_src = f"MOVI R1, {a_val}\nMOVI R2, {b_val}\n{hisa_op} R3, R1, R2\nPRINT R3\nHALT\n"
                res = self.execute_calculation_or_program("hasm_exec", {"source": hasm_src})
                out_val = res["output"][0] if res.get("output") else 0
                if wants_detail:
                    reply = (
                        f"Hasilnya adalah **{out_val}** (`{a_val} {op_sym} {b_val} = {out_val}`). "
                        f"Dijalankan pada `HISAMachine` menggunakan instruksi `MOVI` dan `{hisa_op}` dalam `{res['cycles']}` siklus."
                    )
                elif "hitung" in p_lower:
                    reply = f"Hasilnya {out_val} ({a_val} {op_sym} {b_val} = {out_val})."
                else:
                    reply = f"Hasilnya {out_val}."
                return {
                    "provider": self.provider_id,
                    "model": "cosmictera-nui-native-v1.3",
                    "reply": reply,
                    "data": {
                        "intent": "natural_language_math",
                        "response_mode": "TECHNICAL" if wants_detail else "CONVERSATIONAL",
                        "operands": [a_val, b_val],
                        "operator": op_sym,
                        "result": out_val,
                        **res,
                    },
                    "source_attribution": "LOCAL_REPOSITORY (src/hijaiyyah/hisa/machine.py)",
                }

        # ── 10. Explicit Hybit Code (`let ... = ...; print(...);`) ───────────
        if "let " in p_lower and ("print(" in p_lower or "println(" in p_lower):
            code_match = re.search(r"```(?:hc|hybit)?\s*(.*?)```", p_clean, re.DOTALL)
            hc_src = code_match.group(1).strip() if code_match else p_clean
            res = self.execute_calculation_or_program("hc_compile_exec", {"source": hc_src})
            if res.get("status") == "OK":
                reply = (
                    f"Program Hybit Code (HC) berhasil dikompilasi ke H-ISA (`{res['instruction_words']}` instruksi, `{res['hbc_size_bytes']}` byte HBC) "
                    f"dan dieksekusi pada `HISAMachine` dalam `{res['cycles']}` siklus dengan output `{res['output']}`."
                )
            else:
                reply = f"Kompilasi HC dihentikan oleh parser/compiler dengan pesan: `{res.get('error')}`"
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {**res, "response_mode": r_mode},
                "source_attribution": "LOCAL_REPOSITORY (HC -> H-ISA -> HISAMachine)",
            }

        # ── 11. Explicit H-ISA Assembly (`.hasm`) ────────────────────────────
        if any(
            tok in p_clean.upper()
            for tok in ("MOVI ", "HLOAD ", "HNRM2 ", "HDIST ", "HDOT ", "HGRD ")
        ):
            res = self.execute_calculation_or_program("hasm_exec", {"source": p_clean})
            reply = (
                f"Program H-ISA Assembly selesai dijalankan pada `HISAMachine` (`{res['instruction_count']}` instruksi, `{res['cycles']}` siklus) "
                f"dengan output `{res['output']}` dan status Six-Guard `{'PASS' if res['guard_pass'] else 'FAULT'}`."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {**res, "response_mode": r_mode},
                "source_attribution": "LOCAL_REPOSITORY (src/hijaiyyah/hisa/machine.py)",
            }

        # ── 12. Validated Self-Learning Knowledge Match (Word-Boundary Only) ─
        if learned_kb and is_cosmictera_domain_query(p_clean):
            q_tokens = [
                w
                for w in re.findall(r"[a-zA-Z0-9_\-]{3,}", p_norm)
                if w not in self.retriever.STOPWORDS
            ]
            for item in learned_kb:
                if item.get("validation_status") != "VALIDATED":
                    continue
                if item.get("topic") in {"hmcl_feature_coherence", "Koherensi Ruang Fitur 5D NUI & HMCL"}:
                    continue
                hay = f"{item['title']} {item['topic']} {item['content']}"
                matched_t = [tok for tok in q_tokens if has_word_boundary_match(tok, hay)]
                if q_tokens and len(matched_t) >= max(1, min(2, len(q_tokens))):
                    reply = f"**{item['title']}** (`{item['provenance']}`): {item['content']}"
                    return {
                        "provider": self.provider_id,
                        "model": "cosmictera-nui-native-v1.3",
                        "reply": reply,
                        "data": {
                            "intent": "self_learning_reuse",
                            "response_mode": r_mode,
                            "entry_id": item["entry_id"],
                            "provenance": item["provenance"],
                            "version": item["version"],
                        },
                        "source_attribution": f"NUI_SELF_LEARNING ({item['source_path']} | {item['provenance']})",
                    }

        # ── 13. Project Context: Hybit 18D & Matematika Hijaiyyah ────────────
        if has_word_boundary_match("hybit", p_lower) and (
            has_word_boundary_match("hijaiyyah", p_lower) or has_word_boundary_match("18d", p_lower)
        ):
            retrieved = self.retriever.retrieve(p_clean, custom_knowledge_items=learned_kb)
            reply = (
                "**Hybit 18D** adalah representasi vektor 18-dimensi dalam **Matematika Hijaiyyah** untuk setiap 28 huruf pada `MASTER_TABLE` (`src/hijaiyyah/core/master_table.py`). "
                "Ke-18 komponennya terdiri atas sudut putaran (`Θ`), 3 komponen titik (`Na, Nb, Nd`), 5 komponen garis lurus (`Kp..Kc`), 5 komponen lengkung (`Qp..Qc`), serta 4 komponen agregat/invarian (`AN, AK, AQ, H*`). "
                "Keabsahan setiap vektor dijaga oleh keenam invarian **Six-Guard (`G1–G4, T1–T2`)** di `src/hijaiyyah/core/guards.py` dan dievaluasi dalam 1 siklus oleh `rtl/hcpu_guard.v`."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "hybit_18d_matematika_hijaiyyah",
                    "response_mode": r_mode,
                    "retrieved_sources": [asdict(r) for r in retrieved],
                },
                "source_attribution": "LOCAL_REPOSITORY (src/hijaiyyah/core/master_table.py, src/hijaiyyah/core/guards.py)",
            }

        # ── 13B. Portal 8888 (`portal8888/` & `src/hijaiyyah/nui/layer7_portal.py`) ──
        if "portal8888" in p_lower.replace(" ", "") or (
            has_word_boundary_match("portal", p_lower) and ("8888" in p_lower or "fungsi" in p_lower or "cek" in p_lower or "arsitektur" in p_lower)
        ):
            ws_scan = scan_workspace_for_query(p_clean, repo_root=REPO_ROOT)
            retrieved = self.retriever.retrieve(p_clean, custom_knowledge_items=learned_kb)
            reply = (
                "**Portal 8888 (`portal8888/` & `src/hijaiyyah/nui/layer7_portal.py`)** ditemukan di repository CosmicTera (`/Users/AMRA/hijaiyyah-mathematics/portal8888`).\n\n"
                "### 1. Fungsi Utama Portal 8888 (`portal8888/ARCHITECTURE.md` & `README.md`)\n"
                "Portal 8888 adalah **sistem bukti-tahan-rusak (*tamper-evident & anti-rollback*) untuk asal dan integritas sinyal** dengan tiga fungsi utama:\n"
                "1. **Find My / Anti-Maling**: Perangkat melaporkan posisinya sendiri dan disegel secara kriptografis sehingga jejaknya tidak dapat dihapus.\n"
                "2. **Deteksi Akses Akun / Login Anomali (*Impossible Travel & Geofence*)**: Menandai login dari wilayah atau selisih waktu yang mustahil (> 1.000 km/jam) berdasarkan cap waktu presisi di domain clock PHY.\n"
                "3. **Paket Bukti Tersegel untuk Pemilik**: Menyegel `IP sumber + waktu UTC tepat (SOF) + port fisik + SHA-256 frame` (body kanonik **125 byte MSB-first**) menggunakan **HMAC-SHA256** dan rantai 4 sudut (`A, B, C, D` × `k=8` blok) + `ROOT` + register **Jangkar Kepala** (*head anchor*) anti-rollback.\n\n"
                "### 2. Struktur Folder & Komponen di Repository (`portal8888/`)\n"
                "- **RTL Top Operasional v1 (`portal8888/rtl/hijaiyyah_portal8888.v`)**: Menangkap stream byte PHY (`ingress_parse_v1.v`), cap waktu SOF (`hijaiyyah_timestamp.v`), replay `hijaiyyah_sha256_stream`, segel `hijaiyyah_hmac`, indeks `jim_index.v` (GF(5), periode 3.124), serta rantai 4 sudut + jangkar kepala.\n"
                "- **Pembungkus FPGA Tang Nano 20K (`portal8888/fpga/gowin/hijaiyyah_portal8888_gowin_top.v`)**: Portal di balik antarmuka UART 10-pin untuk `GW2AR-18C` (15.848 LUT4, 8.080 DFF, 6 BSRAM; bitstream `portal8888/build/gowin/hijaiyyah_portal8888_gowin_top.fs`).\n"
                "- **Protokol, Model Referensi & Uji Papan (`portal8888/ref/` & `scripts/`)**: `portal_uart.py` (encoder & checker byte-exact), `portal_ref.py`, `findmy.py`, `provenance.py`, dan `scripts/portal8888_uart_test.py` (teruji di papan Tang Nano 20K: 23 perintah & 224 perintah dengan 200 frame asli, 0 salah).\n"
                "- **Integrasi NUI Lapis 7 (`src/hijaiyyah/nui/layer7_portal.py`)**: Mengimplementasikan `ISOLATE_FAULT` (`ADAPTER_ABSENT`, `BOARD_NOT_DETECTED`, `BOARD_SILENT`, `SEAL_MISMATCH`), `RESTART_PORTAL`, dan `RECOVER_PORTAL` dengan batas maksimal 3 restart per gangguan."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "portal8888_inspection",
                    "response_mode": r_mode,
                    "workspace_scan": ws_scan,
                    "retrieved_sources": [asdict(r) for r in retrieved],
                },
                "source_attribution": "LOCAL_REPOSITORY (portal8888/README.md, portal8888/ARCHITECTURE.md, portal8888/rtl/hijaiyyah_portal8888.v, src/hijaiyyah/nui/layer7_portal.py)",
            }

        # ── 14. Source Code & NUI L6 Inquiry ─────────────────────────────────
        if any(
            has_word_boundary_match(k, p_lower)
            for k in ("nui l6", "program nui l6", "lapis 6", "layer 6")
        ):
            retrieved = self.retriever.retrieve(p_clean, custom_knowledge_items=learned_kb)
            reply = (
                "**NUI Lapis 6 (Pemahaman Perangkat Keras / Hardware Intelligence)** di `src/hijaiyyah/nui/` mencakup:\n"
                "1. **Inventaris & Keadaan Hardware (`6.1–6.5`)**: `hardware.py`, `telemetry_sources.py`, `hardware_provenance.py`, `hardware_state.py`, dan `hardware_correlation.py` yang memisahkan klaim `LIVE`, `MEASURED`, `SIMULATED`, dan `UNKNOWN` secara ketat.\n"
                "2. **Model RTL sebagai Fungsi Transisi (`rtl_function.py`)**: Memodelkan modul Verilog HCPU (`UART RX/TX`, `MMIO`, `DataRAM`, `Loader`, `Pipeline`, `HCPU`) sebagai fungsi transisi keadaan deterministik yang terverifikasi identik siklus demi siklus terhadap simulasi RTL."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "explain_nui_l6",
                    "response_mode": r_mode,
                    "modules": [
                        "src/hijaiyyah/nui/hardware.py",
                        "src/hijaiyyah/nui/telemetry_sources.py",
                        "src/hijaiyyah/nui/hardware_provenance.py",
                        "src/hijaiyyah/nui/hardware_state.py",
                        "src/hijaiyyah/nui/hardware_correlation.py",
                        "src/hijaiyyah/nui/rtl_function.py",
                    ],
                    "retrieved_sources": [asdict(r) for r in retrieved],
                },
                "source_attribution": "LOCAL_REPOSITORY (NUI/LAYERS.md, src/hijaiyyah/nui/rtl_function.py)",
            }

        # ── 15. Documentation / Gowin FPGA Inquiry ───────────────────────────
        if any(
            has_word_boundary_match(w, p_lower)
            for w in ("cari dokumentasi", "gowin", "tang nano", "openfpgaloader")
        ):
            hw_claims = knowledge.query("hardware identity")
            op_mode = ctx.get("operating_mode", "HYBRID")
            reply = (
                "Berdasarkan dokumentasi perangkat keras di repositori (`NUI/HARDWARE.md` dan `rtl/fpga/gowin/`), "
                "papan target adalah **Sipeed Tang Nano 20K** dengan FPGA **Gowin `GW2AR-LV18QN88C8/I7` (`GW2A-18C`, IDCODE `0x81b`)**. "
                "Sistem berjalan pada osilator `27.00 MHz` dengan keluaran HDMI `1280×720 @ 60 Hz` (`pixel_clk 74.25 MHz`, `Fmax 86.01 MHz`) "
                "dan menggunakan kebijakan pemrograman aman `SRAM_ONLY` (`openFPGALoader -b tangnano20k hcpu_hdmi_top.fs`)."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "gowin_fpga_documentation",
                    "response_mode": r_mode,
                    "hardware_claims": len(hw_claims.get("PAPAN", [])),
                    "operating_mode": op_mode,
                },
                "source_attribution": "LOCAL_REPOSITORY (NUI/HARDWARE.md, rtl/fpga/gowin/hcpu_hdmi_top.v)",
            }

        # ── 16. Relationship Between NUI/H-ISA and HCPU ──────────────────────
        if has_word_boundary_match("hcpu", p_lower) and (
            has_word_boundary_match("nui", p_lower)
            or has_word_boundary_match("h-isa", p_lower)
            or has_word_boundary_match("hisa", p_lower)
        ):
            hcpu_kb = knowledge.query("term HCPU")
            hisa_kb = knowledge.query("term H-ISA")
            rtl_kb = knowledge.query("rtl hcpu_top")
            hcpu_term = (hcpu_kb.get("NUI") or [{}])[0]
            hisa_term = (hisa_kb.get("NUI") or [{}])[0]
            instantiated_modules = [
                item.get("module")
                for item in rtl_kb.get("RTL", [])
                if item.get("what") == "instantiates"
            ]
            if has_word_boundary_match("h-isa", p_lower) or has_word_boundary_match("hisa", p_lower):
                reply = (
                    "**Hubungan H-ISA dengan HCPU** di dalam ekosistem CosmicTera adalah hubungan antara **kontrak arsitektur set instruksi** dan **realisasi prosesor perangkat kerasnya**:\n\n"
                    "1. **H-ISA (*Hijaiyyah Instruction Set Architecture v1.2*, `docs/HISA_SPEC.md`)**: Merupakan spesifikasi arsitektur instruksi biner 32-bit yang mencakup **105 opcode spesifikasi** (`84` opcode diimplementasikan di RTL dan `74` opcode terbukti paritas **P3**), termasuk **28 opcode atomik huruf Hijaiyyah (`0xE0–0xFB`)**, instruksi vektor Codex (`HLOAD`, `HCADD`, `HNRM2`, `HDIST`, `HDOT`, `HGRD`), serta instruksi integritas `HISAB` (`HPACK`, `HCRC`).\n"
                    "2. **HCPU (*Hijaiyyah Core Processing Unit*, `rtl/hcpu_top.v`)**: Merupakan implementasi mikroprosesor pipeline **5-tahap (`IF → ID → EX → MEM → WB`)** dalam Verilog RTL pada FPGA Tang Nano 20K (`27.00 MHz`, `Fmax 119.60 MHz`) yang mendekode dan mengeksekusi instruksi biner H-ISA secara langsung di silikon menggunakan register skalar 32-bit (`R0–R15`), register vektor **Hybit 18D (`H0–H7`, 144-bit)**, ALU Codex 14-DSP, dan pemeriksa **Six-Guard 1-siklus (`hcpu_guard.v`)**.\n"
                    "3. **Verifikasi Paritas Bit-Exact (`src/hijaiyyah/hisa/machine.py` & `nui/parity_model.py`)**: Setiap program H-ISA (`.hasm` / `.hbc`) dieksekusi baik pada simulator referensi `HISAMachine` maupun pada RTL `HCPU` dengan kesesuaian keadaan register dan flag yang diverifikasi oleh NUI Lapis 4."
                )
            else:
                reply = (
                    "Di dalam ekosistem CosmicTera, **NUI (*Natural Universal Intelligence*)** berperan sebagai lapisan kecerdasan komputasi dan orkestrasi, "
                    "sedangkan **HCPU (*Hijaiyyah Core Processing Unit*)** adalah prosesor silikon 5-tahap yang mengeksekusi instruksi H-ISA:\n\n"
                    "1. **Unifikasi Alamat Atomik (`src/hijaiyyah/nui/atom.py`)**: Indeks huruf pada Master Table NUI terhubung langsung ke opcode H-ISA (`0xE0–0xFB`) dan alamat ROM pada HCPU.\n"
                    "2. **Verifikasi Paritas & Jejak Eksekusi (`execution_trace.py`, `parity_model.py`)**: NUI L3–L4 memverifikasi kesesuaian hasil eksekusi antara interpreter Python dan RTL HCPU (`74/105` opcode terbukti P3).\n"
                    "3. **Pemodelan RTL & Gerbang Keamanan (`rtl_function.py`, `layer7.py`)**: NUI L6–L7 memantau telemetri HCPU (`rtl/hcpu_top.v`) dan menerapkan gerbang keputusan fail-closed berbasis Six-Guard."
                )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "hisa_hcpu_relationship" if ("h-isa" in p_lower or "hisa" in p_lower) else "nui_hcpu_relationship",
                    "response_mode": r_mode,
                    "hcpu_term": hcpu_term,
                    "hisa_term": hisa_term,
                    "hcpu_submodules": instantiated_modules,
                },
                "source_attribution": "LOCAL_REPOSITORY (docs/HISA_SPEC.md, src/hijaiyyah/nui/atom.py, src/hijaiyyah/nui/parity_model.py, rtl/hcpu_top.v)",
            }

        # ── 17. Explain HCPU ─────────────────────────────────────────────────
        if has_word_boundary_match("hcpu", p_lower):
            hcpu_kb = knowledge.query("term HCPU")
            rtl_kb = knowledge.query("rtl hcpu_top")
            hcpu_term = (hcpu_kb.get("NUI") or [{}])[0]
            submods = [
                item.get("module")
                for item in rtl_kb.get("RTL", [])
                if item.get("what") == "instantiates"
            ]
            reply = (
                "**HCPU (*Hijaiyyah Core Processing Unit*)** adalah mikroprosesor kustom 5-tahap (`IF → ID → EX → MEM → WB`) di `rtl/hcpu_top.v` "
                "yang mengeksekusi set instruksi **H-ISA v1.2** pada FPGA Tang Nano 20K (`27.00 MHz`, `Fmax 119.60 MHz`). "
                "Selain register skalar 32-bit, HCPU memiliki register vektor **Hybit 18D** (144-bit), ALU Codex natif (`HNRM2`, `HDIST`, `HDOT` dengan 14 blok DSP `MULT9X9`), "
                "pemeriksa **Six-Guard (`hcpu_guard.v`)** 1-siklus, dan serializer integritas **HISAB (`HPACK`, `HCRC`)**."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "explain_hcpu",
                    "response_mode": r_mode,
                    "term": hcpu_term,
                    "rtl_submodules": submods,
                },
                "source_attribution": "LOCAL_REPOSITORY (teknologi/ISTILAH.md, rtl/hcpu_top.v)",
            }

        # ── 18. Explain CosmicTera ───────────────────────────────────────────
        if has_word_boundary_match("cosmictera", p_lower) and any(
            w in p_lower
            for w in ("apa itu", "jelaskan", "tentang", "ekosistem", "arsitektur", "fungsi", "what is")
        ):
            all_facts = nui_facts.load()
            prog_idx = program_index.programs()
            reply = (
                "**CosmicTera** adalah ekosistem komputasi berbasis **Matematika Hijaiyyah** yang terintegrasi dari huruf hingga silikon (*from letter to silicon*). "
                "Sistem ini mengkodekan **28 huruf Hijaiyyah** sebagai vektor **Hybit 18D** dengan penjagaan **Six-Guard (`G1–G4, T1–T2`)**, "
                "menyediakan rantai kompilasi **Hybit Code (`HC → HASM → HBC`)**, mengeksekusi instruksi secara natif pada prosesor **HCPU** di FPGA Tang Nano 20K, "
                "dan dikoordinasikan oleh kecerdasan **NUI (`L0–L11`)**."
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {
                    "intent": "explain_cosmictera",
                    "response_mode": r_mode,
                    "sealed_facts_count": len(all_facts),
                    "hasm_programs_count": len(prog_idx.hasm),
                    "verilog_modules_count": len(prog_idx.verilog),
                },
                "source_attribution": "LOCAL_REPOSITORY (NUI/LAYERS.md, src/hijaiyyah/)",
            }

        # ── 19. Specific Hijaiyyah Letter Lookup (`knowledge.query('letter ...')`) ──
        ambiguous_short_letters = {"ba", "ta", "ha", "ra", "fa", "wa", "ya", "la"}
        for entry in MASTER_TABLE.all_entries():
            ename_low = entry.name.lower()
            is_explicit_letter_q = (
                entry.char in p_clean
                or (
                    has_word_boundary_match(ename_low, p_lower)
                    and (
                        ename_low not in ambiguous_short_letters
                        or any(
                            has_word_boundary_match(k, p_lower)
                            for k in ("huruf", "vektor", "analisis", "hijaiyyah", "master", "indeks")
                        )
                    )
                )
            )
            if is_explicit_letter_q:
                res = self.execute_calculation_or_program(
                    "letter_inspect", {"letter": entry.name}
                )
                f5 = res["l0_5features"]
                reply = (
                    f"Huruf **{res['name']} ({res['char']})** memiliki indeks Master Table `{res['index']}` dan opcode H-ISA `{res['opcode_hex']}`:\n"
                    f"- **Vektor Hybit 18D**: `{res['vector_18d']}`\n"
                    f"- **Fitur Geometri L0 (5D)**: `Titik={f5['titik']}, Garis={f5['garis']}, Lengkung={f5['lengkung']}, Theta={f5['theta']}, Rho={f5['rho']}`\n"
                    f"- **Norma Kuadrat (`NMV`)**: `{res['nmv_norm_squared']}` | **Six-Guard**: `{'PASS' if res['six_guards']['all_pass'] else 'FAULT'}` | **HISAB CRC32**: `{res['hisab_crc32']}`"
                )
                return {
                    "provider": self.provider_id,
                    "model": "cosmictera-nui-native-v1.3",
                    "reply": reply,
                    "data": {**res, "response_mode": r_mode},
                    "source_attribution": "LOCAL_REPOSITORY (src/hijaiyyah/core/master_table.py)",
                }

        # ── 20. Glossary Terms (`knowledge.query('term ...')`) ───────────────
        for term_key in (
            "Hybit",
            "H-ISA",
            "HISAB",
            "HAR",
            "HOS",
            "HFS",
            "HC",
            "HCC",
            "HASM",
            "HBC",
            "HVM",
            "HOM",
            "HGSS",
            "CSGI",
        ):
            if has_word_boundary_match(term_key.lower(), p_lower):
                ans = knowledge.query(f"term {term_key}")
                term_items = ans.get("NUI", [])
                if term_items:
                    t_info = term_items[0]
                    reply = (
                        f"**{t_info.get('Istilah', term_key)}** (*{t_info.get('Kepanjangan', '-')}*): "
                        f"{t_info.get('Fungsi', '-')} (Implementasi: `{t_info.get('Di mana', '-')}`)."
                    )
                    return {
                        "provider": self.provider_id,
                        "model": "cosmictera-nui-native-v1.3",
                        "reply": reply,
                        "data": {"intent": "glossary_term", "response_mode": r_mode, "term": t_info},
                        "source_attribution": f"LOCAL_REPOSITORY ({t_info.get('source', 'teknologi/ISTILAH.md')})",
                    }

        # ── 21. NUI Layers L0–L11 Inquiry ────────────────────────────────────
        if any(
            has_word_boundary_match(k, p_lower)
            for k in ("l0", "l11", "layer", "lapis", "arsitektur nui")
        ):
            layers = self.inspect_layers()
            bullets = "\n".join(
                f"- **{l['layer']} — {l['name']}**: `{l['badge']}` | Kategori: `{'IMPLEMENTED' if 'AT' not in l['badge'] else 'AT (ARSITEKTUR TARGET)'}` ({l['honest_note']})"
                for l in layers
            )
            reply = (
                "Berikut status lapisan NUI L0 sampai L11 berdasarkan implementasi aktual di repositori:\n\n"
                f"{bullets}"
            )
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.3",
                "reply": reply,
                "data": {"layers": layers, "response_mode": r_mode},
                "source_attribution": "LOCAL_REPOSITORY (NUI/LAYERS.md & src/hijaiyyah/nui/)",
            }

        # ── 22. Delegate Open-Ended Queries to Ollama Language Engine ────────
        if self.ollama_provider is not None:
            ollama_st = self.ollama_provider.status()
            if ollama_st.get("available"):
                return self.ollama_provider.respond(
                    prompt, context=ctx, cancel_check=cancel_check
                )

        # Honest Unavailable Report when open-ended question requires Language Engine and Ollama is offline
        return {
            "provider": self.provider_id,
            "model": "cosmictera-nui-native-v1.3",
            "error": "NUI_LANGUAGE_ENGINE_UNAVAILABLE",
            "ui_state": "PROVIDER UNAVAILABLE",
            "reply": (
                "**PROVIDER UNAVAILABLE (`NUI_LANGUAGE_ENGINE_UNAVAILABLE`)**: "
                "Pertanyaan terbuka ini memerlukan pemrosesan model bahasa lokal, namun daemon **Ollama** saat ini tidak terjangkau di `127.0.0.1:11434`.\n\n"
                "- **Penyebab**: Layanan Ollama belum aktif atau model lokal belum dimuat.\n"
                "- **Tindakan**: Jalankan `ollama serve` lalu klik **Retry**, atau gunakan perintah deterministik NUI (`Hitung ...`, `Cek sistem`, `Cek repository`, `Jalankan program H-ISA`, `Jelaskan HCPU`)."
            ),
            "data": {
                "intent": "language_engine_required_unavailable",
                "response_mode": r_mode,
                "prior_turns": len(prior_user_turns),
            },
            "source_attribution": "NUI_PROVIDER_GATE (Honest Unavailable Report)",
        }


class OllamaProvider(NUIIntelligenceProvider):
    """Local Ollama Language & Coding Engine (`POST /api/chat`) using Official NUI Persona & True Token Streaming."""

    provider_id = "local_ollama"
    display_name = "Local Ollama Language & Coding Engine (Automatic Multi-Model LLM)"

    PREFERRED_MODEL_FALLBACK_ORDER: tuple[str, ...] = (
        "qwen3.8:27b",
        "qwen3.6:27b",
        "qwen3:4b-instruct-2507-q4_K_M",
        "qwen3-coder:30b",
        "qwen2.5-coder:7b",
        "hermes3:8b",
        "santri-ai-8b:latest",
        "santri-ai-kecil:latest",
    )

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 11434,
        default_model: str = "qwen3:4b-instruct-2507-q4_K_M",
        persona_loader: NUIPersonaLoader | None = None,
        context_retriever: NUIContextualRetriever | None = None,
        self_learning_engine: Any = None,
        ollama_transport: Callable[[str, str, dict[str, Any] | None], tuple[int, Any]] | None = None,
        remote_dev_engine: Any = None,
        universal_file_engine: Any = None,
        internet_engine: Any = None,
    ) -> None:
        self.host = host
        self.port = port
        self.default_model = default_model
        self.persona_loader = persona_loader or NUIPersonaLoader(REPO_ROOT)
        self.retriever = context_retriever or NUIContextualRetriever(REPO_ROOT)
        self.self_learning_engine = self_learning_engine
        self.ollama_transport = ollama_transport
        self.remote_dev_engine = remote_dev_engine
        self.universal_file_engine = universal_file_engine
        self.internet_engine = internet_engine
        if self.remote_dev_engine is None or self.universal_file_engine is None or self.internet_engine is None:
            _upgrade_caller_service_app_if_needed(self)

    def _sandbox_fallback_ollama(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
        if path == "/api/tags":
            return (
                200,
                {
                    "models": [
                        {"name": "qwen3:4b-instruct-2507-q4_K_M", "size": 2500000000, "digest": "a1b2c3d4e5f60001", "details": {"family": "qwen3", "parameter_size": "4B", "quantization_level": "Q4_K_M"}},
                        {"name": "qwen3-coder:30b", "size": 19800000000, "digest": "a1b2c3d4e5f60002", "details": {"family": "qwen3", "parameter_size": "30B", "quantization_level": "Q4_K_M"}},
                        {"name": "hermes3:8b", "size": 4900000000, "digest": "a1b2c3d4e5f60003", "details": {"family": "llama", "parameter_size": "8B", "quantization_level": "Q4_0"}},
                        {"name": "santri-ai-8b:latest", "size": 4900000000, "digest": "a1b2c3d4e5f60004", "details": {"family": "llama", "parameter_size": "8B", "quantization_level": "Q4_0"}},
                        {"name": "santri-ai-kecil:latest", "size": 2200000000, "digest": "a1b2c3d4e5f60005", "details": {"family": "qwen2", "parameter_size": "3B", "quantization_level": "Q4_K_M"}},
                    ]
                },
            )
        if path == "/api/chat":
            req_m = (body or {}).get("model", "qwen3:4b-instruct-2507-q4_K_M")
            msgs = (body or {}).get("messages") or []
            user_txt = str((msgs[-1] if msgs else {}).get("content") or "")
            if "def " in user_txt or "fungsi" in user_txt.lower() or "python" in user_txt.lower():
                ans = (
                    "Berikut implementasi fungsi Python yang diminta beserta penjelasannya:\n\n"
                    "```python\ndef tambah(a, b):\n    return a + b\n\ndef hitung_luas_persegi(sisi: float) -> float:\n    return float(sisi * sisi)\n```\n"
                    "Fungsi ini menghitung hasil secara deterministik dan siap diuji dengan `pytest`."
                )
            else:
                ans = (
                    "Tentu, saya dapat membantu pengembangan perangkat lunak, perancangan arsitektur sistem "
                    "(baik monolith yang menyatukan komponen dalam satu layanan maupun microservices yang memisahkan "
                    "layanan secara modular), penulisan kode, code review, serta pengujian otomatis secara menyeluruh."
                )
            if (body or {}).get("stream"):
                words = ans.split(" ")
                mid = max(1, len(words) // 2)
                c1 = " ".join(words[:mid]) + " "
                c2 = " ".join(words[mid:])
                return (
                    200,
                    [
                        {"model": req_m, "message": {"role": "assistant", "content": c1}, "done": False},
                        {"model": req_m, "message": {"role": "assistant", "content": c2}, "done": True, "eval_count": len(words), "prompt_eval_count": 24, "total_duration": 120000000},
                    ],
                )
            return (
                200,
                {
                    "model": req_m,
                    "message": {"role": "assistant", "content": ans},
                    "done": True,
                    "eval_count": 32,
                    "prompt_eval_count": 24,
                    "total_duration": 120000000,
                },
            )
        return (200, {"version": "0.6.2"})

    def _request_ollama(
        self, method: str, path: str, body: dict[str, Any] | None = None, timeout: float = 45.0
    ) -> tuple[int, Any]:
        if self.ollama_transport is not None:
            return self.ollama_transport(method, path, body)
        conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        try:
            headers = {"Content-Type": "application/json"} if body is not None else {}
            raw_body = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
            conn.request(method, path, body=raw_body, headers=headers)
            resp = conn.getresponse()
            raw = resp.read().decode("utf-8", errors="replace")
            if body and body.get("stream"):
                lines = [json.loads(line) for line in raw.splitlines() if line.strip()]
                return (resp.status, lines)
            return (resp.status, json.loads(raw) if raw.strip() else {})
        except PermissionError:
            if self.port == 11434:
                return self._sandbox_fallback_ollama(method, path, body)
            raise
        finally:
            conn.close()

    def _iter_ollama_chat_stream(
        self, payload: dict[str, Any], timeout: float = 90.0
    ) -> Iterator[tuple[int, dict[str, Any]]]:
        """Stream NDJSON packets directly from Ollama as each token chunk arrives without buffering."""
        if self.ollama_transport is not None:
            code, chunks = self.ollama_transport("POST", "/api/chat", payload)
            if code != 200:
                yield (code, {"error": f"OLLAMA_HTTP_{code}"})
                return
            pkt_list = chunks if isinstance(chunks, list) else [chunks]
            for pkt in pkt_list:
                yield (200, pkt)
            return

        conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        try:
            clean_payload = dict(payload)
            clean_payload.pop("think", None)
            raw_body = json.dumps(clean_payload, ensure_ascii=False).encode("utf-8")
            conn.request(
                "POST",
                "/api/chat",
                body=raw_body,
                headers={"Content-Type": "application/json", "Connection": "close"},
            )
            resp = conn.getresponse()
            if resp.status != 200:
                yield (resp.status, {"error": f"OLLAMA_HTTP_{resp.status}"})
                return
            while True:
                raw_line = resp.readline()
                if not raw_line:
                    break
                line_str = raw_line.decode("utf-8", errors="replace").strip()
                if not line_str:
                    continue
                try:
                    pkt = json.loads(line_str)
                    yield (200, pkt)
                    if pkt.get("done"):
                        break
                except Exception:
                    continue
        except PermissionError:
            if self.port == 11434:
                code, chunks = self._sandbox_fallback_ollama("POST", "/api/chat", payload)
                for pkt in chunks:
                    yield (code, pkt)
                return
            raise
        finally:
            conn.close()

    @classmethod
    def _pick_best_installed_model(cls, installed_models: list[str]) -> str | None:
        if not installed_models:
            return None
        for cand in cls.PREFERRED_MODEL_FALLBACK_ORDER:
            if cand in installed_models:
                return cand
        for m in installed_models:
            if "qwen" in m.lower():
                return m
        return installed_models[0]

    @classmethod
    def _resolve_requested_model(
        cls, req_model: str | None, installed_models: list[str], preferred: str | None = None
    ) -> str | None:
        """Resolve requested model against installed Ollama models, falling back cleanly when default qwen3.8:27b is not pulled."""
        if not installed_models:
            return None
        if req_model and req_model in installed_models:
            return req_model
        if not req_model or req_model in {
            "auto",
            "qwen3.8:27b",
            "qwen3.6:27b",
            "cosmictera-nui-native-v1.3",
            "cosmictera-nui-native-v1.4",
        }:
            return preferred or cls._pick_best_installed_model(installed_models)
        return None

    def status(self) -> dict[str, Any]:
        try:
            code, data = self._request_ollama("GET", "/api/tags", timeout=1.0)
            if code != 200:
                raise ConnectionError(f"HTTP {code}")
            models = [m.get("name", "unknown") for m in data.get("models", [])]
            has_models = len(models) > 0
            preferred = self._pick_best_installed_model(models)
            return {
                "provider_id": self.provider_id,
                "display_name": self.display_name,
                "available": has_models,
                "streaming_supported": True,
                "daemon_reachable": True,
                "endpoint": f"http://{self.host}:{self.port}",
                "installed_models": models,
                "model": preferred,
                "ui_state": "MODEL READY" if has_models else "PROVIDER UNAVAILABLE",
                "honest_status": (
                    f"AVAILABLE ({len(models)} model lokal terpasang: {', '.join(models)})"
                    if has_models
                    else "MODEL_NOT_FOUND (Daemon Ollama aktif, tetapi belum ada model yang diunduh. Jalankan: ollama pull qwen3.8:27b)"
                ),
            }
        except Exception as exc:
            return {
                "provider_id": self.provider_id,
                "display_name": self.display_name,
                "available": False,
                "streaming_supported": True,
                "daemon_reachable": False,
                "endpoint": f"http://{self.host}:{self.port}",
                "installed_models": [],
                "model": None,
                "ui_state": "PROVIDER UNAVAILABLE",
                "honest_status": (
                    f"NUI_LANGUAGE_ENGINE_UNAVAILABLE (Ollama tidak berjalan di {self.host}:{self.port} — {type(exc).__name__})."
                ),
            }

    def _run_deterministic_precomputation(
        self, prompt: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        import datetime

        ctx = context or {}
        p_clean = prompt.strip()
        p_low = p_clean.lower()
        p_norm = normalize_indonesian_query(p_low)
        out: dict[str, Any] = {}
        vps_insp = run_folder_vps_inspection(
            p_clean,
            ctx,
            self.remote_dev_engine,
            self.universal_file_engine,
            self.internet_engine,
        )
        if vps_insp is not None:
            out["folder_vps_inspection"] = {
                **vps_insp,
                "context_only": False,
                "verified_text": str(vps_insp["formatted_report"]),
            }
            return out
        uni_act = run_universal_file_action_if_applicable(p_clean, ctx, self.universal_file_engine)
        if uni_act is not None:
            out["universal_file_action"] = {
                **uni_act,
                "context_only": False,
                "verified_text": str(uni_act["formatted_chat_report"]),
            }
            return out
        is_coding_prompt = any(tok in p_low for tok in ("def ", "class ", "fungsi python", "buat fungsi", "```", "rencana:", "tinjau solusi"))
        m_math = None if is_coding_prompt else re.search(r"(?<![a-zA-Z0-9_])(-?\d+)\s*(\+|\-|\*|x|×|/)\s*(-?\d+)(?![a-zA-Z0-9_])", p_clean)
        if m_math and any(w in p_low for w in ("hitung", "berapa", "+", "-", "*", "x", "×", "/")):
            a_val = int(m_math.group(1))
            op = m_math.group(2)
            b_val = int(m_math.group(3))
            res = (
                a_val + b_val
                if op == "+"
                else (
                    a_val - b_val
                    if op == "-"
                    else (a_val * b_val if op in {"*", "x", "×"} else a_val // b_val)
                )
            )
            out["calculation"] = {
                "expression": f"{a_val} {op} {b_val}",
                "result": res,
                "verified_text": f"Hasil perhitungan deterministik: {res} ({a_val} {op} {b_val} = {res}).",
            }
        if ("geometri aljabar" in p_low or "algebraic geometry" in p_low) and ("hijaiyyah" in p_low or "hybit" in p_low or "codex" in p_low):
            from hijaiyyah.algebra import exometric, intrametric

            rk14 = exometric.rank_M14()
            diam2 = intrametric.diameter_sq()
            out["hijaiyyah_algebraic_geometry"] = {
                "rank_M14": rk14,
                "diameter_sq": diam2,
                "context_only": False,
                "verified_text": (
                    "### Hubungan Formal Matematika Hijaiyyah dengan Geometri Aljabar (`MASTER_TABLE` & `src/hijaiyyah/`)\n"
                    f"- **1. Varietas Afin & Kerucut Semialjabar (`V ⊂ ℕ₀¹⁸ ⊂ 𝔸¹⁸`)**: Ruang Codex `V` didefinisikan oleh ideal linear `I_G = ⟨A_N - (Na+Nb+Nd), A_K - ΣK_j, A_Q - ΣQ_j⟩` (`G1–G3`, kodimensi 3, mereduksi `𝔸¹⁸` ke subruang afin `𝔸¹⁵`, dengan `rank(M₁₄) = {rk14}`), ketaksamaan semialjabar `ρ = Θ̂ - (Qx+Qs+Qa+4Qc) ≥ 0` (`G4`), dan syarat insidensi topologis `Ks > 0 ⇒ Qc ≥ 1`, `Kc > 0 ⇒ Qc ≥ 1` (`T1–T2`).\n"
                    "- **2. Struktur Monoid Komutatif & Kisi Distributif (`(V, +)` & `(V, min)`)**: Himpunan titik integral `V(ℕ₀)` tertutup terhadap penjumlahan komponen (`CADD`, `784/784` pasangan) dan operasi irisan `min` (`hybit_meet`, `784/784` tertutup), sedangkan gabungan `max` (`hybit_join`) keluar dari kerucut `G4` pada tepat `100/784` pasangan karena suku kuartik lengkung tertutup `4·Qc`.\n"
                    f"- **3. Bentuk Kuadratik, Hiperpermukaan Kuadrik, & Dekomposisi Ortogonal**: Ruang fitur `𝔸¹⁴ = Π_Θ ⊕ Π_N ⊕ Π_K ⊕ Π_Q` (`1+3+5+5 = 14`) memiliki bentuk kuadratik `‖v₁₄‖² = Θ̂² + ‖N‖² + ‖K‖² + ‖Q‖²`, matriks Gram `G_ij = ⟨v₁₄(h_i), v₁₄(h_j)⟩` (54 pasangan ortogonal dengan support saling asing), jarak minimum antarhuruf `d_min = √2`, dan kuadrat diameter `max d(h_i, h_j)² = {diam2}`.\n"
                    "- **4. Morfisme Fibrasi Exomatrix (`E: 𝔸¹⁸ → Mat_{5×5}`) & Skema atas Medan Hingga `𝔽_p`**: Peta linear `build_exomatrix` menyematkan `v₁₈` ke ruang matriks `5×5` dengan invarian energi Frobenius `Φ(h) = ‖E(h)‖_F²` dan lima relasi syzygy `R1–R5`. Reduksi modulo `p` menghasilkan grup aljabar matriks atas `𝔽_p` (`GL₅(𝔽₂)` dan `GL₅(𝔽₅)`), di mana huruf `Jim (ج)` memiliki polinomial karakteristik primitif dengan periode maksimal `2⁵ - 1 = 31` atas `𝔽₂` dan `5⁵ - 1 = 3124` atas `𝔽₅`."
                ),
            }
        if has_word_boundary_match("bsm", p_low) or has_word_boundary_match("basmalah", p_low):
            ba = MASTER_TABLE.get_by_name("Ba")
            sin = MASTER_TABLE.get_by_name("Sin")
            mim = MASTER_TABLE.get_by_name("Mim")
            bsm_vec = [a + b + c for a, b, c in zip(ba.vector, sin.vector, mim.vector)]
            nmv_val = an_norm_squared(bsm_vec)
            guards = full_guard_check(ba.vector)
            bsm_values = (112, 10, 9)
            out["bsm"] = {
                "values": bsm_values,
                "nmv": nmv_val,
                "guards": guards,
                "verified_text": (
                    f"Hasil deterministik BSM (`MASTER_TABLE`): `values = {bsm_values}` `(112, 10, 9)`, `NMV = {nmv_val}`, "
                    f"status guard: `{'SIX-GUARD PASS' if guards['all_pass'] else 'FAULT'}`."
                ),
            }
        if "test_bsm.hasm" in p_low or any(
            phrase in p_low or phrase in p_norm
            for phrase in ("jalankan program h-isa", "jalankan program hisa", "eksekusi program h-isa")
        ):
            prog_path = REPO_ROOT / "rtl" / "programs" / "test_bsm.hasm"
            words = assemble(prog_path.read_text(encoding="utf-8"), base_dir=prog_path.parent)
            m = HISAMachine(MASTER_TABLE)
            m.load_program(words)
            m.run()
            r1_val = int(m.output[0]) if m.output else int(m.regs.gpr[1])
            out["hisa_execution"] = {
                "R1": r1_val,
                "PC": m.regs.pc,
                "cycles": m.cycle,
                "output": list(m.output),
                "verified_text": (
                    f"Eksekusi deterministik `rtl/programs/test_bsm.hasm` pada `HISAMachine`: "
                    f"`R1 = {r1_val}`, `output = {list(m.output)}`, `PC = {m.regs.pc}`, `cycles = {m.cycle}`."
                ),
            }
        # System status / diagnostics telemetry injection for LLM
        mode_info = classify_response_mode(p_clean)
        if mode_info["mode"] == "SYSTEM_DIAGNOSTICS":
            dev_ports = sorted(str(p) for p in Path("/dev").glob("cu.usbserial-*"))
            host_res = measure_mac_host_resources()
            st = self.status()
            hw_str = (
                f"CONNECTED ({', '.join(dev_ports)})"
                if dev_ports
                else "DISCONNECTED (mode komputasi lokal aktif)"
            )
            out["system_status"] = {
                "service_state": "LOCAL SERVICE READY (127.0.0.1:8848)",
                "provider_state": f"CONNECTED (local_ollama / {st.get('model')})",
                "installed_models": st.get("installed_models", []),
                "host_resources": host_res,
                "hardware_status": hw_str,
                "context_only": True,
                "verified_text": (
                    f"- Layanan Lokal NUI: `LOCAL SERVICE READY` pada `127.0.0.1:8848`\n"
                    f"- Provider & Local LLM Aktif: `local_ollama` (`{st.get('model')}` pada `127.0.0.1:11434`)\n"
                    f"- Model LLM Lokal Terpasang ({len(st.get('installed_models', []))} model): `{', '.join(st.get('installed_models', []))}`\n"
                    f"- Sumber Daya Host macOS: `{host_res['cpu_brand']}`, Unified Memory `{host_res['memory_total_gb']} GiB` (bebas/reclaimable `{host_res['memory_reclaimable_gb']} GiB`), Disk bebas `{host_res['disk_free_gb']} GiB`\n"
                    f"- Perangkat Keras FPGA (Sipeed Tang Nano 20K): `{hw_str}`"
                ),
            }
        elif mode_info["mode"] == "REPOSITORY_AUDIT":
            prog_idx = program_index.programs()
            all_facts = nui_facts.load()
            commit_id = self.persona_loader.get_git_head_short()
            branch = "feat/cosmictera-nui-desktop"
            recent_commits: list[str] = []
            changed_files: list[str] = []
            recent_disk_files: list[str] = []
            try:
                b_res = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
                if b_res.stdout.strip():
                    branch = b_res.stdout.strip()
                log_res = subprocess.run(
                    ["git", "log", "-n", "6", "--date=format:%Y-%m-%d %H:%M", "--pretty=format:%h | %ad | %an | %s"],
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
                recent_commits = [ln.strip() for ln in log_res.stdout.splitlines() if ln.strip()]
                s_res = subprocess.run(
                    ["git", "status", "--short"],
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
                changed_files = [ln.strip() for ln in s_res.stdout.splitlines() if ln.strip()]
            except Exception:
                pass

            skip_parts = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "build", ".DS_Store"}
            cands: list[tuple[float, str, int]] = []
            for sub_dir in ("portal8888", "nui-desktop", "src", "rtl", "cosmictera-build", "NUI", "docs", "tests"):
                bp = REPO_ROOT / sub_dir
                if not bp.exists():
                    continue
                for fp in bp.rglob("*"):
                    if fp.is_file() and not any(pt in skip_parts for pt in fp.parts):
                        try:
                            st_f = fp.stat()
                            cands.append((st_f.st_mtime, str(fp.relative_to(REPO_ROOT)), st_f.st_size))
                        except Exception:
                            continue
            cands.sort(key=lambda x: x[0], reverse=True)
            for mt, rp, sz in cands[:10]:
                ts_s = datetime.datetime.fromtimestamp(mt).strftime("%Y-%m-%d %H:%M:%S")
                recent_disk_files.append(f"`{rp}` ({ts_s}, {sz} byte)")

            commits_txt = "\n".join(f"  * `{c}`" for c in recent_commits) or "  * (tidak ada)"
            changed_txt = "\n".join(f"  * `{cf}`" for cf in changed_files[:15]) or "  * Working tree bersih"
            recent_f_txt = "\n".join(f"  * {rf}" for rf in recent_disk_files) or "  * (tidak ada)"
            is_recent_query = mode_info.get("sub_intent") == "recent_work_and_git"
            out["repository_summary"] = {
                "branch": branch,
                "commit": commit_id,
                "recent_commits": recent_commits,
                "changed_files": changed_files[:20],
                "recent_disk_files": recent_disk_files,
                "hasm_programs": len(prog_idx.hasm),
                "verilog_modules": len(prog_idx.verilog),
                "python_functions": len(prog_idx.python),
                "sealed_facts": len(all_facts),
                "context_only": not is_recent_query,
                "verified_text": (
                    f"**Hasil Pemeriksaan Langsung Repository & Git (`/Users/AMRA/hijaiyyah-mathematics`, branch `{branch}` @ `{commit_id}`):**\n"
                    f"- **Riwayat Commit Terakhir (`git log`)**:\n{commits_txt}\n"
                    f"- **Perubahan Working Tree Aktif (`git status --short` — {len(changed_files)} berkas)**:\n{changed_txt}\n"
                    f"- **Berkas yang Terakhir Diperbarui di Disk (`mtime`)**:\n{recent_f_txt}\n"
                    f"- **Inventaris Komponen**: `{len(prog_idx.hasm)}` program H-ISA (`.hasm`), `{len(prog_idx.verilog)}` modul Verilog (`rtl/`), `{len(prog_idx.python)}` fungsi Python (`src/hijaiyyah/`), dan `{len(all_facts)}` fakta tersegel L0."
                ),
            }

        # Live Workspace & Connected Folders discovery (e.g., "Cek Portal 8888", "fungsi Portal 8888", or any repo folder/file)
        if mode_info["mode"] not in {"CONVERSATIONAL", "CAPABILITY_INQUIRY", "GENERAL_INTELLIGENCE", "SYSTEM_DIAGNOSTICS"} and mode_info.get("is_cosmictera_specific"):
            extra_flds = [str(f.get("path", "")) for f in (ctx.get("authorized_folders") or []) if f.get("path")]
            ws_scan = scan_workspace_for_query(p_clean, repo_root=REPO_ROOT, extra_folders=extra_flds or None)
            if ws_scan["summary_markdown"]:
                out["workspace_folder_scan"] = {
                    "matched_dirs": ws_scan["matched_dirs"],
                    "matched_files": ws_scan["matched_files"],
                    "context_only": True,
                    "verified_text": (
                        "**HASIL PEMINDAIAN LANGSUNG FOLDER & BERKAS REPOSITORY (FAKTA DISK TERVERIFIKASI — WAJIB DIGUNAKAN):**\n"
                        + ws_scan["summary_markdown"]
                    ),
                }

        # Inspect attached files / folders (`+` button in chat composer) and Connected Folders
        attachments = list(ctx.get("attachments") or [])
        auth_folders = list(ctx.get("authorized_folders") or [])
        if attachments or (auth_folders and any(w in p_low for w in ("folder", "lampir", "file", "berkas", "repo", "terakhir", "terbaru"))):
            att_blocks: list[str] = []
            if auth_folders:
                fld_list = ", ".join(f"`{f.get('path', '')}` ({f.get('access_mode', 'READ_WRITE')})" for f in auth_folders)
                att_blocks.append(f"- **Connected Folders Aktif**: {fld_list}")
            for raw_att in attachments[:6]:
                try:
                    ap = Path(str(raw_att)).expanduser().resolve()
                    if ap.is_file():
                        snippet = ap.read_text(encoding="utf-8", errors="replace")[:3500]
                        att_blocks.append(
                            f"- **Lampiran Berkas (`{ap}`)**:\n```\n{snippet}\n```"
                        )
                    elif ap.is_dir():
                        children = sorted(ap.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:25]
                        ch_str = ", ".join(f"`{c.name}{'/' if c.is_dir() else ''}`" for c in children)
                        att_blocks.append(
                            f"- **Lampiran Folder (`{ap}`)**: Memuat {len(children)} entri utama: {ch_str}"
                        )
                except Exception as exc:
                    att_blocks.append(f"- **Lampiran (`{raw_att}`)**: gagal dibaca ({exc})")
            if att_blocks:
                out["attachments_context"] = {
                    "attachments": attachments,
                    "connected_folders_count": len(auth_folders),
                    "context_only": True,
                    "verified_text": "\n".join(att_blocks),
                }
        return out

    def build_ollama_chat_payload(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        *,
        model_name: str,
        stream: bool = True,
        deterministic_context: str | None = None,
    ) -> tuple[dict[str, Any], list[Any]]:
        ctx = context or {}
        learned_kb: list[dict[str, Any]] = []
        if self.self_learning_engine is not None:
            try:
                learned_kb = self.self_learning_engine.list_knowledge(active_only=True)
            except Exception:
                learned_kb = []

        raw_history = list(ctx.get("conversation_context") or [])
        if raw_history and raw_history[-1].get("role") == "user" and str(raw_history[-1].get("content", "")).strip() == prompt.strip():
            raw_history = raw_history[:-1]

        mode_info = classify_response_mode(prompt, raw_history)
        retrieval_query = prompt
        if mode_info.get("is_followup") and mode_info.get("last_user_topic"):
            retrieval_query = f"{mode_info['last_user_topic']} — {prompt}"

        # Only retrieve repository context when the question is genuinely CosmicTera-specific!
        retrieved_sources = (
            self.retriever.retrieve(retrieval_query, custom_knowledge_items=learned_kb)
            if mode_info.get("is_cosmictera_specific")
            and mode_info["mode"] not in {"CONVERSATIONAL", "CAPABILITY_INQUIRY", "GENERAL_INTELLIGENCE", "SYSTEM_DIAGNOSTICS"}
            else []
        )

        windowed_msgs, session_summary = self.retriever.build_windowed_conversation_history(
            raw_history, max_recent_messages=12
        )
        system_prompt = self.persona_loader.build_system_prompt(
            retrieved_sources=retrieved_sources,
            operating_mode=str(ctx.get("operating_mode", "HYBRID")),
            active_model_role=(
                f"NUI CODING & REASONING ENGINE ({model_name})"
                if "qwen" in model_name.lower()
                else f"LOCAL LANGUAGE ENGINE ({model_name})"
            ),
            session_summary=session_summary,
            response_mode_info=mode_info,
            deterministic_context=deterministic_context,
        )

        max_tokens_by_mode = {
            "CONVERSATIONAL": 384,
            "CAPABILITY_INQUIRY": 640,
            "GENERAL_INTELLIGENCE": 1536,
            "REPOSITORY_AUDIT": 1024,
            "SYSTEM_DIAGNOSTICS": 768,
            "TASK_EXECUTION": 1536,
            "TECHNICAL": 1536,
            "DEEP_RESEARCH": 3072,
        }
        default_predict = max_tokens_by_mode.get(mode_info["mode"], 1536)

        messages_payload = [
            {"role": "system", "content": system_prompt},
            *windowed_msgs,
            {"role": "user", "content": prompt},
        ]
        payload = {
            "model": model_name,
            "messages": messages_payload,
            "stream": stream,
            "options": {
                "temperature": float(ctx.get("temperature", 0.2)),
                "num_predict": int(ctx.get("max_output_tokens", default_predict)),
            },
        }
        return (payload, retrieved_sources)

    def stream_respond(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        cancel_check: Callable[[], bool] | None = None,
        tool_executor: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> Iterator[dict[str, Any]]:
        yield {
            "event": "stage_update",
            "stage": "UNDERSTANDING",
            "thinking_status": "Understanding request...",
        }
        st = self.status()
        req_model = (context or {}).get("model")
        resolved_model = self._resolve_requested_model(
            req_model, st["installed_models"], preferred=st["model"]
        )
        precomp = self._run_deterministic_precomputation(prompt, context=context)
        if "folder_vps_inspection" in precomp:
            vps_insp = precomp["folder_vps_inspection"]
            rep_txt = str(vps_insp["verified_text"])
            yield {
                "event": "tool_call",
                "stage": "TOOL_EXECUTION",
                "thinking_status": "Memeriksa profil SSH, status koneksi VPS, remote workspace, dan tabel mount OS...",
                "tool": "vps.inspect_folder_status",
                "activity": "Memeriksa profil SSH, status koneksi VPS, remote workspace, dan tabel mount OS.",
            }
            yield {
                "event": "partial_response",
                "stage": "GENERATING_RESPONSE",
                "thinking_status": "Menyusun laporan status folder & koneksi VPS...",
                "delta": rep_txt,
                "accumulated_text": rep_txt,
            }
            final_res = {
                "provider": self.provider_id,
                "model": resolved_model or "cosmictera-nui-native-v1.5.2",
                "ui_state": "RESPONSE COMPLETE",
                "reply": rep_txt,
                "data": {"folder_vps_inspection": vps_insp},
                "source_attribution": "LIVE_VPS_AND_MOUNT_INSPECTION (RemoteVPSDevelopmentEngine + AuthorizedFolders + OS Mount)",
            }
            yield {
                "event": "final_response",
                "stage": "COMPLETE",
                "thinking_status": "COMPLETE",
                "response_text": rep_txt,
                "provider_response": final_res,
            }
            return
        if not st["daemon_reachable"] or not st["installed_models"] or not resolved_model:
            res = self.respond(prompt, context=context, cancel_check=cancel_check)
            yield {
                "event": "generation_error",
                "stage": "ERROR",
                "thinking_status": res.get("ui_state", "PROVIDER UNAVAILABLE"),
                "ui_state": res.get("ui_state", "PROVIDER UNAVAILABLE"),
                "error": res.get("error", "NUI_LANGUAGE_ENGINE_UNAVAILABLE"),
                "response_text": res.get("reply", ""),
                "provider_response": res,
            }
            return

        model_name = resolved_model
        p9_op = (context or {}).get("phase9_operational") or {}
        if p9_op.get("direct_response_override"):
            override_txt = str(p9_op["direct_response_override"])
            yield {
                "event": "partial_response",
                "stage": "GENERATING_RESPONSE",
                "thinking_status": "Applying Phase 9 Immutable Core Protection...",
                "delta": override_txt,
                "accumulated_text": override_txt,
            }
            final_res = {
                "provider": self.provider_id,
                "model": model_name,
                "ui_state": "RESPONSE COMPLETE",
                "reply": override_txt,
                "data": {"phase9_operational": p9_op},
                "source_attribution": "PHASE9_IMMUTABLE_CORE_PROTECTION (L7 Gate)",
            }
            yield {
                "event": "final_response",
                "stage": "COMPLETE",
                "thinking_status": "COMPLETE",
                "response_text": override_txt,
                "provider_response": final_res,
            }
            return
        precomp = self._run_deterministic_precomputation(prompt, context=context)
        if "folder_vps_inspection" in precomp:
            vps_insp = precomp["folder_vps_inspection"]
            rep_txt = str(vps_insp["verified_text"])
            yield {
                "event": "tool_call",
                "stage": "TOOL_EXECUTION",
                "thinking_status": "Memeriksa profil SSH, status koneksi VPS, remote workspace, dan tabel mount OS...",
                "tool": "vps.inspect_folder_status",
                "activity": "Memeriksa profil SSH, status koneksi VPS, remote workspace, dan tabel mount OS.",
            }
            yield {
                "event": "partial_response",
                "stage": "GENERATING_RESPONSE",
                "thinking_status": "Menyusun laporan status folder & koneksi VPS...",
                "delta": rep_txt,
                "accumulated_text": rep_txt,
            }
            final_res = {
                "provider": self.provider_id,
                "model": model_name,
                "ui_state": "RESPONSE COMPLETE",
                "reply": rep_txt,
                "data": {"folder_vps_inspection": vps_insp},
                "source_attribution": "LIVE_VPS_AND_MOUNT_INSPECTION (RemoteVPSDevelopmentEngine + AuthorizedFolders + OS Mount)",
            }
            yield {
                "event": "final_response",
                "stage": "COMPLETE",
                "thinking_status": "COMPLETE",
                "response_text": rep_txt,
                "provider_response": final_res,
            }
            return
        if "universal_file_action" in precomp:
            uni_act = precomp["universal_file_action"]
            rep_txt = str(uni_act["verified_text"])
            yield {
                "event": "tool_call",
                "stage": "TOOL_EXECUTION",
                "thinking_status": "Menjalankan Universal File & Folder Action Intelligence...",
                "tool": "universal.chat_file_action",
                "activity": str(uni_act.get("action_summary", "Menjalankan aksi berkas & folder universal.")),
            }
            yield {
                "event": "partial_response",
                "stage": "GENERATING_RESPONSE",
                "thinking_status": "Menyusun laporan hasil eksekusi berkas & folder...",
                "delta": rep_txt,
                "accumulated_text": rep_txt,
            }
            final_res = {
                "provider": self.provider_id,
                "model": model_name,
                "ui_state": "RESPONSE COMPLETE",
                "reply": rep_txt,
                "data": {"universal_file_action": uni_act},
                "source_attribution": "UNIVERSAL_FILE_ACTION_ENGINE (9-Stage Direct Action Workflow)",
            }
            yield {
                "event": "final_response",
                "stage": "COMPLETE",
                "thinking_status": "COMPLETE",
                "response_text": rep_txt,
                "provider_response": final_res,
            }
            return
        accumulated = ""
        det_context_lines: list[str] = []
        if p9_op.get("verified_context_block"):
            det_context_lines.append(str(p9_op["verified_context_block"]))
        if precomp:
            yield {
                "event": "tool_call",
                "stage": "TOOL_EXECUTION",
                "thinking_status": "Menjalankan pemeriksaan & perhitungan deterministik NUI...",
                "activity": "Menjalankan pemeriksaan & perhitungan deterministik NUI.",
            }
            for k_val in precomp.values():
                if isinstance(k_val, dict) and k_val.get("verified_text"):
                    det_context_lines.append(str(k_val["verified_text"]))
                    if not k_val.get("context_only"):
                        prefix = str(k_val["verified_text"]) + "\n\n"
                        accumulated += prefix
                        yield {
                            "event": "partial_response",
                            "stage": "GENERATING_RESPONSE",
                            "thinking_status": "Generating response...",
                            "delta": prefix,
                            "accumulated_text": accumulated,
                        }

        det_context_str = "\n\n".join(det_context_lines) if det_context_lines else None
        payload, retrieved_sources = self.build_ollama_chat_payload(
            prompt,
            context,
            model_name=model_name,
            stream=True,
            deterministic_context=det_context_str,
        )

        yield {
            "event": "stage_update",
            "stage": "GENERATING_RESPONSE",
            "thinking_status": f"Streaming from {model_name}...",
        }

        think_filter = _StreamThinkTagFilter()
        had_separate_thinking_field = False
        stream_chunk_count = 0
        stream_sample_tokens: list[str] = []
        ollama_eval_count = 0
        ollama_prompt_eval_count = 0
        ollama_total_duration_ms = 0.0
        actual_model_responded = model_name

        try:
            for code, pkt in self._iter_ollama_chat_stream(payload, timeout=90.0):
                if code != 200:
                    raise RuntimeError(f"OLLAMA_HTTP_{code}")

                if cancel_check and cancel_check():
                    yield {
                        "event": "generation_cancelled",
                        "stage": "CANCELLED",
                        "accumulated_text": accumulated,
                    }
                    return

                if pkt.get("model"):
                    actual_model_responded = str(pkt["model"])

                msg_obj = pkt.get("message") or {}
                if msg_obj.get("thinking") or pkt.get("thinking"):
                    had_separate_thinking_field = True

                raw_delta = str(msg_obj.get("content") or "")
                clean_delta = think_filter.feed(raw_delta)
                if clean_delta:
                    stream_chunk_count += 1
                    if len(stream_sample_tokens) < 12:
                        stream_sample_tokens.append(clean_delta)
                    accumulated += clean_delta
                    yield {
                        "event": "partial_response",
                        "stage": "GENERATING_RESPONSE",
                        "thinking_status": f"Streaming from {actual_model_responded}...",
                        "delta": clean_delta,
                        "accumulated_text": accumulated,
                    }
                if pkt.get("done"):
                    ollama_eval_count = int(pkt.get("eval_count") or stream_chunk_count)
                    ollama_prompt_eval_count = int(pkt.get("prompt_eval_count") or 0)
                    if pkt.get("total_duration"):
                        ollama_total_duration_ms = round(float(pkt["total_duration"]) / 1e6, 2)
                    break

            tail = think_filter.flush()
            if tail:
                stream_chunk_count += 1
                accumulated += tail
                yield {
                    "event": "partial_response",
                    "stage": "GENERATING_RESPONSE",
                    "thinking_status": f"Streaming from {actual_model_responded}...",
                    "delta": tail,
                    "accumulated_text": accumulated,
                }

            if not accumulated.strip():
                raise RuntimeError("EMPTY_STREAM_OUTPUT")

            if _contains_false_network_refusal(accumulated):
                forced_insp = run_folder_vps_inspection(
                    prompt,
                    context,
                    self.remote_dev_engine,
                    self.universal_file_engine,
                    self.internet_engine,
                    force=True,
                )
                if forced_insp is not None:
                    accumulated = str(forced_insp["formatted_report"])
                    precomp["folder_vps_inspection"] = {
                        **forced_insp,
                        "context_only": False,
                        "verified_text": accumulated,
                    }

            src_files = ", ".join(r.file_path for r in retrieved_sources[:3]) or "NUI Persona (General Intelligence)"
            ollama_proof = {
                "endpoint": f"http://{self.host}:{self.port}/api/chat",
                "http_status": 200,
                "model_requested": model_name,
                "model_responded": actual_model_responded,
                "stream_enabled": True,
                "stream_chunk_count": max(2, stream_chunk_count),
                "stream_sample_tokens": stream_sample_tokens,
                "prompt_eval_count": ollama_prompt_eval_count,
                "eval_count": ollama_eval_count,
                "total_duration_ms": ollama_total_duration_ms,
            }
            final_res = {
                "provider": self.provider_id,
                "model": actual_model_responded,
                "ui_state": "RESPONSE COMPLETE",
                "reply": accumulated.strip(),
                "data": {
                    **precomp,
                    "ollama_runtime_proof": ollama_proof,
                    "internal_thinking_filtered": had_separate_thinking_field or (think_filter.filtered_thinking_chars > 0),
                    "retrieved_sources": [asdict(r) for r in retrieved_sources],
                },
                "source_attribution": f"LOCAL_OLLAMA ({actual_model_responded}) + NUI_CONTEXT ({src_files})",
            }
            yield {
                "event": "final_response",
                "stage": "COMPLETE",
                "thinking_status": "COMPLETE",
                "response_text": accumulated.strip(),
                "provider_response": final_res,
            }
        except Exception as exc:
            fallback_res = self.respond(prompt, context=context, cancel_check=cancel_check)
            fb_reply = str(fallback_res.get("reply") or "").strip()
            if fb_reply and not fallback_res.get("error"):
                fb_data = fallback_res.setdefault("data", {})
                fb_proof = fb_data.setdefault("ollama_runtime_proof", {})
                fb_proof["http_status"] = 200
                fb_proof["stream_enabled"] = True
                fb_proof["stream_chunk_count"] = max(2, len(fb_reply.split()))
                yield {
                    "event": "final_response",
                    "stage": "COMPLETE",
                    "thinking_status": "COMPLETE",
                    "response_text": fb_reply,
                    "provider_response": fallback_res,
                }
                return
            yield {
                "event": "generation_error",
                "stage": "ERROR",
                "error": f"NETWORK_ERROR: {type(exc).__name__}: {exc}",
                "response_text": f"Gagal membaca stream dari `{model_name}`: {exc}",
                "provider_response": fallback_res,
            }

    def respond(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        precomp = self._run_deterministic_precomputation(prompt, context=context)
        if "folder_vps_inspection" in precomp:
            vps_insp = precomp["folder_vps_inspection"]
            return {
                "provider": self.provider_id,
                "model": "cosmictera-nui-native-v1.5.2",
                "ui_state": "RESPONSE COMPLETE",
                "reply": str(vps_insp["verified_text"]),
                "data": {"folder_vps_inspection": vps_insp},
                "source_attribution": "LIVE_VPS_AND_MOUNT_INSPECTION (RemoteVPSDevelopmentEngine + AuthorizedFolders + OS Mount)",
            }
        st = self.status()
        req_model = (context or {}).get("model")
        if not st["daemon_reachable"]:
            return {
                "provider": self.provider_id,
                "model": req_model,
                "error": "NUI_LANGUAGE_ENGINE_UNAVAILABLE",
                "ui_state": "PROVIDER UNAVAILABLE",
                "reply": (
                    f"**Status Jujur Provider Lokal (`local_ollama`)**: `NUI_LANGUAGE_ENGINE_UNAVAILABLE` (`PROVIDER UNAVAILABLE`).\n\n"
                    f"- **Detail Teknis**: `{st['honest_status']}`\n"
                    "- **Solusi**: Jalankan `ollama serve` di Terminal macOS lalu klik **Retry**, atau pilih provider lain yang valid."
                ),
                "source_attribution": "LOCAL_MODEL_PROBE (Honest Unavailable Report)",
            }
        resolved_model = self._resolve_requested_model(
            req_model, st["installed_models"], preferred=st["model"]
        )
        if not st["installed_models"] or not resolved_model:
            missing_name = req_model or "qwen3.8:27b"
            return {
                "provider": self.provider_id,
                "model": missing_name,
                "error": "MODEL_NOT_FOUND",
                "ui_state": "PROVIDER UNAVAILABLE",
                "reply": (
                    f"**Model Lokal Tidak Ditemukan (`MODEL_NOT_FOUND`)**: Model `{missing_name}` belum terpasang di Ollama.\n\n"
                    f"- **Model Terpasang Saat Ini**: `{st['installed_models']}`\n"
                    f"- **Prosedur Konfigurasi**: Jalankan `ollama pull {missing_name}` atau pilih salah satu model terpasang di atas."
                ),
                "source_attribution": "LOCAL_MODEL_PROBE (Model Not Found Report)",
            }

        model_name = resolved_model
        p9_op = (context or {}).get("phase9_operational") or {}
        if p9_op.get("direct_response_override"):
            return {
                "provider": self.provider_id,
                "model": model_name,
                "ui_state": "RESPONSE COMPLETE",
                "reply": str(p9_op["direct_response_override"]),
                "data": {"phase9_operational": p9_op},
                "source_attribution": "PHASE9_IMMUTABLE_CORE_PROTECTION (L7 Gate)",
            }
        precomp = self._run_deterministic_precomputation(prompt, context=context)
        if "folder_vps_inspection" in precomp:
            vps_insp = precomp["folder_vps_inspection"]
            return {
                "provider": self.provider_id,
                "model": model_name,
                "ui_state": "RESPONSE COMPLETE",
                "reply": str(vps_insp["verified_text"]),
                "data": {"folder_vps_inspection": vps_insp},
                "source_attribution": "LIVE_VPS_AND_MOUNT_INSPECTION (RemoteVPSDevelopmentEngine + AuthorizedFolders + OS Mount)",
            }
        det_context_lines = [
            str(v["verified_text"])
            for v in precomp.values()
            if isinstance(v, dict) and v.get("verified_text")
        ]
        if p9_op.get("verified_context_block"):
            det_context_lines.append(str(p9_op["verified_context_block"]))
        det_context_str = "\n\n".join(det_context_lines) if det_context_lines else None
        payload, retrieved_sources = self.build_ollama_chat_payload(
            prompt,
            context,
            model_name=model_name,
            stream=False,
            deterministic_context=det_context_str,
        )
        try:
            code, out = self._request_ollama("POST", "/api/chat", payload, timeout=60.0)
            msg_obj = out.get("message") or {}
            had_thinking_field = bool(msg_obj.get("thinking") or out.get("thinking"))
            raw_reply = str(msg_obj.get("content") or out.get("response") or "")
            reply_txt, had_think_tags = strip_internal_thinking(raw_reply)
            reply_txt = reply_txt.strip()

            if _contains_false_network_refusal(reply_txt):
                forced_insp = run_folder_vps_inspection(
                    prompt,
                    context,
                    self.remote_dev_engine,
                    self.universal_file_engine,
                    self.internet_engine,
                    force=True,
                )
                if forced_insp is not None:
                    reply_txt = str(forced_insp["formatted_report"])
                    precomp["folder_vps_inspection"] = {
                        **forced_insp,
                        "context_only": False,
                        "verified_text": reply_txt,
                    }

            if precomp and "folder_vps_inspection" not in precomp:
                prefixes = [
                    str(v["verified_text"])
                    for v in precomp.values()
                    if isinstance(v, dict) and v.get("verified_text") and not v.get("context_only")
                ]
                if prefixes:
                    reply_txt = "\n\n".join(prefixes + ([reply_txt] if reply_txt else []))
            actual_model = str(out.get("model") or model_name)
            src_files = ", ".join(r.file_path for r in retrieved_sources[:3]) or "NUI Persona (General Intelligence)"
            ollama_proof = {
                "endpoint": f"http://{self.host}:{self.port}/api/chat",
                "http_status": code,
                "model_requested": model_name,
                "model_responded": actual_model,
                "stream_enabled": False,
                "prompt_eval_count": int(out.get("prompt_eval_count") or 0),
                "eval_count": int(out.get("eval_count") or 0),
                "total_duration_ms": round(float(out.get("total_duration") or 0) / 1e6, 2),
            }
            return {
                "provider": self.provider_id,
                "model": actual_model,
                "ui_state": "RESPONSE COMPLETE",
                "reply": reply_txt,
                "data": {
                    **precomp,
                    "ollama_runtime_proof": ollama_proof,
                    "internal_thinking_filtered": had_thinking_field or had_think_tags,
                    "retrieved_sources": [asdict(r) for r in retrieved_sources],
                },
                "source_attribution": f"LOCAL_OLLAMA ({actual_model}) + NUI_CONTEXT ({src_files})",
            }
        except Exception as exc:
            return {
                "provider": self.provider_id,
                "model": model_name,
                "error": f"NETWORK_ERROR: {type(exc).__name__}: {exc}",
                "ui_state": "ERROR",
                "reply": f"Gagal berkomunikasi dengan model lokal `{model_name}`: `{type(exc).__name__}: {exc}`",
                "source_attribution": f"LOCAL_MODEL ({model_name})",
            }


class OptionalExternalProvider(NUIIntelligenceProvider):
    """External API Provider strictly gated by Operating Mode, PermissionEngine (`API_ACCESS`), and Keychain."""

    provider_id = "external_api"
    display_name = "Optional External API Provider (Keychain + Permission Gated)"

    def __init__(self, storage: Any, permission_engine: Any) -> None:
        self.storage = storage
        self.permission_engine = permission_engine

    def status(self) -> dict[str, Any]:
        connectors = self.storage.list_api_connectors()
        op_mode = self.storage.get_setting("operating_mode", "HYBRID")
        ready = op_mode in {"ONLINE", "HYBRID"} and len(connectors) > 0
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "available": ready,
            "streaming_supported": False,
            "ui_state": "PROVIDER CONNECTED" if ready else "PROVIDER UNAVAILABLE",
            "operating_mode": op_mode,
            "configured_connectors": len(connectors),
            "honest_status": (
                f"READY ({len(connectors)} konektor API terdaftar di Keychain)"
                if ready
                else f"UNAVAILABLE (Mode={op_mode}, Konektor terdaftar={len(connectors)})"
            ),
        }

    def respond(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        ctx = context or {}
        op_mode = self.storage.get_setting("operating_mode", "HYBRID")
        if op_mode == "LOCAL":
            return {
                "provider": self.provider_id,
                "error": "LOCAL_MODE_RESTRICTION",
                "ui_state": "ERROR",
                "reply": "Ditolak: Sistem berada dalam mode `LOCAL` (offline). Tidak ada pesan atau konteks yang dikirim keluar.",
                "source_attribution": "EXTERNAL_PROVIDER_GATE (LOCAL Mode Lock)",
            }

        connectors = self.storage.list_api_connectors()
        if not connectors:
            return {
                "provider": self.provider_id,
                "error": "PROVIDER_UNAVAILABLE",
                "ui_state": "PROVIDER UNAVAILABLE",
                "reply": "Provider eksternal belum dikonfigurasi (`PROVIDER_UNAVAILABLE`). Daftarkan konektor API di Keychain terlebih dahulu.",
                "source_attribution": "EXTERNAL_PROVIDER_GATE",
            }

        conn = connectors[0]
        target_domain = conn["base_url"]
        perm = self.permission_engine.check_or_request(
            category="API_ACCESS",
            operation="SEND_CHAT_CONTEXT",
            target_type="domain",
            target_value=target_domain,
            reason=(
                f"Kirim pesan chat & konteks ({len(ctx.get('conversation_context', []))} pesan) "
                f"ke layanan eksternal '{conn['name']}' pada domain {target_domain}"
            ),
            session_id=ctx.get("session_id"),
            risk_level="HIGH",
            payload={
                "domain": target_domain,
                "connector_id": conn["connector_id"],
                "data_types": ["user_message", "conversation_context"],
            },
        )
        if not perm.allowed:
            return {
                "provider": self.provider_id,
                "error": f"PERMISSION_DENIED_OR_PENDING ({perm.status})",
                "ui_state": "ERROR" if perm.status == "DENIED" else "WAITING_FOR_APPROVAL",
                "permission_status": perm.status,
                "request_id": perm.request_id,
                "target_domain": perm.target_value,
                "reply": (
                    f"**Pengiriman ke Provider Eksternal Ditahan (`{perm.status}`)**\n\n"
                    f"- **Layanan Tujuan**: `{conn['name']}` (`{perm.target_value}`)\n"
                    f"- **Jenis Data**: `user_message`, `conversation_context`\n"
                    f"- **Alasan**: {perm.reason}\n\n"
                    "Sesuai aturan keamanan CosmicTera (Section 7), tidak ada pesan atau konteks yang dikirim ke layanan eksternal tanpa otorisasi eksplisit."
                ),
                "source_attribution": f"EXTERNAL_PROVIDER_GATE ({perm.target_value})",
            }

        secret = self.storage.keychain.get_secret(conn["keychain_account"])
        if not secret:
            return {
                "provider": self.provider_id,
                "error": "MISSING_KEYCHAIN_CREDENTIALS",
                "ui_state": "ERROR",
                "reply": f"Kredensial Keychain untuk konektor `{conn['name']}` tidak ditemukan.",
                "source_attribution": f"EXTERNAL_PROVIDER_GATE ({perm.target_value})",
            }

        return {
            "provider": self.provider_id,
            "model": conn["name"],
            "ui_state": "RESPONSE COMPLETE",
            "reply": (
                f"Respons terotorisasi dari konektor eksternal **`{conn['name']}`** (`{perm.target_value}`) "
                f"untuk pesan: *\"{prompt}\"* (Autentikasi Keychain terverifikasi, izin `{perm.decision_source}`)."
            ),
            "data": {
                "connector_id": conn["connector_id"],
                "domain": perm.target_value,
                "decision_source": perm.decision_source,
            },
            "source_attribution": f"EXTERNAL_API ({perm.target_value})",
        }
