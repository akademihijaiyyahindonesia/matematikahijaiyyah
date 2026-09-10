"""The phase lock, the receiver, and the limits both of them really have.

Every figure quoted in `wave/lock.py` is recounted here from the sealed
table rather than copied, so a change to the table moves the assertion
instead of leaving a stale number in a docstring.

Two of these tests exist to hold a limit open rather than to confirm a
success: locking recovers 2.77 bits and a letter needs 4.81, and unwrapping
fails above half the sample rate. Both are properties of the method, not
defects to be fixed later, and a version that quietly stopped exhibiting
them would be reporting more than it measured.
"""
from __future__ import annotations

import collections
import math

import pytest

from hijaiyyah.core.guards import compute_U
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.receiver import (
    BOARD_CLOCK_HZ,
    MATRIX_ORDERS,
    MOTIFS,
    QUANTUM_DEG,
    RUNGS,
    SIGNATURES,
    WIRE_PERIODS,
    PhaseLock,
    RangeReceiver,
    degrees_of,
    emitted_cycle,
    lock_angle,
    matrix_period,
    narrow,
    phase_ramp,
    rung_of,
    tone_hz,
)

ENTRIES = MASTER_TABLE.all_entries()


def _ramp_to(degrees: float, step: float = 45.0) -> list:
    """Wrapped phase climbing to an angle, in steps well under half a turn."""
    n = round(degrees / step)
    return [(i * step) % 360.0 for i in range(n + 1)]


# ── the ladder is read from the table, not written down ──────────

def test_the_ladder_is_derived_and_rung_seven_is_empty() -> None:
    """8 occupied rungs across positions 0..8, with 630 degrees unoccupied."""
    expected = collections.defaultdict(list)
    for entry in ENTRIES:
        expected[entry.vector[0]].append(entry.char)

    assert {k: tuple(v) for k, v in expected.items()} == RUNGS
    assert len(RUNGS) == 8, f"{len(RUNGS)} rungs occupied, not 8"
    assert min(RUNGS) == 0 and max(RUNGS) == 8
    assert 7 not in RUNGS, "rung 7 gained a letter; the free rejection is gone"
    assert sum(len(v) for v in RUNGS.values()) == len(ENTRIES) == 28


def test_the_quantum_comes_from_the_closed_curve_coefficient() -> None:
    """90 degrees is 360/4, and the 4 is what one closed curve costs in U.

    Definition 11.1.1 weights Qc by 4 because a curve that closes is a whole
    turn. If the grid and the guard ever used different numbers, the
    receiver would be snapping signal to a ladder the guards do not check.
    """
    one_closed_curve = [0] * 18
    one_closed_curve[13] = 1  # Qc
    assert compute_U(one_closed_curve) == 4, "Qc no longer costs a whole turn"
    assert 360.0 / QUANTUM_DEG == 4.0
    assert QUANTUM_DEG == 90.0


def test_a_rung_cannot_name_a_letter_and_the_bits_say_why() -> None:
    """2.77 bits arrive, 4.81 are needed. The gap is what `candidates` is for."""
    n = len(ENTRIES)
    entropy = -sum(len(v) / n * math.log2(len(v) / n) for v in RUNGS.values())
    assert entropy == pytest.approx(2.77, abs=0.01)
    assert math.log2(n) == pytest.approx(4.81, abs=0.01)
    assert entropy < math.log2(n), "a rung would now determine a letter"

    alone = sum(1 for v in RUNGS.values() if len(v) == 1)
    assert alone == 2, f"{alone} letters sit alone on a rung, not 2"


def test_adding_the_other_blocks_is_what_resolves_a_letter() -> None:
    """Point, line and curve counts finish what turning alone cannot.

    N is nuqtah, K is khatt, Q is qaws -- and only with all three does the
    signature separate all 28. This is the measured reason a phase
    measurement is never handed back as a character.
    """
    def classes(indices):
        return len({tuple(entry.vector[i] for i in indices) for entry in ENTRIES})

    assert classes([0]) == 8
    assert classes(range(4)) == 21          # + N
    assert classes(range(9)) == 26          # + K
    assert classes(range(14)) == len(ENTRIES)   # + Q, all distinct


