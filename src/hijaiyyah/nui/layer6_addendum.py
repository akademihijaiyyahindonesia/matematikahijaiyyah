"""Layer 6 after its freeze: the post-freeze addendum, read beside the frozen records.

    PYTHONPATH=src python3 -m hijaiyyah.nui.layer6_addendum --write
    PYTHONPATH=src python3 -m hijaiyyah.nui.layer6_addendum --verify

The owner's decision of 1 October 2026, after the HMAC commit (4bff781) left
three Layer 6 --verify checks red: the frozen registry stays immutable, and
what has changed since the freeze is a new record beside it, not a
regeneration. Each entry gives the old pointer or hash, the current state,
the concrete reason, the commit that caused it and the evidence that the
claim is unchanged; nothing is mapped in bulk. The verifiers read both:

    historical freeze  each Layer 6.1-6.3 record, with the page and the spec it
                       was built with, byte for byte the object at the tag
    current state      that record with the addendum's changes applied, which
                       must equal what the evidence builds today

The evidence of equivalence is checked, not believed. It reads the file at
the freeze, at the causing commit's parent, at the causing commit, and now:

    comment-only       every line that is not blank or a whole-line // comment is
                       the same, in order -- the rule the place-and-route
                       fingerprint hashes by
    insert-only        every line of the frozen file is still there, in order;
                       lines were only added
    line-moved         each cited line has the same text at its new number
    row-meaning        the contract row parses to the same field and origin, and
                       still has no source
    remeasured-header  place-and-route figures in the FPGA wrapper header were
                       re-measured; tied to the live RTL fingerprint, fingerprinted
                       sources, target/constraint/build config, toolchain versions,
                       and raw synthesis/PnR report hashes, keeping SIMULATED
                       (PNR/build-derived) strictly separate from MEASURED board runs
    claim-unchanged    an RTL source file changed in design, shifting only its whole-file
                       hash/size metadata while the claim's contract, identity, source,
                       line, value, status, and architectural anchors remain unchanged

For every change, too: the old value is the frozen record's and reproduces
from the file at the freeze and just before the cause, and the new value is
today's build's and reproduces from the file at the cause and now.

A CHAIN (owner, 5 October 2026; extended 2 November 2026 for Jalur A). One
file can be changed again after its entry was written -- the Ka'bah layer 3
commit added lines to the Makefile that 4bff781 had already added lines to,
and Paket 8 (f9c8349) restamped hcpu_gowin_top.v and modified hcpu_top.v after
4bff781 and 48cf0e5. A second change is not accepted because it is a second
change. It is accepted only as an entry that names, in `after`, the one entry
it continues, and every link of that is checked:

    the entry it names was written before it and is about the same file;
    that entry is continued by this one alone -- a chain does not fork;
    it changes the exact same kind of evidence and the exact pointers that
    entry changed, and each old value here is that entry's new value;
    its cause comes after that entry's cause;
    the file just before its cause hashes to its predecessor's cause -- so
    nothing touched the file between the two causes;
    and its own evidence of equivalence holds from that entry's cause on.

The entry it continues then answers for the file at its own cause only, and
the last entry of a chain for the file now. Whole-file hash entries
(comment-only, insert-only, claim-unchanged) and linear line-moved entries may
chain. A pointer changed twice with no such link is still refused.
"""
from __future__ import annotations

import copy
import functools
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from .layer6_freeze import TAG, _ancestor, _blob, _diff, _full, _git
from .repository_index import ROOT

RECORD = ROOT / "NUI" / "layer6_addendum.json"
PAGE = ROOT / "NUI" / "LAYER6_ADDENDUM.md"
HW_SPEC = "NUI/spec/hardware_inventory.json"
HP_SPEC = "NUI/spec/hardware_provenance.json"
#: Each frozen record, then the page and the spec it was built with.
FROZEN = {
    "hardware": ("NUI/hardware_inventory.json", "NUI/HARDWARE.md",
                 "NUI/spec/hardware_inventory.json"),
    "telemetry_sources": ("NUI/telemetry_sources.json", "NUI/TELEMETRY_SOURCES.md",
                          "NUI/spec/telemetry_sources.json"),
    "hardware_provenance": ("NUI/hardware_provenance.json", "NUI/HARDWARE_PROVENANCE.md",
                            "NUI/spec/hardware_provenance.json"),
}
KINDS = (
    "comment-only",
    "insert-only",
    "line-moved",
    "row-meaning",
    "remeasured-header",
    "claim-unchanged",
)
#: The kinds that speak for a whole file's hash or byte count.
WHOLE = ("comment-only", "insert-only", "claim-unchanged")
#: The kinds that may participate in a linear `after` chain.
CHAINABLE = ("comment-only", "insert-only", "line-moved", "claim-unchanged")
CONTRACT = "NUI/spec/telemetry_sources.json"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
Change = dict[str, Any]


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(RECORD.read_text(encoding="utf-8"))
    return data


def _now(path: str) -> bytes:
    """A file as the working tree holds it."""
    return (ROOT / path).read_bytes()


@functools.lru_cache(maxsize=None)
def _commit(name: str) -> str:
    return _full(name)


@functools.lru_cache(maxsize=None)
def _at(commit: str, path: str) -> bytes:
    """A file as git holds it at one commit -- an object, so read once."""
    return _blob(_commit(commit), path)


@functools.lru_cache(maxsize=None)
def _touched(commit: str) -> tuple[str, ...]:
    return tuple(_git("diff-tree", "--no-commit-id", "--name-only", "-r",
                      _commit(commit)).split())


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _lines(data: bytes) -> list[str]:
    return data.decode("utf-8").splitlines()


def _line(data: bytes, n: Any) -> str | None:
    lines = _lines(data)
    return lines[n - 1] if isinstance(n, int) and 1 <= n <= len(lines) else None


