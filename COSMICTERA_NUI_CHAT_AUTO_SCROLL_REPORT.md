# COSMICTERA NUI DESKTOP — SMART AUTO-SCROLL & LIVE CHAT FOLLOW REPORT

## 1. Ringkasan Eksekutif

Laporan ini mendokumentasikan implementasi dan verifikasi **OWNER DIRECTIVE — COSMICTERA NUI DESKTOP SMART AUTO-SCROLL & LIVE CHAT FOLLOW** pada aplikasi macOS native `CosmicTera NUI Desktop` (`nui-desktop/macos/Sources/CosmicTeraNUIApp.swift`).

Seluruh kebutuhan perilaku scroll otomatis dan cerdas selama streaming telah dipenuhi dan diverifikasi:

- **Kompilasi Native macOS App**: `nui-desktop/macos/build/CosmicTera NUI.app` berhasil dikompilasi ulang tanpa error.
- **Verifikasi Pengujian Otomatis**: **41/41 pengujian lulus (`41 passed, 0 failed`)** pada seluruh rangkaian `nui-desktop/tests/`, termasuk `test_nui_smart_auto_scroll.py` yang menguji 12 skenario wajib Bagian 8.
- **Kepatuhan Arsitektur**: Persona resmi NUI (`HybitAIProgram.system`), system prompt, serta metode pemrosesan deterministik tidak diubah.

## 2. Penyebab Masalah Auto-Scroll Sebelumnya (Root Cause Analysis)

Berdasarkan audit pada `nui-desktop/macos/Sources/CosmicTeraNUIApp.swift`:

1. **`ScrollViewReader` Tidak Pernah Memanggil `proxy.scrollTo(...)`**:
   - Pada komponen `NUIChatSectionView`, daftar pesan dibungkus menggunakan `ScrollViewReader { proxy in ScrollView { ... } }`, tetapi variabel `proxy` tidak pernah dipanggil di bagian mana pun saat pesan pengguna dikirim maupun saat event SSE streaming diterima.
2. **Tidak Ada Anchor Bawah (`chat-bottom-anchor`)**:
   - Di bawah daftar pesan (`ForEach(store.messages)`) dan indikator aktivitas streaming (`isGenerating`), tidak terdapat elemen penanda tetap dengan `.id(...)` di bagian paling bawah `LazyVStack` yang menjadi target pengguliran.
3. **Tidak Ada Detektor Posisi Scroll (`NSScrollView` Observer) & State Smart Scroll**:
   - Aplikasi belum membedakan antara kondisi pengguna berada di bagian paling bawah (`isAutoFollowEnabled = true`) dan kondisi pengguna sengaja menggulir ke atas untuk membaca riwayat pesan (`userScrolledUp = true`).

## 3. Komponen UI dan State yang Diperbarui

File utama yang diperbarui:
- `nui-desktop/macos/Sources/CosmicTeraNUIApp.swift`
- `nui-desktop/tests/test_nui_smart_auto_scroll.py`

### A. State Smart Auto-Scroll pada `NUIDesktopStore`

Ditambahkan state terpublikasi dan variabel pengendali pada `NUIDesktopStore`:

- `static let chatBottomAnchorId = "chat-bottom-anchor"`: ID penanda bagian paling bawah percakapan.
- `@Published var isAutoFollowEnabled: Bool = true`: Menentukan apakah tampilan otomatis mengikuti teks terbaru.
- `@Published var userScrolledUp: Bool = false`: Menandai apakah pengguna sedang membaca pesan lama di atas.
- `@Published var scrollTriggerVersion: Int = 0`: Counter pemicu pengguliran ke `chatBottomAnchorId`.
- `@Published var shouldRefocusComposer: Int = 0`: Memastikan fokus kursor tetap berada di kolom input setelah mengirim pesan.
- `private var lastAutoScrollTimestamp: TimeInterval = 0`: Coalescing window (`30 ms`) untuk mencegah antrean animasi bertumpuk saat token streaming datang sangat cepat.

### B. Detektor Scroll Native (`SmartScrollObserverNSView` & `SmartScrollDetectorRepresentable`)

Ditambahkan komponen `NSViewRepresentable` yang terhubung langsung ke `enclosingScrollView` (`NSScrollView`) pada macOS untuk memantau:

- `NSScrollView.didLiveScrollNotification`
- `NSView.boundsDidChangeNotification` pada `contentView`
- Event `.scrollWheel` lokal (`NSEvent.addLocalMonitorForEvents(matching: .scrollWheel)`)

Logika deteksi:
- Menghitung jarak ke batas bawah dokumen (`distanceToBottom = documentHeight - visibleMaxY`).
- Jika pengguna menggulir ke atas (`scrollingDeltaY > 1.5`) dan jarak dari bawah melampaui ambang `28 pt`, memanggil `store.handleUserManualScrollUp()` (`isAutoFollowEnabled = false`, `userScrolledUp = true`).
- Jika pengguna menggulir kembali hingga mencapai jarak `<= 28 pt` dari bagian paling bawah, memanggil `store.handleUserReachedBottom()` (`isAutoFollowEnabled = true`, `userScrolledUp = false`).

### C. Integrasi pada Alur Pesan, Streaming SSE, dan Tool Activity (`handleStreamEvent`)

