"""Layer 7 on one Linux service (src/hijaiyyah/nui/layer7_linux.py): ISOLATE_SERVICE.

The owner's decisions of 6 October 2026: the test VM cosmictera-layer5-uji is
made again, cron.service is the first unit, UNIT_INACTIVE, UNIT_FAILED and
VM_UNREACHABLE are classes of Layer 7 alone, and ISOLATE_SERVICE is a row of
7.4 of its own that only reads. By a further decision the same day,
RESTART_SERVICE is the one action: `sudo systemctl start cron.service` on the
test VM, for UNIT_INACTIVE only, three attempts in all, success being the
reading that follows.

Every output below was measured on that VM on 6 October 2026, before the
classifier was written, and is held here byte for byte: each hashes to the
SHA-256 its lab run recorded outside the repository, and to the one the
contract's table quotes. What is held:

    each measured form gets its name, and only a measured form does;
    inactive and failed are told apart though both exit 3;
    a form that was not measured stops as UNKNOWN, with what was seen;
    isolating runs one argv, once, through Layer 5's guard, on the test VM
    and that unit only, and acts on nothing;
    restarting starts an inactive unit and nothing else, reads it again, and
    stops at three attempts for one fault, counted from the records;
    and what is kept is kept outside the repository.

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


def test_the_isolate_row_is_in_7_4_with_its_permission() -> None:
    assert l7.authorizations()[lx.ISOLATE] == "AUTHORIZED"
    text = CONTRACT.read_text(encoding="utf-8")
    assert "| 13 | Menggolongkan gangguan `cron.service` di VM uji Linux, tanpa tindakan" in text


# -- it acts on nothing --------------------------------------------------------------------


def test_every_report_says_it_may_not_act() -> None:
    reports = [lx.isolate(run=_measured(name)) for name in WANT]
    reports += [lx.isolate(run=_runner(*UNMEASURED[name])) for name in UNMEASURED]
    reports += [lx.isolate("cosmictera-layer5", run=_measured("ACTIVE"))]
    assert all(r["may_act"] is False and r["action"] == lx.ISOLATE for r in reports)
    assert {r["decision"] for r in reports} == {lx.NO_FAULT, lx.ISOLATED, l7.STOP}


def _is_docstring(tree: ast.AST, node: ast.AST) -> bool:
    return any(isinstance(f, (ast.FunctionDef, ast.ClassDef)) and f.body
               and isinstance(f.body[0], ast.Expr) and f.body[0].value is node
               for f in ast.walk(tree))


def test_isolating_runs_the_read_and_nothing_else() -> None:
    assert lx.STATUS_ARGV == ("systemctl", "status", "cron.service")
    assert set(lx.FAULTS) == {"VM_UNREACHABLE", "UNIT_INACTIVE", "UNIT_FAILED"}
    for name in WANT:
        calls: list[Any] = []
        lx.isolate(run=_measured(name, calls))
        assert [c[0][4:] for c in calls] == [list(lx.STATUS_ARGV)], name


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
    for bad in (["--isolate"], ["cosmictera-layer5"], ["--record", "x"]):
        assert lx.main(bad) == 2
    assert "layer7_linux" in capsys.readouterr().out


# ======================================================================================
# RESTART_SERVICE (owner, 6 October 2026): one narrow action, verified by the reading
# ======================================================================================

START = ["sudo", "systemctl", "start", "cron.service"]
STATUS = ["systemctl", "status", "cron.service"]
SINCE = "Tue 2026-10-06 15:18:02 UTC"
AT = datetime(2026, 10, 6, 16, 0, 0, tzinfo=timezone.utc)
READINGS = {"active": (ACTIVE_OUT, "", 0), "inactive": (INACTIVE_OUT, "", 3),
            "failed": (FAILED_OUT, "", 3), "stopped": ("", STOPPED_ERR, 1),
            "activating": (_line("activating (start)"), "", 3)}


class Box:
    """A stand-in for the test VM: the unit's state, and what each start does
    to it. The readings it gives are the measured ones."""

    def __init__(self, state: str = "inactive", then: tuple[str, ...] = ("active",),
                 start_exit: int = 0, since: str = SINCE) -> None:
        self.state, self.then, self.start_exit, self.since = state, list(then), start_exit, since
        self.calls: list[list[str]] = []
        self.kw: list[dict[str, Any]] = []
        self.on_start: Any = None

    @property
    def starts(self) -> int:
        return sum(1 for c in self.calls if c[4:] == START)

    def run(self, argv: list[str], **kw: Any) -> Any:
        self.calls.append(argv)
        self.kw.append(kw)
        assert argv[:4] == ["limactl", "shell", VM, "--"], argv
        if argv[4:] == STATUS:
            out, err, code = READINGS[self.state]
            return SimpleNamespace(returncode=code, stdout=out.replace(SINCE, self.since),
                                   stderr=err)
        assert argv[4:] == START, argv
        if self.on_start is not None:
            self.on_start()
        if self.then:
            self.state = self.then.pop(0)
        return SimpleNamespace(returncode=self.start_exit, stdout="", stderr="")


def _kept(result: dict[str, Any]) -> dict[str, Any]:
    kept: dict[str, Any] = json.loads(
        (Path(result["evidence"]) / "record.json").read_text(encoding="utf-8"))
    return kept


def test_an_inactive_unit_is_started_once_and_read_again(tmp_path: Path) -> None:
    box = Box()
    r = lx.restart(into=tmp_path, run=box.run, now=AT)
    assert (r["decision"], r["fault"], r["condition"]) == (lx.RESTORED, lx.UNIT_INACTIVE, None)
    assert [c[4:] for c in box.calls] == [STATUS, START, STATUS]
    assert all(k["stdin"] is subprocess.DEVNULL and k["timeout"] == lx.TIMEOUT_S
               and k["env"]["LIMA_HOME"] == layer5.host()["lima_home"] for k in box.kw)
    assert [a["attempt"] for a in r["attempts"]] == [1]
    assert r["attempts"][0]["after"]["decision"] == lx.NO_FAULT
    where = Path(r["evidence"])
    assert where == tmp_path.resolve() / "20261006T160000Z-restart"
    assert sorted(p.name for p in where.iterdir()) == [
        "attempt-1.after.stderr.txt", "attempt-1.after.stdout.txt",
        "attempt-1.start.stderr.txt", "attempt-1.start.stdout.txt",
        "before.stderr.txt", "before.stdout.txt", "record.json"]
    assert (where / "before.stdout.txt").read_text(encoding="utf-8") == INACTIVE_OUT
    assert (where / "attempt-1.after.stdout.txt").read_text(encoding="utf-8") == ACTIVE_OUT
    kept = _kept(r)
    assert kept["decision"] == lx.RESTORED and kept["argv"] == START
    assert not {"stdout", "stderr"} & set(kept["before"]["observation"])


def test_three_attempts_in_all_and_never_a_fourth(tmp_path: Path) -> None:
    box = Box(then=())                       # every start leaves it inactive
    r = lx.restart(into=tmp_path, run=box.run, now=AT)
    assert (r["decision"], box.starts) == (lx.FAILED_RECOVERY, 3)
    assert [a["attempt"] for a in r["attempts"]] == [1, 2, 3]
    assert len(box.calls) == 1 + 3 * 2 and lx.attempt_limit() == 3
    assert _kept(r)["decision"] == lx.FAILED_RECOVERY


@pytest.mark.parametrize("then, starts", [(("active",), 1), (("inactive", "active"), 2),
                                          (("inactive", "inactive", "active"), 3)])
def test_it_stops_at_the_first_reading_that_is_active(tmp_path: Path, then: tuple[str, ...],
                                                      starts: int) -> None:
    box = Box(then=then)
    r = lx.restart(into=tmp_path, run=box.run, now=AT)
    assert (r["decision"], box.starts, len(r["attempts"])) == (lx.RESTORED, starts, starts)


def test_success_is_the_reading_and_never_the_exit_code_of_the_start(tmp_path: Path) -> None:
    # exit 0 and the unit is not active: not a success, and the counter moves
    quiet = Box(then=(), start_exit=0)
    r = lx.restart(into=tmp_path / "a", run=quiet.run, now=AT)
    assert r["decision"] == lx.FAILED_RECOVERY
    assert {a["started"]["exit_code"] for a in r["attempts"]} == {0}
    # a non-zero exit and the unit is active: the reading says restored
    loud = Box(then=("active",), start_exit=1)
    r = lx.restart(into=tmp_path / "b", run=loud.run, now=AT)
    assert r["decision"] == lx.RESTORED and r["attempts"][0]["started"]["exit_code"] == 1


@pytest.mark.parametrize("state, decision, fault, condition", [
    ("failed", l7.STOP, lx.UNIT_FAILED, l7.UNAUTHORIZED),
    ("stopped", l7.STOP, lx.VM_UNREACHABLE, l7.UNAUTHORIZED),
    ("activating", l7.STOP, None, l7.UNKNOWN),
    ("active", lx.NO_FAULT, None, None)])
def test_only_an_inactive_unit_is_started(tmp_path: Path, state: str, decision: str,
                                          fault: str | None, condition: str | None) -> None:
    box = Box(state=state)
    r = lx.restart(into=tmp_path, run=box.run, now=AT)
    assert (r["decision"], r["fault"], r["condition"]) == (decision, fault, condition)
    assert box.starts == 0 and [c[4:] for c in box.calls] == [STATUS] and r["attempts"] == []
    # classed and recorded all the same
    kept = _kept(r)
    assert (kept["decision"], kept["fault"]) == (decision, fault)


def test_a_failed_unit_is_classed_recorded_and_not_restarted(tmp_path: Path) -> None:
    box = Box(state="failed")
    r = lx.restart(into=tmp_path, run=box.run, now=AT)
    assert box.starts == 0 and "not restarted" in r["why"] and lx.RESTARTABLE == lx.UNIT_INACTIVE
    assert (Path(r["evidence"]) / "before.stdout.txt").read_text(encoding="utf-8") == FAILED_OUT


@pytest.mark.parametrize("after, condition", [("failed", l7.UNAUTHORIZED),
                                              ("stopped", l7.UNAUTHORIZED),
                                              ("activating", l7.UNKNOWN)])
def test_a_reading_that_is_neither_inactive_nor_active_ends_the_attempts(
        tmp_path: Path, after: str, condition: str) -> None:
    box = Box(then=(after, "active"))
    r = lx.restart(into=tmp_path, run=box.run, now=AT)
    assert (r["decision"], r["condition"], box.starts) == (l7.STOP, condition, 1)
    assert "not restarted again" in r["why"]


def _limit(tmp_path: Path, n: int | None) -> Path:
    text = CONTRACT.read_text(encoding="utf-8")
    line = "Batas percobaan RESTART_SERVICE untuk satu gangguan: 3\n"
    assert text.count(line) == 1
    path = tmp_path / f"LAYER7-{n}.md"
    path.write_text(text.replace(line, "" if n is None else line.replace(": 3", f": {n}")),
                    encoding="utf-8")
    return path


def test_the_attempts_of_one_fault_are_counted_across_runs(tmp_path: Path) -> None:
    store = tmp_path / "store"
    first = Box(then=())
    r1 = lx.restart(into=store, contract=_limit(tmp_path, 2), run=first.run, now=AT)
    assert (r1["decision"], first.starts) == (lx.FAILED_RECOVERY, 2)
    # the same fault, under the owner's limit of three: one start is left
    second = Box(then=())
    r2 = lx.restart(into=store, run=second.run, now=AT.replace(minute=1))
    assert (r2["decision"], second.starts) == (lx.FAILED_RECOVERY, 1)
    assert r2["attempts_before_this_run"] == 2 and [a["attempt"] for a in r2["attempts"]] == [3]
    # and then none: the fault has had its three
    third = Box(then=("active",))
    r3 = lx.restart(into=store, run=third.run, now=AT.replace(minute=2))
    assert (r3["decision"], third.starts, r3["attempts"]) == (lx.FAILED_RECOVERY, 0, [])
    assert "no more" in r3["why"] and [c[4:] for c in third.calls] == [STATUS]
    # another inactive spell is another fault, with its own three
    later = Box(then=("active",), since="Tue 2026-10-06 17:30:00 UTC")
    r4 = lx.restart(into=store, run=later.run, now=AT.replace(minute=3))
    assert (r4["decision"], later.starts) == (lx.RESTORED, 1)
    assert r4["fault_id"] != r1["fault_id"] == r2["fault_id"] == r3["fault_id"]


def test_what_cannot_be_counted_is_not_started(tmp_path: Path) -> None:
    broken = tmp_path / "20261006T150000Z-restart"
    broken.mkdir(parents=True)
    (broken / "record.json").write_text("{not json", encoding="utf-8")
    box = Box()
    r = lx.restart(into=tmp_path, run=box.run, now=AT)
    assert (r["decision"], r["condition"], box.starts) == (l7.STOP, l7.UNKNOWN, 0)

    class NoSince(Box):
        def run(self, argv: list[str], **kw: Any) -> Any:
            got = super().run(argv, **kw)
            got.stdout = got.stdout.replace(f" since {SINCE}; 1min 44s ago", "")
            return got
    assert f" since {SINCE}; 1min 44s ago" in INACTIVE_OUT
    bare = NoSince()
    r = lx.restart(into=tmp_path / "other", run=bare.run, now=AT)
    assert (r["decision"], r["condition"], bare.starts) == (l7.STOP, l7.UNKNOWN, 0)
    assert r["fault"] == lx.UNIT_INACTIVE and r["fault_id"] is None


def test_the_limit_is_the_contract_s_and_without_one_nothing_runs(tmp_path: Path) -> None:
    one = Box(then=())
    r = lx.restart(into=tmp_path / "a", contract=_limit(tmp_path, 1), run=one.run, now=AT)
    assert (r["decision"], one.starts, r["attempt_limit"]) == (lx.FAILED_RECOVERY, 1, 1)
    for n in (None, 0):
        none = Box()
        r = lx.restart(into=tmp_path / "b", contract=_limit(tmp_path, n), run=none.run, now=AT)
        assert (r["decision"], r["condition"], none.calls) == (l7.STOP, l7.UNAUTHORIZED, [])


def _without(tmp_path: Path, name: str, edit: Any) -> Path:
    text = CONTRACT.read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith(f"| {name} |"))
    path = tmp_path / "LAYER7.md"
    path.write_text(text.replace(row + "\n", edit(row)), encoding="utf-8")
    return path


@pytest.mark.parametrize("name", [lx.ISOLATE, lx.RESTART, l7.RECORD],
                         ids=["isolate", "restart", "record"])
@pytest.mark.parametrize("edit", [lambda row: row.replace("**AUTHORIZED**", "**DENIED**") + "\n",
                                  lambda row: ""], ids=["denied", "absent"])
def test_without_all_three_rows_nothing_runs(tmp_path: Path, name: str, edit: Any) -> None:
    box = Box()
    r = lx.restart(into=tmp_path / "store", contract=_without(tmp_path, name, edit),
                   run=box.run, now=AT)
    assert (r["decision"], r["condition"], box.calls) == (l7.STOP, l7.UNAUTHORIZED, [])
    assert not (tmp_path / "store").exists()


@pytest.mark.parametrize("vm, unit", [("cosmictera-layer5", "cron.service"),
                                      (VM, "ssh.service"), ("another-vm", "cron.service")])
def test_the_restart_is_for_the_test_vm_and_that_unit_only(tmp_path: Path, vm: str,
                                                           unit: str) -> None:
    box = Box()
    r = lx.restart(vm, unit, into=tmp_path / "store", run=box.run, now=AT)
    assert (r["decision"], r["condition"], box.calls) == (l7.STOP, l7.UNAUTHORIZED, [])
    assert not (tmp_path / "store").exists()


def test_nothing_is_started_without_a_place_outside_the_repository() -> None:
    for inside in (ROOT, ROOT / "NUI", ROOT / "portal8888" / "build"):
        box = Box()
        r = lx.restart(into=inside, run=box.run, now=AT)
        assert (r["decision"], r["condition"], box.calls) == (l7.STOP, l7.UNAUTHORIZED, [])
    assert not list(ROOT.glob("*-restart")) and not list((ROOT / "NUI").glob("*-restart"))


def test_a_start_that_does_not_return_is_an_attempt_and_the_reading_decides(
        tmp_path: Path) -> None:
    class Hung(Box):
        def run(self, argv: list[str], **kw: Any) -> Any:
            if argv[4:] == START:
                self.calls.append(argv)
                self.kw.append(kw)
                self.state = "active"
                raise subprocess.TimeoutExpired(argv, kw["timeout"])
            return super().run(argv, **kw)
    box = Hung()
    r = lx.restart(into=tmp_path, run=box.run, now=AT)
    assert r["decision"] == lx.RESTORED and box.starts == 1
    assert r["attempts"][0]["started"]["exit_code"] is None
    assert r["attempts"][0]["started"]["timed_out_after_s"] == lx.TIMEOUT_S


def test_an_older_record_changed_during_the_run_is_reported(tmp_path: Path) -> None:
    old = tmp_path / "20261006T151947Z-measure-inactive"
    old.mkdir()
    (old / "stdout.txt").write_text(INACTIVE_OUT, encoding="utf-8")
    box = Box()
    box.on_start = lambda: (old / "stdout.txt").write_text("edited", encoding="utf-8")
    r = lx.restart(into=tmp_path, run=box.run, now=AT)
    assert (r["decision"], r["condition"]) == (l7.STOP, l7.UNAUTHORIZED)
    assert "older record" in r["why"] and _kept(r)["condition"] == l7.UNAUTHORIZED


def test_the_one_acting_argv_is_whole_and_layer_5_s_guard_still_refuses_it() -> None:
    assert lx.START_ARGV == tuple(START)
    for argv in (START, START[1:]):
        with pytest.raises(layer5.Refused):
            layer5.guard(argv)
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    head = tree.body[0]
    assert isinstance(head, ast.Expr)
    strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
               and isinstance(n.value, str) and n is not head.value
               and not _is_docstring(tree, n)]
    assert strings.count("sudo") == 1 and strings.count("start") == 1
    assert sum("sudo" in s for s in strings) == 1
    for word in ("stop", "restart", "reload", "kill", "enable", "disable", "reset-failed",
                 "daemon-reload", "rm", "tee", "reboot", "shutdown", "mask"):
        assert word not in strings, word
    runs = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name) and n.func.id == "run"]
    assert len(runs) == 2
    for call in runs:
        first = call.args[0]
        assert isinstance(first, ast.List)
        assert [ast.literal_eval(e) for e in first.elts[:2]] == ["limactl", "shell"]
        assert isinstance(first.elts[-1], ast.Starred)      # *argv, the module's own
    assert not any(isinstance(n, ast.Attribute) and n.attr in ("Popen", "system", "check_call",
                                                               "check_output", "call")
                   for n in ast.walk(tree))
    # restart() takes no argv, no command and no unit list from its caller
    import inspect
    assert list(inspect.signature(lx.restart).parameters) == [
        "vm", "unit", "into", "contract", "run", "now"]
    assert list(inspect.signature(lx._start).parameters) == ["vm", "run"]


def test_the_contract_opens_one_row_and_keeps_the_general_one_denied() -> None:
    table = l7.authorizations()
    assert table[lx.RESTART] == "AUTHORIZED" and table[lx.ISOLATE] == "AUTHORIZED"
    assert (len(table), sum(v == "AUTHORIZED" for v in table.values()),
            sum(v == "DENIED" for v in table.values())) == (17, 10, 7)
    general = next(row for row in table if row.startswith("10 perintah host lama"))
    assert "`systemctl start`" in general and table[general] == "DENIED"
    assert lx.attempt_limit() == 3
    text = CONTRACT.read_text(encoding="utf-8")
    for needle in ("| 14 | Memulai `cron.service` di VM uji Linux atas `UNIT_INACTIVE`",
                   "**Tiga percobaan, total**", "**`UNIT_INACTIVE` saja.**",
                   "**Berhasil = pembacaan sesudahnya**", "**Gangguan dibuat manusia.**",
                   "**Lari di VM belum ada.**"):
        assert needle in text, needle
    # Owner, 7 October 2026: the test VM's account may run everything, so the
    # bound is NUI's and the contract may not say the OS narrows it.
    flat = " ".join(text.split())
    for needle in ("akun `lima` memiliki `(ALL) NOPASSWD: ALL`",
                   "ditegakkan oleh argv tetap dan guard NUI, bukan oleh pembatasan "
                   + "su" + "doers tingkat OS",
                   "batasan lab, bukan model least-privilege OS yang kuat",
                   "Aturan itu **tidak dipasang**"):
        assert needle in flat, needle
    assert "dipersempit di OS VM uji" not in flat


def test_the_command_line_restarts_only_when_asked(monkeypatch: pytest.MonkeyPatch,
                                                   capsys: pytest.CaptureFixture[str]) -> None:
    asked: list[str] = []
    monkeypatch.setattr(lx, "restart", lambda: asked.append("restart") or {
        "decision": lx.RESTORED})
    assert lx.main(["--restart"]) == 0 and asked == ["restart"]
    monkeypatch.setattr(lx, "restart", lambda: {"decision": lx.FAILED_RECOVERY})
    assert lx.main(["--restart"]) == 1
    for bad in (["--restart", "ssh.service"], ["--start"], ["--restart", "--record"]):
        assert lx.main(bad) == 2
    capsys.readouterr()