# ── wave in, rung out ────────────────────────────────────────────

@pytest.mark.parametrize("entry", ENTRIES, ids=[e.char for e in ENTRIES])
def test_every_letter_survives_the_round_trip(entry) -> None:
    """Letter -> angle -> wrapped wave -> lock -> the rung it started on."""
    target = degrees_of(entry.char)
    assert target == entry.vector[0] * QUANTUM_DEG

    result = PhaseLock().sequence(_ramp_to(target))[-1]
    assert result.rung == entry.vector[0], entry.char
    assert entry.char in result.letters
    assert result.residual_deg == pytest.approx(0.0, abs=1e-9)
    assert result.in_alphabet


def test_a_wrapped_detector_would_lose_half_the_ladder() -> None:
    """Why the accumulator exists: 8 rungs fold onto 4 without it.

    Alif at 0, five letters at 360 and Haa at 720 are one phase modulo a
    turn. Reporting wrapped phase would merge them and the ladder would
    stop being a ladder.
    """
    folded = {rung % 4 for rung in RUNGS}
    assert len(folded) == 4 < len(RUNGS)

    haa = next(e for e in ENTRIES if e.vector[0] == 8)
    alif = next(e for e in ENTRIES if e.vector[0] == 0)
    assert degrees_of(haa.char) % 360.0 == degrees_of(alif.char) % 360.0
    assert PhaseLock().sequence(_ramp_to(degrees_of(haa.char)))[-1].rung == 8


def test_rung_seven_locks_in_range_and_outside_the_alphabet() -> None:
    """On grid, no letter. A rejection with nothing to tune."""
    result = PhaseLock().sequence(_ramp_to(7 * QUANTUM_DEG))[-1]
    assert result.rung == 7
    assert result.letters == () and not result.in_alphabet
    assert result.residual_deg == pytest.approx(0.0, abs=1e-9)


def test_off_grid_samples_report_their_distance_rather_than_hiding_it() -> None:
    for offset in (-44.0, -1.0, 0.0, 1.0, 44.0):
        result = lock_angle(180.0 + offset)
        assert result.rung == 2
        assert result.residual_deg == pytest.approx(offset)
    assert rung_of(134.0) == 1 and rung_of(136.0) == 2


def test_loop_tops_are_the_mod_four_gate() -> None:
    """The gate of Theorem 11.4.1, in the signal domain: whole turns."""
    tops = [rung for rung in RUNGS if lock_angle(rung * QUANTUM_DEG).is_loop_top]
    assert tops == [0, 4, 8]
    assert sum(len(RUNGS[rung]) for rung in tops) == 7, (
        "the gate no longer selects the 7 possibly-closed letters")


# ── lock mode ────────────────────────────────────────────────────

def test_lock_is_earned_over_several_samples_not_claimed_on_one() -> None:
    rx = RangeReceiver(sample_rate=4.0, tolerance_deg=10.0)
    for i in range(rx.lock_after - 1):
        rx.feed((i * 90.0) % 360.0)
        assert not rx.locked, f"lock claimed after {i + 1} samples"
    rx.feed(((rx.lock_after - 1) * 90.0) % 360.0)
    assert rx.locked


def test_lock_is_lost_the_moment_a_sample_leaves_tolerance() -> None:
    rx = RangeReceiver(sample_rate=4.0, tolerance_deg=10.0)
    rx.receive([(i * 90.0) % 360.0 for i in range(8)])
    assert rx.locked
    rx.feed((8 * 90.0 + 30.0) % 360.0)   # 30 degrees off, tolerance is 10
    assert not rx.locked, "an off-grid sample did not break lock"


def test_the_sequence_collapses_runs_and_the_raw_stream_is_kept() -> None:
    """A held tone is one symbol, not one per sample."""
    rx = RangeReceiver(sample_rate=8.0)
    rx.receive([0.0] * 5 + [90.0] * 5 + [180.0] * 5)
    assert rx.sequence == (0, 1, 2)
    assert len(rx.locks) == 15, "the per-sample stream was collapsed too"


