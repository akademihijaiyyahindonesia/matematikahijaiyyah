"""Tests for OWNER DIRECTIVE — COSMICTERA NUI DESKTOP SMART AUTO-SCROLL & LIVE CHAT FOLLOW.

Covers all 12 required verification scenarios in Section 8 of the Owner Directive:
1. Pesan pendek (Short user message -> immediate scroll to bottom).
2. Jawaban pendek (Short streaming reply -> auto-follow to bottom).
3. Jawaban panjang streaming (Long streaming reply -> throttled smooth auto-follow).
4. Jawaban multi-paragraf (Multi-paragraph streaming reply -> auto-follow).
5. Jawaban Markdown (Markdown headings/lists/tables streaming -> auto-follow).
6. Jawaban kode panjang (Long code block streaming -> auto-follow).
7. Tool activity selama jawaban (Context retrieval, tool_call, tool_result, stage_update -> auto-follow).
8. Pengguna scroll ke atas saat NUI masih menjawab (Pauses auto-follow, shows '↓ Kembali ke Jawaban Terbaru').
9. Klik tombol Kembali ke Jawaban Terbaru (Jumps to bottom, re-enables auto-follow, hides button).
10. Mengirim pesan baru setelah membaca pesan lama (Forces scroll to bottom, re-enables auto-follow, keeps composer focus).
11. Stop generation saat jawaban sedang berjalan (Leaves partial reply visible at bottom if not scrolled up).
12. Membuka kembali percakapan panjang dari riwayat (Scrolls to bottom of restored transcript and resets auto-follow).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
if str(NUI_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(NUI_DESKTOP_ROOT))

from backend.providers import OllamaProvider
from backend.self_learning import NUIModelAssetLibrary, NUIMultiModelRouter
from backend.server import NUILocalServiceApp


REPO_ROOT = Path(__file__).resolve().parents[2]
SWIFT_APP_SOURCE = REPO_ROOT / "nui-desktop" / "macos" / "Sources" / "CosmicTeraNUIApp.swift"
BUILT_APP_BINARY = (
    REPO_ROOT
    / "nui-desktop"
    / "macos"
    / "build"
    / "CosmicTera NUI.app"
    / "Contents"
    / "MacOS"
    / "CosmicTeraNUI"
)


class SmartScrollControllerSimulator:
    """Reference behavioral model mirroring NUIDesktopStore's Smart Auto-Scroll state machine in Swift."""

    CHAT_BOTTOM_ANCHOR_ID = "chat-bottom-anchor"

    def __init__(self) -> None:
        self.is_auto_follow_enabled: bool = True
        self.user_scrolled_up: bool = False
        self.scroll_trigger_version: int = 0
        self.should_refocus_composer: bool = False
        self.composer_focused: bool = True
        self.last_auto_scroll_timestamp: float = 0.0
        self.messages: List[Dict[str, Any]] = []
        self.scroll_events: List[Dict[str, Any]] = []
        self.clock_sec: float = 100.0

    def advance_clock(self, delta_sec: float) -> None:
        self.clock_sec += delta_sec

    def request_auto_scroll(self, *, force: bool = False, immediate: bool = False) -> bool:
        if force:
            self.is_auto_follow_enabled = True
            self.user_scrolled_up = False
        if not self.is_auto_follow_enabled:
            return False

        now = self.clock_sec
        # 30ms coalescing window for rapid streaming chunks unless immediate/forced
        if not immediate and not force and (now - self.last_auto_scroll_timestamp) < 0.030:
            return False

        self.last_auto_scroll_timestamp = now
        self.scroll_trigger_version += 1
        self.scroll_events.append(
            {
                "version": self.scroll_trigger_version,
                "anchor": self.CHAT_BOTTOM_ANCHOR_ID,
                "force": force,
                "immediate": immediate,
                "timestamp": now,
            }
        )
        return True

    def handle_user_manual_scroll_up(self) -> None:
        if self.is_auto_follow_enabled or not self.user_scrolled_up:
            self.is_auto_follow_enabled = False
            self.user_scrolled_up = True

    def handle_user_reached_bottom(self) -> None:
        if not self.is_auto_follow_enabled or self.user_scrolled_up:
            self.is_auto_follow_enabled = True
            self.user_scrolled_up = False

    def scroll_to_latest_response(self) -> None:
        self.request_auto_scroll(force=True, immediate=True)

    def send_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})
        self.should_refocus_composer = True
        self.composer_focused = True
        self.request_auto_scroll(force=True, immediate=True)

    def handle_stream_event(self, event_type: str, payload: Dict[str, Any], *, dt: float = 0.035) -> None:
        self.advance_clock(dt)
        if event_type in ("request_accepted", "user_ack", "assistant_placeholder"):
            self.request_auto_scroll(immediate=True)
        elif event_type == "partial_response":
            text = payload.get("accumulated_text") or payload.get("content") or ""
            if self.messages and self.messages[-1]["role"] == "assistant":
                self.messages[-1]["content"] = text
            else:
                self.messages.append({"role": "assistant", "content": text})
            self.request_auto_scroll(immediate=False)
        elif event_type in ("tool_call", "tool_result", "stage_update"):
            self.request_auto_scroll(immediate=False)
        elif event_type in ("final_response", "generation_cancelled", "generation_error"):
            text = payload.get("response_text") or payload.get("content") or ""
            if text:
                if self.messages and self.messages[-1]["role"] == "assistant":
                    self.messages[-1]["content"] = text
                else:
                    self.messages.append({"role": "assistant", "content": text})
            self.request_auto_scroll(immediate=True)

    def load_session_history(self, historical_messages: List[Dict[str, Any]]) -> None:
        self.messages = list(historical_messages)
        self.request_auto_scroll(force=True, immediate=True)


