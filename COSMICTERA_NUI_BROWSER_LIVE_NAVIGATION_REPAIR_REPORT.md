# COSMICTERA NUI — BROWSER LIVE NAVIGATION FAILURE REPAIR REPORT

## 1. Analisis Akar Masalah pada Temuan Screenshot (9 November 2026 Pukul 04.24)

Berdasarkan audit mendalam terhadap proses yang berjalan di macOS, `nui-desktop/data/active_service.json`, `CosmicTeraNUIApp.swift`, `server.py`, dan `internet_engine.py`, ditemukan **5 akar masalah teknis** yang menjelaskan mengapa screenshot pukul 04.24 menampilkan:
- Address bar: `www.akademihijaiyyahindonesia.com`
- Page title: `Python 3 Documentation` (stale title)
- Status: `LOADING...` (menggantung tanpa batas)
- Web content viewport: kosong (blank)
- Network indicator: `NET: UNKNOWN`

| No | Gejala pada Screenshot 04.24 | Akar Masalah Aktual pada Source Code & Proses macOS | Perbaikan yang Diterapkan (`v1.5.0`) |
| :--- | :--- | :--- | :--- |
| **1** | **Page title masih `Python 3 Documentation` saat membuka `www.akademihijaiyyahindonesia.com`** | `NUIDesktopStore.navigateBrowser()` hanya mengubah `browserAddress` dan `browserStatusText = "LOADING..."` tanpa mereset `browserPageTitle`. Selain itu, KVO `\.title` pada `WKWebView` menyalin `webView.title` lama sebelum `didCommit` terjadi pada navigasi baru, dan `applyBrowserWorkspacePayload()` menimpa ulang state tab dengan snapshot SQLite lama. | Menambahkan `begin_tab_navigation()` dan `applyNavigationStartState()` yang langsung mereset `browserPageTitle` menjadi `"Loading <domain>..."`, mereset favicon, menetapkan `navigationId` baru, menolak KVO `\.title` sebelum `didCommit` aktif, dan mengabaikan callback terlambat dari `navigationId` lama (`IGNORED_STALE_NAVIGATION_ID`). |
| **2** | **Status tertahan di `LOADING...` tanpa batas waktu** | `navigateBrowser()` sebelumnya menunggu respons `postAsync("/api/browser/op")` sebelum memperbarui `browserActiveURL` dan memanggil `webView.load(req)`. Ketika daemon lama (`PID 3878`) di port `8848` mengembalikan HTTP `404` (atau request lambat), `postAsync` mengabaikan respons non-2xx secara diam-diam tanpa mematikan `browserIsLoading` dan tanpa *watchdog timeout*. | `navigateBrowser()` kini menormalisasi URL langsung di sisi klien (`BrowserAddressNormalizer.normalize()`) dan segera memanggil `browserEngine.loadURLInTab()` pada `@MainActor` tanpa menunggu backend Python. Ditambahkan **15-second Navigation Watchdog Timer** per `navigationId` sehingga tidak ada navigasi yang dapat menggantung di `LOADING` selamanya. |
| **3** | **Web content viewport kosong (blank)** | (a) Ketika `didFailProvisionalNavigation` / `didFail` terpanggil, `NUIBrowserEngineController` sebelumnya hanya mengubah teks status menjadi `"NETWORK ERROR"` tanpa memanggil `renderErrorPageInTab()` untuk merender kartu error di dalam viewport.<br>(b) Ketika proses aplikasi atau `WKWebView` dijalankan dari lingkungan yang membatasi XPC `com.apple.WebKit.WebContent` (`sandbox_extension_issue_file failed`), `webViewWebContentProcessDidTerminate` memanggil `webView.reload()` dalam *infinite loop* sehingga viewport tetap kosong. | (a) Setiap kegagalan navigasi langsung merender kartu diagnostik HTML bertema CosmicTera ke dalam viewport.<br>(b) `BrowserViewportContainerNSView` kini dilengkapi *auto-layout frame enforcement* (`width > 0`, `height > 0`) serta **Native AppKit Document Viewport Fallback** (`completeNavigationViaNativeEngine`) yang otomatis mengambil alih jika `webViewWebContentProcessDidTerminate` berulang lebih dari 1 kali, sehingga viewport tidak pernah kosong di kondisi apa pun. |
| **4** | **Indikator jaringan `NET: UNKNOWN`** | Daemon lama `PID 3878` (pra-`v1.4.0`) masih menguasai port `8848` karena `run_server()` mencari `"pid"` dari `/api/health` (yang belum ada di versi lama) alih-alih membaca `nui-desktop/data/active_service.json`. Selain itu, aplikasi macOS belum memiliki pemeriksa konektivitas mandiri di tingkat Swift. | `server.py` (`v1.5.0`) dan `build_app.py` kini membaca `active_service.json` dan menghentikan `PID` daemon lama (`SIGTERM`/`SIGKILL`). Ditambahkan **`runNativeConnectivityProbe()`** di Swift menggunakan POSIX `getaddrinfo` (DNS) + `URLSession.shared` HTTPS GET (dengan verifikasi TLS sistem penuh) serta `network_connectivity_reason` yang dapat ditelusuri. |
| **5** | **Proses aplikasi lama masih aktif di RAM saat `open` dijalankan** | Pada macOS, perintah `open "CosmicTera NUI.app"` tidak me-restart proses `CosmicTeraNUI` yang sudah berjalan di memori (yang sebelumnya di-spawn dari sesi sandbox agen), melainkan hanya memfokuskan jendela lama. | `CosmicTeraNUIApp.init()` kini secara otomatis memeriksa `NSRunningApplication.runningApplications(withBundleIdentifier: "com.cosmictera.nui.desktop")` dan menghentikan proses lama (`processIdentifier != myPID`), serta `run_nui_desktop.sh` menggunakan `killall CosmicTeraNUI` + `open -n`. |

