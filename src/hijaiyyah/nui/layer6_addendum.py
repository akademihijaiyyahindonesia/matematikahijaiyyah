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

    comment-only   every line that is not blank or a whole-line // comment is
                   the same, in order -- the rule the place-and-route
                   fingerprint hashes by
    insert-only    every line of the frozen file is still there, in order;
                   lines were only added
    line-moved     each cited line has the same text at its new number
    row-meaning    the contract row parses to the same field and origin, and
                   still has no source

For every change, too: the old value is the frozen record's and reproduces
from the file at the freeze and just before the cause, and the new value is
today's build's and reproduces from the file at the cause and now.
"""
from __future__ import annotations

import copy
import functools
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from .layer6_freeze import TAG, _ancestor, _blob, _diff, _full, _git
from .repository_index import ROOT

RECORD = ROOT / "NUI" / "layer6_addendum.json"
PAGE = ROOT / "NUI" / "LAYER6_ADDENDUM.md"
#: Each frozen record, then the page and the spec it was built with.
FROZEN = {
    "hardware": ("NUI/hardware_inventory.json", "NUI/HARDWARE.md",
                 "NUI/spec/hardware_inventory.json"),
    "telemetry_sources": ("NUI/telemetry_sources.json", "NUI/TELEMETRY_SOURCES.md",
                          "NUI/spec/telemetry_sources.json"),
    "hardware_provenance": ("NUI/hardware_provenance.json", "NUI/HARDWARE_PROVENANCE.md",
                            "NUI/spec/hardware_provenance.json"),
}
KINDS = ("comment-only", "insert-only", "line-moved", "row-meaning")
CONTRACT = "NUI/spec/telemetry_sources.json"
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
    not stand in for it."""
    frozen = frozen if frozen is not None else json.loads(
        (ROOT / FROZEN[name][0]).read_text(encoding="utf-8"))
    out = copy.deepcopy(frozen)
    for c in changes(name, addendum):
        try:
            was = _get(frozen, c["pointer"])
        except (LookupError, ValueError, TypeError):
            raise LookupError(f"{name}{c['pointer']} is not in the frozen record") from None
        if was != c["old"]:
            raise LookupError(f"{name}{c['pointer']}: the frozen record holds {was!r}, "
                              f"not {c['old']!r}")
        _put(out, c["pointer"], c["new"])
    return out


# -- the evidence of equivalence ------------------------------------------------------


def _design(data: bytes) -> list[str]:
    """The lines synthesis sees: not blank, not a whole-line // comment."""
    return [ln for ln in _lines(data) if ln.strip() and not ln.strip().startswith("//")]


def _whole(who: str, path: str, cs: list[Change], v: dict[str, bytes]) -> list[str]:
    """A whole file's hash or size, as the record wrote it before and after."""
    bad = []
    for c in cs:
        size = c["pointer"].endswith("_bytes")
        if {len(b) if size else _sha(b) for b in (v["freeze"], v["before"])} != {c["old"]}:
            bad.append(f"{who}: {c['record']}{c['pointer']} was not {path} at the freeze and "
                       "until its cause")
        if {len(b) if size else _sha(b) for b in (v["cause"], v["now"])} != {c["new"]}:
            bad.append(f"{who}: {c['record']}{c['pointer']} is not {path} at its cause and now")
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


def _equivalent(who: str, e: dict[str, Any], cs: list[Change],
                v: dict[str, bytes]) -> list[str]:
    kind, path, eq = e["equivalence"]["kind"], e["path"], e["equivalence"]
    if kind == "comment-only":
        same = _design(v["freeze"]) == _design(v["now"])
        return ([] if same else [f"{who}: {path} changed in more than comments since the "
                                 "freeze"]) + _whole(who, path, cs, v)
    if kind == "insert-only":
        rest = iter(_lines(v["now"]))
        kept = all(line in rest for line in _lines(v["freeze"]))
        return ([] if kept else [f"{who}: {path} lost or changed a line since the freeze, not "
                                 "only gained some"]) + _whole(who, path, cs, v)
    if kind == "line-moved":
        bad, pairs = [], [(int(a), int(b)) for a, b in eq.get("lines", [])]
        for a, b in pairs:
            texts = {_line(v["freeze"], a), _line(v["before"], a), _line(v["cause"], b),
                     _line(v["now"], b)}
            if len(texts) != 1 or None in texts:
                bad.append(f"{who}: {path}:{a} at the freeze is not {path}:{b} now")
        for c in cs:
            if _moved(c, path, pairs) is None:
                bad.append(f"{who}: {c['record']}{c['pointer']} {c['old']!r} -> {c['new']!r} "
                           "moves none of its cited lines")
        used = {_moved(c, path, pairs) for c in e["changes"]}
        if not pairs or set(pairs) - used:
            bad.append(f"{who}: cited lines {sorted(set(pairs) - used) or 'none'} are moved by "
                       "no change")
        return bad
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


def _entry(e: dict[str, Any], cs: list[Change]) -> list[str]:
    """One entry, held to its reason, its cause and its evidence of
    equivalence -- for the changes it makes to one record."""
    who = str(e.get("id") or "an entry with no id")
    empty = [f for f in ("id", "path", "cause", "reason", "equivalence") if not e.get(f)]
    if empty:
        return [f"{who}: no {', '.join(empty)}"]
    if e["equivalence"].get("kind") not in KINDS:
        return [f"{who}: {e['equivalence'].get('kind')!r} is not evidence of equivalence"]
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
    except (LookupError, OSError) as why:
        return [*bad, f"{who}: {why}"]
    return bad + _equivalent(who, e, cs, v)


def problems(name: str, addendum: dict[str, Any] | None = None) -> list[str]:
    """What keeps the addendum from standing beside one record: a frozen file
    that is no longer the tag's object, a pointer changed twice or changed to
    itself, or an entry without its reason, cause or evidence."""
    addendum = addendum if addendum is not None else load()
    bad = [f"{p} is not the object frozen at {TAG}" for p in FROZEN[name]
           if _now(p) != _at(TAG, p)]
    seen: set[str] = set()
    for e in addendum["entries"]:
        cs = [c for c in e.get("changes", []) if c.get("record") == name]
        if not cs:
            continue
        bad += _entry(e, cs)
        for c in cs:
            if c["pointer"] in seen:
                bad.append(f"{name}{c['pointer']} is changed twice")
            if c["old"] == c["new"]:
                bad.append(f"{name}{c['pointer']} is changed to itself")
            seen.add(c["pointer"])
    return bad


def verify(name: str, fresh: dict[str, Any], frozen: dict[str, Any] | None = None,
           addendum: dict[str, Any] | None = None) -> list[str]:
    """One record as it stands today -- frozen, plus the addendum -- against
    what the evidence builds now: the addendum's problems, then every path
    that still differs."""
    addendum = addendum if addendum is not None else load()
    try:
        now = current(name, frozen, addendum)
    except LookupError as why:
        return [str(why)]
    return problems(name, addendum) + _diff(now, fresh)


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
        out += [f"## {e['id']}", "",
                f"`{e['path']}` · penyebab `{e['cause']}` · bukti kesetaraan "
                f"**{eq['kind']}**" + (f", {where}" if where else ""), "",
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
