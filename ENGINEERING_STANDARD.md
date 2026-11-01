# STANDAR ENGINEERING
# **HOM (Hijaiyyah Operating Machine)**
## Versi 1.1 — 1 September 2026

### Repository: `github.com/hybittech/matematikahijaiyyah.github.io`

---

## 1. IDENTITAS REPOSITORY

| Field | Nilai |
|---|---|
| **Organization** | hybittech |
| **Repository** | matematikahijaiyyah.github.io |
| **Paket** | `hijaiyyah-hom` |
| **Nama Sistem** | Hijaiyyah Operating Machine |
| **Fungsi** | Sistem komputasi inti, bahasa HC, dan RTL HCPU untuk Matematika Hijaiyyah |
| **Bahasa** | Python 3.11+ · Verilog-2001 (RTL) · JavaScript (GUI web) |
| **Layout** | `src/` layout (PEP 517 / PEP 621) |
| **Entry Point** | `hom` · `hc` · `hybit-ai` |
| **Lisensi** | Proprietary — All Rights Reserved (© 2026 Maulana Amratulloh) |

Repositori ini bersifat **publik** (dipublikasikan sebagai GitHub Pages di
hybit.tech). Naskah buku, dokumen paten, dan proposal ditahan di lokal melalui
`.gitignore` dan tidak boleh masuk riwayat git.

---

## 2. POSISI DALAM EKOSISTEM

```text
GitHub Organization: hybittech/
│
├── HOM                        ← repo ini
│   Core computational system + GUI engine
│   Berisi: L0–L7, HC, H-ISA, HCVM, GUI, Audit
│
├── hijaiyyah-mathematics      ← terpisah
│   Teori formal, buku, paper, spesifikasi
│   Berisi: naskah Bab I–V, Origin Protocol, glosarium
│
├── hybit-web                  ← masa depan
│   Frontend / web interface
│
└── hybit-spec                 ← masa depan
    Spesifikasi formal standar terbuka
```

### Aturan Pemisahan

| Aturan | Penjelasan |
|---|---|
| HOM ≠ hijaiyyah-mathematics | sistem ≠ teori |
| HOM berisi kode | hijaiyyah-mathematics berisi naskah |
| HOM berdiri sendiri | bisa di-clone dan dijalankan tanpa repo lain |

---

## 3. STRUKTUR DIREKTORI RESMI

> **Status.** Pohon di bawah ini adalah struktur repositori yang **berlaku**,
> bukan rencana. Ia dijaga oleh `tests/test_integrity/test_engineering_standard.py`:
> setiap berkas yang terdaftar di sini harus ada, dan setiap paket di
> `src/hijaiyyah/` harus terdaftar. Menambah paket baru tanpa memperbarui
> bagian ini akan membuat suite gagal.
>
> Versi 1.0 dokumen ini mendaftar tata letak yang direncanakan pada Maret 2026.
> Tiga puluh berkas di dalamnya tidak pernah ada, dan sepuluh paket yang kini
> berjalan tidak tercantum — termasuk seluruh jalur kompilasi. Bagian ini
> ditulis ulang dari repositori pada 1 September 2026.