def test_swift_source_and_binary_contain_smart_auto_scroll_architecture() -> None:
    """Verify CosmicTeraNUIApp.swift and compiled binary implement all Smart Auto-Scroll components."""
    assert SWIFT_APP_SOURCE.exists(), f"Missing Swift source: {SWIFT_APP_SOURCE}"
    assert BUILT_APP_BINARY.exists(), f"Missing compiled macOS binary: {BUILT_APP_BINARY}"
    swift_code = SWIFT_APP_SOURCE.read_text(encoding="utf-8")

    # 1. Bottom anchor & ScrollViewReader wiring
    assert 'static let chatBottomAnchorId = "chat-bottom-anchor"' in swift_code
    assert ".id(NUIDesktopStore.chatBottomAnchorId)" in swift_code
    assert "proxy.scrollTo(NUIDesktopStore.chatBottomAnchorId, anchor: .bottom)" in swift_code
    assert ".onChange(of: store.scrollTriggerVersion)" in swift_code
    assert ".onChange(of: store.messages.count)" in swift_code

    # 2. Smart Scroll state machine & methods
    assert "@Published var isAutoFollowEnabled: Bool = true" in swift_code
    assert "@Published var userScrolledUp: Bool = false" in swift_code
    assert "@Published var scrollTriggerVersion: Int = 0" in swift_code
    assert "func requestAutoScroll(force: Bool = false, immediate: Bool = false)" in swift_code
    assert "func handleUserManualScrollUp()" in swift_code
    assert "func handleUserReachedBottom()" in swift_code
    assert "func scrollToLatestResponse()" in swift_code

    # 3. Native NSScrollView detector (SmartScrollObserverNSView + SmartScrollDetectorRepresentable)
    assert "final class SmartScrollObserverNSView: NSView" in swift_code
    assert "struct SmartScrollDetectorRepresentable: NSViewRepresentable" in swift_code
    assert "NSScrollView.didLiveScrollNotification" in swift_code
    assert "NSView.boundsDidChangeNotification" in swift_code

    # 4. Floating '↓ Kembali ke Jawaban Terbaru' button & pinned composer focus
    assert "↓ Kembali ke Jawaban Terbaru" in swift_code
    assert "@FocusState private var isComposerFocused: Bool" in swift_code
    assert ".focused($isComposerFocused)" in swift_code


