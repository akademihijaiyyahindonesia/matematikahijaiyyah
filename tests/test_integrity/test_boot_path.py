"""
The boot path: what turns the Tang Nano 20K from a device you flash into a
bridge you develop on.

Until this existed a program lived inside the bitstream. `$readmemh` put it
there at synthesis and `imem_data` was an INPUT to hcpu_top, so the CPU could
not write instruction memory. Changing one instruction meant a full
resynthesis and a reflash -- which made every step after it cost a synthesis
cycle, and made the board a fixed-function device rather than a computer.

Now the bitstream holds the loader and everything else arrives over the wire.

The instruction that hands control over is ERET, and no new one had to be
invented: there is no register-indirect jump in the ISA, but ERET jumps to
TRAP_EPC -- a register the loader writes -- and sets the privilege level in
the same act.
"""
from __future__ import annotations

import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.hisa.machine import HISAMachine
from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED

ROOT = Path(__file__).resolve().parents[2]
LOADER = ROOT / "rtl" / "programs" / "loader.hasm"
DECODE = (ROOT / "rtl" / "hcpu_decode.v").read_text(encoding="utf-8")
LOAD_BASE = 64


def _stream(words: list[int]) -> list[int]:
    """The loader's wire format: count then words, most significant byte first."""
    out = bytearray(struct.pack(">I", len(words)))
    for w in words:
        out += struct.pack(">I", w)
    return list(out)


def _boot(payload_src: str, steps: int = 8000) -> HISAMachine:
    m = HISAMachine(MASTER_TABLE)
    m.code = assemble(LOADER.read_text(encoding="utf-8"))
    # At the loader's base, not zero. Every payload this helper used to get was
    # label-free, so the base never changed a word and the helper looked right
    # while carrying the same bug send_program.py had.
    m.rx_queue = _stream(assemble(payload_src, base=LOAD_BASE))
    for _ in range(steps):
        if m.step() is None:
            break
    return m


# ══════════════════════════════════════════════════════════════════
#  The bug that hid behind two test suites
# ══════════════════════════════════════════════════════════════════

def test_every_opcode_claimed_for_rtl_is_recognised_by_decode() -> None:
    """
    hcpu_decode's `default` branch is HALT_ERR, so an opcode missing from its
    case does not merely do nothing -- it STOPS THE MACHINE.

    OP_ERET was missing for several commits. It redirected correctly, because
    Execute resolves that, and then halted the pipeline before the returned-to
    instruction could retire. Nothing caught it: tb_hcpu_trap exercises the
    trap unit without a decoder, and the interpreter has no decode table at
    all, so ERET had never once run through the real pipeline.

    This is the general form of that bug.
    """
    recognised = set(re.findall(r"`(OP_[A-Z0-9_]+):", DECODE))
    claimed = {f"OP_{op.name}" for op in RTL_IMPLEMENTED}

    # HALT_ERR is what the default branch PRODUCES, not something decode
    # recognises. It is the one legitimate absence.
    #
    # The 28 letter instructions are the other: they are caught by a RANGE
    # check inside `default`, before it can halt, rather than by 28 cases.
    # That is deliberate -- one contiguous block, one comparison -- so the
    # rule here becomes "recognised by name OR inside the letter range".
    assert "`LETTER_OP_FIRST" in DECODE and "`LETTER_OP_LAST" in DECODE
    letters = {f"OP_{op.name}" for op in RTL_IMPLEMENTED
               if 0xE0 <= int(op) <= 0xFB}
    assert len(letters) == 28

    missing = claimed - recognised - letters - {"OP_HALT_ERR"}
    assert not missing, f"decode falls through to HALT_ERR for: {sorted(missing)}"


def test_the_default_branch_really_is_a_halt() -> None:
    """The reason the test above matters, pinned so it cannot quietly change."""
    tail = DECODE[DECODE.index("default: begin"):]
    assert "id_is_halt <= 1'b1" in tail[:1200]
    # And the letter range is checked BEFORE the halt, or the letters would
    # stop the machine exactly the way OP_ERET once did.
    halt_at = tail.index("id_is_halt <= 1'b1")
    range_at = tail.index("`LETTER_OP_FIRST")
    assert range_at < halt_at, "the letter range is checked after the halt"


# ══════════════════════════════════════════════════════════════════
#  The write port
# ══════════════════════════════════════════════════════════════════

