"""
Memory scanning: find an injected region, and recover it byte for byte.

Built against a synthetic dump with artefacts planted at known offsets,
because a scanner tested only on real samples cannot tell a hit from a
coincidence — there is nothing to compare against.

Three versions of the XOR detector failed before this one, and each failure is
recorded here because each was a different way of being wrong.
"""

from __future__ import annotations

import os

from hijaiyyah.crypto.memscan import (
    CLUES,
    canonical,
    find_clue,
    find_nop_sleds,
    find_pe_headers,
    find_xor_staged,
    recover,
    report,
    scan_memory,
    to_autopsy_csv,
    to_volatility_rows,
)

KEY = b"\x9c\x41\x07\x22\xd5"


def _payload() -> bytes:
    """A PE-shaped blob: MZ, a valid e_lfanew, the DOS stub, and imports."""
    pe = bytearray(b"MZ" + b"\x90" * 0x3A)
    pe += (0x40).to_bytes(4, "little") + b"PE\x00\x00" + b"\x64\x86"
    pe += b"This program cannot be run in DOS mode.\r\n" * 40
    pe += b"kernel32.dll\x00VirtualAlloc\x00LoadLibraryA\x00" * 20
    return bytes(pe)


def _dump():
    """A dump with one XOR-staged injection at a known offset."""
    data = bytearray()
    placed = {}

    def place(name, blob):
        placed[name] = (len(data), len(blob))
        data.extend(blob)

    place("text", b"C:\\Windows\\System32\\ntdll.dll\x00" * 200)
    place("zeros", bytes(4096))
    place("packed", os.urandom(6144))
    payload = _payload()
    place("inject", bytes(b ^ KEY[i % 5] for i, b in enumerate(payload)))
    place("sled", b"\x90" * 96)
    place("text2", b"HKEY_LOCAL_MACHINE\\Software\\Microsoft\x00" * 120)
    return bytes(data), placed, payload


# ══════════════════════════════════════════════════════════════════
#  The field that matters: recovering the injected content
# ══════════════════════════════════════════════════════════════════

def test_the_injected_payload_is_recovered_byte_for_byte() -> None:
    """
    A region reported without its content is a suspicion; a region whose
    payload is restored byte for byte is evidence. This is the second.
    """
    data, placed, payload = _dump()
    offset, length = placed["inject"]

    staged = [r for r in scan_memory(data) if r.kind == "XOR_STAGED"]
    assert len(staged) == 1, f"expected one staged region, got {len(staged)}"

    region = staged[0]
    restored = recover(data, region)

    start = max(region.offset, offset)
    stop = min(region.offset + region.length, offset + length)
    got = restored[start - region.offset : stop - region.offset]
    want = payload[start - offset : stop - offset]
    assert got == want, "the recovered payload is not byte-identical"
    assert len(want) > 2000, "the overlap is too small to mean anything"


def test_the_clue_is_what_separates_a_finding_from_arithmetic() -> None:
    """
    The fix that made the scan usable, and the instruction behind it.

    A statistical score says "this reads like text". A clue says "this is a PE
    file". Before clues, two windows straddling the payload edge scored above
    the text threshold by luck and a third recovered a one-byte key over pure
    noise — three findings, none of them real. None carries a clue.
    """
    data, _, _ = _dump()
    region = next(r for r in scan_memory(data) if r.kind == "XOR_STAGED")
    assert find_clue(recover(data, region)) == "DOS/PE stub"
    assert "starts at" in region.evidence

    assert find_clue(os.urandom(4096)) is None
    assert find_clue(b"\x00" * 4096) is None


def test_a_key_is_only_recoverable_up_to_a_rotation_and_the_phase_is_searched() -> None:
    """
    Recovery pins a repeating key up to a cyclic shift, and a scan window does
    not begin where the payload does. Ignoring that matched 47 bytes of 2,048:
    the key was right and its phase was wrong. There are at most len(key)
    rotations, so all are tried and the most text-like kept.
    """
    data, _, _ = _dump()
    region = next(r for r in scan_memory(data) if r.kind == "XOR_STAGED")
    rotations = {KEY[i:] + KEY[:i] for i in range(len(KEY))}
    assert region.key in rotations
    assert canonical(region.key) == canonical(KEY)


def test_windows_over_one_payload_merge_into_one_finding() -> None:
    """
    Two windows over one payload recover the same key at different phases, so
    comparing keys directly leaves them looking like separate findings — one
    2,490-byte injection reported as five regions with five different-looking
    keys. Merging is keyed on the canonical rotation.
    """
    data, _, _ = _dump()
    staged = [r for r in scan_memory(data) if r.kind == "XOR_STAGED"]
    assert len(staged) == 1
    assert staged[0].length > 2000


# ══════════════════════════════════════════════════════════════════
#  The false positives that had to be designed out
# ══════════════════════════════════════════════════════════════════

