#!/usr/bin/env python3
"""Local HTTP + SSE API Server for CosmicTera NUI Desktop (`127.0.0.1:8848`)."""
from __future__ import annotations

import argparse
import http.client
import importlib
import json
import os
import queue
import signal
import socket
import sys
import time
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
NUI_DESKTOP_ROOT = Path(__file__).resolve().parents[1]
if str(NUI_DESKTOP_ROOT) not in sys.path:
    sys.path.insert(0, str(NUI_DESKTOP_ROOT))

import backend.persona_and_context as _pc_mod
import backend.providers as _prov_mod
from backend.internet_engine import RealInternetEngine, parse_and_normalize_address_input
from backend.master_control import CosmicTeraMasterController, check_immutable_core_path
import backend.operational_intelligence as _op_mod
from backend.operational_intelligence import UnifiedOperationalIntelligence
from backend.orchestrator import NUITaskOrchestrator
from backend.permissions import PERMISSION_CATEGORIES, PermissionEngine
from backend.persona_and_context import NUIContextualRetriever, NUIPersonaLoader
from backend.providers import (
    NativeNUIProvider,
    OllamaProvider,
    OptionalExternalProvider,
)
from backend.remote_dev_engine import RemoteVPSDevelopmentEngine
from backend.self_learning import (
    NUIAutonomousSelfLearningEngine,
    NUIModelAssetLibrary,
    NUIMultiModelRouter,
)
from backend.storage import NUIStorage
from backend.tools import NUIToolRegistry
from backend.universal_file_intelligence import UniversalFileActionEngine

ACTIVE_SERVICE_FILE = NUI_DESKTOP_ROOT / "data" / "active_service.json"
SERVICE_VERSION = "1.5.2"


