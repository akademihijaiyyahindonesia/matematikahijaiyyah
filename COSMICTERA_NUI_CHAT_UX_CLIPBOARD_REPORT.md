# COSMICTERA NUI — CHAT EXPERIENCE, NATIVE CLIPBOARD INTEGRATION & VPS FOLDER STATUS REPORT

**Tanggal Verifikasi**: 9 November 2026  
**Aplikasi Target**: `CosmicTera NUI Desktop` (`nui-desktop/macos/build/CosmicTera NUI.app`)  
**Berkas Uji Penerimaan**: `nui-desktop/tests/test_nui_chat_clipboard_ux.py` (**16 / 16 PASSED**)  
**Status Kompilasi Native macOS**: **PASSED (`swiftc` arm64-apple-macos14.0, exit code 0)**  

## 1. User Message Component (`NUIChatSectionView` — Right-Aligned Bubble)

Komponen pesan pengguna di `nui-desktop/macos/Sources/CosmicTeraNUIApp.swift` telah ditingkatkan menjadi *right-aligned chat bubble* (`HStack(alignment: .top) { Spacer(minLength: 75); VStack(alignment: .trailing, spacing: 7) { ... } }`) dengan kemampuan lengkap:

- **Seleksi Teks Penuh & Sebagian**: Seluruh teks dan blok kode di dalam gelembung pertanyaan pengguna menggunakan `.textSelection(.enabled)` pada `RichMarkdownAndCodeView`.
- **Tombol `Salin pertanyaan` (`Copy`)**: Menyalin teks murni pertanyaan pengguna (tanpa footer lampiran UI) langsung ke `NSPasteboard.general` melalui `NUIClipboardManager.shared.copyUserMessage(...)` dan menampilkan indikator visual `Copied ✓ · Tersalin` pada gelembung pesan serta banner konfirmasi di header chat.
- **Dukungan Prompt Panjang & Multibaris**: Mendukung teks panjang, potongan kode multibaris, huruf Hijaiyyah Arab (`ا ب ت ث ج ح خ ...`), serta ekspresi Matematika Hijaiyyah (`||BSM||² = 112`) tanpa pemotongan.
- **Edit Inline & Kirim Ulang (`Edit` & `Resend`)**:
  - Klik **`Edit`** membuka editor multibaris langsung di dalam gelembung pesan (`TextEditor` dengan tombol **Simpan & Kirim Ulang (Resend)** dan **Batal**).
  - Saat dikirim ulang (`submitEditedUserMessage`), backend `NUIStorage.prune_for_edit_and_resend` dan `NUITaskOrchestrator.edit_and_resend_chat_turn` memangkas giliran percakapan lama setelah pesan tersebut dan menghasilkan jawaban baru yang bersih tanpa duplikasi riwayat.

## 2. Assistant Message Component (`NUIChatSectionView` — Left-Aligned Card)

Komponen jawaban NUI dirancang sebagai kartu pesan di sisi kiri (`HStack(alignment: .top) { VStack(alignment: .leading, spacing: 9) { ... }; Spacer(minLength: 35) }`) dengan fitur:

- **Header & Footer Aksi Lengkap**: Menampilkan identitas `COSMICTERA NUI (provider · model)`, waktu respons (`ms`), status eksekusi, serta tombol aksi di bagian atas dan bawah kartu (`Copy`, `Regenerate`, dan menu `Feedback` `👍` / `👎`).
- **Penyalinan Jawaban Penuh (`Copy Full Response`)**: Tombol **`Copy`** memanggil `store.copyAssistantFullAnswer(msg)` yang menyalin **seluruh isi `msg.content`** dari model data (`NUIDesktopStore.messages`), bukan hanya teks yang tampak di *viewport* scroll saat ini (terbukti pada pengujian `test_02_copy_full_assistant_response_native_pasteboard` dengan 5.242 karakter tersalin utuh).
- **Streaming Inkremental & Smart Auto-Scroll**: Menampilkan tahapan berpikir (`liveThinkingStage`), aktivitas tool secara real-time, serta pembaruan teks streaming tanpa memaksa scroll ke bawah apabila pengguna sedang membaca pesan di bagian atas (`userScrolledUp == true`).

