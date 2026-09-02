"""
The substitution as gates, held bit-for-bit against the substitution as a table.

GAPS.md §6 listed the 256-entry lookup as an open weakness: in software a
data-indexed table is the AES cache-timing target, because the cache lines
touched leak the index and the index is the state. The closure is to stop
using a table — compute the inverse in GF((2⁴)²) with logic, where there is
no address to leak and the propagation delay is the same for every input.

A rewrite of a cryptographic primitive is exactly the kind of change that
looks right and is wrong, so these tests are about equality with what already
worked, and about the equality being load-bearing rather than vacuous.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from hijaiyyah.crypto import cube
from hijaiyyah.crypto import sbox_logic as logic

ROOT = Path(__file__).resolve().parents[2]


# ══════════════════════════════════════════════════════════════════
#  Equality with the table it replaces
# ══════════════════════════════════════════════════════════════════

def test_the_logic_reproduces_every_entry_of_the_sealed_table() -> None:
    """
    All 256, not a sample. A substitution that is right on 255 inputs is a
    broken cipher, and nothing in a statistical test would notice.
    """
    assert [logic.substitute(x) for x in range(256)] == list(cube.SBOX)


def test_the_equality_is_load_bearing() -> None:
    """
    Sabotage: one bit changed in the basis matrix must break the agreement.
    Without this, the test above would still pass if `substitute` had quietly
    become a table lookup — and the whole point is that it is not one.
    """
    original = list(logic.TO_TOWER)
    try:
        logic.TO_TOWER[0] ^= 0x01
        assert [logic.substitute(x) for x in range(256)] != list(cube.SBOX)
    finally:
        logic.TO_TOWER[:] = original
    assert [logic.substitute(x) for x in range(256)] == list(cube.SBOX)


def test_no_table_is_consulted_at_byte_width() -> None:
    """
    The claim is the absence of a 256-entry lookup, so it is checked as an
    absence. The 4-bit inverse remains a sixteen-entry map, which synthesises
    to four LUT4s — logic with a fixed delay, not memory with an address.
    """
    assert logic.report()["table_entries"] == 0
    assert len(logic.GF4_INVERSE) == 16


# ══════════════════════════════════════════════════════════════════
#  The tower is derived, not copied
# ══════════════════════════════════════════════════════════════════

def test_the_basis_change_is_a_field_isomorphism() -> None:
    """
    Everything rests on T carrying multiplication across, so it is checked on
    every one of the 65,536 pairs rather than sampled. An additive bijection
    that is not multiplicative would still look like a permutation and would
    produce a substitution that is subtly not the inverse map.
    """
    mul = logic._composite_mul(logic.NU)
    for a in range(256):
        ta = logic.apply_matrix(logic.TO_TOWER, a)
        for b in range(256):
            assert logic.apply_matrix(
                logic.TO_TOWER, logic.gf8_mul(a, b)
            ) == mul(ta, logic.apply_matrix(logic.TO_TOWER, b))


def test_beta_is_a_root_of_the_sealed_polynomial() -> None:
    """
    What ties the tower to this cube rather than to AES. Canright's constants
    are for 0x11B; the sealed field is chosen by the digest, and β had to be
    searched for it. If β stopped satisfying the sealed polynomial, T would
    map into a different field and the S-box would be a different function.
    """
    mul = logic._composite_mul(logic.NU)

    def power(a: int, e: int) -> int:
        result = 1
        while e:
            if e & 1:
                result = mul(result, a)
            a = mul(a, a)
            e >>= 1
        return result

    total = 0
    for exponent in range(9):
        if (cube.POLYNOMIAL >> exponent) & 1:
            total ^= power(logic.BETA, exponent) if exponent else 1
    assert total == 0


def test_the_basis_matrices_invert_each_other() -> None:
    for x in range(256):
        assert logic.apply_matrix(
            logic.FROM_TOWER, logic.apply_matrix(logic.TO_TOWER, x)
        ) == x


def test_the_derivation_is_deterministic() -> None:
    """A search that returned a different tower per run would make the RTL
    unreproducible, and a generated file that changes on every run is not a
    generated file."""
    nu, beta, to_tower, from_tower = logic._derive()
    assert (nu, beta, to_tower, from_tower) == (
        logic.NU,
        logic.BETA,
        logic.TO_TOWER,
        logic.FROM_TOWER,
    )


# ══════════════════════════════════════════════════════════════════
#  The RTL and the Python are one definition
# ══════════════════════════════════════════════════════════════════

def test_the_generated_rtl_is_not_stale() -> None:
    """
    The gate that makes 'generated from the Python' true rather than a comment.
    A seal change that is not carried into the Verilog is a failing test here
    instead of a silicon bug later.
    """
    result = subprocess.run(
        ["python3", "tools/gen_sbox_rtl.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_testbenches_live_where_the_design_glob_will_not_find_them() -> None:
    """
    tests/test_integration/test_fpga_wrapper.py compiles `rtl/*.v` as design
    sources. Putting a testbench there gave the FPGA simulation a second
    `initial` block with its own `$finish`, and thirteen unrelated tests went
    red at once. Testbenches belong in rtl/tb/; this keeps them there.
    """
    strays = [p.name for p in (ROOT / "rtl").glob("tb_*.v")]
    assert not strays, f"testbenches in the design directory: {strays}"


def test_the_rtl_carries_no_byte_wide_table() -> None:
    """
    The whole point, checked in the Verilog itself: 256 case arms would mean
    the table came back.
    """
    source = (ROOT / "rtl" / "hijaiyyah_sbox.v").read_text(encoding="utf-8")
    assert source.count("8'h") < 40, "a byte-wide table appears to have returned"
    assert "gf4_mul" in source and "gf4_inv" in source


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_the_verilog_matches_the_sealed_table() -> None:
    """
    Simulated, not inspected. The Python being right says nothing about the
    gates: this runs all 256 inputs through the actual module.
    """
    build = subprocess.run(
        ["iverilog", "-o", "/tmp/tb_hijaiyyah_sbox", "rtl/hijaiyyah_sbox.v",
         "rtl/tb/tb_hijaiyyah_sbox.v"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["/tmp/tb_hijaiyyah_sbox"], capture_output=True, text=True)
    assert "PASS: 256/256" in run.stdout, run.stdout


# ══════════════════════════════════════════════════════════════════
#  The router: the same logic, WIDTH times, one clock
# ══════════════════════════════════════════════════════════════════

@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_the_router_keeps_every_lane_on_its_own_byte() -> None:
    """
    What the router adds over the S-box is wiring, so wiring is what this
    checks: one clock of latency for every input, reset clearing the stage,
    and no lane reading its neighbour's byte. Crossing the lanes produces a
    module that substitutes every byte correctly and permutes them, which no
    S-box test would see.

    Both failures were induced before this was trusted — crossing the generate
    index and removing the output register each turn it red.
    """
    build = subprocess.run(
        ["iverilog", "-o", "/tmp/tb_hijaiyyah_router", "rtl/hijaiyyah_sbox.v",
         "rtl/hijaiyyah_sbox_router.v", "rtl/tb/tb_hijaiyyah_sbox_router.v"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["/tmp/tb_hijaiyyah_router"], capture_output=True, text=True)
    assert "PASS:" in run.stdout, run.stdout


def test_the_router_documents_measured_area_not_an_estimate() -> None:
    """
    The area figures decide whether the full-face design fits on the board, so
    they have to come from synthesis. This holds the header to quoting the
    numbers yosys produced rather than a multiplication.
    """
    source = (ROOT / "rtl" / "hijaiyyah_sbox_router.v").read_text(encoding="utf-8")
    assert "MEASURED, not estimated" in source
    for figure in ("76 LUT4", "274 LUT4", "2023 LUT4", "6743 LUT4", "8640 LUT4"):
        assert figure in source, f"{figure} missing from the router header"


def test_the_face_is_two_hundred_bytes_not_twenty_five() -> None:
    """
    The arithmetic behind a claim I got wrong three times before checking it.

    The cube face is 25 *lanes* of 64 bits — 1600 bits, 200 bytes — so a
    router at WIDTH=25 covers one eighth of a face, not all of it. A fully
    parallel face needs 200 S-boxes: 15,200 LUT4 in logic, which does not fit
    a Tang Nano 9K's 8,640. The header has to keep saying so.
    """
    from hijaiyyah.crypto import cube

    face_bytes = cube.STATE_LANES * cube.LANE_BITS // 8
    assert face_bytes == 200
    assert face_bytes * 76 > 8640, "a full parallel face would fit after all"

    source = (ROOT / "rtl" / "hijaiyyah_sbox_router.v").read_text(encoding="utf-8")
    assert "SCALE, CORRECTED" in source
    assert "200 BYTES" in source
    assert "does NOT fit" in source


def test_the_area_figures_name_their_mapping_and_their_limit() -> None:
    """
    An area number without its method is the soft kind. The ratio is
    method-independent — both sides went through one mapping — but the
    percentage-of-device line adds an assumption: that generic LUT4 count
    tracks Gowin LUT4 count. synth_gowin did not complete on this module here
    and nextpnr is not installed, so there is no placed-and-routed figure. The
    header has to keep saying which of the two it is.
    """
    source = (ROOT / "rtl" / "hijaiyyah_sbox_router.v").read_text(encoding="utf-8")
    assert "abc -lut 4" in source, "the mapping method is unnamed"
    assert "proxy, not a fitting report" in source
    assert "no placed-and-routed number exists yet" in source


# ══════════════════════════════════════════════════════════════════
#  The linear layer in gates — step one of driving the impulser
# ══════════════════════════════════════════════════════════════════

def test_the_generated_linear_rtl_is_not_stale() -> None:
    """RHO and PI live in cube.py; this keeps the Verilog behind them."""
    result = subprocess.run(
        ["python3", "tools/gen_linear_rtl.py", "--check"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_the_linear_verilog_matches_cube_linear_layer() -> None:
    """
    Sixty-four random 1600-bit states, simulated. A wrong rotation constant or
    a swapped pi destination leaves the layer full rank and avalanche at 0.5 —
    only a vector comparison catches it, which is why this exists.

    Three sabotages were induced before trusting it: a shifted rho rotation, a
    swapped pi destination, and a dropped theta neighbour. All three caught.
    The first rho attempt matched nothing in the file and reported PASS, which
    is the reason a sabotage has to be verified to have actually applied.
    """
    build = subprocess.run(
        ["iverilog", "-g2012", "-o", "/tmp/tb_linear", "rtl/hijaiyyah_linear.v",
         "rtl/tb/tb_hijaiyyah_linear.v"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["/tmp/tb_linear"], cwd=ROOT, capture_output=True, text=True)
    assert "PASS: 64/64" in run.stdout, run.stdout


def test_the_linear_layer_states_its_real_cost() -> None:
    """
    "Pure XOR" is not "free". The layer synthesises to 2560 LUT4 — more than a
    25-byte substitution router — and the ramal trade is good because linear
    and substitution are an order of magnitude apart, not because one is free.
    The header has to carry the numbers, since the loose version of that
    reasoning is what motivated the schedule in the first place.
    """
    source = (ROOT / "rtl" / "hijaiyyah_linear.v").read_text(encoding="utf-8")
    assert "2560 LUT4" in source
    assert "not the same as" in source and "free" in source
    for figure in ("15,200 LUT4", "53,280 LUT4", "38,080 LUT4"):
        assert figure in source, f"{figure} missing from the cost accounting"


# ══════════════════════════════════════════════════════════════════
#  The core: the impulser's pulses, converted back into a computation
# ══════════════════════════════════════════════════════════════════

def test_substitution_is_position_independent_across_the_flat_state() -> None:
    """
    What lets the core slice a flat 200-byte state instead of tracking lanes.
    Asserted rather than assumed, because the whole slicing scheme rests on it.
    """
    import random as _random

    from hijaiyyah.crypto import cube

    rng = _random.Random(1)
    lanes = [rng.getrandbits(64) for _ in range(cube.STATE_LANES)]
    by_lane = [cube._substitute(x) for x in lanes]

    flat = b"".join(x.to_bytes(8, "little") for x in lanes)
    substituted = bytes(cube.SBOX[b] for b in flat)
    by_flat = [
        int.from_bytes(substituted[i * 8 : (i + 1) * 8], "little")
        for i in range(cube.STATE_LANES)
    ]
    assert by_lane == by_flat


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
@pytest.mark.parametrize("slice_bytes", [4, 8, 25, 50, 100])
def test_the_core_reproduces_the_python_at_every_slice_width(slice_bytes: int) -> None:
    """
    The impulser driving a real datapath, which is the only thing that makes a
    pacing generator more than a table. Every width lands on the same state.

    Two handshake bugs were found here and both looked like design faults. A
    registered `stall` is one clock late, so the generator advanced before the
    core was busy and its next linear pulse was dropped: 142 clocks instead of
    253 and a wrong state. Adding a wait state moved the race rather than
    closing it — still wrong, at 156. The fix is a combinational stall, raised
    on the clock the substitution is accepted.
    """
    build = subprocess.run(
        ["iverilog", "-g2012", f"-DSLICE_BYTES={slice_bytes}",
         "-o", f"/tmp/tb_core_{slice_bytes}",
         "rtl/hijaiyyah_ramal_core.v", "rtl/hijaiyyah_ramal_impulse.v",
         "rtl/hijaiyyah_linear.v", "rtl/hijaiyyah_sbox.v",
         "rtl/hijaiyyah_round_constants.v", "rtl/tb/tb_hijaiyyah_ramal_core.v"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([f"/tmp/tb_core_{slice_bytes}"], cwd=ROOT,
                         capture_output=True, text=True)
    assert "PASS: 28 rounds" in run.stdout, run.stdout


def test_the_core_header_reports_that_nothing_fits_the_board_yet() -> None:
    """
    Narrowing the slice does not keep shrinking the design — SLICE=4 costs
    more than SLICE=8, because the cost is the 1600-bit slice multiplexer and
    not the S-boxes. And the cheapest configuration is already over a Tang
    Nano 9K's 8,640 LUT4. Both belong in the header, not in a surprise on the
    board.
    """
    source = (ROOT / "rtl" / "hijaiyyah_ramal_core.v").read_text(encoding="utf-8")
    assert "CONTRADICTS THE OBVIOUS EXPECTATION" in source
    assert "NONE of these fit a Tang Nano 9K" in source
    assert "not built yet" in source


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
@pytest.mark.parametrize("slice_bytes", [4, 8, 25, 50])
def test_the_rotating_core_is_bit_identical_to_the_sliced_one(slice_bytes: int) -> None:
    """
    The architecture the measurement pointed at: rotate the state through one
    fixed substitution position instead of addressing it, so the 1600-bit
    multiplexer disappears. Same state, same clock count, roughly half the
    area — 6,331 LUT4 against 12,074 at SLICE=25 — and it fits the board.
    """
    build = subprocess.run(
        ["iverilog", "-g2012", f"-DSLICE_BYTES={slice_bytes}",
         "-o", f"/tmp/tb_rot_{slice_bytes}",
         "rtl/hijaiyyah_rotate_core.v", "rtl/hijaiyyah_ramal_impulse.v",
         "rtl/hijaiyyah_linear.v", "rtl/hijaiyyah_sbox.v",
         "rtl/hijaiyyah_round_constants.v", "rtl/tb/tb_hijaiyyah_rotate_core.v"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([f"/tmp/tb_rot_{slice_bytes}"], cwd=ROOT,
                         capture_output=True, text=True)
    assert "PASS: 28 rounds" in run.stdout, run.stdout


def test_the_rotating_core_reports_that_it_fits_and_how_that_was_measured() -> None:
    """
    The claim that closes this thread, with its method attached. Fitting is
    asserted from generic 4-LUT mapping, not from a vendor place-and-route,
    and the header has to keep saying which.
    """
    raw = (ROOT / "rtl" / "hijaiyyah_rotate_core.v").read_text(encoding="utf-8")
    # Comment prose wraps across lines, so match against normalised text —
    # the first version of this asserted a phrase that a line break had split.
    source = " ".join(raw.replace("//", " ").split())
    assert "6,229 LUT4" in source and "72%" in source
    assert "not a vendor fitting report" in source
    assert "Fmax has no value until the board arrives" in source


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_standby_holds_the_core_at_both_moments_it_can_be_asserted() -> None:
    """
    Two holds, because the two mechanisms cover disjoint cases and one
    position proves half.

    Inside a substitution the core's own standby branch holds it, and routing
    standby into `stall` is redundant there — `substituting` already stalls the
    generator. Outside a substitution nothing else holds the generator, so
    `stall` must carry standby, and the core branch alone is not enough. Each
    sabotage passes at one position and fails at the other, which is why both
    are tested: 79 mismatches without the core branch, 1 without the stall path.

    The first version of this test captured the frozen state *after* the first
    edge under standby, which hid a one-clock leak, and gated the generator's
    enable as well, which meant the core had nothing to do while held. Both
    sabotages passed against it. A sabotage that passes is a test proving
    nothing.
    """
    build = subprocess.run(
        ["iverilog", "-g2012", "-o", "/tmp/tb_standby",
         "rtl/hijaiyyah_rotate_core.v", "rtl/hijaiyyah_ramal_impulse.v",
         "rtl/hijaiyyah_linear.v", "rtl/hijaiyyah_sbox.v",
         "rtl/hijaiyyah_round_constants.v", "rtl/tb/tb_hijaiyyah_standby.v"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["/tmp/tb_standby"], cwd=ROOT, capture_output=True, text=True)
    assert "PASS: two holds" in run.stdout, run.stdout


def test_the_throughput_figures_name_the_clock_they_assume() -> None:
    """
    27 MHz is what the board's crystal offers, not what this design has been
    shown to close timing at. Fmax is unmeasured — that is E1, and it still has
    no value — so every per-second figure has to carry the assumption.
    """
    raw = (ROOT / "rtl" / "hijaiyyah_rotate_core.v").read_text(encoding="utf-8")
    source = " ".join(raw.replace("//", " ").split())
    assert "AT AN ASSUMED CLOCK" in source
    assert "achievable Fmax is unmeasured" in source
    assert "11.15 MB/s" in source
    # 11.15 is this core's rate fed a byte per clock. It was quoted as the
    # system's for many commits, which overstated it by 4x -- the header has to
    # say so, or the next reader makes the same substitution.
    assert "not the system's" in source
    assert "2.59 MB/s, not 11.15" in source


# ══════════════════════════════════════════════════════════════════
#  The sponge: what turns the permutation into a hash
# ══════════════════════════════════════════════════════════════════

@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_the_sponge_absorbs_two_rate_blocks_exactly_like_cube_py() -> None:
    """
    The first point where the whole crypto datapath is in gates at once:
    substitution, linear layer, round constants, pacing, and the sponge
    scheduling around them. Two rate blocks, so the permutation runs more than
    once and a second-block failure cannot pass as coincidence.

    Three bugs were found getting here and all three were mine, in the
    testbench or the handshake:

    * the lane count was written as a literal and read past the vector file,
      absorbing lanes of X — it is bound to the file at build time now;
    * the ready/valid feed advanced whether or not the sponge had taken the
      lane, so every lane offered during a permutation was dropped;
    * the sponge sampled `perm_done` in the clock `start` was clearing it, read
      the *previous* permutation's done, and skipped the second permutation
      entirely — 28 substitutions in the first block, zero in the second.

    Each produced a fully defined, completely wrong state, which is the worst
    shape a bug can take: nothing looks uninitialised.
    """
    lanes = (ROOT / "rtl" / "tb" / "sponge_lanes.hex").read_text().strip().split("\n")
    build = subprocess.run(
        ["iverilog", "-g2012", f"-DLANES={len(lanes)}", "-o", "/tmp/tb_sponge",
         "rtl/hijaiyyah_sponge.v", "rtl/hijaiyyah_ramal_impulse.v",
         "rtl/hijaiyyah_rotate_core.v", "rtl/hijaiyyah_linear.v",
         "rtl/hijaiyyah_sbox.v", "rtl/hijaiyyah_round_constants.v",
         "rtl/tb/tb_hijaiyyah_sponge.v"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["/tmp/tb_sponge"], cwd=ROOT, capture_output=True, text=True)
    assert "PASS:" in run.stdout, run.stdout


def test_the_sponge_documents_where_padding_and_squeezing_are_not() -> None:
    """
    Two real boundaries rather than omissions. Padding needs the message
    length, which a streaming interface does not have until the stream ends,
    so the caller pads. Squeezing would need a read port, and a read port is
    the 1600-bit multiplexer this design spent six thousand LUT4 removing —
    the whole state is already on `out_state`, so the consumer has the wires.
    """
    raw = (ROOT / "rtl" / "hijaiyyah_sponge.v").read_text(encoding="utf-8")
    source = " ".join(raw.replace("//", " ").split())
    assert "PADDING IS NOT IN THIS MODULE" in source
    assert "SQUEEZING IS NOT IN THIS MODULE" in source
    assert "The caller pads; this absorbs" in source


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_standby_and_load_outrank_an_absorb() -> None:
    """
    A priority bug I introduced and did not catch with anything already here.

    The absorb branch was inserted ahead of `standby` and `load`, so an absorb
    overrode both: asserting standby did not hold an absorb, and load did not
    clear the state while one was in flight. No existing test saw it, because
    the sponge never drives those signals together — only a probe that
    deliberately collides them does. A hold must hold everything and a clear
    must clear everything.
    """
    build = subprocess.run(
        ["iverilog", "-g2012", "-o", "/tmp/tb_priority",
         "rtl/hijaiyyah_rotate_core.v", "rtl/hijaiyyah_linear.v",
         "rtl/hijaiyyah_sbox.v", "rtl/hijaiyyah_round_constants.v",
         "rtl/tb/tb_hijaiyyah_priority.v"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["/tmp/tb_priority"], cwd=ROOT, capture_output=True, text=True)
    assert "PASS: standby holds an absorb" in run.stdout, run.stdout


# ══════════════════════════════════════════════════════════════════
#  Ka'bah whole: bits on a wire to a permuted state
# ══════════════════════════════════════════════════════════════════

@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_the_whole_system_runs_from_raw_bits_to_the_python_state() -> None:
    """
    Every piece was verified alone; this is the one that says they fit
    together. 3,069 raw bits at an arbitrary offset with no byte boundary
    given, through the deserialiser, the jamrah gate, the node counter, lane
    assembly, the tawaf ring and two permutations — landing on exactly the
    state cube.py computes.

    **The bug only integration could find.** The deserialiser put the first
    data bit at shifter[0] instead of shifter[7], so the next shift pushed it
    straight out: the FIRST byte of every stream was wrong and every byte
    after it was right. tb_hijaiyyah_wave passed 78/78 with that present,
    because a classifier over 64-byte windows cannot see one wrong byte. Only
    assembling lanes and comparing against cube.py exposed it.

    Backpressure is exercised here too — the run holds 622 clocks — because a
    source that ignores it loses every lane offered during a permutation.
    """
    bits = (ROOT / "rtl" / "tb" / "kabah_bits.hex").read_text().strip().split("\n")
    sources = [
        "rtl/hijaiyyah_kabah_top.v", "rtl/hijaiyyah_deserialiser.v",
        "rtl/hijaiyyah_jamrah_gate.v", "rtl/hijaiyyah_node_counter.v",
        "rtl/hijaiyyah_sponge.v", "rtl/hijaiyyah_ramal_impulse.v",
        "rtl/hijaiyyah_rotate_core.v", "rtl/hijaiyyah_linear.v",
        "rtl/hijaiyyah_sbox.v", "rtl/hijaiyyah_round_constants.v",
        "rtl/tb/tb_hijaiyyah_kabah_top.v",
    ]
    build = subprocess.run(
        ["iverilog", "-g2012", f"-DNBITS={len(bits)}",
         "-s", "tb_hijaiyyah_kabah_top", "-o", "/tmp/tb_kabah_top", *sources],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["/tmp/tb_kabah_top"], cwd=ROOT,
                         capture_output=True, text=True)
    assert "PASS:" in run.stdout, run.stdout
    assert "clocks held" in run.stdout


def test_the_top_level_names_what_it_does_not_contain() -> None:
    """
    A block diagram invites the wrong reading, so the header has to refuse it.
    The gate and the counter are keyless triage. The sponge is [EH]. Layer 3 —
    HMAC-SHA256, the part that actually carries the security — is not in
    hardware at all, and neither is phase discovery.
    """
    raw = (ROOT / "rtl" / "hijaiyyah_kabah_top.v").read_text(encoding="utf-8")
    source = " ".join(raw.replace("//", " ").split())
    assert "is NOT in this module" in source
    assert "no SHA-256 core" in source
    assert "unauthenticated until software signs it" in source
    assert "Phase discovery is also software" in source


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_the_gate_actually_gates_and_the_break_point_is_joined() -> None:
    """
    An instruction I acknowledged and then skipped for several commits.

    `gate_pulse` went to an output port and the sponge absorbed every byte
    regardless — a detector wired to nothing, which is worse than no detector
    because the output looks like enforcement. In `gate_mode` only bytes that
    name a letter reach the sponge, and the *position* of the first refusal is
    held: "the stream broke at byte 37" rather than "the stream broke".

    Verified on a codex record with one byte corrupted at a known position:
    the break is reported at exactly 37, one refusal counted, and the absorbed
    state equals cube.py over the admitted bytes only. Three sabotages all
    caught — disabling the gate, pinning the position to zero, and counting
    without reporting.

    The mode is a mode on purpose: the check is that a byte names a letter,
    1..28, which is true of a codex record and false of nearly every other
    byte. Gate what is parsed as letters; pass through what is not.
    """
    bits = (ROOT / "rtl" / "tb" / "gate_bits.hex").read_text().strip().split("\n")
    sources = [
        "rtl/hijaiyyah_kabah_top.v", "rtl/hijaiyyah_deserialiser.v",
        "rtl/hijaiyyah_jamrah_gate.v", "rtl/hijaiyyah_node_counter.v",
        "rtl/hijaiyyah_sponge.v", "rtl/hijaiyyah_ramal_impulse.v",
        "rtl/hijaiyyah_rotate_core.v", "rtl/hijaiyyah_linear.v",
        "rtl/hijaiyyah_sbox.v", "rtl/hijaiyyah_round_constants.v",
        "rtl/tb/tb_hijaiyyah_gate_mode.v",
    ]
    build = subprocess.run(
        ["iverilog", "-g2012", f"-DNBITS={len(bits)}",
         "-s", "tb_hijaiyyah_gate_mode", "-o", "/tmp/tb_gate_mode", *sources],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(["/tmp/tb_gate_mode"], cwd=ROOT,
                         capture_output=True, text=True)
    assert "PASS: break at byte 37" in run.stdout, run.stdout
