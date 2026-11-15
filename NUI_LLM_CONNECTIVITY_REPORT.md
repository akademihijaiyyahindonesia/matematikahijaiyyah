# NUI FULL LLM CONNECTIVITY & GENERAL INTELLIGENCE REPAIR REPORT

## 1. Ringkasan Eksekutif

Laporan ini mendokumentasikan hasil audit menyeluruh atas jalur komunikasi **CosmicTera NUI Desktop**, penemuan seluruh aset LLM lokal di macOS, perbaikan pembatasan kecerdasan (*template lock* dan *irrelevant knowledge injection*), serta bukti verifikasi nyata untuk 8 skenario pengujian lintas bidang (kecerdasan umum, pemrograman umum, dan spesialisasi CosmicTera).

- **Masalah Utama yang Ditemukan Saat Audit Runtime**:
  1. **Penguncian Provider pada `native_nui` (Template Deterministik)**: Pada `nui-desktop/data/nui_desktop.db` dan `CosmicTeraNUIApp.swift`, pengaturan `active_provider` terkunci pada `"native_nui"` (`cosmictera-nui-native-v1.3`), sehingga sebagian besar pesan pengguna (`req-13b82554b53e`, `req-b3bf25552f0d`, `req-5e7244073acd`) dijawab oleh blok `if/elif` statis dalam `~35–68 ms` tanpa mencapai Ollama.
  2. **Tidak Ada Delegasi Streaming Langsung ke Local LLM pada Pertanyaan Umum**: `NativeNUIProvider.stream_respond()` sebelumnya memanggil `self.respond()` secara sinkron lalu memotong teks statis dengan `_split_natural_units()`, bukan mengalirkan token NDJSON langsung dari `OllamaProvider.stream_respond()`.
  3. **Injeksi Konteks Repository pada Pertanyaan Umum (Non-CosmicTera)**: `NUIContextualRetriever.retrieve()` sebelumnya tetap mencari kecocokan kata di dokumen internal untuk setiap pertanyaan `TECHNICAL`, sehingga pertanyaan coding/CS umum berisiko tercampur dengan dokumen internal CosmicTera.
  4. **Aturan `HybitAIProgram.system` yang Terlalu Membatasi Topik Umum**: Kalimat *"Jawab hanya dari konteks yang diberikan. Jika konteks tidak memuat jawabannya, katakan tidak tahu"* di `src/hijaiyyah/ai/runtime.py` sebelumnya disuntikkan ke LLM tanpa pemisahan cakupan, sehingga model bahasa merasa dilarang menjawab pertanyaan di luar isi repositori.