def test_the_write_port_advances_its_own_address() -> None:
    """
    One store per word. A loader that had to write the address each time would
    spend two instructions per word, and it has to fit in front of what it
    loads.
    """
    m = HISAMachine(MASTER_TABLE)
    m.code = [0] * 128
    m._periph_write(m.REG_IMEM_ADDR, LOAD_BASE)
    for i, word in enumerate((0xAAAA1111, 0xBBBB2222, 0xCCCC3333)):
        m._periph_write(m.REG_IMEM_DATA, word)
        assert m.imem_waddr == LOAD_BASE + i + 1
    assert m.code[LOAD_BASE:LOAD_BASE + 3] == [0xAAAA1111, 0xBBBB2222, 0xCCCC3333]


def test_the_write_enable_is_combinational_in_the_rtl() -> None:
    """
    Registering imem_we would assert the write one cycle after imem_waddr had
    already advanced, so every word would land at the address after its own --
    a program that almost works, which is the worst kind to debug on a desk.
    """
    mmio = (ROOT / "rtl" / "hcpu_mmio.v").read_text(encoding="utf-8")
    assert "assign imem_we = imem_data_we;" in mmio
    assert not re.search(r"imem_we\s*<=", mmio), "imem_we is registered again"


def test_user_mode_cannot_write_instruction_memory() -> None:
    """
    The write port is in the peripheral window, so the privilege rule already
    covers it -- but a user program that could rewrite code would make every
    other boundary pointless, so it is worth its own check.
    """
    m = HISAMachine(MASTER_TABLE)
    m.code = [0] * 128
    m.mode = m.MODE_USER
    m._mem_write(0xFF3, LOAD_BASE)
    m._mem_write(0xFF7, 0xDEADBEEF)
    assert m._priv_fault
    assert m.code[LOAD_BASE] == 0, "user mode wrote instruction memory"


# ══════════════════════════════════════════════════════════════════
#  The loader, end to end
# ══════════════════════════════════════════════════════════════════

def test_the_loader_fits_in_front_of_what_it_loads() -> None:
    words = assemble(LOADER.read_text(encoding="utf-8"))
    assert len(words) < LOAD_BASE, (
        f"the loader is {len(words)} words and writes from {LOAD_BASE}: it "
        "would overwrite itself while running")


def test_a_program_sent_over_the_wire_runs() -> None:
    m = _boot("        MOVI  R9, 42\n        MOVI  R10, 7\n        HALT\n")
    assert m._halted, "the loaded program never finished"
    assert m.regs.gpr[9] == 42
    assert m.regs.gpr[10] == 7
    assert m.code[LOAD_BASE] == assemble("        MOVI R9, 42\n")[0]


def test_a_second_different_program_runs_without_touching_the_bitstream() -> None:
    """The whole point. One image, any number of programs."""
    first = _boot("        MOVI  R9, 1\n        HALT\n")
    second = _boot("        MOVI  R9, 2\n        MOVI R8, 99\n        HALT\n")
    assert first.regs.gpr[9] == 1
    assert second.regs.gpr[9] == 2 and second.regs.gpr[8] == 99
    # Same loader image both times.
    loader = assemble(LOADER.read_text(encoding="utf-8"))
    assert first.code[:len(loader)] == loader == second.code[:len(loader)]


def test_the_loaded_program_starts_in_supervisor_and_the_reason_is_recorded() -> None:
    """
    Deliberate: at this stage the loaded program IS the system. Dropping it to
    user mode would mean it could not print, could not halt, and would fault on
    its first useful instruction. When an OS exists it will load applications
    through the same mechanism with bit 1 clear.
    """
    m = _boot("        MOVI  R9, 1\n        HALT\n")
    assert m.mode == m.MODE_SUPER
    text = LOADER.read_text(encoding="utf-8")
    assert "MOVI  R7, 2" in text
    assert "SUPERVISOR" in text and "MOVI R7, 0" in text.replace("  ", " ")


# ══════════════════════════════════════════════════════════════════
#  The host tool
# ══════════════════════════════════════════════════════════════════

