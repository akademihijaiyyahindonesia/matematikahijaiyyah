# Portal 8888

**[EH] / DESAIN — belum masuk gerbang, belum di-PnR, belum di papan.** Folder
ini berdiri sendiri di luar `rtl/` dengan sengaja: menaruh `.v` di `rtl/` akan
memicu penjaga sidik jari dan penjaga testbench-yatim. Nama modul masih
**usulan**, menunggu persetujuan pemilik (`AGENTS.md` §2).

Sistem bukti-tahan-rusak untuk asal & integritas sinyal: Find-My/anti-maling,
deteksi login anomali, dan paket bukti untuk penegak hukum. Lokasi tepat datang
dari GPS perangkat sendiri atau dari data ISP lewat hukum — **tidak pernah**
ditebak dari latensi. Lihat [`ARCHITECTURE.md`](ARCHITECTURE.md) (L0–L5, batas,
otorisasi, dasar hukum) dan [`sim/EVIDENCE.md`](sim/EVIDENCE.md) (hasil uji).

## Isi

| berkas | peran | status uji |
|---|---|---|
| `rtl/hijaiyyah_timestamp.v` | cap-waktu UTC disiplin GPS-PPS | ✅ sim |
| `rtl/hijaiyyah_portal8888.v` | FSM 4 sudut + portal + jangkar, HMAC bergiliran | ✅ sim byte-exact |
| `rtl/jim_sync.v` | korelator penanda Jim 31-bit | ✅ sim |
| `rtl/jim_index.v` | nomor blok Jim GF(5), periode 3124 | ✅ sim |
| `rtl/ingress_parse.v` | baca header Ethernet/IP/TCP-UDP | ✅ sim 3000/3000 |
| `tb/*.v` | testbench masing-masing | — |
| `ref/*.py` | model perangkat lunak + verifier byte-exact + kampanye serangan | — |

## Ketergantungan

FSM Portal memakai mesin **HMAC-SHA256 yang sudah di repo** (`rtl/hijaiyyah_hmac.v`,
`rtl/hijaiyyah_sha256_stream.v`, `rtl/hijaiyyah_sha256_core.v` — commit `4bff781`,
207/207 di papan). Simulasi di folder ini dijalankan terhadap berkas itu dan
hasilnya cocok byte demi byte.

## Menjalankan (toolchain oss-cad-suite)

```sh
cd portal8888
R=../rtl
# cap-waktu GPS-PPS
iverilog -g2012 -o /tmp/ts tb/tb_timestamp.v rtl/hijaiyyah_timestamp.v && vvp /tmp/ts
# FSM Portal, byte-exact vs ref/portal_ref.py
python3 ref/portal_ref.py vec > tb/portal_vec.txt
iverilog -g2012 -o /tmp/p8 tb/tb_portal8888.v rtl/hijaiyyah_portal8888.v \
    $R/hijaiyyah_hmac.v $R/hijaiyyah_sha256_stream.v $R/hijaiyyah_sha256_core.v && vvp /tmp/p8
# sistem GPS-PPS -> cap-waktu -> segel, verifikasi byte oleh Python
python3 ref/portal_sys_keys.py > tb/portal_sys_keys.txt
iverilog -g2012 -o /tmp/ps tb/tb_portal8888_system.v rtl/hijaiyyah_portal8888.v \
    rtl/hijaiyyah_timestamp.v $R/hijaiyyah_hmac.v $R/hijaiyyah_sha256_stream.v \
    $R/hijaiyyah_sha256_core.v && vvp /tmp/ps && python3 ref/portal_sys_check.py
```

Kampanye serangan (model perangkat lunak): `python3 ref/campaign.py 300` dan
`python3 ref/attack_prov.py`.

## Yang belum

- Belum masuk gerbang repo (sengaja, di luar `rtl/`).
- PnR repo + simulasi integrasi di toolchain Mac.
- Ed25519 untuk lapis otorisasi (Otorisasi 8888) — belum ada di repo.
- Platform ingress jaringan: KV260 atau PHY tambahan (Tang Nano tak punya
  Ethernet; FSM penuh juga menyesakkan DFF Tang Nano ~75%).
