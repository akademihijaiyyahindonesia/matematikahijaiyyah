"""Phase 12.1 Live Diagnostic Execution & Chat Integration Repair Test Suite.

Verifies:
1. Root Cause Regression: Even when a provider is instantiated without explicit engine references (simulating legacy hot-reload), `run_folder_vps_inspection` self-heals and executes the real diagnostic pipeline instead of falling through to generic LLM text.
2. Intent & Multi-Model Router Alignment: `operational_intelligence.py` classifies folder/VPS/domain/connect queries (including `"kamu hubaungkan"`, `"kamu hubungkan"`, `"cek dns"`, `"cek https"`, `"cek ssh"`) as `SYSTEM_DIAGNOSTICS` and `self_learning.py` routes them to `DETERMINISTIC_COMPUTATION`.
3. Action-First 9-Stage Diagnostic Pipeline Trace: `USER_MESSAGE -> INTENT_UNDERSTANDING -> RESOURCE_RESOLUTION -> DIAGNOSTIC_ACTION_SELECTION -> PERMISSION_CHECK -> LIVE_ENGINE_EXECUTION -> STRUCTURED_RESULT -> RESPONSE_COMPOSER -> CHAT_DISPLAY`.
4. 9-Item Structured Chat Output & Safe Credential Policy:
   - Separates (1) Local Folder Availability, (2) Internet Connectivity, (3) Domain DNS, (4) Website HTTPS, (5) VPS SSH, (6) SFTP, (7) Remote Workspace, (8) File Synchronization, (9) Deployment Status.
   - Never asks the user to type passwords or private keys in chat.
5. Multi-Resolver Live DNS & Strict `PASS_LIVE` vs `PASS_SIMULATED` vs `FAILED` Enforcement.
6. SSH Agent, Keychain, `~/.ssh/config`, `known_hosts`, Live OpenSSH Probe (`probe_and_attempt_live_ssh_connection`), and `DEPLOY.md` (`DOCUMENTED_IN_DEPLOY_MD_ONLY`) provenance.
7. Complete Elimination of False Network/VPS Refusal Messages (`"Maaf, saya tidak bisa menghubungkan atau mengakses perangkat atau jaringan eksternal secara langsung..."`).
8. Swift UI `checkYayasanVPSConnectionNow()` & `verifyFullDeployment()` integration.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "nui-desktop") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "nui-desktop"))

from backend.internet_engine import (  # noqa: E402
    LiveNetworkTransportAdapter,
    RealInternetEngine,
)
from backend.permissions import PermissionEngine  # noqa: E402
from backend.persona_and_context import NUIContextualRetriever, NUIPersonaLoader  # noqa: E402
from backend.providers import (  # noqa: E402
    NativeNUIProvider,
    OllamaProvider,
    _contains_false_network_refusal,
    classify_operational_network_subintent,
    is_folder_vps_status_query,
    run_folder_vps_inspection,
)
from backend.remote_dev_engine import RemoteVPSDevelopmentEngine  # noqa: E402
from backend.server import NUILocalServiceApp, SERVICE_VERSION  # noqa: E402
from backend.storage import NUIStorage  # noqa: E402


class SimulatedDomainTransport:
    """Mock network transport for testing PASS_SIMULATED vs PASS_LIVE separation."""

    def resolve_dns(self, host: str, timeout: float = 3.5) -> dict[str, Any]:
        return {
            "ok": True,
            "host": host,
            "addresses": ["187.53.135.198"],
            "latency_ms": 1.2,
            "error": None,
            "error_category": None,
        }

    def check_tcp(self, host: str, port: int = 443, timeout: float = 3.5) -> dict[str, Any]:
        return {
            "ok": True,
            "host": host,
            "port": port,
            "status": "OPEN",
            "latency_ms": 2.0,
            "error": None,
            "error_category": None,
        }

    def check_tls(self, host: str, port: int = 443, timeout: float = 4.0) -> dict[str, Any]:
        return {
            "ok": True,
            "host": host,
            "port": port,
            "cert_valid": True,
            "tls_version": "TLSv1.3",
            "subject_cn": host,
            "issuer_cn": "Let's Encrypt",
            "not_after": "2027-01-01",
            "status": "VALID",
            "error": None,
            "error_category": None,
        }

    def http_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "status_code": 200,
            "url": url,
            "redirected": False,
            "content_type": "text/html",
            "body_bytes": b"<html><head><title>Akademi Hijaiyyah Indonesia</title></head><body><h1>Yayasan</h1></body></html>",
            "response_headers": {"Server": "nginx"},
            "latency_ms": 5.0,
            "error": None,
            "error_category": None,
        }


@pytest.mark.unit
def test_phase12_1_intent_and_router_classification(tmp_path: Path) -> None:
    """Verify operational_intelligence and self_learning route VPS/folder/domain and follow-up connect queries ('kamu hubaungkan') to SYSTEM_DIAGNOSTICS and DETERMINISTIC_COMPUTATION."""
    app = NUILocalServiceApp(db_path=tmp_path / "phase12_1_router.db", use_os_keychain=False)
    oi = app.operational_intelligence
    router = app.multi_model_router

    queries = [
        "Apakah folder Yayasan sudah terhubung ke VPS?",
        "Cek apakah folder Yayasan sudah terhubung ke VPS.",
        "Periksa folder /Users/AMRA/yayasan, apakah sudah terhubung ke VPS dan apakah domain www.akademihijaiyyahindonesia.com sudah mengarah ke server?",
        "Apakah domain www.akademihijaiyyahindonesia.com sudah terhubung ke server?",
        "Apakah file sudah di-upload?",
        "kamu hubaungkan",
        "kamu hubungkan",
        "cek dns www.akademihijaiyyahindonesia.com",
        "cek https www.akademihijaiyyahindonesia.com",
        "cek ssh ke vps",
    ]
    for q in queries:
        assert is_folder_vps_status_query(q) is True, f"Failed query detection for: {q}"
        intent_info = oi.classify_operational_intent(q)
        assert intent_info["operational_intent"] == "SYSTEM_DIAGNOSTICS", f"Expected SYSTEM_DIAGNOSTICS for {q}, got {intent_info}"
        route_info = router.classify_and_route(q)
        assert route_info["task_class"] == "DETERMINISTIC_COMPUTATION", f"Expected DETERMINISTIC_COMPUTATION for {q}, got {route_info}"


@pytest.mark.unit
def test_phase12_1_subintent_classification() -> None:
    """Verify operational sub-intent classification across full verification, upload, connect ('kamu hubaungkan'), compare, and SSH checks."""
    assert classify_operational_network_subintent(
        "Periksa folder /Users/AMRA/yayasan, apakah sudah terhubung ke VPS dan apakah domain www.akademihijaiyyahindonesia.com sudah mengarah ke server?"
    ) == "full_folder_vps_domain_verification"
    assert classify_operational_network_subintent("Upload website Yayasan ke server.") == "upload_website_to_server"
    assert classify_operational_network_subintent("Sambungkan folder Yayasan ke VPS.") == "connect_folder_to_vps"
    assert classify_operational_network_subintent("kamu hubaungkan") == "connect_folder_to_vps"
    assert classify_operational_network_subintent("kamu hubungkan") == "connect_folder_to_vps"
    assert classify_operational_network_subintent("Bandingkan file lokal dengan server.") == "compare_local_and_remote_files"
    assert classify_operational_network_subintent("Cek koneksi SSH ke VPS.") == "check_vps_ssh_status"


@pytest.mark.integration
def test_phase12_1_self_healing_when_provider_lacks_engine_refs() -> None:
    """Regression test for the PID 32277 hot-reload bug: even when context={} and fallback_engine=None, run_folder_vps_inspection self-heals and never returns None."""
    prompt = "Cek apakah folder Yayasan sudah terhubung ke VPS."
    res = run_folder_vps_inspection(prompt, context={}, fallback_engine=None)
    assert res is not None
    assert res["ok"] is True
    assert "executed_at" in res
    assert "permission_checks" in res
    assert "READ_LOCAL" in res["permission_checks"]
    assert "NETWORK_ACCESS" in res["permission_checks"]
    assert "SSH_CONNECT" in res["permission_checks"]
    assert "diagnostic_pipeline_trace" in res
    assert len(res["diagnostic_pipeline_trace"]) == 9
    stage_names = [s["name"] for s in res["diagnostic_pipeline_trace"]]
    assert stage_names == [
        "USER_MESSAGE",
        "INTENT_UNDERSTANDING",
        "RESOURCE_RESOLUTION",
        "DIAGNOSTIC_ACTION_SELECTION",
        "PERMISSION_CHECK",
        "LIVE_ENGINE_EXECUTION",
        "STRUCTURED_RESULT",
        "RESPONSE_COMPOSER",
        "CHAT_DISPLAY",
    ]


@pytest.mark.integration
def test_phase12_1_ollama_and_native_provider_never_fallback_to_generic_llm_or_ask_passwords(tmp_path: Path) -> None:
    """Verify both OllamaProvider and NativeNUIProvider execute the real diagnostic engine and never ask for passwords/private keys in chat."""
    loader = NUIPersonaLoader(REPO_ROOT)
    retriever = NUIContextualRetriever(REPO_ROOT)
    ollama_prov = OllamaProvider(
        persona_loader=loader,
        context_retriever=retriever,
        ollama_transport=lambda m, p, b: (200, {"message": {"content": "GENERIC_LLM_FALLBACK_SHOULD_NOT_BE_USED"}}),
    )
    native_prov = NativeNUIProvider(
        persona_loader=loader,
        context_retriever=retriever,
        ollama_provider=ollama_prov,
    )

    prompt = "Periksa folder /Users/AMRA/yayasan, apakah sudah terhubung ke VPS dan apakah domain www.akademihijaiyyahindonesia.com sudah mengarah ke server?"
    for prov in (ollama_prov, native_prov):
        out = prov.respond(prompt=prompt, context={})
        text = out.get("reply") or out.get("response_text") or out.get("content") or out.get("response") or ""
        assert "GENERIC_LLM_FALLBACK_SHOULD_NOT_BE_USED" not in text
        assert "QtLabsFolderListModel" not in text
        assert "### 1. LOCAL FOLDER" in text
        assert "### 2. INTERNET" in text
        assert "### 3. DOMAIN (`www.akademihijaiyyahindonesia.com`)" in text
        assert "### 4. VPS" in text
        assert "### 5. FILE SYNCHRONIZATION" in text
        assert "### 6. FINAL CONCLUSION" in text
        for item_header in (
            "1. Local Folder Availability",
            "2. Internet Connectivity",
            "3. Domain DNS",
            "4. Website HTTPS",
            "5. VPS SSH",
            "6. SFTP",
            "7. Remote Workspace",
            "8. File Synchronization",
            "9. Deployment Status",
        ):
            assert item_header in text, f"Missing {item_header} in {prov.provider_id} response"
        assert "tidak pernah meminta password atau private key di chat" in text
        assert "Saya tidak melakukan upload, penghapusan, atau perubahan file selama pemeriksaan." in text


@pytest.mark.integration
def test_phase12_1_streaming_chat_uses_live_diagnostic_engine() -> None:
    """Verify stream_respond on OllamaProvider and NativeNUIProvider yields the deterministic 9-item diagnostic report."""
    loader = NUIPersonaLoader(REPO_ROOT)
    retriever = NUIContextualRetriever(REPO_ROOT)
    ollama_prov = OllamaProvider(
        persona_loader=loader,
        context_retriever=retriever,
    )
    prompt = "Apakah folder Yayasan sudah terhubung ke VPS?"
    chunks = list(ollama_prov.stream_respond(prompt=prompt, context={}))
    final_ev = chunks[-1]
    full_text = final_ev.get("response_text") or final_ev.get("reply") or "".join(c.get("delta", "") for c in chunks)
    assert "### 1. LOCAL FOLDER" in full_text
    assert "### 4. VPS" in full_text
    assert "NOT_CONFIGURED" in full_text


@pytest.mark.integration
def test_phase12_1_kamu_hubaungkan_and_refusal_elimination() -> None:
    """Regression test for 'kamu hubaungkan': verify NUI executes the live macOS backend DNS/HTTPS/SSH check and NEVER emits the 'Maaf, saya tidak bisa menghubungkan...' refusal."""
    refusal_sample = (
        "Maaf, saya tidak bisa menghubungkan atau mengakses perangkat atau jaringan eksternal secara langsung "
        "seperti VPS, server, atau jaringan internet.\n\nSaya adalah NUI (Natural Universal Intelligence), "
        "asisten AI lokal yang beroperasi dalam sistem terbatas."
    )
    assert _contains_false_network_refusal(refusal_sample) is True

    loader = NUIPersonaLoader(REPO_ROOT)
    retriever = NUIContextualRetriever(REPO_ROOT)
    ollama_prov = OllamaProvider(
        persona_loader=loader,
        context_retriever=retriever,
        ollama_transport=lambda m, p, b: (
            (200, {"models": [{"name": "qwen3:4b-instruct-2507-q4_K_M"}]})
            if p == "/api/tags"
            else (200, {"message": {"content": refusal_sample}})
        ),
    )

    # 1. Direct 'kamu hubaungkan' command
    out1 = ollama_prov.respond(prompt="kamu hubaungkan", context={})
    reply1 = out1["reply"]
    assert "Maaf, saya tidak bisa menghubungkan" not in reply1
    assert "asisten AI lokal yang beroperasi dalam sistem terbatas" not in reply1
    assert "### 1. LOCAL FOLDER" in reply1
    assert "### 2. INTERNET" in reply1
    assert "### 3. DOMAIN (`www.akademihijaiyyahindonesia.com`)" in reply1
    assert "### 4. VPS" in reply1
    assert "Live macOS Backend SSH Probe" in reply1
    assert "CONNECT_FOLDER_TO_VPS" in reply1

    # 2. Even on an arbitrary phrasing that would otherwise hit Ollama and return a refusal, the refusal interceptor replaces it with live diagnostics
    out2 = ollama_prov.respond(prompt="tolong akses jaringan eksternal sekarang", context={})
    reply2 = out2["reply"]
    assert "Maaf, saya tidak bisa menghubungkan" not in reply2
    assert "### 1. LOCAL FOLDER" in reply2
    assert "### 2. INTERNET" in reply2


@pytest.mark.live_fs
def test_phase12_1_ssh_agent_keychain_and_deploy_md_provenance(tmp_path: Path) -> None:
    """Verify discover_ssh_and_deployment_metadata and probe_and_attempt_live_ssh_connection inspect SSH Agent, known_hosts, local SSH keys, and DEPLOY.md."""
    storage = NUIStorage(tmp_path / "phase12_1_ssh.db", use_os_keychain=False)
    permissions = PermissionEngine(storage)
    rde = RemoteVPSDevelopmentEngine(storage=storage, permissions=permissions)

    yayasan_dir = Path("/Users/AMRA/yayasan")
    meta = rde.discover_ssh_and_deployment_metadata(str(yayasan_dir))
    assert "ssh_agent" in meta
    assert "sock_present" in meta["ssh_agent"]
    assert "status" in meta["ssh_agent"]
    assert "known_hosts_entries_count" in meta
    assert "local_ssh_keys" in meta
    assert "keychain_credential_refs_count" in meta
    deploy_md = meta["deploy_md"]
    if (yayasan_dir / "DEPLOY.md").is_file():
        assert deploy_md["deploy_md_exists"] is True
        assert deploy_md["documented_vps_host"] == "187.53.135.198"
        assert deploy_md["documented_remote_workspace"] == "/opt/yayasan"
        assert deploy_md["source_file"] == "DEPLOY.md"
        assert deploy_md["evidence_classification"] == "DOCUMENTED_IN_DEPLOY_MD_ONLY"

    probe = rde.probe_and_attempt_live_ssh_connection("187.53.135.198", username="root", port=22, remote_workspace="/opt/yayasan")
    assert probe["attempted"] is True
    assert probe["target"] == "root@187.53.135.198:22"
    assert "ssh_status" in probe


@pytest.mark.mock
def test_phase12_1_multi_resolver_dns_and_pass_simulated_never_pass_live(tmp_path: Path) -> None:
    """Verify mock transport reports PASS_SIMULATED (never PASS_LIVE) and records resolvers_tried + checked_at."""
    storage = NUIStorage(tmp_path / "phase12_1_net.db", use_os_keychain=False)
    permissions = PermissionEngine(storage)
    mock_transport = SimulatedDomainTransport()
    ie = RealInternetEngine(storage=storage, permissions=permissions, transport=mock_transport)

    rep = ie.inspect_domain_and_website("www.akademihijaiyyahindonesia.com")
    assert rep["verification_status"] == "PASS_SIMULATED"
    assert rep["verification_status"] != "PASS_LIVE"
    assert "resolvers_tried" in rep["dns"]
    assert "checked_at" in rep["dns"]
    assert "http_https" in rep


@pytest.mark.live_net
def test_phase12_1_live_domain_multi_resolver_execution(tmp_path: Path) -> None:
    """Verify live network transport tries multiple resolvers (system, dig, DoH) and records honest status."""
    storage = NUIStorage(tmp_path / "phase12_1_live_net.db", use_os_keychain=False)
    permissions = PermissionEngine(storage)
    ie = RealInternetEngine(storage=storage, permissions=permissions, transport=LiveNetworkTransportAdapter())

    dns_res = ie.resolve_dns_records("www.akademihijaiyyahindonesia.com")
    assert "resolvers_tried" in dns_res
    assert len(dns_res["resolvers_tried"]) >= 2
    assert "checked_at" in dns_res
    if dns_res["ok"]:
        assert dns_res["verification_status"] == "PASS_LIVE"
    else:
        assert dns_res["verification_status"] in ("FAILED", "BLOCKED")


@pytest.mark.integration
def test_phase12_1_end_to_end_server_chat_and_vps_full_verification(tmp_path: Path) -> None:
    """Verify NUILocalServiceApp /api/chat and /api/vps/op (full_verification) return identical 9-section truth."""
    app = NUILocalServiceApp(
        db_path=tmp_path / "phase12_1_e2e.db",
        use_os_keychain=False,
    )
    assert SERVICE_VERSION == "1.5.2"

    # 1. Verify /api/vps/op full_verification
    st_vps, vps_payload = app.dispatch_request(
        "POST",
        "/api/vps/op",
        {
            "op": "full_verification",
            "local_path": "/Users/AMRA/yayasan",
            "domain": "www.akademihijaiyyahindonesia.com",
        },
    )
    assert st_vps == 200
    assert vps_payload["ok"] is True
    assert vps_payload["local_canonical_path"] == "/Users/AMRA/yayasan"
    assert vps_payload["ssh_connection_status"] == "NOT_CONFIGURED"
    assert vps_payload["file_synchronization"]["overall_sync_status"] == "NOT_CONFIGURED"
    assert "formatted_report" in vps_payload

    # 2. Verify /api/chat with full diagnostic prompt
    st_chat, chat_payload = app.dispatch_request(
        "POST",
        "/api/chat",
        {
            "message": "Periksa folder /Users/AMRA/yayasan, apakah sudah terhubung ke VPS dan apakah domain www.akademihijaiyyahindonesia.com sudah mengarah ke server?",
            "mode": "HYBRID",
        },
    )
    assert st_chat == 200
    msg = chat_payload.get("response") or chat_payload.get("assistant_message", {}).get("content") or ""
    assert "### 1. LOCAL FOLDER" in msg
    assert "### 2. INTERNET" in msg
    assert "### 3. DOMAIN (`www.akademihijaiyyahindonesia.com`)" in msg
    assert "### 4. VPS" in msg
    assert "### 5. FILE SYNCHRONIZATION" in msg
    assert "### 6. FINAL CONCLUSION" in msg
    assert "187.53.135.198" in msg
    assert "DOCUMENTED_IN_DEPLOY_MD_ONLY" in msg


@pytest.mark.unit
def test_phase12_1_connect_and_upload_write_gates_safe_credential_guidance() -> None:
    """Verify connect_folder_to_vps and upload_website_to_server enforce write gates and guide user to VPS Profile Manager instead of asking for passwords in chat."""
    res_conn = run_folder_vps_inspection("Sambungkan folder Yayasan ke VPS.", context={})
    assert res_conn is not None
    assert "CONNECT_FOLDER_TO_VPS" in res_conn["formatted_response"]
    assert "VPS Profile Manager" in res_conn["formatted_response"]
    assert "tidak pernah" in res_conn["formatted_response"].lower()

    res_up = run_folder_vps_inspection("Upload website Yayasan ke server.", context={})
    assert res_up is not None
    assert "KONFIRMASI OPERASI WRITE DIPERLUKAN" in res_up["formatted_response"]
    assert "tidak ada perubahan atau pengiriman file yang dilakukan" in res_up["formatted_response"]


@pytest.mark.unit
def test_phase12_1_swift_ui_button_and_verification_center_wiring() -> None:
    """Verify CosmicTeraNUIApp.swift wires checkYayasanVPSConnectionNow() to verifyFullDeployment() and v1.5.2."""
    swift_src = (REPO_ROOT / "nui-desktop" / "macos" / "Sources" / "CosmicTeraNUIApp.swift").read_text(encoding="utf-8")
    assert 'if ver != "1.5.2"' in swift_src
    assert "await verifyFullDeployment()" in swift_src
    assert 'overridePrompt: "Periksa folder /Users/AMRA/yayasan, apakah sudah terhubung ke VPS dan apakah domain www.akademihijaiyyahindonesia.com sudah mengarah ke server?"' in swift_src


@pytest.mark.unit
def test_phase12_1_pyproject_pytest_markers_registered() -> None:
    """Verify all 5 pytest markers (unit, live_fs, integration, mock, live_net) are registered in pyproject.toml."""
    toml_txt = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for mk in ("unit:", "live_fs:", "integration:", "mock:", "live_net:"):
        assert mk in toml_txt, f"Missing marker registration {mk} in pyproject.toml"