def test_the_host_tool_assembles_where_the_loader_will_put_the_program() -> None:
    """The tool must assemble at LOAD_BASE, and this proves it rather than
    following it.

    This test used to assemble at base 0 and demand the tool match. It
    passed for as long as the tool was also wrong. Labels are numbered from
    zero, but the loader writes the program to address 64, so a program that
    installs a trap vector from a label installed a pointer into the
    loader's own code -- `mem_protect`, `syscall`, `syscall_io`, `trap_timer`
    and `user_mode`, all five returning zero bytes from the board while
    passing testbenches where the program does start at zero.

    So the base-0 assembly is asserted to DIFFER. A test that only checks
    the tool against a constant retyped here cannot tell a fixed tool from a
    broken one; it can only tell that two transcriptions agree.
    """
    sys.path.insert(0, str(ROOT / "rtl" / "scripts"))
    import send_program

    tool = ROOT / "rtl" / "scripts" / "send_program.py"
    prog = ROOT / "rtl" / "programs" / "trap_timer.hasm"
    out = subprocess.run([sys.executable, str(tool), str(prog)],
                         cwd=ROOT, capture_output=True, check=True).stdout

    source = prog.read_text(encoding="utf-8")
    relocated = assemble(source, base=send_program.LOAD_BASE)
    assert out == bytes(_stream(relocated))
    assert struct.unpack(">I", out[:4])[0] == len(relocated)

    at_zero = assemble(source)
    assert len(at_zero) == len(relocated), "relocation changed the word count"
    assert at_zero != relocated, (
        "assembling at 0 and at 64 produced identical words, so this program "
        "carries no absolute label and cannot demonstrate relocation -- pick "
        "one that does, or the tool's base has stopped mattering")


def test_relocation_moves_the_absolute_labels_and_nothing_else() -> None:
    """Exactly the words that name an address move, and they move by 64."""
    sys.path.insert(0, str(ROOT / "rtl" / "scripts"))
    import send_program

    source = (ROOT / "rtl" / "programs" / "trap_timer.hasm").read_text(encoding="utf-8")
    at_zero = assemble(source)
    relocated = assemble(source, base=send_program.LOAD_BASE)

    moved = [(i, a, b) for i, (a, b) in enumerate(zip(at_zero, relocated, strict=True))
             if a != b]
    assert moved, "nothing moved"
    for _i, a, b in moved:
        assert b - a == send_program.LOAD_BASE, (
            f"a word moved by {b - a}, not by {send_program.LOAD_BASE}")
    assert len(moved) < len(at_zero), "every word moved -- that is not relocation"


def test_the_interpreter_boot_path_relocates_like_the_board() -> None:
    """_boot is this file's own loader path, and it assembled at 0 as well.

    trap_timer.hasm is the payload that tells the difference: its handler
    address moves with the program. Assembled at 0 through this same path it
    took 2,120 traps and never halted -- the board's failure, reproduced in
    the interpreter, invisible for as long as only label-free programs ran.
    """
    source = (ROOT / "rtl" / "programs" / "trap_timer.hasm").read_text(encoding="utf-8")
    m = _boot(source, steps=20000)
    assert m._halted, "the trap vector pointed into the loader -- the board's bug"
    assert m.regs.gpr[8] == 1, "the handler never ran"
    assert sum("TRAP" in t.description for t in m.trace) == 1


def test_the_load_address_has_one_source_and_it_is_the_loader() -> None:
    """64 is written in four places; the loader is the one the board runs.

    hcpu_pkg.vh names the IMEM registers but not where a program lands.
    loader.hasm decides that, twice -- where it starts writing, and where
    ERET enters. send_program.py and nui/freeze.py each carry a LOAD_BASE of
    their own, and the number already agreed everywhere while two of them
    assembled at 0 anyway. So the value is read out of the loader itself and
    every copy is held to it, rather than to each other.
    """
    import re

    sys.path.insert(0, str(ROOT / "rtl" / "scripts"))
    import send_program

    from hijaiyyah.nui.freeze import LOAD_BASE as FREEZE_BASE

    text = LOADER.read_text(encoding="utf-8")
    start = re.search(r"MOVI\s+R7,\s*(\d+)\s*\n\s*STORE\s+R7,\s*R5,\s*0xFF3", text)
    entry = re.search(r"MOVI\s+R7,\s*(\d+)\s*\n\s*STORE\s+R7,\s*R5,\s*0xFF9", text)
    assert start and entry, "the loader no longer sets IMEM_ADDR and TRAP_EPC the way this reads"
    assert start.group(1) == entry.group(1), "the loader writes to one address and enters another"

    loader_base = int(start.group(1))
    assert loader_base == LOAD_BASE == send_program.LOAD_BASE == FREEZE_BASE == 64