```text
hijaiyyah-mathematics/
│
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── AUTHORS
├── NOTICE
├── ENGINEERING_STANDARD.md
├── AGENTS.md                       ← catatan kerja: dasar, nama, alur cerita, aturan
├── CLAUDE.md                       ← hanya memuat AGENTS.md
├── .gitignore
├── .editorconfig
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── hm28.rom                        ← ROM biner Master Table (28 × 144 bit)
│
├── src/
│   └── hijaiyyah/
│       ├── __init__.py
│       ├── __main__.py             ← entry point GUI (`hom`)
│       ├── cli.py                  ← entry point bahasa HC (`hc`)
│       ├── lsp.py                  ← Language Server Protocol untuk .hc
│       ├── version.py
│       │
│       ├── core/                   ← Bab I: codex, guard, tabel tersegel
│       │   ├── __init__.py
│       │   ├── master_table.py     ← SUMBER KEBENARAN 28 × 18
│       │   ├── codex_entry.py
│       │   ├── guards.py           ← G1–G4, T1–T2, compute_U, compute_rho
│       │   ├── hybit.py
│       │   ├── rom.py
│       │   ├── har.py
│       │   ├── hgeo.py
│       │   ├── exomatrix.py
│       │   ├── constants.py
│       │   └── exceptions.py
│       │
│       ├── algebra/                ← Bab II: lima operasi Metrik-Vektorial
│       │   ├── __init__.py
│       │   ├── vektronometry.py    ← VTM — komposisi
│       │   ├── normivektor.py      ← NMV — norma selisih
│       │   ├── aggregametric.py    ← AGM — agregasi string
│       │   ├── intrametric.py      ← ITM — jarak
│       │   ├── exometric.py        ← EXM — konsistensi
│       │   └── _common.py
│       │
│       ├── language/               ← Bab III §IIIF: bahasa HC
│       │   ├── __init__.py
│       │   ├── tokens.py
│       │   ├── lexer.py
│       │   ├── parser.py
│       │   ├── ast_nodes.py
│       │   ├── evaluator.py
│       │   ├── grammar.py
│       │   └── diagnostics.py
│       │
│       ├── compiler/               ← Bab III §IIIG: HCC
│       │   ├── __init__.py         ← pipeline 6 tahap
│       │   └── psi.py              ← tahap 4, Ψ-Injector
│       │
│       ├── assembler/
│       │   └── __init__.py         ← .hasm → .hbc
│       │
│       ├── pipeline/
│       │   └── __init__.py         ← Ψ-Compiler, integrasi CSGI
│       │
│       ├── vm/
│       │   └── __init__.py         ← HVM, runtime perangkat lunak
│       │
│       ├── hisa/                   ← Bab III §IIIF.3.2: H-ISA
│       │   ├── __init__.py
│       │   ├── opcodes.py          ← 28 opcode, encoding kanonik
│       │   ├── registers.py
│       │   ├── machine.py
│       │   ├── assembler.py
│       │   ├── compiler.py
│       │   ├── hbc_format.py
│       │   └── hcheck.py
│       │
│       ├── hisab/                  ← HPACK / HCRC
│       │   ├── __init__.py
│       │   ├── digest.py
│       │   ├── protocol.py
│       │   ├── serialize.py
│       │   └── validate.py
│       │
│       ├── har/
│       │   └── __init__.py         ← HISAB Alphabet Registry
│       │
│       ├── skeleton/               ← Bab I §IC.1.21: CSGI (lapisan L0)
│       │   ├── __init__.py
│       │   ├── skeletonizer.py
│       │   ├── contractor.py
│       │   └── csgi.py
│       │
│       ├── theorems/
│       │   ├── __init__.py
│       │   ├── decomposition.py
│       │   ├── mod4_gate.py
│       │   ├── pythagorean.py
│       │   ├── energy_norm.py
│       │   └── test_suite.py
│       │
│       ├── integrity/
│       │   ├── __init__.py
│       │   ├── injectivity.py
│       │   ├── audit.py
│       │   └── seal.py
│       │
│       ├── crypto/
│       │   ├── __init__.py
│       │   ├── hashing.py
│       │   ├── signing.py
│       │   ├── certificate.py
│       │   ├── guard_filter.py
│       │   ├── guarded_record.py   ← rekaman terjaga, HMAC + HKDF
│       │   ├── cube.py             ← sponge tawaf [EH]
│       │   ├── kabah.py            ← sistem terkomposisi, lima lapis
│       │   └── cli.py              ← entry point `kabah`
│       │
│       ├── net/
│       │   ├── __init__.py
│       │   ├── codec.py
│       │   ├── json_format.py
│       │   └── server.py         ← alias tipis ke receiver/rx.py
│       │
│       ├── receiver/             ← jalur terima: sinyal → rung → kandidat
│       │   ├── __init__.py
│       │   ├── lock.py           ← PhaseLock, tangga perempat-putaran Θ̂
│       │   ├── rx.py             ← RangeReceiver, mode-kunci (dulu HCServer)
│       │   ├── identify.py       ← fase × frekuensi, penyempitan kandidat
│       │   └── tabulate.py       ← bank osilator diturunkan + rekonsiliasi dokumen
│       │
│       ├── release/
│       │   ├── __init__.py
│       │   └── synchronizer.py
│       │
│       ├── ai/                     ← entry point `hybit-ai`
│       │   ├── __init__.py
│       │   ├── __main__.py
│       │   └── runtime.py
│       │
│       ├── nui/                    ← trained side of NUI; needs `pip install .[nui]`
│       │   ├── __init__.py
│       │   ├── features.py         ← titik/garis/lengkung + Theta-hat/rho per letter
│       │   ├── dataset.py          ← accumulation examples, real and synthetic
│       │   ├── model.py            ← physics vs. baseline embedding, sum-pooled
│       │   ├── train.py            ← `python3 -m hijaiyyah.nui.train`
│       │   ├── claims.py           ← tests external "Codex NUI" doc claims against sealed data
│       │   └── pattern_language.py ← tests order effects on GF(2) exomatrix composition
│       │
│       └── gui/
│           ├── __init__.py
│           ├── app.py
│           ├── theme.py
│           ├── widgets.py
│           ├── assets/
│           └── tabs/
│               ├── __init__.py
│               ├── letter_explorer.py
│               ├── master_table.py
│               ├── theorems.py
│               ├── string_integral.py
│               ├── audit.py
│               ├── five_fields.py
│               ├── geometry.py
│               ├── ide.py
│               ├── hisa_machine.py
│               ├── hisab.py
│               ├── bytecode.py
│               ├── csgi.py
│               ├── export.py
│               └── release.py
│
├── rtl/                            ← Bab III §IIIJ: HCPU
│   ├── hcpu_pkg.vh                 ← parameter dan encoding opcode
│   ├── hcpu_top.v
│   ├── hcpu_rom.v                  ← Master Table sebagai ROM
│   ├── hcpu_guard.v                ← G1–G4, T1–T2 dalam satu siklus
│   ├── hcpu_codex_alu.v
│   ├── hcpu_hisab.v
│   ├── hcpu_*.v                    ← fetch, decode, memory, regfile, …
│   ├── tb/                         ← testbench + Makefile
│   ├── fpga/gowin/                 ← Tang Nano 20K
│   └── mpw/                        ← sintesis dan laporan
│
├── data/
│   ├── hm28.json
│   ├── hm28.csv
│   ├── hm28_manifest.json
│   ├── Master Table HM-28-v.1.0-HC18D.pdf
│   ├── kfgqpc/
│   └── logo/
│
├── tests/                          ← cermin struktur src/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_core/
│   ├── test_algebra/
│   ├── test_language/
│   ├── test_compiler/
│   ├── test_assembler/
│   ├── test_hisa/
│   ├── test_hisab/
│   ├── test_har/
│   ├── test_vm/
│   ├── test_pipeline/
│   ├── test_ai/
│   ├── test_theorems/
│   ├── test_integration/
│   └── test_integrity/             ← paritas lintas implementasi
│
├── docs/
├── examples/                       ← *.hc, *.hcai
├── editors/vscode/                 ← pewarnaan sintaks + klien LSP
├── hom-gui/                        ← GUI web (mesin JavaScript)
├── Hybit/                          ← naskah Bab III
├── tools/
│   ├── codex_calculator.py
│   ├── table_verifier.py
│   ├── rom_generator.py
│   ├── csgi_pipeline.py
│   └── benchmark.py
│
└── release/
```