def _parts(pointer: str) -> list[str]:
    return pointer.strip("/").split("/")


def _get(data: Any, pointer: str) -> Any:
    for part in _parts(pointer):
        data = data[int(part)] if isinstance(data, list) else data[part]
    return data


def _put(data: Any, pointer: str, value: Any) -> None:
    *head, last = _parts(pointer)
    for part in head:
        data = data[int(part)] if isinstance(data, list) else data[part]
    if isinstance(data, list):
        data[int(last)] = value
    else:
        data[last] = value


def changes(name: str, addendum: dict[str, Any] | None = None) -> list[Change]:
    """The addendum's changes to one record, in the order written."""
    addendum = addendum if addendum is not None else load()
    return [c for e in addendum["entries"] for c in e["changes"] if c["record"] == name]


def current(name: str, frozen: dict[str, Any] | None = None,
            addendum: dict[str, Any] | None = None) -> dict[str, Any]:
    """The frozen record with the addendum's changes to it applied: what the
    repository holds as that record today. A change whose old value is not
    the frozen record's is refused -- the addendum amends the freeze, it does
    not stand in for it. The one exception is written into the entry: an
    entry that names the entry it comes `after` must hold, as its old value,
    what that entry left there."""
    frozen = frozen if frozen is not None else json.loads(
        (ROOT / FROZEN[name][0]).read_text(encoding="utf-8"))
    addendum = addendum if addendum is not None else load()
    out = copy.deepcopy(frozen)
    for e in addendum["entries"]:
        held, whose = (out, f"the record after {e['after']!r}") if "after" in e \
            else (frozen, "the frozen record")
        for c in e["changes"]:
            if c["record"] != name:
                continue
            try:
                was = _get(held, c["pointer"])
            except (LookupError, ValueError, TypeError):
                raise LookupError(f"{name}{c['pointer']} is not in the frozen record") from None
            if was != c["old"]:
                raise LookupError(f"{name}{c['pointer']}: {whose} holds {was!r}, "
                                  f"not {c['old']!r}")
            _put(out, c["pointer"], c["new"])
    return out


# -- the evidence of equivalence ------------------------------------------------------


def _design(data: bytes) -> list[str]:
    """The lines synthesis sees: not blank, not a whole-line // comment."""
    return [ln for ln in _lines(data) if ln.strip() and not ln.strip().startswith("//")]


Link = tuple[str | None, str | None]


def _whole(who: str, path: str, cs: list[Change], v: dict[str, bytes],
           link: Link = (None, None)) -> list[str]:
    """A whole file's hash or size, as the record wrote it before and after.
    `from` and `to` are the ends this entry answers for: the freeze and now,
    unless it continues an entry or is continued by one."""
    after, then = link
    was = f"from the cause of {after!r} until its own" if after \
        else "at the freeze and until its cause"
    now = f"at its cause, where {then!r} takes over" if then else "at its cause and now"
    bad = []
    for c in cs:
        if c["pointer"].endswith("/value") or c["pointer"].endswith("/claim"):
            continue
        size = c["pointer"].endswith("_bytes")
        if {len(b) if size else _sha(b) for b in (v["from"], v["before"])} != {c["old"]}:
            bad.append(f"{who}: {c['record']}{c['pointer']} was not {path} {was}")
        if {len(b) if size else _sha(b) for b in (v["cause"], v["to"])} != {c["new"]}:
            bad.append(f"{who}: {c['record']}{c['pointer']} is not {path} {now}")
    return bad


def _moved(c: Change, path: str, pairs: list[tuple[int, int]]) -> tuple[int, int] | None:
    """The cited line a change moves: a line number, or a claim that names
    the file and line."""
    old, new = c["old"], c["new"]
    for a, b in pairs:
        if type(old) is int and (old, new) == (a, b):
            return a, b
        if isinstance(old, str) and old.endswith(f"{path}:{a}") and isinstance(new, str) \
                and new == old[:-len(str(a))] + str(b):
            return a, b
    return None


def _row(data: bytes, n: Any) -> re.Match[str] | None:
    rule = json.loads(_now(CONTRACT).decode("utf-8"))["contract"]["row"]
    return re.search(rule, _line(data, n) or "")


def _match_in_bytes(data: bytes, pattern: str) -> tuple[int, str] | None:
    rx = re.compile(pattern)
    for n, ln in enumerate(_lines(data), 1):
        m = rx.search(ln)
        if m is not None:
            return n, (m.group(1) if m.groups() else m.group(0))
    return None


def _rtl_fingerprint(wrapper_path: str, wrapper_bytes: bytes,
                     cause: str | None = None) -> str:
    """Recompute the HCPU RTL fingerprint using test_place_and_route.py's exact rule."""
    gowin = ROOT / "rtl" / "fpga" / "gowin"
    sources = sorted((ROOT / "rtl").glob("*.v")) + sorted((ROOT / "rtl").glob("*.vh")) + [
        gowin / "hcpu_gowin_top.v",
        gowin / "hcpu_gowin.cst",
    ]
    h = hashlib.sha256()
    for f in sources:
        rel = f.relative_to(ROOT).as_posix()
        if rel == wrapper_path:
            raw = wrapper_bytes
        elif cause:
            try:
                raw = _at(cause, rel)
            except LookupError:
                raw = _now(rel)
        else:
            raw = _now(rel)
        h.update(f.name.encode("utf-8"))
        for line in raw.decode("utf-8").splitlines(keepends=True):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            h.update(line.encode("utf-8"))
    return h.hexdigest()