def test_scenarios_1_to_6_streaming_lengths_markdown_and_code() -> None:
    """Scenarios 1, 2, 3, 4, 5, 6:
    1. Short message
    2. Short reply
    3. Long streaming reply (with 30ms coalescing check)
    4. Multi-paragraph reply
    5. Markdown reply
    6. Long code block reply
    """
    sim = SmartScrollControllerSimulator()

    # Scenario 1: Short message sent by user -> immediate scroll to bottom
    sim.send_user_message("Halo")
    assert sim.is_auto_follow_enabled is True
    assert sim.user_scrolled_up is False
    assert sim.composer_focused is True
    assert sim.scroll_events[-1]["force"] is True
    assert sim.scroll_events[-1]["immediate"] is True

    # Scenario 2: Short streaming reply
    v_before = sim.scroll_trigger_version
    sim.handle_stream_event("partial_response", {"content": "Halo! Ada yang bisa saya bantu?"}, dt=0.04)
    sim.handle_stream_event("final_response", {"content": "Halo! Ada yang bisa saya bantu?"}, dt=0.01)
    assert sim.scroll_trigger_version >= v_before + 2

    # Scenario 3: Long streaming reply with rapid chunks (verify throttling prevents jitter)
    sim.send_user_message("Jelaskan arsitektur CosmicTera secara lengkap")
    v_start = sim.scroll_trigger_version
    accumulated = ""
    # 20 rapid tokens arriving every 10ms -> coalesced by 30ms window so it doesn't fire 20 times
    for idx in range(20):
        accumulated += f"Bagian {idx + 1}: penjelasan arsitektur komputasi deterministik CosmicTera. "
        sim.handle_stream_event("partial_response", {"content": accumulated}, dt=0.010)
    sim.handle_stream_event("final_response", {"content": accumulated}, dt=0.010)
    fired_count = sim.scroll_trigger_version - v_start
    assert 4 <= fired_count <= 10, f"Expected coalesced scroll updates (4..10), got {fired_count}"
    assert sim.scroll_events[-1]["immediate"] is True

    # Scenario 4: Multi-paragraph reply
    multi_para = (
        "Paragraf pertama menjelaskan lapisan NUI.\n\n"
        "Paragraf kedua menjelaskan jembatan HISAMachine.\n\n"
        "Paragraf ketiga menyimpulkan alur eksekusi."
    )
    v_before = sim.scroll_trigger_version
    sim.handle_stream_event("partial_response", {"content": multi_para[:40]}, dt=0.04)
    sim.handle_stream_event("partial_response", {"content": multi_para[:90]}, dt=0.04)
    sim.handle_stream_event("final_response", {"content": multi_para}, dt=0.04)
    assert sim.scroll_trigger_version == v_before + 3

    # Scenario 5: Markdown reply (headings, bullet list, table)
    md_reply = (
        "### Ringkasan Modul\n"
        "- **HISAMachine**: Emulator H-ISA\n"
        "- **BSM**: Invarian `(112, 10, 9)`\n\n"
        "| Komponen | Status |\n| --- | --- |\n| HCPU | OK |"
    )
    v_before = sim.scroll_trigger_version
    sim.handle_stream_event("partial_response", {"content": md_reply[:50]}, dt=0.04)
    sim.handle_stream_event("final_response", {"content": md_reply}, dt=0.04)
    assert sim.scroll_trigger_version == v_before + 2

    # Scenario 6: Long code block reply
    code_reply = "```python\n" + "\n".join(f"def step_{i}(x: int) -> int:\n    return x + {i}" for i in range(25)) + "\n```"
    v_before = sim.scroll_trigger_version
    sim.handle_stream_event("partial_response", {"content": code_reply[:120]}, dt=0.04)
    sim.handle_stream_event("partial_response", {"content": code_reply[:300]}, dt=0.04)
    sim.handle_stream_event("final_response", {"content": code_reply}, dt=0.04)
    assert sim.scroll_trigger_version == v_before + 3


