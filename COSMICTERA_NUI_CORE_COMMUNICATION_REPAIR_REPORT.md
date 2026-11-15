# COSMICTERA NUI CORE COMMUNICATION ARCHITECTURE REPAIR REPORT

## 1. Ringkasan Eksekutif & Akar Masalah yang Diperbaiki

Berdasarkan hasil audit kode sumber (*Source Code Audit*) pada repositori `/Users/AMRA/hijaiyyah-mathematics/`, ditemukan bahwa seluruh komponen kecerdasan CosmicTera NUI—meliputi Persona Resmi (`src/hijaiyyah/ai/runtime.py::HybitAIProgram.system`), model lokal Ollama (`127.0.0.1:11434`), basis pengetahuan 7-domain (`src/hijaiyyah/nui/knowledge.py`), parser semantik USR (`src/hijaiyyah/nui/usr.py`), indeks program (`program_index.py`), mesin deterministik (`HISAMachine` + `MASTER_TABLE`), serta *Autonomous Self-Learning Engine* (`self_learning.py`)—sudah ada di dalam repositori, namun belum terhubung secara utuh pada alur komunikasi inti `nui-desktop`.

Enam akar masalah spesifik yang telah diperbaiki dalam implementasi ini:

1. **Pencocokan Substring Biasa (`t in hay`) pada `NUIContextualRetriever` (`persona_and_context.py`)**:
   - **Sebelum Perbaikan**: Pencarian konteks menggunakan operator substring `t in hay` tanpa batas kata (*word boundary*) dan tanpa pemfilteran *stopwords* percakapan bahasa Indonesia (`cara`, `gimana`, `bisa`, `pengembangan`, `sofwer`). Akibatnya:
     - Token `"cara"` pada pertanyaan `"Cara kamu coding gimana?"` cocok dengan substring `"se**cara**"` di dalam fakta `nui.exomatrix_embedding_is_the_most_conservative` (*"...dipilih secara konservatif..."*).
     - Token `"pengembangan"` pada pertanyaan `"Pengembangan sofwer ?"` cocok dengan kalimat di dalam fakta `burnin.tier1_clock_drift` (*"...jam mesin pengembangan..."*).
   - **Sesudah Perbaikan**: Mengimplementasikan pencocokan berbasis batas kata ketat (`has_word_boundary_match()`), normalisasi ejaan & sinonim bahasa Indonesia (`normalize_indonesian_query()`, `normalize_indonesian_token()`, termasuk `"sofwer"` $\rightarrow$ `"software"`, `"koding"` $\rightarrow$ `"coding"`), pembobotan frasa, serta ambang relevansi (`score >= 4.0` dengan *domain keyword trigger* pada `facts/`).
2. **Integrasi Langsung `knowledge.py::query()` dan `usr.py::parse_phrase()` (`persona_and_context.py`)**:
   - **Sebelum Perbaikan**: `NUIContextualRetriever.retrieve()` hanya memindai potongan teks dari daftar berkas statis dan `facts.load()`, tanpa memanggil `src/hijaiyyah/nui/knowledge.py::query()` (Lapis 9 — 7 domain: `NUI`, `HISA`, `RTL`, `HC`, `PAPAN`, `OFF`, `HOST`) maupun `src/hijaiyyah/nui/usr.py::parse_phrase()`.
   - **Sesudah Perbaikan**: Menambahkan metode `NUIContextualRetriever.retrieve_structured_knowledge()` yang secara otomatis memanggil `nui_usr.parse_phrase()` dan `nui_knowledge.query()` untuk istilah kanonik (`term HCPU`, `term Hybit`, dll.), modul RTL (`rtl hcpu_top`), opcode H-ISA (`opcode HLOAD`, dll.), huruf Hijaiyyah (`letter Jim`), program `.hasm`, dan identitas perangkat keras (`hardware identity`, `board latest`).