## 3. Code Block Component & Copy-Only-Code (`CodeBlockCardView`)

Setiap blok kode berpagar Markdown (` ```lang ... ``` `) dirender menggunakan komponen khusus `CodeBlockCardView`:

- **Header Blok Kode**: Menampilkan lencana bahasa terformat (`PYTHON`, `SWIFT`, `BASH / SHELL`, `VERILOG / RTL`, `H-ISA ASM`, `SQL`, `JSON`, `HTML`, `CSS`), jumlah baris kode, tombol **`Buka di Studio`**, dan tombol **`Copy Code`**.
- **Penyalinan Kode Murni (`Copy Code Only`)**: Menekan **`Copy Code`** memanggil `store.copyRawCodeBlock(code: codeBody, blockId: blockId)` -> `NUIClipboardManager.shared.copyCodeBlockOnly(rawCode)` yang menyalin **hanya isi kode murni** ke `NSPasteboard.general` tanpa pagar Markdown (`` ``` ``), tanpa label bahasa, dan tanpa teks penjelasan di sekitarnya.
- **Preservasi Indentasi & Karakter Khusus**: Menggunakan font monospaced dengan `ScrollView(.horizontal)` dan `.textSelection(.enabled)` sehingga spasi, tab (`\t`), baris baru (`\n`), komentar Arab/Hijaiyyah, dan simbol matematika tetap utuh byte-demi-byte.

## 4. Markdown, Table, Formula & Link Rendering (`RichMarkdownAndCodeView` & `MarkdownProseSegmentView`)

Jawaban NUI tidak lagi ditampilkan sebagai satu blok teks mentah tunggal, melainkan diurai secara struktural oleh `MarkdownProseSegmentView.parseBlocks(_:)` menjadi:

- **Heading Hirarkis (`#`, `##`, `###`)**: Dirender dengan ukuran tipografi dan aksen warna `CosmicTheme.cyan` / `CosmicTheme.gold`.
- **Tabel Responsif (`MarkdownTableBlockView`)**: Mengurai tabel Markdown berformat pipa (`| Kolom 1 | Kolom 2 |`) menjadi tabel visual dengan baris header tebal, latar baris berselang-seling, dan seleksi teks per sel.
- **Daftar Bullet & Bernomor (`bulletList`, `numberedList`)**: Merender daftar berpoin (`-`, `*`, `•`) dan bernomor (`1.`, `2.`) dengan perataan indentasi yang rapi.
- **Blockquote (`>`) & Callout Rumus Matematika Hijaiyyah (`formulaCallout`)**: Merender kutipan dengan garis aksen emas serta menampilkan ekspresi matematika seperti `||BSM||² = 112` dan `H_c = 13.714285714285714` di dalam kotak rumus monospaced beraksen zamrud.

## 5. Chat Composer (`ChatComposerTextView` & `NUIComposerNSTextView`)

Area input pesan dibangun menggunakan komponen AppKit native `NUIComposerNSTextView` (`NSTextView` di dalam `NSScrollView` melalui `NSViewRepresentable`):

- **Multiline Auto-Resizing**: Tinggi kotak input menyesuaikan jumlah baris secara otomatis (`ChatComposerTextView.calculatedHeight(for:)` dari `40pt` hingga `132pt`).
- **Penanganan Tombol Keyboard Standar Chat AI Modern**:
  - **`Enter`** (tanpa `Shift`): Langsung mengirim pesan (`onEnterSend`).
  - **`Shift + Enter`**: Menyisipkan baris baru (`\n`) di dalam composer tanpa mengirim pesan.
- **Dukungan Tempel (`Cmd+V` & Tombol `Paste`)**: Menonaktifkan substitusi kutipan/tanda hubung otomatis (`isAutomaticQuoteSubstitutionEnabled = false`, `isAutomaticDashSubstitutionEnabled = false`) sehingga kode program, indentasi tab, huruf Hijaiyyah Arab, dan rumus matematika yang ditempel tetap persis seperti aslinya.
- **Kontrol Lengkap & Indikator Token**: Dilengkapi tombol **`+`** (menu lampiran & pemeriksaan cepat), **`Folder`**, **`Paste`**, **`Kirim`** / **`Stop`**, penghitung karakter/token/baris secara langsung (`karakter · ~token · baris`), serta penyimpanan draft otomatis per sesi (`sessionDrafts` & endpoint `/api/chat/op` `save_draft` / `get_draft`) yang bertahan saat berpindah menu sidebar maupun berpindah sesi.

## 6. Native macOS `NSPasteboard` Integration (`NUIClipboardManager`)

Integrasi papan klip menggunakan `NSPasteboard.general` native macOS di dalam `NUIClipboardManager`:

| Operasi Clipboard | Metode `NUIClipboardManager` / `NUIDesktopStore` | Perilaku & Verifikasi |
| :--- | :--- | :--- |
| Salin pertanyaan pengguna | `copyUserQuestion(_:)` -> `copyUserMessage(_:)` | Membersihkan catatan lampiran UI lalu menulis teks pertanyaan ke `NSPasteboard.general` |
| Salin jawaban lengkap NUI | `copyAssistantFullAnswer(_:)` -> `copyAssistantResponse(_:)` | Menulis seluruh `msg.content` dari store ke `NSPasteboard.general` tanpa terpotong scroll |
| Salin blok kode saja | `copyRawCodeBlock(code:blockId:)` -> `copyCodeBlockOnly(_:)` | Menulis hanya isi kode di dalam blok tanpa pagar Markdown atau narasi |
| Tempel ke composer (`Cmd+V`) | `NUIComposerNSTextView.paste(_:)` & `pasteFromClipboardIntoComposer()` | Membaca `NSPasteboard.general.string(forType: .string)` dan mempertahankan Unicode, Arab Hijaiyyah, tab, dan baris baru |

## 7. Edit, Resend, Regenerate, Feedback & Stop Generation Flow

Alur interaksi percakapan terhubung penuh antara UI Swift (`NUIDesktopStore`) dan layanan lokal Python (`NUITaskOrchestrator` & `NUIStorage`):

- **`Edit & Resend` (`/api/chat/op` `op="edit_and_resend"`)**: Memanggil `storage.prune_for_edit_and_resend(session_id, target_message_id)` untuk menghapus pesan lama beserta respons setelahnya, lalu menjalankan giliran baru dengan teks yang telah diedit.
- **`Regenerate` (`/api/chat/op` `op="regenerate"`)**: Memanggil `storage.pop_last_assistant_for_regenerate(session_id, assistant_message_id)` untuk menghapus jawaban asisten terakhir dan menghasilkan ulang respons baru dari prompt pengguna yang sama tanpa mengotori riwayat sesi.
- **`Feedback` (`/api/chat/op` `op="feedback"`)**: Menyimpan penilaian pengguna (`POSITIVE` / `NEGATIVE` beserta catatan) ke dalam metadata pesan di SQLite dan meneruskannya ke `NUIAutonomousSelfLearningEngine`.
- **`Stop Generation` (`/api/chat/stop`)**: Menghentikan streaming aktif secara instan melalui `orchestrator.stop_chat_generation(request_id, session_id)` dan mengubah status menjadi `STOPPED` (`UI READY`).

## 8. VPS & Connected Folder Status Accuracy (`/Users/AMRA/yayasan`)

Untuk memastikan NUI **tidak pernah** menyimpulkan koneksi atau sinkronisasi VPS hanya dari daftar *Connected Folders* (`READ_WRITE`), keberadaan `.git` lokal, atau berkas `DEPLOY.md`, modul `RemoteVPSDevelopmentEngine.inspect_folder_vps_status` (`nui-desktop/backend/remote_dev_engine.py`) memeriksa ke-9 parameter wajib secara nyata:

| Parameter Wajib | Hasil Pemeriksaan Aktual untuk `/Users/AMRA/yayasan` |
| :--- | :--- |
| `connected_folder_id` | `fld-...` (`READ_WRITE`, terdaftar di Connected Folders lokal) |
| `local_canonical_path` | `/Users/AMRA/yayasan` |
| `remote_ssh_profile` | `NONE (Belum ada profil SSH yang dikonfigurasi untuk folder ini)` |
| `ssh_connection_status` | `NOT_CONFIGURED` |
| `verified_host_fingerprint` | `NONE (Belum ada host fingerprint SHA256 yang diverifikasi)` |
| `sftp_connection` | `NOT_CONFIGURED` |
| `remote_workspace_path` | `NONE` |
| `mount_status` | `LOCAL_FILESYSTEM (APFS on /System/Volumes/Data, tidak ada mount SSHFS/FUSE/remote aktif)` |
| `last_successful_remote_verification` | `NEVER (Belum ada verifikasi remote yang berhasil)` |
| **Klasifikasi Status Akhir** | **`LOCAL_ONLY`** (VPS: `NOT_CONFIGURED`, `inferred_from_git_or_connected_folder = False`) |

Ketika profil SSH didaftarkan tetapi belum terhubung, status dilaporkan secara jujur sebagai **`DISCONNECTED`**. Ketika sesi SSH terhubung dengan verifikasi fingerprint `SHA256:...` dan SFTP aktif, status menjadi **`REMOTE_CONNECTED`**. Ketika tabel `/sbin/mount` OS membuktikan mount `sshfs`/`osxfuse`/`nfs`, status menjadi **`REMOTE_MOUNTED`**. Status **`SYNCED`** hanya diberikan apabila mekanisme sinkronisasi dan bukti verifikasi sinkronisasi tersedia secara eksplisit.

## 9. Hasil Pengujian Penerimaan (`test_nui_chat_clipboard_ux.py`)

Seluruh **16 pengujian** pada `nui-desktop/tests/test_nui_chat_clipboard_ux.py` dan **22 pengujian** regresi Phase 12 pada `nui-desktop/tests/test_nui_phase12_internet_remote.py` lulus **100% (38 / 38 PASSED)**:

1. `test_01_copy_user_message_native_pasteboard`: **PASSED**
2. `test_02_copy_full_assistant_response_native_pasteboard`: **PASSED** (`5242` karakter jawaban lengkap tersalin utuh)
3. `test_03_copy_code_block_only_without_fences_or_explanation`: **PASSED**
4. `test_04_select_partial_text_and_rich_markdown_rendering`: **PASSED**
5. `test_05_paste_multiline_text_into_composer`: **PASSED**
6. `test_06_paste_code_block_into_composer_preserves_indentation`: **PASSED**
7. `test_07_paste_arabic_hijaiyyah_and_mathematical_expressions`: **PASSED**
8. `test_08_enter_key_sends_message`: **PASSED**
9. `test_09_shift_enter_creates_newline_without_sending`: **PASSED**
10. `test_10_edit_and_resend_user_message`: **PASSED**
11. `test_11_regenerate_assistant_response`: **PASSED**
12. `test_12_stop_streaming_response`: **PASSED**
13. `test_13_draft_text_survives_switching_menus_and_sessions`: **PASSED**
14. `test_14_conversation_history_loads_without_contaminating_new_session`: **PASSED**
15. `test_15_folder_status_never_claims_vps_from_git_or_connected_folder`: **PASSED**
16. `test_16_http_server_chat_op_and_vps_folder_inspection_endpoints`: **PASSED**

## 10. Kepatuhan Perlindungan Inti & Batasan

- **43 Modul Kanonik NUI L0–L11 (`src/hijaiyyah/nui/*.py`)**: Tidak disentuh (`0` perubahan).
- **Artefak Freeze `NUI/` (`NUI_MANIFEST.json`, `NUI_FREEZE_CERTIFICATE.md`, `NUI_CHECKSUMS.sha256`)**: Tidak disentuh (`0` perubahan).
- **4 Berkas HDMI FPGA Tang Nano 20K**: Tidak disentuh oleh perubahan ini.
- **Larangan Integrasi Eksternal**: Tidak ada integrasi Jev AI maupun perintah Git destruktif.
