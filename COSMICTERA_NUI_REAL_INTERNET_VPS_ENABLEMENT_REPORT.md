# COSMICTERA NUI — REAL INTERNET, VPS, DOMAIN & FILE VERIFICATION ENABLEMENT REPORT

**Tanggal Verifikasi**: 9 November 2026  
**Repository**: `/Users/AMRA/hijaiyyah-mathematics`  
**Target Sistem**: macOS (Apple Silicon M1 Max, 32 GB RAM) · CosmicTera NUI Desktop (`CosmicTera NUI.app`) + Python Backend (`nui-desktop/backend/`)  
**Status Pengujian**: **19 / 19 PASS** pada `test_nui_real_internet_vps_domain.py` (**75 / 75 PASS** gabungan suite jaringan/VPS/file/chat)  

## 1. Root Cause Analysis of Previous Local-Only Limitation

Sebelum perbaikan ini, ketika pengguna bertanya di chat:
> *"Apakah folder `/Users/AMRA/yayasan` sudah terhubung ke VPS? Apakah file sudah di-upload? Apakah domain `www.akademihijaiyyahindonesia.com` sudah terhubung ke server?"*

terdapat empat akar penyebab mengapa respons NUI belum melakukan pemeriksaan lintas-sistem secara menyeluruh:
1. **Keterbatasan Routing Kueri Operasional (`providers.py`)**: `is_folder_vps_status_query()` sebelumnya hanya mendeteksi kata kunci sempit (`vps`/`ssh` + `folder`) dan belum mengenali ke-10 kueri operasional alami (seperti *"Cek apakah website saya online"*, *"Apakah domain saya sudah terhubung?"*, *"Apakah file sudah di-upload?"*, *"Bandingkan file lokal dengan server"*), serta belum meneruskan `internet_engine` ke `run_folder_vps_inspection()`.
2. **Belum Adanya Orkestrasi 8-Langkah Terpadu**: Meskipun `RealInternetEngine` dan `RemoteVPSDevelopmentEngine` sudah ada, keduanya belum digabungkan dengan `UniversalFileActionEngine` dalam satu pipeline pemeriksaan yang sekaligus mengecek: (A) manifest SHA-256 folder lokal, (B) antarmuka jaringan macOS & konektivitas internet, (C) DNS multi-record domain, (D) HTTP/HTTPS redirect & sertifikat TLS, (E) penemuan konfigurasi SSH/DEPLOY.md, (F) koneksi SSH/SFTP, (G) manifest remote workspace, dan (H) perbandingan SHA-256 lokal vs server.
3. **Absennya `Entitlements.plist` pada Bundel Aplikasi macOS (`build_app.py`)**: `CosmicTera NUI.app` sebelumnya ditandatangani secara ad-hoc tanpa file `Entitlements.plist` yang mendeklarasikan `com.apple.security.network.client` dan `com.apple.security.network.server`.
4. **Ketiadaan Guard Eksplisit pada System Prompt (`persona_and_context.py`)**: Ketika pertanyaan dialihkan ke LLM lokal (Ollama), model terkadang berasumsi bahwa dirinya adalah AI lokal yang tidak memiliki akses internet atau VPS jika konteks hasil pemeriksaan runtime belum disuntikkan secara eksplisit.

## 2. macOS Network & Entitlement Audit

Audit dan perbaikan kapabilitas jaringan pada tingkat aplikasi macOS (`nui-desktop/macos/build_app.py`):
- **Info.plist (`NSAppTransportSecurity`)**: `NSAllowsArbitraryLoads = true` untuk mengizinkan inspeksi HTTP/HTTPS lintas domain dan pengecekan redirect `http://` ke `https://`.
- **Signed Entitlements (`nui-desktop/macos/build/Entitlements.plist`)**:
  - `com.apple.security.network.client = true` (Outbound DNS, TCP, TLS, HTTPS, SSH/SFTP)
  - `com.apple.security.network.server = true` (Local backend service `127.0.0.1:8848`)
  - `com.apple.security.files.user-selected.read-write = true` (Connected Folders access)
- **Bukti Verifikasi `codesign -d --entitlements -`**:
  - Binary `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/build/CosmicTera NUI.app` berhasil dikompilasi ulang dan diverifikasi memiliki ketiga entitlement di atas (`PASS_LIVE`).
- **Pemeriksaan Antarmuka Jaringan macOS (`/sbin/ifconfig`)**:
  - Fungsi `inspect_macos_network_interfaces()` di `internet_engine.py` membaca status antarmuka aktif (`en0`, IPv4 `192.168.1.6`) secara langsung (`PASS_LIVE`).

