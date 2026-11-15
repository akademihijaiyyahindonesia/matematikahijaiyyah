# LAPORAN CODING STUDIO, WEB BUILDER & PENGELOLAAN BERKAS (`COSMICTERA_NUI_CODING_STUDIO_REPORT.md`)

- **Modul Implementasi**: [`nui-desktop/backend/tools.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/tools.py) dan [`nui-desktop/macos/Sources/CosmicTeraNUIApp.swift`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/Sources/CosmicTeraNUIApp.swift)
- **Suite Verifikasi**: [`nui-desktop/tests/test_nui_desktop_full.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_desktop_full.py) (`test_file_management_coding_studio_and_knowledge_buckets`)

## 1. Kemampuan Coding Studio & Bahasa yang Didukung

**CosmicTera Coding Studio** mendukung siklus pengembangan perangkat lunak dan perangkat keras secara lokal:
- **Bahasa Ekosistem CosmicTera**: Hybit Code (`.hc`), H-ISA Assembly (`.hasm`), H-ISA Bytecode (`.hbc`), dan RTL Verilog/SystemVerilog (`.v`, `.sv`).
- **Bahasa Aplikasi & Web**: Python (`.py`), Swift (`.swift`), HTML/CSS/JavaScript/TypeScript, Shell script (`.sh`), JSON, YAML, TOML, SQL, dan Markdown (`.md`).
- **Alat Rekayasa Terintegrasi**:
  - `coding.edit`: Mengubah blok kode secara presisi dengan pembuatan salinan cadangan otomatis (`.bak`) di `.nui_trash` sebelum penulisan.
  - `coding.run_tests`: Menjalankan suite `pytest` langsung dari antarmuka desktop dan mengembalikan kode keluar serta ringkasan stdout/stderr.
  - `git.status` & `git.diff`: Memeriksa branch aktif, 5 commit terakhir, berkas yang dimodifikasi, dan diff statistik tanpa mengubah baseline terkunci.

## 2. Website Creation, Editing & Local Preview (`coding.scaffold_website`)

- Alat `coding.scaffold_website` membangun struktur proyek website lengkap (`index.html`, `styles.css`, `app.js`) menggunakan palet identitas **CosmicTera** (`#060C16` Deep Cosmic Navy, `#30D070` Emerald Green, `#F0C860` Metallic Gold, `#30C0D0` Cyan).
- Pratinjau lokal dapat dibuka secara instan di dalam tab **Browser** (`IsolatedWebView`), sedangkan publikasi ke produksi (`deploy.publish`) dikunci oleh gerbang izin `DEPLOYMENT_FINAL_GATE` yang selalu mewajibkan konfirmasi final terpisah dari pengguna.

## 3. Pengelolaan Berkas Aman & Pemisahan Knowledge Base (`Section 9`)

- **Otorisasi Folder Eksplisit (`authorized_folders`)**: Aplikasi hanya dapat membaca atau menulis pada folder yang telah didaftarkan pengguna (`READ_ONLY` atau `READ_WRITE`).
- **Penghapusan Aman (`.nui_trash`)**: Operasi `files.delete` selalu meminta konfirmasi pengguna (`WAITING_FOR_APPROVAL`) dan memindahkan berkas ke direktori cadangan `.nui_trash/<filename>.<timestamp>.deleted` sehingga tidak ada kehilangan data permanen tanpa sengaja.
- **Pemisahan Tiga Bucket Knowledge Base (`knowledge_items`)**:
  1. `conversation_memory`: Catatan konteks percakapan pengguna.
  2. `reference_docs`: Dokumentasi referensi teknis (`H-ISA`, `MASTER_TABLE`, spesifikasi).
  3. `project_knowledge`: Pengetahuan arsitektur dan status berkas proyek aktif.