def _remeasured_header(who: str, e: dict[str, Any], cs: list[Change],
                       v: dict[str, bytes], link: Link = (None, None)) -> list[str]:
    """Verify a re-measured FPGA wrapper header entry against its RTL fingerprint,
    source blobs, target/build config, toolchain, and external PnR/board reports."""
    path, cause, eq = e["path"], str(e["cause"]), e["equivalence"]
    bad: list[str] = []
    req = ("rtl_fingerprint", "sources", "target", "toolchain", "reports", "items")
    missing = [k for k in req if not eq.get(k)]
    if missing:
        return [f"{who}: remeasured-header missing {', '.join(missing)}"]

    fp = str(eq["rtl_fingerprint"])
    if not HEX64.fullmatch(fp):
        bad.append(f"{who}: rtl_fingerprint {fp!r} is not a 64-hex SHA-256")

    fp_rx = re.compile(r"^// RTL FINGERPRINT: ([0-9a-f]{64})$", re.M)
    m_from = fp_rx.search(v["from"].decode("utf-8"))
    m_cause = fp_rx.search(v["cause"].decode("utf-8"))
    m_to = fp_rx.search(v["to"].decode("utf-8"))
    if m_cause is None or m_to is None or m_cause.group(1) != fp or m_to.group(1) != fp:
        bad.append(f"{who}: {path} does not record RTL FINGERPRINT {fp[:12]} at {cause} and now")
    if m_from is not None and m_from.group(1) == fp:
        bad.append(f"{who}: RTL FINGERPRINT {fp[:12]} did not change from before {cause}")
    if link[1] is None and _rtl_fingerprint(path, v["to"], cause) != fp:
        bad.append(f"{who}: recomputed RTL fingerprint does not match {fp[:12]}")

    sources = eq["sources"]
    if not isinstance(sources, dict) or path not in sources:
        bad.append(f"{who}: sources must map {path} and its RTL inputs to SHA-256 hashes")
    else:
        for spath, want_sha in sources.items():
            if not isinstance(want_sha, str) or not HEX64.fullmatch(want_sha):
                bad.append(f"{who}: source {spath} has invalid sha256 {want_sha!r}")
                continue
            try:
                blob = v["to"] if (spath == path and link[1] is None) else _at(cause, spath)
            except LookupError:
                bad.append(f"{who}: source {spath} does not exist at {cause}")
                continue
            if _sha(blob) != want_sha:
                bad.append(f"{who}: source {spath} does not hash to {want_sha[:12]} at {cause}")

    target = eq["target"]
    t_need = ("board", "device", "family", "cst_path", "cst_sha256",
              "makefile_path", "yosys_flags", "use_dsp", "codex_profile", "constraint_mhz")
    if not isinstance(target, dict) or any(k not in target for k in t_need):
        bad.append(f"{who}: target config is incomplete")
    else:
        try:
            cst_blob = (_now(target["cst_path"]) if link[1] is None
                        else _at(cause, target["cst_path"]))
            mk_text = (_now(target["makefile_path"]) if link[1] is None
                       else _at(cause, target["makefile_path"])).decode("utf-8")
        except (LookupError, OSError) as why:
            bad.append(f"{who}: target file missing: {why}")
        else:
            if _sha(cst_blob) != target["cst_sha256"]:
                bad.append(f"{who}: constraint {target['cst_path']} does not match cst_sha256")
            if not re.search(rf"^DEVICE\s*=\s*{re.escape(str(target['device']))}\b", mk_text, re.M):
                bad.append(f"{who}: Makefile DEVICE is not {target['device']!r}")
            if not re.search(rf"^FAMILY\s*=\s*{re.escape(str(target['family']))}\b", mk_text, re.M):
                bad.append(f"{who}: Makefile FAMILY is not {target['family']!r}")
            if f"YOSYS_FLAGS ?= {target['yosys_flags']}" not in mk_text:
                bad.append(f"{who}: Makefile YOSYS_FLAGS is not {target['yosys_flags']!r}")
            if f"parameter USE_DSP = {target['use_dsp']}" not in v["to"].decode("utf-8"):
                bad.append(f"{who}: {path} does not set USE_DSP = {target['use_dsp']}")

    tc = eq["toolchain"]
    tc_keys = ("yosys", "nextpnr", "gowin_pack", "command")
    if not isinstance(tc, dict) or any(not tc.get(k) for k in tc_keys):
        bad.append(f"{who}: toolchain metadata is incomplete")

    rep = eq["reports"]
    r_need = ("archive_dir", "synth_report", "synth_sha256", "pnr_report", "pnr_sha256",
              "make_bitstream_log", "make_bitstream_sha256", "bitstream_sha256",
              "bitstream_bytes", "board_record_page", "board_record_section")
    if not isinstance(rep, dict) or any(not rep.get(k) for k in r_need):
        bad.append(f"{who}: reports metadata is incomplete")
        return bad
    for hk in ("synth_sha256", "pnr_sha256", "make_bitstream_sha256", "bitstream_sha256"):
        if not isinstance(rep.get(hk), str) or not HEX64.fullmatch(rep[hk]):
            bad.append(f"{who}: {hk} is not a 64-hex SHA-256")
    if rep.get("synth_sha256") == rep.get("pnr_sha256"):
        bad.append(f"{who}: synth_sha256 and pnr_sha256 must be distinct reports")

    try:
        papan_text = (_now(rep["board_record_page"]) if link[1] is None
                      else _at(cause, rep["board_record_page"])).decode("utf-8")
    except (LookupError, OSError) as why:
        bad.append(f"{who}: board_record_page unreadable: {why}")
        papan_text = ""
    if papan_text:
        bpage = rep["board_record_page"]
        bsec = rep["board_record_section"]
        bsha = str(rep["bitstream_sha256"])
        if not re.search(str(bsec), papan_text, re.M):
            bad.append(f"{who}: {bpage} lacks section {bsec!r}")
        if bsha not in papan_text:
            bad.append(f"{who}: {bpage} does not record bitstream {bsha[:12]}")

    # The reports live outside git (K-11), at archive_dir and nowhere else. A
    # machine without them cannot check them, and says so: skipping would let
    # the figures stand on nothing.
    archive = Path(os.path.expanduser(str(rep["archive_dir"])))
    pnr_log_text: str | None = None
    if not archive.is_dir():
        bad.append(f"{who}: evidence archive {rep['archive_dir']} is not on this machine, "
                   "so its synthesis and PnR reports cannot be checked")
    else:
        for rkey, skey in (("synth_report", "synth_sha256"),
                           ("pnr_report", "pnr_sha256"),
                           ("make_bitstream_log", "make_bitstream_sha256")):
            rfile = archive / str(rep[rkey])
            if not rfile.is_file():
                bad.append(f"{who}: archived report {rep[rkey]} is missing")
            elif _sha(rfile.read_bytes()) != rep[skey]:
                bad.append(f"{who}: archived report {rep[rkey]} does not match {skey}")
            elif rkey == "pnr_report":
                pnr_log_text = rfile.read_text(encoding="utf-8", errors="replace")

    hw_spec = json.loads(_now(HW_SPEC).decode("utf-8"))
    spec_by_id = {it["id"]: it for it in hw_spec["items"]}
    spec_idx_by_id = {it["id"]: idx for idx, it in enumerate(hw_spec["items"])}
    items_cfg = eq["items"]
    if not isinstance(items_cfg, dict) or not items_cfg:
        bad.append(f"{who}: no re-measured items declared")
        return bad

    expected_changes: dict[tuple[str, str], tuple[Any, Any]] = {}
    for item_id, icfg in items_cfg.items():
        if item_id not in spec_by_id:
            bad.append(f"{who}: {item_id!r} is not in {HW_SPEC}")
            continue
        sitem = spec_by_id[item_id]
        idx = spec_idx_by_id[item_id]
        if sitem.get("class") != "SIMULATED" or sitem.get("evidence_kind") != "PNR/build-derived":
            bad.append(
                f"{who}: {item_id} must remain SIMULATED (PNR/build-derived), "
                "not promoted to MEASURED"
            )
        pat = (sitem.get("value") or {}).get("pattern")
        if not pat:
            bad.append(f"{who}: {item_id} has no pattern in {HW_SPEC}")
            continue
        for vkey, wline, wval, label in (
            ("from", icfg.get("old_line"), icfg.get("old_value"), "from"),
            ("before", icfg.get("old_line"), icfg.get("old_value"), "before"),
            ("cause", icfg.get("new_line"), icfg.get("new_value"), "cause"),
            ("to", icfg.get("new_line"), icfg.get("new_value"), "to"),
        ):
            hit = _match_in_bytes(v[vkey], pat)
            if hit != (wline, wval):
                bad.append(
                    f"{who}: {item_id} in {path} ({label}) is {hit}, not ({wline}, {wval!r})"
                )
        pnr_pat = str(icfg.get("pnr_pattern") or "")
        new_v = str(icfg.get("new_value", ""))
        nums = [n.replace(",", "") for n in re.findall(r"[\d,]+(?:\.\d+)?", new_v)]
        if not pnr_pat or not all(n in pnr_pat.replace("\\.", ".") for n in nums):
            bad.append(f"{who}: {item_id} pnr_pattern {pnr_pat!r} does not carry {new_v!r}")
        if pnr_log_text is not None and not re.search(pnr_pat, pnr_log_text, re.M):
            bad.append(f"{who}: {item_id} pnr_pattern {pnr_pat!r} not found in PnR report")

        if icfg.get("old_line") != icfg.get("new_line"):
            pair_ln = (icfg["old_line"], icfg["new_line"])
            expected_changes[("hardware", f"/items/{idx}/source/line")] = pair_ln
            expected_changes[("hardware_provenance", f"/claims/{idx}/source/line")] = pair_ln
        if icfg.get("old_value") != icfg.get("new_value"):
            pair_v = (icfg["old_value"], icfg["new_value"])
            expected_changes[("hardware", f"/items/{idx}/value")] = pair_v
            hw_label = sitem["hardware"]
            expected_changes[("hardware_provenance", f"/claims/{idx}/claim")] = (
                f"{hw_label} = {icfg['old_value']}",
                f"{hw_label} = {icfg['new_value']}",
            )

    for c in cs:
        key = (c["record"], c["pointer"])
        if key not in expected_changes:
            bad.append(
                f"{who}: {c['record']}{c['pointer']} is not a valid remeasured-header pointer"
            )
        elif (c["old"], c["new"]) != expected_changes[key]:
            bad.append(f"{who}: {c['record']}{c['pointer']} ({c['old']!r} -> {c['new']!r}) "
                       f"does not match header/report {expected_changes[key]!r}")
    all_keys = {(c["record"], c["pointer"]) for c in e["changes"]}
    missing_keys = sorted(set(expected_changes) - all_keys)
    if missing_keys:
        bad.append(f"{who}: missing remeasured-header pointers {missing_keys}")
    return bad