---

### Aturan Penempatan

| Kalau modul itu … | Letaknya di … |
|---|---|
| mendefinisikan atau memvalidasi codex | `core/` |
| salah satu dari lima operasi Bab II | `algebra/` |
| memproses teks `.hc` | `language/` |
| mengubah AST menjadi instruksi | `compiler/` |
| menyangkut encoding instruksi 32-bit | `hisa/` |
| mengeksekusi bytecode di perangkat lunak | `vm/` |
| mengubah citra glyph menjadi graf | `skeleton/` |
| memeriksa dua implementasi agar sepakat | `tests/test_integrity/` |

**Aturan tunggal yang mengikat:** satu invarian, satu definisi. `U`, guard, encoding
opcode, dan tabel induk masing-masing ditulis **satu kali**; tempat lain memanggilnya.
Pelanggaran aturan ini adalah sumber setiap divergensi yang pernah terjadi di
proyek ini, dan dijaga oleh `test_single_source_of_truth.py`.

---

## 4. FILE KONFIGURASI WAJIB

---

### 4.1 `pyproject.toml`

```toml
[project]
name = "hijaiyyah-hom"
version = "1.0.0"
description = "Hijaiyyah Operating Machine — Core Computational System"
authors = [
    { name = "Maulana Amratulloh" },
    { name = "Hijaiyyah Mathematical Computing Laboratory (HMCL)" }
]
requires-python = ">=3.11"
license = { text = "Proprietary" }

dependencies = [
    "numpy>=1.24",
    "networkx>=3.0",
    "pillow>=10.0",
    "scipy>=1.10",
]

[project.scripts]
hom = "hijaiyyah.__main__:main"

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1",
    "mypy>=1.0",
]

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pyright]
include = ["src", "tests", "tools", "scripts"]
extraPaths = ["src"]
typeCheckingMode = "basic"
reportMissingImports = true
reportMissingModuleSource = false
pythonVersion = "3.11"
executionEnvironments = [
    { root = ".", extraPaths = ["src"] }
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

---

### 4.2 `requirements.txt`

```text
numpy>=1.24
networkx>=3.0
pillow>=10.0
scipy>=1.10
```

---

### 4.3 `requirements-dev.txt`

```text
pytest>=7.0
pytest-cov>=4.0
ruff>=0.1
mypy>=1.0
```

---

### 4.4 `.gitignore`

```text
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.eggs/
venv/
.venv/
.env
*.log
*.swp
*.swo
.DS_Store
Thumbs.db
.idea/
.vscode/
*.rom.bak
```

---

### 4.5 `.editorconfig`

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.md]
trim_trailing_whitespace = false

[*.toml]
indent_size = 2

[*.json]
indent_size = 2
```