def test_the_receiver_names_candidates_and_never_a_single_letter() -> None:
    rx = RangeReceiver(sample_rate=8.0)
    rx.receive(_ramp_to(3 * QUANTUM_DEG))
    assert rx.sequence[-1] == 3
    assert rx.candidates[-1] == RUNGS[3]
    assert len(rx.candidates[-1]) == 6, "rung 3 no longer carries six letters"


def test_the_receiver_flags_the_rung_with_no_letter() -> None:
    rx = RangeReceiver(sample_rate=8.0)
    rx.receive(_ramp_to(7 * QUANTUM_DEG))
    assert 7 in rx.sequence
    assert rx.rejected, "rung 7 passed as though it were a letter"
    assert all(rx.candidates[i] == () for i in rx.rejected)


def test_calibration_anchors_sit_only_on_loop_tops() -> None:
    rx = RangeReceiver(sample_rate=8.0, tolerance_deg=10.0)
    rx.receive(_ramp_to(8 * QUANTUM_DEG, step=90.0))
    anchors = rx.calibration()
    assert [a.rung for a in anchors] == [0, 4, 8]
    assert all(a.residual_deg == pytest.approx(0.0, abs=1e-9) for a in anchors)
    assert all(a.rung % 4 == 0 for a in anchors)


def test_a_constant_offset_shows_up_at_every_anchor() -> None:
    """What the anchors are for: measured against a known zero."""
    rx = RangeReceiver(sample_rate=8.0, tolerance_deg=10.0)
    rx.receive([(5.0 + i * 90.0) % 360.0 for i in range(9)])
    anchors = rx.calibration()
    assert [a.rung for a in anchors] == [0, 4, 8]
    assert all(a.residual_deg == pytest.approx(5.0) for a in anchors)


# ── frequency, and the limit on recovering it ────────────────────

def test_frequency_is_recovered_below_half_the_sample_rate() -> None:
    rx = RangeReceiver(sample_rate=1000.0)
    rx.receive(phase_ramp(hz=10.0, sample_rate=1000.0, samples=101))
    assert rx.frequency_hz() == pytest.approx(10.0, abs=1e-6)


def test_above_half_the_sample_rate_the_recovery_is_wrong_and_stays_wrong() -> None:
    """The aliasing limit, asserted rather than mentioned.

    At 600 Hz sampled at 1000, each step is 216 degrees -- more than half a
    turn -- so the shortest signed path reads it as -144, and the receiver
    reports -400 Hz with no sign that anything went wrong. This is the
    reason the module says the input must be oversampled, and the test is
    here so nobody later reads `frequency_hz` as unconditional.
    """
    rx = RangeReceiver(sample_rate=1000.0)
    rx.receive(phase_ramp(hz=600.0, sample_rate=1000.0, samples=101))
    recovered = rx.frequency_hz()
    assert recovered == pytest.approx(-400.0, abs=1e-6)
    assert abs(recovered - 600.0) > 100.0


# ── refusals ─────────────────────────────────────────────────────

def test_a_tolerance_wider_than_half_a_rung_is_refused() -> None:
    """At 45 degrees every sample is in tolerance and lock means nothing."""
    with pytest.raises(ValueError, match="inside a rung"):
        RangeReceiver(sample_rate=1.0, tolerance_deg=45.0)
    with pytest.raises(ValueError, match="sample_rate"):
        RangeReceiver(sample_rate=0.0)


def test_an_unsealed_letter_is_refused_rather_than_given_an_angle() -> None:
    with pytest.raises(KeyError):
        degrees_of("ء")


def test_hcserver_is_the_receiver_itself_not_a_copy_of_it() -> None:
    """The old glossary name survives; a second implementation does not."""
    from hijaiyyah.net.server import HCServer

    assert HCServer is RangeReceiver


# ══════════════════════════════════════════════════════════════════
#  Frequency: what reaches the wire, and what only describes the matrix
# ══════════════════════════════════════════════════════════════════