3. **Kesinambungan Multi-Turn History & Persona Resmi NUI (`persona_and_context.py`, `providers.py`)**:
   - **Sebelum Perbaikan**: Pertanyaan lanjutan singkat seperti `"Pengembangan software?"`, `"Pengembangan software bisa?"`, `"Contohnya?"`, `"Cara kamu coding gimana?"`, dan `"Lanjutkan pembahasan sebelumnya."` kehilangan konteks giliran sebelumnya dan jatuh ke cabang *fallback* yang menampilkan kutipan fakta mentah atau kalimat template generik.
   - **Sesudah Perbaikan**: Memperluas `classify_response_mode()` dengan `FOLLOWUP_PHRASES`, pelacakan `last_user_topic` dan `last_assistant_reply`, menyuntikkan blok `[8. KONTEKS PERCAKAPAN AKTIF & RIWAYAT SESI]` ke dalam `NUIPersonaLoader.build_system_prompt()`, serta menghubungkan riwayat percakapan multi-giliran di `OllamaProvider` dan `NativeNUIProvider` tanpa mengulang sapaan `Halo!` atau perkenalan diri.
4. **Pemahaman Perintah & Orkestrasi Eksekusi Nyata (`orchestrator.py`, `providers.py`, `self_learning.py`)**:
   - **Sebelum Perbaikan**: Perintah `"Cek sistem."` tidak masuk ke kategori `SYSTEM_DIAGNOSTICS`; perintah `"Jalankan program H-ISA."` tidak memicu eksekusi `rtl/programs/test_bsm.hasm` pada `HISAMachine`.
   - **Sesudah Perbaikan**:
     - `"Cek sistem."` / `"Periksa sistem."` menjalankan pemeriksaan read-only nyata terhadap layanan lokal (`127.0.0.1:8848`), status provider, model Ollama terpasang, memori Unified Memory macOS (`measure_mac_host_resources()`), dan koneksi perangkat keras Tang Nano 20K (`/dev/cu.usbserial-*`).
     - `"Jalankan program H-ISA."` mengidentifikasi dan merakit `rtl/programs/test_bsm.hasm`, mengeksekusinya secara deterministik pada `HISAMachine(MASTER_TABLE)`, dan melaporkan hasil aktual (`R1 = 112`, `output = [112]`, `PC = 9`, `cycles = 9`, Six-Guard `PASS`).
5. **Kejujuran Status Provider & Penghapusan Template Fallback Generik (`providers.py`, `server.py`)**:
   - **Sebelum Perbaikan**: Ketika pertanyaan terbuka tidak cocok dengan 21 aturan deterministik dan Ollama tidak aktif, `NativeNUIProvider` mengembalikan jawaban template generik (`"Apakah Anda ingin saya melakukan perhitungan Matematika Hijaiyyah..."`).
   - **Sesudah Perbaikan**: `NativeNUIProvider` mendelegasikan pertanyaan terbuka ke `OllamaProvider` ketika daemon Ollama aktif, dan melaporkan status jujur `PROVIDER UNAVAILABLE` (`NUI_LANGUAGE_ENGINE_UNAVAILABLE`) beserta penyebab dan langkah pemulihan ketika Ollama tidak aktif—tanpa pernah mengeluarkan kalimat template palsu.
6. **Penghapusan Fake Character-Slicing Streaming (`providers.py`, `CosmicTeraNUIApp.swift`)**:
   - **Sebelum Perbaikan**: `NUIIntelligenceProvider` dan `NativeNUIProvider` memotong string statis setiap `18` atau `28` karakter (`_split_semantic_segments`). Selain itu, timeout socket streaming pada `CosmicTeraNUIApp.swift` hanya `15` detik.
   - **Sesudah Perbaikan**: Menghapus pemotongan karakter tetap (`18`/`28` karakter), menggunakan unit kalimat/frasa alami (`_split_natural_units`) untuk output deterministik dan streaming token asli (`_iter_ollama_chat_stream` + `_StreamThinkTagFilter`) untuk Ollama, serta meningkatkan timeout socket streaming di `CosmicTeraNUIApp.swift` menjadi `90` detik.

---

## 2. Daftar File yang Diubah

