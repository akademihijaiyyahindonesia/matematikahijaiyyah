#!/usr/bin/env python3
"""attack_lab.py -- corrupted inputs, aimed at what already has a baseline.

    python3 rtl/scripts/attack_lab.py --target loader --port /dev/tty.usbserial-X
    python3 rtl/scripts/attack_lab.py --target jamrah --port /dev/tty.usbserial-X
    python3 rtl/scripts/attack_lab.py --target kabah  --port /dev/tty.usbserial-X
    python3 rtl/scripts/attack_lab.py --target loader --source jim5   # class D
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
Every case starts from a container built by rtl/scripts/build_container.py
from rtl/programs/test_from_card.hasm at 0x900. The board writes it to the
card through sd_writer.hasm and is then asked to load it with
rtl/programs/test_prog_load.hasm, which prints 1 or 0.

Since P6 (26 September 2026) the loader's integrity check is CHECKSUM32, the
owner's K-8 and K-10: one 32-bit sum over the sector-16 table entry, the header
with its own checksum field counted as zero, the relocation table and the
program words. The cases follow the owner's six categories -- header,
program table, relocation table, program body, the checksum field itself, and
what lies outside the container -- plus the range checks that were already
there, and two cases that show where a sum's cover ends.

Each case carries the owner's INTENT for its category, and its EXPECT is not
written by hand: it is what the Python loader in build_container.py says
about the very card image the case describes. tests/test_integrity/
test_checksum32.py holds EXPECT to the intent and the simulated HCPU loader to
EXPECT; the board is held to it here. A case sd_writer cannot put on a card --
another table entry, another sector -- is marked so and runs in Python and the
simulation only.

-- target: jamrah --------------------------------------------------------
The gate's whole input space is 256 bytes and cosmictera-build/validasi/JAMRAH.md
already ran all of them, five times, 256/256. What that report measured in time
was ONE number for the whole pass -- 9,218 clocks, 36.01 per byte. So what is
left to attack is not coverage but LATENCY, and rtl/programs/jamrah_gate.hasm
makes a claim about it in its own comment:

    "A gate that branches on its input takes a different number of cycles for
     different bytes, and that is a timing channel on the very check meant to
     be cheap and uniform."

This times each byte on its own, between two reads of the free-running counter
at 0xFF4, and asks whether the 256 numbers are one number. A run also carries
its own control (R3): the SAME predicate written as a comparison loop, which is
what the branchless form was chosen over. If the harness cannot see a
difference there, a constant reading from the real gate would prove nothing.
The control is this lab's, generated here, and is not a variant of the gate the
project ships.

-- target: kabah, and the codex source -----------------------------------
Both are described where they are implemented, further down: the kabah class
bends the input past the single-bit flip KABAH.md measured, and --source jimN
replaces the random generator with Jim's machine so the two can be compared.

Records are written to cosmictera-build/attack-lab/ as JSON, one per run.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from build_container import (  # noqa: E402
    HEADER_WORDS,
    MASK,
    TABLE_SECTOR,
    build,
    card_image,
    load_check,
    seal,
    table_record,
)
from jamrah_board import GATE, gate_body, parse  # noqa: E402
from jamrah_board import run_board as run_program  # noqa: E402
from jim_stream import PERIODS, stream  # noqa: E402
from kabah_board import STATE_BITS, distance, flip  # noqa: E402
from kabah_uart_test import RATE, STATE_BYTES, expected_states  # noqa: E402
from send_container import chunks, read_line  # noqa: E402
from send_program import encode  # noqa: E402

from hijaiyyah.core.master_table import MASTER_TABLE  # noqa: E402
from hijaiyyah.hisa.assembler import assemble  # noqa: E402
from hijaiyyah.hisa.machine import HISAMachine  # noqa: E402

LAB = ROOT / "cosmictera-build" / "attack-lab"
SOURCE = ROOT / "rtl" / "programs" / "test_from_card.hasm"
WRITER = ROOT / "rtl" / "programs" / "sd_writer.hasm"
PROBE = ROOT / "rtl" / "programs" / "test_prog_load.hasm"
LOAD_ADDR = 0x900
ACK_TIMEOUT_S = 5.0
OSC_HZ = 27_000_000      # hcpu_gowin_top.v, USE_PLL = 0

# Free data memory for the jamrah timing pass: clear of the relocation buffer
# (0x300-0x37F), the HOS heap (0xE01-0xE7F) and the MMIO window (0xFF0+).
TIME_AT, PULSE_AT, SCRATCH_AT = 0x400, 0x600, 0x500

# cosmictera-build/validasi/KABAH.md, measured on the board 20 September 2026.
KABAH_BASELINE = 0.4995

DEFAULT_BITSTREAM = {
    "loader": "hcpu_gowin_top_loader.fs",
    "jamrah": "hcpu_gowin_top_loader.fs",
    "kabah": "hijaiyyah_kabah_gowin_top.fs",
}


def base_container() -> list[int]:
    return build(SOURCE.read_text(encoding="utf-8"), SOURCE.parent, LOAD_ADDR)


#: The owner's six categories for P6, 26 September 2026, and what each must
#: do. Two more are the lab's own: the untouched container, and the limit of a
#: sum -- a check anyone can recompute, and that does not see order.
INTENT = {"control": "accept", "header": "reject", "program-table": "reject",
          "relocation": "reject", "program-body": "reject",
          "checksum-field": "reject", "out-of-container": "accept",
          "limit-of-a-sum": "accept"}


def _case(cid: str, category: str, stream: list[int], why: str,
          card: dict[int, list[int]] | None = None,
          word: int | None = None) -> dict[str, object]:
    """One case: what goes to sd_writer, the card it makes, and the verdict the
    Python loader gives that card."""
    card = card if card is not None else card_image(stream)
    ok, reason = load_check(card)
    return {"id": cid, "category": category, "intent": INTENT[category],
            "expect": "accept" if ok else "reject", "by": reason, "why": why,
            "stream": [w & MASK for w in stream], "card": card,
            "board": card == card_image(stream), "word": word}


def cases(container: list[int]) -> list[dict[str, object]]:
    """Every loader case, the owner's six categories and the range checks."""
    reloc_cnt = container[5]
    first = HEADER_WORDS + reloc_cnt
    entry = table_record(len(container))

    def one(cid: str, category: str, word: int, value: int, why: str) -> dict[str, object]:
        stream = list(container)
        stream[word] = value & MASK
        return _case(cid, category, stream, why, word=word)

    def sealed_for(cid: str, record: list[int], why: str) -> dict[str, object]:
        return _case(cid, "program-table", seal(container, record), why)

    swapped = list(container)
    a, b = first, next(i for i in range(first + 1, len(container))
                       if container[i] != container[first])
    swapped[a], swapped[b] = swapped[b], swapped[a]
    changed = list(container)
    changed[first + 1] ^= 1
    other_entry = card_image(container)
    other_entry[TABLE_SECTOR][4:8] = [7, 1, 21, 1]
    other_sector = card_image(container)
    other_sector[21] = [0xA5A5A5A5] * 128

    return [
        _case("intact", "control", list(container), "the container as built"),
        one("magic_flip", "header", 0, container[0] ^ 1, "MAGIC"),
        one("version_one", "header", 1, 1, "a version-1 container"),
        one("words_zero", "header", 2, 0, "WORDS = 0"),
        one("words_plus_one", "header", 2, container[2] + 1,
            "the extra word is zero padding; version 1 accepted it"),
        one("load_addr_minus_one", "header", 3, container[3] - 1,
            "ENTRY is still inside the moved image, so only the sum can see it"),
        one("load_addr_past_imem", "header", 3, 4090, "the image runs past IMEM"),
        one("entry_plus_one", "header", 4, container[4] + 1,
            "still inside the image, so only the sum can see it"),
        one("entry_outside_image", "header", 4, container[3] + container[2] + 4,
            "ENTRY outside the image"),
        one("reloc_cnt_over_buffer", "header", 5, 200, "RELOC_CNT over 128"),
        sealed_for("table_flags_bit_one", [entry[0], entry[1] | 2, entry[2], entry[3]],
                   "sealed for FLAGS 3; sd_writer writes FLAGS 1 -- the entry on the "
                   "card is not the entry sealed"),
        sealed_for("table_sector_count", [entry[0], entry[1], entry[2], entry[3] + 1],
                   "sealed for one more sector than the card's entry names"),
        one("reloc_index_moved", "relocation", HEADER_WORDS,
            (container[HEADER_WORDS] + 1) % container[2],
            "a relocation aimed at another word; version 1 accepted it"),
        one("program_word_flip", "program-body", first + 1, container[first + 1] ^ 1,
            "one bit of one program word"),
        one("checksum_flip", "checksum-field", 6, container[6] ^ 1,
            "one bit of CHECKSUM32"),
        one("checksum_by_version_one_rule", "checksum-field", 6,
            sum(container[first:]) & MASK, "sealed by version 1's rule, program words only"),
        _case("words_after_container", "out-of-container",
              [*container, 0xDEADBEEF, 0x12345678],
              "two words past the container, inside its last sector"),
        _case("another_table_entry", "out-of-container", list(container),
              "a second VALID entry in sector 16", card=other_entry),
        _case("another_sector", "out-of-container", list(container),
              "sector 21, which no entry names, filled", card=other_sector),
        _case("words_swapped", "limit-of-a-sum", swapped,
              "two different program words exchanged: the sum does not see order"),
        _case("body_changed_and_resealed", "limit-of-a-sum",
              seal(changed, entry),
              "one program word changed and CHECKSUM32 recomputed: a sum is public"),
    ]