## 3. Outbound Internet & DNS Engine Implementation

Diimplementasikan pada `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/internet_engine.py`:
- **`inspect_macos_network_interfaces()` & `check_network_interfaces()`**: Memeriksa antarmuka aktif macOS (`en0`), alamat IPv4, dan IPv6 non-link-local.
- **`classify_network_error(exc_or_msg)`**: Mengklasifikasikan setiap kegagalan jaringan secara presisi ke dalam:
  - `DNS_FAILURE`
  - `CONNECTION_REFUSED`
  - `TLS_ERROR`
  - `TIMEOUT`
  - `SANDBOX_BLOCKED`
  - `HTTP_ERROR` / `NETWORK_ERROR`
- **`resolve_dns_records(domain)`**: Mengambil record `A`, `AAAA`, `CNAME`, `NS`, `MX`, dan `TXT` menggunakan resolver sistem macOS (`socket.getaddrinfo`), `/usr/bin/dig`, serta fallback DNS-over-HTTPS JSON, lengkap dengan latensi milidetik dan status verifikasi (`PASS_LIVE` / `PASS_SIMULATED` / `BLOCKED` / `FAILED`).
- **`check_tls(host, port=443)`**: Mengekstrak versi protokol TLS (`TLSv1.3`), cipher suite, validitas sertifikat, `subject_cn`, `issuer_cn`, `issuer_org`, `not_before`, `not_after`, `days_until_expiry`, `san_domains`, dan `cert_sha256`.

## 4. Domain & Website Verification Engine Implementation

Diimplementasikan melalui `inspect_http_https_and_redirects()` dan `inspect_domain_and_website()` pada `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/internet_engine.py`:
- Memeriksa keterjangkauan TCP pada port `80` dan `443`.
- Mengirimkan request `HEAD` dan `GET` pada `http://` dan `https://`, melacak rantai redirect (`redirect_chain`), URL akhir (`final_url`), kode status HTTP, header respons (`Server`, `Content-Type`), serta mengekstrak `<title>` halaman.
- Membandingkan IP hasil resolusi DNS domain dengan IP VPS target (`ip_matches_target_vps`) dan status verifikasi SSH (`remote_vps_verified`).
- Mengklasifikasikan status domain ke dalam **5 kategori wajib Fase 5**:
  1. `DOMAIN_NOT_RESOLVED`: Domain belum memiliki DNS record yang ter-resolve atau kueri DNS gagal.
  2. `DNS_RESOLVED_SERVER_UNREACHABLE`: DNS mengarah ke IP, tetapi port 80/443 tidak merespons.
  3. `SERVER_REACHABLE_WEB_FAILED`: Port TCP terbuka, tetapi HTTP/HTTPS atau TLS gagal.
  4. `WEBSITE_ACCESSIBLE_VPS_UNPROVEN`: Website merespons HTTP/HTTPS dengan baik, tetapi belum terbukti berasal dari VPS milik pengguna karena sesi SSH/SFTP ke VPS belum terverifikasi.
  5. `WEBSITE_ACCESSIBLE_VPS_VERIFIED`: Website merespons HTTP/HTTPS dan IP serta isi/konfigurasi terbukti cocok dengan VPS yang terverifikasi.

## 5. SSH & SFTP Remote Engine Implementation

Diperluas pada `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/remote_dev_engine.py`:
- **`discover_ssh_and_deployment_metadata(local_folder_path)`**:
  - Memeriksa `~/.ssh/config` untuk menemukan alias host SSH tanpa membocorkan kunci privat.
  - Memeriksa `/Users/AMRA/yayasan/DEPLOY.md` dan menemukan referensi terdokumentasi `root@187.53.135.198`, path `/opt/yayasan`, dan domain `www.akademihijaiyyahindonesia.com` dengan label bukti jujur: `DOCUMENTED_IN_DEPLOY_MD_ONLY (Dokumentasi lokal DEPLOY.md, BUKAN bukti profil SSH/SFTP aktif)`.
- **`connect_and_inspect(profile_id)` & Verifikasi Fingerprint Host**:
  - Menolak koneksi secara otomatis (`HOST_KEY_VERIFICATION_FAILED`) apabila fingerprint host tidak berformat `SHA256:...` atau tidak cocok dengan hasil scan host key.
  - Menyimpan kredensial rahasia di macOS Keychain (`KeychainVault`), tidak pernah di SQLite plaintext atau log.