def _claim_unchanged(who: str, e: dict[str, Any], cs: list[Change],
                     v: dict[str, bytes], link: Link = (None, None)) -> list[str]:
    """Verify an RTL design change that moves only whole-file evidence hash/size
    metadata while preserving the claim's contract, identity, source, value,
    status, and architectural anchor lines."""
    path, eq = e["path"], e["equivalence"]
    bad = [] if eq.get("new_value") is not None else _whole(who, path, cs, v, link)
    claim_ids = eq.get("claims")
    anchors = eq.get("anchor_lines")
    if (not isinstance(claim_ids, list) or not claim_ids
            or not all(isinstance(x, str) for x in claim_ids)):
        return [*bad, f"{who}: claim-unchanged requires non-empty claims list"]
    if (not isinstance(anchors, list) or len(anchors) < 3
            or not all(isinstance(x, str) and x.strip() for x in anchors)):
        return [*bad, f"{who}: claim-unchanged requires at least 3 architectural anchor_lines"]

    for vkey in ("freeze", "from", "before", "cause", "to"):
        stripped_set = {ln.strip() for ln in _lines(v[vkey]) if ln.strip()}
        for anc in anchors:
            if anc.strip() not in stripped_set:
                bad.append(f"{who}: anchor line {anc!r} missing from {path} at {vkey}")

    frozen_spec = json.loads(_at(TAG, HW_SPEC).decode("utf-8"))
    now_spec = json.loads(_now(HW_SPEC).decode("utf-8"))
    frozen_hp_spec = json.loads(_at(TAG, HP_SPEC).decode("utf-8"))
    now_hp_spec = json.loads(_now(HP_SPEC).decode("utf-8"))
    if frozen_hp_spec.get("fields") != now_hp_spec.get("fields") or \
            frozen_hp_spec.get("source_kinds") != now_hp_spec.get("source_kinds"):
        bad.append(f"{who}: {HP_SPEC} contract changed since {TAG}")

    f_by_id = {it["id"]: (idx, it) for idx, it in enumerate(frozen_spec["items"])}
    n_by_id = {it["id"]: (idx, it) for idx, it in enumerate(now_spec["items"])}
    frozen_hw = json.loads((ROOT / FROZEN["hardware"][0]).read_text(encoding="utf-8"))
    frozen_hp = json.loads((ROOT / FROZEN["hardware_provenance"][0]).read_text(encoding="utf-8"))

    allowed_pointers: set[tuple[str, str]] = set()
    for cid in claim_ids:
        if cid not in f_by_id or cid not in n_by_id:
            bad.append(f"{who}: claim {cid!r} is not in {HW_SPEC}")
            continue
        f_idx, f_item = f_by_id[cid]
        n_idx, n_item = n_by_id[cid]
        if f_idx != n_idx or f_item != n_item:
            bad.append(f"{who}: specification contract for {cid!r} changed in {HW_SPEC}")
            continue
        if path not in f_item.get("evidence", []):
            bad.append(f"{who}: {path} is not in the evidence contract of {cid!r}")
            continue
        ev_idx = f_item["evidence"].index(path)
        allowed_pointers.add(("hardware", f"/items/{f_idx}/evidence/{ev_idx}/sha256"))
        if (f_item.get("value") or {}).get("file") == path:
            allowed_pointers.add(("hardware", f"/items/{f_idx}/source/sha256"))
        if frozen_hp["claims"][f_idx].get("evidence") == path:
            allowed_pointers.add(("hardware_provenance", f"/claims/{f_idx}/evidence_bytes"))
            allowed_pointers.add(("hardware_provenance", f"/claims/{f_idx}/evidence_sha256"))

        f_hw_item = frozen_hw["items"][f_idx]
        rule = f_item.get("value") or {}
        if rule.get("file") == path:
            pat = rule["pattern"]
            want_line = f_hw_item["source"]["line"]
            want_val = f_hw_item["value"]
            new_val = eq.get("new_value")
            if new_val is not None and cid == "isa_rtl":
                from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED
                allowed_pointers.add(("hardware", f"/items/{f_idx}/value"))
                allowed_pointers.add(("hardware_provenance", f"/claims/{f_idx}/claim"))
                if str(len(RTL_IMPLEMENTED)) != str(new_val):
                    bad.append(
                        f"{who}: RTL_IMPLEMENTED count {len(RTL_IMPLEMENTED)} != {new_val!r}"
                    )
                for vkey in ("freeze", "from", "before"):
                    hit = _match_in_bytes(v[vkey], pat)
                    if hit != (want_line, want_val):
                        bad.append(
                            f"{who}: {cid} in {path} ({vkey}) is {hit}, "
                            f"not ({want_line}, {want_val!r})"
                        )
                for vkey in ("cause", "to"):
                    hit = _match_in_bytes(v[vkey], pat)
                    if hit != (want_line, str(new_val)):
                        bad.append(
                            f"{who}: {cid} in {path} ({vkey}) is {hit}, "
                            f"not ({want_line}, {str(new_val)!r})"
                        )
                old_lsha = {_sha((_line(v[k], want_line) or "").encode("utf-8"))
                            for k in ("from", "before")}
                new_lsha = {_sha((_line(v[k], want_line) or "").encode("utf-8"))
                            for k in ("cause", "to")}
                for c in cs:
                    if c["pointer"].endswith("sha256"):
                        if old_lsha != {c["old"]}:
                            bad.append(f"{who}: {c['record']}{c['pointer']} old hash mismatch")
                        if new_lsha != {c["new"]}:
                            bad.append(f"{who}: {c['record']}{c['pointer']} new hash mismatch")
            else:
                for vkey in ("freeze", "from", "before", "cause", "to"):
                    hit = _match_in_bytes(v[vkey], pat)
                    if hit != (want_line, want_val):
                        bad.append(
                            f"{who}: {cid} in {path} ({vkey}) is {hit}, "
                            f"not ({want_line}, {want_val!r})"
                        )
        elif "file" in rule:
            src_file = rule["file"]
            src_bytes = _at(str(e["cause"]), src_file) if link[1] is not None else _now(src_file)
            hit_now = _match_in_bytes(src_bytes, rule["pattern"])
            expected_val = str(eq.get("expected_value", f_hw_item["value"]))
            want_pair = (f_hw_item["source"]["line"], expected_val)
            if hit_now != want_pair:
                bad.append(f"{who}: {cid} in {src_file} changed from {want_pair} to {hit_now}")
            if cid == "isa_rtl" and path == "rtl/hcpu_pkg.vh":
                from hijaiyyah.hisa.opcodes import RTL_IMPLEMENTED
                if link[1] is None and str(len(RTL_IMPLEMENTED)) != expected_val:
                    bad.append(
                        f"{who}: RTL_IMPLEMENTED count {len(RTL_IMPLEMENTED)} "
                        f"!= {expected_val}"
                    )
                op_rx = r"^`define\s+(OP_\w+)\s+8'h[0-9A-Fa-f]{2}"
                f_ops = set(re.findall(op_rx, v["freeze"].decode("utf-8"), re.M))
                t_ops = set(re.findall(op_rx, v["to"].decode("utf-8"), re.M))
                if not f_ops or not (f_ops <= t_ops):
                    bad.append(f"{who}: {path} lost frozen OP_ definitions {sorted(f_ops - t_ops)}")

    for c in e["changes"]:
        key = (c.get("record"), c.get("pointer"))
        if key not in allowed_pointers:
            bad.append(
                f"{who}: {c.get('record')}{c.get('pointer')} changes claim semantics or value, "
                "not allowed evidence metadata"
            )
    uncovered = sorted(
        set(allowed_pointers) - {(c.get("record"), c.get("pointer")) for c in e["changes"]}
    )
    if uncovered:
        bad.append(f"{who}: does not cover all evidence metadata pointers {uncovered}")
    return bad