Pemanggilan `requestAutoScroll(force:immediate:)` diintegrasikan pada seluruh siklus percakapan:

| Kejadian / Event | Pemanggilan | Perilaku |
| :--- | :--- | :--- |
| Pengguna mengirim pesan (`sendChatMessage`) | `requestAutoScroll(force: true, immediate: true)` | Mengaktifkan kembali auto-follow, langsung menggulir ke pesan baru, dan menjaga fokus input composer |
| Event `user_ack` / `assistant_placeholder` | `requestAutoScroll(immediate: true)` | Menampilkan area respons awal NUI tanpa perlu scroll manual |
| Event `partial_response` (streaming token) | `requestAutoScroll(immediate: false)` | Mengikuti pertambahan teks secara halus (coalesced `30 ms`) selama `isAutoFollowEnabled == true` |
| Event `tool_call`, `tool_result`, `stage_update` | `requestAutoScroll(immediate: false)` | Menjaga status pencarian konteks, eksekusi tool, dan hasil tool tetap terlihat |
| Event `final_response`, `generation_cancelled`, `generation_error` | `requestAutoScroll(immediate: true)` | Memastikan bagian akhir jawaban atau pesan error terlihat utuh di bagian bawah |
| Membuka sesi dari riwayat / membuat sesi baru | `requestAutoScroll(force: true, immediate: true)` | Mengatur ulang auto-follow dan menampilkan bagian akhir percakapan |

### D. Tombol Melayang `↓ Kembali ke Jawaban Terbaru` & Pinned Input Composer

- **Tombol Melayang (`↓ Kembali ke Jawaban Terbaru  ·  Latest Response`)**:
  - Muncul secara otomatis di bagian bawah area chat (di atas composer, tanpa menutupi area ketik) hanya ketika `store.userScrolledUp == true`.
  - Menggunakan tema futuristik CosmicTera (`CosmicTheme.emerald` / `CosmicTheme.cyan` di atas `CosmicTheme.bgSecondary`).
  - Saat diklik, memanggil `store.scrollToLatestResponse()` yang langsung menggulir ke `"chat-bottom-anchor"`, mengaktifkan kembali `isAutoFollowEnabled = true`, dan menyembunyikan tombol.
- **Pinned Input Composer**:
  - Berada di luar `ScrollView` (tetap di bagian bawah window), dilengkapi `@FocusState private var isComposerFocused: Bool` dan `.onChange(of: store.shouldRefocusComposer)` sehingga kursor ketik tidak hilang saat auto-scroll berjalan.

## 4. Penanganan Performa untuk Jawaban Panjang

Untuk memastikan tidak terjadi frame drop, lag, atau posisi scroll yang melompat-lompat (jitter) saat jawaban panjang / kode panjang dialirkan dari Ollama:

1. **Coalescing `30 ms` pada `partial_response`**: Pembaruan scroll selama streaming dibatasi maksimal ~33 kali per detik, sedangkan event kritis (`sendChatMessage`, `final_response`, `generation_cancelled`, `scrollToLatestResponse`) dieksekusi seketika (`immediate: true`).
2. **Tanpa `withAnimation` Beruntun pada Setiap Token**: Pemanggilan `proxy.scrollTo(NUIDesktopStore.chatBottomAnchorId, anchor: .bottom)` dilakukan langsung pada `@MainActor` tanpa menumpuk transaksi animasi SwiftUI yang saling bertabrakan.

## 5. Hasil Pengujian 12 Skenario Wajib (Bagian 8)

Seluruh 12 skenario pada Bagian 8 diuji secara otomatis di `nui-desktop/tests/test_nui_smart_auto_scroll.py` bersama seluruh suite regresi `nui-desktop/tests/`:

| No | Skenario Pengujian | Status |
| :--- | :--- | :--- |
| 1 | Pesan pendek (`send_user_message("Halo")`) | **PASS** |
| 2 | Jawaban pendek streaming (`partial_response` -> `final_response`) | **PASS** |
| 3 | Jawaban panjang streaming (20 chunk beruntun + coalescing `30 ms`) | **PASS** |
| 4 | Jawaban multi-paragraf streaming | **PASS** |
| 5 | Jawaban Markdown (heading, bullet list, tabel) | **PASS** |
| 6 | Jawaban blok kode panjang (`25` fungsi Python bertahap) | **PASS** |
| 7 | Aktivitas tool selama jawaban (`stage_update`, `tool_call`, `tool_result`, `partial_response`, `final_response`) | **PASS** |
| 8 | Pengguna scroll ke atas saat NUI masih menjawab (`isAutoFollowEnabled = false`, `userScrolledUp = true`) | **PASS** |
| 9 | Klik tombol `↓ Kembali ke Jawaban Terbaru` (`scrollToLatestResponse()`) | **PASS** |
| 10 | Mengirim pesan baru setelah membaca pesan lama (`force: true, immediate: true` + fokus composer terjaga) | **PASS** |
| 11 | Stop generation saat jawaban sedang berjalan (`generation_cancelled`) | **PASS** |
| 12 | Membuka kembali percakapan panjang dari riwayat (`load_session_history`) | **PASS** |

Total hasil pengujian seluruh suite `nui-desktop/tests/`:
- **`41 passed in 12.18s` (`0` gagal)**.
