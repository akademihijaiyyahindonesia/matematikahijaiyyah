"""
The boot path: what turns the Tang Nano 9K from a device you flash into a
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
    m.rx_queue = _stream(assemble(payload_src))
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
    missing = claimed - recognised - {"OP_HALT_ERR"}
    assert not missing, f"decode falls through to HALT_ERR for: {sorted(missing)}"


def test_the_default_branch_really_is_a_halt() -> None:
    """The reason the test above matters, pinned so it cannot quietly change."""
    tail = DECODE[DECODE.index("default: begin"):]
    assert "id_is_halt <= 1'b1" in tail[:400]


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

def test_the_host_tool_emits_exactly_what_the_loader_expects() -> None:
    tool = ROOT / "rtl" / "scripts" / "send_program.py"
    prog = ROOT / "rtl" / "programs" / "trap_timer.hasm"
    out = subprocess.run([sys.executable, str(tool), str(prog)],
                         cwd=ROOT, capture_output=True, check=True).stdout

    words = assemble(prog.read_text(encoding="utf-8"))
    assert out == bytes(_stream(words))
    assert struct.unpack(">I", out[:4])[0] == len(words)


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