---

## 5. ENTRY POINT

### `src/hijaiyyah/__main__.py`

```python
# -*- coding: utf-8 -*-
"""Entry point for HOM (Hijaiyyah Operating Machine)."""


def main():
    from hijaiyyah.gui.app import HOMApp
    app = HOMApp()
    app.run()


if __name__ == "__main__":
    main()
```

---

### `src/hijaiyyah/__init__.py`

```python
# -*- coding: utf-8 -*-
"""Hijaiyyah Mathematics — HOM Core Package."""

from .version import __version__

__all__ = ["__version__"]
```

---

### `src/hijaiyyah/version.py`

Dua nomor yang bergerak sendiri-sendiri, dan itu disengaja. Versi perangkat
lunak naik saat kode berubah; identitas dataset hanya berubah kalau Master
Table dirilis ulang — dan Master Table dikunci oleh dokumen kanonik.
Menggabungkan keduanya berarti sebuah perbaikan bug akan tampak seperti
perubahan pada huruf.

```python
# -*- coding: utf-8 -*-
"""Version information for HOM (Hijaiyyah Operating Machine)."""

# HOM software release (SemVer).
__version__ = "1.2.0"

# Sealed Master Table shipped with this software. This is the DATASET
# identifier and moves independently of __version__ — it is fixed by the
# canonical document "Master Table HM-28-v.1.0-HC18D".
__dataset_release__ = "HM-28-v.1.0-HC18D"

# Software-side release tag.
__release__ = "HM-28-v1.2-HC18D"
```

Sinkronisasinya dijaga oleh `tests/test_integrity/test_version_consistency.py`.

---

## 6. CARA MENJALANKAN

### 6.1 Pemasangan

```bash
cd hijaiyyah-mathematics
pip install -e ".[dev]"
```

### 6.2 Tiga entry point

Terdaftar di `[project.scripts]` pada `pyproject.toml`.

| Perintah | Modul | Fungsi |
|---|---|---|
| `hom` | `hijaiyyah.__main__:main` | GUI desktop (Tkinter) |
| `hc` | `hijaiyyah.cli:main` | bahasa HC — `run`, `check`, `repl`, `lsp` |
| `hybit-ai` | `hijaiyyah.ai.__main__:main` | runtime AI lokal |
| `kabah` | `hijaiyyah.crypto.cli:main` | sistem integritas Ka'bah — `keygen`, `seal`, `open`, `fingerprint`, `describe`, `memscan`, `identify`, `examine`, `sign`, `verify`, `manifest` |

```bash
hc run examples/hello.hc
hc check examples/five_fields_demo.hc
python -m hijaiyyah              # setara dengan `hom`
```

### 6.3 Pengujian

```bash
pytest                           # suite Python
cd rtl/tb && make                # testbench RTL (perlu iverilog)
```

Keduanya adalah gerbang rilis. Suite Python memeriksa perangkat lunak;
testbench RTL memeriksa perangkat keras; dan `tests/test_integrity/`
memeriksa bahwa keduanya sepakat.

### 6.4 Linting

```bash
ruff check .
```

### 6.5 Type checking

```bash
mypy src/hijaiyyah
```

`pyright` juga terkonfigurasi di `pyproject.toml`, tetapi **mypy** adalah
gerbang yang dijalankan CI (`.github/workflows/test.yml`). Kalau hanya satu
yang sempat dijalankan, jalankan mypy.