def test_plain_text_and_zero_pages_are_not_reported_as_staged() -> None:
    """
    The first detector fired on both. Its filter was "the decoded bytes are
    not random", which plain text satisfies before any decoding — a filter
    that passes the null case is not a filter.
    """
    assert find_xor_staged(b"C:\\Windows\\System32\\ntdll.dll\x00" * 300) == []
    assert find_xor_staged(bytes(8192)) == []


def test_random_data_yields_no_staged_region() -> None:
    """Real encryption leaves no bias to count, so there is nothing to find."""
    assert find_xor_staged(os.urandom(16384)) == []


# ══════════════════════════════════════════════════════════════════
#  The cheaper signals
# ══════════════════════════════════════════════════════════════════

def test_a_pe_header_needs_a_valid_e_lfanew_not_just_MZ() -> None:
    """
    Bare `MZ` occurs about once every 65,536 random bytes and would bury the
    report. Requiring the offset at 0x3C to land on `PE\\0\\0` makes a false
    positive about 2^-48.
    """
    good = _payload()
    assert [r.offset for r in find_pe_headers(good)] == [0]
    assert find_pe_headers(b"MZ" + os.urandom(4096)) == []


def test_nop_sleds_are_found_and_short_runs_are_not() -> None:
    found = find_nop_sleds(b"\x00" * 100 + b"\x90" * 96 + b"\x00" * 100)
    assert [(r.offset, r.length) for r in found] == [(100, 96)]
    assert find_nop_sleds(b"\x90" * 8) == []


# ══════════════════════════════════════════════════════════════════
#  Reports and exports
# ══════════════════════════════════════════════════════════════════

def test_the_report_is_canonical_and_fixed_width() -> None:
    data, _, _ = _dump()
    encoded = report(data).to_bytes()
    assert encoded.startswith(b"HMS1")
    assert report(data).to_bytes() == encoded


def test_the_report_can_be_sealed_so_findings_cannot_be_rewritten() -> None:
    """
    The part neither Volatility nor Autopsy does. Forensic output that can be
    rewritten on the way to whoever acts on it is worth nothing.
    """
    import pytest

    from hijaiyyah.crypto.guarded_record import CryptoRefusal, GuardedRecord
    from hijaiyyah.crypto.kabah import Kabah

    data, _, _ = _dump()
    system = Kabah(bytes(range(32)), "forensics", track_replays=False)
    record = system.seal(report(data).to_bytes())
    assert system.open(record) == report(data).to_bytes()

    tampered = bytearray(record.to_bytes())
    tampered[-1] ^= 0x01
    with pytest.raises(CryptoRefusal):
        system.open(GuardedRecord.from_bytes(bytes(tampered)))


def test_the_exports_carry_every_region() -> None:
    """
    Written to the documented formats. Neither Volatility nor Autopsy is
    installed here, so the integration itself is untested and is labelled that
    way in the module rather than claimed.
    """
    data, _, _ = _dump()
    regions = scan_memory(data)
    csv = to_autopsy_csv(regions)
    assert csv.count("\n") == len(regions) + 1
    assert to_volatility_rows(regions)[0][0] == regions[0].offset


def test_the_module_says_what_volatility_does_that_it_cannot() -> None:
    """
    Confusing the two jobs would make this worse than useless. Volatility
    walks the OS's own structures and can name a process; this reads bytes.
    """
    from hijaiyyah.crypto import memscan

    doc = " ".join((memscan.__doc__ or "").split())
    assert "Volatility walks the operating system's own structures" in doc
    assert "cannot attribute a region to a process" in doc
    assert "not recoverable here or anywhere without the key" in doc


def test_every_clue_is_distinctive_enough_to_be_worth_having() -> None:
    """A marker that fires on random data is noise wearing a name."""
    sample = os.urandom(1 << 16)
    for marker, name in CLUES:
        assert marker not in sample, f"{name} marker {marker!r} occurs in noise"


def test_the_parse_is_inverted_so_the_region_starts_at_the_payload() -> None:
    """
    Find the anchor, then derive the boundary from it — not the reverse.

    A scan window begins where the scanner tiled it, not where the payload
    begins. Parsing forward from the window edge carried 368 bytes of the
    surrounding page into the output, so the first recovered file did not
    start with `MZ` even though the key was right. Locating the clue and
    trimming to it puts the region exactly on the injection.

    Trimming rotates the key whenever the cut is not a multiple of the period,
    so the phase is re-derived over the trimmed span. Without that the report
    would be right about where the payload is and wrong about how to read it.
    """
    data, placed, payload = _dump()
    offset, _ = placed["inject"]

    region = next(r for r in scan_memory(data) if r.kind == "XOR_STAGED")
    assert region.offset == offset, "the region should start at the injection"
    assert region.key == KEY, "trimming should have re-derived the true phase"

    restored = recover(data, region)
    assert restored.startswith(b"MZ")
    assert restored == payload[: len(restored)]
    assert "starts at" in region.evidence