def jim_cases(container: list[int], src: JimSource,
              count: int) -> list[dict[str, object]]:
    """Class D at the loader: the damaged word and its new value both come from
    the codex stream, and every one of them lands where the 32-bit sum reaches.

    So the prediction for all of them is the same -- refused -- and the target
    the owner set for this class is 100%. A case that is accepted would mean
    two program images with the same 32-bit sum, which is the one thing this
    integrity check is there to prevent.
    """
    first = HEADER_WORDS + container[5]
    words = len(container) - first
    out: list[dict[str, object]] = []
    while len(out) < count:
        index = first + src.randrange(words)
        value = src.randrange(1 << 32)
        if value == container[index]:
            continue
        stream = list(container)
        stream[index] = value
        out.append(_case(f"jim{src.field}_{len(out):02d}_word_{index}",
                         "program-body", stream, "a codex-stream value in a program word",
                         word=index))
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


def run_loader(port: str, bitstream: Path,
               plan: list[dict[str, object]] | None = None) -> dict[str, object]:
    container = base_container()
    results = []
    for case in plan if plan is not None else cases(container):
        kept = {k: v for k, v in case.items() if k not in ("stream", "card")}
        if not case["board"]:
            results.append({**kept, "written": False, "answer": None, "got": "not run",
                            "agrees": None,
                            "skipped": "sd_writer writes one table entry and the "
                                       "container's own sectors; this card needs more"})
            print(f"{case['id']:<30} not run on the board: {case['why']}")
            continue
        configure(bitstream)
        written = write_container(port, list(case["stream"]))  # type: ignore[call-overload]
        configure(bitstream)
        answer = ask_loader(port) if written else None
        got = {None: "no answer", 0: "reject", 1: "accept"}.get(answer, str(answer))
        results.append({**kept, "written": written, "answer": answer, "got": got,
                        "agrees": got == case["expect"]})
        print(f"{case['id']:<30} expect {case['expect']:<7} got {got:<9} "
              f"{'' if got == case['expect'] else '<-- FINDING'}")
    ran = [r for r in results if r["got"] != "not run"]
    return {
        "target": "loader",
        "cases": results,
        "inputs": len(ran),
        "not_run": len(results) - len(ran),
        "rejected": sum(1 for r in ran if r["got"] == "reject"),
        "accepted": sum(1 for r in ran if r["got"] == "accept"),
        "findings": sum(1 for r in ran if not r["agrees"]),
    }