def _equivalent(who: str, e: dict[str, Any], cs: list[Change],
                v: dict[str, bytes], link: Link = (None, None)) -> list[str]:
    kind, path, eq = e["equivalence"]["kind"], e["path"], e["equivalence"]
    since = f"since the cause of {link[0]!r}" if link[0] else "since the freeze"
    if kind == "comment-only":
        same = _design(v["from"]) == _design(v["to"])
        return ([] if same else [f"{who}: {path} changed in more than comments {since}"]) \
            + _whole(who, path, cs, v, link)
    if kind == "insert-only":
        rest = iter(_lines(v["to"]))
        kept = all(line in rest for line in _lines(v["from"]))
        return ([] if kept else [f"{who}: {path} lost or changed a line {since}, not "
                                 "only gained some"]) + _whole(who, path, cs, v, link)
    if kind == "line-moved":
        bad, pairs = [], [(int(a), int(b)) for a, b in eq.get("lines", [])]
        where_from = f"after {link[0]!r}" if link[0] else "at the freeze"
        where_to = f"at {e['cause']}" if link[1] else "now"
        for a, b in pairs:
            texts = {_line(v["from"], a), _line(v["before"], a), _line(v["cause"], b),
                     _line(v["to"], b)}
            if len(texts) != 1 or None in texts:
                bad.append(f"{who}: {path}:{a} {where_from} is not {path}:{b} {where_to}")
        if link[0] and (_sha(v["from"]) != _sha(v["before"])):
            bad.append(f"{who}: {path} moved between {link[0]!r} and {e['cause']}")
        for c in cs:
            if _moved(c, path, pairs) is None:
                bad.append(f"{who}: {c['record']}{c['pointer']} {c['old']!r} -> {c['new']!r} "
                           "moves none of its cited lines")
        used = {_moved(c, path, pairs) for c in e["changes"]}
        if not pairs or set(pairs) - used:
            bad.append(f"{who}: cited lines {sorted(set(pairs) - used) or 'none'} are moved by "
                       "no change")
        return bad
    if kind == "remeasured-header":
        return _remeasured_header(who, e, cs, v, link)
    if kind == "claim-unchanged":
        return _claim_unchanged(who, e, cs, v, link)
    from .telemetry_sources import _has_source
    n, bad = eq.get("line"), []
    was, now = _row(v["freeze"], n), _row(v["now"], n)
    if was is None or now is None:
        return [f"{who}: {path}:{n} is not a row of the contract"]
    if (was["field"], was["origin"].strip()) != (now["field"], now["origin"].strip()):
        bad.append(f"{who}: {path}:{n} names another field or origin than at the freeze")
    if _has_source(was["today"].strip()) != _has_source(now["today"].strip()):
        bad.append(f"{who}: {path}:{n} changed whether its field has a source")

    def hashed(*versions: str) -> set[str]:
        return {_sha((_line(v[k], n) or "").encode("utf-8")) for k in versions}

    for c in cs:
        if hashed("freeze", "before") != {c["old"]}:
            bad.append(f"{who}: {c['record']}{c['pointer']} was not {path}:{n} at the freeze "
                       "and until its cause")
        if hashed("cause", "now") != {c["new"]}:
            bad.append(f"{who}: {c['record']}{c['pointer']} is not {path}:{n} at its cause "
                       "and now")
    return bad