| File | Perubahan Utama |
| :--- | :--- |
| `nui-desktop/backend/persona_and_context.py` | Menambahkan `has_word_boundary_match()`, `normalize_indonesian_query()`, `normalize_indonesian_token()`, `FOLLOWUP_PHRASES`, integrasi langsung `knowledge.query()` dan `usr.parse_phrase()` melalui `retrieve_structured_knowledge()`, penyempurnaan `classify_response_mode()`, perbaikan `HybitAIProgram()` pada `NUIPersonaLoader`, serta penghapusan pencocokan substring `t in hay`. |
| `nui-desktop/backend/providers.py` | Memperbaiki `NativeNUIProvider` dan `OllamaProvider`: penanganan `"Cek sistem."`, `"Jalankan program H-ISA."` (`test_bsm.hasm` $\rightarrow$ `HISAMachine`), `"Pengembangan software?"`, `"Cara kamu coding gimana?"`, `"Contohnya?"`, `"Lanjutkan pembahasan sebelumnya."`, delegasi ke `OllamaProvider`, pelaporan jujur `PROVIDER UNAVAILABLE` (`NUI_LANGUAGE_ENGINE_UNAVAILABLE`), serta penghapusan pemotongan 18 karakter. |
| `nui-desktop/backend/self_learning.py` | Memperluas `NUIMultiModelRouter.classify_and_route()` untuk klasifikasi tugas deterministik/diagnostik/H-ISA vs rekayasa perangkat lunak, pencocokan batas kata pada `retrieve_learned_items()`, dan penambahan `record_turn_observation()` dengan disiplin provenans (`Verified`, `Repository Derived`, `Model Inferred`). |
| `nui-desktop/backend/orchestrator.py` | Menghubungkan `self.native_provider.ollama_provider = self.ollama_provider` dan mencatat observasi setiap giliran percakapan ke `self.self_learning.record_turn_observation()`. |
| `nui-desktop/backend/server.py` | Menghubungkan `persona_loader`, `context_retriever`, dan `ollama_provider` secara konsisten ke `NativeNUIProvider` dan `OllamaProvider`. |
| `nui-desktop/macos/Sources/CosmicTeraNUIApp.swift` | Meningkatkan timeout socket streaming `LocalLoopbackClient.streamChatRequest` dari `15` detik menjadi `90` detik dan menyelaraskan urutan fallback model lokal terpasang. |
| `nui-desktop/tests/test_nui_core_communication_repair.py` | Rangkaian pengujian regresi baru yang memverifikasi seluruh 8 prioritas perbaikan, termasuk 10 kasus uji percakapan dari hasil audit, pencegahan *false positive* substring, integrasi `knowledge.query()` & `usr.parse_phrase()`, dan kejujuran status provider. |

---

## 3. Hasil Pengujian Regresi (`pytest`)

Seluruh rangkaian pengujian di `nui-desktop/tests/` (total **49 pengujian** lintas 6 berkas uji) lulus **100% (`49 passed`)**:

- `nui-desktop/tests/test_nui_core_communication_repair.py` (6/6 PASSED)
- `nui-desktop/tests/test_nui_communication_engine.py` (8/8 PASSED)
- `nui-desktop/tests/test_nui_desktop_full.py` (9/9 PASSED)
- `nui-desktop/tests/test_nui_live_streaming_conversation.py` (4/4 PASSED)
- `nui-desktop/tests/test_nui_natural_conversation_behavior.py` (5/5 PASSED)
- `nui-desktop/tests/test_nui_ollama_qwen_self_learning.py` (10/10 PASSED)
- `nui-desktop/tests/test_nui_smart_auto_scroll.py` (7/7 PASSED)

---

## 4. Perbandingan Respons Sebelum dan Sesudah Perbaikan

