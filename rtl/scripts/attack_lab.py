#!/usr/bin/env python3
"""attack_lab.py -- corrupted inputs, aimed at what already has a baseline.

    python3 rtl/scripts/attack_lab.py --target loader --port /dev/tty.usbserial-X
    python3 rtl/scripts/attack_lab.py --target loader          # plan only, no board

The owner's fifth priority. Each earlier validation left a number to compare
against -- Jamrah 256/256, Hijrah equal to the Python, Ka'bah avalanche 0.4995,
the loader refusing a corrupted image -- and the lab exists to push at those
numbers rather than to produce new ones out of nothing.

-- what this is not ------------------------------------------------------
Not a security claim, and not a proof of resistance. It is a set of inputs that
SHOULD be refused, run against the machine to see whether they are. A case that
is accepted is a finding; a case that is refused is one case, not a guarantee.

-- target: loader --------------------------------------------------------
Every case is a container built by rtl/scripts/build_container.py from
rtl/programs/test_from_card.hasm at 0x900, with exactly one field damaged. The
board writes it to the card through sd_writer.hasm and is then asked to load it
with rtl/programs/test_prog_load.hasm, which prints 1 or 0.

The loader's checks are its own (rtl/programs/hos_prog_load.hasm): MAGIC,
VERSION, a non-zero WORDS, the image inside instruction memory, ENTRY inside
the image, RELOC_CNT within the 128-word buffer, enough words on the card, and
the 32-bit sum. The sum covers THE PROGRAM WORDS ONLY -- the owner's decision
of 18 September -- so a case that damages the header or the relocation table
has to be caught by a range check or not at all. Which of those two it is, is
what this run measures.

Records are written to cosmictera-build/attack-lab/ as JSON, one per run.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from build_container import HEADER_WORDS, build  # noqa: E402
from jamrah_board import parse  # noqa: E402
from send_container import chunks, read_line  # noqa: E402
from send_program import encode  # noqa: E402

from hijaiyyah.hisa.assembler import assemble  # noqa: E402

LAB = ROOT / "cosmictera-build" / "attack-lab"
SOURCE = ROOT / "rtl" / "programs" / "test_from_card.hasm"
WRITER = ROOT / "rtl" / "programs" / "sd_writer.hasm"
PROBE = ROOT / "rtl" / "programs" / "test_prog_load.hasm"
LOAD_ADDR = 0x900
ACK_TIMEOUT_S = 5.0


def base_container() -> list[int]:
    return build(SOURCE.read_text(encoding="utf-8"), SOURCE.parent, LOAD_ADDR)


def cases(container: list[int]) -> list[dict[str, object]]:
    """One damaged field each, with the check that should catch it named.

    `expect` is what hos_prog_load.hasm's own checks say should happen. It is a
    prediction, not a verdict: the run measures, and a disagreement is the
    finding.
    """
    reloc_cnt = container[5]
    first_program = HEADER_WORDS + reloc_cnt
    out: list[dict[str, object]] = [
        {"id": "magic_flip", "word": 0, "value": container[0] ^ 1,
         "expect": "reject", "by": "MAGIC"},
        {"id": "version_bump", "word": 1, "value": container[1] + 1,
         "expect": "reject", "by": "VERSION"},
        {"id": "words_zero", "word": 2, "value": 0,
         "expect": "reject", "by": "WORDS = 0"},
        {"id": "words_plus_one", "word": 2, "value": container[2] + 1,
         "expect": "accept",
         "by": "nothing -- the extra word read is the sector's zero padding, "
               "so the sum is unchanged"},
        {"id": "load_addr_past_imem", "word": 3, "value": 4090,
         "expect": "reject", "by": "image past instruction memory"},
        {"id": "entry_outside_image", "word": 4,
         "value": container[3] + container[2] + 4,
         "expect": "reject", "by": "ENTRY outside the image"},
        {"id": "reloc_cnt_over_buffer", "word": 5, "value": 200,
         "expect": "reject", "by": "RELOC_CNT over 128"},
        {"id": "crc_flip", "word": 6, "value": container[6] ^ 1,
         "expect": "reject", "by": "the 32-bit sum"},
        {"id": "program_word_flip", "word": first_program + 1,
         "value": container[first_program + 1] ^ 1,
         "expect": "reject", "by": "the 32-bit sum"},
    ]
    if reloc_cnt:
        out.append({"id": "reloc_index_moved", "word": HEADER_WORDS,
                    "value": (container[HEADER_WORDS] + 1) % container[2],
                    "expect": "accept",
                    "by": "nothing -- the sum covers program words only"})
    return out


def configure(bitstream: Path) -> None:
    subprocess.run(["openFPGALoader", "-b", "tangnano20k", str(bitstream)],
                   check=True, capture_output=True)
    time.sleep(0.8)


def write_container(port: str, words: list[int]) -> bool:
    """sd_writer through the loader, one acknowledged sector at a time."""
    import serial
    plan = chunks(words)
    with serial.Serial(port, 115200, timeout=0.1) as link:
        link.reset_input_buffer()
        link.write(encode(assemble(WRITER.read_text(encoding="utf-8"),
                                   base_dir=WRITER.parent, base=64)))
        link.flush()
        if read_line(link, time.time() + ACK_TIMEOUT_S).strip() != b"0":
            return False
        for i, c in enumerate(plan, 1):
            link.write(c)
            link.flush()
            if read_line(link, time.time() + ACK_TIMEOUT_S).strip() != str(i).encode():
                return False
        return [read_line(link, time.time() + ACK_TIMEOUT_S).strip()
                for _ in range(2)] == [b"1", str(len(plan)).encode()]


def ask_loader(port: str) -> int | None:
    """test_prog_load.hasm: 1 loaded, 0 refused, None if the board said neither."""
    import serial
    stream = encode(assemble(PROBE.read_text(encoding="utf-8"),
                             base_dir=PROBE.parent, base=64))
    raw = bytearray()
    with serial.Serial(port, 115200, timeout=0.2) as link:
        link.reset_input_buffer()
        link.write(stream)
        link.flush()
        deadline = time.time() + 30
        while b"CYCLES=" not in raw and time.time() < deadline:
            raw += link.read(4096)
    values, _, _ = parse(bytes(raw.split(b"CYCLES=")[0]))
    return values[0] if values else None


def run_loader(port: str, bitstream: Path) -> dict[str, object]:
    container = base_container()
    results = []
    for case in cases(container):
        damaged = list(container)
        damaged[int(case["word"])] = int(case["value"]) & 0xFFFFFFFF
        configure(bitstream)
        written = write_container(port, damaged)
        configure(bitstream)
        answer = ask_loader(port) if written else None
        got = {None: "no answer", 0: "reject", 1: "accept"}.get(answer, str(answer))
        results.append({**case, "written": written, "answer": answer, "got": got,
                        "agrees": got == case["expect"]})
        print(f"{case['id']:<24} expect {case['expect']:<7} got {got:<9} "
              f"{'' if got == case['expect'] else '<-- FINDING'}")
    return {"target": "loader", "cases": results}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", default="loader", choices=["loader"])
    ap.add_argument("--port", help="serial device; omit to print the plan only")
    ap.add_argument("--bitstream", type=Path,
                    default=ROOT / "rtl" / "fpga" / "gowin" / "hcpu_gowin_top_loader.fs")
    args = ap.parse_args(argv)

    container = base_container()
    plan = cases(container)
    if args.port is None:
        print(f"{len(plan)} cases against the loader, container of "
              f"{len(container)} words at {LOAD_ADDR:#05x}:")
        for c in plan:
            print(f"  {c['id']:<24} word {c['word']:<3} expect {c['expect']:<7} "
                  f"caught by {c['by']}")
        return 0

    started = datetime.now(timezone.utc)
    record = run_loader(args.port, args.bitstream)
    findings = [c for c in record["cases"] if not c["agrees"]]  # type: ignore[union-attr]
    rejected = sum(1 for c in record["cases"] if c["got"] == "reject")  # type: ignore[union-attr]
    record |= {
        "attack_id": started.strftime("%Y%m%dT%H%M%SZ") + "-loader",
        "timestamp": started.isoformat(),
        "inputs": len(plan),
        "rejected": rejected,
        "accepted": sum(1 for c in record["cases"] if c["got"] == "accept"),  # type: ignore[union-attr]
        "findings": len(findings),
        "board": "Tang Nano 20K",
        "bitstream": str(args.bitstream.relative_to(ROOT)),
    }
    LAB.mkdir(parents=True, exist_ok=True)
    out = LAB / f"{record['attack_id']}.json"
    out.write_text(json.dumps(record, indent=2) + "\n")
    print(f"\n{rejected}/{len(plan)} refused; {len(findings)} case(s) "
          f"disagreed with the loader's own checks")
    print(f"record: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
