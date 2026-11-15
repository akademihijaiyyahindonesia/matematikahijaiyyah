# LAPORAN AKSES WEB, BROWSER TERISOLASI & INTEGRASI API (`COSMICTERA_NUI_WEB_ACCESS_REPORT.md`)

- **Modul Implementasi**: [`nui-desktop/backend/tools.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/tools.py), [`nui-desktop/backend/permissions.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/permissions.py), dan [`nui-desktop/macos/Sources/CosmicTeraNUIApp.swift`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/macos/Sources/CosmicTeraNUIApp.swift)
- **Suite Verifikasi**: [`nui-desktop/tests/test_nui_desktop_full.py`](file:///Users/AMRA/hijaiyyah-mathematics/nui-desktop/tests/test_nui_desktop_full.py) (`test_operating_modes_and_untrusted_web_isolation`)

## 1. Tiga Mode Operasi Jaringan (`LOCAL`, `HYBRID`, `ONLINE`)

1. **`LOCAL` (Offline Lock)**:
   - Mematikan seluruh kategori akses jaringan eksternal (`INTERNET_ACCESS`, `WEB_SEARCH`, `WEB_READING`, `BROWSER_AUTOMATION`, `API_ACCESS`, `FILE_DOWNLOAD`, `FILE_UPLOAD`, `DEPLOYMENT`) pada tingkat `PermissionEngine` dengan keputusan `OPERATING_MODE_LOCAL_LOCK`.
   - Seluruh komputasi lokal CosmicTera (`NativeNUIProvider`, `HISAMachine`, `MASTER_TABLE`, `Coding Studio`, `Files`, dan `Hardware Monitor`) tetap berfungsi 100% tanpa internet.
2. **`HYBRID` (Default Terkendali)**:
   - Mengutamakan kecerdasan dan komputasi lokal, serta mengizinkan akses ke domain web atau endpoint API eksternal **hanya** apabila telah disetujui pengguna melalui aturan izin per domain/endpoint.
3. **`ONLINE`**:
   - Mengaktifkan pencarian web, pembacaan dokumentasi, dan konektor API eksternal di bawah pengawasan `PermissionEngine` dan pencatatan `audit_logs`.

## 2. Isolasi Konten Web Eksternal & Pertahanan Prompt Injection (`Section 19.2`)

Untuk mencegah serangan *indirect prompt injection* dari halaman web eksternal:
- **Sanitasi Direktif Berbahaya (`sanitize_untrusted_web_content`)**: Setiap halaman yang dibaca melalui `web.read_page` ditandai secara eksplisit dengan `"trust_level": "UNTRUSTED_EXTERNAL_WEB_DATA"` dan `"can_trigger_privileged_tools": False`. Pola injeksi instruksi (seperti upaya mengabaikan instruksi sistem, mengeksekusi perintah shell, atau membocorkan API key) dideteksi dan diganti dengan `[BLOCKED_UNTRUSTED_DIRECTIVE]`.
- **Blokir Eksekusi Alat Berprivilese (`untrusted_context=True`)**: Di dalam `NUIToolRegistry.execute_tool()`, setiap upaya pemanggilan alat pada kategori `LOCAL_FILES`, `REPOSITORY`, `TERMINAL`, `CODE_EXECUTION`, `API_ACCESS`, `ACCOUNT_ACCESS`, `WEBSITE_EDITING`, `DEPLOYMENT`, atau `FILE_UPLOAD` yang berasal dari konteks web tidak tepercaya langsung ditolak (`DENY_PROMPT_INJECTION_GUARD`) dan dicatat ke log audit.
- **Sandbox `WKWebView` Non-Persisten**: Komponen `IsolatedWebView` di aplikasi macOS menggunakan `WKWebsiteDataStore.nonPersistent()` sehingga cookie dan penyimpanan lokal halaman eksternal terisolasi dari sistem utama.

## 3. Atribusi Sumber & Konektor API Berbasis macOS Keychain

- Setiap respons mencantumkan `source_attribution` yang membedakan secara tegas antara:
  - `LOCAL_REPOSITORY` (fakta dan kode terverifikasi di repositori lokal),
  - `EXTERNAL_WEB` (data dari domain eksternal beserta URL/domain sumber),
  - `EXTERNAL_API` (data dari konektor API pengguna),
  - `LOCAL_MODEL` (keluaran model lokal bila tersedia).
- Konektor API (`api.request`) menyimpan token/rahasia di **macOS Keychain** (`KeychainVault`) dan tidak pernah menulis rahasia dalam teks biasa ke basis data SQLite maupun log audit.
