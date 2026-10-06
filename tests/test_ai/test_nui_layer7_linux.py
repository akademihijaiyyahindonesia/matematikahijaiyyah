"""Layer 7 on one Linux service (src/hijaiyyah/nui/layer7_linux.py): ISOLATE_SERVICE.

The owner's decisions of 6 October 2026: the test VM cosmictera-layer5-uji is
made again, cron.service is the first unit, UNIT_INACTIVE, UNIT_FAILED and
VM_UNREACHABLE are classes of Layer 7 alone, and ISOLATE_SERVICE is a row of
7.4 of its own that only reads. Restarting the unit is not opened.

Every output below was measured on that VM on 6 October 2026, before the
classifier was written, and is held here byte for byte: each hashes to the
SHA-256 its lab run recorded outside the repository, and to the one the
contract's table quotes. What is held:

    each measured form gets its name, and only a measured form does;
    inactive and failed are told apart though both exit 3;
    a form that was not measured stops as UNKNOWN, with what was seen;
    one argv runs, once, through Layer 5's guard, on the test VM and that
    unit only -- never sudo, never a start, never the main instance;
    it acts on nothing, and what it keeps is kept outside the repository.

No test touches a VM: the runner is a stand-in that returns the measured
bytes.
"""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hijaiyyah.nui import layer5  # noqa: E402
from hijaiyyah.nui import layer7 as l7  # noqa: E402
from hijaiyyah.nui import layer7_linux as lx  # noqa: E402

VM = "cosmictera-layer5-uji"
SOURCE = ROOT / "src" / "hijaiyyah" / "nui" / "layer7_linux.py"
CONTRACT = ROOT / "NUI" / "LAYER7.md"

# -- the measured outputs, verbatim ----------------------------------------------------
ACTIVE_OUT = (
    "● cron.service - Regular background program processing daemon\n"
    "     Loaded: loaded (/usr/lib/systemd/system/cron.service; enabled; preset: enabled)\n"
    "     Active: active (running) since Tue 2026-10-06 14:57:56 UTC; 15min ago\n"
    "       Docs: man:cron(8)\n"
    "   Main PID: 790 (cron)\n"
    "      Tasks: 1 (limit: 4598)\n"
    "     Memory: 452.0K (peak: 1.8M)\n"
    "        CPU: 20ms\n"
    "     CGroup: /system.slice/cron.service\n"
    "             └─790 /usr/sbin/cron -f -P\n")
ACTIVE_ERR = (
    "")
INACTIVE_OUT = (
    "○ cron.service - Regular background program processing daemon\n"
    "     Loaded: loaded (/usr/lib/systemd/system/cron.service; enabled; preset: enabled)\n"
    "     Active: inactive (dead) since Tue 2026-10-06 15:18:02 UTC; 1min 44s ago\n"
    "   Duration: 20min 6.417s\n"
    "       Docs: man:cron(8)\n"
    "    Process: 790 ExecStart=/usr/sbin/cron -f -P $EXTRA_OPTS (code=killed, signal=TERM)\n"
    "   Main PID: 790 (code=killed, signal=TERM)\n"
    "        CPU: 40ms\n")
INACTIVE_ERR = (
    "")
FAILED_OUT = (
    "× cron.service - Regular background program processing daemon\n"
    "     Loaded: loaded (/usr/lib/systemd/system/cron.service; enabled; preset: enabled)\n"
    "    Drop-In: /run/systemd/system/cron.service.d\n"
    "             └─lab.conf\n"
    "     Active: failed (Result: exit-code) since Tue 2026-10-06 15:35:27 UTC; 43s ago\n"
    "   Duration: 2ms\n"
    "       Docs: man:cron(8)\n"
    "    Process: 1508 ExecStart=/bin/false (code=exited, status=1/FAILURE)\n"
    "   Main PID: 1508 (code=exited, status=1/FAILURE)\n"
    "        CPU: 675us\n")
FAILED_ERR = (
    "")
AFTER_RESET_OUT = (
    "○ cron.service - Regular background program processing daemon\n"
    "     Loaded: loaded (/usr/lib/systemd/system/cron.service; enabled; preset: enabled)\n"
    "     Active: inactive (dead) since Tue 2026-10-06 15:35:27 UTC; 1min 46s ago\n"
    "   Duration: 2ms\n"
    "       Docs: man:cron(8)\n"
    "   Main PID: 1508 (code=exited, status=1/FAILURE)\n"
    "        CPU: 675us\n")
