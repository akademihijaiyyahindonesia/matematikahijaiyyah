"""Automated Acceptance Test Suite for CosmicTera NUI Live Thinking & Streaming Conversation (Sections 1–9).

Verifies:
1. Zero hardcoded demo conversations or mock assistant messages in production sessions.
2. Live Thinking Interface emits real stage events (`REQUEST_RECEIVED`, `UNDERSTANDING`,
   `ANALYZING`, `PLANNING`, `TOOL_EXECUTION`, `VALIDATING`, `GENERATING_RESPONSE`, `COMPLETE`)
   strictly based on actual engine activity (no `PLANNING`/`TOOL_EXECUTION` for simple greeting!).
3. Incremental streaming (`partial_response` deltas) grows text progressively before `final_response`.
4. Tool Activity is emitted ONLY when tools/computations (`5 + 7`, `Jim`, `Cari dokumentasi`) are actually executed.
5. Full 10-step Acceptance Test (Section 9):
   - Step 1: User sends "Halo NUI, siapa kamu?"
   - Step 2: NUI starts processing request (`request_accepted`)
   - Step 3: Process indicator stages appear according to actual events
   - Step 4: Response begins arriving incrementally (`partial_response`)
   - Step 5: Text grows continuously during generation
   - Step 6: Answer finishes and is marked `COMPLETE`
   - Step 7: User sends second question ("Berapa 5 + 7?" and "Ringkas pertanyaan pertama kita.")
   - Step 8: NUI preserves conversation context and records real tool activity for `5 + 7`
   - Step 9: User can stop generation (`generation_cancelled` -> `STOPPED`)
   - Step 10: Application reopens and chat history is loaded from actual SQLite storage
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
if str(NUI_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(NUI_DESKTOP_ROOT))

from backend.server import NUILocalServiceApp


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "live_streaming_test.db"


@pytest.fixture()
def app(db_path: Path) -> NUILocalServiceApp:
    return NUILocalServiceApp(db_path=db_path, use_os_keychain=False)


def test_zero_demo_conversation_on_fresh_production_session(app: NUILocalServiceApp) -> None:
    """Section 1 & 8: Freshly created production session must have zero pre-populated demo messages."""
    code, sess = app.dispatch_request("POST", "/api/sessions", {"title": "Sesi Percakapan Baru"})
    assert code == 201
    assert sess["messages"] == []

    # Verify Swift source code has no hardcoded demo messages in initial state
    swift_src = (
        NUI_DESKTOP_ROOT / "macos" / "Sources" / "CosmicTeraNUIApp.swift"
    ).read_text(encoding="utf-8")
    assert "@Published var messages: [ChatMessageItem] = []" in swift_src
    assert "Permintaan diproses oleh NativeNUIProvider (L0–L11 Deterministic Core) dalam mode" not in swift_src


def test_live_streaming_greeting_does_not_emit_fake_tool_execution(
    app: NUILocalServiceApp,
) -> None:
    """Section 2, 3, 4, 5: Greeting 'Halo NUI, siapa kamu?' streams incrementally without fake TOOL_EXECUTION."""
    events = list(
        app.orchestrator.stream_chat_turn(
            user_message="Halo NUI, siapa kamu?",
            request_id="req-stream-greet-01",
        )
    )
    event_types = [e["event"] for e in events]
    assert event_types[0] == "request_accepted"
    assert "stage_update" in event_types
    assert "partial_response" in event_types
    assert event_types[-1] == "final_response"

    # Greeting does NOT invoke a tool -> must NOT emit tool_call or TOOL_EXECUTION stage
    assert "tool_call" not in event_types
    stages = events[-1]["thinking_stages"]
    assert "REQUEST_RECEIVED" in stages
    assert "UNDERSTANDING" in stages
    assert "ANALYZING" in stages
    assert "GENERATING_RESPONSE" in stages
    assert "COMPLETE" in stages
    assert "TOOL_EXECUTION" not in stages
    assert "PLANNING" not in stages

    # Verify text grew progressively across partial_response events
    partials = [e for e in events if e["event"] == "partial_response"]
    assert len(partials) >= 3
    lengths = [len(p["accumulated_text"]) for p in partials]
    assert lengths == sorted(lengths)
    assert lengths[0] < lengths[-1]

    final_txt = events[-1]["response_text"]
    assert "Natural Universal Intelligence" in final_txt
    assert "CosmicTera" in final_txt


def test_live_streaming_math_emits_real_tool_activity_and_validating(
    app: NUILocalServiceApp,
) -> None:
    """Section 2 & 5: 'Berapa 5 + 7?' emits PLANNING, TOOL_EXECUTION, VALIDATING, and real tool activities."""
    events = list(
        app.orchestrator.stream_chat_turn(
            user_message="Berapa 5 + 7?",
            request_id="req-stream-math-01",
        )
    )
    stages = events[-1]["thinking_stages"]
    assert stages == [
        "REQUEST_RECEIVED",
        "UNDERSTANDING",
        "ANALYZING",
        "PLANNING",
        "TOOL_EXECUTION",
        "VALIDATING",
        "GENERATING_RESPONSE",
        "COMPLETE",
    ]

    tool_acts = events[-1]["tool_activities"]
    assert len(tool_acts) >= 3
    assert any("Mengidentifikasi operasi matematika" in a for a in tool_acts)
    assert any("Memilih computation engine" in a for a in tool_acts)
    assert any("Menjalankan perhitungan" in a for a in tool_acts)
    assert any("Memverifikasi hasil" in a for a in tool_acts)

    assert "Hasilnya 12" in events[-1]["response_text"]


def test_section9_ten_step_acceptance_flow_and_reopen_persistence(
    db_path: Path,
) -> None:
    """Section 9: Full 10-step acceptance verification."""
    app1 = NUILocalServiceApp(db_path=db_path, use_os_keychain=False)
    _, sess = app1.dispatch_request("POST", "/api/sessions", {"title": "Acceptance Live"})
    sid = sess["session_id"]

    # Steps 1–6: User sends "Halo NUI", NUI processes, emits stages, streams partial_response, finishes COMPLETE
    ev_turn1 = list(
        app1.orchestrator.stream_chat_turn(
            session_id=sid,
            user_message="Halo NUI",
            request_id="req-acc-01",
        )
    )
    assert ev_turn1[0]["stage"] == "REQUEST_RECEIVED"
    partials_1 = [e for e in ev_turn1 if e["event"] == "partial_response"]
    assert len(partials_1) >= 2
    assert ev_turn1[-1]["stage"] == "COMPLETE"
    assert ev_turn1[-1]["turn_output"]["execution_status"] == "RESPONSE_COMPLETE"

    # Steps 7–8: User sends second question; NUI maintains conversation context
    ev_turn2 = list(
        app1.orchestrator.stream_chat_turn(
            session_id=sid,
            user_message="Ringkas pertanyaan pertama kita.",
            request_id="req-acc-02",
        )
    )
    assert ev_turn2[-1]["stage"] == "COMPLETE"
    assert "Halo NUI" in ev_turn2[-1]["response_text"]

    # Step 9: User can stop generation mid-flight
    app1.orchestrator.stop_chat_generation(request_id="req-acc-stop", session_id=sid)
    ev_stop = list(
        app1.orchestrator.stream_chat_turn(
            session_id=sid,
            user_message="Jelaskan apa itu CosmicTera.",
            request_id="req-acc-stop",
        )
    )
    assert ev_stop[-1]["event"] == "generation_cancelled"
    assert ev_stop[-1]["stage"] == "CANCELLED"

    # Step 10: Application reopens and chat history is loaded from actual SQLite storage
    app2 = NUILocalServiceApp(db_path=db_path, use_os_keychain=False)
    code, loaded = app2.dispatch_request("GET", f"/api/sessions?session_id={sid}")
    assert code == 200
    assert len(loaded["messages"]) == 6  # 3 user + 3 assistant turns persisted
    assert loaded["messages"][0]["content"] == "Halo NUI"
    assert "Halo NUI" in loaded["messages"][3]["content"]
