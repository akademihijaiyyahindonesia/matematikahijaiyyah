# COSMICTERA NUI — IRRELEVANT KNOWLEDGE INJECTION & RELEVANCE REPAIR REPORT

## 1. Ringkasan Eksekutif

Laporan ini mendokumentasikan pelacakan akar masalah (*root cause*), perbaikan kode sumber, dan hasil pengujian regresi untuk mengatasi bug kritis **Irrelevant Knowledge Injection** pada **CosmicTera NUI Desktop** (`nui-desktop/`).

- **Gejala Kegagalan Sebelumnya**: Ketika pengguna bertanya `"Kamu bisa membantu pengembangan software?"` (tercatat pada log audit aktual sebagai `"kamu bisa membantu pengembangan sofwer"` di `req-9680e9a08f05` serta `"pengembangan sofwer ?"` di `req-c899fc7ce528`), NUI justru menampilkan fakta hardware burn-in mentah:
  - `burnin.no_watchdog_exists`
  - `burnin.tier1_clock_drift`
- **Status Setelah Perbaikan**:
  - Pertanyaan kemampuan pengembangan software dan coding diklasifikasikan secara akurat sebagai `CAPABILITY_INQUIRY` (`software_development_capability`, `coding_workflow_capability`, `programming_languages_capability`, `python_debugging_capability`, `website_development_capability`, `repository_reading_capability`).
  - `NUIContextualRetriever.retrieve()` menerapkan **Intent Gate**, **Domain Trigger Gate**, dan **Relevance Threshold (`>= 6.0`)** sehingga kecocokan satu kata umum (`bisa`, `pengembangan`, `membaca`, `jam`, `mesin`, `berhenti`) tidak pernah lagi menarik fakta `facts/` yang tidak relevan.
  - Pertanyaan hardware spesifik (`"Jelaskan watchdog pada desain CosmicTera."` dan `"Berapa clock drift yang tercatat?"`) tetap mengambil fakta terverifikasi `burnin.no_watchdog_exists` dan `burnin.tier1_clock_drift` secara presisi dan menjelaskannya secara alami.
  - Seluruh **10/10 pengujian regresi wajib** pada [`nui-desktop/tests/test_nui_relevance_repair.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_relevance_repair.py) dan seluruh **59/59 pengujian NUI Desktop** lulus (`PASS`).

## 2. Jejak Request Aktual (*Actual Request Trace* — Sebelum vs Sesudah Perbaikan)

Data berikut diekstrak langsung dari berkas log audit [`nui-desktop/data/communication_audit.jsonl`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/data/communication_audit.jsonl) untuk request `req-9680e9a08f05` (`session_id: "sess-b089277e1172"`), `req-c899fc7ce528`, dan `req-e86ca7775d0d`:

| Parameter Audit | Sebelum Perbaikan (`req-9680e9a08f05` Aktual di Log) | Sesudah Perbaikan (Terverifikasi) |
| :--- | :--- | :--- |
| **Input Pengguna** | `"kamu bisa membantu pengembangan sofwer"` / `"Kamu bisa membantu pengembangan software?"` | `"Kamu bisa membantu pengembangan software?"` (serta varian ejaan `"sofwer"`) |
| **Active Provider** | `native_nui` | `native_nui` (terhubung ke `ollama_provider` bila aktif) |
| **Active Model** | `cosmictera-nui-native-v1.3` (Model lokal Ollama terdeteksi: `qwen3-coder:30b`, `qwen3:4b-instruct-2507-q4_K_M`, `hermes3:8b`, `santri-ai-8b:latest`, `santri-ai-kecil:latest`) | `cosmictera-nui-native-v1.3` + `qwen3-coder:30b` / `qwen3:4b-instruct-2507-q4_K_M` |
| **Response Mode** | `TECHNICAL` (salah klasifikasi karena belum ada mode `CAPABILITY_INQUIRY`) | `CAPABILITY_INQUIRY` |
| **Intent Classification** | `contextual_synthesis` (jatuh ke fallback langkah ke-22) | `software_development_capability` |
| **Conversation History** | Turn 1: `"halo"` -> `"Halo! Ada yang bisa saya bantu?"` | Riwayat sesi multi-giliran dipertahankan (`prior_user_turns`) |
| **Retrieval Query** | `"kamu bisa membantu pengembangan sofwer"` | Dihentikan oleh **Gate 1 (`CAPABILITY_INQUIRY`)** -> tidak melakukan pencarian `facts/` |
| **Retrieved Fact IDs** | `["burnin.no_watchdog_exists", "burnin.tier1_clock_drift"]` | `[]` (`0` fakta burn-in yang ditarik) |
| **Retrieval Scores** | `burnin.no_watchdog_exists = 2.5` (cocok kata `"bisa"` pada *"Mesin yang berhenti tidak **bisa** melaporkan..."*), `burnin.tier1_clock_drift = 2.5` (cocok kata `"pengembangan"` pada *"...relatif terhadap jam mesin **pengembangan**..."*) | `0.0` (Kata umum `"bisa"` & `"pengembangan"` masuk `STOPWORDS`, domain `burnin` wajib memiliki *domain trigger* eksplisit dan skor `>= 6.0`) |
| **Context Sent to Model** | Potongan mentah `Inventaris Fakta Tersegel Lapis 0 (facts/)` berisi kedua fakta `burnin.*` | Konteks kemampuan resmi NUI Persona, bahasa yang didukung, dan daftar `NUIToolRegistry` (tanpa injeksi `facts/` mentah) |
| **Final Response Source** | Fallback langkah ke-22 di `NativeNUIProvider.respond()` yang menyalin `top.excerpt` secara mentah | Handler `CAPABILITY_INQUIRY` / NUI Persona dengan penjelasan kemampuan pengembangan software secara alami & streaming bertahap |
| **Fallback Executed** | Ya — raw dump `Berdasarkan **Inventaris Fakta Tersegel Lapis 0** (facts/ (src/hijaiyyah/nui/facts.py)), - [burnin.no_watchdog_exists] ...` | Tidak ada raw dump `facts/`; menghasilkan jawaban percakapan alami yang mengalir bertahap (*streaming*) |

## 3. Perbaikan Kode Sumber yang Diterapkan

1. **Klasifikasi Intent & Mode `CAPABILITY_INQUIRY` ([`nui-desktop/backend/persona_and_context.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/persona_and_context.py))**:
   - Menambahkan fungsi `classify_capability_subintent(q_lower, q_norm)` dan mode `CAPABILITY_INQUIRY` pada `classify_response_mode()` yang mengenali 7 sub-intent kemampuan NUI:
     - `software_development_capability` (`"Kamu bisa membantu pengembangan software?"`, `"kamu bisa membantu pengembangan sofwer"`, `"buat rancangan program sofwer bis ?"`)
     - `coding_workflow_capability` (`"Bagaimana cara kamu coding?"`, `"Cara kamu coding gimana?"`)
     - `programming_languages_capability` (`"Bahasa pemrograman apa yang bisa kamu bantu?"`)
     - `python_debugging_capability` (`"Bisa memperbaiki bug Python?"`)
     - `website_development_capability` (`"Bisa membuat website?"`)
     - `repository_reading_capability` (`"Apakah kamu bisa membaca repository CosmicTera?"`)
     - `general_nui_capability` (`"Apa saja tugas kamu?"`)