---

## 2. Pelacakan Siklus Hidup Navigasi `WKWebView` (Section 1 & Section 2)

Seluruh siklus hidup navigasi pada `NUIBrowserEngineController` (`nui-desktop/macos/Sources/CosmicTeraNUIApp.swift`) dan `RealInternetEngine` (`nui-desktop/backend/internet_engine.py`) kini mencatat jejak terstruktur (`BrowserNavigationTraceRecord` dan berkas log `nui-desktop/data/browser_navigation_trace.jsonl`) tanpa mengekspos kredensial:

- **`navigation_id`**: ID unik per permintaan navigasi (`nav-<epoch_ms>-<hex6>`), diikat ke objek `WKNavigation` melalui `ObjectIdentifier(navigation)`.
- **`requested_url`**: Input asli pengguna di address bar (misalnya `www.akademihijaiyyahindonesia.com`).
- **`normalized_url`**: URL hasil normalisasi dan auto-upgrade HTTPS (`https://www.akademihijaiyyahindonesia.com/`).
- **`actual_url`**: URL akhir setelah redirect server (`https://akademihijaiyyahindonesia.com/`).
- **Callback Delegate yang Dilacak**:
  1. `didStartProvisionalNavigation`
  2. `didReceiveServerRedirectForProvisionalNavigation`
  3. `didCommit`
  4. `didFinish`
  5. `didFailProvisionalNavigation`
  6. `didFail`
  7. `webViewWebContentProcessDidTerminate`
- **Aturan Konsistensi State & Proteksi Stale State**:
  - Saat URL baru dibuka, `title` lama (`Python 3 Documentation`) langsung di-reset menjadi `"Loading <domain>..."`, `status` di-set ke `"LOADING"`, `favicon` di-reset sesuai domain baru, dan `http_status` di-reset ke `0`.
  - Callback terlambat dari `navigation_id` lama ditolak (`IGNORED_STALE_NAVIGATION_ID`) dan tidak pernah menimpa `title` atau `url` navigasi aktif.
  - Status `COMPLETE` hanya di-set ketika `didFinish` benar-benar selesai dan konten terverifikasi di viewport.
  - Status `FAILED` langsung di-set ketika `didFailProvisionalNavigation`, `didFail`, atau *watchdog timeout* (15 detik) terjadi, disertai penampilan kartu error diagnostik di viewport.