- **`disconnect_profile(profile_id)`**: Memutus sesi profil VPS secara aman dan mencatat ke dalam audit log.
- **`inspect_remote_workspace_manifest(profile_id, remote_path)`**: Mengambil daftar seluruh berkas di dalam `remote_workspace` beserta hash `SHA-256` masing-masing berkas melalui SFTP/SSH read-only.

## 6. Folder-to-VPS Mapping Implementation

Diimplementasikan pada `UniversalResourceRegistry` di `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/universal_file_intelligence.py`:
- **`set_folder_vps_mapping()` & `get_folder_vps_mapping()`**: Menyimpan dan mengambil ke-12 atribut pemetaan Fase 4 secara eksplisit di SQLite:
  - `resource_id`, `local_canonical_path`, `resource_type`, `permission_scope`, `remote_profile_id`, `remote_host_identifier`, `remote_workspace_path`, `last_local_inspection`, `last_remote_inspection`, `last_successful_synchronization`, `last_verified_commit`, `last_verified_manifest`, dan `explicitly_mapped_to_vps`.
- Menegakkan aturan bahwa folder lokal **tidak pernah** diasumsikan terhubung ke VPS hanya karena terdaftar di Connected Folders, memiliki `.git`, atau memiliki `DEPLOY.md`.

## 7. Local vs Remote File Comparison Implementation

Diimplementasikan pada `UniversalFileActionEngine` di `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/universal_file_intelligence.py`:
- **`build_local_directory_manifest(local_path)`**: Menghitung jumlah berkas, ukuran byte total, daftar path relatif, `mtime`, `SHA-256` per berkas, dan digest `manifest_sha256` tingkat direktori.
- **`compare_local_and_remote_manifests(local_path, profile_id, remote_path)`**: Membandingkan manifest lokal dengan manifest remote VPS dan mengklasifikasikan setiap berkas ke dalam:
  - `MATCH`: Berkas ada di lokal dan di server dengan hash `SHA-256` identik.
  - `LOCAL_ONLY`: Berkas ada di lokal, tetapi belum ada di server.
  - `REMOTE_ONLY`: Berkas ada di server, tetapi tidak ada di lokal.
  - `CONTENT_MISMATCH`: Berkas ada di kedua sisi, tetapi hash `SHA-256` berbeda.
  - `UNKNOWN` / `NOT_CONFIGURED`: Tidak dapat membandingkan karena sesi SSH/SFTP ke VPS belum dikonfigurasi atau belum terhubung.

## 8. Conversational Tool Routing Integration

Diperbarui pada `persona_and_context.py`, `orchestrator.py`, `providers.py`, dan `server.py`:
- `is_folder_vps_status_query()` dan `classify_operational_network_subintent()` mengenali seluruh 10 kalimat perintah operasional Fase 7 maupun gabungan pertanyaan pemeriksaan folder/VPS/file/domain.
- `NativeNUIProvider` dan `OllamaProvider` secara otomatis mengeksekusi `run_folder_vps_inspection()` dan mengembalikan laporan 6-bagian terstruktur berdasarkan data runtime nyata.
- `NUIPersonaLoader.build_system_prompt()` melarang keras klaim *"Saya adalah AI lokal dan tidak mempunyai akses internet atau VPS"*.

## 9. Permission & Security Enforcement

Diperbarui pada `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/permissions.py`:
- Menambahkan 11 cakupan izin operasional eksplisit Fase 8 ke dalam `PERMISSION_CATEGORIES`:
  - `READ_LOCAL`, `READ_REMOTE`, `NETWORK_ACCESS`, `SSH_CONNECT`, `SFTP_ACCESS`, `REMOTE_COMMAND`, `UPLOAD_FILE`, `DOWNLOAD_FILE`, `SYNC_DIRECTORY`, `MODIFY_REMOTE`, `DEPLOY_WEBSITE`.
- Menambahkan operasi baca diagnostik (`INSPECT`, `DIAGNOSE`, `CHECK_DOMAIN`, `COMPARE_MANIFEST`) ke `READ_SAFE_OPERATIONS` sehingga pemeriksaan status bersifat 100% read-only dan tidak pernah memicu upload atau modifikasi server tanpa konfirmasi eksplisit.

## 10. UI Verification Panel Changes