- **Perbaikan Arsitektural yang Diterapkan**:
  - Menjadikan **Local Ollama Language & Coding Engine (`local_ollama`)** sebagai engine runtime utama dengan pemilihan otomatis atas **5 model LLM lokal yang terpasang di Mac** (`qwen3:4b-instruct-2507-q4_K_M`, `qwen3-coder:30b`, `hermes3:8b`, `santri-ai-8b:latest`, `santri-ai-kecil:latest`).
  - Menambahkan mode **`GENERAL_INTELLIGENCE`** dan fungsi gerbang **`is_cosmictera_domain_query()`** di [`nui-desktop/backend/persona_and_context.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/persona_and_context.py) sehingga pertanyaan umum/coding (Pertanyaan 1–5) selalu memiliki `retrieved_sources = []` (`0` fakta/dokumen repositori yang disuntikkan) dan dijawab langsung oleh Local LLM.
  - Memperbarui `NUIPersonaLoader.build_system_prompt()` agar mempertahankan identitas resmi `HybitAIProgram.system` untuk klaim internal CosmicTera, sekaligus membuka penuh kemampuan LLM untuk menjawab pemrograman umum (Python, JS, Swift, C/C++, HTML, CSS, Rust, SQL, REST API vs GraphQL, debugging), matematika, analisis, dan percakapan lintas bahasa.
  - Menambahkan perekaman bukti telemetri langsung dari Ollama (**`ollama_runtime_proof`**) di [`nui-desktop/backend/providers.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/providers.py) yang mencatat `endpoint` (`127.0.0.1:11434/api/chat`), `http_status` (`200`), `model_responded`, `stream_chunk_count`, `stream_sample_tokens`, `prompt_eval_count`, `eval_count`, dan `total_duration_ms`.
  - Menambahkan fitur **hot-reload otomatis (`_hot_reload_if_needed()`)** di [`nui-desktop/backend/server.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/server.py) serta memperbarui [`nui-desktop/launch_cosmictera_nui.command`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/launch_cosmictera_nui.command).

## 2. Inventaris Seluruh Aset LLM Lokal & Engine Komputasi yang Ditemukan

Hasil pemindaian runtime pada mesin host macOS (`Apple M1 Max`, `32.0 GiB Unified Memory`, `96.01 GiB` ruang disk bebas) menemukan seluruh aset model bahasa lokal dan engine deterministik berikut yang kini terintegrasi otomatis ke dalam NUI:

| Kategori Aset | Nama Model / Komponen | Endpoint / Lokasi | Peran Otomatis di CosmicTera NUI | Status Runtime |
| :--- | :--- | :--- | :--- | :--- |
| **Local LLM (Ollama)** | `qwen3:4b-instruct-2507-q4_K_M` | `127.0.0.1:11434/api/chat` | **Primary Fast Interactive LLM & General Coding Engine** (respons streaming cepat `1,3–3,2 detik`) | **CONNECTED & ACTIVE** |
| **Local LLM (Ollama)** | `qwen3-coder:30b` | `127.0.0.1:11434/api/chat` | **Heavy Software Engineering & Architecture Specialist (30B Q4_K_M)** | **CONNECTED & READY** |
| **Local LLM (Ollama)** | `hermes3:8b` | `127.0.0.1:11434/api/chat` | **General Reasoning, Analysis & Tool-Use Model (8B)** | **CONNECTED & READY** |
| **Local LLM (Ollama)** | `santri-ai-8b:latest` | `127.0.0.1:11434/api/chat` | **Indonesian Conversational & Domain Reasoning Model (8B)** | **CONNECTED & READY** |
| **Local LLM (Ollama)** | `santri-ai-kecil:latest` | `127.0.0.1:11434/api/chat` | **Lightweight Fast Indonesian Assistant Model** | **CONNECTED & READY** |
| **NUI Identity & Rules** | `HybitAIProgram.system` | `src/hijaiyyah/ai/runtime.py` | **Identitas Resmi NUI & Aturan Epistemik Klaim CosmicTera (`K1–K15`, `R1–R13`)** | **ACTIVE** |
| **NUI Knowledge L9** | `knowledge.query()` & `usr.parse_phrase()` | `src/hijaiyyah/nui/knowledge.py`, `usr.py` | **7-Domain Structured Knowledge Base (`HC, HISA, RTL, OFF, PAPAN, NUI, HOST`)** | **ACTIVE** |
| **NUI Deterministic Core** | `HISAMachine` & `MASTER_TABLE` | `src/hijaiyyah/hisa/machine.py`, `core/master_table.py` | **Eksekusi Bit-Exact H-ISA (`.hasm`/`.hbc`), Vektor Hybit 18D, Six-Guard (`G1–G4, T1–T2`)** | **ACTIVE** |
| **NUI Self-Learning** | `NUIAutonomousSelfLearningEngine` | `nui-desktop/backend/self_learning.py`, `src/hijaiyyah/hmcl/` | **Validasi Coding Skill via `pytest` & Pencatatan Observasi Berprovenansi** | **ACTIVE** |

## 3. Bukti Koneksi Runtime ke Ollama & Streaming Token Asli

Berdasarkan jejak audit runtime di [`nui-desktop/data/nui_desktop.db`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/data/nui_desktop.db) dan [`nui-desktop/data/communication_audit.jsonl`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/data/communication_audit.jsonl) serta verifikasi protokol pada [`nui-desktop/tests/test_nui_llm_connectivity.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_llm_connectivity.py):

1. **Jalur Koneksi Aktual End-to-End**:
   - **Desktop UI (`CosmicTeraNUIApp.swift`)**: `NUIDesktopStore.sendChatMessage()` mengirim request `POST /api/chat/stream` ke `127.0.0.1:8848` melalui `LocalLoopbackClient.streamChatRequest()`.
   - **Backend Server (`server.py`)**: Menerima request di `/api/chat/stream`, menjalankan `_hot_reload_if_needed()`, dan memanggil `NUITaskOrchestrator.stream_chat_turn()`.
   - **Orchestrator & Router (`orchestrator.py` & `self_learning.py`)**: Memilih `OllamaProvider` (`provider: "local_ollama"`, `model: "qwen3:4b-instruct-2507-q4_K_M"` atau `"qwen3-coder:30b"`).
   - **Ollama Daemon (`providers.py`)**: Membuka koneksi streaming ke `POST 127.0.0.1:11434/api/chat` dengan `"stream": true` melalui `_iter_ollama_chat_stream()` yang membaca baris NDJSON (`resp.fp.readline()`) secara langsung saat setiap token dihasilkan model.
   - **Filter `<think>` & Pengiriman SSE ke UI**: `_StreamThinkTagFilter` menyaring blok `<think>...</think>` secara *real-time* dan memancarkan event SSE `partial_response` (`delta` + `accumulated_text`) ke UI untuk setiap potongan token asli dari model, diakhiri dengan `final_response` yang memuat objek `ollama_runtime_proof`.
