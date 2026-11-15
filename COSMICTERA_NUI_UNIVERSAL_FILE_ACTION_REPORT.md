# COSMICTERA NUI — UNIVERSAL FILE & FOLDER ACTION INTELLIGENCE REPORT

**Tanggal Verifikasi**: 9 November 2026  
**Aplikasi Target**: `CosmicTera NUI Desktop` (`nui-desktop/macos/build/CosmicTera NUI.app`)  
**Modul Inti**: `nui-desktop/backend/universal_file_intelligence.py`  
**Berkas Uji Penerimaan**: `nui-desktop/tests/test_nui_universal_file_actions.py` (**18 / 18 PASSED**)  
**Status Uji Gabungan (`test_nui_universal_file_actions.py` + `test_nui_chat_clipboard_ux.py` + `test_nui_phase12_internet_remote.py`)**: **56 / 56 PASSED**  

## 1. Universal Resource Registry (`UniversalResourceRegistry`)

`UniversalResourceRegistry` di `nui-desktop/backend/universal_file_intelligence.py` mengelola ke-8 tipe sumber daya universal secara terpadu:

- `CHAT_ATTACHMENT` (berkas yang dilampirkan langsung pada pesan chat, baik melalui path lokal maupun referensi non-path `attachment://...` + payload bytes/base64/teks)
- `UPLOADED_FOLDER` (folder yang diunggah langsung atau hasil ekstraksi otomatis arsip `.zip` ke direktori staging terisolasi)
- `CONNECTED_LOCAL_FOLDER` (folder lokal yang dihubungkan pengguna dengan cakupan izin `READ_ONLY` atau `READ_WRITE`, seperti `/Users/AMRA/yayasan`, `/Users/AMRA/hijaiyyah-mathematics`, dan `/Users/AMRA/opt`)
- `LOCAL_WORKSPACE` (workspace aktif proyek)
- `GIT_REPOSITORY` (repositori Git lokal)
- `REMOTE_VPS_FOLDER` (direktori pada server VPS jarak jauh)
- `REMOTE_WORKSPACE` (workspace SSH/SFTP yang terhubung pada VPS)
- `GENERATED_FILE` (berkas hasil olahan/generasi NUI yang telah diverifikasi keberadaannya di disk beserta checksum SHA-256)

Setiap `UniversalResourceRecord` menyimpan 10 atribut wajib: `resource_id`, `source_type`, `name`, `canonical_path_or_reference`, `mime_type`, `size_bytes`, `permission_scope`, `availability`, `source_provenance`, serta `created_at` dan `accessed_at`.

## 2. Contextual Resource Resolution (`ContextualResourceResolver`)

Ketika pengguna memberikan instruksi natural di chat seperti *"Periksa file ini"*, *"Buka folder yang tadi saya unggah"*, *"Gabungkan semua laporan ini menjadi satu PDF"*, *"Buatkan laporan dari semua file Excel"*, *"Buat infografik berdasarkan dokumen tersebut"*, atau *"Upload folder ini ke VPS"*, `ContextualResourceResolver` menyelesaikan rujukan objek secara deterministik berdasarkan 7 tingkat prioritas:

1. **Tier 1 (`CURRENT_MESSAGE_ATTACHMENT`)**: Lampiran pada pesan saat ini.
2. **Tier 2 (`SESSION_PREVIOUS_ATTACHMENT`)**: Lampiran atau berkas hasil (`GENERATED_FILE`) pada giliran percakapan sebelumnya di sesi yang sama (`session_id`).
3. **Tier 3 (`UPLOADED_FOLDER`)**: Folder yang diunggah atau diekstrak dari arsip ZIP ke staging.
4. **Tier 4 (`CONNECTED_LOCAL_FOLDER`)**: Folder lokal yang terhubung aktif (`Connected Folders`).
5. **Tier 5 (`LOCAL_WORKSPACE`)**: Workspace lokal aktif.
6. **Tier 6 (`GIT_REPOSITORY`)**: Repositori Git lokal.
7. **Tier 7 (`REMOTE_WORKSPACE`)**: Workspace remote VPS yang telah terhubung.

