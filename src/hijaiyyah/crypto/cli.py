# -*- coding: utf-8 -*-
"""`kabah` — the system from a shell, with nothing to configure.

Five commands and one key file. The library was already three lines with no
configuration; this is for the case where writing three lines of Python is
three lines too many.

    kabah keygen                    writes ~/.kabah.key, mode 0600
    kabah seal  ledger.txt          → ledger.txt.kbh
    kabah open  ledger.txt.kbh      → ledger.txt
    kabah fingerprint ledger.txt    the [EH] sponge digest
    kabah describe                  every layer and what it guarantees
    kabah memscan dump.raw          find injected regions, recover payloads
    kabah identify fragment.bin     what a headerless fragment is

The key file is the only state. Losing it loses nothing that was encrypted —
nothing here encrypts — but it makes sealed records unverifiable, which for an
integrity system is the same as losing them.
"""

from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from hijaiyyah.crypto.guarded_record import GuardedRecord, reject_degenerate_key
from hijaiyyah.crypto.kabah import EXPANSION, NAME, CryptoRefusal, Kabah, generate_key

#: Where the key lives unless --key says otherwise.
DEFAULT_KEY = Path.home() / ".kabah.key"

#: Suffix for sealed records.
SUFFIX = ".kbh"


def _load_key(path: Path) -> bytes:
    """Read the master key, refusing one the filesystem is sharing."""
    if not path.exists():
        raise CryptoRefusal(
            f"no key at {path} — run `kabah keygen` first, or pass --key"
        )
    mode = path.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise CryptoRefusal(
            f"{path} is readable by others (mode {oct(mode & 0o777)}); "
            "run `chmod 600` on it before using it"
        )
    key = bytes.fromhex(path.read_text(encoding="ascii").strip())
    if len(key) < 16:
        raise CryptoRefusal(f"{path} holds {len(key)} bytes; at least 16 are needed")
    reject_degenerate_key(key, str(path))
    return key


def cmd_keygen(args: argparse.Namespace) -> int:
    path = Path(args.key)
    if path.exists() and not args.force:
        print(
            f"{path} already exists. Overwriting it makes every record sealed "
            "with it unverifiable; pass --force if that is intended.",
            file=sys.stderr,
        )
        return 1
    path.write_text(generate_key().hex() + "\n", encoding="ascii")
    os.chmod(path, 0o600)
    print(f"key written to {path} (mode 600)")
    return 0


def cmd_seal(args: argparse.Namespace) -> int:
    source = Path(args.file)
    target = Path(args.out) if args.out else source.with_suffix(source.suffix + SUFFIX)
    system = Kabah(_load_key(Path(args.key)), args.purpose)
    target.write_bytes(system.seal(source.read_bytes()).to_bytes())
    print(f"{source} → {target}  ({target.stat().st_size} bytes)")
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    source = Path(args.file)
    if args.out:
        target = Path(args.out)
    elif source.suffix == SUFFIX:
        target = source.with_suffix("")
    else:
        target = source.with_suffix(source.suffix + ".opened")

    system = Kabah(_load_key(Path(args.key)), args.purpose, track_replays=False)
    record = GuardedRecord.from_bytes(source.read_bytes())

    if not system.triage(record):
        raise CryptoRefusal("structure rejected before any hash was computed")

    target.write_bytes(system.open(record))
    print(f"{source} → {target}  (verified)")
    return 0


def cmd_fingerprint(args: argparse.Namespace) -> int:
    digest = Kabah.fingerprint(Path(args.file).read_bytes())
    print(f"{digest.hex()}  {args.file}")
    print(
        "[EH] not a vetted hash — use sha256sum for anything that matters",
        file=sys.stderr,
    )
    return 0


