# COSMICTERA NUI — QWEN3.8-27B CODING INTEGRATION REPORT

- **Tanggal Laporan**: `2026-11-07`
- **Repositori**: [`/Users/AMRA/hijaiyyah-mathematics`](file:///Users/AMRA/hijaiyyah-mathematics)
- **Branch Pengembangan**: `feat/cosmictera-nui-desktop`
- **Modul Implementasi Utama**:
  - [`nui-desktop/backend/self_learning.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/self_learning.py) (`NUIModelAssetLibrary`, `NUIMultiModelRouter`, `measure_mac_host_resources`)
  - [`nui-desktop/backend/orchestrator.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/orchestrator.py) (`NUITaskOrchestrator`)
  - [`nui-desktop/macos/Sources/CosmicTeraNUIApp.swift`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/Sources/CosmicTeraNUIApp.swift) (`LanguageEngineSectionView`)

## 1. Spesifikasi Perangkat Keras Mac & Evaluasi Kapasitas Memori

Hasil pengukuran telemetri perangkat keras aktual melalui [`measure_mac_host_resources()`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/self_learning.py):

| Komponen Perangkat Keras | Spesifikasi Aktual Terukur | Analisis Kapasitas `Qwen3.8-27B` |
| :--- | :--- | :--- |
| **Prosesor (SoC)** | **Apple M1 Max** (`arm64`) | Mendukung akselerasi Metal GPU terpadu penuh untuk inferensi lokal |
| **Total Unified Memory** | **32.0 GiB** (`34,359,738,368` byte) | Kapasitas total mencukupi untuk bobot Q4_K_M `27B` (~`17.5–18.0 GiB`) |
| **Memori Bebas + Inactive (Reclaimable)** | **~12.72 GiB** bebas tanpa swap saat beban aplikasi aktif (`Active: 12.75 GiB`, `Wired: 3.27 GiB`) | `can_fit_total_ram = True`; memuat bobot 18 GiB akan menggunakan kompresi memori macOS / sebagian swap kecuali aplikasi berat lain ditutup atau model di-unload setelah tugas selesai |
| **Ruang Disk Bebas (`/`)** | **97.0 GiB tersedia** dari `460.0 GiB` | Sangat mencukupi untuk penyimpanan artefak model lokal (~18 GiB) |

## 2. Registrasi Model Asset `Qwen3.8-27B` di NUI Model Library

`Qwen3.8-27B` telah didaftarkan sebagai aset resmi di [`NUIModelAssetLibrary`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/self_learning.py):

- **Model Name**: `Qwen3.8-27B`
- **Display Label Resmi**: **`NUI CODING SPECIALIST — QWEN3.8-27B`**
- **Primary Tag**: `qwen3.8:27b`
- **Fallback Tag Resmi**: `qwen3.6:27b` (otomatis dipilih apabila `qwen3.8:27b` belum tersedia di repositori tag lokal)
- **Role**: `Software Engineering, Coding, Architecture, Debugging, Test Generation`
- **Controlled Persona**: `CosmicTera NUI` (`HybitAIProgram.system`)
- **Lifecycle Status**:
  - Hanya ditandai **`VERIFIED`** setelah uji inferensi nyata (`POST /api/chat` melalui `verify_model_inference()`) mengembalikan respons valid.
  - Mendukung kontrol siklus hidup penuh (`Refresh Models`, `Select Model`, `Load Model` dengan `keep_alive="15m"`, dan `Unload Model` dengan `keep_alive=0` untuk membebaskan Unified Memory).

## 3. Arsitektur Multi-Model Routing (`NUIMultiModelRouter`)

[`NUIMultiModelRouter`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/self_learning.py) mengklasifikasikan setiap permintaan pengguna dan memilih engine paling tepat tanpa kehilangan identitas NUI:

| Kategori Tugas | Engine Terpilih | Cara Kerja |
| :--- | :--- | :--- |
| **`DETERMINISTIC_COMPUTATION`** | `NUI_DETERMINISTIC_ENGINE` | Perhitungan aritmetika, nilai `BSM (112, 10, 9)`, tabel 28 huruf × 18D, Six-Guard, dan simulasi `HISAMachine` dieksekusi langsung oleh Python di `src/hijaiyyah/*` |
| **`CODING_ENGINEERING`** | `QWEN38_CODING_SPECIALIST` | Penulisan kode Python/Swift/Verilog/HTML/JS/CSS, refactoring, analisis bug, dan pembuatan unit test dirutekan ke `qwen3.8:27b` (atau `qwen3.6:27b`) di bawah kendali Persona NUI |
| **`EMBEDDING_COHERENCE`** | `NUI_L0_HMCL_EMBEDDING_ENGINE` | Pencarian konteks repositori dan koherensi tingkat lanjut menggunakan `NUIContextualRetriever` dan modul `src/hijaiyyah/hmcl/*` |
| **`GENERAL_AND_PROJECT_REASONING`** | `OLLAMA_WITH_NUI_PERSONA` | Percakapan umum dan penjelasan proyek menggunakan model lokal Ollama dengan injeksi 9-lapis System Prompt NUI |

## 4. Hasil Verifikasi & Pengujian Coding

Di dalam [`test_nui_ollama_qwen_self_learning.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_ollama_qwen_self_learning.py), alur kerja `QWEN38_CODING_SPECIALIST` telah diuji penuh:

1. **Klasifikasi & Routing Otomatis**: Permintaan `"Buatkan fungsi Python sederhana untuk menghitung faktor bilangan"` secara otomatis diklasifikasikan sebagai `CODING_ENGINEERING` dan diarahkan ke `QWEN38_CODING_SPECIALIST` (`qwen3.8:27b`).
2. **Siklus Hidup Memori**: Operasi `select`, `verify` (`status == "VERIFIED"`), `load` (`status == "READY"`), dan `unload` (`status == "UNLOADED"`) berjalan mulus melalui `POST /api/models/op`.
3. **Verifikasi Eksekusi Kode (`pytest`)**: Kode yang dihasilkan untuk ketrampilan baru (`gcd_euclid_skill`) diuji otomatis dengan `pytest` di sandbox terisolasi sebelum disimpan sebagai ketrampilan tervalidasi.