Apabila terdapat beberapa sumber daya dengan nama serupa pada tingkat prioritas yang sama dan tidak dapat dibedakan dari konteks sesi, resolver mengembalikan status `AMBIGUOUS_RESOURCE` (`needs_clarification = True`) beserta satu pertanyaan klarifikasi spesifik yang mencantumkan ID dan lokasi kandidat.

## 3. Universal File Operations & 7 Adapter Terpadu (`UniversalFileActionEngine`)

Sesuai Bagian 3 dan Bagian 7 spesifikasi, ketujuh adapter terpadu telah diimplementasikan dan dihubungkan ke `NUITaskOrchestrator`, `NativeNUIProvider`, `OllamaProvider`, dan `NUILocalServiceApp` (`/api/resources` & `/api/resources/op`):

| Adapter Terpadu | Kelas / Komponen Implementasi | Cakupan Fungsi |
| :--- | :--- | :--- |
| `AttachmentResolver` | `ContextualResourceResolver` | Resolusi lampiran pesan aktif, riwayat lampiran sesi, dan referensi `attachment://...` |
| `FolderResourceManager` | `UniversalResourceRegistry` | Sinkronisasi Connected Folders, Uploaded Folders, Local Workspace, Git Repo, dan Remote VPS |
| `FileOperationEngine` | `UniversalFileActionEngine` | List/traverse direktori bertingkat, baca, cari isi lintas berkas, buat, edit (copy-on-edit), ganti nama, salin, pindah, hapus |
| `DocumentProcessingEngine` | `UniversalDocumentIntelligence` | Ekstraksi teks/tabel/slide/metadata, perbandingan dokumen (`unified_diff`), agregasi numerik Excel/CSV |
| `ArchiveManager` | `ArchiveManager` | Inspeksi manifest `.zip`/`.tar`/`.tgz`, blokir *path traversal* & symlink, ekstraksi ke staging aman, pembuatan paket `.zip` |
| `OutputManager` | `UniversalFileActionEngine` | Penggabungan dokumen menjadi `.pdf`, pembuatan laporan `.md`/`.pdf`, pembuatan infografik visual `.svg`, verifikasi fisik SHA-256 |
| `RemoteFileAdapter` | `UniversalFileActionEngine` + `RemoteVPSDevelopmentEngine` | Transfer berkas/folder ke VPS setelah verifikasi sesi SSH `CONNECTED`, fingerprint `SHA256:...`, dan izin `VPS_WRITE` |

## 4. Universal Document Intelligence (18 Format Didukung)

`UniversalDocumentIntelligence` mendukung pembacaan, ekstraksi struktur, pencarian lintas berkas, perbandingan versi, dan pembuatan laporan untuk ke-18 kategori format:

- **Dokumen & Perkantoran**: `PDF` (`.pdf`), `DOCX` (`.docx`), `XLSX` (`.xlsx`), `PPTX` (`.pptx`), `TXT` (`.txt`), `Markdown` (`.md`), `CSV` (`.csv`), `JSON` (`.json`), `XML` (`.xml`).
- **Kode Sumber & Bahasa Komputasi CosmicTera**: `Python` (`.py` dengan analisis AST fungsi/kelas), `Swift` (`.swift`), `C/C++` (`.c`, `.cpp`, `.h`), `Verilog/SystemVerilog` (`.v`, `.sv`), `H-ISA Assembly` (`.hasm`), `Hijaiyyah-C` (`.hc`), serta `HTML/CSS/JavaScript` (`.html`, `.css`, `.js`, `.ts`).
- **Citra & Arsip**: `PNG/JPG/WebP` (`.png`, `.jpg`, `.jpeg`, `.webp` dengan ekstraksi dimensi piksel & SHA-256) serta `ZIP/TAR` (`.zip`, `.tar`, `.tar.gz`, `.tgz`).
- **Pelaporan Jujur Format Tidak Didukung**: Berkas biner yang tidak didukung (misalnya `.dmg`, `.exe`, `.iso`) dilaporkan secara eksplisit dengan status `UNSUPPORTED_FORMAT` beserta daftar format yang didukung.