def _links(addendum: dict[str, Any]) -> tuple[dict[str, Link], dict[str, list[str]]]:
    """The chains the addendum writes out: for each entry, the entry it
    continues and the entry that continues it -- and, for each entry that
    names one in `after`, what keeps that link from holding. A link is never
    inferred; it is the entry's own `after`, and it is checked."""
    entries = addendum["entries"]
    ids = [e.get("id") for e in entries]
    after: dict[str, str] = {}
    then: dict[str, str] = {}
    bad: dict[str, list[str]] = {}
    for i, e in enumerate(entries):
        if "after" not in e:
            continue
        who, a = str(e.get("id") or "an entry with no id"), e["after"]
        why = bad.setdefault(who, [])
        if not isinstance(a, str) or a not in ids[:i]:
            why.append(f"{who}: comes after {a!r}, which is no entry written before it")
            continue
        p = entries[ids.index(a)]
        if p.get("path") != e.get("path"):
            why.append(f"{who}: continues {a!r}, which is about another file")
        p_kind = (p.get("equivalence") or {}).get("kind")
        e_kind = (e.get("equivalence") or {}).get("kind")
        if (e_kind == "line-moved") != (p_kind == "line-moved"):
            why.append(
                f"{who}: a chain is only for a whole file's hash or line-moved "
                f"of the same kind, cannot link {p_kind!r} to {e_kind!r}"
            )
        elif e_kind == "line-moved":
            p_lines = [int(b) for _, b in (p.get("equivalence") or {}).get("lines", [])]
            e_lines = [int(x) for x, _ in (e.get("equivalence") or {}).get("lines", [])]
            if p_lines != e_lines:
                why.append(
                    f"{who}: line-moved chain positions {e_lines} "
                    f"do not continue {p_lines} of {a!r}"
                )
        if a in then:
            why.append(f"{who}: {a!r} is already continued by {then[a]!r}")
            continue
        after[who], then[a] = a, who
        left = {(c.get("record"), c.get("pointer")): c.get("new") for c in p.get("changes", [])}
        held = {(c.get("record"), c.get("pointer")): c.get("old") for c in e.get("changes", [])}
        if set(left) != set(held):
            why.append(f"{who}: does not change the pointers {a!r} changed, all of them and "
                       "no other")
        elif left != held:
            why.append(f"{who}: its old values are not the new values of {a!r}")
        try:
            first, second = _commit(str(p.get("cause"))), _commit(str(e.get("cause")))
        except LookupError:
            continue
        if first == second or not _ancestor(first, second):
            why.append(f"{who}: {e.get('cause')} does not come after {p.get('cause')}, the "
                       f"cause of {a!r}")
        else:
            try:
                if _at(first, str(e.get("path"))) != _at(second + "^", str(e.get("path"))):
                    why.append(
                        f"{who}: {e.get('path')} moved between "
                        f"{p.get('cause')} and {e.get('cause')}"
                    )
            except LookupError:
                pass
    return {i: (after.get(i), then.get(i)) for i in set(after) | set(then)}, bad


