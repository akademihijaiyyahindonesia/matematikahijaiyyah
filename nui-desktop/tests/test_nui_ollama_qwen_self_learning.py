"""Comprehensive End-to-End Tests for:
1. Directive 1: Ollama Local Language Engine Integration + Official NUI Persona (`HybitAIProgram.system`) + Contextual Retrieval (TEST A – TEST J)
2. Directive 2: Qwen3.8-27B Coding Intelligence (`NUI CODING SPECIALIST — QWEN3.8-27B`) + Multi-Model Routing + Autonomous Self-Learning Center (10 Submenus, Pytest Skill Validation, User Feedback, Rollback, Immutable Boundary Protection, Mac Resource Telemetry).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
if str(NUI_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(NUI_DESKTOP_ROOT))

from backend.providers import OllamaProvider
from backend.self_learning import (
    NUIModelAssetLibrary,
    NUIMultiModelRouter,
    measure_mac_host_resources,
)
from backend.server import NUILocalServiceApp


def _in_memory_ollama_transport(
    method: str, path: str, body: dict[str, Any] | None = None
) -> tuple[int, Any]:
    """In-memory Ollama API protocol transport (`/api/tags`, `/api/ps`, `/api/version`, `/api/generate`, `/api/chat`)."""
    if method == "GET":
        if path == "/api/version":
            return (200, {"version": "0.6.2-local"})
        if path == "/api/tags":
            return (
                200,
                {
                    "models": [
                        {
                            "name": "qwen3.8:27b",
                            "model": "qwen3.8:27b",
                            "size": int(17.8 * (1024**3)),
                            "digest": "sha256:qwen38_27b_digest",
                            "details": {
                                "family": "qwen3",
                                "parameter_size": "27B",
                                "quantization_level": "Q4_K_M",
                            },
                        },
                        {
                            "name": "qwen2.5-coder:7b",
                            "model": "qwen2.5-coder:7b",
                            "size": int(4.7 * (1024**3)),
                            "digest": "sha256:qwen25_7b_digest",
                            "details": {
                                "family": "qwen2",
                                "parameter_size": "7B",
                                "quantization_level": "Q4_K_M",
                            },
                        },
                    ]
                },
            )
        if path == "/api/ps":
            return (
                200,
                {
                    "models": [
                        {
                            "name": "qwen3.8:27b",
                            "model": "qwen3.8:27b",
                            "size": int(17.8 * (1024**3)),
                        }
                    ]
                },
            )
        return (404, {"error": "not found"})

    payload = body or {}
    if path == "/api/generate":
        return (
            200,
            {
                "model": payload.get("model", "qwen3.8:27b"),
                "done": True,
                "keep_alive": payload.get("keep_alive"),
            },
        )

    if path == "/api/chat":
        model_name = payload.get("model", "qwen3.8:27b")
        if model_name == "missing-model:latest":
            return (404, {"error": "model 'missing-model:latest' not found"})

        messages = payload.get("messages", [])
        sys_msg = next((m["content"] for m in messages if m.get("role") == "system"), "")
        user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
        last_user = user_msgs[-1] if user_msgs else ""
        stream = bool(payload.get("stream", False))

        has_nui_persona = "CosmicTera" in sys_msg and "Natural Universal Intelligence" in sys_msg

        if "siapa kamu" in last_user.lower() or "who are you" in last_user.lower():
            reply_chunks = [
                "Saya adalah **CosmicTera NUI** (Natural Universal Intelligence), ",
                "sistem kecerdasan ekosistem komputasi Matematika Hijaiyyah ",
                f"(Persona aktif: `{has_nui_persona}`, Model: `{model_name}`).",
            ]
        elif "fokus kita tadi" in last_user.lower():
            prior_text = " | ".join(user_msgs[:-1])
            reply_chunks = [
                "Berdasarkan riwayat percakapan sesi ini, fokus kita adalah: ",
                f"**komunikasi NUI** (konteks sebelumnya: `{prior_text}`).",
            ]
        elif "faktor bilangan" in last_user.lower():
            reply_chunks = [
                "Berikut fungsi Python terverifikasi dari **NUI CODING SPECIALIST**:\n```python\n",
                "def faktor_bilangan(n: int) -> list[int]:\n",
                "    return [i for i in range(1, n + 1) if n % i == 0]\n```\n",
            ]
        else:
            reply_chunks = [
                f"[CosmicTera NUI via `{model_name}`] ",
                "Analisis selesai dengan konteks repositori dan deterministik NUI.",
            ]

        if not stream:
            return (
                200,
                {
                    "model": model_name,
                    "message": {"role": "assistant", "content": "".join(reply_chunks)},
                    "done": True,
                },
            )

        stream_packets = [
            {
                "model": model_name,
                "message": {"role": "assistant", "content": ch},
                "done": False,
            }
            for ch in reply_chunks
        ] + [
            {
                "model": model_name,
                "message": {"role": "assistant", "content": ""},
                "done": True,
            }
        ]
        return (200, stream_packets)

    return (404, {"error": "unknown endpoint"})


@pytest.fixture()
def nui_app_with_ollama(tmp_path: Path) -> NUILocalServiceApp:
    db_file = tmp_path / "test_nui_ollama.db"
    app = NUILocalServiceApp(db_path=db_file, use_os_keychain=False)
    app.model_library = NUIModelAssetLibrary(
        storage=app.storage,
        ollama_transport=_in_memory_ollama_transport,
    )
    app.multi_model_router = NUIMultiModelRouter(app.model_library)
    app.self_learning.asset_library = app.model_library
    app.self_learning.router = app.multi_model_router
    app.ollama_provider = OllamaProvider(
        default_model="qwen3.8:27b",
        persona_loader=app.persona_loader,
        context_retriever=app.context_retriever,
        self_learning_engine=app.self_learning,
        ollama_transport=_in_memory_ollama_transport,
    )
    app.orchestrator.model_library = app.model_library
    app.orchestrator.multi_model_router = app.multi_model_router
    app.orchestrator.ollama_provider = app.ollama_provider
    return app


def test_a_ollama_connection_and_model_discovery(nui_app_with_ollama: NUILocalServiceApp) -> None:
    """TEST A — Verify Ollama runtime connection, version, and local model discovery."""
    code, lib = nui_app_with_ollama.dispatch_request("GET", "/api/models/library")
    assert code == 200
    probe = lib["ollama_probe"]
    assert probe["service_running"] is True
    assert probe["connection_state"] == "CONNECTED"
    assert "qwen3.8:27b" in probe["model_names"]

    qwen_asset = lib["qwen38_coding_specialist"]
    assert qwen_asset["display_label"] == "NUI CODING SPECIALIST — QWEN3.8-27B"
    assert qwen_asset["ollama_tag"] == "qwen3.8:27b"


def test_b_persona_preservation_across_providers(nui_app_with_ollama: NUILocalServiceApp) -> None:
    """TEST B — Verify NUI preserves official `HybitAIProgram.system` persona on both Native and Ollama providers."""
    code_p, persona_info = nui_app_with_ollama.dispatch_request("GET", "/api/persona")
    assert code_p == 200
    assert persona_info["persona"]["persona_source"] == "src/hijaiyyah/ai/runtime.py::HybitAIProgram.system"
    assert "CosmicTera" in persona_info["system_prompt_preview"]
    assert "K1" in persona_info["system_prompt_preview"]

    code, out = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/chat",
        {
            "user_message": "Siapa kamu?",
            "provider": "local_ollama",
            "model": "qwen3.8:27b",
        },
    )
    assert code == 200
    assert out["execution_status"] == "RESPONSE_COMPLETE"
    assert "CosmicTera NUI" in out["response_text"]
    assert "Persona aktif: `True`" in out["response_text"]


def test_c_project_context_layers_l0_to_l11(nui_app_with_ollama: NUILocalServiceApp) -> None:
    """TEST C — Verify NUI answers L0–L11 status from real `NUI/LAYERS.md` & `inspect_layers()`."""
    code, out = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": "Apa status lapisan NUI L0 sampai L11?", "provider": "native_nui"},
    )
    assert code == 200
    text = out["response_text"]
    assert "L0" in text and "L11" in text
    assert "IMPLEMENTED" in text
    assert "AT (ARSITEKTUR TARGET)" in text


def test_d_deterministic_computation_and_bsm(nui_app_with_ollama: NUILocalServiceApp) -> None:
    """TEST D — Verify arithmetic (`128 * 64`) and `compute_basmalah()` run deterministically in Python, never guessed by LLM."""
    code1, out1 = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": "Hitung 128 * 64", "provider": "local_ollama"},
    )
    assert code1 == 200
    assert "8192" in out1["response_text"]
    assert out1["provider_response"]["data"]["calculation"]["result"] == 8192

    code2, out2 = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": "Hitung nilai BSM", "provider": "local_ollama"},
    )
    assert code2 == 200
    assert "(112, 10, 9)" in out2["response_text"]
    assert "SIX-GUARD PASS" in out2["response_text"]


def test_e_hisa_cpu_context_test_bsm_hasm(nui_app_with_ollama: NUILocalServiceApp) -> None:
    """TEST E — Verify `Jelaskan program test_bsm.hasm` executes the real H-ISA program on `HISAMachine` (`R1 = 112, PC = 9, cycles = 9`)."""
    code, out = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": "Jelaskan program test_bsm.hasm", "provider": "native_nui"},
    )
    assert code == 200
    assert "112" in out["response_text"]
    assert out["provider_response"]["data"]["hisa_execution"]["R1"] == 112
    assert out["provider_response"]["data"]["hisa_execution"]["PC"] == 9
    assert out["provider_response"]["data"]["hisa_execution"]["cycles"] == 9


def test_f_coding_request_with_qwen38_routing(nui_app_with_ollama: NUILocalServiceApp) -> None:
    """TEST F — Verify coding request routes to `QWEN38_CODING_SPECIALIST` and returns Python code."""
    code_r, route = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/models/op",
        {
            "op": "route",
            "query": "Buatkan fungsi Python sederhana untuk menghitung faktor bilangan",
        },
    )
    assert code_r == 200
    assert route["selected_engine"] == "QWEN38_CODING_SPECIALIST"
    assert route["selected_model"] == "qwen3.8:27b"

    code, out = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/chat",
        {
            "user_message": "Buatkan fungsi Python sederhana untuk menghitung faktor bilangan",
            "provider": "auto",
        },
    )
    assert code == 200
    assert "def faktor_bilangan" in out["response_text"]


def test_g_multi_turn_session_memory(nui_app_with_ollama: NUILocalServiceApp) -> None:
    """TEST G — Verify multi-turn conversation memory persists across turns in a session."""
    _, sess = nui_app_with_ollama.dispatch_request(
        "POST", "/api/sessions", {"title": "Multi-Turn Test", "provider": "local_ollama"}
    )
    sid = sess["session_id"]

    nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/chat",
        {
            "session_id": sid,
            "user_message": "Ingat bahwa fokus kita sekarang adalah komunikasi NUI.",
            "provider": "local_ollama",
        },
    )
    code2, out2 = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/chat",
        {
            "session_id": sid,
            "user_message": "Apa fokus kita tadi?",
            "provider": "local_ollama",
        },
    )
    assert code2 == 200
    assert "komunikasi NUI" in out2["response_text"]


def test_h_and_i_streaming_and_stop_generation(nui_app_with_ollama: NUILocalServiceApp) -> None:
    """TEST H & TEST I — Verify incremental streaming chunks and mid-stream stop cancellation."""
    events = list(
        nui_app_with_ollama.orchestrator.stream_chat_turn(
            user_message="Siapa kamu?",
            provider_id="local_ollama",
            model="qwen3.8:27b",
        )
    )
    partial_events = [e for e in events if e.get("event") == "partial_response"]
    assert len(partial_events) >= 2
    assert events[-1]["event"] == "final_response"

    stop_events = list(
        nui_app_with_ollama.orchestrator.stream_chat_turn(
            user_message="Siapa kamu?",
            provider_id="local_ollama",
            simulate_stop=True,
        )
    )
    assert stop_events[-1]["event"] == "generation_cancelled"
    assert stop_events[-1]["turn_output"]["execution_status"] == "STOPPED"


def test_j_ollama_unavailable_honest_error(tmp_path: Path) -> None:
    """TEST J — Verify honest `NUI_LANGUAGE_ENGINE_UNAVAILABLE` / `PROVIDER_UNAVAILABLE` when Ollama is offline."""
    app = NUILocalServiceApp(db_path=tmp_path / "offline.db", use_os_keychain=False)

    def _offline_transport(method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
        raise ConnectionRefusedError("Ollama daemon offline on 127.0.0.1:11434")

    app.ollama_provider = OllamaProvider(
        persona_loader=app.persona_loader,
        context_retriever=app.context_retriever,
        self_learning_engine=app.self_learning,
        ollama_transport=_offline_transport,
    )
    app.orchestrator.ollama_provider = app.ollama_provider

    code, out = app.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": "Halo Ollama", "provider": "local_ollama"},
    )
    assert code == 200
    assert out["execution_status"] == "PROVIDER_UNAVAILABLE"
    assert "NUI_LANGUAGE_ENGINE_UNAVAILABLE" in out["response_text"]


def test_qwen38_model_verification_and_lifecycle(nui_app_with_ollama: NUILocalServiceApp) -> None:
    """Verify Qwen3.8-27B select, load, verify inference (`VERIFIED`), and unload operations."""
    c_sel, res_sel = nui_app_with_ollama.dispatch_request(
        "POST", "/api/models/op", {"op": "select", "model_tag": "qwen3.8:27b"}
    )
    assert c_sel == 200
    assert res_sel["selected_model"] == "qwen3.8:27b"

    c_ver, res_ver = nui_app_with_ollama.dispatch_request(
        "POST", "/api/models/op", {"op": "verify", "model_tag": "qwen3.8:27b"}
    )
    assert c_ver == 200
    assert res_ver["verified"] is True
    assert res_ver["status"] == "VERIFIED"

    c_load, res_load = nui_app_with_ollama.dispatch_request(
        "POST", "/api/models/op", {"op": "load", "model_tag": "qwen3.8:27b"}
    )
    assert c_load == 200
    assert res_load["status"] == "READY"

    c_un, res_un = nui_app_with_ollama.dispatch_request(
        "POST", "/api/models/op", {"op": "unload", "model_tag": "qwen3.8:27b"}
    )
    assert c_un == 200
    assert res_un["status"] == "UNLOADED"


def test_autonomous_self_learning_full_lifecycle(nui_app_with_ollama: NUILocalServiceApp) -> None:
    """Verify all 7 Self-Learning requirements: ingest, index/retrieve, coding skill + pytest, reuse, feedback, rollback, immutable boundary protection."""
    c1, entry = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/self-learning/op",
        {
            "op": "ingest_knowledge",
            "topic": "Protokol Sinkronisasi HDMI Option A",
            "summary": "Sequencer reset bertahap 2.0 ms: pll_locked -> clkdiv_rst_n -> oser_rst -> video_rst_n.",
            "source": "cosmictera-build/stage-1-5-unified-soc/hdmi_option_a_11452b9c",
            "confidence": "Verified",
            "applicable_domain": "fpga_hdmi",
        },
    )
    assert c1 == 200
    assert entry["validation_status"] == "VALIDATED"

    c2, ctx = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/context/retrieve",
        {"query": "Protokol Sinkronisasi HDMI Option A clkdiv_rst_n", "top_k": 5},
    )
    assert c2 == 200
    assert any("clkdiv_rst_n" in item["excerpt"] for item in ctx["items"])

    c3, skill_ok = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/self-learning/op",
        {
            "op": "run_coding_skill",
            "skill_name": "gcd_euclid_skill",
            "problem_statement": "Compute greatest common divisor deterministically",
            "module_code": (
                "def gcd_euclid(a: int, b: int) -> int:\n"
                "    while b:\n"
                "        a, b = b, a % b\n"
                "    return abs(a)\n"
            ),
            "test_code": (
                "from learned_skill_mod import gcd_euclid\n"
                "def test_gcd():\n"
                "    assert gcd_euclid(112, 14) == 14\n"
                "    assert gcd_euclid(28, 18) == 2\n"
            ),
            "applicable_domain": "hijaiyyah_math_helpers",
        },
    )
    assert c3 == 200
    assert skill_ok["passed"] is True
    assert skill_ok["validation_status"] == "VALIDATED"
    assert skill_ok["knowledge_entry_id"] is not None

    _, skill_fail = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/self-learning/op",
        {
            "op": "run_coding_skill",
            "skill_name": "broken_skill",
            "problem_statement": "Intentional failure test",
            "module_code": "def bad_fn(): return 1\n",
            "test_code": "from learned_skill_mod import bad_fn\ndef test_bad(): assert bad_fn() == 999\n",
        },
    )
    assert skill_fail["passed"] is False
    assert skill_fail["validation_status"] == "REJECTED_FAILED_TESTS"
    assert skill_fail["knowledge_entry_id"] is None

    learned_matches = nui_app_with_ollama.self_learning.retrieve_learned_items("gcd_euclid_skill")
    assert any(m["topic"] == "Coding Skill: gcd_euclid_skill" for m in learned_matches)

    c5, fb = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/self-learning/op",
        {
            "op": "feedback",
            "topic": "Protokol Sinkronisasi HDMI Option A",
            "correction_summary": "Pastikan urutan reset menyebutkan register 1-siklus DVI (red_dvi..vsync_dvi).",
            "target_entry_id": entry["entry_id"],
        },
    )
    assert c5 == 200
    assert fb["confidence"] == "User Provided"
    superseded = nui_app_with_ollama.self_learning.get_entry(entry["entry_id"])
    assert superseded is not None
    assert superseded["validation_status"] == "SUPERSEDED_BY_USER_FEEDBACK"

    c6, rb = nui_app_with_ollama.dispatch_request(
        "POST",
        "/api/self-learning/op",
        {
            "op": "rollback",
            "entry_id": fb["entry_id"],
            "reason": "Testing snapshot rollback",
        },
    )
    assert c6 == 200
    assert rb["rolled_back"] is True
    after_rb = nui_app_with_ollama.self_learning.get_entry(fb["entry_id"])
    assert after_rb is not None
    assert after_rb["active"] == 0
    assert after_rb["validation_status"] == "ROLLED_BACK"

    for protected_domain in (
        "NUI_PERSONA",
        "NUI_L0_L11_DEFINITIONS",
        "HIJAIYYAH_MATHEMATICS_CONSTANTS",
        "HISA_CPU_SEMANTICS",
        "PERMISSION_SECURITY_POLICY",
    ):
        c7, bound = nui_app_with_ollama.dispatch_request(
            "POST",
            "/api/self-learning/op",
            {
                "op": "check_boundary",
                "target_domain": protected_domain,
                "proposed_change": "Override core rule",
            },
        )
        assert c7 == 200
        assert bound["allowed"] is False
        assert bound["status"] == "BLOCKED_IMMUTABLE_BOUNDARY"


def test_mac_resource_telemetry_and_10_submenus(nui_app_with_ollama: NUILocalServiceApp) -> None:
    """Verify Mac resource telemetry and all 10 NUI Self-Learning Center submenus."""
    res = measure_mac_host_resources()
    assert res["memory_total_gb"] >= 16.0
    assert res["disk_free_gb"] > 5.0
    assert "qwen38_27b_fit" in res

    code, ov = nui_app_with_ollama.dispatch_request("GET", "/api/self-learning/overview")
    assert code == 200
    for key in (
        "1_learning_overview",
        "2_knowledge_base",
        "3_coding_skills",
        "4_model_assets",
        "5_learning_history",
        "6_feedback",
        "7_evaluation",
        "8_skill_validation",
        "9_model_performance",
        "10_learning_configuration",
    ):
        assert key in ov