AFTER_RESET_ERR = (
    "")
VM_MISSING_OUT = (
    "")
VM_MISSING_ERR = (
    "time=\"2026-10-06T22:39:20+07:00\" level=fatal msg=\"instance `cosmictera-layer5-tidak-ada` does not exist, run `limactl create cosmictera-layer5-tidak-ada` to create a new instance\"\n"  # noqa: E501
)
VM_STOPPED_OUT = (
    "")
VM_STOPPED_ERR = (
    "time=\"2026-10-06T22:39:28+07:00\" level=fatal msg=\"instance `cosmictera-layer5-uji` is stopped, run `limactl start cosmictera-layer5-uji` to start the instance\"\n"  # noqa: E501
)
AFTER_BOOT_OUT = (
    "● cron.service - Regular background program processing daemon\n"
    "     Loaded: loaded (/usr/lib/systemd/system/cron.service; enabled; preset: enabled)\n"
    "     Active: active (running) since Tue 2026-10-06 15:39:41 UTC; 40s ago\n"
    "       Docs: man:cron(8)\n"
    "   Main PID: 680 (cron)\n"
    "      Tasks: 1 (limit: 4598)\n"
    "     Memory: 436.0K (peak: 1.5M)\n"
    "        CPU: 3ms\n"
    "     CGroup: /system.slice/cron.service\n"
    "             └─680 /usr/sbin/cron -f -P\n")
AFTER_BOOT_ERR = (
    "")

