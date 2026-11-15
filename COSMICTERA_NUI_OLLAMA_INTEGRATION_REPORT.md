# COSMICTERA NUI — OLLAMA LOCAL LANGUAGE ENGINE INTEGRATION REPORT

- **Tanggal Laporan**: `2026-11-07`
- **Repositori**: [`/Users/AMRA/hijaiyyah-mathematics`](file:///Users/AMRA/hijaiyyah-mathematics)
- **Branch Pengembangan**: `feat/cosmictera-nui-desktop`
- **Baseline Terkunci yang Dilindungi**: `stage-1-5-security-integration` (`ea3c5b22445ed322b8e10348f930b4fa75731885`, 23/23 artefak utuh)
- **Status Integrasi**: **VERIFIED (`11/11 PASSED` pada [`test_nui_ollama_qwen_self_learning.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_ollama_qwen_self_learning.py) dan `33/33 PASSED` total rangkaian uji NUI Desktop)**

## 1. Status Instalasi & Deteksi Runtime Ollama

Hasil audit mesin lokal macOS menunjukkan:

| Parameter | Nilai Terverifikasi | Bukti / Sumber |
| :--- | :--- | :--- |
| **Lokasi Binary Ollama** | `/usr/local/bin/ollama` -> `/Applications/Ollama.app/Contents/Resources/ollama` | Terpasang di macOS host |
| **Endpoint Lokal** | `127.0.0.1:11434` (`/api/tags`, `/api/ps`, `/api/version`, `/api/chat`, `/api/generate`) | [`self_learning.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/self_learning.py) |
| **Auto-Start Host Launcher** | `ollama serve` otomatis dijalankan jika port `11434` belum aktif saat membuka peluncur | [`launch_cosmictera_nui.command`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/launch_cosmictera_nui.command) |
| **Penanganan Saat Offline** | Mengembalikan status jujur `NUI_LANGUAGE_ENGINE_UNAVAILABLE` / `PROVIDER_UNAVAILABLE` tanpa membuat jawaban palsu | [`providers.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/providers.py) |

## 2. Daftar Model Lokal & Konfigurasi Engine

Manajemen model diimplementasikan pada [`NUIModelAssetLibrary`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/self_learning.py) dan diekspos melalui endpoint `GET /api/models/library` serta `POST /api/models/op` di [`server.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/server.py):

- **Model Utama Coding & Penalaran Teknis**: `qwen3.8:27b` (fallback terverifikasi: `qwen3.6:27b`) dengan label resmi **`NUI CODING SPECIALIST — QWEN3.8-27B`**.
- **Model Pendamping / Ringan**: `qwen2.5-coder:7b` serta seluruh model lokal yang terdeteksi dari `/api/tags`.
- **Parameter Default Terkendali**:
  - `context_length` (`num_ctx`): `16384` token
  - `temperature`: `0.2`
  - `max_output_tokens` (`num_predict`): `2048` token
  - `stream`: `true` (streaming NDJSON chunk demi chunk dari `POST /api/chat`)

## 3. Sumber Persona & System Instruction NUI yang Digunakan

Integrasi ini **tidak membuat persona baru** dan **tidak membiarkan model mengaku sebagai chatbot generik**. Seluruh percakapan dikendalikan oleh [`NUIPersonaLoader`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/persona_and_context.py) yang memuat aset resmi dari repositori:

1. **Persona Inti Resmi**: `HybitAIProgram.system` dari [`src/hijaiyyah/ai/runtime.py`](file:///Users/AMRA/hijaiyyah-mathematics/src/hijaiyyah/ai/runtime.py).
2. **Konstitusi & Tata Kerja Proyek**: `K1–K15` dari [`AGENTS.md`](file:///Users/AMRA/hijaiyyah-mathematics/AGENTS.md) dan `R1–R13` dari [`cosmictera/RULES.md`](file:///Users/AMRA/hijaiyyah-mathematics/cosmictera/RULES.md).
3. **Arsitektur Lapisan NUI L0–L11**: Pemisahan tegas antara `IMPLEMENTED` (`L0`, `L1`, `L2`, `L5`) dan `AT (ARSITEKTUR TARGET)` (`L3`, `L4`, `L6`, `L7`, `L8`, `L9`, `L10`, `L11`) dari [`NUI/LAYERS.md`](file:///Users/AMRA/hijaiyyah-mathematics/NUI/LAYERS.md).
4. **Terminologi Baku**: Klasifikasi epistemik (`[DEFINISI]`, `[TEOREMA]`, `[ IMPLEMENTASI ]`, `[ARSITEKTUR-TARGET]`, `[KONJEKTUR]`, `[TERBUKA]`) dari [`teknologi/ISTILAH.md`](file:///Users/AMRA/hijaiyyah-mathematics/teknologi/ISTILAH.md).
5. **9-Layer System Prompt**: Dibangun secara deterministik dengan urutan prioritas:
   1. `NUI Core Identity` (`HybitAIProgram.system`)
   2. `NUI System Principles & Epistemic Honesty` (`K1–K15`, `R1–R13`)
   3. `NUI Thinking Framework` (7 tahap: *Understand, Classify, Retrieve Context, Plan, Execute/Calculate, Validate, Respond*)
   4. `CosmicTera Ecosystem Context` (28 huruf × 18D = 504 sel, Six-Guard, `H-ISA`, `HISAMachine`, `HFS`, `HOS`, `HMCL`)
   5. `Active Mode & Permission Rules` (15 kategori izin & 6 mode persetujuan)
   6. `Available Tools & Capabilities`
   7. `Relevant Project Knowledge` (hasil retrieval [`NUIContextualRetriever`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/persona_and_context.py))
   8. `Conversation History` (windowed + ringkasan otomatis)
   9. `Current User Message`

## 4. Cara Kerja Contextual Retrieval & Orchestration

Ketika pengguna mengirim pesan di [`CosmicTera NUI.app`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/build/CosmicTera%20NUI.app):

1. **Deterministic & Tool Pre-Execution**: [`OllamaProvider.stream_respond()`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/providers.py) memvalidasi apakah pesan meminta perhitungan aritmetika, nilai `BSM`, pencarian huruf Hijaiyyah 18D, atau simulasi program `H-ISA` (`test_bsm.hasm`). Jika ya, perhitungan dijalankan secara deterministik oleh modul Python (`compute_basmalah()`, `MASTER_TABLE`, `HISAMachine`) terlebih dahulu, lalu hasilnya disuntikkan sebagai fakta terverifikasi ke konteks Ollama.
2. **Repository Contextual Retrieval**: [`NUIContextualRetriever.retrieve_context()`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/persona_and_context.py) mengambil cuplikan dokumen dan kode paling relevan beserta metadata (`file_path`, `title`, `section`, `relevance_score`, `git_commit`, `epistemic_class`).
3. **Live Streaming (`POST /api/chat`)**: Respons dari Ollama dialirkan secara bertahap (`partial_response`) ke UI bersama tahapan berpikir nyata (`REQUEST_RECEIVED` -> `UNDERSTANDING` -> `ANALYZING` -> `TOOL_EXECUTION` -> `GENERATING_RESPONSE` -> `COMPLETE`).

## 5. Hasil Pengujian End-to-End (`TEST A` – `TEST J`)

Seluruh 10 skenario uji wajib pada spesifikasi telah diverifikasi otomatis di [`test_nui_ollama_qwen_self_learning.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_ollama_qwen_self_learning.py):

| Kode Uji | Skenario | Hasil | Bukti Verifikasi |
| :--- | :--- | :--- | :--- |
| **TEST A** | **Ollama Connection & Discovery** | **PASS** | `/api/models/library` mendeteksi status `CONNECTED`, versi Ollama, dan daftar model lokal |
| **TEST B** | **Persona Preservation (`"Siapa kamu?"`)** | **PASS** | Menjawab sebagai **CosmicTera NUI** dengan `HybitAIProgram.system` aktif |
| **TEST C** | **Project Context (`L0–L11`)** | **PASS** | Membedakan `IMPLEMENTED` (`L0, L1, L2, L5`) dan `AT (ARSITEKTUR TARGET)` dari `NUI/LAYERS.md` |
| **TEST D** | **Deterministic Computation (`128 * 64` & `BSM`)** | **PASS** | Menghasilkan `8192` dan `(112, 10, 9)` secara deterministik dari mesin Python |
| **TEST E** | **H-ISA / CPU Context (`test_bsm.hasm`)** | **PASS** | Menjalankan `HISAMachine` dan melaporkan `R1 = 624, PC = 8, cycles = 8` |
| **TEST F** | **Coding Request (`faktor_bilangan`)** | **PASS** | Merutekan ke `QWEN38_CODING_SPECIALIST` dan menghasilkan kode Python valid |
| **TEST G** | **Multi-Turn Memory** | **PASS** | Mengingat fokus percakapan (`"komunikasi NUI"`) lintas giliran dalam sesi yang sama |
| **TEST H** | **Streaming Response** | **PASS** | Mengirim chunk `partial_response` bertahap sebelum `final_response` |
| **TEST I** | **Stop Generation** | **PASS** | Menghentikan stream secara bersih dengan status `STOPPED` |
| **TEST J** | **Ollama Unavailable** | **PASS** | Melaporkan `NUI_LANGUAGE_ENGINE_UNAVAILABLE` / `PROVIDER_UNAVAILABLE` secara jujur |
