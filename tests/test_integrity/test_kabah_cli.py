"""
`kabah` from a shell: plug and play, and the refusals that come with it.

The library was already three lines with no configuration. The command exists
for the case where three lines of Python is three lines too many — and because
a security tool that is awkward to run gets run wrong.

Every refusal here is tested, because a CLI that quietly does the wrong thing
with a missing key or a world-readable one is worse than one that will not run.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from hijaiyyah.crypto.cli import main


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    key = tmp_path / "k.key"
    assert main(["--key", str(key), "keygen"]) == 0
    (tmp_path / "ledger.txt").write_text("TRANSFER 1500000 IDR\n", encoding="utf-8")
    return tmp_path


def test_seal_and_open_round_trip(workspace: Path) -> None:
    key = str(workspace / "k.key")
    source = workspace / "ledger.txt"
    original = source.read_bytes()

    assert main(["--key", key, "seal", str(source)]) == 0
    sealed = workspace / "ledger.txt.kbh"
    assert sealed.exists()

    out = workspace / "recovered.txt"
    assert main(["--key", key, "open", str(sealed), "--out", str(out)]) == 0
    assert out.read_bytes() == original


def test_a_tampered_record_is_refused(workspace: Path, capsys) -> None:
    key = str(workspace / "k.key")
    assert main(["--key", key, "seal", str(workspace / "ledger.txt")]) == 0

    sealed = workspace / "ledger.txt.kbh"
    data = bytearray(sealed.read_bytes())
    data[len(data) - 1] ^= 1
    sealed.write_bytes(bytes(data))

    assert main(["--key", key, "open", str(sealed), "--out", str(workspace / "x")]) == 1
    assert "authentication failed" in capsys.readouterr().err


def test_a_different_purpose_cannot_open_it(workspace: Path) -> None:
    key = str(workspace / "k.key")
    assert main(["--key", key, "--purpose", "ledger", "seal",
                 str(workspace / "ledger.txt")]) == 0
    assert main(["--key", key, "--purpose", "audit", "open",
                 str(workspace / "ledger.txt.kbh"),
                 "--out", str(workspace / "x")]) == 1


def test_a_missing_key_says_what_to_do(workspace: Path, capsys) -> None:
    assert main(["--key", str(workspace / "absent.key"), "seal",
                 str(workspace / "ledger.txt")]) == 1
    assert "kabah keygen" in capsys.readouterr().err


def test_a_world_readable_key_is_refused(workspace: Path, capsys) -> None:
    """
    A key the filesystem is sharing is not a key. Refusing is the whole point
    of checking.
    """
    key = workspace / "k.key"
    os.chmod(key, 0o644)
    assert main(["--key", str(key), "seal", str(workspace / "ledger.txt")]) == 1
    assert "readable by others" in capsys.readouterr().err


def test_keygen_writes_a_private_key(workspace: Path) -> None:
    mode = (workspace / "k.key").stat().st_mode
    assert not mode & (stat.S_IRWXG | stat.S_IRWXO), "keygen must write 0600"


def test_keygen_refuses_to_overwrite_without_force(workspace: Path, capsys) -> None:
    """
    Overwriting makes every record sealed with the old key unverifiable, which
    for an integrity system is the same as losing them.
    """
    key = str(workspace / "k.key")
    before = (workspace / "k.key").read_text(encoding="ascii")
    assert main(["--key", key, "keygen"]) == 1
    assert "already exists" in capsys.readouterr().err
    assert (workspace / "k.key").read_text(encoding="ascii") == before

    assert main(["--key", key, "keygen", "--force"]) == 0
    assert (workspace / "k.key").read_text(encoding="ascii") != before


def test_fingerprint_warns_that_it_is_not_a_vetted_hash(workspace: Path, capsys) -> None:
    assert main(["fingerprint", str(workspace / "ledger.txt")]) == 0
    captured = capsys.readouterr()
    assert len(captured.out.split()[0]) == 64
    assert "[EH]" in captured.err
    assert "sha256sum" in captured.err


def test_describe_names_the_layer_that_carries_security(capsys) -> None:
    assert main(["describe"]) == 0
    out = capsys.readouterr().out
    assert "Lapis 3 memikul keamanannya" in out
    assert "Lapis 1 tanpa kunci — bukan otentikasi" in out
    assert "[EH]" in out, "the sponge layer must still be labelled"


def test_the_command_is_registered_as_an_entry_point() -> None:
    import tomllib

    root = Path(__file__).resolve().parents[2]
    with open(root / "pyproject.toml", "rb") as handle:
        scripts = tomllib.load(handle)["project"]["scripts"]
    assert scripts["kabah"] == "hijaiyyah.crypto.cli:main"
