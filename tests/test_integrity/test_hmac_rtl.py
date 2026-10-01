"""
Ka'bah lapis 3 in logic: HMAC-SHA256 as RTL, held to the standards' own vectors.

Lapis 3 is the one layer of Ka'bah that carries the security, and until this
file it lived only in software -- hmac.new in src/hijaiyyah/crypto/signing.py.
rtl/hijaiyyah_sha256_core.v, rtl/hijaiyyah_sha256_stream.v and
rtl/hijaiyyah_hmac.v put the same construction into logic; nothing in them is
new cryptography, and the benches below hold them to the vectors the
standards themselves publish, not to vectors this repository invented:

    - FIPS 180-4's example messages and its one-million-'a' long message;
    - RFC 4231 test cases 1-7, which rtl/tb/gen_hmac_vectors.py checks against
      the RFC text before writing them;
    - every message length 0..129 (every padding boundary of one and two
      blocks) and seeded random keys and messages, against Python's hashlib
      and hmac.

The third bench drives rtl/fpga/gowin/hijaiyyah_hmac_gowin_top.v only through
its UART pins at the real 27 MHz and 115200 baud -- the way the board and
rtl/scripts/hmac_uart_test.py will.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOWIN = ROOT / "rtl" / "fpga" / "gowin"

CORE = ["rtl/hijaiyyah_sha256_stream.v", "rtl/hijaiyyah_sha256_core.v"]
HMAC = ["rtl/hijaiyyah_hmac.v", *CORE]
WRAPPER = ["rtl/fpga/gowin/hijaiyyah_hmac_gowin_top.v", *HMAC,
           "rtl/hcpu_uart_rx.v", "rtl/hcpu_uart_tx.v"]


def _bench(bench: str, sources: list[str], timeout: int) -> str:
    top = Path(bench).stem
    out = f"/tmp/{top}.vvp"
    build = subprocess.run(
        ["iverilog", "-g2012", "-s", top, "-o", out, bench, *sources],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["vvp", out], cwd=ROOT, capture_output=True,
                         text=True, timeout=timeout)
    assert run.returncode == 0, run.stdout[-3000:]
    return run.stdout


def _passed(stdout: str) -> int:
    m = re.search(r"SEMUA LULUS \((\d+) pemeriksaan\)", stdout)
    assert m, stdout[-3000:]
    return int(m.group(1))


def test_sha256_stream_meets_fips_180_4() -> None:
    """155 digests: FIPS 180-4's examples, every length 0..129, twenty random
    lengths to 999, and the one-million-'a' message."""
    out = _bench("rtl/tb/tb_hijaiyyah_sha256_stream.v", CORE, timeout=600)
    assert _passed(out) == 155
    assert ("digest=cdc76e5c9914fb9281a1c7e284d73e67"
            "f1809a48a497200e046d39ccc7112cd0  OK") in out


def test_hmac_meets_rfc_4231_and_its_timing_does_not_follow_the_data() -> None:
    """RFC 4231 cases 1-7 and sixty random keys/messages, plus one timing
    check: 100 bytes of 0x00 under an all-zero key and 100 bytes of 0xFF under
    an all-0xFF key take the same number of clocks."""
    out = _bench("rtl/tb/tb_hijaiyyah_hmac.v", HMAC, timeout=300)
    assert _passed(out) == 68
    for case in range(1, 8):
        assert re.search(rf"RFC4231-{case} len=\d+ cycles=\d+ +OK", out), case
    assert "EQUAL" in out


def test_the_board_wrapper_answers_through_its_uart_pins() -> None:
    """Ten requests framed exactly as rtl/scripts/hmac_uart_test.py frames
    them, answered bit-exact over uart_txd."""
    out = _bench("rtl/tb/tb_hijaiyyah_hmac_gowin_top.v", WRAPPER, timeout=600)
    assert _passed(out) == 10


def test_the_board_wrapper_is_ten_pins() -> None:
    wrapper = (GOWIN / "hijaiyyah_hmac_gowin_top.v").read_text(encoding="utf-8")
    head = wrapper[wrapper.index("module hijaiyyah_hmac_gowin_top"):]
    head = head[head.index(") (") : head.index(");")]
    bits = sum(int(hi) + 1 for hi in
               re.findall(r"(?:input|output)\s+(?:wire|reg)?\s*\[\s*(\d+)\s*:\s*0\]", head))
    bits += len(re.findall(r"(?:input|output)\s+wire\s+\w", head))
    assert bits == 10, f"the HMAC wrapper has {bits} pins, not 10"


def test_the_board_script_checks_against_the_repository_signing_path() -> None:
    """hmac_uart_test.py compares the board with signing.sign_bytes -- the
    software lapis 3 the logic replaces -- and refuses to run if that path
    disagrees with the RFC 4231 text. Run without a port it only prints."""
    run = subprocess.run(
        [sys.executable, "rtl/scripts/hmac_uart_test.py", "--random", "3"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert run.returncode == 0, run.stderr
    lines = run.stdout.splitlines()
    assert len(lines) == 10
    assert lines[1].endswith(
        "want=5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843")
    script = (ROOT / "rtl" / "scripts" / "hmac_uart_test.py").read_text(encoding="utf-8")
    assert "from hijaiyyah.crypto.signing import sign_bytes" in script