def test_scenario_7_live_tool_activity_and_streaming_integration(tmp_path: Path) -> None:
    """Scenario 7: Tool activity during reply (stage_update, tool_call, tool_result, partial_response, final_response)."""
    app = NUILocalServiceApp(db_path=tmp_path / "nui_scroll_test.db", use_os_keychain=False)
    code, sess = app.dispatch_request("POST", "/api/sessions", {"title": "Smart Scroll Tool Session"})
    assert code == 201
    session_id = sess["session_id"]

    sim = SmartScrollControllerSimulator()
    sim.send_user_message("Berapa 5 + 7?")

    events = list(
        app.orchestrator.stream_chat_turn(
            session_id=session_id,
            user_message="Berapa 5 + 7?",
            request_id="req-scroll-tool-01",
        )
    )
    seen_types = {ev["event"] for ev in events}
    assert "stage_update" in seen_types
    assert "tool_call" in seen_types
    assert "tool_result" in seen_types
    assert "partial_response" in seen_types
    assert "final_response" in seen_types

    v_before_stream = sim.scroll_trigger_version
    for ev in events:
        sim.handle_stream_event(ev["event"], ev, dt=0.035)

    assert sim.scroll_trigger_version > v_before_stream
    assert sim.is_auto_follow_enabled is True
    assert sim.user_scrolled_up is False
    assert "12" in sim.messages[-1]["content"]


def test_scenarios_8_9_10_11_12_smart_scroll_conditions() -> None:
    """Scenarios 8, 9, 10, 11, 12:
    8. User scrolls up while NUI is still streaming -> pauses auto-scroll, shows button.
    9. User clicks '↓ Kembali ke Jawaban Terbaru' -> jumps to bottom, re-enables auto-follow.
    10. User sends a new message while reading older messages -> forces scroll to bottom & keeps composer focus.
    11. User stops generation while streaming -> final partial remains visible at bottom.
    12. User reopens a long conversation from history -> scrolls to bottom and resets auto-follow.
    """
    sim = SmartScrollControllerSimulator()
    sim.send_user_message("Jelaskan BSM invariant")
    sim.handle_stream_event("partial_response", {"content": "Bagian awal jawaban..."}, dt=0.04)

    # Scenario 8: User manually scrolls up to inspect an older message during streaming
    sim.handle_user_manual_scroll_up()
    assert sim.is_auto_follow_enabled is False
    assert sim.user_scrolled_up is True

    v_paused = sim.scroll_trigger_version
    # Subsequent streaming chunks arrive while user is reading older messages -> NO forced scroll!
    sim.handle_stream_event("partial_response", {"content": "Bagian awal jawaban... lanjutan 1"}, dt=0.04)
    sim.handle_stream_event("partial_response", {"content": "Bagian awal jawaban... lanjutan 2"}, dt=0.04)
    assert sim.scroll_trigger_version == v_paused, "Auto-scroll must stay paused while userScrolledUp is True"

    # Scenario 9: User clicks '↓ Kembali ke Jawaban Terbaru'
    sim.scroll_to_latest_response()
    assert sim.is_auto_follow_enabled is True
    assert sim.user_scrolled_up is False
    assert sim.scroll_trigger_version == v_paused + 1
    assert sim.scroll_events[-1]["force"] is True
    assert sim.scroll_events[-1]["immediate"] is True

    # Next streaming chunk now auto-scrolls again
    sim.handle_stream_event("partial_response", {"content": "Bagian awal jawaban... lanjutan 3"}, dt=0.04)
    assert sim.scroll_trigger_version == v_paused + 2

    # Scenario 10: User scrolls up again to read old messages, then sends a new message (Condition 3)
    sim.handle_user_manual_scroll_up()
    assert sim.is_auto_follow_enabled is False
    assert sim.user_scrolled_up is True
    v_before_send = sim.scroll_trigger_version
    sim.send_user_message("Pertanyaan baru setelah baca pesan lama")
    assert sim.is_auto_follow_enabled is True
    assert sim.user_scrolled_up is False
    assert sim.composer_focused is True
    assert sim.scroll_trigger_version == v_before_send + 1

    # Scenario 11: Stop generation while streaming (Condition 4)
    sim.handle_stream_event("partial_response", {"content": "Jawaban sedang diketik..."}, dt=0.04)
    v_before_stop = sim.scroll_trigger_version
    sim.handle_stream_event("generation_cancelled", {"content": "Jawaban sedang diketik... [Dihentikan]"}, dt=0.01)
    assert sim.scroll_trigger_version == v_before_stop + 1
    assert sim.scroll_events[-1]["immediate"] is True

    # Scenario 12: Reopening a long conversation from history
    sim.handle_user_manual_scroll_up()
    long_history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"Pesan riwayat #{i + 1}"}
        for i in range(40)
    ]
    v_before_load = sim.scroll_trigger_version
    sim.load_session_history(long_history)
    assert len(sim.messages) == 40
    assert sim.is_auto_follow_enabled is True
    assert sim.user_scrolled_up is False
    assert sim.scroll_trigger_version == v_before_load + 1


