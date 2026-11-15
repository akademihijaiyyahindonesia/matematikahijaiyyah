"""Mandatory 10-case Relevance & Irrelevant Knowledge Injection Regression Test Suite for CosmicTera NUI Desktop.

Verifies all 10 mandatory test cases from the Critical Bug Directive:
1. "Kamu bisa membantu pengembangan software?" (and exact audit log spelling "kamu bisa membantu pengembangan sofwer")
2. "Bagaimana cara kamu coding?"
3. "Bahasa pemrograman apa yang bisa kamu bantu?"
4. "Bisa memperbaiki bug Python?"
5. "Bisa membuat website?"
6. "Contohnya?"
7. "Apakah kamu bisa membaca repository CosmicTera?"
8. "Cek sistem."
9. "Jelaskan watchdog pada desain CosmicTera."
10. "Berapa clock drift yang tercatat?"
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
if str(NUI_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(NUI_DESKTOP_ROOT))

from backend.persona_and_context import (
    NUIContextualRetriever,
    classify_response_mode,
)
from backend.server import NUILocalServiceApp


@pytest.fixture()
def nui_app(tmp_path: Path) -> NUILocalServiceApp:
    db_file = tmp_path / "test_nui_relevance_repair.db"
    return NUILocalServiceApp(db_path=db_file, use_os_keychain=False)


def _assert_no_burnin_injection(reply_text: str, retrieved_sources: list[dict]) -> None:
    lower_reply = reply_text.lower()
    assert "burnin.no_watchdog_exists" not in lower_reply
    assert "burnin.tier1_clock_drift" not in lower_reply
    assert "tidak ada modul watchdog" not in lower_reply
    assert "hanyut jam papan" not in lower_reply
    for src in retrieved_sources:
        excerpt_low = str(src.get("excerpt", "")).lower()
        assert "burnin.no_watchdog_exists" not in excerpt_low
        assert "burnin.tier1_clock_drift" not in excerpt_low


def test_01_software_development_capability_and_logged_typo(nui_app: NUILocalServiceApp) -> None:
    """Test 1: 'Kamu bisa membantu pengembangan software?' & 'kamu bisa membantu pengembangan sofwer'."""
    retriever = NUIContextualRetriever()
    for prompt in (
        "Kamu bisa membantu pengembangan software?",
        "kamu bisa membantu pengembangan sofwer",
        "pengembangan sofwer ?",
        "buat rancangan program sofwer bis ?",
        "Kamu bisa membantu penegmbangan softer ?",
        "kamu bisa bantu poengembangan sofwer",
    ):
        mode = classify_response_mode(prompt)
        assert mode["mode"] == "CAPABILITY_INQUIRY"
        assert mode["sub_intent"] == "software_development_capability"
        assert retriever.retrieve(prompt) == []

        code, out = nui_app.dispatch_request(
            "POST",
            "/api/chat",
            {"user_message": prompt, "provider": "native_nui"},
        )
        assert code == 200
        reply = out["response_text"]
        retrieved = out["provider_response"]["data"].get("retrieved_sources", [])
        _assert_no_burnin_injection(reply, retrieved)
        assert "menganalisis source code" in reply
        assert "merancang program" in reply
        assert "menulis dan memperbaiki kode" in reply
        assert "unit test" in reply
        assert "debugging" in reply
        assert "website dan aplikasi" in reply
        assert "sesuai izin Anda" in reply

        # Verify streaming emits incremental partial_response deltas
        partial_events = [
            ev for ev in out.get("stream_events", []) if ev.get("event") == "partial_response"
        ]
        assert len(partial_events) >= 2


def test_02_how_do_you_code(nui_app: NUILocalServiceApp) -> None:
    """Test 2: 'Bagaimana cara kamu coding?'."""
    prompt = "Bagaimana cara kamu coding?"
    mode = classify_response_mode(prompt)
    assert mode["mode"] == "CAPABILITY_INQUIRY"
    assert mode["sub_intent"] == "coding_workflow_capability"
    assert nui_app.context_retriever.retrieve(prompt) == []

    code, out = nui_app.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": prompt, "provider": "native_nui"},
    )
    assert code == 200
    reply = out["response_text"]
    retrieved = out["provider_response"]["data"].get("retrieved_sources", [])
    _assert_no_burnin_injection(reply, retrieved)
    assert "files.read" in reply
    assert "coding.edit" in reply
    assert "pytest" in reply


def test_03_programming_languages_supported(nui_app: NUILocalServiceApp) -> None:
    """Test 3: 'Bahasa pemrograman apa yang bisa kamu bantu?'."""
    prompt = "Bahasa pemrograman apa yang bisa kamu bantu?"
    mode = classify_response_mode(prompt)
    assert mode["mode"] == "CAPABILITY_INQUIRY"
    assert mode["sub_intent"] == "programming_languages_capability"
    assert nui_app.context_retriever.retrieve(prompt) == []

    code, out = nui_app.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": prompt, "provider": "native_nui"},
    )
    assert code == 200
    reply = out["response_text"]
    retrieved = out["provider_response"]["data"].get("retrieved_sources", [])
    _assert_no_burnin_injection(reply, retrieved)
    for lang in ("Python", "Swift", "JavaScript", "Verilog", "H-ISA", "Hybit Code"):
        assert lang in reply


def test_04_can_fix_python_bugs(nui_app: NUILocalServiceApp) -> None:
    """Test 4: 'Bisa memperbaiki bug Python?'."""
    prompt = "Bisa memperbaiki bug Python?"
    mode = classify_response_mode(prompt)
    assert mode["mode"] == "CAPABILITY_INQUIRY"
    assert mode["sub_intent"] == "python_debugging_capability"
    assert nui_app.context_retriever.retrieve(prompt) == []

    code, out = nui_app.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": prompt, "provider": "native_nui"},
    )
    assert code == 200
    reply = out["response_text"]
    retrieved = out["provider_response"]["data"].get("retrieved_sources", [])
    _assert_no_burnin_injection(reply, retrieved)
    assert "bug Python" in reply
    assert "traceback" in reply.lower()
    assert "pytest" in reply


def test_05_can_build_website(nui_app: NUILocalServiceApp) -> None:
    """Test 5: 'Bisa membuat website?'."""
    prompt = "Bisa membuat website?"
    mode = classify_response_mode(prompt)
    assert mode["mode"] == "CAPABILITY_INQUIRY"
    assert mode["sub_intent"] == "website_development_capability"
    assert nui_app.context_retriever.retrieve(prompt) == []

    code, out = nui_app.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": prompt, "provider": "native_nui"},
    )
    assert code == 200
    reply = out["response_text"]
    retrieved = out["provider_response"]["data"].get("retrieved_sources", [])
    _assert_no_burnin_injection(reply, retrieved)
    assert "website" in reply.lower()
    assert "HTML" in reply
    assert "CSS" in reply
    assert "JavaScript" in reply


def test_06_contextual_followup_contohnya(nui_app: NUILocalServiceApp) -> None:
    """Test 6: Multi-turn follow-up 'Contohnya?' after asking about software development."""
    _, sess = nui_app.dispatch_request(
        "POST", "/api/sessions", {"title": "Test Relevance Multi-Turn"}
    )
    sid = sess["session_id"]

    # Turn 1: Ask capability question
    nui_app.dispatch_request(
        "POST",
        "/api/chat",
        {
            "session_id": sid,
            "user_message": "Kamu bisa membantu pengembangan software?",
            "provider": "native_nui",
        },
    )

    # Turn 2: Follow-up "Contohnya?"
    prompt = "Contohnya?"
    assert nui_app.context_retriever.retrieve(prompt) == []
    code, out = nui_app.dispatch_request(
        "POST",
        "/api/chat",
        {
            "session_id": sid,
            "user_message": prompt,
            "provider": "native_nui",
        },
    )
    assert code == 200
    reply = out["response_text"]
    retrieved = out["provider_response"]["data"].get("retrieved_sources", [])
    _assert_no_burnin_injection(reply, retrieved)
    assert "contoh konkret" in reply.lower()
    assert "Kamu bisa membantu pengembangan software?" in reply


def test_07_can_read_cosmictera_repository(nui_app: NUILocalServiceApp) -> None:
    """Test 7: 'Apakah kamu bisa membaca repository CosmicTera?'."""
    prompt = "Apakah kamu bisa membaca repository CosmicTera?"
    mode = classify_response_mode(prompt)
    assert mode["mode"] == "CAPABILITY_INQUIRY"
    assert mode["sub_intent"] == "repository_reading_capability"
    assert nui_app.context_retriever.retrieve(prompt) == []

    code, out = nui_app.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": prompt, "provider": "native_nui"},
    )
    assert code == 200
    reply = out["response_text"]
    retrieved = out["provider_response"]["data"].get("retrieved_sources", [])
    _assert_no_burnin_injection(reply, retrieved)
    assert "membaca dan menganalisis repository CosmicTera" in reply
    assert "PermissionEngine" in reply


def test_08_system_diagnostics_cek_sistem(nui_app: NUILocalServiceApp) -> None:
    """Test 8: 'Cek sistem.'."""
    prompt = "Cek sistem."
    mode = classify_response_mode(prompt)
    assert mode["mode"] == "SYSTEM_DIAGNOSTICS"
    assert nui_app.context_retriever.retrieve(prompt) == []

    code, out = nui_app.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": prompt, "provider": "native_nui"},
    )
    assert code == 200
    reply = out["response_text"]
    retrieved = out["provider_response"]["data"].get("retrieved_sources", [])
    _assert_no_burnin_injection(reply, retrieved)
    assert "LOCAL SERVICE READY" in reply
    assert "PROVIDER CONNECTED" in reply


def test_09_explicit_watchdog_question_retrieves_burnin_fact(nui_app: NUILocalServiceApp) -> None:
    """Test 9: 'Jelaskan watchdog pada desain CosmicTera.' MUST retrieve burnin.no_watchdog_exists."""
    prompt = "Jelaskan watchdog pada desain CosmicTera."
    mode = classify_response_mode(prompt)
    assert mode["mode"] == "TECHNICAL"

    sources = nui_app.context_retriever.retrieve(prompt)
    assert len(sources) >= 1
    fact_sources = [s for s in sources if s.epistemic_class == "REPOSITORY_FACT"]
    assert len(fact_sources) == 1
    assert "burnin.no_watchdog_exists" in fact_sources[0].excerpt

    code, out = nui_app.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": prompt, "provider": "native_nui"},
    )
    assert code == 200
    reply = out["response_text"]
    assert "burnin.no_watchdog_exists" in reply
    assert "tidak ada modul **watchdog**" in reply or "tidak ada modul watchdog" in reply.lower()
    assert out["provider_response"]["data"]["fact_id"] == "burnin.no_watchdog_exists"


def test_10_explicit_clock_drift_question_retrieves_burnin_fact(nui_app: NUILocalServiceApp) -> None:
    """Test 10: 'Berapa clock drift yang tercatat?' MUST retrieve burnin.tier1_clock_drift."""
    prompt = "Berapa clock drift yang tercatat?"
    mode = classify_response_mode(prompt)
    assert mode["mode"] == "TECHNICAL"

    sources = nui_app.context_retriever.retrieve(prompt)
    assert len(sources) >= 1
    fact_sources = [s for s in sources if s.epistemic_class == "REPOSITORY_FACT"]
    assert len(fact_sources) == 1
    assert "burnin.tier1_clock_drift" in fact_sources[0].excerpt

    code, out = nui_app.dispatch_request(
        "POST",
        "/api/chat",
        {"user_message": prompt, "provider": "native_nui"},
    )
    assert code == 200
    reply = out["response_text"]
    assert "burnin.tier1_clock_drift" in reply
    assert "0,0292 detik per jam" in reply
    assert "8,1 ppm" in reply
    assert out["provider_response"]["data"]["fact_id"] == "burnin.tier1_clock_drift"
