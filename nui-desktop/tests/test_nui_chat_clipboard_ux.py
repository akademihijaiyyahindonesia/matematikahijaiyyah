"""End-to-End Acceptance Test Suite for CosmicTera NUI Chat Experience, Native Clipboard Integration & VPS Folder Status Accuracy.

Covers all 15 required test cases in Section 9 plus Section 8 VPS & Connected Folder status verification:
1. Copy user message (`Salin pertanyaan` / `Copy` via `NSPasteboard.general`)
2. Copy full assistant response (including long responses beyond scroll viewport)
3. Copy code block only (raw code without markdown fences or surrounding explanation)
4. Select partial text (`.textSelection(.enabled)` across user bubbles, assistant prose, tables, formulas, and code blocks)
5. Paste multiline text into composer
6. Paste code block into composer (preserving indentation, tabs, line breaks, and special characters)
7. Paste Arabic Hijaiyyah characters (`ا ب ت ث ج ح خ ...`) and mathematical expressions (`||BSM||² = 112`)
8. `Enter` sends message
9. `Shift+Enter` creates new line without sending
10. Edit and resend user message (pruning stale turns and generating a fresh response)
11. Regenerate assistant response (replacing the assistant turn cleanly)
12. Stop streaming response (`/api/chat/stop` & cancellation handling)
13. Draft text survives switching sidebar menus (`NUI Chat` -> `Browser` -> `NUI Chat`)
14. Conversation history loads without contaminating new session (strict session isolation + per-session draft persistence)
15. Folder status check does NOT claim VPS connection without verified SSH/SFTP/mount proof (`/Users/AMRA/yayasan` & all 9 required fields)
"""

from __future__ import annotations

from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import socket
import subprocess
import sys
import threading
from typing import Any
from urllib import request as urllib_request

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
if str(NUI_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(NUI_DESKTOP_ROOT))

from backend.orchestrator import NUITaskOrchestrator
from backend.remote_dev_engine import (
    RemoteVPSDevelopmentEngine,
    VPSConnectionProfile,
)
from backend.server import NUILocalServiceApp, create_request_handler
from backend.storage import NUIStorage


YAYASAN_PATH = Path("/Users/AMRA/yayasan")
SWIFT_SOURCE = REPO_ROOT / "nui-desktop" / "macos" / "Sources" / "CosmicTeraNUIApp.swift"
APP_BINARY = (
    REPO_ROOT
    / "nui-desktop"
    / "macos"
    / "build"
    / "CosmicTera NUI.app"
    / "Contents"
    / "MacOS"
    / "CosmicTeraNUI"
)

REQUIRED_VPS_FOLDER_FIELDS = (
    "connected_folder_id",
    "local_canonical_path",
    "remote_ssh_profile",
    "ssh_connection_status",
    "verified_host_fingerprint",
    "sftp_connection",
    "remote_workspace_path",
    "mount_status",
    "last_successful_remote_verification",
)