def cmd_memscan(args: argparse.Namespace) -> int:
    """Scan a memory or RAM dump, and recover what can be recovered.

    Reads bytes, not operating-system structures: it cannot name a process or
    read page permissions, which is what Volatility is for. What it does is
    find regions whose structure is wrong for where they sit, and restore the
    payload where one is obfuscated.
    """
    from hijaiyyah.crypto.memscan import (
        find_clue,
        recover,
        report,
        to_autopsy_csv,
    )

    data = Path(args.file).read_bytes()
    found = report(data)

    if args.csv:
        print(to_autopsy_csv(found.regions), end="")
        return 0

    print(f"{args.file}  {len(data):,} bytes\n")
    print(f"{'offset':>10} {'length':>9}  {'kind':<14} {'confidence':<10} evidence")
    for region in found.regions:
        print(f"{region.offset:>10} {region.length:>9}  {region.kind:<14} "
              f"{region.confidence:<10} {region.evidence}")

    staged = [r for r in found.regions if r.key]
    if staged:
        print()
        for region in staged:
            payload = recover(data, region)
            clue = find_clue(payload)
            key = region.key or b""
            print(f"  recovered at {region.offset:#x}: key {key.hex()}, "
                  f"{len(payload):,} bytes, {clue or 'unnamed'}")
            if args.out:
                target = Path(f"{args.out}.{region.offset:08x}.bin")
                target.write_bytes(payload)
                print(f"    written to {target}")

    counts = found.summary()
    print(f"\n  {sum(counts.values())} regions: "
          + ", ".join(f"{n}x {k}" for k, n in sorted(counts.items())))
    print("  [CC] structural triage — high entropy is not malice, and nothing "
          "encrypted with a real cipher is recoverable here", file=sys.stderr)
    return 0


def cmd_identify(args: argparse.Namespace) -> int:
    """Name headerless data from the composition of its bytes.

    Where a magic number exists it wins and is reported as the answer — a
    header is better evidence than any statistic. This is for the case where
    there is none: a carved fragment, a memory page, a recovered sector.
    """
    from hijaiyyah.crypto.elements import atoms, identify
    from hijaiyyah.crypto.memscan import find_clue

    data = Path(args.file).read_bytes()
    found = identify(data, clue=find_clue(data[:4096]))

    print(f"{args.file}  {len(data):,} bytes\n")
    print(f"  keluarga   {found.family}   ({found.confidence})")
    if found.marker:
        print(f"  penanda    {found.marker}")
    print()
    for name, value in atoms(data).as_row().items():
        bar = "\u2588" * int(min(value, 8.0) / 8.0 * 28) if name == "entropy" \
            else "\u2588" * int(value * 28)
        print(f"  {name:<10} {value:>7}  {bar}")
    if found.caveat:
        print(f"\n  [CC] {found.caveat}")
    return 0


def cmd_describe(args: argparse.Namespace) -> int:
    info: Dict[str, Any] = Kabah.describe()
    layers: List[Dict[str, Any]] = info["layers"]
    sponge: Dict[str, Any] = info["sponge"]
    seal: str = info["seal"]

    print(f"{NAME} — {EXPANSION}\n")
    print(f"  dataset seal   {seal[:32]}…\n")
    for layer in layers:
        keyed = "berkunci  " if layer["keyed"] else "tanpa kunci"
        print(f"  {layer['index']}  {layer['name']:<13} [{layer['label']:<2}] "
              f"{keyed}  {layer['guarantee']}")
    print(
        f"\n  sponge  state {sponge['state_bits']} bit · rate {sponge['rate_bytes']} B · "
        f"capacity {sponge['capacity_bits']} bit (~{sponge['security_bits']}) · "
        f"{sponge['circuits']} ronde"
    )
    print("\n  Lapis 3 memikul keamanannya. Lapis 1 tanpa kunci — bukan otentikasi.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kabah", description=__doc__)
    parser.add_argument("--key", default=str(DEFAULT_KEY), help="master key file")
    parser.add_argument("--purpose", default="default", help="key domain label")
    sub = parser.add_subparsers(dest="command", required=True)

    keygen = sub.add_parser("keygen", help="write a new master key")
    keygen.add_argument("--force", action="store_true")
    keygen.set_defaults(func=cmd_keygen)

    for name, func, help_text in (
        ("seal", cmd_seal, "encode and authenticate a file"),
        ("open", cmd_open, "verify and recover a file"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("file")
        p.add_argument("--out")
        p.set_defaults(func=func)

    fp = sub.add_parser("fingerprint", help="sponge digest [EH]")
    fp.add_argument("file")
    fp.set_defaults(func=cmd_fingerprint)

    scan = sub.add_parser("memscan", help="find injected regions in a dump")
    scan.add_argument("file")
    scan.add_argument("--out", help="write recovered payloads to this prefix")
    scan.add_argument("--csv", action="store_true", help="Autopsy-shaped CSV")
    scan.set_defaults(func=cmd_memscan)

    ident = sub.add_parser("identify", help="what headerless data is")
    ident.add_argument("file")
    ident.set_defaults(func=cmd_identify)

    sub.add_parser("describe", help="what each layer guarantees").set_defaults(
        func=cmd_describe
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except CryptoRefusal as refusal:
        print(f"kabah: {refusal}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"kabah: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
