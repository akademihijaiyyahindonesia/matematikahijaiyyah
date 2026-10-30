"""CHECKSUM32 and 4-B' overlay verification, held to one reading across builders and loaders.

The owner's step P6, 26 September 2026, on K-8 and K-10: one 32-bit sum, mod
2^32, over the sector-16 table entry, the container's header with its own
checksum field counted as zero, the relocation table and the program words --
and nothing outside the container. The owner's condition before calling it
final: decide the canonical byte and word order and test it, so that the
builder, the Python loader and the HCPU loader do not hold three different
ideas of what is being summed.

Step Q-F9e (4-B' on HCPU overlay loading) adds two-phase static control-flow
and call-depth verification (<= 28 levels, leaving 4 levels of RA_DEPTH = 32
for supervisor traps) to the Stage 3 overlay loader path (`hos_prog_load` /
`SYSCALL 9`), while preserving the Stage 2 raw container path
(`hos_prog_load_raw` / `load_check_raw`) for kernel and Stage 2 fixtures.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
TB = ROOT / "rtl" / "tb"

import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

from attack_lab import INTENT, LOAD_ADDR, base_container, cases  # noqa: E402
from build_container import (  # noqa: E402
    CHECKSUM_AT,
    FLAGS_VALID,
    MAGIC,
    OVERLAY_MAX_CALL_DEPTH,
    OVERLAY_WORK_MAX,
    PROGRAM_ID,
    START_SECTOR,
    VERSION,
    build,
    card_bytes,
    card_image,
    card_words,
    checksum32,
    load_check,
    load_check_raw,
    seal,
    table_record,
)
from send_program import encode  # noqa: E402

from hijaiyyah.core.master_table import MASTER_TABLE  # noqa: E402
from hijaiyyah.hisa.assembler import assemble  # noqa: E402
from hijaiyyah.hisa.machine import HISAMachine  # noqa: E402
from hijaiyyah.hisa.opcodes import OpCode  # noqa: E402

CASES = cases(base_container())
OWNER_SIX = ("header", "program-table", "relocation", "program-body",
             "checksum-field", "out-of-container")
PROGRAMS_DIR = ROOT / "rtl" / "programs"


# -- one order ------------------------------------------------------------------------


def test_the_card_holds_a_word_most_significant_byte_first() -> None:
    """rtl/hcpu_sdio.v fixes it -- buf[31:24] is byte 0 -- and the Python side
    must read the same bytes into the same words."""
    sdio = (ROOT / "rtl" / "hcpu_sdio.v").read_text(encoding="utf-8")
    assert "most significant byte\n    // first: buf[31:24] is byte 0" in sdio
    assert card_bytes([0x01020304, 0xA0B0C0D0]) == bytes.fromhex("01020304A0B0C0D0")
    container = base_container()
    assert card_words(card_bytes(container)) == container


def test_the_wire_carries_the_same_words_in_the_same_order() -> None:
    """send_program.py frames a container for sd_writer: a count, then each word
    most significant byte first -- the order the card keeps it in."""
    container = base_container()
    stream = encode(container)
    assert stream[:4] == len(container).to_bytes(4, "big")
    assert stream[4:] == card_bytes(container)


def test_the_table_entry_is_the_one_sd_writer_writes() -> None:
    """PROGRAM_ID, FLAGS and START_SECTOR in the builder are read back out of
    rtl/programs/sd_writer.hasm, the program that really writes sector 16."""
    text = (ROOT / "rtl" / "programs" / "sd_writer.hasm").read_text(encoding="utf-8")
    found = {m.group(2): int(m.group(1)) for m in re.finditer(
        r"MOVI\s+R1,\s*(\d+)\s*;\s*(PROGRAM_ID|FLAGS|START_SECTOR)", text)}
    assert found == {"PROGRAM_ID": PROGRAM_ID, "FLAGS": FLAGS_VALID,
                     "START_SECTOR": START_SECTOR}
    assert table_record(129) == [1, 1, 17, 2], "SECTOR_COUNT rounds up"


def test_the_sum_is_the_owners_definition_written_out() -> None:
    """CHECKSUM32 by hand, from K-10's words, against the builder's: the record,
    then the header with the checksum as zero, the table, the program."""
    container = base_container()
    record = table_record(len(container))
    by_hand = sum(record) + sum(w for i, w in enumerate(container) if i != CHECKSUM_AT)
    assert container[CHECKSUM_AT] == checksum32(record, container) == by_hand % 2 ** 32
    assert container[1] == VERSION == 2


# -- the Python loader against the owner's intent --------------------------------------


@pytest.mark.parametrize("case", CASES, ids=[str(c["id"]) for c in CASES])
def test_the_python_loader_does_what_the_category_asks(case: dict[str, Any]) -> None:
    assert case["expect"] == case["intent"] == INTENT[str(case["category"])], case["by"]
    assert load_check(case["card"]) == (case["expect"] == "accept", case["by"])


def test_each_of_the_owners_six_categories_has_its_own_case() -> None:
    have = {str(c["category"]) for c in CASES}
    assert set(OWNER_SIX) <= have, set(OWNER_SIX) - have
    for category in OWNER_SIX[:-1]:
        assert any(c["category"] == category and c["by"] == "CHECKSUM32"
                   for c in CASES), f"{category}: no case the sum alone refuses"


def test_what_version_one_let_through_is_refused_now() -> None:
    """The attack lab's two accepted cases of 20 September 2026 are why K-8
    exists. They are CHECKSUM32's to refuse now, not a range check's."""
    by_id: dict[str, dict[str, Any]] = {str(c["id"]): c for c in CASES}
    for cid in ("words_plus_one", "reloc_index_moved"):
        assert (by_id[cid]["expect"], by_id[cid]["by"]) == ("reject", "CHECKSUM32"), cid


def test_the_limits_of_a_sum_are_named_not_hidden() -> None:
    """A sum is public and does not see order: two words exchanged, or a body
    changed and resealed, both load. Written down as what K-10's algorithm
    is, not as a defect of this implementation."""
    by_id: dict[str, dict[str, Any]] = {str(c["id"]): c for c in CASES}
    for cid in ("words_swapped", "body_changed_and_resealed"):
        assert by_id[cid]["expect"] == "accept"
        assert by_id[cid]["category"] == "limit-of-a-sum"
    assert card_image(by_id["words_swapped"]["stream"]) != card_image(base_container())


# -- Q-F9e: 4-B' static overlay verification on HCPU loader ---------------------------


def _raw_container(words: list[int], relocs: list[int],
                   load_addr: int = LOAD_ADDR,
                   entry_offset: int = 0) -> list[int]:
    c = [MAGIC, VERSION, len(words), load_addr, load_addr + entry_offset,
         len(relocs), 0, *relocs, *words]
    return seal(c, table_record(len(c)))


def _asm_container(source: str, load_addr: int = LOAD_ADDR,
                   entry_label: str | None = None) -> list[int]:
    return build(source, PROGRAMS_DIR, load_addr, entry_label=entry_label)


def _chain_call_source(depth: int) -> str:
    if depth == 0:
        return "        MOVI R1, 1\n        HALT\n"
    lines = ["        CALL f1", "        HALT"]
    for i in range(1, depth):
        lines.append(f"f{i}:    CALL f{i + 1}")
        lines.append("        RET")
    lines.append(f"f{depth}: MOVI R1, 1")
    lines.append("        RET")
    return "\n".join(lines) + "\n"


def _diamond_call_source(max_depth: int) -> str:
    """A diamond DAG where a1..a{max_depth-1} are first visited via a shallower
    direct call from main (depth 1..max_depth-1), and then reached at depth
    `max_depth` via b0 -> a1 -> ... -> a{max_depth-1}."""
    chain_len = max_depth - 1
    lines = [
        "        CALL a1",
        "        CALL b0",
        "        HALT",
        "b0:     CALL a1",
        "        RET",
    ]
    for i in range(1, chain_len):
        lines.append(f"a{i}:    CALL a{i + 1}")
        lines.append("        RET")
    lines.append(f"a{chain_len}: MOVI R1, 1")
    lines.append("        RET")
    return "\n".join(lines) + "\n"


def _wide_branch_fanout_source(branches: int) -> str:
    """`branches` conditional branches fanning out to `branches` distinct basic
    blocks `arm_0 .. arm_{branches-1}`. Exercises `branches` simultaneous
    worklist entries in Phase V2."""
    lines = [f"        JEQ arm_{i}" for i in range(branches)]
    lines.append("        HALT")
    for i in range(branches):
        lines.append(f"arm_{i}: HALT")
    return "\n".join(lines) + "\n"


def _wide_binary_tree_source(levels: int = 8) -> str:
    """Balanced binary decision tree of `2^levels - 1` JEQ branch nodes and
    `2^levels` HALT leaves (`511` words for `levels=8`, `0` relocations).
    Uses only `levels` worklist slots at peak."""
    lines: list[str] = []

    def emit(level: int, prefix: str) -> None:
        if level == levels:
            lines.append(f"{prefix}: HALT")
            return
        right = f"{prefix}r"
        lines.append(f"{prefix}: JEQ {right}")
        emit(level + 1, f"{prefix}l")
        emit(level + 1, right)

    emit(0, "n")
    return "\n".join(lines) + "\n"


def _wide_call_branch_source(call_count: int = 60) -> str:
    """`call_count` sequential CALLs in main to a subroutine with 8 internal
    conditional branches. Exercises > 480 dynamic branch paths while keeping
    relocations <= 128 and peak worklist depth <= 9."""
    lines = ["        JMP main", "sub:"]
    lines.extend(f"        JEQ b{i}" for i in range(8))
    lines.extend(f"b{i}:    NOP" for i in range(8))
    lines.append("        RET")
    lines.append("main:")
    lines.extend("        CALL sub" for _ in range(call_count))
    lines.append("        HALT")
    return "\n".join(lines) + "\n"


def _overlay_cases() -> list[dict[str, Any]]:
    nop = int(OpCode.NOP) << 24
    halt = int(OpCode.HALT) << 24
    jmp = int(OpCode.JMP) << 24
    jeq = int(OpCode.JEQ) << 24
    call = int(OpCode.CALL) << 24
    movi_r1_1 = (int(OpCode.MOVI) << 24) | (1 << 20) | 1

    raw_cases: list[tuple[str, list[int], str, str]] = [
        # 1. Call-depth bound (<= 28 accepted, 29 rejected)
        ("depth_28_chain", _asm_container(_chain_call_source(OVERLAY_MAX_CALL_DEPTH)),
         "accept", "loaded"),
        ("depth_29_chain", _asm_container(_chain_call_source(OVERLAY_MAX_CALL_DEPTH + 1)),
         "reject", "invalid: call depth 29 exceeds maximum 28"),
        ("depth_28_diamond", _asm_container(_diamond_call_source(OVERLAY_MAX_CALL_DEPTH)),
         "accept", "loaded"),
        ("depth_29_diamond", _asm_container(_diamond_call_source(OVERLAY_MAX_CALL_DEPTH + 1)),
         "reject", "invalid: call depth 29 exceeds maximum 28"),
        # 2. RET at call depth 0 (overlay rule)
        ("ret_at_depth0_direct", _asm_container("        RET\n"),
         "reject", "invalid: RET reachable at call depth 0"),
        ("ret_at_depth0_via_jeq",
         _asm_container("        CMPI R1, 0\n        JEQ bad\n        HALT\nbad:    RET\n"),
         "reject", "invalid: RET reachable at call depth 0"),
        ("ret_at_depth0_after_call",
         _asm_container("        CALL sub\n        RET\nsub:    MOVI R1, 1\n        RET\n"),
         "reject", "invalid: RET reachable at call depth 0"),
        # 3. Valid CALL/RET & ENTRY > LOAD_ADDR
        ("valid_nested_calls",
         _asm_container("        CALL s1\n        CALL s2\n        HALT\n"
                        "s1:     CALL s2\n        RET\ns2:     MOVI R1, 7\n        RET\n"),
         "accept", "loaded"),
        ("valid_entry_gt_load_addr",
         _asm_container("sub:    MOVI R1, 42\n        RET\n"
                        "start:  CALL sub\n        HALT\n", entry_label="start"),
         "accept", "loaded"),
        # 4. Recursion & unprovable control flow (unverified)
        ("direct_recursion",
         _asm_container("        CALL r\n        HALT\nr:      CALL r\n        RET\n"),
         "reject", "unverified: recursive call cycle"),
        ("mutual_recursion",
         _asm_container("        CALL a\n        HALT\n"
                        "a:      CALL b\n        RET\nb:      CALL a\n        RET\n"),
         "reject", "unverified: recursive call cycle"),
        ("call_to_entry_recursion",
         _asm_container("start:  CALL start\n        HALT\n"),
         "reject", "unverified: recursive call to ENTRY"),
        ("eret_dynamic_target",
         _asm_container("        ERET\n        HALT\n"),
         "reject", "unverified: dynamic control transfer ERET"),
        ("cross_procedure_jmp",
         _asm_container("        CALL s1\n        CALL s2\n        HALT\n"
                        "s1:     JMP s2_mid\ns2:     MOVI R1, 1\ns2_mid: RET\n"),
         "reject", "unverified: cross-procedure control flow"),
        ("fallthrough_into_callee",
         _asm_container("        CALL sub\nsub:    MOVI R1, 1\n        RET\n"),
         "reject", "unverified: cross-procedure control flow"),
        # 5. PUSH / POP / HALT_ERR / illegal opcode rejection
        ("push_rejected",
         _asm_container("        PUSH R1\n        HALT\n"),
         "reject", "invalid: forbidden opcode PUSH"),
        ("pop_rejected",
         _asm_container("        POP R1\n        HALT\n"),
         "reject", "invalid: forbidden opcode POP"),
        ("halt_err_rejected",
         _asm_container("        HALT_ERR\n        HALT\n"),
         "reject", "invalid: forbidden opcode HALT_ERR"),
        ("illegal_opcode_rejected",
         _raw_container([(0x99 << 24), halt], []),
         "reject", "invalid: illegal opcode 0x99"),
        # 6. Out-of-bounds targets & fall-through past end (resealed containers)
        ("jmp_past_end_resealed",
         _raw_container([jmp | 5, halt], [0]),
         "reject", "invalid: absolute target"),
        ("jmp_unrelocated_resealed",
         _raw_container([jmp | 0, halt], []),
         "reject", "invalid: absolute target"),
        ("jeq_before_start_resealed",
         _raw_container([jeq | 0xFFF, halt], []),
         "reject", "invalid: relative target"),
        ("jeq_past_end_resealed",
         _raw_container([nop, jeq | 5, halt], []),
         "reject", "invalid: relative target"),
        ("ordinary_fallthrough_resealed",
         _raw_container([movi_r1_1], []),
         "reject", "invalid: fall-through past end of program"),
        ("jeq_at_final_word_resealed",
         _raw_container([nop, jeq | 0], []),
         "reject", "invalid: conditional branch at final word"),
        ("call_at_final_word_resealed",
         _raw_container([halt, call | 0], [1], entry_offset=1),
         "reject", "invalid: CALL at final word"),
        # 7. Worklist capacity & wide-branching graphs (binary tree 255 branches,
        #    60x8 call-branch fanout, linear 252 accepted, linear 253 fail-closed)
        ("wide_binary_tree_255_branches",
         _asm_container(_wide_binary_tree_source(8)),
         "accept", "loaded"),
        ("wide_call_branch_fanout",
         _asm_container(_wide_call_branch_source(60)),
         "accept", "loaded"),
        ("wide_branch_252_accepted",
         _asm_container(_wide_branch_fanout_source(OVERLAY_WORK_MAX)),
         "accept", "loaded"),
        ("wide_branch_253_fail_closed",
         _asm_container(_wide_branch_fanout_source(OVERLAY_WORK_MAX + 1)),
         "reject", "unverified: worklist capacity 252 exceeded"),
    ]
    out: list[dict[str, Any]] = []
    for cid, stream, expect, reason_prefix in raw_cases:
        out.append({
            "id": cid,
            "stream": stream,
            "card": card_image(stream),
            "expect": expect,
            "reason_prefix": reason_prefix,
        })
    return out


OVERLAY_CASES = _overlay_cases()


def _run_interpreter_loader(card: dict[int, list[int]],
                            *, raw_mode: bool = False) -> tuple[int, int]:
    """Run assembled test_prog_load.hasm (which includes hos_prog_load.hasm)
    on HISAMachine with an attached SD card image. Returns (verdict, imem_writes)."""
    prog = PROGRAMS_DIR / "test_prog_load.hasm"
    words = assemble(prog.read_text(encoding="utf-8"), base_dir=PROGRAMS_DIR, base=0)
    machine = HISAMachine(MASTER_TABLE, hcheck_interval=0)
    machine.load_program(words)
    if raw_mode:
        machine.data_mem[0xED7] = 1

    sd_sec = 0
    sd_idx = 0
    sd_buf = [0] * 128

    def sd_read(reg: int) -> int:
        nonlocal sd_idx
        if reg == 1:  # SD_STATUS: bit 1 ok | bit 3 present
            return 0xA
        if reg == 3:  # SD_DATA
            val = sd_buf[sd_idx & 0x7F]
            sd_idx = (sd_idx + 1) & 0x7F
            return val
        return 0

    def sd_write(reg: int, value: int) -> None:
        nonlocal sd_sec, sd_idx, sd_buf
        if reg == 0 and value == 2:  # SD_CMD = read
            sd_buf = list(card.get(sd_sec, [0] * 128))
            sd_idx = 0
        elif reg == 2:  # SD_SECTOR
            sd_sec = value
        elif reg == 4 and (value & 1):  # SD_CONTROL rewind
            sd_idx = 0

    machine._sd_read = sd_read  # type: ignore[method-assign]
    machine._sd_write = sd_write  # type: ignore[method-assign]

    imem_writes = 0
    orig_periph_write = machine._periph_write

    def tracked_periph_write(reg: int, value: int) -> None:
        nonlocal imem_writes
        if reg == HISAMachine.REG_IMEM_DATA:
            imem_writes += 1
        orig_periph_write(reg, value)

    machine._periph_write = tracked_periph_write  # type: ignore[method-assign]
    steps = 0
    while not machine._halted and steps < 500_000:
        machine.step()
        steps += 1
    assert machine._halted, f"loader did not halt within {steps} steps"
    assert len(machine.output) == 1
    return int(machine.output[0]), imem_writes


@pytest.mark.parametrize("case", OVERLAY_CASES, ids=[str(c["id"]) for c in OVERLAY_CASES])
def test_overlay_verifier_python_and_interpreter_agree_and_protect_imem(
        case: dict[str, Any]) -> None:
    """Every 4-B' overlay case must receive the same verdict from Python
    load_check and from HCPU hos_prog_load.hasm, with diagnostic distinction
    between `invalid:` and `unverified:`, and zero IMEM writes on refusal."""
    ok, reason = load_check(case["card"])
    want_ok = case["expect"] == "accept"
    assert ok is want_ok, (case["id"], ok, reason)
    assert reason.startswith(case["reason_prefix"]), (case["id"], reason, case["reason_prefix"])

    verdict, imem_writes = _run_interpreter_loader(case["card"], raw_mode=False)
    assert verdict == (1 if want_ok else 0), (case["id"], verdict, reason)
    if not want_ok:
        assert imem_writes == 0, f"{case['id']} wrote {imem_writes} words to IMEM before refusal"
    else:
        expected_words = case["stream"][2]
        assert imem_writes == expected_words, (case["id"], imem_writes, expected_words)


def test_option_two_separates_stage_two_raw_from_stage_three_overlay() -> None:
    """Option 2: subroutine.hasm (PUSH) and shell.hasm (PUSH/POP/ERET) are
    accepted on the Stage 2 raw path (`load_check_raw` / `hos_prog_load_raw`)
    and refused on the Stage 3 overlay path (`load_check` / `hos_prog_load`)
    with zero IMEM writes."""
    for name, expected_reason in (
        ("subroutine.hasm", "invalid: forbidden opcode PUSH"),
        ("shell.hasm", "invalid: forbidden opcode PUSH"),
    ):
        src = PROGRAMS_DIR / name
        container = build(src.read_text(encoding="utf-8"), PROGRAMS_DIR, LOAD_ADDR)
        card = card_image(container)

        raw_ok, raw_reason = load_check_raw(card)
        assert (raw_ok, raw_reason) == (True, "loaded"), (name, raw_ok, raw_reason)
        ov_ok, ov_reason = load_check(card, overlay=True)
        assert not ov_ok and ov_reason.startswith(expected_reason), (name, ov_ok, ov_reason)

        raw_verdict, raw_writes = _run_interpreter_loader(card, raw_mode=True)
        assert raw_verdict == 1 and raw_writes == container[2], (name, raw_verdict, raw_writes)

        ov_verdict, ov_writes = _run_interpreter_loader(card, raw_mode=False)
        assert ov_verdict == 0 and ov_writes == 0, (name, ov_verdict, ov_writes)


def test_container_flags_and_metadata_cannot_bypass_overlay_verification(
        bench: Path) -> None:
    """Forged sector-16 FLAGS bits or header metadata resealed with a valid
    CHECKSUM32 cannot switch the Stage 3 overlay loader (`hos_prog_load` /
    `SYSCALL 9`) into raw mode or bypass 4-B' verification."""
    sub_src = (PROGRAMS_DIR / "subroutine.hasm").read_text(encoding="utf-8")
    base_sub = build(sub_src, PROGRAMS_DIR, LOAD_ADDR)

    forged_cards: list[tuple[str, dict[int, list[int]], bool]] = []
    for flags_val in (0x00000003, 0x000000FF, 0x80000001, 0xFFFFFFFF):
        rec = table_record(len(base_sub), flags=flags_val)
        resealed = seal(base_sub, rec)
        forged_cards.append((f"flags_{flags_val:#010x}", card_image(resealed, record=rec), True))

    for ver_val in (0, 1, 3, 0x80000002):
        tampered = list(base_sub)
        tampered[1] = ver_val
        rec = table_record(len(tampered))
        resealed = seal(tampered, rec)
        forged_cards.append((f"version_{ver_val:#010x}", card_image(resealed, record=rec), False))

    for label, card, raw_accepts in forged_cards:
        raw_ok, _ = load_check_raw(card)
        assert raw_ok is raw_accepts, label

        ov_ok, ov_reason = load_check(card, overlay=True)
        assert not ov_ok, (label, ov_reason)
        if raw_accepts:
            assert ov_reason.startswith("invalid: forbidden opcode PUSH"), (label, ov_reason)

        verdict, imem_writes = _run_interpreter_loader(card, raw_mode=False)
        assert verdict == 0 and imem_writes == 0, (label, verdict, imem_writes)

        rtl_ans = _hcpu(bench, card)
        assert (rtl_ans["DONE"], rtl_ans["ANSWER"], rtl_ans["ABSENT"]) == (1, 0, 0), (
            label, rtl_ans
        )