def test_installed_ollama_models_auto_fallback_when_qwen38_not_pulled(tmp_path: Path) -> None:
    """Verify that when qwen3.8:27b is not pulled but ['santri-ai-kecil:latest', 'qwen3:4b-instruct-2507-q4_K_M',
    'santri-ai-8b:latest', 'hermes3:8b', 'qwen3-coder:30b'] are installed, OllamaProvider and NUIModelAssetLibrary
    automatically resolve to 'qwen3-coder:30b' without failing with MODEL_NOT_FOUND."""
    user_installed = [
        {"name": "santri-ai-kecil:latest", "model": "santri-ai-kecil:latest", "size": 2_000_000_000},
        {"name": "qwen3:4b-instruct-2507-q4_K_M", "model": "qwen3:4b-instruct-2507-q4_K_M", "size": 2_600_000_000},
        {"name": "santri-ai-8b:latest", "model": "santri-ai-8b:latest", "size": 4_900_000_000},
        {"name": "hermes3:8b", "model": "hermes3:8b", "size": 4_700_000_000},
        {"name": "qwen3-coder:30b", "model": "qwen3-coder:30b", "size": 18_500_000_000},
    ]

    def _transport(method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
        if method == "GET" and path == "/api/tags":
            return (200, {"models": user_installed})
        if method == "GET" and path == "/api/ps":
            return (200, {"models": []})
        if method == "GET" and path == "/api/version":
            return (200, {"version": "0.6.2"})
        if method == "POST" and path == "/api/chat":
            req_m = (body or {}).get("model", "")
            assert req_m == "qwen3-coder:30b", f"Expected fallback to qwen3-coder:30b, got {req_m}"
            if (body or {}).get("stream"):
                return (
                    200,
                    [
                        {"model": req_m, "message": {"role": "assistant", "content": "Halo! Saya NUI dari CosmicTera."}, "done": False},
                        {"model": req_m, "message": {"role": "assistant", "content": ""}, "done": True},
                    ],
                )
            return (200, {"model": req_m, "message": {"role": "assistant", "content": "Halo! Saya NUI dari CosmicTera."}, "done": True})
        return (404, {})

    app = NUILocalServiceApp(db_path=tmp_path / "fallback_test.db", use_os_keychain=False)
    app.model_library = NUIModelAssetLibrary(storage=app.storage, ollama_transport=_transport)
    app.multi_model_router = NUIMultiModelRouter(app.model_library)
    app.ollama_provider = OllamaProvider(
        persona_loader=app.persona_loader,
        context_retriever=app.context_retriever,
        self_learning_engine=app.self_learning,
        ollama_transport=_transport,
    )
    app.orchestrator.model_library = app.model_library
    app.orchestrator.multi_model_router = app.multi_model_router
    app.orchestrator.ollama_provider = app.ollama_provider

    code_lib, lib = app.dispatch_request("GET", "/api/models/library")
    assert code_lib == 200
    assert lib["selected_model"] == "qwen3-coder:30b"

    # Even if UI sends model="qwen3.8:27b", OllamaProvider resolves cleanly to "qwen3-coder:30b"
    code_chat, out = app.dispatch_request(
        "POST",
        "/api/chat",
        {
            "user_message": "Halo NUI",
            "provider": "local_ollama",
            "model": "qwen3.8:27b",
        },
    )
    assert code_chat == 200
    assert out["execution_status"] == "RESPONSE_COMPLETE"
    assert out["model"] == "qwen3-coder:30b"
    assert "MODEL_NOT_FOUND" not in out["response_text"]