# -- target: jamrah -------------------------------------------------------

# The predicate the gate computes, written the way the gate's own comment says
# it was NOT written: a loop that stops as soon as it matches. Same answer for
# all 256 bytes, and a different number of cycles for nearly every one. It is
# the control, not a proposal -- rtl/programs/jamrah_gate.hasm stays as it is.
CHAIN_CONTROL = """        MOVI  R3, 0
        MOVI  R6, 1
c_scan: CMP   R1, R6
        JEQ   c_hit
        ADDI  R6, R6, 1
        CMPI  R6, 29
        JNE   c_scan
        JMP   c_done
c_hit:  MOVI  R3, 1
c_done: NOP"""


def timed_sweep(inner: str) -> str:
    """256 bytes, each timed on its own, then the numbers printed.

    The counter is read immediately before and after `inner`, so what lies
    inside the window is `inner` plus two fixed instructions -- the same two
    for every byte. Byte-to-byte differences are therefore `inner`'s own. Every
    register but R0 belongs to the gate body, so the loop keeps its counter in
    R0 and its first reading in memory.
    """
    return f"""; GENERATED by rtl/scripts/attack_lab.py. Do not edit.
        MOVI  R0, 0
t_loop: MOV   R1, R0
        MOVI  R5, 0
        LOAD  R4, R5, 0xFF4         ; counter before this byte
        STORE R4, R5, {SCRATCH_AT:#05x}
{inner}
        MOVI  R5, 0
        LOAD  R4, R5, 0xFF4         ; counter after it
        LOAD  R12, R5, {SCRATCH_AT:#05x}
        SUB   R4, R4, R12
        STORE R4, R0, {TIME_AT:#05x}
        STORE R3, R0, {PULSE_AT:#05x}
        ADDI  R0, R0, 1
        CMPI  R0, 256
        JNE   t_loop

        MOVI  R0, 0
p_loop: LOAD  R1, R0, {TIME_AT:#05x}
        PRINT R1                    ; the byte's own count, in the counter's unit
        LOAD  R1, R0, {PULSE_AT:#05x}
        PRINT R1                    ; and its pulse
        ADDI  R0, R0, 1
        CMPI  R0, 256
        JNE   p_loop
        HALT
"""


