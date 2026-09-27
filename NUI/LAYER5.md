# Lapis 5 dibekukan — baseline intelijen host

Dihasilkan `src/hijaiyyah/nui/layer5_freeze.py` dari evidence store, untuk tag `layer5-freeze-2026-09-27`. Instance: `cosmictera-layer5`. Yang di-commit hanya pointer dan hash; teks observasinya tetap di `~/cosmictera-layer5/observations/`, di luar repositori (K-11).

## Baseline

| kolektor | status | run | observed_at | stdout sha256 | stderr sha256 |
|---|---|---|---|---|---|
| `host_identity` | PASS | `20260927T050203Z-collectors` | 2026-09-27T05:02:03 | `87458b3b1f1c…` | `e3b0c44298fc…` |
| `processes` | PASS | `20260927T083814Z-collectors` | 2026-09-27T08:38:14 | `f01fcfdd2511…` | `e3b0c44298fc…` |
| `mounts` | PASS | `20260927T083814Z-collectors` | 2026-09-27T08:38:15 | `da590b49988b…` | `e3b0c44298fc…` |
| `root_listing` | PASS | `20260927T083814Z-collectors` | 2026-09-27T08:38:15 | `6ddd418bf2a3…` | `e3b0c44298fc…` |
| `systemd_overview` | PASS | `20260927T083814Z-collectors` | 2026-09-27T08:38:15 | `cb0e9545cf97…` | `e3b0c44298fc…` |
| `journal` | unavailable_due_to_permissions | `20260927T083814Z-collectors` | 2026-09-27T08:38:15 | `e3b0c44298fc…` | `f67710d9a290…` |
| `interfaces` | PASS | `20260927T083814Z-collectors` | 2026-09-27T08:38:15 | `f93525acf046…` | `e3b0c44298fc…` |
| `links` | PASS | `20260927T083814Z-collectors` | 2026-09-27T08:38:15 | `62adece16205…` | `e3b0c44298fc…` |
| `routes` | PASS | `20260927T083814Z-collectors` | 2026-09-27T08:38:15 | `70ba1421db04…` | `e3b0c44298fc…` |
| `interface_counters` | PASS | `20260927T083814Z-collectors` | 2026-09-27T08:38:15 | `d204d15706d8…` | `e3b0c44298fc…` |
| `containers` | unavailable_command_absent | `20260927T083814Z-collectors` | 2026-09-27T08:38:15 | `e3b0c44298fc…` | `92a1d429ddff…` |

## Kesegaran

`stale_after_seconds` = `300` — ditetapkan pemilik, 27 September 2026: 300 detik, satu ambang global untuk semua kolektor tanpa pengecualian -- cukup ketat supaya current berarti dekat dengan keadaan runtime, tanpa menuntut kolektor berjalan terus.

Aturannya: known current bila umur observasi tidak lebih dari stale_after_seconds; known but stale bila lebih, bila jam mundur, atau bila stale_after_seconds belum ditetapkan -- tanpa nilai, tidak ada observasi yang diklaim current; unknown bila tidak ada observasi yang mendukung.

Jamnya: cap waktu UTC jam host Mac saat observe() mulai (medan `timestamp` manifest, `observed_at` di jawaban), dibandingkan jam host yang sama saat kueri dijawab.

Kesegaran dinilai saat kueri dijawab, bukan dibekukan di sini: yang dibekukan adalah `observed_at` tiap observasi dan aturannya.

## Delta dari baseline ke run berikutnya

Run pembanding: `20260927T095339Z-collectors`. Aturan butir: usulan, kecuali yang dikunci pemilik: `processes`.

| kolektor | muncul | hilang | berubah | status | sha256 butir |
|---|---:|---:|---:|---|---|
| `host_identity` | 0 | 0 | 0 | PASS | `0d268d725e43…` |
| `processes` | 0 | 0 | 0 | PASS | `a354e3b1a200…` |
| `mounts` | 0 | 0 | 0 | PASS | `0d268d725e43…` |
| `root_listing` | 0 | 0 | 2 | PASS | `83df9f12a926…` |
| `systemd_overview` | 0 | 0 | 0 | PASS | `0d268d725e43…` |
| `journal` | 0 | 0 | 0 | unavailable_due_to_permissions | `0d268d725e43…` |
| `interfaces` | 0 | 0 | 0 | PASS | `0d268d725e43…` |
| `links` | 0 | 0 | 0 | PASS | `0d268d725e43…` |
| `routes` | 0 | 0 | 0 | PASS | `0d268d725e43…` |
| `interface_counters` | 0 | 0 | 2 | PASS | `5aa0cef9702c…` |
| `containers` | 0 | 0 | 0 | unavailable_command_absent | `0d268d725e43…` |

`processes` — dicatat terpisah sebagai `kernel_thread_changes`, bukan perubahan `processes` itu sendiri: 8 muncul, 6 hilang, 0 berubah.

Isi butirnya dibaca dari evidence store dengan `python3 -m hijaiyyah.nui.knowledge host delta <kolektor>`, lengkap dengan provenance kedua run. Tidak ada tindakan otomatis atas delta.

## Riwayat P8

| langkah | manifest | sha256 |
|---|---|---|
| P8.3 isolation, test instance | `observations/20260926T013117Z-isolation/manifest.json` | `83f0932f317e…` |
| P8.3 negative digest | `observations/20260926T013234Z-digest-negative/manifest.json` | `b0ee2b79e855…` |
| P8.4 eleven collectors, test instance | `observations/20260926T053008Z-collectors/manifest.json` | `89829f5c1f00…` |
| P8.7 promotion, main instance | `observations/20260926T091643Z-isolation/manifest.json` | `a5f590c2827e…` |
| P8.6 first main collector | `observations/cosmictera-layer5/20260927T050203Z-collectors/manifest.json` | `0786a7627046…` |
| ten main collectors | `observations/cosmictera-layer5/20260927T083814Z-collectors/manifest.json` | `cfaa3484f0fa…` |
| first run after the baseline | `observations/cosmictera-layer5/20260927T095339Z-collectors/manifest.json` | `b31b7571af74…` |
| test instance retired (K-17) | `observations/cosmictera-layer5-uji/20260927T083913Z-retirement/manifest.json` | `8325041a4995…` |

## Mengulang

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.layer5_freeze --verify
```