Diperbarui pada `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/Sources/CosmicTeraNUIApp.swift`:
- Menambahkan panel **Network, Domain & VPS Verification Center (Phase 9)** pada workspace **Web & Internet** yang menampilkan ke-12 indikator status real-time:
  1. `Internet Status`
  2. `DNS Status`
  3. `Domain Status`
  4. `HTTPS / TLS Status`
  5. `VPS SSH Status`
  6. `Host Fingerprint Status`
  7. `SFTP Status`
  8. `Local Folder` (`/Users/AMRA/yayasan`)
  9. `Remote Workspace`
  10. `File Sync Status`
  11. `Last Verification Time`
  12. `Error Details`
- Menyediakan ke-9 tombol aksi operasional langsung:
  - `Test Internet`, `Check Domain`, `Test SSH`, `Inspect Remote Workspace`, `Compare Local and Remote`, `Upload Files`, `Sync Directory`, `Verify Deployment`, dan `Disconnect Remote`.

## 11. Live Verification Results for `/Users/AMRA/yayasan`

Hasil pemeriksaan langsung (`PASS_LIVE` pada filesystem lokal macOS):
- **Connected Folder ID**: `fld-8a76b6f5e8` (`READ_WRITE`)
- **Local Canonical Path**: `/Users/AMRA/yayasan` (`AVAILABLE`)
- **Files Inspected**: `600` berkas proyek (`491.248.072` byte terindeks pada batas enumerasi manifest)
- **Local Manifest SHA-256**: `24803a784a2f861e56161b6a4225c350231b57f2dffc0fbed52622d9efff8b6f`
- **OS Mount Table (`/sbin/mount`)**: `LOCAL_FILESYSTEM (APFS on /, tidak ada mount SSHFS/FUSE/remote aktif)`
- **Dokumentasi Lokal Ditemukan**: `/Users/AMRA/yayasan/DEPLOY.md` mencatat target `root@187.53.135.198`, path `/opt/yayasan`, dan domain `www.akademihijaiyyahindonesia.com` (`DOCUMENTED_IN_DEPLOY_MD_ONLY`).

## 12. Live Verification Results for `www.akademihijaiyyahindonesia.com`

| Lingkungan Eksekusi | Status Pemeriksaan | Klasifikasi Domain | Detail Bukti |
| :--- | :--- | :--- | :--- |
| **macOS Host Network Interface (`/sbin/ifconfig`)** | `PASS_LIVE` | Antarmuka `en0` `ACTIVE` (IPv4 `192.168.1.6`) | Diverifikasi langsung melalui `/sbin/ifconfig` |
| **Deterministic / Simulated Transport (`SimulatedDomainTransport`)** | `PASS_SIMULATED` | `WEBSITE_ACCESSIBLE_VPS_UNPROVEN` (ketika SSH belum terverifikasi) & `WEBSITE_ACCESSIBLE_VPS_VERIFIED` (ketika IP cocok + SSH terverifikasi) | Menguji kelima klasifikasi Fase 5, rantai redirect `308/301`, TLSv1.3, dan kecocokan IP VPS (`test_01` s/d `test_05`, `test_16`) |
| **Subprocess Runner Sandbox (Ketika `RequiresNetworkAccess=false`)** | `BLOCKED` / `FAILED` | `DOMAIN_NOT_RESOLVED` (`DNS_FAILURE`) | Diklasifikasikan secara jujur tanpa memalsukan status online ketika soket keluar diblokir oleh sandbox |
| **Native macOS App (`CosmicTera NUI.app` dengan `com.apple.security.network.client`)** | `PASS_LIVE` (Entitlement Signed) | Siap menjalankan `check_domain` secara langsung dari aplikasi desktop | Ditandatangani dengan `Entitlements.plist` (`com.apple.security.network.client = true`) |

## 13. SSH/VPS Status and What Credentials/Config Were Found or Missing

- **Status Saat Ini**: `NOT_CONFIGURED` (Status Folder: `LOCAL_ONLY`).
- **Apa yang Ditemukan**:
  - Di dalam `/Users/AMRA/yayasan/DEPLOY.md` ditemukan catatan dokumentasi deployment ke `root@187.53.135.198` pada direktori `/opt/yayasan`.
- **Apa yang Belum Tersedia (`MISSING`)**:
  1. Berkas `~/.ssh/config` belum ada di komputer macOS pengguna (`NOT_FOUND`).
  2. Belum ada profil SSH terdaftar di `RemoteVPSDevelopmentEngine` (`0` profil).
  3. Belum ada kunci privat SSH atau kredensial di macOS Keychain untuk `root@187.53.135.198` beserta `expected_host_fingerprint` (`SHA256:...`).
