# MODEL OTORISASI & KEAMANAN: COSMICTERA NUI DESKTOP (`COSMICTERA_NUI_PERMISSION_MODEL.md`)

- **Modul Implementasi**: [`nui-desktop/backend/permissions.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/permissions.py) dan [`nui-desktop/backend/storage.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/storage.py)
- **Suite Verifikasi**: [`nui-desktop/tests/test_nui_desktop_full.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_desktop_full.py) (`test_15_permission_categories_and_6_approval_modes`, `test_secret_redaction_in_audit_logs`)

## 1. Lima Belas Kategori Izin (`PERMISSION_CATEGORIES`)

Setiap aksi alat di dalam `NUIToolRegistry` wajib melewati evaluasi `PermissionEngine.check_or_request()` pada salah satu dari 15 kategori berikut:

| No | Kode Kategori | Label UI | Tingkat Risiko Default | Cakupan Pengendalian |
|---|---|---|---|---|
| 1 | `INTERNET_ACCESS` | Internet Access | `MEDIUM` | Koneksi keluar jaringan eksternal. |
| 2 | `WEB_SEARCH` | Web Search | `LOW` | Pencarian kueri melalui mesin pencari / dokumentasi. |
| 3 | `WEB_READING` | Web Reading | `LOW` | Pembacaan isi halaman web publik per domain. |
| 4 | `BROWSER_AUTOMATION` | Browser Automation | `HIGH` | Navigasi, klik elemen, dan interaksi DOM pada browser terintegrasi. |
| 5 | `WEB_CODING` | Web Coding | `MEDIUM` | Pembuatan dan pengeditan proyek website lokal. |
| 6 | `API_ACCESS` | API Access | `HIGH` | Pemanggilan REST API eksternal menggunakan kredensial pengguna. |
| 7 | `FILE_DOWNLOAD` | File Download | `MEDIUM` | Pengunduhan berkas dari internet ke direktori lokal. |
| 8 | `FILE_UPLOAD` | File Upload | `HIGH` | Pengunggahan berkas lokal ke layanan eksternal. |
| 9 | `LOCAL_FILES` | Local Files | `MEDIUM` | Operasi baca, tulis, ubah nama, dan hapus berkas lokal. |
| 10 | `REPOSITORY` | Repository | `MEDIUM` | Operasi pembacaan status, diff, dan modifikasi repositori git. |
| 11 | `TERMINAL` | Terminal | `HIGH` | Eksekusi perintah shell di mesin lokal. |
| 12 | `CODE_EXECUTION` | Code Execution | `MEDIUM` | Eksekusi skrip Python, H-ISA, compiler, test runner, dan kendali hardware. |
| 13 | `ACCOUNT_ACCESS` | Account Access | `CRITICAL` | Akses sesi login atau akun pengguna. |
| 14 | `WEBSITE_EDITING` | Website Editing | `HIGH` | Pengubahan halaman atau konfigurasi website milik pengguna. |
| 15 | `DEPLOYMENT` | Deployment | `CRITICAL` | Publikasi/deploy ke lingkungan produksi (wajib konfirmasi final terpisah). |

## 2. Enam Mode Persetujuan (`APPROVAL_DECISIONS`)

1. **`ALLOW_ONCE`**: Memberikan token izin satu kali pakai untuk tuple `(category, target_type, target_value, operation)`. Setelah satu eksekusi selesai, token habis dan pemanggilan berikutnya kembali meminta persetujuan (`WAITING_FOR_APPROVAL`).
2. **`ALLOW_SESSION`**: Menyimpan aturan izin yang hanya berlaku untuk `session_id` aktif saat ini. Sesi lain tidak mewarisi izin tersebut.
3. **`ALWAYS_ALLOW`**: Menyimpan aturan izin persisten di SQLite untuk target spesifik yang disetujui pengguna.
4. **`ASK_EVERY_TIME`**: Memaksa pembuatan permintaan persetujuan (`WAITING_FOR_APPROVAL`) setiap kali target diakses.
5. **`DENY`**: Memblokir akses ke target secara eksplisit dan mencatat penolakan ke dalam log audit.
6. **`REVOKE_ACCESS`**: Mencabut seluruh aturan aktif dan token `ALLOW_ONCE` untuk target tersebut secara seketika.

## 3. Isolasi Target Granular & Aturan Khusus

- **Isolasi Domain (`_target_matches`)**: Izin untuk `docs.python.org` diverifikasi hanya cocok untuk `docs.python.org` (atau subdomainnya) dan **tidak pernah** memberikan akses ke domain lain seperti `github.com`.
- **Isolasi Folder (`_is_within_authorized_folder`)**: Izin akses ke `/Users/AMRA/folder_a` diverifikasi menggunakan resolusi path absolut (`Path.resolve()`) dan **tidak pernah** mengizinkan akses ke `/Users/AMRA/folder_b`. Operasi penghapusan (`files.delete`) tetap meminta konfirmasi eksplisit dan memindahkan berkas ke `.nui_trash`.
- **Gerbang Final Produksi (`DEPLOYMENT_FINAL_GATE`)**: Meskipun pengguna telah memiliki aturan `ALWAYS_ALLOW` umum, setiap aksi kategori `DEPLOYMENT` yang tidak menyertakan bendera konfirmasi final eksplisit (`explicit_final_deploy_confirmed=True`) selalu dihentikan pada status `WAITING_FOR_APPROVAL`.
- **Penyimpanan Rahasia di Keychain & Redaksi Audit Otomatis**: Kredensial API disimpan di **macOS Keychain** (`com.cosmictera.nui.desktop`), dan fungsi `redact_secrets()` menyensor pola `sk-...`, `ghp_...`, `Bearer ...`, `api_key`, `token`, `secret`, serta `password` menjadi `[REDACTED]` sebelum ditulis ke tabel `audit_logs`.