def _entry(e: dict[str, Any], cs: list[Change], link: Link = (None, None),
           unlinked: list[str] | None = None,
           addendum: dict[str, Any] | None = None) -> list[str]:
    """One entry, held to its reason, its cause and its evidence of
    equivalence -- for the changes it makes to one record -- and, when it
    continues an entry or is continued by one, to that link."""
    who = str(e.get("id") or "an entry with no id")
    empty = [f for f in ("id", "path", "cause", "reason", "equivalence") if not e.get(f)]
    if empty:
        return [f"{who}: no {', '.join(empty)}"]
    if e["equivalence"].get("kind") not in KINDS:
        return [f"{who}: {e['equivalence'].get('kind')!r} is not evidence of equivalence"]
    if ("after" in e or link[1]) and e["equivalence"]["kind"] not in CHAINABLE:
        return [f"{who}: a chain is only for a whole file's hash or line-moved, and "
                f"{e['equivalence']['kind']!r} is not one"]
    if unlinked:
        return list(unlinked)
    path, cause = e["path"], e["cause"]
    try:
        commit = _commit(cause)
    except LookupError:
        return [f"{who}: {cause} is not a commit"]
    bad = []
    if commit == _commit(TAG) or not _ancestor(_commit(TAG), commit):
        bad.append(f"{who}: {cause} does not come after {TAG}")
    if path not in _touched(commit):
        bad.append(f"{who}: {cause} does not change {path}")
    try:
        v = {"freeze": _at(TAG, path), "before": _at(commit + "^", path),
             "cause": _at(commit, path), "now": _now(path)}
        if link[1] and addendum is not None:
            nxt = next((x for x in addendum["entries"] if x.get("id") == link[1]), None)
            if nxt is not None:
                v["to"] = _at(_commit(str(nxt["cause"])) + "^", path)
            else:
                v["to"] = v["cause"]
        else:
            v["to"] = v["cause"] if link[1] else v["now"]
    except (LookupError, OSError) as why:
        return [*bad, f"{who}: {why}"]
    v["from"] = v["before"] if link[0] else v["freeze"]
    return bad + _equivalent(who, e, cs, v, link)


def problems(name: str, addendum: dict[str, Any] | None = None) -> list[str]:
    """What keeps the addendum from standing beside one record: a frozen file
    that is no longer the tag's object, a pointer changed twice or changed to
    itself, or an entry without its reason, cause or evidence. A pointer is
    changed twice unless the second entry names, in `after`, the entry that
    changed it last -- and that link holds."""
    addendum = addendum if addendum is not None else load()
    bad = [f"{p} is not the object frozen at {TAG}" for p in FROZEN[name]
           if _now(p) != _at(TAG, p)]
    links, unlinked = _links(addendum)
    last: dict[str, Any] = {}
    for e in addendum["entries"]:
        cs = [c for c in e.get("changes", []) if c.get("record") == name]
        if not cs:
            continue
        who = str(e.get("id") or "an entry with no id")
        bad += _entry(e, cs, links.get(who, (None, None)), unlinked.get(who), addendum)
        for c in cs:
            if c["pointer"] in last and links.get(who, (None, None))[0] != last[c["pointer"]]:
                bad.append(f"{name}{c['pointer']} is changed twice")
            if c["old"] == c["new"]:
                bad.append(f"{name}{c['pointer']} is changed to itself")
            last[c["pointer"]] = e.get("id")
    return bad


def verify(name: str, fresh: dict[str, Any], frozen: dict[str, Any] | None = None,
           addendum: dict[str, Any] | None = None) -> list[str]:
    """One record as it stands today -- frozen, plus the addendum -- against
    what the evidence builds now: the addendum's problems, then every path
    that still differs."""
    addendum = addendum if addendum is not None else load()
    probs = problems(name, addendum)
    try:
        now = current(name, frozen, addendum)
    except LookupError as why:
        return [*probs, str(why)]
    return probs + _diff(now, fresh)