| Input Pengguna | Sebelum Perbaikan (Audit) | Sesudah Perbaikan (Terverifikasi) |
| :--- | :--- | :--- |
| **`Kamu siapa?`** | Memperkenalkan diri dengan sapaan statis tanpa kesinambungan pada giliran berikutnya. | `"Halo! Saya NUI, Natural Universal Intelligence dari CosmicTera. Saya siap membantu Anda melakukan komputasi, mengembangkan software, memahami Matematika Hijaiyyah, dan mengelola sistem CosmicTera."` |
| **`Pengembangan software?`** / **`Pengembangan software bisa?`** | Salah menarik fakta `burnin.tier1_clock_drift` (*"...jam mesin pengembangan..."*) karena pencocokan substring `pengembangan`. | Melanjutkan konteks perkenalan tanpa mengulang sapaan `Halo!`, menjelaskan alur rekayasa software NUI (`Python`, `H-ISA .hasm`, `Hybit Code .hc`, `Swift`, `Verilog RTL`, `pytest`, `HISAMachine`). |
| **`Cek sistem.`** | Tidak dikenali sebagai diagnostik; jatuh ke pencarian fakta acak `burnin.tier1_clock_drift`. | Menjalankan pemeriksaan read-only nyata dan menampilkan status aktual Layanan Lokal (`127.0.0.1:8848`), Provider, Ollama Local Language Engine, Unified Memory macOS, dan perangkat keras Tang Nano 20K. |
| **`Contohnya?`** | Jatuh ke kalimat template generik *"Apakah Anda ingin saya melakukan perhitungan Matematika Hijaiyyah..."*. | Memberikan contoh konkret sesuai topik sebelumnya (contoh kode Python `MASTER_TABLE` & `Six-Guard` serta program H-ISA `rtl/programs/test_bsm.hasm`). |
| **`Cara kamu coding gimana?`** | Salah menarik fakta `nui.exomatrix_embedding_is_the_most_conservative` karena kata `"cara"` cocok dengan substring `"se**cara**"`. | Menjelaskan 3 tahap alur kerja coding NUI (`L1–L2` pemetaan AST & grafik kode di `src/hijaiyyah/`, penulisan/edit kode dengan `mypy` & `ruff`, serta pengujian otomatis `pytest` & `HISAMachine`). |
| **`Jalankan program H-ISA.`** | Tidak mengeksekusi program `.hasm`; jatuh ke pencarian fakta teks. | Merakit dan mengeksekusi `rtl/programs/test_bsm.hasm` (`9` instruksi) pada `HISAMachine` dan melaporkan hasil aktual: `Output [112]` (`R1 = 112`), `PC = 9`, `9` siklus, Six-Guard `PASS`. |
| **`Lanjutkan pembahasan sebelumnya.`** | Kehilangan konteks dan mengeluarkan kalimat template generik. | Melanjutkan topik terakhir di dalam riwayat sesi (`prior_user_turns`) secara langsung dan terstruktur. |
| **`Jelaskan hubungan NUI dengan HCPU.`** | Hanya menampilkan definisi HCPU tanpa mengaitkan peran NUI. | Memanggil `knowledge.query("term HCPU")` dan `knowledge.query("rtl hcpu_top")` lalu menjelaskan 3 titik integrasi NUI–HCPU: unifikasi alamat atomik (`atom.py`), paritas eksekusi P3 (`parity_model.py`), dan gerbang fail-closed L6–L7 (`rtl_function.py`, `layer7.py`). |
| **`Hitung 5 + 7.`** | Berhasil (`12`), namun penjelasan tindak lanjutnya tidak terhubung dengan baik. | Menjalankan kompilasi deterministik `usr.lower` $\rightarrow$ `assemble` $\rightarrow$ `HISAMachine` dan menghasilkan `"Hasilnya 12 (5 + 7 = 12)."` |
| **`Cari dokumentasi Gowin FPGA.`** | Menampilkan ringkasan umum tanpa kueri klaim perangkat keras L9. | Memanggil `knowledge.query("hardware identity")` dan merangkum spesifikasi **Sipeed Tang Nano 20K** (`Gowin GW2AR-LV18QN88C8/I7`, `GW2A-18C`, `IDCODE 0x81b`, `27.00 MHz`, HDMI `1280×720 @ 60 Hz`, kebijakan `SRAM_ONLY`). |