## 5. Alur Eksekusi Langsung 9 Tahap dari Chat & Model Izin (Section 5, 6, 8)

Setiap perintah kerja berkas/folder di chat mengeksekusi 9 tahapan:
`UNDERSTAND_REQUEST` -> `RESOLVE_RESOURCE` -> `INSPECT_RESOURCE` -> `PLAN_OPERATION` -> `CHECK_PERMISSION` -> `EXECUTE_OPERATION` -> `VERIFY_OUTPUT` -> `SAVE_RESULT` -> `RETURN_RESULT_TO_CHAT`.

Aturan izin berdasarkan sumber ditegakkan secara ketat oleh backend:
- **`CHAT_ATTACHMENT`**: Ketika diedit (`edit_resource_file`), NUI **tidak pernah menimpa berkas asli** pengguna tanpa izin eksplisit; NUI membuat salinan hasil baru di direktori output (`EDITED_AS_NEW_COPY`) dan memverifikasi SHA-256 berkas asli tetap identik byte-demi-byte.
- **`UPLOADED_FOLDER`**: Akses dibatasi ketat hanya di dalam direktori staging folder yang diunggah.
- **`CONNECTED_LOCAL_FOLDER`**: Menghormati mode `READ_ONLY` (menolak penulisan/pengeditan dengan `FOLDER_READ_ONLY_DENIED`), mengizinkan penulisan pada folder `READ_WRITE`, serta menolak akses ke folder yang berada di luar daftar izin (`PATH_OUTSIDE_AUTHORIZED_RESOURCES`) atau yang telah diputuskan (`DISCONNECTED_FOLDER_DENIED`).
- **`REMOTE_VPS`**: Transfer berkas/folder ke VPS (`transfer_resource_to_vps`) ditolak apabila profil VPS belum dikonfigurasi (`VPS_NOT_CONFIGURED`) atau belum terhubung dengan fingerprint host `SHA256:...` terverifikasi (`VPS_NOT_CONNECTED_OR_UNVERIFIED`).
- **`GENERATED_FILE` & Pengiriman Hasil di Chat**: Setiap hasil eksekusi menampilkan tabel laporan terstruktur di NUI Chat (apa yang dikerjakan, file sumber, file yang dibuat/diubah dengan tautan `file://`, lokasi output, jumlah file yang diproses, hasil validasi SHA-256, dan file yang dilewati) serta menyediakan tombol aksi **`Copy`**, **`Open`**, dan **`Reveal in Finder`** pada UI macOS `CosmicTera NUI.app`.

## 6. Hasil Pengujian Penerimaan (`test_nui_universal_file_actions.py` — 18 / 18 PASSED)

Pengujian dipisahkan secara eksplisit ke dalam 4 kategori (`UNIT`, `MOCK`, `INTEGRATION`, dan `LIVE FILESYSTEM TEST`):