2. **Filter Relevansi Ketat pada Contextual Retrieval ([`nui-desktop/backend/persona_and_context.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/persona_and_context.py))**:
   - **Gate 1 (Intent Gate)**: `NUIContextualRetriever.retrieve()` langsung mengembalikan `[]` jika mode pertanyaan adalah `CONVERSATIONAL`, `CAPABILITY_INQUIRY`, atau `SYSTEM_DIAGNOSTICS`.
   - **Gate 2 (Stopwords Kata Umum)**: Kata kerja dan kata benda percakapan umum (`bisa`, `membantu`, `pengembangan`, `software`, `sofwer`, `membaca`, `membuat`, `memperbaiki`, `rancangan`, `mesin`, `jam`, `berhenti`, `tercatat`, `berapa`) dimasukkan ke `STOPWORDS` sehingga tidak pernah mencocokkan teks narasi di dalam `facts/`.
   - **Gate 3 (Domain Trigger & Ambang Skor `>= 6.0`)**: Fakta di dalam `facts/` hanya dievaluasi apabila query memiliki kata kunci pemicu domain eksplisit (`FACT_DOMAIN_KEYWORDS`, misalnya `watchdog`, `clock drift`, `drift`, `hanyut`, `burnin`, `ppm`) dan mencapai `total_fact_score >= 6.0`.
3. **Penyusunan Respons Alami & Penghapusan Raw Fact Dump ([`nui-desktop/backend/providers.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/providers.py) & [`nui-desktop/backend/server.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/server.py))**:
   - Menangani seluruh sub-intent `CAPABILITY_INQUIRY` secara alami dengan menjelaskan kemampuan coding NUI, bahasa pemrograman yang didukung, dan tools yang terdaftar (`files.read`, `files.write`, `coding.edit`, `coding.run_test`, `web.preview`).
   - Menangani pertanyaan hardware spesifik `watchdog` (`burnin.no_watchdog_exists`) dan `clock drift` (`burnin.tier1_clock_drift`) dengan mengambil fakta Lapis 0 yang relevan dan menjelaskannya dalam kalimat teknis yang jelas (bukan dump daftar ID fakta mentah).
   - Menghubungkan `ollama_provider=self.ollama_provider` ke `NativeNUIProvider` pada [`nui-desktop/backend/server.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/server.py) dan me-restart layanan lokal `127.0.0.1:8848`.

## 4. Hasil 10 Pengujian Regresi Wajib (`test_nui_relevance_repair.py`)

Seluruh 10 skenario uji wajib telah diuji secara otomatis melalui [`nui-desktop/tests/test_nui_relevance_repair.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_relevance_repair.py):

| No | Pertanyaan Uji | Mode & Sub-Intent | Fakta `burnin.*` Ditarik? | Hasil Respons Aktual NUI | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `"Kamu bisa membantu pengembangan software?"` (dan `"kamu bisa membantu pengembangan sofwer"`) | `CAPABILITY_INQUIRY` (`software_development_capability`) | **TIDAK (`[]`)** | *"Tentu. Saya dapat membantu menganalisis source code, merancang program, menulis dan memperbaiki kode, membuat unit test, melakukan debugging, serta membantu pengembangan website dan aplikasi. Untuk pekerjaan pada repository, saya dapat menggunakan coding engine dan tools yang tersedia, memeriksa perubahan, dan menjalankan pengujian sesuai izin Anda."* | **PASS** |
| **2** | `"Bagaimana cara kamu coding?"` | `CAPABILITY_INQUIRY` (`coding_workflow_capability`) | **TIDAK (`[]`)** | Menjelaskan 3 tahap kerja coding NUI: Analisis Konteks (`files.read`, `program_index.py`), Perancangan & Penulisan Kode (`coding.edit`, `files.write`), serta Pengujian & Validasi (`pytest`, `HISAMachine`). | **PASS** |
| **3** | `"Bahasa pemrograman apa yang bisa kamu bantu?"` | `CAPABILITY_INQUIRY` (`programming_languages_capability`) | **TIDAK (`[]`)** | Menyebutkan bahasa umum (Python, Swift, C/C++, JavaScript/TypeScript, HTML/CSS, SQL, Bash/Shell) dan bahasa CosmicTera (Verilog RTL `.v`, H-ISA `.hasm`, Hybit Code `.hc`). | **PASS** |
| **4** | `"Bisa memperbaiki bug Python?"` | `CAPABILITY_INQUIRY` (`python_debugging_capability`) | **TIDAK (`[]`)** | Menjelaskan alur pelacakan traceback error, perbaikan terarah (`coding.edit`), dan verifikasi regresi dengan `pytest`. | **PASS** |
| **5** | `"Bisa membuat website?"` | `CAPABILITY_INQUIRY` (`website_development_capability`) | **TIDAK (`[]`)** | Menjelaskan kemampuan pembuatan frontend (HTML5, CSS, JavaScript/TypeScript), backend Python, dan pratinjau di Browser/Web Preview (`web.preview`). | **PASS** |
| **6** | `"Contohnya?"` (setelah pertanyaan pengembangan software) | `TECHNICAL` (`contextual_followup_example`) | **TIDAK (`[]`)** | Melanjutkan konteks pertanyaan sebelumnya dengan memberikan contoh konkret fungsi Python terverifikasi (`MASTER_TABLE` & `Six-Guard`) dan program H-ISA (`test_bsm.hasm`). | **PASS** |
| **7** | `"Apakah kamu bisa membaca repository CosmicTera?"` | `CAPABILITY_INQUIRY` (`repository_reading_capability`) | **TIDAK (`[]`)** | Menjelaskan kemampuan membaca dan menganalisis repository CosmicTera melalui `files.list`, `files.read`, `git.status`, dan indeks `L1–L2` sesuai izin `PermissionEngine`. | **PASS** |
| **8** | `"Cek sistem."` | `SYSTEM_DIAGNOSTICS` (`system_health_check`) | **TIDAK (`[]`)** | Menjalankan pemeriksaan read-only dan melaporkan status aktual `LOCAL SERVICE READY (127.0.0.1:8848)`, `PROVIDER CONNECTED`, model Ollama, memori host, dan status hardware. | **PASS** |
| **9** | `"Jelaskan watchdog pada desain CosmicTera."` | `TECHNICAL` (`hardware_burnin_watchdog`) | **YA (`burnin.no_watchdog_exists`, skor `6.5`)** | Mengambil fakta `burnin.no_watchdog_exists` (`DP`) dan menjelaskan bahwa tidak ada modul watchdog di `rtl/` karena mesin yang berhenti tidak dapat melaporkan dirinya berhenti; pemantauan dilakukan host melalui selang kebisuan dan kerja nyata per jam. | **PASS** |
| **10** | `"Berapa clock drift yang tercatat?"` | `TECHNICAL` (`hardware_burnin_clock_drift`) | **YA (`burnin.tier1_clock_drift`, skor `6.5`)** | Mengambil fakta `burnin.tier1_clock_drift` (`CC`) dan menjelaskan bahwa clock drift papan terhadap jam host yang tercatat adalah **−0,0292 detik per jam** selama 24 jam (**8,1 ppm**). | **PASS** |