def split_pairs(values: list[int]) -> tuple[list[int], list[int]]:
    if len(values) != 512:
        raise ValueError(f"expected 512 printed values, got {len(values)}")
    return values[0::2], values[1::2]


def jamrah_measure(values: list[int], unit: str) -> dict[str, object]:
    """Pass, reject, and the spread of the per-byte counts."""
    counts, pulses = split_pairs(values)
    wrong = [b for b in range(256) if pulses[b] != int(1 <= b <= 28)]
    spread = sorted(set(counts))
    return {
        "unit": unit,
        "inputs": 256,
        "accepted": sum(pulses),
        "rejected": 256 - sum(pulses),
        "pulse_disagreements": wrong,
        "distinct_counts": len(spread),
        "min": spread[0],
        "max": spread[-1],
        "mean": sum(counts) / len(counts),
        "counts": counts,
    }


def run_jamrah(port: str | None, bitstream: Path,
               runs: int = 1) -> dict[str, object]:
    """The gate over all 256 bytes, `runs` times, then its control once.

    Repeated because a single constant reading could be a counter that stopped
    rather than a gate that is uniform; JAMRAH.md took the same precaution with
    its five runs.
    """
    body = "\n".join(gate_body(GATE.read_text(encoding="utf-8")))
    out: dict[str, object] = {"target": "jamrah"}

    def sweep(inner: str) -> dict[str, object]:
        program = timed_sweep(inner)
        if port is None:
            machine = HISAMachine(MASTER_TABLE)
            machine.load_program(assemble(program))
            machine.run()
            return jamrah_measure(list(machine.output), "instructions")
        configure(bitstream)
        values, dropped, junk = run_program(port, program, timeout_s=60.0)
        measured = jamrah_measure(values, "clocks")
        measured |= {"dropped_bytes": dropped,
                     "rejected_lines": [bytes(x).decode("latin-1") for x in junk]}
        return measured

    gate_runs = [sweep(body) for _ in range(runs)]
    for i, m in enumerate(gate_runs, 1):
        print(f"gate run {i:<9} {m['distinct_counts']:>3} distinct "
              f"{m['unit']:<12} min {m['min']:>4} max {m['max']:>4}   "
              f"pulse {m['accepted']}/28 accepted, "
              f"{len(m['pulse_disagreements'])} disagree")  # type: ignore[arg-type]
    control = sweep(CHAIN_CONTROL)
    print(f"chain_control   {control['distinct_counts']:>3} distinct "
          f"{control['unit']:<12} min {control['min']:>4} max {control['max']:>4}   "
          f"pulse {control['accepted']}/28 accepted, "
          f"{len(control['pulse_disagreements'])} disagree")  # type: ignore[arg-type]
    first = gate_runs[0]
    constant = all(m["distinct_counts"] == 1 for m in gate_runs)
    out |= {
        "gate_runs": gate_runs, "gate": first, "chain_control": control,
        "runs_identical": all(m["counts"] == first["counts"] for m in gate_runs),
        "runs": runs,
        "inputs": 256 * runs,
        "accepted_per_run": first["accepted"],
        "rejected_per_run": first["rejected"],
        "clocks_per_byte": first["min"] if constant else None,
        "control_distinct_counts": control["distinct_counts"],
        "constant_time": constant,
        "findings": 0 if constant and int(control["distinct_counts"]) > 1 else 1,
    }
    return out


