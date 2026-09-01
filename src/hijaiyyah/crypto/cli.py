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
