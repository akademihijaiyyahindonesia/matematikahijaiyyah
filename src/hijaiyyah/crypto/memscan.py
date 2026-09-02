# -*- coding: utf-8 -*-
"""Memory and RAM scanning — find injected regions, and recover them.

**What this does and what Volatility does are different jobs**, and confusing
them would make this module worse than useless. Volatility walks the operating
system's own structures — the VAD tree, the process list, the PEB — and can
therefore say *which process* was injected and *what permissions* the region
carries. This module parses none of that and cannot make those statements.

What it reads is the bytes. It finds regions whose **structure** is wrong for
where they sit, and where a region is obfuscated it **recovers the payload**.
That is a narrower claim and a real one: staging an XOR-obfuscated blob in
memory before decoding it in place is what a large share of commodity malware
actually does, and the key falls out of counting rather than searching.

**The four signals, and what each is worth.**

*PE in anonymous memory* — an ``MZ`` header with a valid ``e_lfanew`` pointing
at ``PE\\0\\0``. A mapped executable has one too, so this is only interesting
where the surrounding bytes say it should not be. Strong when it sits inside
high-entropy filler; weak on its own.

*XOR-staged payload* — a region whose per-bit-position bias survives, so a key
can be recovered and the plaintext restored **byte for byte**. This is the one
that produces evidence rather than suspicion: the recovered content either
parses as something or it does not.

*NOP sled* — a long run of 0x90. Cheap, classic, and easily avoided by anyone
who cares; kept because it costs nothing and still appears in real samples.

*High-entropy run* — packed or encrypted content. On its own it means nothing:
:mod:`hijaiyyah.crypto.node_counter` measures compressed and encrypted data as
indistinguishable, and base64 defeats the classifier entirely. It is a place to
look, never a finding.

**What it cannot do.** It cannot attribute a region to a process, read page
permissions, or recover anything encrypted with a real cipher — 0% against
AES-class output, measured, against 0.4% for blind guessing. A ransomware-
encrypted page is not recoverable here or anywhere without the key.

**Findings are sealed.** Forensic output that can be rewritten on the way to
whoever acts on it is worth nothing, so a report carries layer 3's
HMAC-SHA256 bound to the dataset seal. That is the part neither Volatility nor
Autopsy does.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from hijaiyyah.crypto.node_counter import (
    HIGH_ENTROPY,
    WINDOW,
    classify_window,
    recover_repeating_key,
    scan,
)

#: Shortest run of 0x90 worth reporting. Below this, ordinary data trips it.
NOP_SLED_MIN = 32

#: Shortest high-entropy run worth reporting, in windows.
ENTROPY_RUN_MIN = 4

#: Bytes of a region to attempt key recovery over. Below ~256 the recovery
#: rate falls off sharply: 66.8% at 64 bytes against 95.0% at 1024.
RECOVER_MIN = 256


@dataclass(frozen=True)
class Region:
    """One candidate, with the evidence that produced it."""

    offset: int
    length: int
    kind: str
    evidence: str
    confidence: str                      # "strong" | "weak"
    key: Optional[bytes] = None          # recovered, when there was one

    def as_row(self) -> Dict[str, object]:
        return {
            "offset": self.offset,
            "length": self.length,
            "kind": self.kind,
            "confidence": self.confidence,
            "key": self.key.hex() if self.key else "",
            "evidence": self.evidence,
        }


#: Word-level markers that name what a decoded region *is*. A statistical
#: score says "this reads like text"; a clue says "this is a PE file". The
#: difference decided three findings in the first real scan: two windows
#: straddling the payload edge scored above the text threshold by luck, and a
#: third recovered a one-byte key over pure noise. None of them carries a clue,
#: and none of them survives this.
CLUES: Tuple[Tuple[bytes, str], ...] = (
    (b"MZ\x90", "DOS/PE stub"),
    (b"PE\x00\x00", "PE header"),
    (b"\x7fELF", "ELF"),
    (b"PK\x03\x04", "ZIP"),
    (b"%PDF", "PDF"),
    (b"\x89PNG", "PNG"),
    (b"\x1f\x8b\x08", "gzip"),
    (b"This program cannot", "DOS stub text"),
    (b"kernel32", "Win32 import"),
    (b"LoadLibrary", "Win32 import"),
    (b"VirtualAlloc", "Win32 import"),
    (b"GetProcAddress", "Win32 import"),
    (b"HKEY_", "registry path"),
    (b"http://", "URL"),
    (b"https://", "URL"),
    (b"<?xml", "XML"),
)


def locate_clue(block: bytes) -> Optional[Tuple[int, str]]:
    """Where the marker sits, and what it names.

    The position is the point: a scan window begins where the scanner tiled
    it, not where the payload begins. Parsing forward from the window's edge
    carries whatever preceded the payload into the output — the first
    recovered file here did not start with ``MZ`` because 368 bytes of the
    surrounding page came with it.

    So the parse is inverted: find the anchor first, then derive the boundary
    from it. The same move as recovering a byte boundary rather than assuming
    one.
    """
    best: Optional[Tuple[int, str]] = None
    for marker, name in CLUES:
        at = block.find(marker)
        if at >= 0 and (best is None or at < best[0]):
            best = (at, name)
    return best


def find_clue(block: bytes) -> Optional[str]:
    """Name what a decoded region is, or return None.

    The clue sits *above* the parser: before anything tries to interpret the
    bytes, this says whether they are worth interpreting. A region that
    decodes to something statistically text-like but carries no marker is
    arithmetic that happened to land well, not a finding.
    """
    found = locate_clue(block)
    return found[1] if found else None


def canonical(key: bytes) -> bytes:
    """The lexicographically smallest rotation of a key.

    Recovery pins a repeating key only up to a cyclic shift, so two windows
    over one payload return the same key at different phases. Comparing them
    directly makes one finding look like several.
    """
    if not key:
        return key
    return min(key[i:] + key[:i] for i in range(len(key)))


# ── signals ──────────────────────────────────────────────────────

def find_pe_headers(data: bytes) -> List[Region]:
    """``MZ`` followed by a valid ``e_lfanew`` pointing at ``PE\\0\\0``.

    The two-step check matters. Bare ``MZ`` occurs about once every 65,536
    random bytes and would bury the report; requiring the offset at 0x3C to
    land on ``PE\\0\\0`` makes a false positive about 2^-48.
    """
    found: List[Region] = []
    start = 0
    while True:
        at = data.find(b"MZ", start)
        if at < 0:
            break
        start = at + 2
        if at + 0x40 > len(data):
            continue
        lfanew = int.from_bytes(data[at + 0x3C : at + 0x40], "little")
        target = at + lfanew
        if 0 < lfanew < 0x1000 and target + 4 <= len(data):
            if data[target : target + 4] == b"PE\x00\x00":
                found.append(Region(
                    at, 0x40 + lfanew, "PE_HEADER",
                    f"MZ at {at:#x}, e_lfanew {lfanew:#x} lands on PE\\0\\0",
                    "strong"))
    return found


def find_nop_sleds(data: bytes, minimum: int = NOP_SLED_MIN) -> List[Region]:
    """Runs of 0x90 at least ``minimum`` bytes long."""
    found: List[Region] = []
    run = 0
    for index, byte in enumerate(data + b"\x00"):
        if byte == 0x90:
            run += 1
            continue
        if run >= minimum:
            found.append(Region(
                index - run, run, "NOP_SLED",
                f"{run} consecutive 0x90", "weak"))
        run = 0
    return found


def find_entropy_runs(data: bytes, minimum: int = ENTROPY_RUN_MIN) -> List[Region]:
    """Contiguous runs of high-entropy windows.

    Reported as *weak* on purpose. Compressed and encrypted data are the same
    object to the classifier, so this cannot separate a packed payload from a
    zip file, and it says so rather than implying otherwise.
    """
    verdicts = scan(data)
    found: List[Region] = []
    start = None
    for index, verdict in enumerate([*verdicts, None]):
        if verdict == HIGH_ENTROPY:
            if start is None:
                start = index
        elif start is not None:
            span = index - start
            if span >= minimum:
                found.append(Region(
                    start * WINDOW, span * WINDOW, "HIGH_ENTROPY",
                    f"{span} consecutive high-entropy windows", "weak"))
            start = None
    return found


def find_xor_staged(data: bytes, chunk: int = 2048, step: int = 512) -> List[Region]:
    """Regions that are obfuscated *and* decode to plaintext.

    **The first version of this fired on almost everything**, including plain
    ASCII filler and pages of zeroes, and the recovery then picked the wrong
    region entirely. Its filter was "the decoded bytes are not random", which
    plain text already satisfies before any decoding — so it accepted every
    region that was not high-entropy. A filter that passes the null case is
    not a filter.

    Three conditions now, and the region has to meet all of them:

    * the region does **not** already read as text — if it did, nothing is
      hidden in it and there is nothing to recover;
    * the recovered key is not :data:`~hijaiyyah.crypto.node_counter.MODEL_MASK`
      alone, which is what the recovery returns when it found no bias at all;
    * decoding with that key turns the region **into** text.

    "Obfuscated, and decodes to plaintext" is the actual signal. Windows slide
    by ``step`` rather than tiling at ``chunk``, because a payload does not
    arrive aligned to a scanner's block size — the injection this was first
    tested against sat at offset 16,240 and every fixed 4,096-byte chunk
    straddled it.
    """
    from hijaiyyah.crypto.node_counter import MODEL_MASK, TEXT

    def text_score(block: bytes, key: bytes) -> float:
        """Fraction of windows that read as text once decoded with this key."""
        decoded = bytes(b ^ key[i % len(key)] for i, b in enumerate(block))
        windows = [decoded[i:i + WINDOW]
                   for i in range(0, len(decoded) - WINDOW + 1, WINDOW)]
        if not windows:
            return 0.0
        return sum(classify_window(w) == TEXT for w in windows) / len(windows)

    def best_rotation(block: bytes, key: bytes) -> Tuple[bytes, float]:
        """Pick the key rotation that actually aligns with this block.

        Recovery identifies a repeating key only **up to a cyclic shift** —
        the residue classes cannot be numbered without an absolute start, and
        a scan window does not begin where the payload does. The first version
        ignored this and matched 47 bytes of 2,048: the key was right and its
        phase was wrong. There are at most `len(key)` rotations, so trying
        them all and keeping the most text-like costs nothing.
        """
        best = (key, text_score(block, key))
        for shift in range(1, len(key)):
            rotated = key[shift:] + key[:shift]
            score = text_score(block, rotated)
            if score > best[1]:
                best = (rotated, score)
        return best

    hits: List[Tuple[int, int, bytes]] = []
    for start in range(0, max(1, len(data) - chunk + 1), step):
        block = data[start : start + chunk]
        if len(block) < RECOVER_MIN:
            break
        if classify_window(block[:WINDOW]) == TEXT:
            continue                              # already plain; nothing hidden
        key = recover_repeating_key(block)
        if not key or key == bytes([MODEL_MASK]):
            continue                              # no bias was found
        key, score = best_rotation(block, key)
        if score < 0.7:
            continue          # partly text is a window straddling the payload
        decoded = bytes(b ^ key[i % len(key)] for i, b in enumerate(block))
        if find_clue(decoded) is None:
            continue          # reads like text, but is not anything
        hits.append((start, len(block), key))

    # Merge overlapping hits, keyed on the CANONICAL rotation. Two windows
    # over one payload recover the same key at different phases, so comparing
    # the keys directly leaves them looking like separate findings -- which is
    # exactly what happened: one 2,490-byte injection reported as five regions
    # with five different-looking keys, three of them correct.
    merged: List[Region] = []
    for start, length, key in hits:
        canon = canonical(key)
        if merged and canonical(merged[-1].key or b"") == canon \
                and start <= merged[-1].offset + merged[-1].length:
            prev = merged[-1]
            merged[-1] = Region(
                prev.offset, max(prev.length, start + length - prev.offset),
                prev.kind, prev.evidence, prev.confidence, prev.key)
        else:
            merged.append(Region(
                start, length, "XOR_STAGED",
                f"period {len(key)}, obfuscated region decodes to text",
                "strong", key))

    # The merged span is longer than any window that built it, so its phase is
    # re-derived over the whole thing rather than inherited from the first.
    out: List[Region] = []
    for r in merged:
        block = data[r.offset : r.offset + r.length]
        key = best_rotation(block, r.key or b"")[0]
        decoded = bytes(b ^ key[i % len(key)] for i, b in enumerate(block))
        found = locate_clue(decoded)
        if found is None:
            continue

        # Trim to the anchor, then re-derive the phase for the trimmed span:
        # cutting the front by a number of bytes that is not a multiple of the
        # period rotates the key, and reporting the untrimmed one would be
        # right about the payload and wrong about how to decode it.
        at, clue = found
        offset, length = r.offset + at, r.length - at
        if length < RECOVER_MIN:
            continue
        trimmed = data[offset : offset + length]
        key = best_rotation(trimmed, key)[0]
        out.append(Region(
            offset, length, "XOR_STAGED",
            f"period {len(key)}, starts at {clue}", "strong", key))
    return out


# ── the scan, and the recovery ───────────────────────────────────

def scan_memory(data: bytes) -> List[Region]:
    """Every signal, sorted by offset."""
    regions = (find_pe_headers(data) + find_xor_staged(data)
               + find_nop_sleds(data) + find_entropy_runs(data))
    return sorted(regions, key=lambda r: (r.offset, r.kind))


def recover(data: bytes, region: Region) -> bytes:
    """The injected content, deobfuscated where a key was recovered.

    This is the field that matters. A region reported without its content is
    a suspicion; a region whose payload is restored byte for byte is evidence.
    """
    block = data[region.offset : region.offset + region.length]
    if region.key:
        return bytes(b ^ region.key[i % len(region.key)] for i, b in enumerate(block))
    return block


@dataclass(frozen=True)
class MemoryReport:
    """What the scan found, before anything authenticates it."""

    source_length: int
    regions: Tuple[Region, ...] = field(default_factory=tuple)

    def to_bytes(self) -> bytes:
        """Canonical: fixed-width integers, one reading per report."""
        out = bytearray(b"HMS1")
        out += self.source_length.to_bytes(8, "big")
        out += len(self.regions).to_bytes(4, "big")
        for r in self.regions:
            kind = r.kind.encode("ascii")[:16].ljust(16, b"\x00")
            key = (r.key or b"")[:16].ljust(16, b"\x00")
            out += (r.offset.to_bytes(8, "big") + r.length.to_bytes(8, "big")
                    + kind + bytes([len(r.key or b"")]) + key
                    + bytes([1 if r.confidence == "strong" else 0]))
        return bytes(out)

    def summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in self.regions:
            counts[r.kind] = counts.get(r.kind, 0) + 1
        return counts


def report(data: bytes) -> MemoryReport:
    return MemoryReport(len(data), tuple(scan_memory(data)))


# ── exports, in the shapes the two tools consume ─────────────────

def to_autopsy_csv(regions: Sequence[Region]) -> str:
    """One row per region, the shape Autopsy's CSV ingest expects.

    Written against the documented format. **Not tested against Autopsy** —
    it is not installed here, and claiming a verified integration on that
    basis would be exactly the kind of assertion this project refuses.
    """
    header = "offset,length,kind,confidence,key,evidence"
    rows = [header]
    for r in regions:
        rows.append(
            f'{r.offset},{r.length},{r.kind},{r.confidence},'
            f'{r.key.hex() if r.key else ""},"{r.evidence}"')
    return "\n".join(rows) + "\n"


def to_volatility_rows(regions: Sequence[Region]) -> List[Tuple]:
    """Rows for a Volatility 3 ``TreeGrid``, in its column order.

    Same caveat: written to the documented interface, **not run inside
    Volatility**, which is not installed here.
    """
    return [(r.offset, r.length, r.kind, r.confidence,
             r.key.hex() if r.key else "", r.evidence) for r in regions]