def test_matrix_order_and_wire_period_are_not_the_same_number() -> None:
    """Six letters where they disagree, named rather than counted.

    `cosmic-codex-jim/WAVE.md` tabulates matrix order and calls it the
    letter's emitted period. For these six it is not: the matrix cycles and
    the emitted bit does not. Naming them means a change to the table has to
    move this list, instead of a count staying accidentally right.
    """
    disagree = sorted(c for c in MOTIFS if MATRIX_ORDERS[c] != WIRE_PERIODS[c])
    assert disagree == sorted(["ب", "ح", "ط", "ظ", "ل", "م"])
    for char in disagree:
        assert MATRIX_ORDERS[char] > WIRE_PERIODS[char], char
        assert len(set(MOTIFS[char])) == 1, f"{char} emits a varying motif"


def test_the_two_banks_and_why_only_one_is_receivable() -> None:
    """Five periods in the matrix, three on the wire. Both recomputed."""
    assert dict(sorted(collections.Counter(MATRIX_ORDERS.values()).items())) == {
        1: 16, 2: 2, 3: 7, 4: 1, 31: 2}
    assert dict(sorted(collections.Counter(WIRE_PERIODS.values()).items())) == {
        1: 22, 3: 4, 31: 2}
    assert sum(collections.Counter(WIRE_PERIODS.values()).values()) == len(ENTRIES)


def test_twenty_two_letters_are_silent_on_the_wire_not_sixteen() -> None:
    """The correction, stated as a number a receiver could check."""
    silent = [c for c, p in WIRE_PERIODS.items() if p == 1]
    assert len(silent) == 22
    assert all(tone_hz(c) == 0.0 for c in silent)
    assert all(len(set(MOTIFS[c])) == 1 for c in silent), "a silent letter varies"

    emitting = sorted(c for c, p in WIRE_PERIODS.items() if p > 1)
    assert emitting == sorted(["ج", "خ", "ذ", "ز", "غ", "ف"])
    assert all(tone_hz(c) > 0.0 for c in emitting)


def test_the_alphabet_is_two_tones() -> None:
    nine_mhz = sorted(c for c in WIRE_PERIODS if WIRE_PERIODS[c] == 3)
    longest = sorted(c for c in WIRE_PERIODS if WIRE_PERIODS[c] == 31)

    assert nine_mhz == sorted(["ذ", "ز", "غ", "ف"])
    assert longest == sorted(["ج", "خ"])
    for char in nine_mhz:
        assert tone_hz(char) == pytest.approx(9_000_000.0)
    for char in longest:
        assert tone_hz(char) == pytest.approx(870_967.7, abs=0.1)
        assert tone_hz(char) == BOARD_CLOCK_HZ / 31
    assert tone_hz(longest[0]) < tone_hz(nine_mhz[0]), "period 31 is the lowest tone"


def test_a_cycling_matrix_can_still_emit_a_constant() -> None:
    """`ba` is the clearest case, and the reason wire period exists at all."""
    assert MATRIX_ORDERS["ب"] == 4
    assert emitted_cycle("ب") == (0,)
    assert WIRE_PERIODS["ب"] == 1 and tone_hz("ب") == 0.0
    assert matrix_period("ب") == 4, "matrix_period stopped reporting the matrix"


def test_phase_separates_what_frequency_cannot() -> None:
    """Four letters share 9 MHz; the motif tells one of them apart.

    `110` and `101` are the same tone one shift along, so a receiver that
    measured only frequency would return all four. The motif carries phase.
    """
    at_nine = {c: MOTIFS[c] for c in MOTIFS if WIRE_PERIODS[c] == 3}
    assert set(at_nine.values()) == {(1, 1, 0), (1, 0, 1)}
    assert at_nine["غ"] == (1, 0, 1)
    assert all(at_nine[c] == (1, 1, 0) for c in ("ذ", "ز", "ف"))
    assert sorted(at_nine["غ"]) == sorted(at_nine["ذ"]), "not a shift of one another"


