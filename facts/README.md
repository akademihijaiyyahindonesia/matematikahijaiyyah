# Inventaris fakta — Lapis 0 NUI

**Perintah pemilik, 21 September 2026:** *"Jangan mulai dengan AI. Mulai
dengan inventaris fakta."*

Tiap lapis NUI di atas ini menanyakan hal yang sama di wilayah berbeda — apa
yang diketahui benar tentang opcode ini, modul ini, target ini — dan tak satu
pun bisa menjawabnya dari model. Jawabannya datang dari sini.

Satu fakta = satu berkas JSON, dengan tujuh medan yang pemilik tetapkan:

```
fact_id   statement   source   evidence   verification_method   status   timestamp
```

JSON, bukan YAML, karena PyYAML tidak terpasang dan menambah dependensi butuh
izin pemilik (`AGENTS.md`).

## Statusnya kosakata repo ini, bukan kosakata baru

`cosmictera/RULES.md` sudah punya lima label dan R2 melarang menaikkannya
tanpa bukti baru. Inventaris ini memakai kelimanya dan tidak menambah yang
keenam:

```
VF  terbukti, bukan diuji sampel        DP  benar karena konstruksinya
CC  dijalankan atas ruang habis         EH  terukur, belum dikriptanalisis
AT  belum dikerjakan
```

Menulis "verified" di sebelahnya akan meninggalkan dua kosakata untuk satu
gagasan — yang `ENGINEERING_STANDARD.md` sebut cacat.

## Tiga jenis verifikasi, dan bedanya adalah intinya

| jenis | artinya |
|---|---|
| `derive` | nilainya **dihitung ulang dari repositori tiap kali tes berjalan**, dan faktanya merah kalau keduanya berselisih. Fakta jenis ini tidak bisa lapuk diam-diam |
| `pytest` | fakta menyebut node tes yang harus ada dan lulus |
| `board` | fakta datang dari Tang Nano 20K dan **tidak bisa dijalankan ulang di sini**. Catatannya buktinya; mengulangnya butuh perangkat kerasnya |

Yang ketiga sengaja tidak berpura-pura. Inventaris yang mengaku sudah
menanyai papan padahal tidak, adalah inventaris yang tidak bisa dipercaya
pada yang lain.

## Isinya hari ini

```bash
PYTHONPATH=src python3 -m hijaiyyah.nui.facts
python3 -m pytest -q tests/test_integrity/test_facts.py
```

**21 fakta di tujuh domain**: 9 dihitung ulang di sini, 7 dibuktikan sebuah
tes, 5 diukur di papan.

```
burnin      counter_wrap_seconds · no_watchdog_exists
crypto      kabah_avalanche_single_bit · kabah_security_rests_on_layer_three ·
            kabah_wrapper_has_no_length_field
fpga        jamrah_sweep_is_exhaustive · jamrah_node_sum ·
            jamrah_gate_is_constant_time · sd_init_fails_after_interrupted_read
hisa        address_unification · no_computed_jump · instruction_memory_words ·
            print_cannot_render_large_values · hijrah_length_one_counts
nui         codex_theta_u_rho_sum · letter_count ·
            exomatrix_embedding_is_the_most_conservative
repository  data_memory_words · four_gates
telemetry   host_time_is_not_the_truth · four_fields_have_no_source
```

**Ini permulaan, bukan seluruh yang terukur di repositori ini.** Fakta
ditambahkan ketika ia punya sumber, bukti, dan cara verifikasi — tidak
sebelum itu.

## Yang dijaga

`tests/test_integrity/test_facts.py`: tiap fakta punya ketujuh medan, tiap
berkas yang dikutip ada, tiap status ada di tabel RULES, tiap fakta `derive`
menghitung ulang ke nilainya, tiap node `pytest` ada di pohon, dan tiap fakta
`board` menyebut perintahnya. Tiga sabotase diuji dan ketiganya merah: nilai
yang tak lagi cocok dengan Master Table, bukti yang berkasnya dihapus, dan
status keenam di luar kosakata.