- **Kesimpulan Jujur**: Karena profil SSH, fingerprint host `SHA256:...`, dan sesi SFTP ke `187.53.135.198` belum dikonfigurasi, NUI melaporkan secara jujur bahwa hubungan aktif ke VPS adalah `NOT_CONFIGURED` (`LOCAL_ONLY`) dan status sinkronisasi berkas ke server belum dapat diverifikasi (`NOT_CONFIGURED`).

## 14. Automated Test Results

Seluruh **19 pengujian baru** pada `nui-desktop/tests/test_nui_real_internet_vps_domain.py` dan **56 pengujian regresi** pada suite terkait lulus 100% (**75 / 75 PASS** dalam `31.52s`):

| Suite Pengujian | Jumlah Test | Status | Cakupan Verifikasi |
| :--- | :--- | :--- | :--- |
| `nui-desktop/tests/test_nui_real_internet_vps_domain.py` | **19 / 19** | **PASS** | DNS lookup, HTTPS request, TLS cert inspection, Redirect chain, 5 klasifikasi domain, SSH unconfigured & `DEPLOY.md` discovery, SSH simulated connection, Host fingerprint mismatch block, SFTP manifest listing, Local vs Remote SHA-256 comparison (`MATCH`, `CONTENT_MISMATCH`, `LOCAL_ONLY`, `REMOTE_ONLY`), Full verification `/Users/AMRA/yayasan` & `www.akademihijaiyyahindonesia.com`, Read-only safety, Write confirmation gate, 10 conversational queries |
| `nui-desktop/tests/test_nui_universal_file_actions.py` | **18 / 18** | **PASS** | 9-stage Universal File & Folder Action workflow, PDF/DOCX/XLSX/PPTX/ZIP/Code, copy-on-edit attachment safety |
| `nui-desktop/tests/test_nui_chat_clipboard_ux.py` | **16 / 16** | **PASS** | Native `NSPasteboard` copy/paste, code block copy, edit & resend, regenerate, stop stream, 9-field VPS status accuracy |
| `nui-desktop/tests/test_nui_phase12_internet_remote.py` | **22 / 22** | **PASS** | Connected folder disconnect/reconnect, Browser security & sanitization, staging downloads, Keychain isolation, VPS guards & audit redaction |
| **Total Kumulatif Verifikasi** | **75 / 75** | **100% PASS** | Seluruh skenario Fase 1–12 terverifikasi tanpa menyentuh modul kanonik `src/hijaiyyah/nui/` |

## 15. Modified Files

 Seluruh perubahan terisolasi di dalam `nui-desktop/` (tanpa mengubah satu pun dari 43 modul kanonik `src/hijaiyyah/nui/*.py`, artefak freeze `NUI/`, maupun berkas RTL/HDMI):
1. `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/permissions.py`
2. `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/internet_engine.py`
3. `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/remote_dev_engine.py`
4. `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/universal_file_intelligence.py`
5. `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/persona_and_context.py`
6. `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/orchestrator.py`
7. `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/providers.py`
8. `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/server.py`
9. `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/build_app.py`
10. `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/Sources/CosmicTeraNUIApp.swift`
11. `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/build/CosmicTera NUI.app` (beserta `Entitlements.plist`)
12. `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_real_internet_vps_domain.py`
13. `/Users/AMRA/hijaiyyah-mathematics/COSMICTERA_NUI_REAL_INTERNET_VPS_ENABLEMENT_REPORT.md`

## 16. Remaining Limitations and Honest Verification Status

- **Internet & Antarmuka Jaringan macOS**: `PASS_LIVE` untuk pemeriksaan antarmuka macOS (`en0` aktif pada `192.168.1.6`) dan penandatanganan entitlement `com.apple.security.network.client` pada `CosmicTera NUI.app`; `PASS_SIMULATED` untuk skenario uji deterministik DNS/HTTP/TLS/Redirect di pytest.
- **Koneksi SSH/SFTP ke VPS (`187.53.135.198`)**: `PASS_SIMULATED` untuk seluruh alur transport SSH/SFTP, verifikasi fingerprint `SHA256:...`, dan perbandingan manifest SHA-256; **`NOT_CONFIGURED` secara live** karena profil SSH, kunci privat/kredensial Keychain, dan fingerprint `SHA256:...` untuk server `187.53.135.198` belum didaftarkan oleh pengguna.
- **Jaminan Keamanan Read-Only**: Seluruh pemeriksaan jaringan, domain, VPS, dan manifest berkas berjalan 100% dalam mode baca (`READ_ONLY`) tanpa melakukan upload, penghapusan, atau perubahan berkas.

