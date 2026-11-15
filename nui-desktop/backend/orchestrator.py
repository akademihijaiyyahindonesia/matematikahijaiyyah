"""NUI Task, Multi-Model Router & Streaming Communication Orchestrator for CosmicTera NUI Desktop.

Supports:
- Incremental SSE Streaming (`stream_chat_turn` for `POST /api/chat/stream`) emitting:
  - `provider_init` / `request_accepted` (`REQUEST_RECEIVED`)
  - `stage_update` (`UNDERSTANDING`, `ANALYZING`, `PLANNING`, `TOOL_EXECUTION`, `VALIDATING`, `GENERATING_RESPONSE`)
  - `tool_call` & `tool_result` (ONLY when tools or computations actually run)
  - `partial_response` (incremental text delta + accumulated text)
  - `final_response` (`COMPLETE`)
  - `generation_cancelled` (`STOPPED`)
  - `generation_error` (`ERROR` / `PROVIDER_UNAVAILABLE` / `NUI_LANGUAGE_ENGINE_UNAVAILABLE`)
- Multi-Model Intelligence Routing (`NUIMultiModelRouter`):
  - `NUI_DETERMINISTIC_ENGINE` (`src/hijaiyyah/*` + `HISAMachine`)
  - `QWEN38_CODING_SPECIALIST` (`qwen3.8:27b` / `qwen3.6:27b` via Ollama with NUI Persona)
  - `NUI_L0_HMCL_EMBEDDING_ENGINE` (`src/hijaiyyah/hmcl/*` + `NUIContextualRetriever`)
  - `OLLAMA_WITH_NUI_PERSONA` (Local Ollama model governed by official `HybitAIProgram.system`)
"""
from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field
from typing import Any

from .permissions import PermissionEngine
from .providers import (
    NUIIntelligenceProvider,
    NativeNUIProvider,
    OllamaProvider,
    OptionalExternalProvider,
)
from .self_learning import (
    NUIAutonomousSelfLearningEngine,
    NUIModelAssetLibrary,
    NUIMultiModelRouter,
)
from .storage import NUIStorage
from .tools import NUIToolRegistry


@dataclass
class NUIChatRequest:
    request_id: str
    session_id: str
    message_id: str
    user_message: str
    conversation_context: list[dict[str, Any]] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    provider: str = "native_nui"
    model: str | None = None
    ui_handler: str = "NUIDesktopStore.sendChatMessage"
    timestamp: float = field(default_factory=time.time)


@dataclass
class NUIChatResponse:
    request_id: str
    response_id: str
    session_id: str
    message_id: str
    response_text: str
    provider: str
    model: str | None
    execution_status: str
    ui_state: str
    response_time_ms: float
    source_attribution: str
    thinking_stages: list[str] = field(default_factory=list)
    tool_activities: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    timestamp: float = field(default_factory=time.time)


