# ARSITEKTUR TEKNIS: COSMICTERA NUI DESKTOP (`COSMICTERA_NUI_DESKTOP_ARCHITECTURE.md`)

- **Aplikasi Desktop**: [`nui-desktop/macos/build/CosmicTera NUI.app`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/build/CosmicTera%20NUI.app) (`SwiftUI` + `AppKit` + `WebKit`)
- **Backend Layanan Lokal**: [`nui-desktop/backend/`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend) (`Python 3.13`, `SQLite WAL`, `ThreadingHTTPServer` + `SSE`)
- **Pustaka Inti yang Dihubungkan**: [`src/hijaiyyah/`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah) dan [`NUI/`](file:///Users/AMRA/hijaiyyah-mathematics/NUI)

## 1. Diagram Arsitektur 2-Lapisan (Native macOS UI + NUI Local Service)

```
+-----------------------------------------------------------------------------------+
|                        COSMICTERA NUI DESKTOP (macOS .app)                        |
|  SwiftUI + AppKit + Isolated WKWebView | Official Logo & CosmicTera Dark Palette  |
|  [13 Sidebar Menus]  <--->  [Main Center Workspace]  <--->  [Right NUI Inspector] |
|                                [Bottom Activity Bar]                              |
+-----------------------------------------+-----------------------------------------+
                                          | Loopback JSON + Server-Sent Events (SSE)
                                          | Localhost Endpoint: 127.0.0.1:8848
+-----------------------------------------v-----------------------------------------+
|                         NUI LOCAL SERVICE (nui-desktop/backend/)                  |
|                                                                                   |
|  +---------------------------+   +---------------------------------------------+  |
|  |   NUITaskOrchestrator     |   |            PermissionEngine                 |  |
|  |  - Goal Decomposition     |-->|  - 15 Permission Categories                 |  |
|  |  - Step Queue & Progress  |   |  - 6 Approval Modes (Once/Session/Always/   |  |
|  |  - WAITING_FOR_APPROVAL   |   |    Ask/Deny/Revoke)                         |  |
|  |  - Stop / Cancel / Resume |   |  - Domain, Folder & Endpoint Granularity    |  |
|  +-------------+-------------+   +----------------------+----------------------+  |
|                |                                        |                         |
|                v                                        v                         |
|  +-----------------------------------------------------------------------------+  |
|  |                              NUIToolRegistry                                |  |
|  |  - LocalFileTools (.nui_trash backup)   - CodingTools (Edit/Website/Pytest) |  |
|  |  - GitTools (Status/Log/Diff)           - TerminalTools (Gated & Audited)   |  |
|  |  - Web/BrowserTools (Prompt Injection Guard) - APIConnectors (Keychain)     |  |
|  |  - HardwareTools (Tang Nano 20K / S1 / S2)   - CosmicTeraSubsystemTools     |  |
|  +--------------------------------------+--------------------------------------+  |
|                                         |                                         |
|  +--------------------------------------v--------------------------------------+  |
|  |                         NUIIntelligenceProvider                             |  |
|  |  1. NativeNUIProvider -> src/hijaiyyah (L0-L11 + 11 CosmicTera Subsystems)  |  |
|  |  2. OllamaProvider    -> 127.0.0.1:11434 (Honest Available/Unavailable)     |  |
|  |  3. OptionalExternalProvider -> Keychain + Permission Gated REST Adapter    |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

## 2. Pemetaan Komponen Backend & Frontend

| Berkas | Tanggung Jawab Arsitektural |
|---|---|
| [`nui-desktop/backend/storage.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/storage.py) | Penyimpanan SQLite thread-safe (`sessions`, `messages`, `tasks`, `permission_rules`, `pending_approvals`, `authorized_folders`, `api_connectors`, `knowledge_items`, `audit_logs`), integrasi `KeychainVault`, dan fungsi `redact_secrets`. |
| [`nui-desktop/backend/permissions.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/permissions.py) | Implementasi `PermissionEngine` dengan 15 kategori izin, 6 mode persetujuan, normalisasi domain dan path absolut, pemeriksaan mode operasi `LOCAL` vs `HYBRID`/`ONLINE`, dan gerbang final `DEPLOYMENT`. |
| [`nui-desktop/backend/providers.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/providers.py) | Implementasi `NativeNUIProvider` (terhubung ke `MASTER_TABLE`, `guards`, `exomatrix`, `algebra`, `hisa`, `hisab`, `crypto.cube`, `nui.features`, `nui.usr`, `nui.knowledge`), `OllamaProvider`, dan `OptionalExternalProvider`. |
| [`nui-desktop/backend/tools.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/tools.py) | Registri alat `NUIToolRegistry` beserta sanitizer `sanitize_untrusted_web_content` dan pengendali perangkat keras `CosmicTeraNUIControlCenter`. |
| [`nui-desktop/backend/orchestrator.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/orchestrator.py) | Orkestrator multi-langkah `NUITaskOrchestrator` yang mengelola siklus hidup tugas (`QUEUED`, `RUNNING`, `WAITING_FOR_APPROVAL`, `COMPLETED`, `FAILED`, `CANCELLED`). |
| [`nui-desktop/backend/server.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/server.py) | Server HTTP + SSE pada `127.0.0.1:8848` beserta metode `dispatch_request` untuk pengujian deterministik. |
| [`nui-desktop/macos/Sources/CosmicTeraNUIApp.swift`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/Sources/CosmicTeraNUIApp.swift) | Antarmuka native macOS (`SwiftUI` + `AppKit` + `WebKit`) dengan 13 tampilan navigasi, inspector kanan, dan bar aktivitas bawah. |

## 3. Integrasi Jujur NUI L0–L11

Setiap lapisan NUI dipetakan langsung ke modul yang telah terverifikasi di repositori tanpa klaim berlebihan:
- **L0 (`RUNNING`)**: [`src/hijaiyyah/nui/facts.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/nui/facts.py) & [`features.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/nui/features.py) — 27 fakta tersegel dan ekstraksi 5 fitur geometri huruf.
- **L1 (`COMPLETE`)**: [`src/hijaiyyah/nui/repository_graph.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/nui/repository_graph.py) — 1.828 node dan 4.689 edge.
- **L2 (`COMPLETE`)**: [`src/hijaiyyah/nui/program_index.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/nui/program_index.py) — 62 program `.hasm`, 1.541 fungsi Python, dan 128 modul Verilog.
- **L3 (`COMPLETE`)**: [`src/hijaiyyah/nui/execution_trace.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/nui/execution_trace.py) — 63 lari eksekusi dan 1.478 edge kausal.
- **L4 (`COMPLETE`)**: [`src/hijaiyyah/nui/parity_model.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/nui/parity_model.py) — 74/105 opcode terbukti paritas P3.
- **L5 (`READY`)**: [`src/hijaiyyah/nui/layer5.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/nui/layer5.py) — 11 kolektor observasi host Ubuntu ARM64.
- **L6 (`RUNNING`)**: [`src/hijaiyyah/nui/hardware_state.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/nui/hardware_state.py) & [`rtl_function.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/nui/rtl_function.py) — model transisi keadaan RTL dan monitor HDMI `86.01 MHz`.
- **L7 (`READY`)**: [`src/hijaiyyah/nui/layer7.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/nui/layer7.py) & [`layer7_decision.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/nui/layer7_decision.py) — gerbang keputusan fail-closed dengan `record_sha256`.
- **L8 (`NOT IMPLEMENTED` / `AT`)**: Ditampilkan jujur sebagai `AT (MANUAL DIAGNOSTICS)`.
- **L9 (`COMPLETE`)**: [`src/hijaiyyah/nui/knowledge.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/nui/knowledge.py) — mesin kueri 7 domain (`HC`, `HISA`, `RTL`, `OFF`, `PAPAN`, `NUI`, `HOST`).
- **L10 (`NOT IMPLEMENTED` / `AT`)**: Ditampilkan jujur sebagai `AT (NOT IMPLEMENTED)`.
- **L11 (`READY` / `AT`)**: [`src/hijaiyyah/nui/atom.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/nui/atom.py) — unifikasi alamat atomik indeks Master Table = opcode H-ISA = alamat ROM HCPU.