#: name: (lab run, VM, exit code, stdout, stderr, sha256 of each as recorded)
MEASURED = {
    "ACTIVE": ("20261006T151343Z-measure-active",
              "cosmictera-layer5-uji", 0, ACTIVE_OUT, ACTIVE_ERR,
              "4398ac39764fc2540bf99105896aab1eff2f0a7b567d29d008bb416b59bbddf5",
              "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "INACTIVE": ("20261006T151947Z-measure-inactive",
                "cosmictera-layer5-uji", 3, INACTIVE_OUT, INACTIVE_ERR,
                "4c068df7891507858e05690e2a2c459371bf8778fccc1c249c005d452edc7c8a",
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "FAILED": ("20261006T153611Z-measure-failed",
              "cosmictera-layer5-uji", 3, FAILED_OUT, FAILED_ERR,
              "61a942fffa2a678f0b544973038d14798d17e31133fb38c6aab70f713cdb4c79",
              "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "AFTER_RESET": ("20261006T153714Z-measure-inactive-after-reset",
                   "cosmictera-layer5-uji", 3, AFTER_RESET_OUT, AFTER_RESET_ERR,
                   "9b26eef8e05744c94350bb4991a32532b569ababc36754b102650a4f33179b01",
                   "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "VM_MISSING": ("20261006T153920Z-measure-vm-missing",
                  "cosmictera-layer5-tidak-ada", 1, VM_MISSING_OUT, VM_MISSING_ERR,
                  "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                  "81671e4246f50b95cd7523d102de89d16ac0f0c269b2173e0b1e9967f1b4d39a"),
    "VM_STOPPED": ("20261006T153928Z-measure-vm-stopped",
                  "cosmictera-layer5-uji", 1, VM_STOPPED_OUT, VM_STOPPED_ERR,
                  "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                  "f66cb9fc825de6e5d23d8bd0fb480565fc9681a56409fa32094a9786589d12a4"),
    "AFTER_BOOT": ("20261006T154021Z-measure-active-after-boot",
                  "cosmictera-layer5-uji", 0, AFTER_BOOT_OUT, AFTER_BOOT_ERR,
                  "4f60abe00643511cbc3220548a3c62d5d75506f25608fd075befa5300c60b3e1",
                  "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
}
WANT = {"ACTIVE": (lx.NO_FAULT, None), "AFTER_BOOT": (lx.NO_FAULT, None),
        "INACTIVE": (lx.ISOLATED, lx.UNIT_INACTIVE),
        "AFTER_RESET": (lx.ISOLATED, lx.UNIT_INACTIVE),
        "FAILED": (lx.ISOLATED, lx.UNIT_FAILED),
        "VM_STOPPED": (lx.ISOLATED, lx.VM_UNREACHABLE)}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _runner(out: str = "", err: str = "", code: int = 0,
            calls: list[Any] | None = None) -> Any:
    def run(argv: list[str], **kw: Any) -> Any:
        if calls is not None:
            calls.append((argv, kw))
        return SimpleNamespace(returncode=code, stdout=out, stderr=err)
    return run


def _measured(name: str, calls: list[Any] | None = None) -> Any:
    _, _, code, out, err, _, _ = MEASURED[name]
    return _runner(out, err, code, calls)


def _seen(out: str = "", err: str = "", code: int = 0, vm: str = VM) -> dict[str, Any]:
    return {"vm_name": vm, "stdout": out, "stderr": err, "exit_code": code}


# -- the fixtures are the measurements -------------------------------------------------


def test_each_fixture_is_the_bytes_its_lab_run_recorded() -> None:
    assert len(MEASURED) == 7
    for name, (run, _, _, out, err, out_sha, err_sha) in MEASURED.items():
        assert (_sha(out), _sha(err)) == (out_sha, err_sha), name
        assert run.startswith("20261006T") and "-measure-" in run, name


def test_the_contract_quotes_the_runs_and_their_hashes() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    for name, (run, _, code, _, _, out_sha, _) in MEASURED.items():
        row = next(line for line in text.splitlines() if line.startswith(f"| `{run}` |"))
        assert f"| {code} |" in row and f"`{out_sha[:12]}…`" in row, name


# -- each measured form gets its name ---------------------------------------------------


@pytest.mark.parametrize("name", WANT)
def test_a_measured_form_is_classed_as_measured(name: str) -> None:
    decision, fault = WANT[name]
    r = lx.isolate(run=_measured(name))
    assert (r["decision"], r["fault"], r["condition"]) == (decision, fault, None), r["why"]
    assert r["observation"]["exit_code"] == MEASURED[name][2]
    assert r["observation"]["stdout_sha256"] == MEASURED[name][5]


def test_inactive_and_failed_exit_alike_and_are_told_apart() -> None:
    assert MEASURED["INACTIVE"][2] == MEASURED["FAILED"][2] == 3
    assert lx.classify(_seen(INACTIVE_OUT, "", 3))[0] == lx.UNIT_INACTIVE
    assert lx.classify(_seen(FAILED_OUT, "", 3))[0] == lx.UNIT_FAILED
    assert lx.UNIT_INACTIVE != lx.UNIT_FAILED
    # Layer 5 is not changed: to it both are a collector error.
    assert {layer5.outcome(3, "")} == {"collector_error"}
    assert "UNIT_INACTIVE" not in json.dumps(layer5.load()["outcomes"])


def test_the_main_pid_line_does_not_class_the_unit() -> None:
    """After reset-failed the unit is inactive and still shows the FAILURE of
    its last process; it is UNIT_INACTIVE, not UNIT_FAILED."""
    assert "status=1/FAILURE" in AFTER_RESET_OUT and "inactive (dead)" in AFTER_RESET_OUT
    assert lx.classify(_seen(AFTER_RESET_OUT, "", 3))[0] == lx.UNIT_INACTIVE


def test_a_vm_that_does_not_answer_is_classed_from_limactl_itself() -> None:
    stopped, missing = MEASURED["VM_STOPPED"], MEASURED["VM_MISSING"]
    assert lx.classify(_seen("", stopped[4], 1))[0] == lx.VM_UNREACHABLE
    # the missing instance was measured under the name it does not have
    assert lx.classify(_seen("", missing[4], 1, vm=missing[1]))[0] == lx.VM_UNREACHABLE
    said = missing[4].replace(missing[1], VM)
    r = lx.isolate(run=_runner("", said, 1))
    assert (r["decision"], r["fault"]) == (lx.ISOLATED, lx.VM_UNREACHABLE)


# -- only a measured form gets a name ----------------------------------------------------


def _line(state: str) -> str:
    assert "Active: inactive (dead)" in INACTIVE_OUT
    return INACTIVE_OUT.replace("Active: inactive (dead)", f"Active: {state}")


STOPPED_ERR = MEASURED["VM_STOPPED"][4]
UNMEASURED: dict[str, tuple[str, str, int]] = {
    "failed by a start timeout": (_line("failed (Result: timeout)"), "", 3),
    "failed by a signal": (_line("failed (Result: signal)"), "", 3),
    "activating": (_line("activating (start)"), "", 3),
    "deactivating": (_line("deactivating (stop-sigterm)"), "", 3),
    "active but exited": (_line("active (exited)"), "", 0),
    "active with exit 3": (ACTIVE_OUT, "", 3),
    "inactive with exit 0": (INACTIVE_OUT, "", 0),
    "inactive with exit 1": (INACTIVE_OUT, "", 1),
    "failed with exit 0": (FAILED_OUT, "", 0),
    "a stderr that is not empty": (INACTIVE_OUT, "Warning: something\n", 3),
    "the status of another unit": (INACTIVE_OUT.replace("cron.service - ", "ssh.service - "),
                                   "", 3),
    "two Active lines": (INACTIVE_OUT + FAILED_OUT, "", 3),
    "a unit that is not found": ("", "Unit cron.service could not be found.\n", 4),
    "nothing at all": ("", "", 255),
    "limactl refusing another VM": ("", STOPPED_ERR.replace(VM, "cosmictera-layer5"), 1),
    "limactl refusing, with a stdout": ("x\n", STOPPED_ERR, 1),
    "limactl refusing, with another exit": ("", STOPPED_ERR, 255),
    "an Active line with no detail": (_line("inactive"), "", 3),
}


@pytest.mark.parametrize("name", UNMEASURED)
def test_a_form_that_was_not_measured_stops_as_unknown(name: str) -> None:
    out, err, code = UNMEASURED[name]
    r = lx.isolate(run=_runner(out, err, code))
    assert (r["decision"], r["condition"], r["fault"]) == (l7.STOP, l7.UNKNOWN, None), r["why"]
    assert r["why"] and r["observation"]["exit_code"] == code


def test_no_answer_within_the_limit_stops_as_unknown() -> None:
    def run(argv: list[str], **kw: Any) -> Any:
        raise subprocess.TimeoutExpired(argv, kw["timeout"])
    r = lx.isolate(run=run)
    assert (r["decision"], r["condition"], r["observation"]) == (l7.STOP, l7.UNKNOWN, None)


# -- one argv, once, on the test VM and that unit ----------------------------------------


def test_it_runs_one_command_once_and_it_is_the_read() -> None:
    calls: list[Any] = []
    r = lx.isolate(run=_measured("INACTIVE", calls))
    assert [c[0] for c in calls] == [
        ["limactl", "shell", VM, "--", "systemctl", "status", "cron.service"]]
    kw = calls[0][1]
    assert kw["stdin"] is subprocess.DEVNULL and kw["timeout"] == lx.TIMEOUT_S
    assert kw["env"]["LIMA_HOME"] == layer5.host()["lima_home"]
    assert r["observation"]["allowed_by"] == "systemctl status"
    assert layer5.guard(list(lx.STATUS_ARGV)) == "systemctl status"
    assert lx.instance() == layer5.load()["host"]["test_instance"] == VM


def test_the_guard_decides_before_anything_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []

    def refuse(argv: list[str]) -> str:
        raise layer5.Refused("off the allowlist")
    monkeypatch.setattr(layer5, "guard", refuse)
    r = lx.isolate(run=_measured("ACTIVE", calls))
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.UNKNOWN) and calls == []


@pytest.mark.parametrize("vm, unit", [("cosmictera-layer5", "cron.service"),
                                      (VM, "ssh.service"), (VM, "cron"),
                                      ("another-vm", "cron.service"),
                                      (VM + ";id", "cron.service")])
def test_another_vm_or_unit_is_not_this_row(vm: str, unit: str) -> None:
    calls: list[Any] = []
    r = lx.isolate(vm, unit, run=_measured("INACTIVE", calls))
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.UNAUTHORIZED)
    assert calls == [] and r["observation"] is None


def _contract(tmp_path: Path, edit: Any) -> Path:
    text = CONTRACT.read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith(f"| {lx.ISOLATE} |"))
    path = tmp_path / "LAYER7.md"
    path.write_text(text.replace(row + "\n", edit(row)), encoding="utf-8")
    return path


@pytest.mark.parametrize("edit", [lambda row: row.replace("**AUTHORIZED**", "**DENIED**") + "\n",
                                  lambda row: ""], ids=["denied", "absent"])
def test_without_its_row_it_does_not_read(tmp_path: Path, edit: Any) -> None:
    calls: list[Any] = []
    r = lx.isolate(contract=_contract(tmp_path, edit), run=_measured("INACTIVE", calls))
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.UNAUTHORIZED) and calls == []


