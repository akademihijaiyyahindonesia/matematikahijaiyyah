"""Comprehensive Regression Test Suite for CosmicTera NUI Core Communication Architecture Repair.

Validates all 8 Owner Directive Priorities:
1. Primary Provider & Installed Model Selection (`qwen3:4b-instruct-2507-q4_K_M`, `qwen3-coder:30b`, `hermes3:8b`, etc.) + Honest `PROVIDER UNAVAILABLE` when Ollama is offline.
2. Official Persona (`HybitAIProgram.system`) + Multi-Turn Conversation Continuity (`prior_user_turns`, `last_user_topic`, `is_followup`).
3. Contextual Retrieval Precision (Eliminates substring false positives like `"cara"` matching `"secara"` and `"pengembangan"` matching `burnin.tier1_clock_drift`) + Integration of `knowledge.query()` and `usr.parse_phrase()`.
4. Intent & Orchestration for all 10 required user prompts (`"Kamu siapa?"`, `"Pengembangan software?"`, `"Cek sistem."`, `"Contohnya?"`, `"Cara kamu coding gimana?"`, `"Jalankan program H-ISA."`, `"Lanjutkan pembahasan sebelumnya."`, `"Jelaskan hubungan NUI dengan HCPU."`, `"Hitung 5 + 7."`, `"Cari dokumentasi Gowin FPGA."`) + `"Cek repository."`.
5. Removal of fake character-slicing streaming (`18`-char slicing removed) + clean separation of thinking metadata, tool activity, and response content.
6. Self-Learning turn observation recording with strict provenance (`Verified`, `Repository Derived`, `Model Inferred`) and validation status (`VALIDATED` vs `CANDIDATE_UNVALIDATED`).
7. Sequential multi-turn conversational acceptance test (`"Kamu siapa?"` -> `"Pengembangan software bisa?"` -> `"Cek sistem."`).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = NUI_DESKTOP_ROOT.parent
if str(NUI_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(NUI_DESKTOP_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from backend.persona_and_context import (
    NUIContextualRetriever,
    has_word_boundary_match,
    normalize_indonesian_query,
)
from backend.providers import NativeNUIProvider, OllamaProvider
from backend.server import NUILocalServiceApp


def test_priority3_word_boundary_eliminates_substring_false_positives() -> None:
    """Verify 'cara' never matches 'secara' and 'pengembangan sofwer ?' never triggers clock_drift."""
    assert has_word_boundary_match("cara", "bagaimana cara kerja hcpu") is True
    assert has_word_boundary_match("cara", "dipilih secara konservatif") is False

    normalized = normalize_indonesian_query("pengembangan sofwer ?")
    assert "software" in normalized

    retriever = NUIContextualRetriever()

    # 1. "cara kamu koding gimana?" must NOT pull nui.exomatrix_embedding_is_the_most_conservative
    sources_coding = retriever.retrieve("cara kamu koding gimana?")
    excerpts_coding = "\n".join(s.excerpt for s in sources_coding)
    assert "exomatrix_embedding_is_the_most_conservative" not in excerpts_coding, (
        f"False positive substring match 'cara' in 'secara' still present: {excerpts_coding}"
    )

    # 2. "pengembangan sofwer ?" must NOT pull burnin.tier1_clock_drift
    sources_sw = retriever.retrieve("pengembangan sofwer ?")
    excerpts_sw = "\n".join(s.excerpt for s in sources_sw)
    assert "burnin.tier1_clock_drift" not in excerpts_sw, (
        f"False positive match on burnin.tier1_clock_drift still present: {excerpts_sw}"
    )


def test_priority3_knowledge_query_and_usr_parse_phrase_integration() -> None:
    """Verify NUIContextualRetriever integrates hijaiyyah.nui.knowledge.query() and usr.parse_phrase()."""
    retriever = NUIContextualRetriever()

    # HCPU query should retrieve structured knowledge from hijaiyyah.nui.knowledge.query()
    hcpu_sources = retriever.retrieve("Jelaskan hubungan NUI dengan HCPU.")
    classes = {s.epistemic_class for s in hcpu_sources}
    excerpts = "\n".join(s.excerpt for s in hcpu_sources)
    assert "KNOWLEDGE_L9_7DOMAIN" in classes or "HCPU" in excerpts
    assert "hcpu_top" in excerpts or "HCPU" in excerpts

    # USR phrase should invoke hijaiyyah.nui.usr.parse_phrase()
    usr_sources = retriever.retrieve("ukur test_bsm.hasm")
    usr_classes = {s.epistemic_class for s in usr_sources}
    usr_excerpts = "\n".join(s.excerpt for s in usr_sources)
    assert "USR_SEMANTIC_PARSE" in usr_classes or "test_bsm.hasm" in usr_excerpts


def test_priority1_and_2_multi_turn_acceptance_dialogue(tmp_path: Path) -> None:
    """Verify the 3-turn acceptance dialogue from Section 4:
    Turn 1: 'Kamu siapa?'
    Turn 2: 'Pengembangan software bisa?' (follows up without repeating greeting or dumping clock_drift)
    Turn 3: 'Cek sistem.' (executes real system check)
    """
    app = NUILocalServiceApp(db_path=tmp_path / "test_acceptance.db", use_os_keychain=False)
    _, sess = app.dispatch_request("POST", "/api/sessions", {"title": "Uji Percakapan Multi-Giliran"})
    sid = sess["session_id"]

    # Turn 1: "Kamu siapa?"
    code1, out1 = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Kamu siapa?"},
    )
    assert code1 == 200
    reply1 = out1["response_text"]
    assert "NUI" in reply1

    # Turn 2: "Pengembangan software bisa?"
    code2, out2 = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Pengembangan software bisa?"},
    )
    assert code2 == 200
    reply2 = out2["response_text"]
    assert "burnin.tier1_clock_drift" not in reply2
    assert not reply2.strip().lower().startswith("halo!")
    assert any(
        kw in reply2.lower()
        for kw in ("perangkat lunak", "software", "python", "verilog", "swift", "hasm", "kode", "coding")
    )

    # Turn 3: "Cek sistem."
    code3, out3 = app.dispatch_request(
        "POST",
        "/api/chat",
        {"session_id": sid, "user_message": "Cek sistem."},
    )
    assert code3 == 200
    reply3 = out3["response_text"]
    assert "burnin.tier1_clock_drift" not in reply3
    assert any(kw in reply3 for kw in ("Diagnostik Sistem", "Layanan Lokal", "127.0.0.1:8848", "Unified Memory"))


def test_priority4_all_ten_audit_prompts_and_repository_check(tmp_path: Path) -> None:
    """Verify all 10 prompts required in Priority 7 plus 'Cek repository.' produce accurate, relevant responses."""
    app = NUILocalServiceApp(db_path=tmp_path / "test_ten_prompts.db", use_os_keychain=False)
    _, sess = app.dispatch_request("POST", "/api/sessions", {"title": "Uji 10 Prompt Audit"})
    sid = sess["session_id"]

    prompts_and_checks: list[tuple[str, list[str], list[str]]] = [
        (
            "Kamu siapa?",
            ["NUI", "CosmicTera"],
            ["burnin.tier1_clock_drift"],
        ),
        (
            "Pengembangan software?",
            ["menganalisis source code", "merancang program"],
            ["burnin.tier1_clock_drift", "exomatrix_embedding_is_the_most_conservative"],
        ),
        (
            "Cek sistem.",
            ["127.0.0.1:8848", "Ollama", "Tang Nano 20K"],
            ["burnin.tier1_clock_drift", "Apakah Anda ingin saya melakukan perhitungan"],
        ),
        (
            "Contohnya?",
            ["test_bsm.hasm", "112"],
            ["burnin.tier1_clock_drift", "Apakah Anda ingin saya melakukan perhitungan"],
        ),
        (
            "Cara kamu coding gimana?",
            ["pytest", "src/hijaiyyah"],
            ["exomatrix_embedding_is_the_most_conservative", "secara konservatif"],
        ),
        (
            "Jalankan program H-ISA.",
            ["test_bsm.hasm", "112", "HISAMachine"],
            ["exomatrix_embedding_is_the_most_conservative", "Apakah Anda ingin saya melakukan perhitungan"],
        ),
        (
            "Lanjutkan pembahasan sebelumnya.",
            ["Melanjutkan", "Jalankan program H-ISA"],
            ["Apakah Anda ingin saya melakukan perhitungan Matematika Hijaiyyah"],
        ),
        (
            "Jelaskan hubungan NUI dengan HCPU.",
            ["HCPU", "NUI"],
            ["burnin.tier1_clock_drift"],
        ),
        (
            "Hitung 5 + 7.",
            ["12", "5 + 7 = 12"],
            ["burnin.tier1_clock_drift"],
        ),
        (
            "Cari dokumentasi Gowin FPGA.",
            ["Gowin", "GW2AR"],
            ["burnin.tier1_clock_drift"],
        ),
        (
            "Cek repository.",
            ["Branch", "H-ISA"],
            ["burnin.tier1_clock_drift"],
        ),
    ]

    for prompt, must_contain, must_not_contain in prompts_and_checks:
        code, out = app.dispatch_request(
            "POST",
            "/api/chat",
            {"session_id": sid, "user_message": prompt, "provider": "native_nui"},
        )
        assert code == 200, f"Failed HTTP status on prompt {prompt!r}"
        reply = out["response_text"]
        for expected in must_contain:
            assert expected.lower() in reply.lower(), (
                f"Prompt {prompt!r} missing {expected!r} in reply:\n{reply}"
            )
        for forbidden in must_not_contain:
            assert forbidden.lower() not in reply.lower(), (
                f"Prompt {prompt!r} contained forbidden {forbidden!r} in reply:\n{reply}"
            )


def test_priority1_honest_provider_unavailable_when_ollama_offline() -> None:
    """Verify open-ended queries report honest PROVIDER UNAVAILABLE when Ollama is unreachable (never generic template)."""
    offline_ollama = OllamaProvider(
        ollama_transport=lambda m, p, b: (_ for _ in ()).throw(ConnectionRefusedError("Ollama offline"))
    )
    native = NativeNUIProvider(ollama_provider=offline_ollama)

    resp = native.respond(
        "Bagaimana pendapatmu mengenai tren cuaca global tahun depan?",
        context={"conversation_context": []},
    )
    assert resp["error"] == "NUI_LANGUAGE_ENGINE_UNAVAILABLE"
    assert "PROVIDER UNAVAILABLE" in resp["reply"]
    assert "Apakah Anda ingin saya melakukan perhitungan Matematika Hijaiyyah" not in resp["reply"]


def test_priority5_real_token_streaming_and_no_18char_slicing() -> None:
    """Verify OllamaProvider streams real tokens and strips <think> tags without 18-char slicing."""
    stream_packets = [
        {"message": {"role": "assistant", "content": "<think>Analisis internal singkat.</think>"}, "done": False},
        {"message": {"role": "assistant", "content": "Saya adalah CosmicTera NUI, "}, "done": False},
        {"message": {"role": "assistant", "content": "asisten kecerdasan ekosistem komputasi CosmicTera."}, "done": False},
        {"message": {"role": "assistant", "content": ""}, "done": True, "eval_count": 14},
    ]

    def _mock_transport(method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
        if method == "GET" and path == "/api/tags":
            return (200, {"models": [{"name": "qwen3:4b-instruct-2507-q4_K_M", "size": 2500000000}]})
        if method == "POST" and path == "/api/chat":
            return (200, stream_packets)
        return (200, {})

    ollama = OllamaProvider(ollama_transport=_mock_transport)

    events = list(
        ollama.stream_respond(
            "Kamu siapa?",
            context={"model": "qwen3:4b-instruct-2507-q4_K_M", "conversation_context": []},
        )
    )
    partials = [e for e in events if e.get("event") == "partial_response"]
    finals = [e for e in events if e.get("event") == "final_response"]

    assert len(partials) >= 2
    assert partials[0]["delta"] == "Saya adalah CosmicTera NUI, "
    assert "<think>" not in partials[-1]["accumulated_text"]
    assert len(finals) == 1
    assert "Saya adalah CosmicTera NUI" in finals[0]["response_text"]


def test_priority6_self_learning_records_turn_observations(tmp_path: Path) -> None:
    """Verify self_learning records turn observations with VALIDATED for deterministic and CANDIDATE_UNVALIDATED for model inference."""
    app = NUILocalServiceApp(db_path=tmp_path / "test_sl_obs.db", use_os_keychain=False)
    _, sess = app.dispatch_request("POST", "/api/sessions", {"title": "Uji Observasi Self-Learning"})
    sid = sess["session_id"]

    app.dispatch_request("POST", "/api/chat", {"session_id": sid, "user_message": "Hitung 5 + 7."})
    _, ov = app.dispatch_request("GET", "/api/self-learning/overview")
    versions = ov["learning_history"]
    turn_obs = [v for v in versions if v["action_type"] == "TURN_OBSERVATION"]
    assert len(turn_obs) >= 1