def test_what_the_receiver_can_and_cannot_resolve() -> None:
    """Every figure recomputed. The ceiling is the point of the test.

    A run reaching 28 classes would mean the wave had started carrying the
    point, line and curve counts, which no phase or frequency does.
    """
    n = len(ENTRIES)

    def stat(key):
        groups = collections.defaultdict(list)
        for entry in ENTRIES:
            groups[key(entry.char)].append(entry.char)
        sizes = [len(v) for v in groups.values()]
        return (len(groups),
                -sum(s / n * math.log2(s / n) for s in sizes),
                sum(1 for s in sizes if s == 1))

    def rung(c):
        return next(r for r, v in RUNGS.items() if c in v)

    assert stat(rung) == (8, pytest.approx(2.77, abs=0.01), 2)
    assert stat(lambda c: WIRE_PERIODS[c]) == (3, pytest.approx(0.95, abs=0.01), 0)
    assert stat(lambda c: MOTIFS[c]) == (6, pytest.approx(1.84, abs=0.01), 3)
    assert stat(lambda c: (rung(c), WIRE_PERIODS[c])) == (
        12, pytest.approx(3.33, abs=0.01), 5)

    both = stat(lambda c: (rung(c), WIRE_PERIODS[c], MOTIFS[c]))
    assert both == (13, pytest.approx(3.40, abs=0.01), 7)
    assert len(SIGNATURES) == 13
    assert both[1] < math.log2(n), "the wave started naming letters outright"


def test_the_matrix_figure_is_better_and_unusable() -> None:
    """Kept so the tempting number cannot quietly come back.

    Matrix order gives 16 classes and 3.82 bits -- strictly better than the
    3.40 the wire gives, and describing a measurement no receiver can make.
    """
    n = len(ENTRIES)
    def rung(c):
        return next(r for r, v in RUNGS.items() if c in v)
    groups = collections.defaultdict(list)
    for entry in ENTRIES:
        groups[(rung(entry.char), MATRIX_ORDERS[entry.char])].append(entry.char)
    sizes = [len(v) for v in groups.values()]
    entropy = -sum(s / n * math.log2(s / n) for s in sizes)

    assert len(groups) == 16
    assert entropy == pytest.approx(3.82, abs=0.01)
    assert entropy > 3.40, "the matrix figure stopped being the flattering one"


def test_narrowing_never_guesses_and_rejects_cleanly() -> None:
    assert narrow(3) == RUNGS[3] and len(narrow(3)) == 6
    assert narrow(3, 3) == ("غ",)
    assert narrow(3, 3, (1, 0, 1)) == ("غ",)
    assert narrow(3, 3, (1, 1, 0)) == (), "a motif that is not there returned a letter"
    assert narrow(7, 1) == () and narrow(7) == ()


def test_every_letter_is_reachable_through_its_own_signature() -> None:
    for entry in ENTRIES:
        rung = entry.vector[0]
        found = narrow(rung, WIRE_PERIODS[entry.char], MOTIFS[entry.char])
        assert entry.char in found, entry.char
        assert set(found) <= set(RUNGS[rung]), "narrowing added a letter"


def test_an_unsealed_letter_has_no_motif() -> None:
    with pytest.raises(KeyError):
        emitted_cycle("ء")


# ══════════════════════════════════════════════════════════════════
#  Nothing measured is not the same as measured zero
# ══════════════════════════════════════════════════════════════════

def test_no_signal_and_a_constant_signal_are_told_apart() -> None:
    """Absence gets its own value, because zero already means something.

    The same defect class as `OP_NOP = 8'h00`: erased instruction memory and
    memory full of NOPs are identical bits, which is why every bitstream this
    project built shipped with an empty program and no simulation could see
    it. A frequency of 0.0 for "nothing arrived" would repeat it here.
    """
    empty = RangeReceiver(sample_rate=1000.0)
    assert empty.frequency_hz() is None, "silence reported as a measurement"

    one = RangeReceiver(sample_rate=1000.0)
    one.feed(0.0)
    assert one.frequency_hz() is None, "one sample is not a frequency"

    constant = RangeReceiver(sample_rate=1000.0)
    constant.receive([90.0] * 8)
    assert constant.frequency_hz() == 0.0, "a held phase is a measured zero"
    assert constant.frequency_hz() is not None


def test_a_reset_receiver_reports_absence_again() -> None:
    rx = RangeReceiver(sample_rate=1000.0)
    rx.receive(phase_ramp(hz=10.0, sample_rate=1000.0, samples=50))
    assert rx.frequency_hz() == pytest.approx(10.0, abs=1e-6)
    rx.reset()
    assert rx.frequency_hz() is None and rx.sequence == () and not rx.locked