---

## 7. ATURAN CODING

---

### 7.1 Bahasa dan encoding

| Aturan | Nilai |
|---|---|
| Encoding file | UTF-8 |
| Line ending | LF |
| Max line length | 100 karakter |
| Python version | 3.11+ |
| Docstring style | Google style |
| Type hints | wajib untuk function signatures |

---

### 7.2 Penamaan

| Objek | Konvensi | Contoh |
|---|---|---|
| File/modul | `snake_case` | `master_table.py` |
| Kelas | `PascalCase` | `MasterTable` |
| Fungsi/method | `snake_case` | `get_by_char()` |
| Konstanta | `UPPER_SNAKE` | `H28_ALPHABET` |
| Variabel lokal | `snake_case` | `entry_count` |
| Private | `_prefix` | `_load()` |
| Dunder | `__name__` | `__init__()` |

---

### 7.3 Import

```python
# stdlib first
import hashlib
import json
from typing import Dict, List, Optional

# third-party
import numpy as np

# internal
from hijaiyyah.core.master_table import MasterTable
from hijaiyyah.core.codex_entry import CodexEntry
```

Jangan gunakan:
```python
from module import *
```

---

### 7.4 Docstring setiap file

Setiap file Python wajib memiliki docstring di baris pertama:

```python
# -*- coding: utf-8 -*-
"""
Module description.
"""
```

---

### 7.5 Error handling

Gunakan exception kustom:

```python
from hijaiyyah.errors import HijaiyyahError
```

Bukan `raise Exception(...)`.

---

## 8. ATURAN ARSITEKTUR

---

### 8.1 Pemisahan layer

| Layer | Fungsi | Boleh mengakses |
|---|---|---|
| `core/` | data formal, codex, guard | tidak ada layer lain |
| `algebra/` | operasi Bab II | `core/` |
| `integrity/` | audit, injectivity | `core/` |
| `theorems/` | theorem checks | `core/`, `algebra/` |
| `language/` | HC lexer, parser, evaluator | `core/`, `algebra/` |
| `hisa/` | ISA machine | `core/` |
| `skeleton/` | CSGI | `core/` |
| `crypto/` | hash, sign | `core/` |
| `net/` | data exchange | `core/`, `crypto/` |
|  `receiver/` | fase → rung, frekuensi → periode, penerima mode-kunci | `core/` |
| `release/` | versioning | `core/`, `crypto/` |
| `gui/` | tampilan | semua layer |

### 8.2 Prinsip utama

| Prinsip | Penjelasan |
|---|---|
| GUI tidak boleh menghitung | logika domain harus di service/algebra/core |
| Core tidak boleh import GUI | dependency satu arah |
| Setiap modul harus bisa diuji tanpa GUI | pure function > side effect |
| Setiap tab GUI harus file terpisah | satu tab = satu file |

---

## 9. ATURAN TESTING

---

### 9.1 Wajib ada test untuk:

| Modul | Test minimum |
|---|---|
| `core/master_table` | jumlah entri, panjang vektor, guard, injektivitas |
| `algebra/*` | satu test per fungsi utama |
| `language/lexer` | tokenisasi dasar, Hijaiyyah literal, error case |
| `language/parser` | parse let, fn, if, method call |
| `integrity/` | injectivity, seal |
| `theorems/` | full suite 13 test |

### 9.2 Golden test
Untuk output yang harus stabil, gunakan golden file:

```text
tests/golden/
    letter_ba.json
    string_bsm.json
    theorem_results.json
```

---

## 10. ATURAN GIT

---

### 10.1 Branching

| Branch | Fungsi |
|---|---|
| `main` | stable release |
| `dev` | development aktif |
| `feature/*` | fitur baru |
| `fix/*` | perbaikan bug |
| `release/*` | persiapan rilis |

### 10.2 Commit message

Format:

```text
[module] short description

- detail 1
- detail 2
```

Contoh:

```text
[core] fix master table guard validation

- added checksum verification on load
- added topology guard for Ks/Kc
```

### 10.3 Yang tidak boleh di-commit

| File/Folder | Alasan |
|---|---|
| `__pycache__/` | cache Python |
| `*.pyc` | bytecode |
| `venv/` | environment lokal |
| `.env` | secrets |
| `dist/` | build output |
| `build/` | build output |
| `*.log` | log runtime |
| `.vscode/` | setting lokal |

---