def test_the_row_is_in_7_4_and_restarting_is_not() -> None:
    table = l7.authorizations()
    assert table[lx.ISOLATE] == "AUTHORIZED"
    assert not any("RESTART_SERVICE" in row for row in table)
    assert not any("systemctl start" in row and status == "AUTHORIZED"
                   for row, status in table.items())
    text = CONTRACT.read_text(encoding="utf-8")
    assert "| 13 | Menggolongkan gangguan `cron.service` di VM uji Linux, tanpa tindakan" in text
    assert "Sampai saat itu tidak ada izin tindakan otomatis pada Linux" in text


# -- it acts on nothing --------------------------------------------------------------------


def test_every_report_says_it_may_not_act() -> None:
    reports = [lx.isolate(run=_measured(name)) for name in WANT]
    reports += [lx.isolate(run=_runner(*UNMEASURED[name])) for name in UNMEASURED]
    reports += [lx.isolate("cosmictera-layer5", run=_measured("ACTIVE"))]
    assert all(r["may_act"] is False and r["action"] == lx.ISOLATE for r in reports)
    assert {r["decision"] for r in reports} == {lx.NO_FAULT, lx.ISOLATED, l7.STOP}


def test_the_module_holds_one_argv_and_no_way_to_change_the_vm() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    doc = ast.get_docstring(tree) or ""
    assert "sudo" in doc and "RESTART_SERVICE" in doc      # said, as what it does not do
    head = tree.body[0]
    assert isinstance(head, ast.Expr)
    strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
               and isinstance(n.value, str) and n is not head.value]
    for word in ("sudo", "start", "stop", "restart", "reload", "kill", "enable", "disable",
                 "reset-failed", "daemon-reload", "rm", "tee"):
        assert word not in strings, word
    assert not any("sudo" in s for s in strings)
    assert lx.STATUS_ARGV == ("systemctl", "status", "cron.service")
    runs = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name) and n.func.id == "run"]
    assert len(runs) == 1
    first = runs[0].args[0]
    assert isinstance(first, ast.List)
    assert [ast.literal_eval(e) for e in first.elts[:2]] == ["limactl", "shell"]
    assert not any(isinstance(n, ast.Attribute) and n.attr in ("Popen", "system", "check_call",
                                                               "check_output", "call")
                   for n in ast.walk(tree))
    assert set(lx.FAULTS) == {"VM_UNREACHABLE", "UNIT_INACTIVE", "UNIT_FAILED"}