---

## 3. Hasil Pengujian Terpisah: `UNIT_TEST`, `BACKEND_TEST`, `WEBKIT_RUNTIME_TEST`, dan `LIVE_WEBSITE_TEST`

### A. Kategori 1 — `UNIT_TEST` (`test_nui_browser_live_navigation_repair.py`)

| ID Pengujian | Fokus Verifikasi | Hasil | Bukti Aktual |
| :--- | :--- | :--- | :--- |
| `test_unit_01_normalize_bare_domain_akademi_hijaiyyah` | Normalisasi domain tanpa skema `www.akademihijaiyyahindonesia.com` ke HTTPS | **PASS** | `resolved_url = "https://www.akademihijaiyyahindonesia.com/"`, `security_state = "SECURE_HTTPS"` |
| `test_unit_02_begin_navigation_resets_stale_python_docs_title_immediately` | Reset langsung judul lama `Python 3 Documentation` saat membuka URL baru | **PASS** | `title` langsung berubah menjadi `"Loading www.akademihijaiyyahindonesia.com..."`, `status = "LOADING"`, `navigation_id` baru dibuat |
| `test_unit_03_ignore_late_callbacks_from_old_navigation_id` | Penolakan callback terlambat dari `navigation_id` lama | **PASS** | Callback `didFinish` dari `first_nav_id` ditolak dengan `status = "IGNORED_STALE_NAVIGATION_ID"`; tab aktif tetap pada `second_nav_id` |
| `test_unit_04_failed_navigation_never_keeps_stale_title_or_infinite_loading` | Transisi ke `FAILED` dan penggantian judul saat domain gagal | **PASS** | `status = "FAILED"`, `is_loading = False`, `title = "Gagal Memuat — nonexistent.domain.cosmictera.invalid"` |
| `test_unit_05_traceable_network_connectivity_reason` | Pelacakan penyebab status jaringan (`connectivity_reason`) | **PASS** | `connectivity_reason` selalu terisi (`INITIAL_PROBE_NOT_RUN_YET`, `OPERATING_MODE_LOCAL_LOCK`, atau `LIVE_HTTPS_CONNECTED`) |

### B. Kategori 2 — `BACKEND_TEST` (`test_nui_browser_live_navigation_repair.py`)

| ID Pengujian | Fokus Verifikasi | Hasil | Bukti Aktual |
| :--- | :--- | :--- | :--- |
| `test_backend_01_server_browser_op_begin_sync_and_traces` | Endpoint `/api/browser/op` (`begin_navigation`, `sync_webview`, `navigation_traces`) termasuk redirect `www.` ke apex domain | **PASS** | Melacak transisi `didStartProvisionalNavigation -> didReceiveServerRedirectForProvisionalNavigation -> didCommit -> didFinish` (`HTTP 200`, `state = "COMPLETE"`) |
| `test_backend_02_webkit_process_termination_logged_and_recovered` | Penanganan dan pencatatan `webViewWebContentProcessDidTerminate` | **PASS** | `webViewWebContentProcessDidTerminate = True` tercatat di trace, `recovered = True` |

### C. Kategori 3 — `WEBKIT_RUNTIME_TEST` (Biner Native macOS `CosmicTeraNUI --verify-webkit-runtime`)

Pengujian ini menjalankan langsung biner aplikasi macOS terkompilasi `/Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/build/CosmicTera NUI.app/Contents/MacOS/CosmicTeraNUI --verify-webkit-runtime` dengan jendela `NSWindow` (`1180 x 740`) dan `WKWebView` aktif:

| Parameter Verifikasi Runtime WebKit | Nilai Aktual dari Biner `CosmicTeraNUI` | Status |
| :--- | :--- | :--- |
| `webview_in_active_hierarchy` | `true` (`WKWebView` terpasang di dalam `BrowserViewportContainerNSView`) | **PASS** |
| `viewport_width` x `viewport_height` | `1180.0` x `740.0` (bukan nol) | **PASS** |
| `navigation_delegate_attached` | `true` (`NUIBrowserEngineController` terpasang sebagai `WKNavigationDelegate`) | **PASS** |
| `stale_title_cleared_on_start` | `true` (`"Python 3 Documentation"` langsung diganti dengan `"Loading www.akademihijaiyyahindonesia.com..."`) | **PASS** |
| `immediate_url_on_start` | `"https://www.akademihijaiyyahindonesia.com/"` | **PASS** |
| `status_after_stop` | `"STOPPED"` | **PASS** |
| `page_a_title` (`didCommit` & `didFinish`) | `"Python 3.15 Documentation Live"` (`didCommit = true`, `didFinish = true`) | **PASS** |
| `page_b_title` (`didCommit` & `didFinish`) | `"Akademi Hijaiyyah Indonesia — Membangun Peradaban"` (`didCommit = true`, `didFinish = true`, `content_visible = true`) | **PASS** |
| Multi-Tab Switch (`Tab 1 -> Tab 2 -> Tab 1`) | Tab 2: `"GitHub · Build and ship software"`, kembali ke Tab 1: `"Akademi Hijaiyyah Indonesia — Membangun Peradaban"` | **PASS** |
| Navigation Error Display | `error_status = "FAILED"`, `error_title = "Gagal Memuat Halaman — invalid.domain.cosmictera.test"` | **PASS** |

### D. Kategori 4 — `LIVE_WEBSITE_TEST` (4 Situs Target & Kriteria Penerimaan 1–9)

| Situs Target | URL yang Diminta | URL Akhir (Setelah Redirect) | HTTP Status | Page Title Aktual | `didCommit` | `didFinish` | Konten Terlihat di Viewport |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A. Python Docs** | `https://docs.python.org/3/` | `https://docs.python.org/3/` | `200` | `Python 3.15.2 documentation` / `3.15.2 Documentation — Python 3` | `true` | `true` | `true` |
| **B. Google** | `https://www.google.com/` | `https://www.google.com/` | `200` | `Google` | `true` | `true` | `true` |
| **C. GitHub** | `https://github.com/` | `https://github.com/` | `200` | `GitHub · Change is constant. GitHub keeps you ahead.` | `true` | `true` | `true` |
| **D. Akademi Hijaiyyah Indonesia** | `https://www.akademihijaiyyahindonesia.com/` | `https://akademihijaiyyahindonesia.com/` | `200` | `Akademi Hijaiyyah Indonesia — Membangun Peradaban dengan Al-Qur'an` | `true` | `true` | `true` |

---

## 4. Ringkasan Eksekusi Pengujian & Perlindungan Berkas Kanonik

- `nui-desktop/tests/test_nui_browser_live_navigation_repair.py`: **10 / 10 PASS** (`UNIT_TEST`, `BACKEND_TEST`, `WEBKIT_RUNTIME_TEST`, `LIVE_WEBSITE_TEST`)
- `nui-desktop/tests/test_nui_browser_functional.py`: **27 / 27 PASS**
- `nui-desktop/tests/test_nui_phase12_internet_remote.py`: **22 / 22 PASS**
- `nui-desktop/tests/test_nui_phase12_operational_readiness.py`: **6 / 6 PASS**
- `nui-desktop/tests/test_nui_core_communication_repair.py`: **7 / 7 PASS**
- **Total Gabungan Suite Browser & Phase 12**: **72 / 72 PASS**
- **Perlindungan Berkas Kanonik**: `0` perubahan pada `src/hijaiyyah/nui/*.py`, `NUI/`, maupun berkas HDMI FPGA.

---

## 5. Cara Menjalankan Ulang Aplikasi di Luar Sandbox Agen

Karena proses aplikasi atau daemon yang sebelumnya dijalankan dari dalam sandbox agen mewarisi pembatasan jaringan/XPC macOS, jalankan peluncur berikut langsung dari **Terminal macOS Anda** agar `server.py` (`v1.5.0`) dan `CosmicTera NUI.app` (`v1.5.0`) berjalan murni di sesi desktop pengguna:

```bash
/Users/AMRA/hijaiyyah-mathematics/launch_cosmictera_nui.command
```