| No | Nama Pengujian | Kategori Uji | Skenario yang Diverifikasi | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `test_01_unit_read_pdf_attachment` | `UNIT` | Membaca lampiran PDF via referensi `attachment://...` & ekstraksi teks multi-halaman | **PASSED** |
| 2 | `test_02_unit_read_docx` | `UNIT` | Membaca paragraf dan tabel dari dokumen `.docx` | **PASSED** |
| 3 | `test_03_unit_process_xlsx` | `UNIT` | Memproses workbook `.xlsx` dan menghitung agregasi numerik kolom (`sum`, `mean`, `min`, `max`) | **PASSED** |
| 4 | `test_04_unit_read_pptx` | `UNIT` | Membaca judul slide dan poin-poin presentasi `.pptx` | **PASSED** |
| 5 | `test_05_unit_read_source_code_and_unsupported_format` | `UNIT` | Membaca kode `.py` (AST) & `.hasm` serta menolak format `.dmg` dengan `UNSUPPORTED_FORMAT` | **PASSED** |
| 6 | `test_06_live_fs_process_uploaded_zip_to_staging` | `LIVE FILESYSTEM` | Mengekstrak arsip `.zip` secara aman ke staging dan mendaftarkannya sebagai `UPLOADED_FOLDER` | **PASSED** |
| 7 | `test_07_live_fs_traverse_nested_directories` | `LIVE FILESYSTEM` | Menelusuri struktur direktori bertingkat (`bab1/sub_a`, `bab2/sub_b`) secara rekursif | **PASSED** |
| 8 | `test_08_live_fs_search_content_across_files` | `LIVE FILESYSTEM` | Mencari isi `"Matematika Hijaiyyah"` lintas berkas `.md`, `.docx`, dan `.txt` | **PASSED** |
| 9 | `test_09_live_fs_compare_documents` | `LIVE FILESYSTEM` | Membandingkan dua versi dokumen dan menghasilkan `unified_diff` serta rasio kemiripan | **PASSED** |
| 10 | `test_10_live_fs_create_output_file_and_pdf_merge` | `LIVE FILESYSTEM` | Menggabungkan beberapa dokumen menjadi satu berkas `.pdf` valid dan memverifikasi hasilnya di disk | **PASSED** |
| 11 | `test_11_live_fs_preserve_original_attachment_on_edit` | `LIVE FILESYSTEM` | Memastikan pengeditan `CHAT_ATTACHMENT` membuat salinan baru tanpa menimpa berkas asli | **PASSED** |
| 12 | `test_12_live_fs_deny_folder_outside_permissions` | `LIVE FILESYSTEM` | Menolak akses pada folder di luar Connected Folders & Uploaded Folders (`PATH_OUTSIDE_AUTHORIZED_RESOURCES`) | **PASSED** |
| 13 | `test_13_live_fs_respect_read_only_folder` | `LIVE FILESYSTEM` | Mengizinkan baca tetapi menolak penulisan pada Connected Folder `READ_ONLY` (`FOLDER_READ_ONLY_DENIED`) | **PASSED** |
| 14 | `test_14_live_fs_use_read_write_folder` | `LIVE FILESYSTEM` | Mengizinkan pembacaan dan pengeditan pada Connected Folder `READ_WRITE` | **PASSED** |
| 15 | `test_15_integration_chat_output_accessible_with_ui_actions` | `INTEGRATION` | Menghasilkan laporan dari berkas Excel langsung melalui chat lengkap dengan aksi `Copy`, `Open`, `Reveal in Finder` | **PASSED** |
| 16 | `test_16_integration_process_multiple_attachments_in_one_job` | `INTEGRATION` | Memproses 3 lampiran berbeda (`.docx`, `.md`, `.txt`) sekaligus menjadi satu berkas PDF | **PASSED** |
| 17 | `test_17_integration_retain_resource_context_on_followup` | `INTEGRATION` | Mempertahankan konteks berkas pada giliran follow-up (*"Buat infografik berdasarkan dokumen tersebut"*) tanpa lampiran ulang | **PASSED** |
| 18 | `test_18_mock_vps_transfer_only_after_verified_connection` | `MOCK` | Menolak transfer ke VPS saat belum terhubung, dan mengizinkan transfer hanya setelah SSH + fingerprint `SHA256` + `VPS_WRITE` terverifikasi | **PASSED** |

## 7. Kepatuhan Perlindungan Inti

- **43 Modul Kanonik NUI L0–L11 (`src/hijaiyyah/nui/*.py`)**: Tidak disentuh (`0` perubahan).
- **Artefak Freeze `NUI/` (`NUI_MANIFEST.json`, `NUI_FREEZE_CERTIFICATE.md`, `NUI_CHECKSUMS.sha256`)**: Tidak disentuh (`0` perubahan).
- **4 Berkas HDMI FPGA Tang Nano 20K**: Tidak disentuh oleh perubahan ini.
- **Tidak Ada Integrasi Jev AI**: Sepenuhnya mandiri di dalam arsitektur lokal CosmicTera NUI.