# -- what it keeps -------------------------------------------------------------------------


def test_a_report_is_kept_outside_the_repository(tmp_path: Path) -> None:
    r = lx.isolate(run=_measured("FAILED"))
    at = datetime(2026, 10, 6, 15, 40, 0, tzinfo=timezone.utc)
    where = lx.record(r, into=tmp_path, now=at)
    assert where == tmp_path.resolve() / "20261006T154000Z-isolate"
    assert sorted(p.name for p in where.iterdir()) == ["report.json", "stderr.txt", "stdout.txt"]
    assert (where / "stdout.txt").read_text(encoding="utf-8") == FAILED_OUT
    kept = json.loads((where / "report.json").read_text(encoding="utf-8"))
    assert kept["fault"] == lx.UNIT_FAILED and kept["may_act"] is False
    assert "stdout" not in kept["observation"]
    assert kept["observation"]["stdout_sha256"] == _sha(FAILED_OUT)
    with pytest.raises(FileExistsError):
        lx.record(r, into=tmp_path, now=at)


def test_evidence_inside_the_repository_is_refused(tmp_path: Path) -> None:
    r = lx.isolate(run=_measured("ACTIVE"))
    for inside in (ROOT, ROOT / "NUI", ROOT / "portal8888" / "build"):
        with pytest.raises(layer5.Refused, match="inside the repository"):
            lx.record(r, into=inside)
    denied = tmp_path / "LAYER7.md"
    denied.write_text(CONTRACT.read_text(encoding="utf-8").replace(
        f"| {l7.RECORD} | Mekanisme Lapis 5 (7.3, 7.6, 7.7) | **AUTHORIZED** |",
        f"| {l7.RECORD} | Mekanisme Lapis 5 (7.3, 7.6, 7.7) | **DENIED** |"), encoding="utf-8")
    with pytest.raises(layer5.Refused, match="does not authorize recording"):
        lx.record(r, into=tmp_path, contract=denied)
    assert lx.EVIDENCE == "~/cosmictera-layer5/linux-service/"


def test_the_command_line_takes_nothing_but_record(capsys: pytest.CaptureFixture[str]) -> None:
    for bad in (["--restart"], ["cosmictera-layer5"], ["--record", "x"]):
        assert lx.main(bad) == 2
    assert "layer7_linux" in capsys.readouterr().out
