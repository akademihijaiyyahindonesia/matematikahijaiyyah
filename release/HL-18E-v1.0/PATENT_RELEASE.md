# OFFICIAL PATENT RELEASE DECLARATION

**Target Dataset:** `Master Table MH-28-v.1.0-HC18D`
**Date of Release:** March 2026
**Author & Copyright:** Maulana Amratulloh, © 2026

## 1. Mathematical Seal

The Hijaiyyah Operating Machine Master Table has been fully standardized and verified against the canonical 28×18 geometric ruleset.

The absolute, final, and cryptographically verified SHA-256 footprint is:
`f82d385917ffe32ae2b5711409b1341e90934c52172ae9d0fa68888e3b9c51c8`

## 2. Artifact Lockdown

By order of this patent release, all underlying data files representing this Master Table are sealed by **measurement**, not by file permissions.

This paragraph previously claimed the files were "permanently locked (Read-Only) at the filesystem level". They were not, and never had been: measured on 11 September 2026, all seven were mode 0o644 or 0o700 — writable by the owner, every one of them. A filesystem bit is in any case the wrong instrument here, because it protects nothing a `git checkout` cannot undo and would break the build the moment `make rom` regenerates `hm28.rom`.

What actually holds is stronger and is checked on every run: `MASTER_TABLE.compute_sha256()` is measured against the seal below in `tests/test_integrity/test_authorship.py`, `data/hm28.json` and `data/hm28_manifest.json` are measured against the same in `tests/test_integrity/test_dataset_consistency.py`, and `hm28.rom` decodes 28/28 back to the table. A modification does not need to be prevented to be caught; it needs to be measured.

The following artifacts are sealed under this release:
- `src/hijaiyyah/core/master_table.py`
- `data/hm28.json`
- `data/hm28.csv`
- `data/hm28_manifest.json`
- `hm28.rom`
- `release/HL-18E-v1.0/MANIFEST.json`
- `release/HL-18E-v1.0/CERTIFICATE.json`

## 3. Patent Protections

The structural components, the multi-dimensional numeric mapping (Θ̂, N, K, Q, A, H*), the derived string integrals, and the execution rules enforced by the codebase are strictly protected intellectual property.

*No cryptographic hashes or geometry key artifacts shall ever be modified.*