class DeterministicSSHTransport:
    """Controlled SSH/SFTP adapter for testing VPS folder status states deterministically."""

    def __init__(self) -> None:
        self.known_fingerprint = "SHA256:YayasanVerifiedHostKeyFingerprint12345"
        self.remote_files: dict[str, str] = {
            "/srv/yayasan/README.md": "# Yayasan Remote Workspace\n",
        }

    def verify_host_fingerprint(
        self, host: str, port: int, expected_fingerprint: str, timeout: float = 5.0
    ) -> dict[str, Any]:
        matched = expected_fingerprint.strip() == self.known_fingerprint
        return {
            "ok": matched,
            "verified": matched,
            "status": (
                "HOST_KEY_VERIFIED" if matched else "HOST_KEY_VERIFICATION_FAILED"
            ),
            "expected_fingerprint": expected_fingerprint,
            "scanned_fingerprints": [
                f"256 {self.known_fingerprint} {host} (ED25519)"
            ],
            "reason": "Host key matched." if matched else "Host fingerprint mismatch!",
        }

    def run_ssh_command(
        self,
        profile: VPSConnectionProfile,
        command: str,
        *,
        timeout: float = 10.0,
        keychain_secret: str | None = None,
    ) -> dict[str, Any]:
        if "uname -srm" in command:
            return {
                "ok": True,
                "exit_code": 0,
                "stdout": "Linux 6.8.0-45-generic x86_64\n/usr/bin/python3\n/usr/bin/git\n",
                "stderr": "",
                "timed_out": False,
            }
        return {
            "ok": True,
            "exit_code": 0,
            "stdout": f"Executed: {command}\n",
            "stderr": "",
            "timed_out": False,
        }

    def sftp_read_file(
        self,
        profile: VPSConnectionProfile,
        remote_path: str,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        content = self.remote_files.get(remote_path, "")
        return {
            "ok": bool(content),
            "remote_path": remote_path,
            "content": content,
            "size_bytes": len(content.encode("utf-8")),
            "timed_out": False,
        }

    def sftp_write_file(
        self,
        profile: VPSConnectionProfile,
        remote_path: str,
        content: str,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        self.remote_files[remote_path] = content
        return {
            "ok": True,
            "remote_path": remote_path,
            "bytes_written": len(content.encode("utf-8")),
            "exit_code": 0,
            "stderr": "",
            "timed_out": False,
        }


@pytest.fixture(scope="module")
def native_ui_clipboard_report() -> dict:
    """Executes `--verify-chat-clipboard-ui` on the compiled macOS native app binary once per module."""
    assert APP_BINARY.exists(), f"Compiled macOS app binary not found at {APP_BINARY}"
    proc = subprocess.run(
        [str(APP_BINARY), "--verify-chat-clipboard-ui"],
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    out = proc.stdout
    assert "CHAT_CLIPBOARD_UI_VERIFY_JSON_START" in out
    assert "CHAT_CLIPBOARD_UI_VERIFY_JSON_END" in out
    raw_json = out.split("CHAT_CLIPBOARD_UI_VERIFY_JSON_START", 1)[1].split(
        "CHAT_CLIPBOARD_UI_VERIFY_JSON_END", 1
    )[0]
    return json.loads(raw_json.strip())


def _build_test_stack(tmp_path: Path) -> dict[str, Any]:
    app = NUILocalServiceApp(
        db_path=tmp_path / "test_chat_clipboard.db", use_os_keychain=False
    )
    if YAYASAN_PATH.exists():
        app.storage.add_authorized_folder(
            YAYASAN_PATH, label="yayasan", access_mode="READ_WRITE"
        )
    ssh_transport = DeterministicSSHTransport()
    remote_engine = RemoteVPSDevelopmentEngine(
        storage=app.storage,
        permissions=app.permissions,
        transport=ssh_transport,
    )
    app.remote_dev_engine = remote_engine
    app.native_provider.remote_dev_engine = remote_engine
    app.ollama_provider.remote_dev_engine = remote_engine
    app.orchestrator.remote_dev_engine = remote_engine
    return {
        "app": app,
        "storage": app.storage,
        "permissions": app.permissions,
        "tools": app.tools,
        "ssh_transport": ssh_transport,
        "remote_engine": remote_engine,
        "orchestrator": app.orchestrator,
    }


# ---------------------------------------------------------------------------
# 1. Copy user message
# ---------------------------------------------------------------------------
def test_01_copy_user_message_native_pasteboard(native_ui_clipboard_report: dict):
    assert native_ui_clipboard_report["copy_user_message_pass"] is True
    swift_src = SWIFT_SOURCE.read_text(encoding="utf-8")
    assert "func copyUserQuestion(_ msg: ChatMessageItem)" in swift_src
    assert "Salin pertanyaan" in swift_src
    assert "Copied ✓ · Tersalin" in swift_src


# ---------------------------------------------------------------------------
# 2. Copy full assistant response (even when response is long / scrolled)
# ---------------------------------------------------------------------------
def test_02_copy_full_assistant_response_native_pasteboard(
    native_ui_clipboard_report: dict,
):
    assert native_ui_clipboard_report["copy_full_assistant_response_pass"] is True
    assert native_ui_clipboard_report["copied_assistant_char_count"] > 4500
    swift_src = SWIFT_SOURCE.read_text(encoding="utf-8")
    assert "func copyAssistantFullAnswer(_ msg: ChatMessageItem)" in swift_src
    assert "NUIClipboardManager.shared.copyAssistantResponse(msg.content)" in swift_src


# ---------------------------------------------------------------------------
# 3. Copy code block only (raw code without markdown fences or explanation)
# ---------------------------------------------------------------------------
def test_03_copy_code_block_only_without_fences_or_explanation(
    native_ui_clipboard_report: dict,
):
    assert native_ui_clipboard_report["copy_code_block_only_pass"] is True
    swift_src = SWIFT_SOURCE.read_text(encoding="utf-8")
    assert "func copyCodeBlockOnly(_ rawCode: String) -> Bool" in swift_src
    assert "func copyRawCodeBlock(code: String, blockId: String)" in swift_src
    assert "struct CodeBlockCardView: View" in swift_src


# ---------------------------------------------------------------------------
# 4. Select partial text & rich Markdown rendering (tables, headings, formulas)
# ---------------------------------------------------------------------------
def test_04_select_partial_text_and_rich_markdown_rendering(
    native_ui_clipboard_report: dict,
):
    assert (
        native_ui_clipboard_report["markdown_parser_heading_table_formula_pass"] is True
    )
    swift_src = SWIFT_SOURCE.read_text(encoding="utf-8")
    assert swift_src.count(".textSelection(.enabled)") >= 8
    assert "struct MarkdownTableBlockView: View" in swift_src
    assert "struct MarkdownProseSegmentView: View" in swift_src
    assert "case formulaCallout(text: String)" in swift_src


# ---------------------------------------------------------------------------
# 5. Paste multiline text into composer
# ---------------------------------------------------------------------------
def test_05_paste_multiline_text_into_composer(native_ui_clipboard_report: dict):
    assert (
        native_ui_clipboard_report["paste_multiline_unicode_hijaiyyah_math_pass"]
        is True
    )
    swift_src = SWIFT_SOURCE.read_text(encoding="utf-8")
    assert "final class NUIComposerNSTextView: NSTextView" in swift_src
    assert "override func paste(_ sender: Any?)" in swift_src
    assert "func pasteFromClipboardIntoComposer()" in swift_src


# ---------------------------------------------------------------------------
# 6. Paste code block into composer (preserving indentation, tabs, line breaks)
# ---------------------------------------------------------------------------
def test_06_paste_code_block_into_composer_preserves_indentation(
    native_ui_clipboard_report: dict,
):
    assert (
        native_ui_clipboard_report["paste_multiline_unicode_hijaiyyah_math_pass"]
        is True
    )
    swift_src = SWIFT_SOURCE.read_text(encoding="utf-8")
    assert "tv.isAutomaticQuoteSubstitutionEnabled = false" in swift_src
    assert "tv.isAutomaticDashSubstitutionEnabled = false" in swift_src
    assert "tv.isAutomaticTextReplacementEnabled = false" in swift_src


# ---------------------------------------------------------------------------
# 7. Paste Arabic Hijaiyyah characters and mathematical expressions
# ---------------------------------------------------------------------------
def test_07_paste_arabic_hijaiyyah_and_mathematical_expressions(
    native_ui_clipboard_report: dict, tmp_path: Path
):
    assert (
        native_ui_clipboard_report["paste_multiline_unicode_hijaiyyah_math_pass"]
        is True
    )
    stack = _build_test_stack(tmp_path)
    storage: NUIStorage = stack["storage"]
    sess = storage.create_session("Hijaiyyah Paste Session")
    sid = sess["session_id"]

    pasted_prompt = (
        "Analisis huruf Hijaiyyah: ا ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن و ه لا ء ي\n"
        "Rumus kuantitatif: ||BSM||² = 112, H_c = 13.714285714285714, τ₀ = 49.000 ms"
    )
    storage.save_session_draft(sid, pasted_prompt)
    assert storage.get_session_draft(sid) == pasted_prompt


# ---------------------------------------------------------------------------
# 8. Enter sends message
# ---------------------------------------------------------------------------
def test_08_enter_key_sends_message(native_ui_clipboard_report: dict):
    assert native_ui_clipboard_report["enter_triggers_send_pass"] is True
    swift_src = SWIFT_SOURCE.read_text(encoding="utf-8")
    assert "let isReturnOrEnter = (event.keyCode == 36 || event.keyCode == 76)" in swift_src
    assert "onEnterSend?()" in swift_src


# ---------------------------------------------------------------------------
# 9. Shift+Enter creates new line without sending
# ---------------------------------------------------------------------------
def test_09_shift_enter_creates_newline_without_sending(
    native_ui_clipboard_report: dict,
):
    assert native_ui_clipboard_report["shift_enter_newline_without_send_pass"] is True
    swift_src = SWIFT_SOURCE.read_text(encoding="utf-8")
    assert "if flags.contains(.shift)" in swift_src
    assert "super.insertNewline(nil)" in swift_src


# ---------------------------------------------------------------------------
# 10. Edit and resend user message
# ---------------------------------------------------------------------------
def test_10_edit_and_resend_user_message(
    native_ui_clipboard_report: dict, tmp_path: Path
):
    assert native_ui_clipboard_report["inline_edit_user_message_pass"] is True
    stack = _build_test_stack(tmp_path)
    storage: NUIStorage = stack["storage"]
    orchestrator: NUITaskOrchestrator = stack["orchestrator"]

    sess = storage.create_session("Edit Resend Session")
    sid = sess["session_id"]
    storage.set_setting("active_provider", "native_nui")

    # Initial turn
    t1 = orchestrator.handle_chat_turn(
        session_id=sid,
        user_message="Berapa 2 + 2?",
        message_id="msg-user-1",
    )
    assert t1["ok"] is True
    msgs_before = storage.list_messages(sid)
    assert len(msgs_before) == 2

    # Edit msg-user-1 and resend with a new prompt
    edited = orchestrator.edit_and_resend_chat_turn(
        session_id=sid,
        target_message_id="msg-user-1",
        updated_user_message="Cek apakah folder Yayasan sudah terhubung ke VPS.",
        provider="native_nui",
    )
    assert edited["ok"] is True
    assert edited["edited_message_id"] == "msg-user-1"
    assert "connected_folder_id" in edited["response"]
    assert "LOCAL_ONLY" in edited["response"]

    msgs_after = storage.list_messages(sid)
    assert len(msgs_after) == 2
    assert (
        msgs_after[0]["content"]
        == "Cek apakah folder Yayasan sudah terhubung ke VPS."
    )
    assert "LOCAL_ONLY" in msgs_after[1]["content"]


# ---------------------------------------------------------------------------
# 11. Regenerate assistant response
# ---------------------------------------------------------------------------
def test_11_regenerate_assistant_response(tmp_path: Path):
    stack = _build_test_stack(tmp_path)
    storage: NUIStorage = stack["storage"]
    orchestrator: NUITaskOrchestrator = stack["orchestrator"]

    sess = storage.create_session("Regenerate Session")
    sid = sess["session_id"]
    storage.set_setting("active_provider", "native_nui")

    t1 = orchestrator.handle_chat_turn(
        session_id=sid,
        user_message="Cek apakah folder Yayasan sudah terhubung ke VPS.",
        message_id="msg-regen-u1",
    )
    assert t1["ok"] is True
    msgs_initial = storage.list_messages(sid)
    assert len(msgs_initial) == 2
    first_asst_id = msgs_initial[1]["message_id"]

    regen = orchestrator.regenerate_chat_turn(
        session_id=sid,
        assistant_message_id=first_asst_id,
        provider="native_nui",
    )
    assert regen["ok"] is True
    assert regen["regenerated"] is True
    assert "LOCAL_ONLY" in regen["response"]

    msgs_after = storage.list_messages(sid)
    assert len(msgs_after) == 2
    assert msgs_after[0]["role"] == "user"
    assert msgs_after[1]["role"] == "assistant"
    assert "LOCAL_ONLY" in msgs_after[1]["content"]


# ---------------------------------------------------------------------------
# 12. Stop streaming response
# ---------------------------------------------------------------------------
def test_12_stop_streaming_response(tmp_path: Path):
    stack = _build_test_stack(tmp_path)
    storage: NUIStorage = stack["storage"]
    orchestrator: NUITaskOrchestrator = stack["orchestrator"]

    sess = storage.create_session("Stop Stream Session")
    sid = sess["session_id"]
    storage.set_setting("active_provider", "native_nui")

    events = []
    req_id = "req-stop-test-12"

    for ev in orchestrator.stream_chat_turn(
        session_id=sid,
        user_message="Jelaskan arsitektur CosmicTera NUI secara lengkap.",
        request_id=req_id,
        provider_id="native_nui",
    ):
        events.append(ev)
        if ev.get("event") in {"request_accepted", "partial_response"}:
            orchestrator.stop_chat_generation(request_id=req_id, session_id=sid)

    assert any(
        e.get("event") == "generation_cancelled"
        or e.get("turn_output", {}).get("execution_status") == "STOPPED"
        for e in events
    )


# ---------------------------------------------------------------------------
# 13. Draft text survives switching menus and sessions
# ---------------------------------------------------------------------------
def test_13_draft_text_survives_switching_menus_and_sessions(
    native_ui_clipboard_report: dict, tmp_path: Path
):
    assert native_ui_clipboard_report["draft_survived_menu_switch_pass"] is True

    stack = _build_test_stack(tmp_path)
    storage: NUIStorage = stack["storage"]
    s1 = storage.create_session("Sesi Alpha")["session_id"]
    s2 = storage.create_session("Sesi Beta")["session_id"]

    draft_alpha = "Draft kode H-ISA untuk Sesi Alpha:\nHLOAD H1, 2\nHCADD H4, H1, H2"
    draft_beta = "Pertanyaan VPS untuk Sesi Beta"
    storage.save_session_draft(s1, draft_alpha)
    storage.save_session_draft(s2, draft_beta)

    assert storage.get_session_draft(s1) == draft_alpha
    assert storage.get_session_draft(s2) == draft_beta


# ---------------------------------------------------------------------------
# 14. Conversation history loads without contaminating new session
# ---------------------------------------------------------------------------
def test_14_conversation_history_loads_without_contaminating_new_session(
    tmp_path: Path,
):
    stack = _build_test_stack(tmp_path)
    storage: NUIStorage = stack["storage"]
    orchestrator: NUITaskOrchestrator = stack["orchestrator"]
    storage.set_setting("active_provider", "native_nui")

    s_old = storage.create_session("Sesi Lama")["session_id"]
    orchestrator.handle_chat_turn(
        session_id=s_old,
        user_message="Simpan kata kunci unik: GARUDA_7788_ALPHA",
    )
    old_msgs = storage.list_messages(s_old)
    assert len(old_msgs) == 2

    # Create a brand new session and verify zero message contamination
    s_new = storage.create_session("Sesi Baru Bersih")["session_id"]
    new_msgs = storage.list_messages(s_new)
    assert new_msgs == []

    orchestrator.handle_chat_turn(
        session_id=s_new,
        user_message="Cek apakah folder Yayasan sudah terhubung ke VPS.",
    )
    new_msgs_after = storage.list_messages(s_new)
    assert len(new_msgs_after) == 2
    for m in new_msgs_after:
        assert "GARUDA_7788_ALPHA" not in m["content"]


# ---------------------------------------------------------------------------
# 15. Folder status check does NOT claim VPS connection without verified proof
# ---------------------------------------------------------------------------
def test_15_folder_status_never_claims_vps_from_git_or_connected_folder(
    native_ui_clipboard_report: dict, tmp_path: Path
):
    assert native_ui_clipboard_report["yayasan_in_default_authorized_folders"] is True
    stack = _build_test_stack(tmp_path)
    app: NUILocalServiceApp = stack["app"]
    remote_engine: RemoteVPSDevelopmentEngine = stack["remote_engine"]
    ssh_transport: DeterministicSSHTransport = stack["ssh_transport"]

    # 15a. Inspect /Users/AMRA/yayasan (has local READ_WRITE Connected Folder, local .git, and DEPLOY.md, but NO SSH profile/session/mount)
    report = remote_engine.inspect_folder_vps_status("/Users/AMRA/yayasan")
    assert report["ok"] is True
    for field in REQUIRED_VPS_FOLDER_FIELDS:
        assert field in report, f"Missing required field: {field}"

    assert report["local_canonical_path"] == "/Users/AMRA/yayasan"
    assert report["local_folder_status"] == "READ_WRITE"
    assert "NONE" in report["remote_ssh_profile"]
    assert report["ssh_connection_status"] == "NOT_CONFIGURED"
    assert "NONE" in report["verified_host_fingerprint"]
    assert report["sftp_connection"] == "NOT_CONFIGURED"
    assert report["remote_workspace_path"] == "NONE"
    assert "NEVER" in report["last_successful_remote_verification"]
    assert report["inferred_from_git_or_connected_folder"] is False
    assert report["status"] in RemoteVPSDevelopmentEngine.VALID_FOLDER_VPS_STATUSES
    assert report["status"] == "LOCAL_ONLY"
    assert report["vps_connection_status"] == "NOT_CONFIGURED"
    assert "LOCAL_ONLY" in report["formatted_report"]
    assert "Connected Folders" in report["formatted_report"]

    # 15b. Register an SSH profile for yayasan without connecting -> must be DISCONNECTED, not REMOTE_CONNECTED
    app.permissions.set_rule(
        category="VPS_CONNECT",
        target_type="endpoint",
        target_value="*",
        operation="*",
        decision="ALWAYS_ALLOW",
    )
    prof = remote_engine.register_profile(
        name="yayasan-vps-prod",
        host="vps.yayasan.example.org",
        port=22,
        username="deploy",
        auth_method="SSH_KEY",
        remote_workspace="/srv/yayasan",
        expected_host_fingerprint=ssh_transport.known_fingerprint,
    )
    pid = prof["profile_id"]
    report_disconnected = remote_engine.inspect_folder_vps_status("/Users/AMRA/yayasan")
    assert report_disconnected["ssh_connection_status"] == "DISCONNECTED"
    assert report_disconnected["sftp_connection"] == "INACTIVE"
    assert report_disconnected["status"] == "DISCONNECTED"
    assert report_disconnected["inferred_from_git_or_connected_folder"] is False

    # 15c. Connect SSH session with verified host fingerprint -> becomes REMOTE_CONNECTED (still not SYNCED unless sync proof exists)
    conn_res = remote_engine.connect_and_inspect(pid)
    assert conn_res["ok"] is True
    report_connected = remote_engine.inspect_folder_vps_status("/Users/AMRA/yayasan")
    assert report_connected["ssh_connection_status"] == "CONNECTED"
    assert (
        report_connected["verified_host_fingerprint"] == ssh_transport.known_fingerprint
    )
    assert report_connected["sftp_connection"] == "ACTIVE"
    assert report_connected["remote_workspace_path"] == "/srv/yayasan"
    assert report_connected["status"] == "REMOTE_CONNECTED"
    assert "NEVER" not in report_connected["last_successful_remote_verification"]

    # 15d. Verify REMOTE_MOUNTED when OS mount table indicates sshfs/fuse mount
    report_mounted = remote_engine.inspect_folder_vps_status(
        "/Users/AMRA/yayasan",
        mount_table_override="deploy@vps.yayasan.example.org:/srv/yayasan on /Users/AMRA/yayasan (osxfuse, nodev, nosuid)",
    )
    assert report_mounted["status"] == "REMOTE_MOUNTED"
    assert "REMOTE_MOUNTED" in report_mounted["mount_status"]


# ---------------------------------------------------------------------------
# 16. Server API Dispatch Verification (/api/chat/op & /api/vps/op)
# ---------------------------------------------------------------------------
def test_16_http_server_chat_op_and_vps_folder_inspection_endpoints(tmp_path: Path):
    app = NUILocalServiceApp(
        db_path=tmp_path / "server_chat_ux.db", use_os_keychain=False
    )
    if YAYASAN_PATH.exists():
        app.storage.add_authorized_folder(
            YAYASAN_PATH, label="yayasan", access_mode="READ_WRITE"
        )

    def _post(path: str, payload: dict) -> dict:
        code, res = app.dispatch_request("POST", path, payload)
        assert code in {200, 201}, f"Unexpected HTTP status {code} for {path}: {res}"
        return res

    # 1. Inspect /Users/AMRA/yayasan via /api/vps/op
    vps_check = _post(
        "/api/vps/op",
        {"op": "inspect_folder", "folder_path": "/Users/AMRA/yayasan"},
    )
    assert vps_check["ok"] is True
    for field in REQUIRED_VPS_FOLDER_FIELDS:
        assert field in vps_check
    assert vps_check["status"] == "LOCAL_ONLY"
    assert vps_check["inferred_from_git_or_connected_folder"] is False

    # 2. Save & retrieve draft via /api/chat/op
    sess = _post("/api/sessions", {"title": "HTTP UX Session"})
    sid = sess["session_id"]
    draft_res = _post(
        "/api/chat/op",
        {
            "op": "save_draft",
            "session_id": sid,
            "draft_text": "Cek apakah folder Yayasan sudah terhubung ke VPS.",
        },
    )
    assert draft_res["ok"] is True
    get_draft = _post("/api/chat/op", {"op": "get_draft", "session_id": sid})
    assert (
        get_draft["draft_text"]
        == "Cek apakah folder Yayasan sudah terhubung ke VPS."
    )

    # 3. Ask NUI in chat about folder Yayasan VPS connection
    _post("/api/settings", {"active_provider": "native_nui"})
    chat_res = _post(
        "/api/chat",
        {
            "session_id": sid,
            "message_id": "m-http-1",
            "user_message": "Cek apakah folder Yayasan sudah terhubung ke VPS.",
            "provider": "native_nui",
        },
    )
    assert chat_res["ok"] is True
    assert "LOCAL_ONLY" in chat_res["response"]
    assert "connected_folder_id" in chat_res["response"]
    assert "mount_status" in chat_res["response"]

    # 4. Record feedback via /api/chat/op
    fb_res = _post(
        "/api/chat/op",
        {
            "op": "feedback",
            "session_id": sid,
            "message_id": "m-http-1",
            "rating": "POSITIVE",
            "note": "Pemeriksaan VPS akurat berdasarkan bukti koneksi nyata.",
        },
    )
    assert fb_res["ok"] is True
    assert fb_res["rating"] == "POSITIVE"