def check(addendum: dict[str, Any] | None = None) -> list[str]:
    """The whole addendum: its kinds, its entries named once, every change to
    a record that exists, and each record reconciled by its own verifier."""
    from . import hardware, hardware_provenance, telemetry_sources
    addendum = addendum if addendum is not None else load()
    bad = []
    if list(addendum.get("kinds", {})) != list(KINDS):
        bad.append(f"the kinds of evidence are not {list(KINDS)}")
    ids = [e.get("id") for e in addendum["entries"]]
    if len(ids) != len(set(ids)):
        bad.append("an entry id is used twice")
    bad += [f"{e.get('id')}: {c.get('record')!r} is no frozen record"
            for e in addendum["entries"] for c in e.get("changes", [])
            if c.get("record") not in FROZEN]
    verifiers = {"hardware": hardware.verify, "telemetry_sources": telemetry_sources.verify,
                 "hardware_provenance": hardware_provenance.verify}
    for name, run in verifiers.items():
        bad += [f"{name}: {p}" for p in run()]
    return bad


# -- the page ---------------------------------------------------------------------------


def _shown(value: Any) -> str:
    if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value):
        return f"`{value[:12]}…`"
    return f"`{value}`"


def _subject(frozen: dict[str, Any], pointer: str) -> str:
    """The item, claim, field or signal a pointer lies in, named as the
    frozen record names it."""
    parts = _parts(pointer)
    if parts[0] in ("items", "claims", "registry"):
        row = frozen[parts[0]][int(parts[1])]
        return f"`{row.get('id') or row.get('field')}`"
    if parts[:2] == ["rtl_signals", "signals"]:
        return f"`{frozen['rtl_signals']['signals'][int(parts[2])]['name']}`"
    return "—"


def page(addendum: dict[str, Any]) -> str:
    """NUI/LAYER6_ADDENDUM.md, drawn from the record and, for the names of
    what each pointer lies in, from the frozen records."""
    frozen = {name: json.loads((ROOT / paths[0]).read_text(encoding="utf-8"))
              for name, paths in FROZEN.items()}
    counts = {name: len(changes(name, addendum)) for name in FROZEN}
    total = sum(counts.values())
    out = ["# Adendum pasca-freeze Lapis 6", "",
           f"Dihasilkan `src/hijaiyyah/nui/layer6_addendum.py` dari "
           f"`{RECORD.relative_to(ROOT)}`. {addendum['decided']}.", "",
           f"> {addendum['rule']}", "",
           f"Catatan beku Lapis 6.1–6.3 — model, halaman, dan spec-nya — tetap byte demi byte "
           f"objek di tag `{TAG}`. Adendum ini catatan baru di sampingnya, bukan bangkitan "
           "ulang: **freeze historis ≠ keadaan repositori sekarang**. Keadaan sekarang adalah "
           "catatan beku dengan perubahan di bawah ini, dan harus sama dengan yang dibangun "
           "buktinya hari ini.", "",
           f"**{len(addendum['entries'])} entri, {total} perubahan**: "
           + ", ".join(f"`{n}` {k}" for n, k in counts.items()) + ".", "",
           "## Bukti kesetaraan", ""]
    out += [f"- **{k}** — {v}." for k, v in addendum["kinds"].items()]
    if addendum.get("chain"):
        out += ["", "## Rantai perubahan", "", f"{addendum['chain']}."]
    out += ["", "Untuk tiap perubahan: nilai lama adalah nilai catatan beku dan dihasilkan "
            "ulang dari berkasnya di freeze dan tepat sebelum commit penyebab; nilai sekarang "
            "adalah hasil build hari ini dan dihasilkan ulang dari berkasnya di commit penyebab "
            "dan di pohon kerja.", ""]
    for e in addendum["entries"]:
        eq, where = e["equivalence"], ""
        if eq["kind"] == "line-moved":
            where = "baris " + ", ".join(f"{a} → {b}" for a, b in eq["lines"])
        elif eq["kind"] == "row-meaning":
            where = f"baris {eq['line']}"
        elif eq["kind"] == "remeasured-header":
            fp_short = eq["rtl_fingerprint"][:12]
            pnr_short = eq["reports"]["pnr_sha256"][:12]
            where = f"sidik jari `{fp_short}…`, laporan `{pnr_short}…`"
        elif eq["kind"] == "claim-unchanged":
            where = "klaim " + ", ".join(f"`{c}`" for c in eq["claims"])
        out += [f"## {e['id']}", "",
                f"`{e['path']}` · penyebab `{e['cause']}` · bukti kesetaraan "
                f"**{eq['kind']}**" + (f", {where}" if where else "")
                + (f" · melanjutkan entri **{e['after']}**" if "after" in e else ""), "",
                f"{e['reason']}.", "",
                "| catatan | butir | pointer | lama | sekarang |", "|---|---|---|---|---|"]
        out += [f"| `{c['record']}` | {_subject(frozen[c['record']], c['pointer'])} | "
                f"`{c['pointer']}` | {_shown(c['old'])} | {_shown(c['new'])} |"
                for c in e["changes"]]
        out.append("")
    out += ["## Mengulang", "", "```bash",
            "PYTHONPATH=src python3 -m hijaiyyah.nui.layer6_addendum --verify", "```"]
    return "\n".join(out) + "\n"


def write() -> Path:
    PAGE.write_text(page(load()), encoding="utf-8")
    return PAGE


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args[:1] == ["--write"]:
        print(f"page: {write().relative_to(ROOT)}")
        return 0
    addendum = load()
    bad = check(addendum)
    if PAGE.read_text(encoding="utf-8") != page(addendum):
        bad.append(f"{PAGE.relative_to(ROOT)} is not drawn from the record")
    total = sum(len(changes(n, addendum)) for n in FROZEN)
    print("\n".join(bad) if bad else
          f"post-freeze addendum holds: {len(addendum['entries'])} entries, {total} changes; "
          f"the frozen records are the objects at {TAG}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