# -- the generator ---------------------------------------------------------


class JimSource:
    """random.Random's surface, fed by Jim's machine instead of Mersenne.

    The owner's class D: the cases come from the codex stream rather than from
    a random number generator. It is deterministic and periodic -- 155 bytes
    over GF(2), 3,124 over GF(5), both measured by rtl/scripts/jim_stream.py --
    so a run repeats exactly and a case can be named by its position in the
    sequence. It is NOT claimed to be uniform, and nothing here treats it as a
    random oracle. The question it exists to ask is the one the lab's README
    leaves open: whether a structured sweep reaches anything a random one does
    not. A run therefore reports what it drew, so the two can be compared.
    """

    BYTE_PERIOD: ClassVar[dict[int, int]] = {2: 155, 5: 3124}   # measured

    def __init__(self, field: int) -> None:
        self.field = field
        self.drawn = 0
        self._data = stream(field, 4096)
        self._i = 0

    def _byte(self) -> int:
        if self._i >= len(self._data):
            # stream() always starts from the same state, so a longer ask is
            # the same sequence continued, not a different one.
            self._data = stream(self.field, len(self._data) * 2)
        value = self._data[self._i]
        self._i += 1
        self.drawn += 1
        return value

    def randrange(self, n: int) -> int:
        value = 0
        for _ in range((max(n - 1, 1).bit_length() + 7) // 8):
            value = value << 8 | self._byte()
        return value % n

    def sample(self, population: range, k: int) -> list[int]:
        out: list[int] = []
        for _ in range(64 * k):
            if len(out) == k:
                break
            pick = population[self.randrange(len(population))]
            if pick not in out:
                out.append(pick)
        if len(out) != k:
            raise ValueError(f"GF({self.field}) did not reach {k} distinct "
                             f"positions in {64 * k} draws -- its byte period "
                             f"is {self.BYTE_PERIOD[self.field]}")
        return out

    def shuffle(self, seq: list[int]) -> None:
        for i in range(len(seq) - 1, 0, -1):
            j = self.randrange(i + 1)
            seq[i], seq[j] = seq[j], seq[i]


Source = random.Random | JimSource


def source_for(name: str, seed: int) -> Source:
    if name == "random":
        return random.Random(seed)
    return JimSource(int(name.removeprefix("jim")))


def source_note(name: str, src: Source, seed: int) -> dict[str, object]:
    if isinstance(src, JimSource):
        return {"source": name, "field": src.field,
                "state_period": PERIODS[src.field],
                "byte_period": src.BYTE_PERIOD[src.field],
                "bytes_drawn": src.drawn}
    return {"source": name, "seed": seed}


# -- target: kabah --------------------------------------------------------
#
# cosmictera-build/validasi/KABAH.md left the numbers this class pushes at:
# avalanche 0.4995 over single-bit flips, 8/8 chained frames matching cube.py,
# replay identical after reconfiguration and chaining within a run. What it did
# not do is bend the input further -- more bits at once, the same blocks in a
# different order, a frame cut in half, a frame repeated. Each of those is a
# thing an attacker can do to a stream with no framing and no key.


def send_raw(port: str, pieces: list[bytes],
             reply_timeout: float = 2.0) -> list[bytes]:
    """Write each piece, read whatever reply it draws.

    A piece need not be a whole frame. The wrapper absorbs a fixed 128 bytes
    and has no length field, so a short piece draws NOTHING until later bytes
    complete its 128 -- which is the point of the truncation case.
    """
    import serial
    out = []
    with serial.Serial(port, 115200, timeout=reply_timeout) as link:
        link.reset_input_buffer()
        for piece in pieces:
            link.write(piece)
            link.flush()
            out.append(link.read(STATE_BYTES))
    return out


def kabah_avalanche(port: str, bitstream: Path, widths: list[int], trials: int,
                    rng: Source) -> list[dict[str, object]]:
    """Distance between a block's state and that of the same block with k bits
    flipped. k = 1 is KABAH.md's column; the rest are new."""
    rows = []
    for k in widths:
        dists, bad = [], 0
        for _ in range(trials):
            block = bytes(rng.randrange(256) for _ in range(RATE))
            other = block
            for bit in rng.sample(range(RATE * 8), k):
                other = flip(other, bit)
            configure(bitstream)
            first = send_raw(port, [block])[0]
            configure(bitstream)
            second = send_raw(port, [other])[0]
            if (first != expected_states(block)[0]
                    or second != expected_states(other)[0]):
                bad += 1
            dists.append(distance(first, second))
        mean = sum(dists) / len(dists)
        rows.append({"bits_flipped": k, "trials": trials,
                     "mean_fraction": mean / STATE_BITS,
                     "min_fraction": min(dists) / STATE_BITS,
                     "max_fraction": max(dists) / STATE_BITS,
                     "integrity_failures": bad})
        print(f"  {k:>3} bit(s) flipped: mean {mean / STATE_BITS:.4f} of "
              f"{STATE_BITS} bits, {trials} trials, {bad} integrity failure(s)")
    return rows


def kabah_permutation(port: str, bitstream: Path, frames: int,
                      rng: Source) -> dict[str, object]:
    """The same blocks, a different order. The sponge chains, so the final
    state must move; a permutation that left it alone would mean the absorb
    schedule cannot see order -- the shape of defect 3ccf193 found."""
    blocks = [bytes(rng.randrange(256) for _ in range(RATE)) for _ in range(frames)]
    order = list(range(frames))
    mixed_order = order[:]
    while mixed_order == order:
        rng.shuffle(mixed_order)
    configure(bitstream)
    straight = send_raw(port, blocks)
    configure(bitstream)
    mixed = send_raw(port, [blocks[i] for i in mixed_order])
    faithful = (straight == expected_states(b"".join(blocks))
                and mixed == expected_states(b"".join(blocks[i] for i in mixed_order)))
    moved = straight[-1] != mixed[-1]
    print(f"  permutation {order} -> {mixed_order}: final state "
          f"{'differs' if moved else 'IDENTICAL'}, "
          f"{distance(straight[-1], mixed[-1]) / STATE_BITS:.4f} of the state, "
          f"both runs match cube.py: {faithful}")
    return {"frames": frames, "order": mixed_order, "final_state_differs": moved,
            "fraction_changed": distance(straight[-1], mixed[-1]) / STATE_BITS,
            "both_match_cube": faithful}


def kabah_truncated(port: str, bitstream: Path, cut: int,
                    rng: Source) -> dict[str, object]:
    """Half a frame, then the other half from somewhere else."""
    head = bytes(rng.randrange(256) for _ in range(cut))
    tail = bytes(rng.randrange(256) for _ in range(RATE - cut))
    configure(bitstream)
    replies = send_raw(port, [head, tail])
    spliced = replies[1] == expected_states(head + tail)[0]
    print(f"  {cut} bytes then {RATE - cut}: the short piece drew "
          f"{len(replies[0])} bytes, the completion drew {len(replies[1])}, "
          f"and it is cube.py of the SPLICE: {spliced}")
    return {"cut_at": cut, "reply_to_short_piece": len(replies[0]),
            "reply_after_completion": len(replies[1]),
            "equals_cube_of_the_splice": spliced}


def kabah_duplicated(port: str, bitstream: Path, times: int,
                     rng: Source) -> dict[str, object]:
    """One frame, sent again and again inside a single run."""
    block = bytes(rng.randrange(256) for _ in range(RATE))
    configure(bitstream)
    got = send_raw(port, [block] * times)
    want = expected_states(block * times)
    agree = sum(1 for g, w in zip(got, want, strict=True) if g == w)
    print(f"  the same frame {times} times: {agree}/{times} match cube.py, "
          f"{len(set(got))}/{times} states distinct")
    return {"frames": times, "match_cube": agree, "distinct_states": len(set(got))}


def run_kabah(port: str, bitstream: Path, trials: int,
              rng: Source) -> dict[str, object]:
    widths = [1, 2, 4, 8, 16, 32, 64]
    print(f"avalanche against KABAH.md's {KABAH_BASELINE:.4f}:")
    avalanche = kabah_avalanche(port, bitstream, widths, trials, rng)
    print("order, truncation, repetition:")
    permutation = kabah_permutation(port, bitstream, 4, rng)
    truncated = kabah_truncated(port, bitstream, RATE // 2, rng)
    duplicated = kabah_duplicated(port, bitstream, 4, rng)
    single = next(r for r in avalanche if r["bits_flipped"] == 1)
    frames = int(permutation["frames"])
    repeats = int(duplicated["frames"])
    failures = sum(int(r["integrity_failures"]) for r in avalanche)  # type: ignore[call-overload]
    collisions = 0 if (permutation["final_state_differs"]
                       and duplicated["distinct_states"] == repeats) else 1
    return {
        "target": "kabah",
        "baseline": KABAH_BASELINE,
        "avalanche": avalanche,
        "avalanche_single_bit": single["mean_fraction"],
        "permutation": permutation,
        "truncated": truncated,
        "duplicated": duplicated,
        "inputs": len(widths) * trials * 2 + frames * 2 + 2 + repeats,
        # The owner's record names a reject count. A sponge has none: it
        # absorbs whatever arrives, and the wrapper has no length field to
        # refuse a short frame with. Said here rather than left to be guessed.
        "rejected": "not applicable -- the sponge absorbs, it does not refuse",
        "integrity_failures": failures,
        "collisions": collisions,
        "findings": failures + collisions,
    }


def save(record: dict[str, object], started: datetime, target: str,
         bitstream: Path) -> Path:
    """One JSON per run, with the fields the owner named for the lab."""
    record |= {
        "attack_id": started.strftime("%Y%m%dT%H%M%SZ") + f"-{target}",
        "timestamp": started.isoformat(),
        "board": "Tang Nano 20K",
        "clock_hz": OSC_HZ,
        "bitstream": str(bitstream.relative_to(ROOT)),
    }
    LAB.mkdir(parents=True, exist_ok=True)
    out = LAB / f"{record['attack_id']}.json"
    out.write_text(json.dumps(record, indent=2) + "\n")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", default="loader",
                    choices=sorted(DEFAULT_BITSTREAM))
    ap.add_argument("--port", help="serial device; omit to print the plan only")
    ap.add_argument("--bitstream", type=Path, default=None,
                    help="defaults to the slot the target runs in")
    ap.add_argument("--runs", type=int, default=1,
                    help="jamrah: how many times to sweep the 256 bytes")
    ap.add_argument("--trials", type=int, default=4,
                    help="kabah: trials per avalanche width")
    ap.add_argument("--seed", type=int, default=20260920)
    ap.add_argument("--source", default="random", choices=["random", "jim2", "jim5"],
                    help="where the cases come from; jimN is the codex stream")
    ap.add_argument("--cases", type=int, default=16,
                    help="loader with --source jimN: how many damaged words")
    args = ap.parse_args(argv)
    started = datetime.now(timezone.utc)
    bitstream = (args.bitstream or
                 ROOT / "rtl" / "fpga" / "gowin" / DEFAULT_BITSTREAM[args.target])

    if args.target == "kabah":
        if args.port is None:
            print(f"kabah: avalanche at 1, 2, 4, 8, 16, 32, 64 bits x "
                  f"{args.trials} trials against KABAH.md's {KABAH_BASELINE}, "
                  f"then permutation, truncation, repetition.")
            print(f"slot: {bitstream.relative_to(ROOT)}; each trial "
                  f"reconfigures the board twice.")
            return 0
        src = source_for(args.source, args.seed)
        record = run_kabah(args.port, bitstream, args.trials, src)
        record |= source_note(args.source, src, args.seed)
        out = save(record, started,
                   "kabah" if args.source == "random" else f"kabah-{args.source}",
                   bitstream)
        print(f"\nsingle-bit avalanche {record['avalanche_single_bit']:.4f} "
              f"against the baseline {KABAH_BASELINE:.4f}; "
              f"{record['findings']} finding(s)")
        print(f"record: {out.relative_to(ROOT)}")
        return 0

    if args.target == "jamrah":
        # Without a port this still runs, in the interpreter, and counts
        # INSTRUCTIONS instead of clocks. The two units are never compared.
        record = run_jamrah(args.port, bitstream, args.runs)
        constant, control = record["constant_time"], record["control_distinct_counts"]
        print(f"\nthe gate takes {record['clocks_per_byte']} "
              f"{record['gate']['unit']} for every one of 256 bytes" if constant  # type: ignore[index]
              else "\nthe gate's count is NOT one number")
        if args.runs > 1:
            print(f"{args.runs} runs of 256: "
                  f"{'identical, byte for byte' if record['runs_identical'] else 'NOT identical'}")
        print(f"the control, same answer, spreads over {control} counts -- "
              f"so the measurement can see a difference when there is one")
        if args.port is None:
            return 0
        out = save(record, started, "jamrah", bitstream)
        print(f"record: {out.relative_to(ROOT)}")
        return 0

    container = base_container()
    src = source_for(args.source, args.seed)
    plan = (cases(container) if args.source == "random"
            else jim_cases(container, src, args.cases))  # type: ignore[arg-type]
    if args.port is None:
        print(f"{len(plan)} cases against the loader, container of "
              f"{len(container)} words at {LOAD_ADDR:#05x}:")
        for c in plan:
            where = "" if c["board"] else "  (Python and simulation only)"
            print(f"  {c['id']:<30} {c['category']:<17} expect {c['expect']:<7} "
                  f"{c['by']}{where}")
        return 0

    record = run_loader(args.port, bitstream, plan)
    record |= source_note(args.source, src, args.seed)
    out = save(record, started,
               "loader" if args.source == "random" else f"loader-{args.source}",
               bitstream)
    print(f"\n{record['rejected']}/{record['inputs']} refused; "
          f"{record['findings']} case(s) disagreed with the loader's own checks")
    print(f"record: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