2. **Bukti Log Koneksi Ollama Aktual di Database (`nui_desktop.db`)**:
   - `req-01121d91d7fd`: `Ollama Local Language Engine: CONNECTED (qwen3-coder:30b, 5 model lokal terpasang)` pada `Apple M1 Max (32.0 GiB RAM)`.
   - `req-ec17e04e8872`: `provider="local_ollama"`, `model="qwen3:4b-instruct-2507-q4_K_M"`, `http_status=200`, `execution_status="RESPONSE_COMPLETE"`, `response_time_ms=1364.462`.
   - `req-9f9926cc55b9`: `provider="local_ollama"`, `model="qwen3:4b-instruct-2507-q4_K_M"`, `http_status=200`, `execution_status="RESPONSE_COMPLETE"`, `response_time_ms=3188.619`.
   - `req-6a3302413b8d`: `provider="local_ollama"`, `model="qwen3:4b-instruct-2507-q4_K_M"`, `http_status=200`, `execution_status="RESPONSE_COMPLETE"`, `response_time_ms=8597.606`.

## 4. Hasil Delapan Pengujian Wajib (Section 4)

Kedelapan pengujian wajib telah diverifikasi melalui [`nui-desktop/tests/test_nui_llm_connectivity.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_llm_connectivity.py):

| No | Pertanyaan Uji | Klasifikasi Mode & Domain | Konteks Repository Disuntikkan? | Provider & Model Penjawab | Ringkasan Respons & Bukti Streaming | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `"Kamu bisa membantu pengembangan software?"` | `CAPABILITY_INQUIRY` (`is_cosmictera_specific=False`) | **TIDAK (`[]` — 0 fakta repo)** | `local_ollama` (`qwen3:4b-instruct-2507-q4_K_M`) | Menjelaskan secara alami kemampuan NUI dalam perancangan arsitektur aplikasi, penulisan kode lintas bahasa (Python, JS, Swift, C/C++, Rust, HTML/CSS), debugging, dan unit test tanpa injeksi `burnin.*`. (`HTTP 200`, `stream=True`). | **PASS** |
| **2** | `"Buatkan contoh aplikasi Python sederhana."` | `GENERAL_INTELLIGENCE` (`is_cosmictera_specific=False`) | **TIDAK (`[]` — 0 fakta repo)** | `local_ollama` (`qwen3:4b-instruct-2507-q4_K_M`) | Menghasilkan kode aplikasi Python lengkap dan siap dijalankan (`def main()`, manajemen daftar tugas CLI) beserta penjelasan cara menjalankannya secara streaming token demi token. (`HTTP 200`, `stream=True`). | **PASS** |
| **3** | `"Jelaskan perbedaan REST API dan GraphQL."` | `GENERAL_INTELLIGENCE` (`is_cosmictera_specific=False`) | **TIDAK (`[]` — 0 fakta repo)** | `local_ollama` (`qwen3:4b-instruct-2507-q4_K_M`) | Menjelaskan perbandingan arsitektur REST API (multi-endpoint berbasis resource) vs GraphQL (single endpoint `/graphql`, query fleksibel anti *over-fetching*/*under-fetching*) tanpa menyentuh fakta hardware CosmicTera. (`HTTP 200`, `stream=True`). | **PASS** |
| **4** | `"Bagaimana cara membuat website dari nol?"` | `GENERAL_INTELLIGENCE` (`is_cosmictera_specific=False`) | **TIDAK (`[]` — 0 fakta repo)** | `local_ollama` (`qwen3:4b-instruct-2507-q4_K_M`) | Menjelaskan tahapan terstruktur pembuatan website dari nol: struktur HTML5 (`index.html`), styling responsif CSS (`style.css`), interaktivitas JavaScript (`app.js`), backend API, hingga deployment. (`HTTP 200`, `stream=True`). | **PASS** |
| **5** | `"Bantu saya mencari bug dalam kode ini."` | `GENERAL_INTELLIGENCE` (`is_cosmictera_specific=False`) | **TIDAK (`[]` — 0 fakta repo)** | `local_ollama` (`qwen3:4b-instruct-2507-q4_K_M`) | Merespons secara kooperatif dengan meminta potongan kode/traceback yang ingin diperiksa serta menjelaskan metodologi pelacakan bug (*off-by-one*, *null/None reference*, kesalahan tipe data). (`HTTP 200`, `stream=True`). | **PASS** |
| **6** | `"Apa fungsi repository CosmicTera?"` | `REPOSITORY_AUDIT` (`is_cosmictera_specific=True`) | **YA (`NUI/LAYERS.md` + Ringkasan Repo Aktual: 128 modul Verilog, 62 program `.hasm`, 1541 fungsi Python, 27 fakta L0)** | `local_ollama` (`qwen3:4b-instruct-2507-q4_K_M`) | Menjelaskan fungsi repository `/Users/AMRA/hijaiyyah-mathematics` sebagai ekosistem komputasi *from letter to silicon* berbasis Matematika Hijaiyyah (28 huruf × Hybit 18D, Six-Guard, HC/HASM/HBC, HCPU di Tang Nano 20K, dan NUI L0–L11). (`HTTP 200`, `stream=True`). | **PASS** |
| **7** | `"Jelaskan hubungan H-ISA dengan HCPU."` | `TECHNICAL` (`is_cosmictera_specific=True`) | **YA (`docs/HISA_SPEC.md`, `teknologi/ISTILAH.md`, `knowledge.query('term HCPU')`, `rtl hcpu_top`)** | `local_ollama` (`qwen3:4b-instruct-2507-q4_K_M`) | Menjelaskan bahwa **H-ISA** adalah kontrak arsitektur set instruksi biner 32-bit (105 opcode spesifikasi, 84 opcode RTL, 74 opcode P3, 28 opcode huruf `0xE0–0xFB`), sedangkan **HCPU** (`rtl/hcpu_top.v`) adalah mikroprosesor pipeline 5-tahap (`IF -> ID -> EX -> MEM -> WB`) yang mengeksekusi H-ISA di silikon. (`HTTP 200`, `stream=True`). | **PASS** |
| **8** | `"Cek status sistem CosmicTera."` | `SYSTEM_DIAGNOSTICS` (`is_cosmictera_specific=True`) | **YA (Telemetri Host & Layanan Aktual: `127.0.0.1:8848`, `127.0.0.1:11434`, 5 model Ollama, RAM 32 GiB, Tang Nano 20K)** | `local_ollama` (`qwen3:4b-instruct-2507-q4_K_M`) | Melaporkan status aktual `LOCAL SERVICE READY (127.0.0.1:8848)`, koneksi aktif `local_ollama` beserta ke-5 model lokal yang terpasang, memori `Apple M1 Max (32.0 GiB)`, dan status koneksi hardware FPGA secara jujur. (`HTTP 200`, `stream=True`). | **PASS** |

## 5. Daftar Berkas yang Diperbarui

- [`nui-desktop/backend/persona_and_context.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/persona_and_context.py): Menambahkan fungsi `is_cosmictera_domain_query()`, mode `GENERAL_INTELLIGENCE`, pemisahan cakupan aturan `HybitAIProgram.system` untuk pertanyaan umum vs klaim internal CosmicTera, serta penyaringan ketat `NUIContextualRetriever.retrieve()`.
- [`nui-desktop/backend/providers.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/providers.py): Memperbarui `OllamaProvider` dan `NativeNUIProvider` agar mengalirkan token asli dari Ollama (`POST /api/chat`, `stream: true`), menyertakan `ollama_runtime_proof`, dan mendelegasikan pertanyaan `GENERAL_INTELLIGENCE` langsung ke Local LLM.
- [`nui-desktop/backend/server.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/server.py): Menambahkan `_hot_reload_if_needed()` dan mengatur default provider produksi ke `local_ollama` saat daemon Ollama aktif.
- [`nui-desktop/launch_cosmictera_nui.command`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/launch_cosmictera_nui.command): Memastikan database `nui_desktop.db` disetel ke `local_ollama`, mengompilasi ulang aplikasi bila kode Swift berubah, dan me-restart layanan `127.0.0.1:8848`.
- [`nui-desktop/tests/test_nui_llm_connectivity.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_llm_connectivity.py): Pengujian otomatis untuk ke-8 skenario wajib (Pertanyaan 1–5 tanpa injeksi fakta repo, Pertanyaan 6–8 dengan konteks repo/sistem terverifikasi).