## 11. ATURAN RELEASE

---

### 11.1 Release checklist

Sebelum release:

1. semua test PASS,
2. SHA-256 master table dihitung ulang,
3. MANIFEST.json diperbarui,
4. RELEASE_NOTES.md ditulis,
5. version.py diperbarui,
6. CHANGELOG.md diperbarui,
7. tag git dibuat.

### 11.2 Versioning

Gunakan **Semantic Versioning**:

```text
MAJOR.MINOR.PATCH
```

Contoh:
- `1.0.0` — rilis pertama
- `1.1.0` — fitur baru
- `1.0.1` — bugfix

### 11.3 Tag

```bash
git tag -a v1.0.0 -m "HOM v1.0.0 — Initial Release"
git push origin v1.0.0
```

---

## 12. ATURAN DOKUMENTASI

---

### 12.1 Wajib ada di `docs/`:

| File | Isi |
|---|---|
| `architecture.md` | L0–L7, flow, diagram |
| `hc_language.md` | sintaks, tipe, contoh |
| `hisa_spec.md` | ISA, opcode, register |
| `csgi_spec.md` | pipeline skeleton |
| `hcvm_spec.md` | VM model |
| `release_policy.md` | kebijakan rilis |
| `changelog.md` | catatan perubahan |

### 12.2 README.md wajib berisi:

1. judul dan deskripsi singkat,
2. cara install,
3. cara menjalankan,
4. cara testing,
5. struktur direktori,
6. lisensi,
7. link ke dokumentasi.

---

## 13. ATURAN KEAMANAN

---

### 13.1 File `SECURITY.md`

Isi minimal:
- cara melaporkan kerentanan,
- kebijakan penanganan.

### 13.2 Tidak boleh di-commit:

| Data | Alasan |
|---|---|
| API key | sensitif |
| Private key | sensitif |
| Password | sensitif |
| `.env` file | berisi secrets |

### 13.3 Guard ≠ kriptografi penuh

Ini harus dipahami seluruh tim:
- guard = validasi struktural,
- HGSS = crypto layer,
- keduanya **bukan** pengganti PKI/TLS/SSL untuk komunikasi jaringan.

---

## 14. WORKFLOW GITHUB

---

### 14.1 Inisialisasi

```bash
git init
git add .
git commit -m "[init] HOM core system initialized"
git remote add origin https://github.com/hybittech/HOM.git
git branch -M main
git push -u origin main
```

### 14.2 CI minimal (GitHub Actions)

Buat file `.github/workflows/test.yml`:

```yaml
name: Test Suite

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run tests
        run: pytest --tb=short -q

      - name: Lint
        run: ruff check src/
```

---

## 15. CHECKLIST SEBELUM PUSH PERTAMA

| No | Item | Status |
|---|---|---|
| 1 | `README.md` ada dan informatif | ☐ |
| 2 | `LICENSE` ada | ☐ |
| 3 | `.gitignore` ada dan benar | ☐ |
| 4 | `pyproject.toml` lengkap | ☐ |
| 5 | `src/hijaiyyah/__main__.py` berfungsi | ☐ |
| 6 | `src/hijaiyyah/__init__.py` ada | ☐ |
| 7 | `src/hijaiyyah/version.py` ada | ☐ |
| 8 | `src/hijaiyyah/core/master_table.py` berfungsi | ☐ |
| 9 | `tests/test_core/test_master_table.py` PASS | ☐ |
| 10 | `python -m hijaiyyah` berjalan | ☐ |
| 11 | Tidak ada file sensitif di repo | ☐ |
| 12 | Tidak ada `__pycache__` di repo | ☐ |

---

## 16. RINGKASAN SATU HALAMAN

### Repo ini:
- **nama**: `hybittech/HOM`
- **isi**: core system + GUI Matematika Hijaiyyah
- **layout**: `src/` layout (PEP 517)
- **entry**: `python -m hijaiyyah`
- **test**: `pytest`
- **lint**: `ruff`
- **type**: `pyright`
- **CI**: GitHub Actions

### Prinsip utama:
1. **GUI terpisah dari logic** — GUI hanya merender,
2. **Core tidak import GUI** — dependency satu arah,
3. **Setiap modul bisa diuji sendiri** — tanpa GUI,
4. **Setiap tab satu file** — modular,
5. **Test wajib ada** — sebelum push,
6. **Commit message standar** — `[module] description`,
7. **Release terstruktur** — manifest, certificate, tag.

---
