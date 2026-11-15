# LAPORAN PERBAIKAN: NUI CHAT & COMMUNICATION ENGINE COSMICTERA (`COSMICTERA_NUI_COMMUNICATION_REPAIR_REPORT.md`)

- **Tanggal Penyelesaian**: 7 November 2026
- **Repositori**: [`/Users/AMRA/hijaiyyah-mathematics`](file:///Users/AMRA/hijaiyyah-mathematics) (`feat/cosmictera-nui-desktop`)
- **Aplikasi Native macOS (Diperbarui)**: [`nui-desktop/macos/build/CosmicTera NUI.app`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/build/CosmicTera%20NUI.app) (sumber: [`CosmicTeraNUIApp.swift`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/Sources/CosmicTeraNUIApp.swift))
- **Layanan Backend & Communication Engine (`127.0.0.1:8848`)**: [`server.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/server.py), [`orchestrator.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/orchestrator.py), [`providers.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/providers.py), dan [`storage.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/storage.py)
- **Suite Pengujian Komunikasi End-to-End**: [`test_nui_communication_engine.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_communication_engine.py) (**8 fungsi uji mencakup 4 kueri diagnostik + 16 skenario wajib + 5 tahap percakapan nyata: `100% PASSED`**)

## 1. Akar Penyebab Mengapa Komunikasi Sebelumnya Gagal & Komponen yang Bermasalah

Audit menyeluruh pada jalur `USER INPUT → NUI DESKTOP UI → REQUEST HANDLER → NUI LOCAL SERVICE → INTELLIGENCE ENGINE → RESPONSE → UI` menemukan tiga akar masalah teknis yang menyebabkan NUI tidak merespons percakapan pengguna secara nyata:

| No | Komponen yang Bermasalah | Temuan Audit Aktual | Perbaikan yang Diterapkan |
|---|---|---|---|
| **1** | **Frontend macOS (`CosmicTeraNUIApp.swift`)** | Fungsi `NUIDesktopStore.sendChatMessage()` pada biner sebelumnya hanya mengeksekusi *in-memory stub* lokal di Swift tanpa mengirim request jaringan/socket ke `NUI Local Service` (`127.0.0.1:8848`). Selain itu, ketika `CosmicTera NUI.app` dibuka langsung dari Finder tanpa skrip peluncur, aplikasi tidak secara otomatis menjalankan daemon `server.py`. | Mengimplementasikan **`LocalLoopbackClient`** berbasis socket TCP POSIX (`Darwin.socket`, `connect`, `send`, `recv`) ke `127.0.0.1:8848` (membaca port aktif dari `nui-desktop/data/active_service.json`), serta menambahkan `spawnDaemonIfNeeded()` (`posix_spawn`) saat aplikasi dibuka dan penghentian bersih saat aplikasi ditutup (`NSApplication.willTerminateNotification`). |
| **2** | **Conversation & NLU Engine (`nui-desktop/backend/providers.py`)** | `NativeNUIProvider.respond()` sebelumnya hanya mencocokkan 4 pola sempit (kode `let ... print(...)`, opcode `.hasm`, nama satu huruf Hijaiyyah, atau kata `l0`/`layer`), mengabaikan `conversation_context` (riwayat pesan dalam sesi), dan mengembalikan paragraf statis yang sama untuk pertanyaan bahasa alami seperti *"Halo, apakah NUI aktif?"*, *"Jelaskan fungsi HCPU."*, *"Hitung 5 + 7."*, *"Apa hubungan NUI dengan HCPU?"*, maupun *"Ringkas pertanyaan pertama kita."*. | Membangun mesin pemahaman bahasa alami (**NLU & Multi-Turn Conversation Engine**) di dalam `NativeNUIProvider` yang: (a) membaca `conversation_context` per sesi untuk meringkas/merujuk giliran sebelumnya, (b) menerjemahkan ekspresi hitungan bahasa alami (*"Hitung 5 + 7"*) ke kompilasi `HC -> H-ISA -> HISAMachine` nyata, (c) menelusuri relasi lintas modul di `knowledge.py`, `teknologi/ISTILAH.md`, `facts/`, dan `rtl/hcpu_top.v`, serta (d) memeriksa status koneksi layanan dan port hardware `/dev/cu.usbserial-*` secara live. |
| **3** | **Kontrak Komunikasi & Orkestrator (`orchestrator.py` & `server.py`)** | Belum adanya struktur kontrak eksplisit `NUIChatRequest` / `NUIChatResponse` dengan korelasi `request_id` dan `session_id`, belum adanya endpoint pembatalan `POST /api/chat/stop` untuk tombol `Stop Generation`, serta belum adanya tabel audit khusus komunikasi (`communication_logs`). | Mengimplementasikan dataclass `NUIChatRequest` & `NUIChatResponse`, endpoint `POST /api/chat/stop` dan `GET /api/comm/logs`, tabel SQLite `communication_logs` + berkas `nui-desktop/data/communication_audit.jsonl`, serta pemisahan tegas 8 status UI (`UI READY`, `LOCAL SERVICE READY`, `PROVIDER CONNECTED`, `MODEL READY`, `GENERATING`, `RESPONSE COMPLETE`, `ERROR`, `PROVIDER UNAVAILABLE`). |

## 2. Audit & Status Intelligence Provider yang Tersedia (Section 2)

Sistem membedakan secara tegas antara **NUI Orchestrator**, **NUI L0–L11**, **Conversation Engine**, **Local Model Runtime**, dan **External Model Provider**:

| Provider ID | Nama Komponen | Jenis & Sumber | Status Aktual di Mesin Ini | Perilaku & Penanganan Jujur |
|---|---|---|---|---|
| **`native_nui`** (Default Aktif) | **CosmicTera Native NUI Engine (`cosmictera-nui-native-v1.3`)** | Deterministic NLU + `HISAMachine` + `HC/HASM/HBC` Compiler + 7-Domain Knowledge Base (`src/hijaiyyah/nui/`) | **`PROVIDER CONNECTED` / `MODEL READY`** (Selalu aktif secara lokal tanpa internet) | Mengeksekusi perhitungan melalui `usr.lower` & `HISAMachine`, menjawab kueri arsitektur dari `knowledge.py`, `facts/`, dan `ISTILAH.md`, serta memelihara `conversation_context` multi-giliran per sesi. |
| **`local_ollama`** (Opsional) | **Local Model Provider (`OllamaProvider`)** | Adapter HTTP lokal ke `127.0.0.1:11434` (`/api/tags`, `/api/generate`) | **`PROVIDER UNAVAILABLE`** (Biner `ollama` belum terpasang di mesin host) | Melaporkan secara jujur `PROVIDER UNAVAILABLE` beserta prosedur konfigurasi (`ollama serve` dan `ollama pull hermes3:8b`) atau `MODEL_NOT_FOUND` jika model belum diunduh — **tidak pernah** mengklaim model LLM aktif bila belum terpasang. |
| **`external_api`** (Opsional) | **Optional External API Provider (`OptionalExternalProvider`)** | Adapter REST eksternal berbasis macOS Keychain + `PermissionEngine` (`API_ACCESS`) | **Terkendali oleh Mode & Izin** (`LOCAL` = diblokir; `ONLINE`/`HYBRID` = wajib izin per domain) | Menampilkan domain tujuan dan jenis data (`user_message`, `conversation_context`), lalu meminta otorisasi (`WAITING_FOR_APPROVAL`) sebelum mengirim satu byte pun keluar. |

## 3. Service, Endpoint, dan Kontrak Komunikasi (`NUIChatRequest` / `NUIChatResponse`)

- **Binding Default**: Loopback lokal `127.0.0.1:8848` (dicatat otomatis ke [`nui-desktop/data/active_service.json`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/data/active_service.json) beserta `pid` dan pengecekan tabrakan port).
- **Daftar Endpoint Komunikasi**:
  - `GET /api/health` — Mengembalikan `service_state` (`LOCAL SERVICE READY`), `provider_state` (`PROVIDER CONNECTED` / `PROVIDER UNAVAILABLE`), `model_state` (`MODEL READY`), `operating_mode`, dan `pid`.
  - `POST /api/chat` — Menerima `NUIChatRequest` (`request_id`, `session_id`, `message_id`, `user_message`, `provider`, `model`, `attachments`, `ui_handler`) dan mengembalikan `NUIChatResponse` (`request_id`, `response_id`, `session_id`, `message_id`, `response_text`, `provider`, `model`, `execution_status`, `ui_state`, `response_time_ms`, `source_attribution`, `data`, `error`, `timestamp`).
  - `POST /api/chat/stop` — Membatalkan generasi yang sedang berjalan berdasarkan `request_id` atau `session_id` dan mengembalikan `execution_status: "STOPPED"`.
  - `GET /api/sessions` & `POST /api/sessions` — Memuat daftar sesi, riwayat pesan per `session_id`, membuat sesi baru, mengubah nama, mengekspor Markdown, dan menghapus sesi.
  - `GET /api/comm/logs` — Mengambil catatan audit komunikasi lengkap dari tabel `communication_logs`.

## 4. Log Komunikasi & Hasil Reproduksi 4 Kueri Diagnostik (Section 3)

Berikut adalah rekaman aktual dari tabel `communication_logs` / [`nui-desktop/data/communication_audit.jsonl`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/data/communication_audit.jsonl) untuk keempat pesan diagnostik wajib:

| Request ID | Pesan Pengguna | UI Handler | Endpoint | HTTP | Provider & Model | Status Eksekusi & UI State | Waktu Respons | Ringkasan Respons yang Diterima UI |
|---|---|---|---|---|---|---|---|---|
| `req-diag-01` | *"Halo, apakah NUI aktif?"* | `NUIDesktopStore.sendChatMessage` | `/api/chat` | `200` | `native_nui` (`cosmictera-nui-native-v1.3`) | `RESPONSE_COMPLETE` / `RESPONSE COMPLETE` | `2.1 ms` | Melaporkan `LOCAL SERVICE READY` (`127.0.0.1:8848`), `PROVIDER CONNECTED`, `MODEL READY`, mode `HYBRID`, dan status port USB-UART Tang Nano 20K. |
| `req-diag-02` | *"Jelaskan fungsi HCPU."* | `NUIDesktopStore.sendChatMessage` | `/api/chat` | `200` | `native_nui` (`cosmictera-nui-native-v1.3`) | `RESPONSE_COMPLETE` / `RESPONSE COMPLETE` | `4.8 ms` | Menjelaskan fungsi *Hijaiyyah Core Processing Unit* (`teknologi/ISTILAH.md:45`), ALU Codex 18D (`14× MULT9X9`), Six-Guard `HGRD`, HISAB `HPACK`/`HCRC`, pipeline 5-tahap (`rtl/hcpu_top.v`), dan `Fmax 119.60 MHz` post-route. |
| `req-diag-03` | *"Hitung 5 + 7."* | `NUIDesktopStore.sendChatMessage` | `/api/chat` | `200` | `native_nui` (`cosmictera-nui-native-v1.3`) | `RESPONSE_COMPLETE` / `RESPONSE COMPLETE` | `1.4 ms` | Mengompilasi `let a = 5; let b = 7; print(a + b);` lewat `usr.lower` ke H-ISA (`MOVI R1, 5`, `MOVI R2, 7`, `ADD R3, R1, R2`, `PRINT R3`, `HALT`), mengeksekusinya di `HISAMachine`, dan mengembalikan hasil **`5 + 7 = 12`** (`output: [12]`, `5` siklus). |
| `req-diag-04` | *"Apa status koneksi sistem?"* | `NUIDesktopStore.sendChatMessage` | `/api/chat` | `200` | `native_nui` (`cosmictera-nui-native-v1.3`) | `RESPONSE_COMPLETE` / `RESPONSE COMPLETE` | `1.9 ms` | Melaporkan koneksi layanan `127.0.0.1:8848`, status provider, deteksi port fisik `/dev/cu.usbserial-*`, hash bitstream `hcpu_hdmi_top.fs`, dan jumlah pesan dalam sesi SQLite. |

## 5. Hasil Pengujian 16 Skenario Wajib (Section 8) & 5 Tahap Percakapan Nyata (Section 9)

### 5.1 Matriks 16 Skenario Pengujian Wajib (`test_nui_communication_engine.py`)

| No | Skenario Uji Wajib | Fungsi Pengujian & Verifikasi | Hasil |
|---|---|---|---|
| 1 | UI mengirim pesan | `test_1_to_5_end_to_end_ui_to_backend_to_provider_to_timeline` (`request_id`, `message_id`, `ui_handler`) | **PASS** |
| 2 | Backend menerima pesan | `POST /api/chat` memvalidasi payload dan menyimpan pesan pengguna ke SQLite | **PASS** |
| 3 | Provider menerima request | `NativeNUIProvider.respond()` menerima prompt beserta `conversation_context` | **PASS** |
| 4 | Provider mengembalikan jawaban | Mengembalikan hasil eksekusi `HISAMachine` (`8 + 14 = 22`, `output: [22]`) | **PASS** |
| 5 | UI menampilkan jawaban | Timeline sesi (`GET /api/sessions?session_id=...`) memuat pesan pengguna & asisten dengan korelasi `request_id` | **PASS** |
| 6 | Conversation context dipertahankan | `test_6_and_7_conversation_context_and_multiple_sessions_isolation` (giliran ke-2 meringkas giliran ke-1 secara akurat) | **PASS** |
| 7 | Multiple session terisolasi | `Session Alpha` (*"Jelaskan fungsi HCPU."*) dan `Session Beta` (*"Analisis huruf Jim (ج)."*) tidak pernah saling mencampur riwayat | **PASS** |
| 8 | Provider tidak tersedia | `test_8_and_9_provider_unavailable_and_model_not_found` -> `execution_status: "PROVIDER_UNAVAILABLE"`, `ui_state: "PROVIDER UNAVAILABLE"` | **PASS** |
| 9 | Model tidak ditemukan | `OllamaProvider` saat model `hermes3:8b` belum terpasang -> `error: "MODEL_NOT_FOUND"` | **PASS** |
| 10 | Backend tidak berjalan | `test_10_11_12_13_backend_offline_network_timeout_and_empty_response` -> deteksi port tertutup & auto-spawn daemon di `CosmicTeraNUIApp.swift` | **PASS** |
| 11 | Network error | Penanganan exception `NETWORK_ERROR` tanpa crash dan ditampilkan di banner error UI | **PASS** |
| 12 | Request timeout | Penanganan `REQUEST_TIMEOUT` dengan status `ERROR` dan pencatatan di `communication_logs` | **PASS** |
| 13 | Response kosong | Penanganan respons kosong menjadi `error: "EMPTY_RESPONSE"`, `execution_status: "ERROR"` | **PASS** |
| 14 | Stop generation | `test_14_stop_generation_cancels_request` (`POST /api/chat/stop` membatalkan `request_id` -> `execution_status: "STOPPED"`) | **PASS** |
| 15 | Permission denied & Mode Lokal/Online | `test_15_permission_denied_and_online_authorization_for_external_provider` (Mode `LOCAL` memblokir `external_api`; Mode `ONLINE` menahan pada `WAITING_FOR_APPROVAL` dan menolak saat `DENY`) | **PASS** |
| 16 | Aplikasi dibuka ulang & service persisten | `test_16_application_reopen_and_service_persistence` (Menutup & membuka ulang instance pada SQLite memulihkan sesi dan konteks percakapan utuh) | **PASS** |

### 5.2 Hasil Uji Percakapan Nyata 5 Tahap Berurutan (Section 9)

Diambil langsung dari pengujian `test_section9_five_stage_real_conversation_acceptance`:
1. **Tahap 1 — `"Halo NUI."`**:
   - Status: `RESPONSE_COMPLETE` (`ui_state: "RESPONSE COMPLETE"`).
   - Jawaban: Melaporkan `LOCAL SERVICE READY` (`127.0.0.1:8848`), `PROVIDER CONNECTED` (`cosmictera-nui-native-v1.3`), `MODEL READY`, dan kesiapan sesi.
2. **Tahap 2 — `"Jelaskan apa itu CosmicTera."`**:
   - Status: `RESPONSE_COMPLETE`.
   - Jawaban: Menjelaskan ekosistem komputasi dari huruf hingga silikon berbasis **Matematika Hijaiyyah** (`28 huruf Hijaiyyah` × `18D`, `Six-Guard`), rantai `HC → HASM → HBC → HVM` (`62` program HASM), prosesor silikon **HCPU** (`128` modul Verilog, `27.00 MHz` / `119.60 MHz` Fmax), keamanan `Ka'bah`/`Jamrah`/`HISAB`/`USSS`, dan `27` fakta tersegel NUI `L0–L11`.
3. **Tahap 3 — `"Apa hubungan NUI dengan HCPU?"`**:
   - Status: `RESPONSE_COMPLETE`.
   - Jawaban: Menjelaskan hubungan antara NUI sebagai lapisan kecerdasan/koordinasi dan HCPU sebagai prosesor silikon melalui unifikasi alamat atomik (`src/hijaiyyah/nui/atom.py`: indeks Master Table = opcode H-ISA = alamat ROM HCPU), jejak & paritas eksekusi (`execution_trace.py`, `parity_model.py` `74/105` P3), pemodelan fungsi RTL & telemetri HDMI (`rtl_function.py`, `hcpu_hdmi_top.v`), serta gerbang keputusan fail-closed (`layer7.py`).
4. **Tahap 4 — `"Hitung 5 + 7 dan jelaskan hasilnya."`**:
   - Status: `RESPONSE_COMPLETE`.
   - Jawaban: Mengompilasi `let a = 5; let b = 7; print(a + b);` menjadi 5 instruksi H-ISA (`MOVI`, `MOVI`, `ADD`, `PRINT`, `HALT`), mengeksekusinya pada `HISAMachine` (`output: [12]`, `5` siklus), dan menjelaskan tahapan eksekusi register hingga menghasilkan **`5 + 7 = 12`**.
5. **Tahap 5 — `"Ringkas pertanyaan pertama kita."`**:
   - Status: `RESPONSE_COMPLETE`.
   - Jawaban: Membaca `conversation_context` sesi (`4` giliran pengguna sebelumnya), mengidentifikasi secara eksak bahwa pertanyaan pertama pengguna adalah **`"Halo NUI."`**, merangkum jawaban pertama NUI, dan mencantumkan urutan ke-4 pertanyaan sebelumnya dalam sesi tersebut.
