"""End-to-End Automated Test Suite for NUI Chat & Communication Engine (Sections 3, 4, 6, 7, 8 & 9)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
if str(NUI_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(NUI_DESKTOP_ROOT))

from backend.providers import NUIIntelligenceProvider, OllamaProvider
from backend.server import NUILocalServiceApp


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "comm_engine_test.db"


@pytest.fixture()
def app(db_path: Path) -> NUILocalServiceApp:
    return NUILocalServiceApp(db_path=db_path, use_os_keychain=False)


def test_section3_four_diagnostic_queries_and_audit_logs(app: NUILocalServiceApp) -> None:
    _, sess = app.dispatch_request("POST", "/api/sessions", {"title": "Section 3 Diagnostic"})
    sid = sess["session_id"]

    queries = [
        ("req-diag-01", "Halo, apakah NUI aktif?"),
        ("req-diag-02", "Jelaskan fungsi HCPU."),
        ("req-diag-03", "Hitung 5 + 7."),
        ("req-diag-04", "Apa status koneksi sistem?"),
    ]

    for req_id, q_text in queries:
        code, resp = app.dispatch_request(
            "POST",
            "/api/chat",
            {
                "request_id": req_id,
                "session_id": sid,
                "user_message": q_text,
                "ui_handler": "NUIDesktopStore.sendChatMessage",
            },
        )
        assert code == 200
        assert resp["request_id"] == req_id
        assert resp["session_id"] == sid
        assert resp["execution_status"] == "RESPONSE_COMPLETE"
        assert resp["ui_state"] == "RESPONSE COMPLETE"
        assert resp["provider"] == "native_nui"
        assert resp["model"] == "cosmictera-nui-native-v1.3"
        assert resp["error"] is None
        assert resp["response_time_ms"] >= 0

    msgs = app.storage.list_messages(sid)
    assert len(msgs) == 8
    assert "LOCAL SERVICE READY" in msgs[1]["content"]
    assert "Hijaiyyah Core Processing Unit" in msgs[3]["content"]
    assert "5 + 7 = 12" in msgs[5]["content"]
    assert "127.0.0.1:8848" in msgs[7]["content"]

    comm_logs = app.storage.list_communication_logs(session_id=sid)
    assert len(comm_logs) == 4
    logged_ids = {row["request_id"] for row in comm_logs}
    assert logged_ids == {"req-diag-01", "req-diag-02", "req-diag-03", "req-diag-04"}


def test_1_to_5_end_to_end_ui_to_backend_to_provider_to_timeline(
    app: NUILocalServiceApp,
) -> None:
    code, out = app.dispatch_request(
        "POST",
        "/api/chat",
        {
            "request_id": "req-e2e-001",
            "message_id": "msg-user-001",
            "user_message": "Hitung 8 + 14.",
            "ui_handler": "NUIChatSectionView.onSubmit",
        },
    )
    assert code == 200
    assert out["request_id"] == "req-e2e-001"
    assert out["chat_request"]["message_id"] == "msg-user-001"
    assert out["provider"] == "native_nui"
    assert "8 + 14 = 22" in out["response_text"]
    assert out["provider_response"]["data"]["output"] == [22]

    sid = out["session_id"]
    s_code, s_data = app.dispatch_request("GET", f"/api/sessions?session_id={sid}")
    assert s_code == 200
    timeline = s_data["messages"]
    assert len(timeline) == 2
    assert timeline[0]["message_id"] == "msg-user-001"
    assert timeline[0]["role"] == "user"
    assert timeline[1]["role"] == "assistant"
    assert timeline[1]["request_id"] == "req-e2e-001"
    assert "22" in timeline[1]["content"]


def test_6_and_7_conversation_context_and_multiple_sessions_isolation(
    app: NUILocalServiceApp,
) -> None:
    _, sess_a = app.dispatch_request("POST", "/api/sessions", {"title": "Session Alpha"})
    sid_a = sess_a["session_id"]

    _, sess_b = app.dispatch_request("POST", "/api/sessions", {"title": "Session Beta"})
    sid_b = sess_b["session_id"]

    app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid_a, "user_message": "Jelaskan fungsi HCPU."},
    )
    app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid_b, "user_message": "Analisis huruf Jim (ج)."},
    )

    _, sum_a = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid_a, "user_message": "Ringkas pertanyaan pertama kita."},
    )
    _, sum_b = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid_b, "user_message": "Ringkas pertanyaan pertama kita."},
    )

    assert "Jelaskan fungsi HCPU." in sum_a["response_text"]
    assert "Analisis huruf Jim" not in sum_a["response_text"]

    assert "Analisis huruf Jim (ج)." in sum_b["response_text"]
    assert "Jelaskan fungsi HCPU." not in sum_b["response_text"]


def test_8_and_9_provider_unavailable_and_model_not_found(
    app: NUILocalServiceApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, out_unavail = app.dispatch_request(
        "POST",
        "/api/chat",
        {
            "user_message": "Halo",
            "provider": "nonexistent_provider",
        },
    )
    assert out_unavail["execution_status"] == "PROVIDER_UNAVAILABLE"
    assert out_unavail["ui_state"] == "PROVIDER UNAVAILABLE"
    assert out_unavail["error"] is not None

    monkeypatch.setattr(
        app.ollama_provider,
        "status",
        lambda: {
            "provider_id": "local_ollama",
            "display_name": "Local Model Provider",
            "available": False,
            "daemon_reachable": True,
            "installed_models": [],
            "model": None,
            "ui_state": "PROVIDER UNAVAILABLE",
            "honest_status": "MODEL_NOT_FOUND",
        },
    )
    _, out_missing_model = app.dispatch_request(
        "POST",
        "/api/chat",
        {
            "user_message": "Halo Ollama",
            "provider": "local_ollama",
            "model": "hermes3:8b",
        },
    )
    assert out_missing_model["execution_status"] == "PROVIDER_UNAVAILABLE"
    assert out_missing_model["ui_state"] == "PROVIDER UNAVAILABLE"
    assert out_missing_model["error"] == "MODEL_NOT_FOUND"
    assert "MODEL_NOT_FOUND" in out_missing_model["response_text"]


def test_10_11_12_13_backend_offline_network_timeout_and_empty_response(
    app: NUILocalServiceApp,
) -> None:
    offline_probe = OllamaProvider(host="127.0.0.1", port=65439).status()
    assert offline_probe["available"] is False
    assert offline_probe["ui_state"] == "PROVIDER UNAVAILABLE"

    class NetworkErrorProvider(NUIIntelligenceProvider):
        provider_id = "net_err_prov"
        display_name = "Network Error Mock"

        def status(self) -> dict[str, Any]:
            return {"provider_id": self.provider_id, "available": True}

        def respond(self, prompt: str, context: dict[str, Any] | None = None, cancel_check: Any = None) -> dict[str, Any]:
            return {
                "provider": self.provider_id,
                "error": "NETWORK_ERROR: ConnectionResetError",
                "reply": "Gagal berkomunikasi karena gangguan jaringan.",
            }

    class TimeoutProvider(NUIIntelligenceProvider):
        provider_id = "timeout_prov"
        display_name = "Timeout Mock"

        def status(self) -> dict[str, Any]:
            return {"provider_id": self.provider_id, "available": True}

        def respond(self, prompt: str, context: dict[str, Any] | None = None, cancel_check: Any = None) -> dict[str, Any]:
            return {
                "provider": self.provider_id,
                "error": "REQUEST_TIMEOUT: Timed out after 10.0s",
                "reply": "Permintaan melebihi batas waktu.",
            }

    class EmptyResponseProvider(NUIIntelligenceProvider):
        provider_id = "empty_prov"
        display_name = "Empty Mock"

        def status(self) -> dict[str, Any]:
            return {"provider_id": self.provider_id, "available": True}

        def respond(self, prompt: str, context: dict[str, Any] | None = None, cancel_check: Any = None) -> dict[str, Any]:
            return {
                "provider": self.provider_id,
                "reply": "   ",
            }

    orig_get = app.orchestrator.get_provider
    try:
        app.orchestrator.get_provider = lambda pid=None: NetworkErrorProvider()  # type: ignore[assignment]
        _, r_net = app.dispatch_request("POST", "/api/chat", {"user_message": "Test net"})
        assert r_net["execution_status"] == "ERROR"
        assert "NETWORK_ERROR" in r_net["error"]

        app.orchestrator.get_provider = lambda pid=None: TimeoutProvider()  # type: ignore[assignment]
        _, r_time = app.dispatch_request("POST", "/api/chat", {"user_message": "Test timeout"})
        assert r_time["execution_status"] == "ERROR"
        assert "REQUEST_TIMEOUT" in r_time["error"]

        app.orchestrator.get_provider = lambda pid=None: EmptyResponseProvider()  # type: ignore[assignment]
        _, r_empty = app.dispatch_request("POST", "/api/chat", {"user_message": "Test empty"})
        assert r_empty["execution_status"] == "ERROR"
        assert r_empty["error"] == "EMPTY_RESPONSE"
    finally:
        app.orchestrator.get_provider = orig_get  # type: ignore[assignment]


def test_14_stop_generation_cancels_request(app: NUILocalServiceApp) -> None:
    _, stop_res = app.dispatch_request(
        "POST",
        "/api/chat/stop",
        {"request_id": "req-to-stop-99", "session_id": "sess-stop-test"},
    )
    assert stop_res["stopped"] is True
    assert stop_res["execution_status"] == "STOPPED"

    _, chat_out = app.dispatch_request(
        "POST",
        "/api/chat",
        {
            "request_id": "req-to-stop-99",
            "session_id": "sess-stop-test",
            "user_message": "Hitung 10 + 20.",
        },
    )
    assert chat_out["execution_status"] == "STOPPED"
    assert chat_out["error"] == "GENERATION_STOPPED"


def test_15_permission_denied_and_online_authorization_for_external_provider(
    app: NUILocalServiceApp,
) -> None:
    app.storage.register_api_connector(
        name="External Cloud LLM",
        base_url="api.external-llm.example",
        secret="secret-" + ("abcd" * 5),
    )

    app.storage.set_setting("operating_mode", "LOCAL")
    _, r_local = app.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": "Halo", "provider": "external_api"},
    )
    assert r_local["execution_status"] == "ERROR"
    assert r_local["error"] == "LOCAL_MODE_RESTRICTION"

    app.storage.set_setting("operating_mode", "ONLINE")
    _, r_wait = app.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": "Rahasia Proyek", "provider": "external_api"},
    )
    assert r_wait["execution_status"] == "WAITING_FOR_APPROVAL"
    assert r_wait["ui_state"] == "WAITING_FOR_APPROVAL"
    perm_req_id = r_wait["provider_response"]["request_id"]

    app.permissions.decide_request(perm_req_id, "DENY")
    _, r_denied = app.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": "Rahasia Proyek", "provider": "external_api"},
    )
    assert r_denied["execution_status"] == "ERROR"
    assert "DENIED" in r_denied["error"]


def test_16_application_reopen_and_service_persistence(db_path: Path) -> None:
    app1 = NUILocalServiceApp(db_path=db_path, use_os_keychain=False)
    _, turn1 = app1.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": "sess-persist-01", "user_message": "Halo NUI."},
    )
    assert turn1["execution_status"] == "RESPONSE_COMPLETE"

    app2 = NUILocalServiceApp(db_path=db_path, use_os_keychain=False)
    code, loaded_sess = app2.dispatch_request(
        "GET", "/api/sessions?session_id=sess-persist-01"
    )
    assert code == 200
    assert len(loaded_sess["messages"]) == 2
    assert loaded_sess["messages"][0]["content"] == "Halo NUI."

    _, turn2 = app2.dispatch_request(
        "POST",
        "/api/chat",
        {
            "session_id": "sess-persist-01",
            "user_message": "Ringkas pertanyaan pertama kita.",
        },
    )
    assert turn2["execution_status"] == "RESPONSE_COMPLETE"
    assert "Halo NUI." in turn2["response_text"]


def test_section9_five_stage_real_conversation_acceptance(
    app: NUILocalServiceApp,
) -> None:
    _, sess = app.dispatch_request(
        "POST",
        "/api/sessions",
        {"title": "Uji Penerimaan 5 Tahap Percakapan Nyata"},
    )
    sid = sess["session_id"]

    _, r1 = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Halo NUI."},
    )
    assert r1["execution_status"] == "RESPONSE_COMPLETE"
    assert "Halo! Saya NUI dari CosmicTera." in r1["response_text"]
    assert "LOCAL SERVICE READY" not in r1["response_text"]

    _, r2 = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Jelaskan apa itu CosmicTera."},
    )
    assert r2["execution_status"] == "RESPONSE_COMPLETE"
    assert "Matematika Hijaiyyah" in r2["response_text"]
    assert "28 huruf Hijaiyyah" in r2["response_text"]
    assert "HCPU" in r2["response_text"]

    _, r3 = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Apa hubungan NUI dengan HCPU?"},
    )
    assert r3["execution_status"] == "RESPONSE_COMPLETE"
    assert "Hijaiyyah Core Processing Unit" in r3["response_text"]
    assert "atom.py" in r3["response_text"]
    assert "parity_model.py" in r3["response_text"]

    _, r4 = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Hitung 5 + 7 dan jelaskan hasilnya."},
    )
    assert r4["execution_status"] == "RESPONSE_COMPLETE"
    assert "5 + 7 = 12" in r4["response_text"]
    assert r4["provider_response"]["data"]["output"] == [12]
    assert "MOVI" in r4["response_text"]

    _, r5 = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Ringkas pertanyaan pertama kita."},
    )
    assert r5["execution_status"] == "RESPONSE_COMPLETE"
    assert "Halo NUI." in r5["response_text"]
    assert r5["provider_response"]["data"]["first_user_question"] == "Halo NUI."
    assert r5["provider_response"]["data"]["prior_user_turns_count"] == 4