# -- the HCPU loader against the Python one ---------------------------------------------

HAVE_SIM = shutil.which("iverilog") is not None and shutil.which("vvp") is not None


@pytest.fixture(scope="module")
def bench() -> Path:
    if not HAVE_SIM and os.environ.get("HOM_REQUIRE_IVERILOG") != "1":
        pytest.skip("Icarus Verilog is required to run the HCPU loader")
    subprocess.run(["make", "-s", "tb_hcpu_prog_load_card.vvp", "shell_progload.hex"],
                   cwd=TB, check=True, capture_output=True)
    return TB / "tb_hcpu_prog_load_card.vvp"


def _hcpu(bench: Path, card: dict[int, list[int]]) -> dict[str, int]:
    words = [w for s in range(16, 24) for w in card.get(s, [0] * 128)]
    with tempfile.NamedTemporaryFile("w", suffix=".hex", delete=False) as fh:
        fh.write("\n".join(f"{w:08X}" for w in words) + "\n")
        name = fh.name
    try:
        out = subprocess.run(["vvp", bench.name, f"+CARD={name}"], cwd=TB,
                             capture_output=True, text=True, timeout=600).stdout
    finally:
        os.unlink(name)
    line = next(ln for ln in out.splitlines() if ln.startswith("DONE="))
    return {k: int(v) for k, v in (p.split("=") for p in line.split())}


def test_the_hcpu_loader_gives_the_python_loaders_verdict_on_every_card(
        bench: Path) -> None:
    """Same card, bit for bit, to both loaders. One run of the simulated HCPU per
    case, in parallel: the probe asks for PROGRAM_ID 1 and records the answer."""
    all_cases = [*CASES, *OVERLAY_CASES]
    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as pool:
        got = dict(zip([c["id"] for c in all_cases],
                       pool.map(lambda c: _hcpu(bench, c["card"]), all_cases), strict=True))
    wrong = []
    for case in all_cases:
        answer = got[case["id"]]
        want = 1 if case["expect"] == "accept" else 0
        if (answer["DONE"], answer["ANSWER"], answer["ABSENT"]) != (1, want, 0):
            wrong.append((case["id"], case["expect"], answer))
    assert not wrong, wrong
