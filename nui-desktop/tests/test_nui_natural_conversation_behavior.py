"""Acceptance Test Suite for Owner Directive — CosmicTera NUI Natural Conversation & Response Behavior (TEST A – TEST G).

Verifies:
- TEST A: User "Hai." -> Concise natural greeting ("Halo! Ada yang bisa saya bantu?"), no system status dump.
- TEST B: User "Kamu siapa?" -> Short natural introduction from official NUI persona (`HybitAIProgram.system`), no raw MASTER_TABLE/opcode/KB dump.
- TEST C: User "Cek repository." -> Short confirmation, real repository inspection (`Sedang memeriksa repository...`), and concise summary asking if user wants details.
- TEST D: User "Berapa 5 + 7?" -> Direct answer "Hasilnya 12." computed deterministically via HISAMachine.
- TEST E: User "Jelaskan lebih detail." -> Understands prior turn context (math or repository check) and provides detailed explanation.
- TEST F: User "Tampilkan seluruh hasil audit." -> Only at this stage does NUI output the full multi-section audit report.
- TEST G: Streaming output from active Ollama/Qwen model arrives incrementally (`partial_response`) and strictly strips/separates `thinking` fields and `<think>...</think>` blocks from chat `content`.
- Section 4 & 8: No repeated self-introductions in the same session, no unrequested system status in chat, and no raw retrieval snippet dumps.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
if str(NUI_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(NUI_DESKTOP_ROOT))

from backend.persona_and_context import classify_response_mode, strip_internal_thinking
from backend.providers import OllamaProvider
from backend.self_learning import NUIModelAssetLibrary, NUIMultiModelRouter
from backend.server import NUILocalServiceApp


def _ollama_with_thinking_transport(
    method: str, path: str, body: dict[str, Any] | None = None
) -> tuple[int, Any]:
    """Mock Ollama transport that emits both `thinking` fields and `<think>...</think>` tags to test strict separation."""
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
                        }
                    ]
                },
            )
        if path == "/api/ps":
            return (200, {"models": [{"name": "qwen3.8:27b", "model": "qwen3.8:27b"}]})
        return (404, {"error": "not found"})

    payload = body or {}
    if path == "/api/chat":
        model_name = payload.get("model", "qwen3.8:27b")
        stream = bool(payload.get("stream", False))

        assert payload.get("think") is False

        if not stream:
            return (
                200,
                {
                    "model": model_name,
                    "message": {
                        "role": "assistant",
                        "thinking": "INTERNAL_CHAIN_OF_THOUGHT_MUST_NOT_APPEAR",
                        "content": "<think>SECRET_DRAFT_REASONING</think>Halo! Saya NUI dari CosmicTera. Ada yang bisa saya bantu?",
                    },
                    "done": True,
                },
            )

        stream_packets = [
            {
                "model": model_name,
                "message": {
                    "role": "assistant",
                    "thinking": "STEP_1_INTERNAL_REASONING_HIDDEN",
                    "content": "<think>INTERNAL_THOUGHT_CHUNK_1 ",
                },
                "done": False,
            },
            {
                "model": model_name,
                "message": {
                    "role": "assistant",
                    "thinking": "STEP_2_INTERNAL_REASONING_HIDDEN",
                    "content": "INTERNAL_THOUGHT_CHUNK_2</think>Halo! Saya NUI ",
                },
                "done": False,
            },
            {
                "model": model_name,
                "message": {
                    "role": "assistant",
                    "content": "dari CosmicTera. ",
                },
                "done": False,
            },
            {
                "model": model_name,
                "message": {
                    "role": "assistant",
                    "content": "Ada yang bisa saya bantu?",
                },
                "done": False,
            },
            {
                "model": model_name,
                "message": {"role": "assistant", "content": ""},
                "done": True,
            },
        ]
        return (200, stream_packets)

    return (404, {"error": "unknown"})


@pytest.fixture()
def app(tmp_path: Path) -> NUILocalServiceApp:
    return NUILocalServiceApp(db_path=tmp_path / "natural_conv.db", use_os_keychain=False)


def test_acceptance_a_to_f_multi_turn_natural_conversation(app: NUILocalServiceApp) -> None:
    """Verify Acceptance Tests A, B, C, D, E, and F in a single natural multi-turn session."""
    _, sess = app.dispatch_request("POST", "/api/sessions", {"title": "Natural Conversation Acceptance"})
    sid = sess["session_id"]

    # TEST A: User: "Hai." -> Expected: "Halo! Ada yang bisa saya bantu?"
    code_a, out_a = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Hai."},
    )
    assert code_a == 200
    assert out_a["response_text"] == "Halo! Ada yang bisa saya bantu?"
    assert "LOCAL SERVICE READY" not in out_a["response_text"]
    assert "PROVIDER CONNECTED" not in out_a["response_text"]
    assert out_a["provider_response"]["data"]["response_mode"] == "CONVERSATIONAL"

    # TEST B: User: "Kamu siapa?" -> Concise introduction from official NUI persona, no raw KB dump
    code_b, out_b = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Kamu siapa?"},
    )
    assert code_b == 200
    txt_b = out_b["response_text"]
    assert "NUI" in txt_b
    assert "Natural Universal Intelligence" in txt_b
    assert "CosmicTera" in txt_b
    assert not txt_b.startswith("Halo!")
    assert "MASTER_TABLE" not in txt_b
    assert "LOCAL SERVICE READY" not in txt_b

    # TEST C: User: "Cek repository." -> Short confirmation, real inspection, concise summary
    events_c = list(
        app.orchestrator.stream_chat_turn(
            session_id=sid,
            user_message="Cek repository.",
        )
    )
    tool_events_c = [e for e in events_c if e.get("event") == "tool_call"]
    assert any(e.get("activity") == "Sedang memeriksa repository..." for e in tool_events_c)
    txt_c = events_c[-1]["response_text"]
    assert "Baik, saya akan memeriksa repository CosmicTera." in txt_c
    assert "Repository berhasil diperiksa. Saya menemukan beberapa komponen utama pada HCPU, H-ISA, dan NUI." in txt_c
    assert "Apakah Anda ingin melihat ringkasan hasil pemeriksaannya?" in txt_c
    assert "DP" not in txt_c and "VF" not in txt_c

    # Follow-up on TEST C: User asks for detail on the repo check
    code_c2, out_c2 = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Jelaskan lebih detail."},
    )
    assert code_c2 == 200
    assert "HCPU" in out_c2["response_text"]
    assert "H-ISA" in out_c2["response_text"]
    assert "NUI L0–L11" in out_c2["response_text"]

    # TEST D: User: "Berapa 5 + 7?" -> Expected: "Hasilnya 12."
    code_d, out_d = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Berapa 5 + 7?"},
    )
    assert code_d == 200
    assert out_d["response_text"] == "Hasilnya 12."
    assert out_d["provider_response"]["data"]["result"] == 12

    # TEST E: User: "Jelaskan lebih detail." -> Understands previous math turn ("Berapa 5 + 7?") and explains
    code_e, out_e = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Jelaskan lebih detail."},
    )
    assert code_e == 200
    txt_e = out_e["response_text"]
    assert "5 + 7 = 12" in txt_e
    assert "HISAMachine" in txt_e
    assert "MOVI" in txt_e

    # TEST F: User: "Tampilkan seluruh hasil audit." -> Full multi-section report delivered only now
    code_f, out_f = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Tampilkan seluruh hasil audit."},
    )
    assert code_f == 200
    txt_f = out_f["response_text"]
    assert out_f["provider_response"]["data"]["response_mode"] == "DEEP_RESEARCH"
    assert "1. Status Git & Inventaris Kode" in txt_f
    assert "2. Subsistem Komputasi Utama" in txt_f
    assert "3. Status Lapisan NUI L0–L11" in txt_f


def test_acceptance_g_ollama_streaming_and_internal_thinking_separation(tmp_path: Path) -> None:
    """TEST G: Verify streaming output comes from active Ollama/Qwen model and never exposes `thinking` or `<think>`."""
    app = NUILocalServiceApp(db_path=tmp_path / "ollama_think.db", use_os_keychain=False)
    app.model_library = NUIModelAssetLibrary(
        storage=app.storage,
        ollama_transport=_ollama_with_thinking_transport,
    )
    app.multi_model_router = NUIMultiModelRouter(app.model_library)
    app.ollama_provider = OllamaProvider(
        default_model="qwen3.8:27b",
        persona_loader=app.persona_loader,
        context_retriever=app.context_retriever,
        self_learning_engine=app.self_learning,
        ollama_transport=_ollama_with_thinking_transport,
    )
    app.orchestrator.model_library = app.model_library
    app.orchestrator.multi_model_router = app.multi_model_router
    app.orchestrator.ollama_provider = app.ollama_provider

    events = list(
        app.orchestrator.stream_chat_turn(
            user_message="Hai NUI.",
            provider_id="local_ollama",
            model="qwen3.8:27b",
        )
    )
    partials = [e for e in events if e.get("event") == "partial_response"]
    assert len(partials) == 3

    for p in partials:
        assert "INTERNAL_CHAIN_OF_THOUGHT" not in p["delta"]
        assert "STEP_1_INTERNAL_REASONING" not in p["delta"]
        assert "INTERNAL_THOUGHT_CHUNK" not in p["delta"]
        assert "<think>" not in p["delta"]
        assert "</think>" not in p["delta"]

    final_ev = events[-1]
    assert final_ev["event"] == "final_response"
    assert final_ev["response_text"] == "Halo! Saya NUI dari CosmicTera. Ada yang bisa saya bantu?"
    assert final_ev["turn_output"]["provider_response"]["data"]["internal_thinking_filtered"] is True


def test_response_mode_classifier_and_think_stripper() -> None:
    """Verify response mode classification across all 6 modes and `<think>` stripping."""
    assert classify_response_mode("Hai.")["mode"] == "CONVERSATIONAL"
    assert classify_response_mode("Kamu siapa?")["mode"] == "CONVERSATIONAL"
    assert classify_response_mode("Berapa 5 + 7?")["mode"] == "CONVERSATIONAL"
    assert classify_response_mode("Cek repository.")["mode"] == "REPOSITORY_AUDIT"
    assert classify_response_mode("Tampilkan seluruh hasil audit.")["mode"] == "DEEP_RESEARCH"
    assert classify_response_mode("Apa status koneksi sistem?")["mode"] == "SYSTEM_DIAGNOSTICS"
    assert classify_response_mode("Jelaskan hubungan Hybit 18D dengan Matematika Hijaiyyah.")["mode"] == "TECHNICAL"

    cleaned, had = strip_internal_thinking("<think> penalaran internal </think>Jawaban bersih.")
    assert had is True
    assert cleaned == "Jawaban bersih."
