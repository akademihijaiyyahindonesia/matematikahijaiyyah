# Portal 8888

**[EH] / DESAIN — belum masuk gerbang; satu lari di papan Tang Nano 20K.** Folder
ini berdiri sendiri di luar `rtl/` dengan sengaja: menaruh `.v` di `rtl/` akan
memicu penjaga sidik jari dan penjaga testbench-yatim. Nama yang sudah
disetujui pemilik: top `hijaiyyah_portal8888` dan pembungkus
`hijaiyyah_portal8888_gowin_top`; nama modul lain tetap usulan (`AGENTS.md` §2).

## Active v1 Implementation

`hijaiyyah_portal8888` is the locked operational v1 top in this local folder.
It accepts one PHY-byte stream (`phy_port`, `phy_byte_valid`, `phy_byte`,
`phy_last`) in one clock domain. The sealed L1 body is exactly 125 bytes,
MSB-first: `DEV|PORT|T_sec|T_tick|T_source|T_uncert_ns|CTR|status|ver|SRC_IP|
SPORT|DPORT|PROTO|SRC_MAC|FRAME_HASH|IDX|PREV`. L1 v1 has no `LOC`.

Keys arrive only through five write-once provisioning slots, then `prov_lock`;
they are neither output nor operational input ports. A frame is buffered and
replayed through SHA-256 because the SHA stream can stall. Simulation validates
one 9,216-byte frame byte-exactly against the Python reference. Frames above
that limit, or frames arriving while replay/sealing is busy, are dropped and
reported; v1 has no queue. This is fail-closed, not a throughput claim.

A Tang Nano 20K wrapper exists, `fpga/gowin/hijaiyyah_portal8888_gowin_top.v`:
the Portal behind a UART on ten pins, validated in simulation through its UART
pins and placed and routed for the GW2AR-18C (15,848 LUT4, 8,080 DFF, 6 BSRAM). The board has no Ethernet port, so a frame reaches the PHY stream from
the host, one UART byte per PHY byte. No AXI mapping or PHY choice exists.

Sistem bukti-tahan-rusak untuk asal & integritas sinyal: Find-My/anti-maling,
deteksi login anomali, dan paket bukti untuk pemilik. Lokasi tepat datang
dari GPS perangkat sendiri atau dari data ISP lewat hukum — **tidak pernah**
ditebak dari latensi. Lihat [`ARCHITECTURE.md`](ARCHITECTURE.md) (L0–L5, batas,
otorisasi, dasar hukum) dan [`sim/EVIDENCE.md`](sim/EVIDENCE.md) (hasil uji).

## Isi

| berkas | peran | status uji |
|---|---|---|
| `rtl/hijaiyyah_timestamp.v` | cap-waktu: UTC diprovisi, disiplin GPS-PPS, holdover | ✅ sim; di papan berjalan bebas (tanpa PPS) |
| `rtl/hijaiyyah_portal8888.v` | top v1: tangkap, SHA-256 frame, segel HMAC, rantai 4 sudut, ROOT, jangkar; top lama di berkas yang sama | ✅ sim byte-exact; ✅ papan lewat pembungkus |
| `rtl/jim_sync.v` | korelator penanda Jim 31-bit | ✅ sim |
| `rtl/jim_index.v` | nomor blok Jim GF(5), periode 3124 | ✅ sim |
| `rtl/ingress_parse.v` | baca header Ethernet/IP/TCP-UDP (lama) | ✅ sim 3000/3000 |
| `rtl/ingress_parse_v1.v` | baca header v1, frame kontinu sampai 9.216 byte | ✅ sim; ✅ papan, 200 frame asli |
| `fpga/gowin/hijaiyyah_portal8888_gowin_top.v` | pembungkus Tang Nano 20K: Portal di balik UART, 10 pin | ✅ sim lewat pin UART: 23 perintah, 0 salah |
| `ref/portal_uart.py` | protokol UART pembungkus: satu penyandi dan satu pemeriksa, untuk bench dan papan | — |
| `scripts/portal8888_uart_test.py` | uji papan lewat port serial, memakai pemeriksa yang sama | ✅ papan, satu lari: 23 perintah, 0 salah |
| `tb/*.v` | testbench masing-masing, keluar non-nol saat gagal | — |
| `ref/*.py` | model perangkat lunak, verifier byte-exact, kampanye serangan, generator vektor | — |
| `Makefile` | mengulang seluruh bukti dari build bersih | — |

## Ketergantungan

FSM Portal memakai mesin **HMAC-SHA256 yang sudah di repo** (`rtl/hijaiyyah_hmac.v`,
`rtl/hijaiyyah_sha256_stream.v`, `rtl/hijaiyyah_sha256_core.v` — commit `4bff781`,
207/207 di papan), dibaca dari `../rtl`, bukan disalin.

## Menjalankan (toolchain oss-cad-suite)

```sh
cd portal8888
make            # vektor, semua bench, R3 rujukan, sistem lama, dan pembungkus lewat UART
make ref        # model perangkat lunak + kampanye serangan
make synth      # hitungan sel yosys synth_gowin -nodsp per modul
make vcd        # lari sistem lama lagi, dengan VCD seluruh sinyal
make sim_gowin_top          # pembungkus UART: seluruh skenario, 10 clock per bit
make sim_gowin_top_115200   # skenario pendek pada 115200, laju papan
make portal8888_bitstream   # synth_gowin -> nextpnr-himbaechel -> gowin_pack
```

Semua keluaran ke `build/`, yang di-gitignore.

## Yang belum

- Belum masuk gerbang repo (sengaja, di luar `rtl/`).
- Bukti papan baru dua lari lewat UART, yang kedua dengan 200 frame asli
  (`sim/EVIDENCE.md` §9). Lari berulang dan PPS belum diuji di papan. Memuat papan
  tetap langkah laboratorium atas perintah pemilik.
- Kontrak AXI/host dan PHY Ethernet belum dikunci.
- Ed25519 untuk lapis otorisasi (Otorisasi 8888) — belum ada di repo.
- Platform ingress jaringan: KV260 atau PHY tambahan — Tang Nano 20K tidak
  punya port Ethernet.
