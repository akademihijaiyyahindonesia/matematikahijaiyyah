"""The raw capture path and the offline parser, held to what P1 asks of them.

The owner's step P1, 24 September 2026: the bytes from the wire are the
primary evidence, and the parser reads them afterwards. So the parser is the
thing that can be tested without a board, and it is tested by breaking the
wire rather than by feeding it clean lines: merged, truncated, garbled,
missing a field, one field too many, a line with no newline yet, and a line
that simply says "error".

One rule outranks the rest and has a test of its own: a parse error is never a
board error. Tier 2's log carries two `error` rows that the board never
raised, because a lost newline let `0H` be dropped and the six numbers after
it be read with their fields shifted. Those exact bytes are replayed here
against both parsers -- the one that wrote the rows, and this one.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "rtl" / "scripts"))

import burn_in_capture  # noqa: E402
from burn_in import FIELDS, Feed, Run  # noqa: E402
from burn_in_parse import _Times, load_capture, parse  # noqa: E402

FIRST_CYCLE = b"28\n3072\n178\n18502\n17713\n1\n1\n"


def beat(n: int, errors: int = 0, sd_fails: int = 0, wraps: int = 0,
         counter_hi: int = 0, sd_status: int = 0) -> bytes:
    """One heartbeat as burn_in.hasm prints it: the marker, then six numbers."""
    values = (n, errors, sd_fails, wraps, counter_hi, sd_status)
    assert len(values) == len(FIELDS)
    return b"H\n" + b"".join(b"%d\n" % v for v in values)


def clean(beats: int = 5) -> bytes:
    return FIRST_CYCLE + b"".join(beat(n, counter_hi=n * 4) for n in range(1, beats + 1))


def test_a_clean_capture_parses_whole_and_says_nothing_is_wrong() -> None:
    parsed = parse(clean(5))
    assert [b["heartbeats"] for b in parsed.beats] == [1, 2, 3, 4, 5]
    assert parsed.errors == []
    assert parsed.board_errors == 0 and parsed.board_error_growth == []
    assert parsed.first_cycle is not None
    assert parsed.first_cycle["pulse_sum"] == 28
    assert parsed.first_cycle["card_word"] == 18502 << 16 | 17713
    assert set(parsed.beats[0]) == {*FIELDS, "cycles", "board_uptime_s", "offset", "utc"}


def test_the_board_counter_is_read_only_from_beats_that_parsed_whole() -> None:
    """A run where the board really did raise its counter: the growth is
    reported, and it comes from the field of a beat, not from a line of text."""
    raw = FIRST_CYCLE + beat(1) + beat(2, errors=1) + beat(3, errors=1)
    parsed = parse(raw)
    assert parsed.board_errors == 1
    assert [b["heartbeats"] for b in parsed.board_error_growth] == [2]
    assert parsed.errors == []


#: What the owner listed for P1, each as bytes on the wire and the reason it
#: must be refused. Every one of them is a sabotage of the parser: if any
#: passes, a corrupt line has become a record.
BROKEN = [
    ("merged line, the tier 2 shape", FIRST_CYCLE + beat(1) + b"0H\n" + b"2\n0\n0\n0\n8\n0\n",
     "merged_record"),
    ("two markers run together", FIRST_CYCLE + beat(1) + b"HH\n" + beat(2), "merged_record"),
    ("a number with the next marker stuck to it",
     FIRST_CYCLE + beat(1) + b"12H34\n" + beat(2), "merged_record"),
    ("truncated record, five fields", FIRST_CYCLE + b"H\n1\n0\n0\n0\n5\n" + beat(2),
     "truncated_record"),
    ("a beat with no fields at all", FIRST_CYCLE + b"H\n" + beat(2), "truncated_record"),
    ("garbled field, PRINT above 2^22", FIRST_CYCLE + b"H\n335544;<\n0\n0\n0\n5\n0\n",
     "non_numeric_field"),
    ("a hexadecimal-looking field", FIRST_CYCLE + b"H\n1A2B\n0\n0\n0\n5\n0\n",
     "non_numeric_field"),
    ("a line that says error", FIRST_CYCLE + beat(1) + b"error\n" + beat(2),
     "non_numeric_field"),
    ("a line that says ERROR 5", FIRST_CYCLE + beat(1) + b"ERROR 5\n" + beat(2),
     "non_numeric_field"),
    ("one field too many", FIRST_CYCLE + b"H\n1\n0\n0\n0\n5\n0\n7\n" + beat(2),
     "unexpected_field_count"),
    ("a field wider than 32 bits", FIRST_CYCLE + b"H\n4294967296\n0\n0\n0\n5\n0\n",
     "field_out_of_range"),
    ("a partial line at the end", FIRST_CYCLE + beat(1) + b"H\n2\n0\n0", "partial_line"),
    ("six numbers before the first marker", b"28\n3072\n178\n18502\n17713\n1\nH\n" + beat(1),
     "unexpected_field_count"),
]


@pytest.mark.parametrize("name, raw, reason", BROKEN, ids=[b[0] for b in BROKEN])
def test_a_broken_line_is_a_parse_error_and_never_a_board_error(
        name: str, raw: bytes, reason: str) -> None:
    parsed = parse(raw)
    assert reason in parsed.reasons, (name, parsed.reasons)
    assert parsed.board_errors == 0, (name, parsed.board_errors)
    assert parsed.board_error_growth == [], name
    assert all(b["errors"] == 0 for b in parsed.beats), name


@pytest.mark.parametrize("name, raw, reason", BROKEN, ids=[b[0] for b in BROKEN])
def test_no_beat_is_built_across_a_refused_line(name: str, raw: bytes,
                                                reason: str) -> None:
    """The fields pending when a line is refused are dropped, so the numbers
    after it cannot complete that beat. Every beat that survives must be one
    the wire really sent whole -- checked by finding its six fields, in order,
    inside the bytes between its marker and the next."""
    parsed = parse(raw)
    for item in parsed.beats:
        fields = b"".join(b"%d\n" % item[f] for f in FIELDS)
        assert raw[item["offset"]:].startswith(b"H\n" + fields), (name, item)


def test_the_tier_two_bytes_that_made_two_false_errors_are_refused_now() -> None:
    """The regression P1 exists for, replayed against both parsers.

    The shape is tier 2's own, and the numbers are the ones its log carries.
    A beat opens and gives its first field, 7,194; the newline before the next
    marker is gone, so `0H` arrives as one line and the marker with it; the
    fields that follow belong to a later beat, 7,440 among them. The old Feed
    drops the merged line but keeps what was pending, so those fields complete
    the open beat one place out -- `errors` holding the beat number 7,440 --
    and it writes the error row that is in the log. This parser refuses the
    merged line, drops what was pending, and the board's count stays 0.
    """
    # The beats alone, without the first cycle: the old Feed is given
    # `beating=True` here, and fed the first cycle's seven numbers it would
    # read six of them as a beat -- a defect of its own, already recorded in
    # its docstring, and not the one under test.
    raw = b"H\n7194\n" + b"0H\n" + b"7440\n0\n0\n73\n645351\n" + beat(7195)

    log = ROOT / "cosmictera-build" / "burn-in"          # not written to
    assert log.is_dir()
    import tempfile
    from datetime import datetime, timezone
    with tempfile.TemporaryDirectory() as tmp:
        run = Run(Path(tmp) / "old.jsonl", datetime.now(timezone.utc))
        feed = Feed(run, {}, gap_threshold=1e9, beating=True)
        feed.take(raw)
        run.log.close()
        old = [json.loads(ln) for ln in (Path(tmp) / "old.jsonl").read_text().splitlines()]
    bad, = [r for r in old if r["kind"] == "error"]
    assert (bad["heartbeats"], bad["errors"]) == (7194, 7440), bad
    # run.errors is not asserted: it holds the LAST beat's count, and the beat
    # after this one reports 0. What the old parser did is in the row it wrote.

    parsed = parse(raw)
    assert parsed.board_errors == 0
    assert parsed.reasons == {"merged_record": 1, "unexpected_field_count": 5}
    assert [b["heartbeats"] for b in parsed.beats] == [7195]


def test_a_stray_group_after_a_refusal_cannot_become_a_first_cycle() -> None:
    """My own hole, found before the board was asked: seven stray numbers
    after a refused line must not be read as the first cycle, which is the
    one group that is counted rather than marked."""
    raw = clean(1) + b"0H\n" + b"28\n3072\n178\n18502\n17713\n1\n1\n" + beat(2)
    parsed = parse(raw)
    assert parsed.first_cycle is not None
    assert parsed.first_cycle["offset"] == len(FIRST_CYCLE)
    assert parsed.reasons["unexpected_field_count"] == 7
    assert [b["heartbeats"] for b in parsed.beats] == [1, 2]


def test_arrival_times_come_from_the_sidecar_and_are_the_hosts() -> None:
    raw = clean(2)
    times = _Times([{"offset": 0, "utc": "2026-09-24T10:00:00+00:00", "n": 40},
                    {"offset": 40, "utc": "2026-09-24T10:00:02+00:00", "n": 200}])
    parsed = parse(raw, times)
    # The first beat's marker sits at byte 28, inside the first read; the
    # second is past byte 40, so it carries the later arrival.
    assert parsed.beats[0]["offset"] == len(FIRST_CYCLE)
    assert parsed.beats[0]["utc"] == "2026-09-24T10:00:00+00:00"
    assert parsed.beats[1]["utc"] == "2026-09-24T10:00:02+00:00"


# -- the capture tool ----------------------------------------------------------------


def test_the_capture_tool_does_not_parse() -> None:
    """P1's separation, held in the source: the capture path knows nothing of
    heartbeats, fields or errors. If it learned to parse, the raw file would
    stop being the evidence and become a second opinion."""
    text = (ROOT / "rtl" / "scripts" / "burn_in_capture.py").read_text(encoding="utf-8")
    body = text.split('"""', 2)[2]
    for word in ("FIELDS", "FIRST", "heartbeat", "isdigit", "errors"):
        assert word not in body, word
    assert "import burn_in" not in body and "from burn_in import" in text