class NUILocalServiceApp:
    """Container holding all wired backend components for CosmicTera NUI Desktop."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        use_os_keychain: bool = True,
    ) -> None:
        default_db = NUI_DESKTOP_ROOT / "data" / "nui_desktop.db"
        resolved_db = Path(db_path or default_db)

        self.storage = NUIStorage(resolved_db, use_os_keychain=use_os_keychain)
        self.permissions = PermissionEngine(self.storage)
        self.persona_loader = NUIPersonaLoader(REPO_ROOT)
        self.context_retriever = NUIContextualRetriever(REPO_ROOT)
        self.model_library = NUIModelAssetLibrary(storage=self.storage)
        self.multi_model_router = NUIMultiModelRouter(self.model_library)
        self.self_learning = NUIAutonomousSelfLearningEngine(
            storage=self.storage,
            asset_library=self.model_library,
            router=self.multi_model_router,
        )

        self.internet_engine = RealInternetEngine(
            storage=self.storage,
            permissions=self.permissions,
        )
        self.remote_dev_engine = RemoteVPSDevelopmentEngine(
            storage=self.storage,
            permissions=self.permissions,
        )
        self.universal_file_engine = UniversalFileActionEngine(
            storage=self.storage,
            permissions=self.permissions,
            remote_dev_engine=self.remote_dev_engine,
        )
        self.ollama_provider = OllamaProvider(
            persona_loader=self.persona_loader,
            context_retriever=self.context_retriever,
            self_learning_engine=self.self_learning,
            remote_dev_engine=self.remote_dev_engine,
            universal_file_engine=self.universal_file_engine,
            internet_engine=self.internet_engine,
        )
        self.native_provider = NativeNUIProvider(
            persona_loader=self.persona_loader,
            context_retriever=self.context_retriever,
            self_learning_engine=self.self_learning,
            ollama_provider=self.ollama_provider,
            remote_dev_engine=self.remote_dev_engine,
            universal_file_engine=self.universal_file_engine,
            internet_engine=self.internet_engine,
        )
        self.external_provider = OptionalExternalProvider(self.storage, self.permissions)
        self.tools = NUIToolRegistry(
            self.storage, self.permissions, self.native_provider
        )
        self.operational_intelligence = UnifiedOperationalIntelligence(
            repo_root=REPO_ROOT,
            data_dir=resolved_db.parent,
            storage=self.storage,
            permission_engine=self.permissions,
            layers_bridge=self.native_provider.layers_bridge,
            model_library=self.model_library,
            multi_model_router=self.multi_model_router,
            tool_registry=self.tools,
            retriever=self.context_retriever,
        )
        self.orchestrator = NUITaskOrchestrator(
            storage=self.storage,
            permissions=self.permissions,
            tools=self.tools,
            native_provider=self.native_provider,
            ollama_provider=self.ollama_provider,
            external_provider=self.external_provider,
            model_library=self.model_library,
            multi_model_router=self.multi_model_router,
            self_learning=self.self_learning,
            operational_intelligence=self.operational_intelligence,
            remote_dev_engine=self.remote_dev_engine,
            universal_file_engine=self.universal_file_engine,
            internet_engine=self.internet_engine,
        )
        self.master_controller = CosmicTeraMasterController(
            storage=self.storage,
            permissions=self.permissions,
            persona_loader=self.persona_loader,
            context_retriever=self.context_retriever,
            model_library=self.model_library,
            self_learning=self.self_learning,
            ollama_provider=self.ollama_provider,
            native_provider=self.native_provider,
            tools=self.tools,
        )
        self.active_folder_processes: set[str] = set()
        self._last_module_mtimes: tuple[float, float] | None = None
        if not self.storage.list_authorized_folders(active_only=False):
            self.storage.add_authorized_folder(
                REPO_ROOT,
                label="hijaiyyah-mathematics",
                access_mode="READ_WRITE",
            )
        if resolved_db == default_db and Path("/Users/AMRA/yayasan").exists():
            if self.storage.get_authorized_folder("/Users/AMRA/yayasan") is None:
                self.storage.add_authorized_folder(
                    Path("/Users/AMRA/yayasan"),
                    label="yayasan",
                    access_mode="READ_WRITE",
                )
        self.context_retriever.sync_active_folders(
            [f["path"] for f in self.storage.list_authorized_folders(active_only=True)]
        )
        if resolved_db == default_db:
            ollama_st = self.ollama_provider.status()
            if ollama_st.get("available"):
                self.storage.set_setting("active_provider", "local_ollama")
                if ollama_st.get("model"):
                    self.storage.set_setting("selected_ollama_model", ollama_st["model"])

    def _hot_reload_if_needed(self) -> None:
        """Automatically reload persona_and_context.py, providers.py, and diagnostic engines if modified on disk."""
        try:
            pc_file = Path(_pc_mod.__file__)
            prov_file = Path(_prov_mod.__file__)
            current_mtimes = (pc_file.stat().st_mtime, prov_file.stat().st_mtime)
            if self._last_module_mtimes is None:
                self._last_module_mtimes = current_mtimes
                return
            if current_mtimes != self._last_module_mtimes:
                self._last_module_mtimes = current_mtimes
                if getattr(self.ollama_provider, "ollama_transport", None) is not None:
                    return
                importlib.reload(_pc_mod)
                importlib.reload(_prov_mod)
                self.persona_loader = _pc_mod.NUIPersonaLoader(REPO_ROOT)
                self.context_retriever = _pc_mod.NUIContextualRetriever(REPO_ROOT)
                self.ollama_provider = _prov_mod.OllamaProvider(
                    persona_loader=self.persona_loader,
                    context_retriever=self.context_retriever,
                    self_learning_engine=self.self_learning,
                    remote_dev_engine=self.remote_dev_engine,
                    universal_file_engine=self.universal_file_engine,
                    internet_engine=self.internet_engine,
                )
                self.native_provider = _prov_mod.NativeNUIProvider(
                    persona_loader=self.persona_loader,
                    context_retriever=self.context_retriever,
                    self_learning_engine=self.self_learning,
                    ollama_provider=self.ollama_provider,
                    remote_dev_engine=self.remote_dev_engine,
                    universal_file_engine=self.universal_file_engine,
                    internet_engine=self.internet_engine,
                )
                self.orchestrator.ollama_provider = self.ollama_provider
                self.orchestrator.native_provider = self.native_provider
                self.orchestrator.remote_dev_engine = self.remote_dev_engine
                self.orchestrator.universal_file_engine = self.universal_file_engine
                self.orchestrator.internet_engine = self.internet_engine
        except Exception:
            pass

    def get_health_payload(self) -> dict[str, Any]:
        active_prov_id = self.storage.get_setting("active_provider", "native_nui")
        try:
            prov = self.orchestrator.get_provider(active_prov_id)
            prov_st = prov.status()
        except Exception as exc:
            prov_st = {
                "provider_id": active_prov_id,
                "available": False,
                "ui_state": "PROVIDER UNAVAILABLE",
                "honest_status": str(exc),
            }
        ollama_probe = self.model_library.probe_ollama_runtime()
        cur_mode = self.storage.get_setting("operating_mode", "HYBRID")
        if cur_mode == "LOCAL":
            net_state = "OFFLINE (LOCAL MODE)"
            net_reason = "OPERATING_MODE_LOCAL_LOCK: Outbound internet dinonaktifkan pada mode LOCAL."
        elif self.internet_engine._last_diagnostics:
            net_state = self.internet_engine._last_diagnostics.get("overall_status", "UNKNOWN")
            net_reason = self.internet_engine._last_diagnostics.get(
                "connectivity_reason",
                f"DIAGNOSTICS_{net_state}",
            )
        else:
            net_state = "UNKNOWN"
            net_reason = "INITIAL_PROBE_PENDING: Belum menjalankan run_connectivity_diagnostics()."
        return {
            "status": "READY",
            "service_state": "LOCAL SERVICE READY",
            "provider_state": prov_st.get(
                "ui_state",
                "PROVIDER CONNECTED" if prov_st.get("available") else "PROVIDER UNAVAILABLE",
            ),
            "model_state": prov_st.get("model_state", prov_st.get("ui_state", "MODEL READY")),
            "network_connectivity_state": net_state,
            "network_connectivity_reason": net_reason,
            "provider_and_network_mode_separated": True,
            "provider_available": bool(prov_st.get("available", False)),
            "provider_details": prov_st,
            "ollama_engine": ollama_probe,
            "persona": self.persona_loader.load_official_persona_metadata(),
            "service": "CosmicTera NUI Local Service",
            "version": SERVICE_VERSION,
            "operating_mode": cur_mode,
            "active_provider": active_prov_id,
            "pid": os.getpid(),
            "timestamp": time.time(),
        }

    def disconnect_folder_complete(self, folder_id_or_path: str) -> tuple[int, dict[str, Any]]:
        """Execute complete Part A2 Connected Folder disconnect workflow."""
        res = self.storage.disconnect_authorized_folder(
            folder_id_or_path,
            in_use_folders=self.active_folder_processes,
        )
        if not res.get("ok"):
            status_str = str(res.get("status", "ERROR"))
            http_code = 409 if status_str == "FOLDER_IN_USE" else 404
            return (http_code, res)

        fpath = str(res["path"])
        fid = str(res["folder_id"])
        revoked_rules = self.permissions.revoke_folder_permissions(fpath)
        remaining_ctx_folders = self.context_retriever.release_folder(fpath)
        active_list = self.storage.list_authorized_folders(active_only=True)
        disconnected_list = [
            f for f in self.storage.list_authorized_folders(active_only=False) if not f.get("active")
        ]
        self.storage.record_audit(
            user_request=f"Disconnect Connected Folder {res.get('label')} ({fid})",
            tool_name="folders.disconnect",
            category="LOCAL_FILES",
            target=fpath,
            operation="DISCONNECT_FOLDER",
            approval_decision="USER_DISCONNECTED",
            status="DISCONNECTED",
            result_summary=res.get("notification", f"Disconnected folder {fid}"),
            metadata={
                "folder_id": fid,
                "revoked_permission_rules": revoked_rules,
                "physical_files_intact": res.get("physical_files_intact", True),
            },
        )
        res["revoked_permission_rules"] = revoked_rules
        res["active_context_folders"] = remaining_ctx_folders
        res["folders"] = active_list
        res["authorized_folders"] = active_list
        res["disconnected_folders"] = disconnected_list
        return (200, res)

    def reconnect_folder_complete(
        self,
        folder_id_or_path: str,
        *,
        label: str | None = None,
        access_mode: str | None = None,
    ) -> tuple[int, dict[str, Any]]:
        """Reconnect a previously disconnected folder or add a new folder and update context."""
        res = self.storage.reconnect_authorized_folder(
            folder_id_or_path,
            label=label,
            access_mode=access_mode,
        )
        if res.get("ok") is False:
            return (404, res)
        active_list = self.storage.list_authorized_folders(active_only=True)
        disconnected_list = [
            f for f in self.storage.list_authorized_folders(active_only=False) if not f.get("active")
        ]
        self.context_retriever.sync_active_folders([f["path"] for f in active_list])
        self.storage.record_audit(
            user_request=f"Connect/Reconnect Folder {res.get('label')} ({res.get('folder_id')})",
            tool_name="folders.connect",
            category="LOCAL_FILES",
            target=str(res.get("path", folder_id_or_path)),
            operation="CONNECT_FOLDER",
            approval_decision=f"USER_AUTHORIZED:{res.get('access_mode', 'READ_WRITE')}",
            status="CONNECTED",
            result_summary=res.get("notification", "Folder connected"),
            metadata={"folder_id": res.get("folder_id"), "access_mode": res.get("access_mode")},
        )
        res["folders"] = active_list
        res["authorized_folders"] = active_list
        res["disconnected_folders"] = disconnected_list
        return (200, res)

    def _dispatch_browser_op(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        """Dispatch Browser Workspace operations (`POST /api/browser/op` or `POST /api/web/op`)."""
        op_val = str(payload.get("op", "state")).lower()
        ie = self.internet_engine

        if op_val == "state":
            return (200, ie.get_browser_workspace_state())
        if op_val == "parse_input":
            return (
                200,
                parse_and_normalize_address_input(
                    str(payload.get("raw_input") or payload.get("url") or ""),
                    current_url=payload.get("current_url") or payload.get("previous_url"),
                    allow_explicit_http_downgrade=bool(payload.get("allow_explicit_http_downgrade", False)),
                ),
            )
        if op_val == "new_tab":
            return (
                200,
                ie.new_tab(
                    url=str(payload.get("url") or payload.get("initial_input") or "") or None,
                    title=str(payload.get("title") or "New Tab"),
                    switch_to=bool(payload.get("switch_to", payload.get("make_active", True))),
                    execute_fetch=bool(payload.get("execute_fetch", False)),
                ),
            )
        if op_val == "close_tab":
            return (200, ie.close_tab(str(payload.get("tab_id") or "")))
        if op_val == "switch_tab":
            return (200, ie.switch_tab(str(payload.get("tab_id") or "")))
        if op_val == "move_tab":
            return (
                200,
                ie.move_tab(
                    str(payload.get("tab_id") or ""),
                    int(payload.get("to_index", payload.get("new_index", 0))),
                ),
            )
        if op_val == "begin_navigation":
            return (
                200,
                ie.begin_tab_navigation(
                    payload.get("tab_id"),
                    str(payload.get("raw_input") or payload.get("url") or ""),
                    navigation_id=payload.get("navigation_id"),
                    record_back_stack=bool(payload.get("record_back_stack", True)),
                ),
            )
        if op_val == "navigate":
            return (
                200,
                ie.navigate_tab(
                    payload.get("tab_id"),
                    str(payload.get("raw_input") or payload.get("url") or ""),
                    navigation_id=payload.get("navigation_id"),
                    record_back_stack=bool(payload.get("record_back_stack", True)),
                    session_id=payload.get("session_id"),
                    allow_interactive_browser=bool(payload.get("allow_interactive_browser", True)),
                ),
            )
        if op_val == "navigation_traces":
            return (
                200,
                {
                    "ok": True,
                    "traces": ie.get_navigation_traces(
                        tab_id=payload.get("tab_id"),
                        limit=int(payload.get("limit", 50)),
                    ),
                },
            )
        if op_val == "back":
            return (200, ie.go_back(tab_id=payload.get("tab_id")))
        if op_val == "forward":
            return (200, ie.go_forward(tab_id=payload.get("tab_id")))
        if op_val == "reload":
            return (200, ie.reload_tab(tab_id=payload.get("tab_id")))
        if op_val == "stop":
            return (200, ie.stop_tab_loading(tab_id=payload.get("tab_id")))
        if op_val == "zoom":
            return (
                200,
                ie.set_tab_zoom(
                    payload.get("tab_id"),
                    float(payload.get("zoom_level", 1.0)),
                ),
            )
        if op_val == "find":
            return (
                200,
                ie.find_on_page(
                    payload.get("tab_id"),
                    str(payload.get("query") or ""),
                ),
            )
        if op_val == "recover_webkit":
            return (
                200,
                ie.handle_webkit_process_termination(
                    tab_id=payload.get("tab_id"),
                    auto_recover=bool(payload.get("auto_recover", True)),
                ),
            )
        if op_val == "sync_webview":
            return (
                200,
                ie.sync_webview_lifecycle_event(
                    tab_id=payload.get("tab_id"),
                    navigation_id=payload.get("navigation_id"),
                    event=str(payload.get("event") or "FINISHED"),
                    requested_url=payload.get("requested_url"),
                    normalized_url=payload.get("normalized_url"),
                    actual_url=payload.get("actual_url"),
                    url=payload.get("url"),
                    title=payload.get("title"),
                    http_status=payload.get("http_status") or payload.get("http_status_code"),
                    progress=payload.get("progress"),
                    can_go_back=payload.get("can_go_back"),
                    can_go_forward=payload.get("can_go_forward"),
                    error_code=payload.get("error_code"),
                    error_message=payload.get("error_message"),
                    elapsed_ms=payload.get("elapsed_ms"),
                    content_visible=payload.get("content_visible"),
                ),
            )
        if op_val == "restore_tabs":
            return (200, ie.restore_tabs_according_to_policy())
        if op_val == "list_bookmarks":
            bms = ie.list_bookmarks(folder=payload.get("folder"))
            folders = sorted({bm["folder"] for bm in bms} | {"Documentation", "Development", "General"})
            return (200, {"ok": True, "bookmarks": bms, "folders": folders})
        if op_val == "add_bookmark":
            return (
                200,
                ie.add_bookmark(
                    title=str(payload.get("title") or ""),
                    url=str(payload.get("url") or ""),
                    folder=str(payload.get("folder") or "General"),
                    favicon=payload.get("favicon"),
                ),
            )
        if op_val == "edit_bookmark":
            return (
                200,
                ie.edit_bookmark(
                    str(payload.get("bookmark_id") or ""),
                    title=payload.get("title"),
                    url=payload.get("url"),
                    folder=payload.get("folder"),
                ),
            )
        if op_val == "organize_bookmark":
            return (
                200,
                ie.organize_bookmark_folder(
                    str(payload.get("bookmark_id") or ""),
                    str(payload.get("folder") or "General"),
                ),
            )
        if op_val == "delete_bookmark":
            return (200, ie.delete_bookmark(str(payload.get("bookmark_id") or "")))
        if op_val == "search_history":
            return (
                200,
                {
                    "ok": True,
                    "history": ie.search_history(
                        query=payload.get("query"),
                        limit=int(payload.get("limit", 100)),
                    ),
                },
            )
        if op_val == "delete_history":
            ids = list(payload.get("visit_ids") or payload.get("history_ids") or [])
            if payload.get("visit_id") and payload["visit_id"] not in ids:
                ids.append(str(payload["visit_id"]))
            if payload.get("history_id") and payload["history_id"] not in ids:
                ids.append(str(payload["history_id"]))
            return (200, ie.delete_history_items(ids))
        if op_val == "clear_history":
            return (200, ie.clear_all_history())
        if op_val == "get_session_policy":
            return (200, {"ok": True, "session_policy": ie.get_session_policy()})
        if op_val == "set_session_policy":
            return (200, ie.set_session_policy(str(payload.get("policy") or "PERSISTENT_PROFILE")))
        if op_val == "clear_cookies":
            return (200, ie.clear_cookies())
        if op_val == "clear_cache":
            return (200, ie.clear_cache())
        if op_val == "clear_session":
            return (200, ie.clear_browser_session_data())
        if op_val == "download":
            return (
                200,
                ie.download_file_to_staging(
                    str(payload.get("url", "")),
                    filename=payload.get("filename"),
                    expected_sha256=payload.get("expected_sha256"),
                    session_id=payload.get("session_id"),
                    download_id=payload.get("download_id"),
                    allow_interactive_browser=bool(payload.get("allow_interactive_browser", False)),
                ),
            )
        if op_val == "cancel_download":
            return (200, ie.download_manager.cancel_download(str(payload.get("download_id") or "")))
        if op_val == "retry_download":
            return (
                200,
                ie.retry_download(
                    str(payload.get("download_id") or ""),
                    session_id=payload.get("session_id"),
                ),
            )
        if op_val == "remove_download":
            return (
                200,
                ie.download_manager.remove_download(
                    str(payload.get("download_id") or ""),
                    delete_staged_file=bool(payload.get("delete_staged_file", False)),
                ),
            )
        if op_val == "reveal_download":
            return (
                200,
                ie.download_manager.reveal_in_finder(
                    str(payload.get("download_id") or ""),
                    trigger_os_open=bool(payload.get("trigger_os_open", payload.get("execute_os_open", False))),
                ),
            )
        if op_val == "probe_site":
            return (
                200,
                ie.probe_single_site(
                    str(payload.get("url") or "https://docs.python.org/3/"),
                    timeout=float(payload.get("timeout", 4.0)),
                ),
            )
        if op_val == "diagnostics":
            return (200, ie.run_connectivity_diagnostics())

        return (400, {"error": f"Unknown browser op: {op_val}"})

    def dispatch_request(
        self, method: str, raw_path: str, body: dict[str, Any] | None = None
    ) -> tuple[int, dict[str, Any]]:
        """Dispatch an API request directly (used by HTTP server and tests)."""
        self._hot_reload_if_needed()
        parsed = urlparse(raw_path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)
        m = method.upper()
        payload = body or {}

        if m == "GET":
            if path == "/api/health":
                return (200, self.get_health_payload())
            if path == "/api/browser/state":
                return (200, self.internet_engine.get_browser_workspace_state())
            if path == "/api/capabilities":
                return (
                    200,
                    {
                        "providers": [
                            self.native_provider.status(),
                            self.ollama_provider.status(),
                            self.external_provider.status(),
                        ],
                        "permission_categories": PERMISSION_CATEGORIES,
                        "tools": self.tools.list_tools(),
                        "operating_mode": self.storage.get_setting("operating_mode", "HYBRID"),
                        "persona": self.persona_loader.load_official_persona_metadata(),
                        "model_library": self.model_library.get_model_library_snapshot(),
                    },
                )
            if path == "/api/persona":
                q = qs.get("q", ["CosmicTera NUI Architecture"])[0]
                learned = self.self_learning.list_knowledge(active_only=True)
                retrieved = self.context_retriever.retrieve(q, custom_knowledge_items=learned)
                prompt_text = self.persona_loader.build_system_prompt(
                    retrieved_sources=retrieved,
                    operating_mode=self.storage.get_setting("operating_mode", "HYBRID"),
                )
                meta = self.persona_loader.load_official_persona_metadata()
                meta["persona_source"] = "src/hijaiyyah/ai/runtime.py::HybitAIProgram.system"
                return (
                    200,
                    {
                        "persona": meta,
                        "system_prompt_preview": prompt_text,
                        "retrieved_context": [asdict(r) for r in retrieved],
                    },
                )
            if path == "/api/models/library":
                return (200, self.model_library.get_model_library_snapshot())
            if path == "/api/self-learning/overview":
                return (
                    200,
                    self.self_learning.get_self_learning_center_overview(
                        model_library=self.model_library
                    ),
                )
            if path == "/api/nui/layers":
                return (200, {"layers": self.native_provider.inspect_layers()})
            if path == "/api/layers/canonical":
                layer_id = (qs.get("layer", [None])[0] or "").upper()
                bridge = self.native_provider.layers_bridge
                if layer_id == "L0":
                    return (200, bridge.l0.get_overview())
                if layer_id == "L1":
                    return (200, bridge.l1.get_overview())
                if layer_id == "L2":
                    return (200, bridge.l2.get_overview())
                if layer_id == "L3":
                    return (200, bridge.l3.get_overview())
                if layer_id == "L4":
                    return (200, bridge.l4.get_parity_overview())
                if layer_id == "L5":
                    return (200, bridge.l5.get_host_observation_summary())
                if layer_id == "L6":
                    return (200, bridge.l6.get_hardware_intelligence_summary())
                if layer_id == "L7":
                    return (200, bridge.l7.get_overview())
                if layer_id == "L8":
                    return (200, bridge.l8.get_overview())
                if layer_id == "L9":
                    return (200, bridge.l9.get_overview())
                if layer_id == "L10":
                    return (200, bridge.l10.get_overview())
                if layer_id == "L11":
                    return (200, bridge.l11.get_overview())
                matrix_list = bridge.get_all_layers_live_matrix()
                return (
                    200,
                    {
                        "total_layers": len(matrix_list),
                        "layer_count": len(matrix_list),
                        "layers": matrix_list,
                    },
                )
            if path == "/api/subsystems":
                return (200, {"subsystems": self.native_provider.inspect_subsystems()})
            if path == "/api/sessions":
                q = qs.get("q", [None])[0]
                sid = qs.get("session_id", [None])[0]
                if sid:
                    sess = self.storage.get_session(sid)
                    return (200, sess) if sess else (404, {"error": "Session not found"})
                return (200, {"sessions": self.storage.list_sessions(query=q)})
            if path == "/api/sessions/export":
                sid = qs.get("session_id", [""])[0]
                md = self.storage.export_session_markdown(sid)
                return (
                    (200, {"session_id": sid, "markdown": md})
                    if md is not None
                    else (404, {"error": "Session not found"})
                )
            if path == "/api/comm/logs":
                sid = qs.get("session_id", [None])[0]
                return (
                    200,
                    {"communication_logs": self.storage.list_communication_logs(session_id=sid)},
                )
            if path == "/api/resources":
                sid = qs.get("session_id", [None])[0]
                st = qs.get("source_type", [None])[0]
                self.universal_file_engine.registry.sync_system_resources(self.remote_dev_engine)
                recs = self.universal_file_engine.registry.list_resources(source_type=st, session_id=sid)
                return (200, {"ok": True, "resources": [r.to_dict() for r in recs], "total": len(recs)})
            if path == "/api/tasks":
                return (200, {"tasks": self.storage.list_tasks()})
            if path.startswith("/api/tasks/"):
                parts = path.split("/")
                if len(parts) == 4:
                    t = self.storage.get_task(parts[3])
                    return (200, t) if t else (404, {"error": "Task not found"})
            if path == "/api/permissions":
                rules_list = list(self.permissions.list_rules(active_only=False))
                covered_cats = {r.get("category") for r in rules_list}
                for cat, meta in PERMISSION_CATEGORIES.items():
                    if cat not in covered_cats:
                        rules_list.append(
                            {
                                "category": cat,
                                "target_pattern": "*",
                                "mode": meta.get("default_risk", "ASK_EVERY_TIME"),
                            }
                        )
                all_flds = self.storage.list_authorized_folders(active_only=False)
                active_flds = [f for f in all_flds if f.get("active")]
                disc_flds = [f for f in all_flds if not f.get("active")]
                return (
                    200,
                    {
                        "categories": PERMISSION_CATEGORIES,
                        "rules": rules_list,
                        "pending_approvals": self.permissions.list_pending_approvals(status="PENDING"),
                        "authorized_folders": active_flds,
                        "disconnected_folders": disc_flds,
                        "api_connectors": self.storage.list_api_connectors(),
                    },
                )
            if path in {"/api/files/folders", "/api/folders"}:
                all_flds = self.storage.list_authorized_folders(active_only=False)
                active_flds = [f for f in all_flds if f.get("active")]
                disc_flds = [f for f in all_flds if not f.get("active")]
                return (
                    200,
                    {
                        "folders": active_flds,
                        "authorized_folders": active_flds,
                        "disconnected_folders": disc_flds,
                        "knowledge": {
                            "conversation_memory": self.storage.list_knowledge_items("conversation_memory"),
                            "reference_docs": self.storage.list_knowledge_items("reference_docs"),
                            "project_knowledge": self.storage.list_knowledge_items("project_knowledge"),
                        },
                    },
                )
            if path == "/api/hardware/status":
                sim_disc = qs.get("simulate_disconnected", ["0"])[0] in {"1", "true", "yes"}
                return (
                    200,
                    self.tools._handle_hardware_status({"simulate_disconnected": sim_disc}, {}),
                )
            if path == "/api/git/status":
                return (200, self.tools._handle_git_status({"repo_path": str(REPO_ROOT)}, {}))
            if path == "/api/audit":
                cat = qs.get("category", [None])[0]
                return (200, {"audit_logs": self.storage.list_audit_logs(limit=100, category=cat)})
            if path == "/api/settings":
                return (200, self.storage.get_all_settings())
            if path == "/api/web/status":
                probe_live = qs.get("probe", ["0"])[0] in {"1", "true", "yes"}
                cur_mode = self.storage.get_setting("operating_mode", "HYBRID")
                diag = (
                    self.internet_engine.run_connectivity_diagnostics()
                    if probe_live or self.internet_engine._last_diagnostics is None
                    else self.internet_engine._last_diagnostics
                )
                return (
                    200,
                    {
                        "status": "READY",
                        "connectivity_status": diag.get("overall_status", "READY"),
                        "diagnostics": diag,
                        "operating_mode": cur_mode,
                        "active_model_provider": self.storage.get_setting("active_provider", "local_ollama"),
                        "provider_mode_separated": True,
                        "web_allowed_in_current_mode": cur_mode != "LOCAL",
                        "search_provider": diag.get("search_provider", {}).get("provider", "Multi-Adapter Technical Search"),
                        "downloads": self.internet_engine.download_manager.list_downloads(),
                        "browser_workspace": self.internet_engine.get_browser_workspace_state(),
                        "session_policy": self.internet_engine.get_session_policy(),
                        "client_timeout_seconds": 6.0,
                        "sandbox_datastore": "NON_PERSISTENT" if self.internet_engine.get_session_policy() == "TEMPORARY_PRIVATE" else "PERSISTENT_PROFILE",
                        "last_checked": diag.get("last_checked", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
                    },
                )
            if path == "/api/vps/profiles":
                return (
                    200,
                    {
                        "profiles": self.remote_dev_engine.list_profiles(),
                        "total_profiles": len(self.remote_dev_engine.list_profiles()),
                    },
                )
            if path == "/api/master/panels":
                return (200, self.master_controller.get_control_center_panels())
            if path == "/api/master/llm-inventory":
                return (200, self.master_controller.llm_registry.get_inventory())
            if path == "/api/master/capabilities":
                return (200, self.master_controller.capability_intel.get_capability_matrix())
            if path == "/api/master/stack":
                return (200, self.master_controller.stack_mapper.map_full_stack())
            if path == "/api/master/repo-intel":
                return (200, self.master_controller.repo_intel.get_architecture_and_graph_summary())
            if path == "/api/master/subsystems":
                return (200, {"subsystems": self.master_controller.system_controller.inspect_all_subsystems()})
            if path == "/api/master/hardware-workflow":
                sim_disc = qs.get("simulate_disconnected", ["0"])[0] in {"1", "true", "yes"}
                return (
                    200,
                    self.master_controller.hardware_controller.inspect_hardware_and_fpga_workflow(
                        simulate_disconnected=sim_disc
                    ),
                )
            if path == "/api/master/engineering-memory":
                return (200, self.master_controller.engineering_memory.get_memory_breakdown())
            if path == "/api/phase9/status":
                return (
                    200,
                    {
                        "phase": "PHASE_9_UNIFIED_OPERATIONAL_INTELLIGENCE",
                        "operational_intents": list(_op_mod.OPERATIONAL_INTENTS),
                        "operational_cycle_stages": list(_op_mod.OPERATIONAL_CYCLE_STAGES),
                        "layers_live_matrix": self.native_provider.layers_bridge.get_all_layers_live_matrix(),
                        "recovery_status": self.operational_intelligence.reliability.get_recovery_status(),
                    },
                )

        if m == "POST":
            if path == "/api/browser/op":
                return self._dispatch_browser_op(payload)
            if path == "/api/settings/reset":
                defaults = {
                    "active_provider": "local_ollama",
                    "operating_mode": "HYBRID",
                    "selected_ollama_model": "qwen3:4b-instruct-2507-q4_K_M",
                    "theme": "COSMIC_DARK",
                    "streaming_enabled": "true",
                    "auto_scroll_enabled": "true",
                    "resource_policy": "BALANCED_M1_MAX_32GB",
                }
                for k, v in defaults.items():
                    self.storage.set_setting(k, v)
                return (
                    200,
                    {
                        "reset": True,
                        "status": "RESET_TO_DEFAULTS",
                        "settings": self.storage.get_all_settings(),
                    },
                )
            if path == "/api/phase9/converse":
                msg_text = str(payload.get("user_message") or payload.get("message") or payload.get("prompt") or "")
                sess_id = str(payload.get("session_id") or "")
                if not sess_id:
                    sess_id = self.storage.create_session(title=msg_text[:48] or "Phase 9 Session")["session_id"]
                p9_res = self.operational_intelligence.execute_operational_cycle(msg_text, sess_id)
                return (200, p9_res)
            if path == "/api/chat":
                msg_text = str(payload.get("user_message") or payload.get("message") or "")
                out = self.orchestrator.handle_chat_turn(
                    session_id=payload.get("session_id"),
                    user_message=msg_text,
                    request_id=payload.get("request_id"),
                    message_id=payload.get("message_id"),
                    provider_id=payload.get("provider") or payload.get("provider_id"),
                    model=payload.get("model"),
                    attachments=payload.get("attachments"),
                    tool_call=payload.get("tool_call"),
                    ui_handler=str(payload.get("ui_handler", "NUIDesktopStore.sendChatMessage")),
                    simulate_stop=bool(payload.get("simulate_stop", False)),
                )
                return (200, out)
            if path == "/api/chat/stop":
                out = self.orchestrator.stop_chat_generation(
                    request_id=payload.get("request_id"),
                    session_id=payload.get("session_id"),
                )
                return (200, out)
            if path == "/api/chat/op":
                op_val = str(payload.get("op", "")).lower()
                if op_val == "edit_and_resend":
                    return (
                        200,
                        self.orchestrator.edit_and_resend_chat_turn(
                            session_id=str(payload.get("session_id") or ""),
                            target_message_id=payload.get("message_id") or payload.get("target_message_id"),
                            edited_user_message=str(payload.get("user_message") or payload.get("content") or ""),
                            provider_id=payload.get("provider") or payload.get("provider_id"),
                            model=payload.get("model"),
                            attachments=payload.get("attachments"),
                        ),
                    )
                if op_val == "regenerate":
                    return (
                        200,
                        self.orchestrator.regenerate_chat_turn(
                            session_id=str(payload.get("session_id") or ""),
                            assistant_message_id=payload.get("message_id") or payload.get("assistant_message_id"),
                            provider_id=payload.get("provider") or payload.get("provider_id"),
                            model=payload.get("model"),
                        ),
                    )
                if op_val == "feedback":
                    sid = str(payload.get("session_id") or "")
                    mid = str(payload.get("message_id") or "")
                    rating = str(payload.get("rating") or "THUMBS_UP")
                    note = str(payload.get("note") or payload.get("correction_summary") or "")
                    fb_res = self.storage.record_message_feedback(sid, mid, rating, note)
                    if note and self.self_learning is not None:
                        sl_entry = self.self_learning.apply_user_feedback(
                            topic=f"Chat Feedback ({rating} on {mid})",
                            correction_summary=note,
                            applicable_domain="chat_feedback",
                        )
                        fb_res["self_learning_entry"] = sl_entry
                    return (200, fb_res)
                if op_val == "save_draft":
                    draft_val = str(payload.get("draft") if payload.get("draft") is not None else (payload.get("draft_text") or ""))
                    return (
                        200,
                        self.storage.save_session_draft(
                            str(payload.get("session_id") or "default"),
                            draft_val,
                        ),
                    )
                if op_val == "get_draft":
                    sid = str(payload.get("session_id") or "default")
                    d_txt = self.storage.get_session_draft(sid)
                    return (200, {"ok": True, "session_id": sid, "draft": d_txt, "draft_text": d_txt})
                return (400, {"error": f"Unknown chat op: {op_val}"})
            if path == "/api/context/retrieve":
                q = str(payload.get("query") or "")
                top_k = int(payload.get("top_k", 5))
                learned = self.self_learning.list_knowledge(active_only=True)
                items = [
                    asdict(r)
                    for r in self.context_retriever.retrieve(
                        q, custom_knowledge_items=learned, max_sources=top_k
                    )
                ]
                return (200, {"query": q, "items": items, "total_matches": len(items)})
            if path == "/api/models/op":
                op = str(payload.get("op", "refresh")).lower()
                if op == "refresh":
                    return (200, self.model_library.get_model_library_snapshot())
                if op == "select":
                    model_tag = str(payload.get("model_tag") or payload.get("model") or "qwen3:4b-instruct-2507-q4_K_M")
                    res = self.model_library.select_model(model_tag)
                    self.storage.set_setting("selected_ollama_model", model_tag)
                    return (200, res)
                if op in {"load", "unload"}:
                    model_tag = str(
                        payload.get("model_tag")
                        or payload.get("model")
                        or self.model_library.selected_model
                    )
                    return (
                        200,
                        self.model_library.load_or_unload_model(
                            model_tag, action=op.upper()
                        ),
                    )
                if op in {"verify", "test"}:
                    model_tag = str(
                        payload.get("model_tag")
                        or payload.get("model")
                        or self.model_library.selected_model
                    )
                    return (200, self.model_library.verify_model_inference(model_tag))
                if op == "config":
                    cfg = self.model_library.update_engine_config(
                        context_length=payload.get("context_length"),
                        temperature=payload.get("temperature"),
                        max_output_tokens=payload.get("max_output_tokens"),
                        selected_model=payload.get("selected_model"),
                    )
                    return (200, cfg)
                if op == "route":
                    return (
                        200,
                        self.multi_model_router.route_task(
                            str(payload.get("query", "")),
                            requested_provider=payload.get("provider"),
                            requested_model=payload.get("model"),
                        ),
                    )
                return (400, {"error": f"Unknown model op: {op}"})
            if path == "/api/self-learning/op":
                op = str(payload.get("op", "overview")).lower()
                if op == "overview":
                    return (
                        200,
                        self.self_learning.get_self_learning_center_overview(
                            model_library=self.model_library
                        ),
                    )
                if op == "ingest_knowledge":
                    entry = self.self_learning.ingest_knowledge(
                        topic=str(payload.get("topic", "Project Knowledge")),
                        summary=str(payload.get("summary", "")),
                        source=str(payload.get("source", "Repository")),
                        confidence=str(payload.get("confidence", "Repository Derived")),
                        validation_status=str(payload.get("validation_status", "VALIDATED")),
                        applicable_domain=str(payload.get("applicable_domain", "general")),
                        code_artifact=payload.get("code_artifact"),
                        test_evidence=payload.get("test_evidence"),
                        metadata=payload.get("metadata"),
                    )
                    return (200, entry)
                if op == "run_coding_skill":
                    res = self.self_learning.run_coding_skill_cycle(
                        skill_name=str(payload.get("skill_name", "Learned Coding Skill")),
                        problem_statement=str(payload.get("problem_statement", "")),
                        module_code=str(payload.get("module_code", "")),
                        test_code=str(payload.get("test_code", "")),
                        applicable_domain=str(payload.get("applicable_domain", "python_coding")),
                        source=str(payload.get("source", "NUI Coding Studio")),
                    )
                    return (200, res)
                if op == "feedback":
                    res = self.self_learning.apply_user_feedback(
                        topic=str(payload.get("topic", "User Feedback Correction")),
                        correction_summary=str(payload.get("correction_summary", "")),
                        target_entry_id=payload.get("target_entry_id"),
                        applicable_domain=str(payload.get("applicable_domain", "user_preference")),
                    )
                    return (200, res)
                if op == "rollback":
                    res = self.self_learning.rollback_entry(
                        entry_id=str(payload.get("entry_id", "")),
                        reason=str(payload.get("reason", "Rollback requested by user")),
                    )
                    return (200, res)
                if op == "check_boundary":
                    res = self.self_learning.attempt_protected_modification(
                        target_domain=str(payload.get("target_domain", "NUI_PERSONA")),
                        proposed_change=str(payload.get("proposed_change", "")),
                    )
                    return (200, res)
                return (400, {"error": f"Unknown self-learning op: {op}"})
            if path == "/api/sessions":
                sess = self.storage.create_session(
                    title=str(payload.get("title", "Sesi Baru CosmicTera NUI")),
                    mode=payload.get("mode"),
                    provider=payload.get("provider"),
                    session_id=payload.get("session_id"),
                )
                return (201, sess)
            if path == "/api/sessions/rename":
                sess = self.storage.rename_session(
                    str(payload["session_id"]), str(payload["title"])
                )
                return (200, sess or {"error": "Not found"})
            if path == "/api/sessions/delete":
                deleted = self.storage.delete_session(str(payload["session_id"]))
                return (200, {"deleted": deleted})
            if path == "/api/subsystems/execute":
                kind = payload.get("kind")
                if kind:
                    res = self.native_provider.execute_calculation_or_program(
                        str(kind), payload.get("payload", {})
                    )
                    return (200, res)
                sub_name = str(payload.get("subsystem", "HYBIT_18D_MATH"))
                self.permissions.set_rule(
                    category="CODE_EXECUTION",
                    target_type="subsystem",
                    target_value=sub_name,
                    operation="*",
                    decision="ALWAYS_ALLOW",
                )
                out = self.tools.execute_tool(
                    "cosmictera.control_loop",
                    {
                        "subsystem": sub_name,
                        "operation": payload.get("operation", "COMPUTE_BSM_112_10_9"),
                        "payload": payload.get("payload", {}),
                    },
                    user_request=str(payload.get("user_request", "Subsystem control loop")),
                )
                return (200, out)
            if path == "/api/tasks":
                t = self.orchestrator.create_and_run_task(
                    title=str(payload.get("title", "NUI Task")),
                    steps=list(payload.get("steps", [])),
                    session_id=payload.get("session_id"),
                    user_request=str(payload.get("user_request", "")),
                )
                return (201, t)
            if path.startswith("/api/tasks/") and path.endswith("/stop"):
                tid = path.split("/")[3]
                return (200, self.orchestrator.stop_task(tid))
            if path.startswith("/api/tasks/") and path.endswith("/resume"):
                tid = path.split("/")[3]
                return (200, self.orchestrator.run_or_resume_task(tid))
            if path == "/api/permissions/request":
                perm = self.permissions.check_or_request(
                    category=str(payload["category"]),
                    operation=str(payload.get("operation", "EXEC")),
                    target_type=str(payload.get("target_type", "resource")),
                    target_value=str(payload.get("target_value", "*")),
                    reason=str(payload.get("reason", "Explicit permission check")),
                    session_id=payload.get("session_id"),
                    task_id=payload.get("task_id"),
                    risk_level=payload.get("risk_level"),
                    payload=payload.get("payload"),
                    explicit_final_deploy_confirmed=bool(
                        payload.get("explicit_final_deploy_confirmed", False)
                    ),
                )
                return (200, perm.__dict__)
            if path == "/api/permissions/decide":
                if "request_id" in payload and payload["request_id"]:
                    res = self.permissions.decide_request(
                        request_id=str(payload["request_id"]),
                        decision=str(payload["decision"]),
                        expires_in_seconds=payload.get("expires_in_seconds"),
                    )
                    return (200, res)
                rule = self.permissions.set_rule(
                    category=str(payload["category"]),
                    target_type=str(payload["target_type"]),
                    target_value=str(payload["target_value"]),
                    operation=str(payload.get("operation", "*")),
                    decision=str(payload["decision"]),
                    session_id=payload.get("session_id"),
                    expires_at=payload.get("expires_at"),
                )
                return (200, rule)
            if path == "/api/permissions/revoke":
                if "rule_id" in payload:
                    return (200, {"revoked": self.permissions.revoke_rule(str(payload["rule_id"]))})
                count = self.permissions.revoke_Matching_rules(
                    category=str(payload["category"]),
                    target_type=str(payload["target_type"]),
                    target_value=str(payload["target_value"]),
                )
                return (200, {"revoked_count": count})
            if path in {"/api/files/folders", "/api/folders", "/api/folders/reconnect"}:
                action = str(payload.get("action", "RECONNECT" if path.endswith("/reconnect") else "ADD")).upper()
                target_id_or_path = str(payload.get("folder_id") or payload.get("path") or "")
                if action in {"REVOKE", "DISCONNECT", "DELETE"}:
                    return self.disconnect_folder_complete(target_id_or_path)
                return self.reconnect_folder_complete(
                    target_id_or_path,
                    label=payload.get("label"),
                    access_mode=str(payload.get("access_mode", "READ_WRITE")) if payload.get("access_mode") else None,
                )
            if path == "/api/files/op":
                tool_name = f"files.{payload.get('op', 'list')}"
                params = dict(payload.get("params") or {})
                for k in ("path", "content", "pattern"):
                    if k in payload and k not in params:
                        params[k] = payload[k]
                out = self.tools.execute_tool(
                    tool_name,
                    params,
                    user_request=str(payload.get("user_request", f"File op {tool_name}")),
                    session_id=payload.get("session_id"),
                )
                return (200, out)
            if path == "/api/coding/op":
                tool_name = f"coding.{payload.get('op', 'edit')}"
                out = self.tools.execute_tool(
                    tool_name,
                    payload.get("params", {}),
                    user_request=str(payload.get("user_request", f"Coding op {tool_name}")),
                    session_id=payload.get("session_id"),
                )
                return (200, out)
            if path == "/api/web/op":
                op_val = str(payload.get("op", "")).lower()
                if "tool" in payload:
                    tool_name = str(payload["tool"])
                    params = dict(payload.get("params") or {})
                    for k in ("query", "url"):
                        if k in payload and k not in params:
                            params[k] = payload[k]
                    out = self.tools.execute_tool(
                        tool_name,
                        params,
                        user_request=str(payload.get("user_request", f"Web op {tool_name}")),
                        session_id=payload.get("session_id"),
                        untrusted_context=bool(payload.get("untrusted_context", False)),
                        explicit_final_deploy_confirmed=bool(
                            payload.get("explicit_final_deploy_confirmed", False)
                        ),
                    )
                    return (200, out)
                browser_ops = {
                    "state",
                    "parse_input",
                    "new_tab",
                    "close_tab",
                    "switch_tab",
                    "move_tab",
                    "begin_navigation",
                    "navigate",
                    "navigation_traces",
                    "back",
                    "forward",
                    "reload",
                    "stop",
                    "zoom",
                    "find",
                    "recover_webkit",
                    "sync_webview",
                    "restore_tabs",
                    "list_bookmarks",
                    "add_bookmark",
                    "edit_bookmark",
                    "organize_bookmark",
                    "delete_bookmark",
                    "search_history",
                    "delete_history",
                    "clear_history",
                    "get_session_policy",
                    "set_session_policy",
                    "clear_cookies",
                    "clear_cache",
                    "clear_session",
                    "download",
                    "cancel_download",
                    "retry_download",
                    "remove_download",
                    "reveal_download",
                    "probe_site",
                    "diagnostics",
                }
                if op_val in browser_ops:
                    return self._dispatch_browser_op(payload)
                if op_val == "fetch":
                    url_val = str(payload.get("url") or (payload.get("params") or {}).get("url") or "")
                    for_browser = bool(payload.get("for_browser", False))
                    return (
                        200,
                        self.internet_engine.fetch_url(
                            url_val,
                            session_id=payload.get("session_id"),
                            for_browser=for_browser,
                            allow_interactive_browser=bool(payload.get("allow_interactive_browser", False)),
                        ),
                    )
                if op_val == "compare":
                    urls = list(payload.get("urls") or [])
                    return (200, self.internet_engine.compare_sources(urls, topic=str(payload.get("topic", "Comparison")), session_id=payload.get("session_id")))
                if op_val == "save_note":
                    return (
                        200,
                        self.internet_engine.save_research_note(
                            title=str(payload.get("title", "Research Note")),
                            summary=str(payload.get("summary", "")),
                            citations=list(payload.get("citations") or []),
                        ),
                    )
                if op_val == "dependency_plan":
                    return (
                        200,
                        self.internet_engine.inspect_dependency_plan(
                            manager=str(payload.get("manager", "pip")),
                            package=str(payload.get("package", "")),
                            version=payload.get("version"),
                            target_workspace=payload.get("target_workspace"),
                        ),
                    )
                if op_val == "dependency_install":
                    return (
                        200,
                        self.internet_engine.install_dependency(
                            manager=str(payload.get("manager", "pip")),
                            package=str(payload.get("package", "")),
                            version=payload.get("version"),
                            target_workspace=payload.get("target_workspace"),
                            dry_run=bool(payload.get("dry_run", True)),
                            session_id=payload.get("session_id"),
                        ),
                    )
                if op_val in {"check_domain", "inspect_domain", "verify_domain"}:
                    return (
                        200,
                        self.internet_engine.inspect_domain_and_website(
                            domain=str(payload.get("domain") or payload.get("url") or "www.akademihijaiyyahindonesia.com"),
                            target_vps_ip=payload.get("target_vps_ip"),
                            remote_verified=bool(payload.get("remote_verified", False)),
                            timeout=float(payload.get("timeout", 6.0)),
                        ),
                    )
                if op_val == "dns_records":
                    rec_types = tuple(payload.get("record_types") or ("A", "AAAA", "CNAME", "NS", "MX", "TXT"))
                    return (
                        200,
                        self.internet_engine.resolve_dns_records(
                            str(payload.get("domain") or "www.akademihijaiyyahindonesia.com"),
                            record_types=rec_types,
                            timeout=float(payload.get("timeout", 5.0)),
                        ),
                    )
                if op_val == "http_tls":
                    return (
                        200,
                        self.internet_engine.inspect_http_https_and_redirects(
                            str(payload.get("domain") or payload.get("url") or "www.akademihijaiyyahindonesia.com"),
                            timeout=float(payload.get("timeout", 6.0)),
                        ),
                    )
                if op_val == "network_interfaces":
                    return (200, self.internet_engine.check_network_interfaces())
                # Default to live internet search (with legacy web.search tool fallback if needed)
                q_val = str(payload.get("query") or (payload.get("params") or {}).get("query") or "")
                res = self.internet_engine.search_web(q_val, session_id=payload.get("session_id"))
                if res.get("status") == "WAITING_FOR_APPROVAL":
                    params = dict(payload.get("params") or {"query": q_val})
                    tool_out = self.tools.execute_tool(
                        "web.search",
                        params,
                        user_request=str(payload.get("user_request", f"Web search {q_val}")),
                        session_id=payload.get("session_id"),
                    )
                    if tool_out.get("ok"):
                        return (200, tool_out)
                return (200, res)
            if path == "/api/vps/op":
                op_val = str(payload.get("op", "list")).lower()
                if op_val == "list":
                    return (200, {"profiles": self.remote_dev_engine.list_profiles()})
                if op_val == "register":
                    prof = self.remote_dev_engine.register_profile(
                        name=str(payload.get("name", "VPS Server")),
                        host=str(payload["host"]),
                        username=str(payload.get("username", "ubuntu")),
                        expected_host_fingerprint=str(payload.get("expected_host_fingerprint", "")),
                        remote_workspace=str(payload.get("remote_workspace", "/home/ubuntu/workspace")),
                        port=int(payload.get("port", 22)),
                        auth_method=str(payload.get("auth_method", "SSH_KEY")),
                        ssh_key_path=payload.get("ssh_key_path"),
                        secret_credential=payload.get("secret_credential"),
                        connect_timeout_seconds=float(payload.get("connect_timeout_seconds", 8.0)),
                    )
                    return (200, prof)
                if op_val == "connect":
                    return (
                        200,
                        self.remote_dev_engine.connect_and_inspect(
                            str(payload["profile_id"]),
                            session_id=payload.get("session_id"),
                        ),
                    )
                if op_val == "disconnect":
                    return (
                        200,
                        self.remote_dev_engine.disconnect_profile(
                            str(payload.get("profile_id") or ""),
                        ),
                    )
                if op_val == "discover_config":
                    return (
                        200,
                        self.remote_dev_engine.discover_ssh_and_deployment_metadata(
                            str(payload.get("folder_path") or payload.get("path") or "/Users/AMRA/yayasan"),
                        ),
                    )
                if op_val == "inspect_remote_manifest":
                    return (
                        200,
                        self.remote_dev_engine.inspect_remote_workspace_manifest(
                            str(payload.get("profile_id") or ""),
                            remote_path=payload.get("remote_path"),
                            session_id=payload.get("session_id"),
                        ),
                    )
                if op_val == "set_folder_mapping":
                    return (
                        200,
                        self.universal_file_engine.registry.set_folder_vps_mapping(
                            local_canonical_path=str(payload.get("local_path") or payload.get("path") or "/Users/AMRA/yayasan"),
                            remote_profile_id=payload.get("profile_id"),
                            remote_host_identifier=payload.get("remote_host"),
                            remote_workspace_path=payload.get("remote_workspace_path"),
                            permission_scope=str(payload.get("permission_scope", "READ_LOCAL")),
                            last_local_inspection=payload.get("last_local_inspection"),
                            last_remote_inspection=payload.get("last_remote_inspection"),
                            last_successful_synchronization=payload.get("last_successful_synchronization"),
                            last_verified_commit=payload.get("last_verified_commit"),
                            last_verified_manifest=payload.get("last_verified_manifest"),
                        ),
                    )
                if op_val == "get_folder_mapping":
                    m_res = self.universal_file_engine.registry.get_folder_vps_mapping(
                        str(payload.get("local_path") or payload.get("path") or "/Users/AMRA/yayasan"),
                    )
                    return (200, {"ok": m_res is not None, "mapping": m_res})
                if op_val == "compare_manifests":
                    return (
                        200,
                        self.universal_file_engine.compare_local_and_remote_manifests(
                            local_path=str(payload.get("local_path") or payload.get("path") or "/Users/AMRA/yayasan"),
                            profile_id=payload.get("profile_id"),
                            remote_path=payload.get("remote_path"),
                            remote_manifest_override=payload.get("remote_manifest_override"),
                            session_id=payload.get("session_id"),
                        ),
                    )
                if op_val == "full_verification":
                    q_str = str(
                        payload.get("query")
                        or f"Apakah folder {payload.get('local_path', '/Users/AMRA/yayasan')} sudah terhubung ke VPS? Apakah file sudah di-upload? Apakah domain {payload.get('domain', 'www.akademihijaiyyahindonesia.com')} sudah terhubung ke server?"
                    )
                    insp = _prov_mod.run_folder_vps_inspection(
                        q_str,
                        context={
                            "remote_dev_engine": self.remote_dev_engine,
                            "universal_file_engine": self.universal_file_engine,
                            "internet_engine": self.internet_engine,
                        },
                    )
                    return (200, insp or {"ok": False, "error": "INSPECTION_NOT_MATCHED"})
                if op_val == "read":
                    return (
                        200,
                        self.remote_dev_engine.read_remote_file(
                            str(payload["profile_id"]),
                            str(payload["remote_path"]),
                            session_id=payload.get("session_id"),
                        ),
                    )
                if op_val == "write":
                    return (
                        200,
                        self.remote_dev_engine.write_remote_file(
                            str(payload["profile_id"]),
                            str(payload["remote_path"]),
                            str(payload.get("content", "")),
                            session_id=payload.get("session_id"),
                        ),
                    )
                if op_val == "execute":
                    return (
                        200,
                        self.remote_dev_engine.execute_remote_command(
                            str(payload["profile_id"]),
                            str(payload["command"]),
                            cwd=payload.get("cwd"),
                            timeout_seconds=payload.get("timeout_seconds"),
                            explicit_sudo_approved=bool(payload.get("explicit_sudo_approved", False)),
                            explicit_destructive_approved=bool(payload.get("explicit_destructive_approved", False)),
                            session_id=payload.get("session_id"),
                        ),
                    )
                if op_val == "deploy":
                    return (
                        200,
                        self.remote_dev_engine.execute_remote_deployment(
                            str(payload["profile_id"]),
                            str(payload.get("deploy_command", "./deploy.sh")),
                            explicit_final_deploy_confirmed=bool(
                                payload.get("explicit_final_deploy_confirmed", False)
                            ),
                            session_id=payload.get("session_id"),
                        ),
                    )
                if op_val == "recover":
                    return (
                        200,
                        self.remote_dev_engine.recover_connection(
                            str(payload["profile_id"]),
                            session_id=payload.get("session_id"),
                        ),
                    )
                if op_val in {"inspect_folder", "folder_status"}:
                    return (
                        200,
                        self.remote_dev_engine.inspect_folder_vps_status(
                            str(payload.get("folder") or payload.get("folder_path") or payload.get("path") or "/Users/AMRA/yayasan"),
                            mount_table_override=payload.get("mount_table_override"),
                            sync_mechanism=payload.get("sync_mechanism"),
                            sync_verification_proof=payload.get("sync_verification_proof"),
                            simulate_transport_unknown=bool(payload.get("simulate_transport_unknown", False)),
                        ),
                    )
                return (400, {"error": f"Unknown VPS op: {op_val}"})
            if path in {"/api/resources/op", "/api/files/universal"}:
                op_val = str(payload.get("op", "execute_chat_action")).lower()
                ufe = self.universal_file_engine
                if op_val == "attach":
                    return (
                        200,
                        ufe.attach_and_register(
                            name=payload.get("name"),
                            path_or_reference=str(payload.get("path") or payload.get("reference") or ""),
                            source_type=str(payload.get("source_type", "CHAT_ATTACHMENT")),
                            session_id=payload.get("session_id"),
                            base64_content=payload.get("base64_content"),
                            text_content=payload.get("text_content"),
                        ),
                    )
                if op_val == "resolve":
                    return (
                        200,
                        ufe.resolver.resolve(
                            str(payload.get("query") or payload.get("user_message") or ""),
                            session_id=payload.get("session_id"),
                            current_attachment_ids=payload.get("current_attachment_ids"),
                            explicit_resource_id=payload.get("resource_id"),
                        ),
                    )
                if op_val == "inspect":
                    p = Path(str(payload.get("path") or "")).expanduser().resolve()
                    return (200, ufe.doc_intelligence.inspect_and_extract(p))
                if op_val == "traverse":
                    return (
                        200,
                        ufe.list_and_traverse_directory(
                            str(payload.get("resource_id") or payload.get("path") or ""),
                            recursive=bool(payload.get("recursive", True)),
                        ),
                    )
                if op_val == "search":
                    return (
                        200,
                        ufe.search_across_files(
                            str(payload.get("query") or ""),
                            list(payload.get("targets") or [payload.get("path") or REPO_ROOT]),
                        ),
                    )
                if op_val == "compare":
                    return (
                        200,
                        ufe.doc_intelligence.compare_documents(
                            Path(str(payload["path_a"])).expanduser().resolve(),
                            Path(str(payload["path_b"])).expanduser().resolve(),
                        ),
                    )
                if op_val == "edit":
                    return (
                        200,
                        ufe.edit_resource_file(
                            str(payload.get("resource_id") or payload.get("path") or ""),
                            new_content=payload.get("new_content"),
                            target_snippet=payload.get("target_snippet"),
                            replacement_snippet=payload.get("replacement_snippet"),
                            allow_overwrite_original_attachment=bool(payload.get("allow_overwrite_original_attachment", False)),
                            session_id=payload.get("session_id"),
                        ),
                    )
                if op_val == "merge_pdf":
                    return (
                        200,
                        ufe.merge_documents_to_pdf(
                            list(payload.get("sources") or []),
                            output_pdf_path=Path(str(payload["output_path"])).expanduser().resolve() if payload.get("output_path") else None,
                            title=str(payload.get("title", "CosmicTera NUI Combined PDF")),
                            session_id=payload.get("session_id"),
                        ),
                    )
                if op_val == "spreadsheet_report":
                    return (
                        200,
                        ufe.generate_spreadsheet_report(
                            list(payload.get("sources") or []),
                            output_report_path=Path(str(payload["output_path"])).expanduser().resolve() if payload.get("output_path") else None,
                            session_id=payload.get("session_id"),
                        ),
                    )
                if op_val == "infographic":
                    return (
                        200,
                        ufe.generate_infographic_from_resources(
                            list(payload.get("sources") or []),
                            output_svg_path=Path(str(payload["output_path"])).expanduser().resolve() if payload.get("output_path") else None,
                            session_id=payload.get("session_id"),
                        ),
                    )
                if op_val == "transfer_to_vps":
                    return (
                        200,
                        ufe.transfer_resource_to_vps(
                            str(payload.get("resource_id") or payload.get("path") or ""),
                            profile_id=payload.get("profile_id"),
                            remote_target_subpath=payload.get("remote_target_subpath"),
                            session_id=payload.get("session_id"),
                        ),
                    )
                return (
                    200,
                    ufe.execute_chat_file_action(
                        str(payload.get("user_message") or payload.get("query") or ""),
                        session_id=payload.get("session_id"),
                        attachments=payload.get("attachments"),
                    ),
                )
            if path == "/api/hardware/control":
                self.permissions.set_rule(
                    category="CODE_EXECUTION",
                    target_type="subsystem",
                    target_value=str(payload.get("subsystem", "TANG_NANO_20K")),
                    operation="*",
                    decision="ALWAYS_ALLOW",
                )
                out = self.tools.execute_tool(
                    "hardware.control",
                    {
                        "subsystem": payload.get("subsystem", "TANG_NANO_20K"),
                        "action": payload.get("action", "S1_STOP"),
                        "payload": payload.get("payload", {}),
                    },
                    user_request=f"Hardware Monitor control: {payload.get('action')}",
                )
                return (200, out)
            if path == "/api/settings":
                for k, v in payload.items():
                    self.storage.set_setting(k, v)
                return (200, self.storage.get_all_settings())
            if path == "/api/master/op":
                op = str(payload.get("op", "panels")).lower()
                if op == "panels":
                    return (200, self.master_controller.get_control_center_panels())
                if op == "benchmark_model":
                    mid = str(payload.get("model_id") or self.model_library.selected_model)
                    live = bool(payload.get("run_live_probe", True))
                    return (
                        200,
                        self.master_controller.capability_intel.evaluate_model_capabilities(
                            mid, run_live_probe=live
                        ),
                    )
                if op == "select_optimal_model":
                    return (
                        200,
                        self.master_controller.intelligent_router.select_optimal_model(
                            str(payload.get("prompt", "")),
                            latency_budget_ms=float(payload.get("latency_budget_ms", 15000.0)),
                            require_heavy_specialist=bool(
                                payload.get("require_heavy_specialist", False)
                            ),
                        ),
                    )
                if op == "multi_model_pipeline":
                    return (
                        200,
                        self.master_controller.intelligent_router.execute_multi_model_pipeline(
                            str(payload.get("task_prompt") or payload.get("prompt") or ""),
                            prefer_fast=bool(payload.get("prefer_fast", True)),
                            verify_code_syntax=bool(payload.get("verify_code_syntax", True)),
                        ),
                    )
                if op == "semantic_search":
                    return (
                        200,
                        self.master_controller.repo_intel.semantic_code_search(
                            str(payload.get("query", "")),
                            limit=int(payload.get("limit", 10)),
                        ),
                    )
                if op == "test_map":
                    return (
                        200,
                        self.master_controller.repo_intel.map_tests_to_code(
                            str(payload.get("target", "hisa"))
                        ),
                    )
                if op == "trace_error":
                    return (
                        200,
                        self.master_controller.repo_intel.trace_error_to_source(
                            str(payload.get("traceback_text", ""))
                        ),
                    )
                if op == "impact_analysis":
                    return (
                        200,
                        self.master_controller.repo_intel.analyze_cross_layer_impact(
                            str(payload.get("path", "src/hijaiyyah/hisa/vm.py"))
                        ),
                    )
                if op == "engineering_loop":
                    return (
                        200,
                        self.master_controller.engineering_loop.run_engineering_loop(
                            task_goal=str(payload["task_goal"]),
                            target_file=Path(str(payload["target_file"])),
                            test_file=Path(str(payload["test_file"])),
                            candidate_patch_code=str(payload["candidate_patch_code"]),
                            repaired_patch_code=payload.get("repaired_patch_code"),
                        ),
                    )
                if op == "store_memory":
                    return (
                        200,
                        self.master_controller.engineering_memory.store_memory(
                            category=str(payload.get("category", "ARCHITECTURE_KNOWLEDGE")),
                            title=str(payload.get("title", "Engineering Note")),
                            content=str(payload.get("content", "")),
                            epistemic_state=str(payload.get("epistemic_state", "CANDIDATE")),
                            source_path=str(payload.get("source_path", "NUI Engineering")),
                            evidence=str(payload.get("evidence", "")),
                            supersede_memory_id=payload.get("supersede_memory_id"),
                        ),
                    )
                if op == "check_immutable_path":
                    return (
                        200,
                        check_immutable_core_path(
                            str(payload.get("path", "")),
                            explicit_owner_approval=bool(
                                payload.get("explicit_owner_approval", False)
                            ),
                        ),
                    )
                if op == "check_pull_readiness":
                    return (
                        200,
                        self.master_controller.llm_registry.check_pull_model_readiness(
                            str(payload.get("model_id", "qwen3.8:27b")),
                            estimated_size_gib=float(payload.get("estimated_size_gib", 18.0)),
                            user_approved=bool(payload.get("user_approved", False)),
                        ),
                    )
                return (400, {"error": f"Unknown master op: {op}"})
            if path == "/api/layers/query":
                op = str(payload.get("op", "matrix")).lower()
                bridge = self.native_provider.layers_bridge
                if op == "matrix":
                    return (200, {"layers": bridge.get_all_layers_live_matrix()})
                if op == "l0_atom":
                    return (200, bridge.l0.inspect_letter_atom(payload.get("letter", "Jim")))
                if op == "l0_address_unification":
                    return (200, bridge.l0.verify_address_unification())
                if op == "l0_claims":
                    return (200, bridge.l0.verify_angle_claims())
                if op == "l1_impact":
                    return (200, bridge.l1.query_file_impact(str(payload.get("path", "src/hijaiyyah/hisa/machine.py"))))
                if op == "l2_explain":
                    return (200, bridge.l2.explain_program(str(payload.get("target", "rtl/hcpu_top.v"))))
                if op == "l3_trace":
                    if payload.get("source"):
                        return (200, bridge.l3.trace_hasm_program(str(payload["source"]), label=str(payload.get("label", "inline_hasm"))))
                    return (200, bridge.l3.trace_hasm_file(str(payload.get("program", "rtl/programs/test_bsm.hasm"))))
                if op == "l4_parity":
                    return (200, bridge.l4.get_parity_overview())
                if op == "l5_host":
                    return (200, bridge.l5.get_host_observation_summary(run_live_collect=bool(payload.get("run_live_collect", False))))
                if op == "l6_hardware":
                    return (200, bridge.l6.get_hardware_intelligence_summary())
                if op == "l6_rtl_sim":
                    return (200, bridge.l6.simulate_rtl_transition(program=str(payload.get("program", "test_bsm.hasm")), max_cycles=int(payload.get("max_cycles", 64))))
                if op == "l7_decide":
                    return (
                        200,
                        bridge.l7.evaluate_and_decide(
                            operation=str(payload.get("operation", "VERIFY_RUNTIME_PARITY")),
                            domain=str(payload.get("domain", "PARITY")),
                            program=payload.get("program"),
                            live_board=bool(payload.get("live_board", False)),
                        ),
                    )
                if op == "l7_portal_isolate":
                    return (
                        200,
                        bridge.l7.isolate_portal_fault(
                            has_usb_device=bool(payload.get("has_usb_device", False)),
                            jtag_detected=bool(payload.get("jtag_detected", False)),
                        ),
                    )
                if op == "l7_linux_isolate":
                    return (200, bridge.l7.isolate_linux_fault())
                if op == "l8_summary":
                    return (200, bridge.l8.get_summary())
                if op == "l8_scan":
                    res = bridge.l8.scan_all()
                    bridge.record_layer_action(
                        layer="L8",
                        operation="l8_scan",
                        target="repository",
                        verified=all(v["valid"] for v in res["verifications"]),
                        summary=f"Scanned {res['count']} anomalies",
                    )
                    return (200, res)
                if op == "l8_diagnose":
                    symptom = str(payload.get("symptom") or payload.get("query") or "OFF-PRINT-SILICON")
                    res = bridge.l8.diagnose(symptom)
                    bridge.record_layer_action(
                        layer="L8",
                        operation="l8_diagnose",
                        target=symptom,
                        verified=res["verification"]["valid"],
                        record_sha256=res["record"]["record_sha256"],
                        summary=res["record"]["diagnosis_id"],
                    )
                    return (200, res)
                if op == "l9_summary":
                    return (200, bridge.l9.get_summary())
                if op == "l9_reason":
                    q = str(payload.get("query") or "opcode ADD")
                    res = bridge.l9.reason(q)
                    bridge.record_layer_action(
                        layer="L9",
                        operation="l9_reason",
                        target=q,
                        verified=res["verification"]["valid"],
                        record_sha256=res["record"]["record_sha256"],
                        summary=f"{res['record']['reasoning_id']} -> {res['record']['conclusion']['verdict']}",
                    )
                    return (200, res)
                if op == "l10_summary":
                    return (200, bridge.l10.get_summary())
                if op == "l10_engineer_hasm":
                    letters = tuple(payload.get("letters") or ("ب", "س", "م"))
                    goal = str(payload.get("goal") or "Synthesize register-safe H-ISA program")
                    res = bridge.l10.engineer_hasm(letters=letters, goal=goal)
                    bridge.record_layer_action(
                        layer="L10",
                        operation="l10_engineer_hasm",
                        target=",".join(letters),
                        verified=res["verification"]["valid"],
                        record_sha256=res["record"]["record_sha256"],
                        summary=f"{res['record']['engineering_id']} -> {res['record']['status']}",
                    )
                    return (200, res)
                if op == "l10_engineer_python":
                    res = bridge.l10.engineer_python(
                        target_file=str(payload["target_file"]),
                        test_file=str(payload["test_file"]),
                        patch_code=str(payload["patch_code"]),
                        goal=str(payload.get("goal", "Repair sandbox Python module")),
                        explicit_owner_approval=bool(payload.get("explicit_owner_approval", False)),
                    )
                    bridge.record_layer_action(
                        layer="L10",
                        operation="l10_engineer_python",
                        target=str(payload["target_file"]),
                        verified=res["verification"]["valid"],
                        record_sha256=res["record"]["record_sha256"],
                        summary=f"{res['record']['engineering_id']} -> {res['record']['status']}",
                    )
                    return (200, res)
                if op == "l11_summary":
                    return (200, bridge.l11.get_summary(run_rtl=bool(payload.get("run_rtl", False))))
                if op == "l11_execute_chain":
                    src = str(payload.get("source") or "")
                    res = (
                        bridge.l11.execute_chain(
                            src,
                            is_hc_compat=bool(payload.get("is_hc_compat", False)),
                            expected_outputs=payload.get("expected_outputs"),
                            run_rtl=bool(payload.get("run_rtl", False)),
                        )
                        if src
                        else bridge.l11.execute_chain(
                            is_hc_compat=bool(payload.get("is_hc_compat", False)),
                            expected_outputs=payload.get("expected_outputs"),
                            run_rtl=bool(payload.get("run_rtl", False)),
                        )
                    )
                    bridge.record_layer_action(
                        layer="L11",
                        operation="l11_execute_chain",
                        target=res["record"]["computation_id"],
                        verified=res["verification"]["valid"],
                        record_sha256=res["record"]["record_sha256"],
                        summary=f"11 junctions passed={res['record']['all_junctions_passed']}",
                    )
                    return (200, res)
                if op == "trace_interlayer":
                    subj = str(payload.get("subject") or "PRINT")
                    return (200, bridge.trace_interlayer_relationships(subj))
                if op == "action_log":
                    return (200, bridge.get_action_log())
                return (400, {"error": f"Unknown layer query op: {op}"})

        if m == "DELETE":
            if path.startswith("/api/folders/") or path.startswith("/api/files/folders/"):
                raw_target = unquote(path.rsplit("/", 1)[-1])
                return self.disconnect_folder_complete(raw_target)
            if path in {"/api/folders", "/api/files/folders"}:
                target_id = str(payload.get("folder_id") or payload.get("path") or qs.get("folder_id", [""])[0])
                return self.disconnect_folder_complete(target_id)

        return (404, {"error": f"Unknown endpoint {m} {path}"})


def create_request_handler(app: NUILocalServiceApp) -> type[BaseHTTPRequestHandler]:
    class NUIRequestHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_json(self, data: Any, status: int = HTTPStatus.OK) -> None:
            body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw) if raw.strip() else {}

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            if path == "/api/events/stream":
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()

                q_evt: queue.Queue[dict[str, Any]] = queue.Queue()
                app.orchestrator.subscribe_events(q_evt.put)
                try:
                    init_msg = json.dumps({"event": "connected", "timestamp": time.time()})
                    self.wfile.write(f"data: {init_msg}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    while True:
                        try:
                            evt = q_evt.get(timeout=5.0)
                            line = f"data: {json.dumps(evt, default=str)}\n\n"
                            self.wfile.write(line.encode("utf-8"))
                            self.wfile.flush()
                        except queue.Empty:
                            self.wfile.write(b": heartbeat\n\n")
                            self.wfile.flush()
                except Exception:
                    pass
                finally:
                    app.orchestrator.unsubscribe_events(q_evt.put)
                return

            try:
                status_code, payload = app.dispatch_request("GET", self.path)
                self._send_json(payload, status_code)
            except Exception as exc:
                self._send_json(
                    {"error": f"{type(exc).__name__}: {exc}"},
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            try:
                body = self._read_json_body()
                if path == "/api/chat/stream":
                    app._hot_reload_if_needed()
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "close")
                    self.end_headers()

                    msg_text = str(body.get("user_message") or body.get("message") or "")
                    for ev in app.orchestrator.stream_chat_turn(
                        session_id=body.get("session_id"),
                        user_message=msg_text,
                        request_id=body.get("request_id"),
                        message_id=body.get("message_id"),
                        provider_id=body.get("provider") or body.get("provider_id"),
                        model=body.get("model"),
                        attachments=body.get("attachments"),
                        tool_call=body.get("tool_call"),
                        ui_handler=str(body.get("ui_handler", "NUIDesktopStore.streamChatMessage")),
                        simulate_stop=bool(body.get("simulate_stop", False)),
                    ):
                        line = f"data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
                        self.wfile.write(line.encode("utf-8"))
                        self.wfile.flush()
                    return

                status_code, payload = app.dispatch_request("POST", self.path, body)
                self._send_json(payload, status_code)
            except Exception as exc:
                self._send_json(
                    {"error": f"{type(exc).__name__}: {exc}"},
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )

        def do_DELETE(self) -> None:
            try:
                body = self._read_json_body()
                status_code, payload = app.dispatch_request("DELETE", self.path, body)
                self._send_json(payload, status_code)
            except Exception as exc:
                self._send_json(
                    {"error": f"{type(exc).__name__}: {exc}"},
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )

    return NUIRequestHandler


def probe_existing_nui_service(host: str, port: int) -> dict[str, Any] | None:
    conn = None
    try:
        conn = http.client.HTTPConnection(host, port, timeout=0.6)
        conn.request("GET", "/api/health")
        resp = conn.getresponse()
        if resp.status == 200:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("service") == "CosmicTera NUI Local Service":
                return data
    except Exception:
        pass
    finally:
        if conn is not None:
            conn.close()
    return None


def find_available_port(host: str, preferred_port: int = 8848) -> int:
    for candidate in range(preferred_port, preferred_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, candidate))
                return candidate
            except OSError:
                continue
    return preferred_port


def write_active_service_info(host: str, port: int, pid: int) -> None:
    ACTIVE_SERVICE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_SERVICE_FILE.write_text(
        json.dumps(
            {
                "host": host,
                "port": port,
                "pid": pid,
                "version": SERVICE_VERSION,
                "service": "CosmicTera NUI Local Service",
                "status": "LOCAL SERVICE READY",
                "updated_at": time.time(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def run_server(host: str = "127.0.0.1", port: int = 8848, db_path: str | None = None) -> None:
    existing = probe_existing_nui_service(host, port)
    if existing is not None:
        if existing.get("version") == SERVICE_VERSION:
            write_active_service_info(host, port, int(existing.get("pid") or os.getpid()))
            print(
                f"[CosmicTera NUI Local Service] Reusing healthy v{SERVICE_VERSION} instance on {host}:{port} (PID {existing.get('pid')})"
            )
            return
        old_pid = int(existing.get("pid") or 0)
        if old_pid <= 0 and ACTIVE_SERVICE_FILE.exists():
            try:
                active_info = json.loads(ACTIVE_SERVICE_FILE.read_text(encoding="utf-8"))
                old_pid = int(active_info.get("pid") or 0)
            except Exception:
                old_pid = 0
        if old_pid > 0 and old_pid != os.getpid():
            try:
                os.kill(old_pid, signal.SIGTERM)
                for _ in range(15):
                    time.sleep(0.1)
                    if probe_existing_nui_service(host, port) is None:
                        break
                if probe_existing_nui_service(host, port) is not None:
                    os.kill(old_pid, signal.SIGKILL)
                    time.sleep(0.2)
            except Exception:
                pass

    actual_port = find_available_port(host, port)
    app = NUILocalServiceApp(db_path=db_path)
    app.storage.set_setting("service_port", actual_port)
    handler_cls = create_request_handler(app)
    httpd = ThreadingHTTPServer((host, actual_port), handler_cls)
    write_active_service_info(host, actual_port, os.getpid())
    print(f"[CosmicTera NUI Local Service v{SERVICE_VERSION}] Listening on {host}:{actual_port} (PID {os.getpid()})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CosmicTera NUI Desktop Local Service")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8848, help="Bind port (default: 8848)")
    parser.add_argument("--db", default=None, help="Path to SQLite database")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, db_path=args.db)