def test_the_bridge_targets_put_the_sealed_board_image_back() -> None:
    """Baking the loader rewrites program.hex, and program.hex is sealed.

    rtl/fpga/gowin/program.hex is tracked on purpose: the CosmicTera manifest
    seals it and check_board_hex re-assembles it from the Makefile's PROGRAM.
    `make bridge` left it alone only because of a bug -- program.hex was newer
    than loader.hasm, so make called it up to date and baked test_bsm into the
    "loader" bitstream. With that fixed the bridge targets really do write the
    loader image, and the wrapper simulation then read it and printed nothing.
    So every target that bakes the loader must put the sealed image back, from
    the same default PROGRAM check_board_hex uses.
    """
    import re

    makefile = (ROOT / "rtl" / "fpga" / "gowin" / "Makefile").read_text(encoding="utf-8")
    default = re.search(r"^PROGRAM\s*\?=\s*(\S+)\s*$", makefile, re.M)
    assert default, "the Makefile no longer names a default PROGRAM"

    for target, flash in (("bridge", "flash"), ("hdmi_bridge", "hdmi_flash")):
        recipe = re.search(rf"^{target}:\n((?:\t.*\n)+)", makefile, re.M)
        assert recipe, f"no {target} target"
        lines = [ln.strip() for ln in recipe.group(1).splitlines()]
        assert lines[0] == f"$(MAKE) PROGRAM=$(RTL_DIR)/programs/loader.hasm {flash}", lines
        assert f"$(MAKE) PROGRAM={default.group(1)} program.hex" in lines[1:], (
            f"{target} bakes the loader and leaves the sealed program.hex overwritten")


def test_the_wire_order_is_most_significant_byte_first() -> None:
    """
    The loader assembles each word with `SHLI 8` then `OR`, so the first byte
    it sees must be the most significant. Little-endian would load every
    instruction byte-reversed and the board would run something that looks
    almost like a program.
    """
    text = LOADER.read_text(encoding="utf-8")
    assert "SHLI  R3, R3, 8" in text
    assert "OR    R3, R3, R2" in text
    m = _boot("        MOVI  R9, 42\n        HALT\n")
    assert m.code[LOAD_BASE] == assemble("        MOVI R9, 42\n")[0]


def test_the_tool_refuses_a_program_that_would_not_fit() -> None:
    sys.path.insert(0, str(ROOT / "rtl" / "scripts"))
    import send_program

    with pytest.raises(ValueError, match="will not fit"):
        send_program.encode([0] * (send_program.MAX_WORDS + 1))
    assert send_program.MAX_WORDS == 4096 - LOAD_BASE


# ══════════════════════════════════════════════════════════════════
#  And in RTL, over a real serial pin
# ══════════════════════════════════════════════════════════════════

@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_the_boot_path_works_in_rtl_not_only_in_the_interpreter(tmp_path: Path) -> None:
    """
    The interpreter loading a program is worth something and is not the same
    claim: it has no UART timing, no BRAM latency, no pipeline, and no write
    port that could land a word one address late. This drives the actual pin
    at the actual baud into the actual design.

    It is also the test that found OP_ERET missing from decode, which two
    other suites had run past.
    """
    payload = assemble("        MOVI  R9, 42\n        MOVI  R10, 7\n        HALT\n")
    (tmp_path / "payload.txt").write_text(
        "\n".join(f"{b:02x}" for b in _stream(payload)) + "\n")

    loader_hex = subprocess.run(
        [sys.executable, str(ROOT / "rtl" / "scripts" / "asm2hex.py"), str(LOADER)],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout
    (tmp_path / "loader.hex").write_text(loader_hex)

    sources = [str(ROOT / "rtl" / "tb" / "tb_gowin_loader.v"),
               str(ROOT / "rtl" / "fpga" / "gowin" / "hcpu_gowin_top.v"),
               *sorted(str(p) for p in (ROOT / "rtl").glob("hcpu_*.v"))]
    subprocess.run(["iverilog", "-g2012", "-I", str(ROOT / "rtl"),
                    "-o", str(tmp_path / "tb"), *sources],
                   cwd=tmp_path, capture_output=True, check=True)
    out = subprocess.run(["vvp", str(tmp_path / "tb")], cwd=tmp_path,
                         capture_output=True, text=True).stdout
    assert "PASS" in out, out