class NUITaskOrchestrator:
    """Coordinates live streaming chat, multi-model routing, tool executions, and SSE events."""

    def __init__(
        self,
        storage: NUIStorage,
        permissions: PermissionEngine,
        tools: NUIToolRegistry,
        native_provider: NativeNUIProvider,
        ollama_provider: OllamaProvider,
        external_provider: OptionalExternalProvider,
        model_library: NUIModelAssetLibrary | None = None,
        multi_model_router: NUIMultiModelRouter | None = None,
        self_learning: NUIAutonomousSelfLearningEngine | None = None,
        operational_intelligence: Any | None = None,
        remote_dev_engine: Any | None = None,
        universal_file_engine: Any | None = None,
        internet_engine: Any | None = None,
    ) -> None:
        self.storage = storage
        self.permissions = permissions
        self.tools = tools
        self.native_provider = native_provider
        self.ollama_provider = ollama_provider
        if getattr(self.native_provider, "ollama_provider", None) is None:
            self.native_provider.ollama_provider = self.ollama_provider
        self.external_provider = external_provider
        self.model_library = model_library or NUIModelAssetLibrary()
        self.multi_model_router = multi_model_router or NUIMultiModelRouter(self.model_library)
        self.self_learning = self_learning
        self.operational_intelligence = operational_intelligence
        self.remote_dev_engine = remote_dev_engine
        self.universal_file_engine = universal_file_engine
        self.internet_engine = internet_engine
        self._cancelled_tasks: set[str] = set()
        self._cancelled_requests: set[str] = set()
        self._active_requests_by_session: dict[str, str] = {}
        self._subscribers: list[Callable[[dict[str, Any]], None]] = []
        self._lock = threading.RLock()

    def subscribe_events(self, callback: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            self._subscribers.append(callback)

    def unsubscribe_events(self, callback: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def emit_event(self, event_type: str, payload: dict[str, Any]) -> None:
        evt = {
            "event": event_type,
            "timestamp": time.time(),
            "payload": payload,
        }
        with self._lock:
            subs = list(self._subscribers)
        for cb in subs:
            try:
                cb(evt)
            except Exception:
                pass

    def get_provider(self, provider_id: str | None = None) -> NUIIntelligenceProvider:
        pid = provider_id or self.storage.get_setting("active_provider", "native_nui")
        if pid in {"local_ollama", "ollama"}:
            return self.ollama_provider
        if pid == "external_api":
            return self.external_provider
        if pid in {"native_nui", "auto", "multi_model"}:
            return self.native_provider
        raise KeyError(f"PROVIDER_UNAVAILABLE: Provider '{pid}' tidak terdaftar")

    def stop_chat_generation(
        self, request_id: str | None = None, session_id: str | None = None
    ) -> dict[str, Any]:
        """Cancel an in-flight chat generation by request_id or session_id."""
        with self._lock:
            target_req = request_id
            if not target_req and session_id:
                target_req = self._active_requests_by_session.get(session_id)
            if target_req:
                self._cancelled_requests.add(target_req)
        self.emit_event(
            "chat.stopped",
            {"request_id": target_req, "session_id": session_id, "ui_state": "UI READY"},
        )
        return {
            "stopped": True,
            "request_id": target_req,
            "session_id": session_id,
            "execution_status": "STOPPED",
            "ui_state": "UI READY",
        }

    def stream_chat_turn(
        self,
        *,
        session_id: str | None = None,
        user_message: str,
        request_id: str | None = None,
        message_id: str | None = None,
        provider_id: str | None = None,
        model: str | None = None,
        attachments: list[str] | None = None,
        tool_call: dict[str, Any] | None = None,
        ui_handler: str = "NUIDesktopStore.streamChatMessage",
        simulate_stop: bool = False,
    ) -> Iterator[dict[str, Any]]:
        """Stream live thinking stages, multi-model routing, tool calls, partial response deltas, and final completion."""
        t0 = time.perf_counter()
        req_id = request_id or f"req-{uuid.uuid4().hex[:12]}"
        user_msg_id = message_id or f"msg-{uuid.uuid4().hex[:12]}"
        resp_id = f"resp-{uuid.uuid4().hex[:12]}"

        sess = self.storage.get_session(session_id) if session_id else None
        if not sess:
            sess = self.storage.create_session(
                title=(user_message.strip()[:48] or "Sesi CosmicTera NUI"),
                session_id=session_id if (session_id and session_id.startswith("sess-")) else None,
            )
        eff_session_id = sess["session_id"]
        requested_prov = (
            provider_id
            or sess.get("provider")
            or self.storage.get_setting("active_provider", "native_nui")
        )
        routing_decision = self.multi_model_router.route_task(
            user_message,
            requested_provider=requested_prov,
            requested_model=model,
        )
        if requested_prov in {"auto", "multi_model"}:
            eff_provider_id = routing_decision["selected_provider"]
            eff_model = model or routing_decision.get("selected_model")
        else:
            eff_provider_id = "local_ollama" if requested_prov == "ollama" else requested_prov
            if eff_provider_id == "local_ollama":
                cand_m = model or routing_decision.get("selected_model")
                if cand_m and cand_m.startswith("cosmictera-nui-native"):
                    cand_m = routing_decision.get("language_explainer")
                    if cand_m and cand_m.startswith("cosmictera-nui-native"):
                        cand_m = None
                eff_model = cand_m
            else:
                eff_model = model

        prior_messages = self.storage.list_messages(eff_session_id)
        chat_req = NUIChatRequest(
            request_id=req_id,
            session_id=eff_session_id,
            message_id=user_msg_id,
            user_message=user_message,
            conversation_context=prior_messages,
            attachments=list(attachments or []),
            provider=eff_provider_id,
            model=eff_model,
            ui_handler=ui_handler,
            timestamp=time.time(),
        )

        with self._lock:
            self._active_requests_by_session[eff_session_id] = req_id
            if simulate_stop:
                self._cancelled_requests.add(req_id)

        user_msg_record = self.storage.add_message(
            session_id=eff_session_id,
            role="user",
            content=user_message,
            metadata={
                "attachments": chat_req.attachments,
                "request_id": req_id,
                "routing_decision": routing_decision,
            },
            message_id=user_msg_id,
            request_id=req_id,
        )

        observed_stages: list[str] = ["REQUEST_RECEIVED"]
        observed_tools: list[str] = []
        first_token_ms: float | None = None
        tool_start_ms: float | None = None
        tool_end_ms: float | None = None

        ev_init = {
            "event": "request_accepted",
            "request_id": req_id,
            "session_id": eff_session_id,
            "message_id": user_msg_id,
            "stage": "REQUEST_RECEIVED",
            "thinking_status": "NUI is thinking...",
            "ui_state": "GENERATING",
            "routing_decision": routing_decision,
            "user_message": user_msg_record,
            "timestamp": time.time(),
        }
        self.emit_event("chat.stream", ev_init)
        yield ev_init

        try:
            if req_id in self._cancelled_requests:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                stop_text = "Pembuatan respons dihentikan oleh pengguna (`STOPPED`)."
                if "CANCELLED" not in observed_stages:
                    observed_stages.append("CANCELLED")
                asst_msg = self.storage.add_message(
                    session_id=eff_session_id,
                    role="assistant",
                    content=stop_text,
                    metadata={
                        "request_id": req_id,
                        "execution_status": "STOPPED",
                        "thinking_stages": observed_stages,
                    },
                    message_id=resp_id,
                    request_id=req_id,
                )
                chat_resp = NUIChatResponse(
                    request_id=req_id,
                    response_id=resp_id,
                    session_id=eff_session_id,
                    message_id=asst_msg["message_id"],
                    response_text=stop_text,
                    provider=eff_provider_id,
                    model=eff_model,
                    execution_status="STOPPED",
                    ui_state="UI READY",
                    response_time_ms=round(elapsed_ms, 3),
                    source_attribution="NUI_ORCHESTRATOR (Stopped by User)",
                    thinking_stages=observed_stages,
                    tool_activities=observed_tools,
                    data={"stopped": True, "routing_decision": routing_decision},
                    error="GENERATION_STOPPED",
                )
                self._log_comm(chat_req, chat_resp, http_status=200)
                ev_cancel = {
                    "event": "generation_cancelled",
                    "request_id": req_id,
                    "session_id": eff_session_id,
                    "stage": "CANCELLED",
                    "thinking_status": "GENERATION CANCELLED",
                    "ui_state": "UI READY",
                    "turn_output": self._format_turn_output(
                        chat_req, chat_resp, user_msg_record, asst_msg
                    ),
                }
                self.emit_event("chat.stream", ev_cancel)
                yield ev_cancel
                return

            try:
                provider = self.get_provider(eff_provider_id)
            except KeyError as exc:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                err_txt = str(exc)
                reply_txt = f"**Provider Tidak Tersedia (`PROVIDER_UNAVAILABLE`)**: {err_txt}"
                asst_msg = self.storage.add_message(
                    session_id=eff_session_id,
                    role="assistant",
                    content=reply_txt,
                    metadata={"request_id": req_id, "error": err_txt},
                    message_id=resp_id,
                    request_id=req_id,
                )
                chat_resp = NUIChatResponse(
                    request_id=req_id,
                    response_id=resp_id,
                    session_id=eff_session_id,
                    message_id=asst_msg["message_id"],
                    response_text=reply_txt,
                    provider=eff_provider_id,
                    model=eff_model,
                    execution_status="PROVIDER_UNAVAILABLE",
                    ui_state="PROVIDER UNAVAILABLE",
                    response_time_ms=round(elapsed_ms, 3),
                    source_attribution="NUI_PROVIDER_ROUTER",
                    thinking_stages=observed_stages,
                    error=err_txt,
                )
                self._log_comm(chat_req, chat_resp, http_status=200)
                ev_err = {
                    "event": "generation_error",
                    "request_id": req_id,
                    "session_id": eff_session_id,
                    "stage": "ERROR",
                    "thinking_status": "PROVIDER UNAVAILABLE",
                    "ui_state": "PROVIDER UNAVAILABLE",
                    "error": err_txt,
                    "turn_output": self._format_turn_output(
                        chat_req, chat_resp, user_msg_record, asst_msg
                    ),
                }
                self.emit_event("chat.stream", ev_err)
                yield ev_err
                return

            full_context_messages = prior_messages + [user_msg_record]
            accumulated_text = ""
            final_provider_resp: dict[str, Any] = {}

            phase9_record: dict[str, Any] | None = None
            if self.operational_intelligence is not None:
                try:
                    phase9_record = self.operational_intelligence.execute_operational_cycle(
                        prompt=user_message,
                        session_id=eff_session_id,
                    )
                    if "PLAN" not in observed_stages:
                        observed_stages.append("PLAN")
                    ev_p9 = {
                        "event": "phase9_operational_plan",
                        "request_id": req_id,
                        "session_id": eff_session_id,
                        "stage": "PLAN",
                        "thinking_status": f"Phase 9 Operational Cycle ({phase9_record.get('operational_intent')})...",
                        "operational_intent": phase9_record.get("operational_intent"),
                        "follow_up_type": phase9_record.get("follow_up_type"),
                        "plan": phase9_record.get("plan"),
                        "permission_decision": phase9_record.get("permission_decision"),
                        "cycle_stages_completed": phase9_record.get("cycle_stages_completed"),
                    }
                    self.emit_event("chat.stream", ev_p9)
                    yield ev_p9
                except Exception:
                    phase9_record = None

            if phase9_record and phase9_record.get("direct_response_override"):
                accumulated_text = str(phase9_record["direct_response_override"])
                final_provider_resp = {
                    "provider": eff_provider_id,
                    "model": eff_model or "NUI-L7-Gate",
                    "ui_state": "RESPONSE COMPLETE",
                    "reply": accumulated_text,
                    "data": {"phase9_operational": phase9_record},
                    "source_attribution": "PHASE9_IMMUTABLE_CORE_PROTECTION (L7 Gate)",
                }
                ev_part = {
                    "event": "partial_response",
                    "request_id": req_id,
                    "session_id": eff_session_id,
                    "stage": "GENERATING_RESPONSE",
                    "thinking_status": "Applying Phase 9 Immutable Core Protection...",
                    "delta": accumulated_text,
                    "accumulated_text": accumulated_text,
                }
                self.emit_event("chat.stream", ev_part)
                yield ev_part
                provider_iter = []
            else:
                provider_iter = provider.stream_respond(
                    user_message,
                    context={
                        "request_id": req_id,
                        "session_id": eff_session_id,
                        "conversation_context": full_context_messages,
                        "attachments": chat_req.attachments,
                        "authorized_folders": self.storage.list_authorized_folders(),
                        "operating_mode": self.storage.get_setting("operating_mode", "HYBRID"),
                        "model": eff_model,
                        "routing_decision": routing_decision,
                        "phase9_operational": phase9_record,
                        "remote_dev_engine": self.remote_dev_engine,
                        "universal_file_engine": self.universal_file_engine,
                        "internet_engine": self.internet_engine,
                    },
                    cancel_check=lambda: req_id in self._cancelled_requests,
                    tool_executor=lambda t_name, t_params: self.tools.execute_tool(
                        t_name,
                        t_params,
                        user_request=user_message,
                        session_id=eff_session_id,
                    ),
                )

            for item in provider_iter:
                ev_kind = item.get("event", "stage_update")
                stg = item.get("stage")
                if stg and stg not in observed_stages:
                    if not (stg == "COMPLETE" and ("CANCELLED" in observed_stages or req_id in self._cancelled_requests)):
                        observed_stages.append(stg)
                if ev_kind == "tool_call" and tool_start_ms is None:
                    tool_start_ms = round((time.perf_counter() - t0) * 1000.0, 3)
                if ev_kind in ("tool_result", "partial_response", "final_response") and tool_start_ms is not None and tool_end_ms is None:
                    tool_end_ms = round((time.perf_counter() - t0) * 1000.0, 3)
                if item.get("activity"):
                    observed_tools.append(str(item["activity"]))

                if ev_kind == "partial_response":
                    if first_token_ms is None:
                        first_token_ms = round((time.perf_counter() - t0) * 1000.0, 3)
                    accumulated_text = str(item.get("accumulated_text", accumulated_text))

                if ev_kind == "generation_cancelled":
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    observed_stages = [s for s in observed_stages if s != "COMPLETE"]
                    if "CANCELLED" not in observed_stages:
                        observed_stages.append("CANCELLED")
                    partial = str(item.get("accumulated_text") or accumulated_text)
                    stop_body = (
                        f"{partial}\n\n*[Generasi dihentikan oleh pengguna (`STOPPED`)]*"
                        if partial
                        else "Pembuatan respons dihentikan oleh pengguna (`STOPPED`)."
                    )
                    asst_msg = self.storage.add_message(
                        session_id=eff_session_id,
                        role="assistant",
                        content=stop_body,
                        metadata={
                            "request_id": req_id,
                            "execution_status": "STOPPED",
                            "thinking_stages": observed_stages,
                            "tool_activities": observed_tools,
                        },
                        message_id=resp_id,
                        request_id=req_id,
                    )
                    chat_resp = NUIChatResponse(
                        request_id=req_id,
                        response_id=resp_id,
                        session_id=eff_session_id,
                        message_id=asst_msg["message_id"],
                        response_text=stop_body,
                        provider=eff_provider_id,
                        model=eff_model,
                        execution_status="STOPPED",
                        ui_state="UI READY",
                        response_time_ms=round(elapsed_ms, 3),
                        source_attribution="NUI_ORCHESTRATOR (Stopped during stream)",
                        thinking_stages=observed_stages,
                        tool_activities=observed_tools,
                        data={"stopped": True, "partial_text": partial},
                        error="GENERATION_STOPPED",
                    )
                    self._log_comm(chat_req, chat_resp, http_status=200)
                    ev_out = {
                        **item,
                        "request_id": req_id,
                        "session_id": eff_session_id,
                        "thinking_stages": observed_stages,
                        "tool_activities": observed_tools,
                        "turn_output": self._format_turn_output(
                            chat_req, chat_resp, user_msg_record, asst_msg
                        ),
                    }
                    self.emit_event("chat.stream", ev_out)
                    yield ev_out
                    return

                if ev_kind == "generation_error":
                    final_provider_resp = item.get("provider_response") or {}
                    accumulated_text = str(
                        item.get("response_text")
                        or final_provider_resp.get("reply")
                        or "Terjadi kesalahan saat memproses permintaan."
                    )
                    break

                if ev_kind == "final_response":
                    final_provider_resp = item.get("provider_response") or {}
                    accumulated_text = str(
                        item.get("response_text")
                        or final_provider_resp.get("reply")
                        or accumulated_text
                    )
                    break

                stream_pkt = {
                    **item,
                    "request_id": req_id,
                    "session_id": eff_session_id,
                    "thinking_stages": list(observed_stages),
                    "tool_activities": list(observed_tools),
                }
                self.emit_event("chat.stream", stream_pkt)
                yield stream_pkt

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            generation_end_ms = round(elapsed_ms, 3)
            if first_token_ms is None and accumulated_text:
                first_token_ms = generation_end_ms
            prov_err = final_provider_resp.get("error")
            if req_id in self._cancelled_requests or "CANCELLED" in observed_stages:
                observed_stages = [s for s in observed_stages if s != "COMPLETE"]
                if "CANCELLED" not in observed_stages:
                    observed_stages.append("CANCELLED")
                exec_status = "STOPPED"
                ui_st = "UI READY"
                prov_err = "GENERATION_STOPPED"
            elif prov_err in {
                "PROVIDER_UNAVAILABLE",
                "MODEL_NOT_FOUND",
                "NUI_LANGUAGE_ENGINE_UNAVAILABLE",
            }:
                exec_status = "PROVIDER_UNAVAILABLE"
                ui_st = "PROVIDER UNAVAILABLE"
            elif prov_err and "WAITING_FOR_APPROVAL" in str(prov_err):
                exec_status = "WAITING_FOR_APPROVAL"
                ui_st = "WAITING_FOR_APPROVAL"
            elif prov_err:
                exec_status = "ERROR"
                ui_st = "ERROR"
            else:
                observed_stages = [s for s in observed_stages if s != "CANCELLED"]
                exec_status = "RESPONSE_COMPLETE"
                ui_st = "RESPONSE COMPLETE"
                if "COMPLETE" not in observed_stages:
                    observed_stages.append("COMPLETE")

            reply_text = accumulated_text.strip()
            if not reply_text:
                reply_text = "Provider mengembalikan respons kosong (`EMPTY_RESPONSE`)."
                exec_status = "ERROR"
                ui_st = "ERROR"
                prov_err = "EMPTY_RESPONSE"

            resp_data = dict(final_provider_resp.get("data", {}))
            resp_data["routing_decision"] = routing_decision
            resp_data["latency_breakdown"] = {
                "request_received_ms": 0.0,
                "first_token_ms": first_token_ms,
                "tool_start_ms": tool_start_ms,
                "tool_end_ms": tool_end_ms,
                "generation_end_ms": generation_end_ms,
                "total_duration_ms": generation_end_ms,
            }
            if phase9_record is not None:
                resp_data["phase9_operational"] = {
                    k: v for k, v in phase9_record.items() if k != "verified_context_block"
                }

            asst_msg = self.storage.add_message(
                session_id=eff_session_id,
                role="assistant",
                content=reply_text,
                metadata={
                    "request_id": req_id,
                    "response_id": resp_id,
                    "provider": final_provider_resp.get("provider", eff_provider_id),
                    "model": final_provider_resp.get("model", eff_model),
                    "execution_status": exec_status,
                    "ui_state": ui_st,
                    "response_time_ms": round(elapsed_ms, 3),
                    "thinking_stages": observed_stages,
                    "tool_activities": observed_tools,
                    "source_attribution": final_provider_resp.get("source_attribution", ""),
                    "routing_decision": routing_decision,
                    "data": resp_data,
                    "error": prov_err,
                },
                message_id=resp_id,
                request_id=req_id,
            )

            chat_resp = NUIChatResponse(
                request_id=req_id,
                response_id=resp_id,
                session_id=eff_session_id,
                message_id=asst_msg["message_id"],
                response_text=reply_text,
                provider=final_provider_resp.get("provider", eff_provider_id),
                model=final_provider_resp.get("model", eff_model),
                execution_status=exec_status,
                ui_state=ui_st,
                response_time_ms=round(elapsed_ms, 3),
                source_attribution=str(
                    final_provider_resp.get("source_attribution", "LOCAL_REPOSITORY")
                ),
                thinking_stages=observed_stages,
                tool_activities=observed_tools,
                data=resp_data,
                error=prov_err,
            )
            self._log_comm(chat_req, chat_resp, http_status=200)
            if self.self_learning is not None and not prov_err:
                try:
                    self.self_learning.record_turn_observation(
                        session_id=eff_session_id,
                        user_message=user_message,
                        response_text=reply_text,
                        provider=chat_resp.provider,
                        model=chat_resp.model,
                        source_attribution=chat_resp.source_attribution,
                        retrieved_sources=resp_data.get("retrieved_sources"),
                        deterministic_verified=bool(
                            resp_data.get("calc_result")
                            or resp_data.get("hisa_result")
                            or resp_data.get("deterministic_calc")
                            or resp_data.get("deterministic_hisa")
                        ),
                    )
                except Exception:
                    pass
            turn_out = self._format_turn_output(
                chat_req,
                chat_resp,
                user_msg_record,
                asst_msg,
                raw_provider_resp=final_provider_resp,
            )
            turn_out["routing_decision"] = routing_decision
            final_ev = {
                "event": "final_response" if not prov_err else "generation_error",
                "request_id": req_id,
                "session_id": eff_session_id,
                "stage": "COMPLETE" if not prov_err else "ERROR",
                "thinking_status": "COMPLETE" if not prov_err else ui_st,
                "ui_state": ui_st,
                "response_text": reply_text,
                "thinking_stages": observed_stages,
                "tool_activities": observed_tools,
                "routing_decision": routing_decision,
                "turn_output": turn_out,
            }
            self.emit_event("chat.stream", final_ev)
            yield final_ev
        finally:
            with self._lock:
                if self._active_requests_by_session.get(eff_session_id) == req_id:
                    self._active_requests_by_session.pop(eff_session_id, None)

    def handle_chat_turn(
        self,
        *,
        session_id: str | None = None,
        user_message: str,
        request_id: str | None = None,
        message_id: str | None = None,
        provider_id: str | None = None,
        model: str | None = None,
        attachments: list[str] | None = None,
        tool_call: dict[str, Any] | None = None,
        ui_handler: str = "NUIDesktopStore.sendChatMessage",
        simulate_stop: bool = False,
    ) -> dict[str, Any]:
        """Execute a chat turn (using explicit tool orchestration if tool_call is given, or consuming stream_chat_turn)."""
        if tool_call and "name" in tool_call:
            t0 = time.perf_counter()
            req_id = request_id or f"req-{uuid.uuid4().hex[:12]}"
            user_msg_id = message_id or f"msg-{uuid.uuid4().hex[:12]}"
            resp_id = f"resp-{uuid.uuid4().hex[:12]}"
            sess = self.storage.get_session(session_id) if session_id else None
            if not sess:
                sess = self.storage.create_session(
                    title=(user_message.strip()[:48] or "Sesi CosmicTera NUI"),
                    session_id=session_id if (session_id and session_id.startswith("sess-")) else None,
                )
            eff_session_id = sess["session_id"]
            eff_provider_id = provider_id or sess.get("provider") or "native_nui"
            prior_messages = self.storage.list_messages(eff_session_id)
            chat_req = NUIChatRequest(
                request_id=req_id,
                session_id=eff_session_id,
                message_id=user_msg_id,
                user_message=user_message,
                conversation_context=prior_messages,
                attachments=list(attachments or []),
                provider=eff_provider_id,
                model=model,
                ui_handler=ui_handler,
                timestamp=time.time(),
            )
            user_msg_record = self.storage.add_message(
                session_id=eff_session_id,
                role="user",
                content=user_message,
                metadata={"attachments": chat_req.attachments, "request_id": req_id},
                message_id=user_msg_id,
                request_id=req_id,
            )
            task = self.create_and_run_task(
                title=f"Tool: {tool_call['name']}",
                steps=[
                    {
                        "step_id": 1,
                        "title": f"Execute {tool_call['name']}",
                        "tool": tool_call["name"],
                        "params": tool_call.get("params", {}),
                        "explicit_final_deploy_confirmed": bool(
                            tool_call.get("explicit_final_deploy_confirmed", False)
                        ),
                        "untrusted_context": bool(
                            tool_call.get("untrusted_context", False)
                        ),
                    }
                ],
                session_id=eff_session_id,
                user_request=user_message,
            )
            status = task["status"]
            if status == "WAITING_FOR_APPROVAL":
                pending_req = task["result"].get("pending_request_id")
                reply_text = (
                    f"**Menunggu Otorisasi Pengguna (`WAITING_FOR_APPROVAL`)**\n\n"
                    f"- **Alat**: `{tool_call['name']}`\n"
                    f"- **Alasan**: {task['result'].get('reason', 'Memerlukan izin akses')}\n"
                    f"- **Request ID**: `{pending_req}`"
                )
                exec_status = "WAITING_FOR_APPROVAL"
                ui_st = "WAITING_FOR_APPROVAL"
                err_val = None
            elif status == "COMPLETED":
                reply_text = (
                    f"**Eksekusi Alat Selesai (`{tool_call['name']}`)**\n\n"
                    f"- **Status**: `COMPLETED`\n"
                    f"- **Ringkasan**: `{task['result'].get('summary', 'OK')}`"
                )
                exec_status = "RESPONSE_COMPLETE"
                ui_st = "RESPONSE COMPLETE"
                err_val = None
            else:
                err_val = str(task.get("error") or task["result"].get("reason", "Denied"))
                reply_text = (
                    f"**Eksekusi Alat Dihentikan (`{tool_call['name']}`)**\n\n"
                    f"- **Status**: `{status}`\n"
                    f"- **Keterangan**: `{err_val}`"
                )
                exec_status = "ERROR"
                ui_st = "ERROR"

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            asst_msg = self.storage.add_message(
                session_id=eff_session_id,
                role="assistant",
                content=reply_text,
                metadata={
                    "request_id": req_id,
                    "task_id": task["task_id"],
                    "task_status": status,
                },
                message_id=resp_id,
                request_id=req_id,
            )
            chat_resp = NUIChatResponse(
                request_id=req_id,
                response_id=resp_id,
                session_id=eff_session_id,
                message_id=asst_msg["message_id"],
                response_text=reply_text,
                provider=eff_provider_id,
                model="nui-tool-orchestrator",
                execution_status=exec_status,
                ui_state=ui_st,
                response_time_ms=round(elapsed_ms, 3),
                source_attribution=f"NUI_TOOL_ORCHESTRATOR ({tool_call['name']})",
                thinking_stages=["REQUEST_RECEIVED", "UNDERSTANDING", "PLANNING", "TOOL_EXECUTION", "COMPLETE"],
                tool_activities=[f"Executed {tool_call['name']} -> {status}"],
                data={"task": task},
                error=err_val,
            )
            self._log_comm(chat_req, chat_resp, http_status=200)
            return {
                **self._format_turn_output(
                    chat_req, chat_resp, user_msg_record, asst_msg
                ),
                "task": task,
            }

        stream_events: list[dict[str, Any]] = []
        final_turn_output: dict[str, Any] = {}
        for ev in self.stream_chat_turn(
            session_id=session_id,
            user_message=user_message,
            request_id=request_id,
            message_id=message_id,
            provider_id=provider_id,
            model=model,
            attachments=attachments,
            ui_handler=ui_handler,
            simulate_stop=simulate_stop,
        ):
            stream_events.append(ev)
            if "turn_output" in ev:
                final_turn_output = ev["turn_output"]

        final_turn_output["stream_events"] = stream_events
        return final_turn_output

    def _log_comm(
        self, req: NUIChatRequest, resp: NUIChatResponse, http_status: int = 200
    ) -> None:
        self.storage.record_communication_log(
            request_id=req.request_id,
            response_id=resp.response_id,
            session_id=req.session_id,
            user_message_id=req.message_id,
            assistant_message_id=resp.message_id,
            ui_handler=req.ui_handler,
            endpoint="/api/chat/stream",
            http_status=http_status,
            provider=resp.provider,
            model=resp.model,
            execution_status=resp.execution_status,
            ui_state=resp.ui_state,
            response_time_ms=resp.response_time_ms,
            user_message=req.user_message,
            response_preview=resp.response_text,
            error=resp.error,
        )

    @staticmethod
    def _format_turn_output(
        req: NUIChatRequest,
        resp: NUIChatResponse,
        user_msg: dict[str, Any],
        asst_msg: dict[str, Any],
        raw_provider_resp: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": resp.error is None,
            "request_id": resp.request_id,
            "response_id": resp.response_id,
            "session_id": resp.session_id,
            "message_id": resp.message_id,
            "response": resp.response_text,
            "response_text": resp.response_text,
            "provider": resp.provider,
            "model": resp.model,
            "execution_status": resp.execution_status,
            "ui_state": resp.ui_state,
            "response_time_ms": resp.response_time_ms,
            "source_attribution": resp.source_attribution,
            "thinking_stages": resp.thinking_stages,
            "tool_activities": resp.tool_activities,
            "data": resp.data,
            "phase9_operational": (resp.data or {}).get("phase9_operational"),
            "error": resp.error,
            "timestamp": resp.timestamp,
            "chat_request": asdict(req),
            "chat_response": asdict(resp),
            "user_message": user_msg,
            "assistant_message": asst_msg,
            "provider_response": raw_provider_resp
            or {
                "provider": resp.provider,
                "model": resp.model,
                "reply": resp.response_text,
                "data": resp.data,
                "error": resp.error,
                "source_attribution": resp.source_attribution,
            },
        }

    # ── Multi-Step Task Orchestration ────────────────────────────────────────

    def create_and_run_task(
        self,
        *,
        title: str,
        steps: list[dict[str, Any]],
        session_id: str | None = None,
        user_request: str = "",
    ) -> dict[str, Any]:
        normalized_steps = []
        for idx, s in enumerate(steps, start=1):
            normalized_steps.append(
                {
                    "step_id": s.get("step_id", idx),
                    "title": s.get("title", f"Step {idx}: {s.get('tool', 'action')}"),
                    "tool": s["tool"],
                    "params": s.get("params", {}),
                    "status": "QUEUED",
                    "explicit_final_deploy_confirmed": bool(
                        s.get("explicit_final_deploy_confirmed", False)
                    ),
                    "untrusted_context": bool(s.get("untrusted_context", False)),
                }
            )
        task = self.storage.create_task(
            title=title,
            steps=normalized_steps,
            session_id=session_id,
            status="QUEUED",
        )
        return self.run_or_resume_task(task["task_id"], user_request=user_request or title)

    def run_or_resume_task(
        self, task_id: str, user_request: str = ""
    ) -> dict[str, Any]:
        task = self.storage.get_task(task_id)
        if not task:
            raise KeyError(f"Task {task_id!r} not found")

        if task_id in self._cancelled_tasks or task["status"] == "CANCELLED":
            return self.storage.update_task(
                task_id, status="CANCELLED", error="Cancelled by user"
            )  # type: ignore[return-value]

        steps = list(task["steps"])
        self.storage.update_task(task_id, status="RUNNING", steps=steps)
        self.emit_event("task.updated", {"task_id": task_id, "status": "RUNNING"})

        last_summary = ""
        step_outputs: list[dict[str, Any]] = []

        for step in steps:
            if task_id in self._cancelled_tasks:
                return self.storage.update_task(
                    task_id,
                    status="CANCELLED",
                    steps=steps,
                    error="Cancelled by user via Stop button",
                )  # type: ignore[return-value]

            if step.get("status") == "COMPLETED":
                if "output" in step:
                    step_outputs.append(step["output"])
                continue

            step["status"] = "RUNNING"
            self.storage.update_task(task_id, status="RUNNING", steps=steps)

            out = self.tools.execute_tool(
                step["tool"],
                step.get("params", {}),
                user_request=user_request or task["title"],
                session_id=task["session_id"],
                task_id=task_id,
                explicit_final_deploy_confirmed=bool(
                    step.get("explicit_final_deploy_confirmed", False)
                ),
                untrusted_context=bool(step.get("untrusted_context", False)),
            )

            if out["status"] == "WAITING_FOR_APPROVAL":
                step["status"] = "WAITING_FOR_APPROVAL"
                step["request_id"] = out.get("request_id")
                updated = self.storage.update_task(
                    task_id,
                    status="WAITING_FOR_APPROVAL",
                    steps=steps,
                    result={
                        "pending_request_id": out.get("request_id"),
                        "reason": out.get("reason"),
                        "category": out.get("category"),
                        "target": out.get("target"),
                    },
                )
                self.emit_event("task.waiting_approval", updated or {})
                return updated  # type: ignore[return-value]

            if not out.get("ok", False):
                step["status"] = "FAILED"
                step["error"] = out.get("reason") or out.get("error") or "Execution failed"
                updated = self.storage.update_task(
                    task_id,
                    status="FAILED",
                    steps=steps,
                    result=out,
                    error=step["error"],
                )
                self.emit_event("chat.failed", updated or {})
                return updated  # type: ignore[return-value]

            step["status"] = "COMPLETED"
            step["output"] = out["result"]
            step_outputs.append(out["result"])
            last_summary = str(out["result"].get("summary", "Completed"))
            self.storage.update_task(task_id, status="RUNNING", steps=steps)

        final_task = self.storage.update_task(
            task_id,
            status="COMPLETED",
            steps=steps,
            result={"summary": last_summary, "step_outputs": step_outputs},
            error=None,
        )
        self.emit_event("task.completed", final_task or {})
        return final_task  # type: ignore[return-value]

    def stop_task(self, task_id: str) -> dict[str, Any]:
        self._cancelled_tasks.add(task_id)
        task = self.storage.get_task(task_id)
        if not task:
            raise KeyError(f"Task {task_id!r} not found")
        steps = list(task["steps"])
        for s in steps:
            if s.get("status") in {"QUEUED", "RUNNING", "WAITING_FOR_APPROVAL"}:
                s["status"] = "CANCELLED"
        updated = self.storage.update_task(
            task_id,
            status="CANCELLED",
            steps=steps,
            error="Task stopped by user",
        )
        self.emit_event("task.cancelled", updated or {})
        return updated  # type: ignore[return-value]

    def edit_and_resend_chat_turn(
        self,
        *,
        session_id: str,
        target_message_id: str | None = None,
        edited_user_message: str | None = None,
        updated_user_message: str | None = None,
        provider_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        attachments: list[str] | None = None,
    ) -> dict[str, Any]:
        """Edit an existing user message in `session_id` (pruning the stale response after it) and resend cleanly."""
        eff_msg = str(edited_user_message if edited_user_message is not None else (updated_user_message or ""))
        eff_prov = provider_id or provider
        pruned_info: dict[str, Any] = {"ok": False, "pruned_count": 0}
        if target_message_id:
            pruned_info = self.storage.prune_for_edit_and_resend(session_id, target_message_id)
        out = self.handle_chat_turn(
            session_id=session_id,
            user_message=eff_msg,
            message_id=target_message_id,
            provider_id=eff_prov,
            model=model,
            attachments=attachments,
            ui_handler="NUIDesktopStore.editAndResend",
        )
        out["edited_and_resent"] = True
        out["edited_message_id"] = target_message_id
        out["pruned_info"] = pruned_info
        return out

    def regenerate_chat_turn(
        self,
        *,
        session_id: str,
        assistant_message_id: str | None = None,
        provider_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Regenerate the assistant response for the last user message in `session_id` without corrupting session history."""
        eff_prov = provider_id or provider
        popped = self.storage.pop_last_assistant_for_regenerate(session_id, assistant_message_id)
        if not popped.get("ok"):
            return {"ok": False, "error": popped.get("reason", "NO_USER_MESSAGE_FOUND")}
        out = self.handle_chat_turn(
            session_id=session_id,
            user_message=str(popped["user_message"]),
            provider_id=eff_prov,
            model=model,
            attachments=popped.get("attachments"),
            ui_handler="NUIDesktopStore.regenerateResponse",
        )
        out["regenerated"] = True
        out["popped_info"] = popped
        return out