def test_burn_in_itself_is_not_the_capture_tool() -> None:
    """The owner's instruction, 24 September 2026: burn_in.py is not turned
    into the capture tool, so every record it has written keeps its meaning."""
    text = (ROOT / "rtl" / "scripts" / "burn_in.py").read_text(encoding="utf-8")
    for word in ("-capture", "raw_sha256", "def capture", "capture_version"):
        assert word not in text, word


def test_the_manifest_records_what_p1_asks_for(tmp_path: Path,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    """Start and end, the device, the bitstream's fingerprint computed from the
    file, the byte count, and the SHA256 of the raw bytes."""
    from datetime import datetime, timezone

    bitstream = tmp_path / "loader.fs"
    bitstream.write_bytes(b"not a real bitstream")
    sink = burn_in_capture.Capture(tmp_path / "x.raw", tmp_path / "x.times.jsonl")
    sink.take(b"H\n1\n", 1_758_000_000.0)
    sink.close()
    started = datetime(2026, 9, 24, 10, 0, tzinfo=timezone.utc)
    ended = datetime(2026, 9, 24, 10, 12, tzinfo=timezone.utc)
    record = burn_in_capture.manifest("20260924T100000Z-capture", started, ended,
                                      "duration reached", "/dev/null", bitstream,
                                      sink, 12.0)
    assert record["bitstream_sha256"] == hashlib.sha256(b"not a real bitstream").hexdigest()
    assert record["raw_sha256"] == hashlib.sha256(b"H\n1\n").hexdigest()
    assert record["bytes"] == 4 and record["reads"] == 1
    assert record["started"] == started.isoformat()
    assert record["ended_utc"] == ended.isoformat()
    assert record["seconds_captured"] == 720.0
    assert record["device"]["port"] == "/dev/null"
    assert record["ended"] == "duration reached"


class _Port:
    """One row of pyserial's port listing, as a Mac lists the board's adapter."""

    def __init__(self, device: str) -> None:
        self.device = device
        self.serial_number = "2025030317"
        self.hwid = "USB VID:PID=0403:6010 SER=2025030317 LOCATION=0-1"
        self.manufacturer = "SIPEED"
        self.product = "USB Debugger"


def test_the_dial_in_node_finds_its_adapter_in_a_call_out_listing(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A Mac lists only /dev/cu.X; a capture given /dev/tty.X of the same
    device must still record the adapter. Matched by path alone it wrote "not
    in this host's listing" with the adapter attached (08f1e36)."""
    list_ports = pytest.importorskip("serial.tools.list_ports")
    monkeypatch.setattr(list_ports, "comports", lambda: [_Port("/dev/cu.usbserial-X")])
    found = burn_in_capture.device_identity("/dev/tty.usbserial-X")
    assert found["serial_number"] == "2025030317"
    assert found["vid_pid"].startswith("USB VID:PID=0403:6010")
    assert "note" not in found


def test_a_linux_tty_is_not_taken_for_a_mac_call_out_node(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Linux has no `tty.` prefix: /dev/ttyUSB0 is not /dev/cu.USB0, and the
    listing must not lend it an identity."""
    list_ports = pytest.importorskip("serial.tools.list_ports")
    monkeypatch.setattr(list_ports, "comports", lambda: [_Port("/dev/cu.USB0")])
    assert not burn_in_capture._same_device("/dev/ttyUSB0", "/dev/cu.USB0")
    found = burn_in_capture.device_identity("/dev/ttyUSB0")
    assert found["note"] == "the port is not in this host's listing"
    assert "serial_number" not in found


def test_a_capture_whose_bytes_changed_is_refused(tmp_path: Path) -> None:
    """R3 on the evidence itself: the manifest's SHA256 is checked before the
    bytes are read as anything, so a raw file edited afterwards cannot be
    parsed into a clean report."""
    raw = tmp_path / "r-capture.raw"
    raw.write_bytes(clean(2))
    (tmp_path / "r-capture.times.jsonl").write_text("", encoding="utf-8")
    manifest = tmp_path / "r-capture.json"
    manifest.write_text(json.dumps({
        "raw": "r-capture.raw", "times": "r-capture.times.jsonl",
        "raw_sha256": hashlib.sha256(clean(2)).hexdigest()}), encoding="utf-8")
    assert load_capture(manifest)[0] == clean(2)

    raw.write_bytes(clean(3))
    with pytest.raises(SystemExit, match="is not the"):
        load_capture(manifest)
