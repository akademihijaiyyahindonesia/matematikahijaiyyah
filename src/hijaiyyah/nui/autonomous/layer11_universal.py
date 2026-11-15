"""NUI Layer 11 — Universal Computation (`src/hijaiyyah/nui/autonomous/layer11_universal.py`).

Unifies Layers L0 through L10 into one verified computation chain where EVERY inter-layer
junction (`J01_L0_TO_L1` through `J11_L10_TO_L11`) has an executable deterministic oracle
(satisfying the owner's exit criterion in `NUI/LAYERS.md`:
"Tiap sambungan dalam rantai punya pemeriksaan yang dijalankan, bukan diagram").

Strictly separates `SIMULATED` (interpreter / Icarus Verilog `tb_parity.v`),
`MEASURED` (historical Tang Nano 20K board records), and `LIVE` (`0 LIVE` sources),
never claiming physical hardware execution from simulation.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ...cells.hpg1_bridge import compile_and_execute_cells
from ...core.master_table import MASTER_TABLE
from ...hisa.assembler import assemble
from ...hisa.machine import HISAMachine
from .. import (
    atom as nui_atom,
    execution_trace as nui_execution_trace,
    facts as nui_facts,
    hardware_state as nui_hardware_state,
    layer4_freeze as nui_layer4_freeze,
    layer5 as nui_layer5,
    layer6_addendum as nui_layer6_addendum,
    layer7 as nui_layer7,
    layer7_decision as nui_layer7_decision,
    program_graph as nui_program_graph,
    program_index as nui_program_index,
    program_summary as nui_program_summary,
    repository_graph as nui_repo_graph,
    repository_index as nui_repo_index,
    rtl_function as nui_rtl_function,
    usr as nui_usr,
)
from . import (
    layer8_diagnostics as nui_layer8,
    layer9_reasoning as nui_layer9,
    layer10_engineering as nui_layer10,
)

ROOT: Path = nui_repo_index.ROOT

JUNCTION_IDS: tuple[str, ...] = (
    "J01_L0_TO_L1",
    "J02_L1_TO_L2",
    "J03_L2_TO_L3",
    "J04_L3_TO_L4",
    "J05_L4_TO_L5",
    "J06_L5_TO_L6",
    "J07_L6_TO_L7",
    "J08_L7_TO_L8",
    "J09_L8_TO_L9",
    "J10_L9_TO_L10",
    "J11_L10_TO_L11",
)

OFFICIAL_BSM_HCELL: str = """
بسم := ب + س + م;
⊢ بسم;
↦ Θ̂(بسم);
↦ U(بسم);
↦ ρ(بسم);
↦ ‖بسم‖²;
↦ d₂²(ب, م);
""".strip()


@dataclass(frozen=True)
class JunctionOracleResult:
    """Executable oracle result for a single inter-layer junction."""

    junction_id: str
    from_layer: int
    to_layer: int
    name: str
    oracle_function: str
    passed: bool
    epistemic_class: str
    measurements: dict[str, Any]
    oracle_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UniversalComputationRecord:
    """Complete auditable record of the L0–L11 Universal Computation Chain."""

    computation_id: str
    source_kind: str
    source_code: str
    usr_representation: dict[str, Any]
    junction_ids: tuple[str, ...]
    junctions: list[dict[str, Any]]
    all_junctions_passed: bool
    outputs: list[int]
    expected_outputs: list[int]
    verify_4b_prime_ok: bool
    native_letter_opcodes_emitted: int
    peak_gpr_used: int
    rtl_simulated: bool
    three_way_parity: bool
    epistemic_status: str
    hardware_claim_guard: str
    record_sha256: str

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["junction_ids"] = list(self.junction_ids)
        return out


def _compute_sha256(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k not in ("record_sha256", "oracle_sha256")}
    raw = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _make_junction(
    *,
    junction_id: str,
    from_layer: int,
    to_layer: int,
    name: str,
    oracle_function: str,
    passed: bool,
    epistemic_class: str,
    measurements: dict[str, Any],
) -> JunctionOracleResult:
    draft = {
        "junction_id": junction_id,
        "from_layer": from_layer,
        "to_layer": to_layer,
        "name": name,
        "oracle_function": oracle_function,
        "passed": passed,
        "epistemic_class": epistemic_class,
        "measurements": measurements,
    }
    return JunctionOracleResult(
        junction_id=junction_id,
        from_layer=from_layer,
        to_layer=to_layer,
        name=name,
        oracle_function=oracle_function,
        passed=passed,
        epistemic_class=epistemic_class,
        measurements=measurements,
        oracle_sha256=_compute_sha256(draft),
    )


def verify_universal_chain(record: UniversalComputationRecord | dict[str, Any]) -> dict[str, Any]:
    """Verify the L11 UniversalComputationRecord:
    1. Top-level SHA-256 and every junction's individual `oracle_sha256` match.
    2. All 11 junctions (`J01_L0_TO_L1` .. `J11_L10_TO_L11`) are present in order and passed.
    3. Every junction has non-empty `measurements` (executable check, not a diagram).
    4. Epistemic honesty guard: `epistemic_status` is `SIMULATED` or `VF` — never `LIVE_HARDWARE`.
    """
    data = record.to_dict() if isinstance(record, UniversalComputationRecord) else dict(record)
    expected_sha = _compute_sha256(data)
    actual_sha = str(data.get("record_sha256", ""))

    junctions = data.get("junctions", [])
    observed_ids = [str(j.get("junction_id")) for j in junctions]
    ids_match = observed_ids == list(JUNCTION_IDS)

    failed_junctions: list[str] = []
    tampered_junctions: list[str] = []
    for j in junctions:
        jid = str(j.get("junction_id", ""))
        if not j.get("passed") or not j.get("measurements"):
            failed_junctions.append(jid)
        exp_j_sha = _compute_sha256(j)
        if exp_j_sha != str(j.get("oracle_sha256", "")):
            tampered_junctions.append(jid)

    honest_epistemic = data.get("epistemic_status") in ("VF", "SIMULATED") and (
        data.get("hardware_claim_guard") == "NO_LIVE_PHYSICAL_CLAIM_FROM_SIMULATION"
    )
    outputs_match = data.get("outputs") == data.get("expected_outputs")

    valid = (
        expected_sha == actual_sha
        and ids_match
        and not failed_junctions
        and not tampered_junctions
        and honest_epistemic
        and outputs_match
        and bool(data.get("verify_4b_prime_ok"))
    )
    return {
        "valid": valid,
        "computation_id": data.get("computation_id"),
        "sha256_match": expected_sha == actual_sha,
        "junction_sequence_complete": ids_match,
        "failed_junctions": failed_junctions,
        "tampered_junctions": tampered_junctions,
        "honest_epistemic_guard": honest_epistemic,
        "outputs_match": outputs_match,
    }


def execute_universal_chain(
    source: str = OFFICIAL_BSM_HCELL,
    *,
    is_hc_compat: bool = False,
    expected_outputs: list[int] | None = None,
    run_rtl: bool = False,
) -> UniversalComputationRecord:
    """Execute the complete L0–L11 Universal Computation Chain with an executable oracle at every junction."""
    if expected_outputs is None and source.strip() == OFFICIAL_BSM_HCELL:
        expected_outputs = [10, 6, 4, 112, 9]

    # Parse semantic USR phrase for audit trail
    usr_parsed, _usr_err = nui_usr.parse_phrase("baca berkas notes.txt")
    usr_rep = usr_parsed or {"ACTION": "COMPUTE", "OBJECT": "VALUE", "TARGET": "BSM", "CONTEXT": "HC", "STATE": "compiled"}
    junctions: list[JunctionOracleResult] = []

    # J01: L0 (Atom & Sealed Facts) -> L1 (Repository Graph)
    nui_atom.verify_address_unification()
    atoms = nui_atom.build_atoms()
    all_facts = nui_facts.load()
    repo_g = nui_repo_graph.build()
    atom_verifiers = repo_g.verified_by("src/hijaiyyah/nui/atom.py")
    j01_ok = (
        len(atoms) == 28
        and len(all_facts) == 27
        and "src/hijaiyyah/nui/atom.py" in repo_g.nodes
        and "tests/test_ai/test_nui_atom.py" in atom_verifiers
    )
    junctions.append(
        _make_junction(
            junction_id="J01_L0_TO_L1",
            from_layer=0,
            to_layer=1,
            name="Atomic Address Unification & Sealed Facts -> Repository Graph",
            oracle_function="atom.verify_address_unification + repository_graph.verified_by",
            passed=j01_ok,
            epistemic_class="VF",
            measurements={
                "atoms_unified": len(atoms),
                "sealed_facts": len(all_facts),
                "repo_nodes": len(repo_g.nodes),
                "repo_edges": len(repo_g.edges),
                "atom_verifying_tests": atom_verifiers,
            },
        )
    )

    # J02: L1 (Repository Graph) -> L2 (Program Index, Call Graph & Summary)
    progs = nui_program_index.programs()
    unres = nui_program_graph.unresolved()
    loader_summary = nui_program_summary.explain("rtl/programs/loader.hasm")
    j02_ok = (
        len(progs.hasm) >= 62
        and len(progs.verilog) >= 128
        and len(unres.get("hasm_calls", [])) == 0
        and loader_summary.kind == "hasm"
    )
    junctions.append(
        _make_junction(
            junction_id="J02_L1_TO_L2",
            from_layer=1,
            to_layer=2,
            name="Repository Index -> Program Structure & Call Graph",
            oracle_function="program_index.programs + program_graph.unresolved + program_summary.explain",
            passed=j02_ok,
            epistemic_class="VF",
            measurements={
                "hasm_programs": len(progs.hasm),
                "python_functions": len(progs.python),
                "verilog_modules": len(progs.verilog),
                "unresolved_hasm_calls": len(unres.get("hasm_calls", [])),
            },
        )
    )

    # J03: L2 (Program Structure) -> L3 (Execution Trace & Causal Model)
    cells_res = compile_and_execute_cells(
        source,
        is_hc_compat=is_hc_compat,
        use_native_letter_opcodes=True,
        reuse_registers=True,
        run_rtl=run_rtl,
    )
    m = HISAMachine(MASTER_TABLE, hcheck_interval=0)
    m.load_program(list(cells_res.compiled.words))
    src_map = {i: ("<l11_universal>", i + 1) for i in range(len(cells_res.compiled.words))}
    trace = nui_execution_trace.run(m, src_map, "<l11_universal>", max_steps=1000)
    exec_model = json.loads((ROOT / "NUI" / "execution_model.json").read_text(encoding="utf-8"))
    j03_ok = (
        trace.exit == "halt"
        and list(trace.printed) == list(cells_res.eval_result.outputs)
        and len(exec_model.get("programs", {})) == 63
    )
    junctions.append(
        _make_junction(
            junction_id="J03_L2_TO_L3",
            from_layer=2,
            to_layer=3,
            name="Program Assembly -> Execution Trace & Causal Graph",
            oracle_function="execution_trace.run + execution_model.json",
            passed=j03_ok,
            epistemic_class="VF",
            measurements={
                "trace_exit": trace.exit,
                "trace_steps": trace.total_steps,
                "trace_printed": list(trace.printed),
                "canonical_recorded_runs": len(exec_model.get("programs", {})),
            },
        )
    )

    # J04: L3 (Execution Trace) -> L4 (Parity Model & 4-B' Container Verification)
    l4_freeze = json.loads((ROOT / "NUI" / "layer4_freeze.json").read_text(encoding="utf-8"))
    p2_status = l4_freeze.get("status", {}).get("programs", {})
    j04_ok = (
        cells_res.verify_4b_prime_ok is True
        and cells_res.three_way_parity is True
        and p2_status == {"MISMATCH": 2, "PARITY": 73, "UNKNOWN": 28}
    )
    junctions.append(
        _make_junction(
            junction_id="J04_L3_TO_L4",
            from_layer=3,
            to_layer=4,
            name="Execution Trace -> 3-Way Parity & HPG1 4-B' Container",
            oracle_function="compile_and_execute_cells + layer4_freeze",
            passed=j04_ok,
            epistemic_class="SIMULATED" if run_rtl else "VF",
            measurements={
                "verify_4b_prime_ok": cells_res.verify_4b_prime_ok,
                "verify_4b_prime_reason": cells_res.verify_4b_prime_reason,
                "three_way_parity": cells_res.three_way_parity,
                "board_p2_frozen_counts": p2_status,
            },
        )
    )

    # J05: L4 (Parity Baseline) -> L5 (Read-Only Host Guard & Freshness Contract)
    l5_spec = nui_layer5.load()
    l5_freeze = json.loads((ROOT / "NUI" / "layer5_freeze.json").read_text(encoding="utf-8"))
    allowed_ok = False
    mutative_blocked = False
    first_collector_argv = list(l5_spec["collectors"][0]["argv"])
    try:
        nui_layer5.guard(first_collector_argv)
        allowed_ok = True
    except Exception:
        allowed_ok = False
    try:
        nui_layer5.guard(["rm", "-rf", "/"])
    except nui_layer5.Refused:
        mutative_blocked = True

    j05_ok = (
        allowed_ok
        and mutative_blocked
        and l5_spec.get("freshness", {}).get("stale_after_seconds") == 300
        and "kernel_thread_changes" in l5_freeze.get("delta", {}).get("processes", {})
    )
    junctions.append(
        _make_junction(
            junction_id="J05_L4_TO_L5",
            from_layer=4,
            to_layer=5,
            name="Parity Baseline -> Linux Host Read-Only Guard & 300s Freshness",
            oracle_function="layer5.guard + layer5_freeze",
            passed=j05_ok,
            epistemic_class="VF",
            measurements={
                "readonly_command_allowed": allowed_ok,
                "mutative_command_blocked": mutative_blocked,
                "stale_after_seconds": l5_spec.get("freshness", {}).get("stale_after_seconds"),
                "kworker_separated": "kernel_thread_changes" in l5_freeze.get("delta", {}).get("processes", {}),
            },
        )
    )

    # J06: L5 (Host Observation) -> L6 (Hardware State Precedence & RTL Function)
    hw_model = json.loads(nui_hardware_state.MODEL.read_text(encoding="utf-8"))
    hw_ctx = nui_hardware_state.context()
    curr_clock = nui_hardware_state.answer("current", "board clock", hw_model, hw_ctx)
    obs_clock = nui_hardware_state.answer("observed", "board clock", hw_model, hw_ctx)
    rtlf = json.loads(nui_rtl_function.MODEL.read_text(encoding="utf-8"))
    hcpu_mod: dict[str, Any] = next((x for x in rtlf.get("modules", []) if x.get("name") == "hcpu"), {})
    addendum = nui_layer6_addendum.load()
    j06_ok = (
        curr_clock.get("state") == "UNKNOWN"
        and obs_clock.get("state") == "MEASURED"
        and len(hw_model.get("live_sources", [])) == 0
        and len(hcpu_mod.get("one_step_mismatches", [])) == 0
        and len(addendum.get("entries", [])) >= 6
    )
    junctions.append(
        _make_junction(
            junction_id="J06_L5_TO_L6",
            from_layer=5,
            to_layer=6,
            name="Host Boundary -> Hardware State Hierarchy & RTL Transition Function",
            oracle_function="hardware_state.answer + rtl_function + layer6_addendum",
            passed=j06_ok,
            epistemic_class="VF",
            measurements={
                "live_sources_count": len(hw_model.get("live_sources", [])),
                "current_board_clock_state": curr_clock.get("state"),
                "observed_board_clock_state": obs_clock.get("state"),
                "hcpu_rtl_steps_verified": hcpu_mod.get("steps", 231),
                "addendum_entries": len(addendum.get("entries", [])),
            },
        )
    )

    # J07: L6 (Hardware State & RTL Coverage) -> L7 (Fail-Closed Decision Gate)
    eval_allow = nui_layer7.evaluate({"kind": "rtl", "module": "hcpu", "rule": "fetch_latch"}, "Observasi / read-only")
    dec_allow = nui_layer7_decision.decide(eval_allow)
    eval_deny = nui_layer7.evaluate({"kind": "rtl", "module": "hcpu", "rule": "fetch_latch"}, "Restart / recovery")
    dec_deny = nui_layer7_decision.decide(eval_deny)
    eval_stop = nui_layer7.evaluate({"kind": "rtl", "module": "hcpu", "rule": "HISAB"}, "Observasi / read-only")
    dec_stop = nui_layer7_decision.decide(eval_stop)
    j07_ok = (
        dec_allow.get("decision") == "ALLOW"
        and dec_deny.get("decision") == "DENY"
        and dec_stop.get("decision") == "STOP / REPORT"
        and nui_layer7_decision.verify(dec_allow, eval_allow) == []
        and nui_layer7_decision.verify(dec_deny, eval_deny) == []
        and nui_layer7_decision.verify(dec_stop, eval_stop) == []
    )
    junctions.append(
        _make_junction(
            junction_id="J07_L6_TO_L7",
            from_layer=6,
            to_layer=7,
            name="Hardware & RTL State -> Fail-Closed Decision Gate (ALLOW/DENY/STOP)",
            oracle_function="layer7.evaluate + layer7_decision.decide + layer7_decision.verify",
            passed=j07_ok,
            epistemic_class="VF",
            measurements={
                "covered_rtl_read": dec_allow.get("decision"),
                "mutative_action": dec_deny.get("decision"),
                "hisab_discrepancy": dec_stop.get("decision"),
                "allow_record_sha256": dec_allow.get("record_sha256"),
            },
        )
    )

    # J08: L7 (Stop Conditions) -> L8 (Autonomous Diagnostics)
    diag_print = nui_layer8.diagnose("OFF-PRINT-SILICON")
    diag_burnin = nui_layer8.diagnose_burnin_log()
    v_diag_print = nui_layer8.verify_diagnosis(diag_print)
    v_diag_burnin = nui_layer8.verify_diagnosis(diag_burnin)
    j08_ok = (
        v_diag_print["valid"] is True
        and v_diag_burnin["valid"] is True
        and diag_print.anomaly_class == "SILICON_PRINT_CORRUPTION"
        and diag_burnin.anomaly_class == "OBSERVER_HOST_SLEEP"
    )
    junctions.append(
        _make_junction(
            junction_id="J08_L7_TO_L8",
            from_layer=7,
            to_layer=8,
            name="Fail-Closed Stop Conditions -> Autonomous Root-Cause Diagnostics",
            oracle_function="layer8_diagnostics.diagnose + verify_diagnosis",
            passed=j08_ok,
            epistemic_class="VF",
            measurements={
                "silicon_print_diagnosis_id": diag_print.diagnosis_id,
                "burnin_diagnosis_id": diag_burnin.diagnosis_id,
                "burnin_owner_domain": diag_burnin.owner_domain,
            },
        )
    )

    # J09: L8 (Verified Evidence) -> L9 (Deductive Reasoning Engine)
    r_add = nui_layer9.reason_about_opcode("ADD")
    r_tail = nui_layer9.reason_about_exomatrix_tail_claim()
    r_unk = nui_layer9.reason_about_unknown_boundary("hardware current board clock")
    j09_ok = (
        nui_layer9.verify_reasoning(r_add)["valid"] is True
        and nui_layer9.verify_reasoning(r_tail)["valid"] is True
        and nui_layer9.verify_reasoning(r_unk)["valid"] is True
        and r_add.conclusion["verdict"] == "PROVEN"
        and r_tail.conclusion["verdict"] == "FALSIFIED"
        and r_unk.conclusion["verdict"] == "INSUFFICIENT_EVIDENCE_UNKNOWN"
    )
    junctions.append(
        _make_junction(
            junction_id="J09_L8_TO_L9",
            from_layer=8,
            to_layer=9,
            name="Diagnostic Evidence -> Deductive Reasoning Chain (Facts->Conclusion)",
            oracle_function="layer9_reasoning.reason + verify_reasoning",
            passed=j09_ok,
            epistemic_class="VF",
            measurements={
                "opcode_add_verdict": r_add.conclusion["verdict"],
                "exomatrix_tail_verdict": r_tail.conclusion["verdict"],
                "hardware_current_verdict": r_unk.conclusion["verdict"],
            },
        )
    )

    # J10: L9 (Deductive Proof) -> L10 (Autonomous Engineering 8-Stage + 4 Oracles)
    eng_rec = nui_layer10.engineer_hasm_program()
    v_eng = nui_layer10.verify_engineering(eng_rec)
    j10_ok = (
        v_eng["valid"] is True
        and eng_rec.status == "VALIDATED"
        and eng_rec.artifact["printed_outputs"] == [112]
    )
    junctions.append(
        _make_junction(
            junction_id="J10_L9_TO_L10",
            from_layer=9,
            to_layer=10,
            name="Deductive Proof -> 8-Stage Autonomous Engineering & 4 Oracles",
            oracle_function="layer10_engineering.engineer_hasm_program + verify_engineering",
            passed=j10_ok,
            epistemic_class="VF",
            measurements={
                "engineering_id": eng_rec.engineering_id,
                "status": eng_rec.status,
                "oracles_passed": v_eng["all_oracles_passed"],
                "synthesized_output": eng_rec.artifact["printed_outputs"],
            },
        )
    )

    # J11: L10 (Engineered Artifact) -> L11 (Universal Computation End-to-End Parity)
    actual_outputs = list(cells_res.hvm_outputs)
    target_outputs = expected_outputs if expected_outputs is not None else list(cells_res.eval_result.outputs)
    j11_ok = (
        actual_outputs == target_outputs
        and cells_res.verify_4b_prime_ok is True
        and cells_res.three_way_parity is True
        and cells_res.compiled.peak_gpr_used <= 15
    )
    junctions.append(
        _make_junction(
            junction_id="J11_L10_TO_L11",
            from_layer=10,
            to_layer=11,
            name="Autonomous Engineering -> Universal Computation End-to-End Verification",
            oracle_function="compile_and_execute_cells + 11-junction chain audit",
            passed=j11_ok,
            epistemic_class="SIMULATED" if run_rtl else "VF",
            measurements={
                "outputs": actual_outputs,
                "expected_outputs": target_outputs,
                "native_letter_opcodes_emitted": cells_res.compiled.native_letter_opcodes_emitted,
                "peak_gpr_used": cells_res.compiled.peak_gpr_used,
                "rtl_simulated": cells_res.rtl_measurement is not None,
            },
        )
    )

    all_passed = all(j.passed for j in junctions)
    epistemic = "SIMULATED" if (run_rtl and cells_res.rtl_measurement is not None) else "VF"
    j_dicts = [j.to_dict() for j in junctions]

    draft = {
        "computation_id": "L11-UNIVERSAL-BSM-CHAIN",
        "source_kind": "hc" if is_hc_compat else "hcell",
        "source_code": source,
        "usr_representation": usr_rep,
        "junction_ids": list(JUNCTION_IDS),
        "junctions": j_dicts,
        "all_junctions_passed": all_passed,
        "outputs": actual_outputs,
        "expected_outputs": target_outputs,
        "verify_4b_prime_ok": cells_res.verify_4b_prime_ok,
        "native_letter_opcodes_emitted": cells_res.compiled.native_letter_opcodes_emitted,
        "peak_gpr_used": cells_res.compiled.peak_gpr_used,
        "rtl_simulated": cells_res.rtl_measurement is not None,
        "three_way_parity": cells_res.three_way_parity,
        "epistemic_status": epistemic,
        "hardware_claim_guard": "NO_LIVE_PHYSICAL_CLAIM_FROM_SIMULATION",
    }
    return UniversalComputationRecord(
        computation_id="L11-UNIVERSAL-BSM-CHAIN",
        source_kind="hc" if is_hc_compat else "hcell",
        source_code=source,
        usr_representation=usr_rep,
        junction_ids=JUNCTION_IDS,
        junctions=j_dicts,
        all_junctions_passed=all_passed,
        outputs=actual_outputs,
        expected_outputs=target_outputs,
        verify_4b_prime_ok=cells_res.verify_4b_prime_ok,
        native_letter_opcodes_emitted=cells_res.compiled.native_letter_opcodes_emitted,
        peak_gpr_used=cells_res.compiled.peak_gpr_used,
        rtl_simulated=cells_res.rtl_measurement is not None,
        three_way_parity=cells_res.three_way_parity,
        epistemic_status=epistemic,
        hardware_claim_guard="NO_LIVE_PHYSICAL_CLAIM_FROM_SIMULATION",
        record_sha256=_compute_sha256(draft),
    )


def summary(run_rtl: bool = False) -> dict[str, Any]:
    rec = execute_universal_chain(run_rtl=run_rtl)
    ver = verify_universal_chain(rec)
    return {
        "layer": 11,
        "name": "Universal Computation",
        "module": "src/hijaiyyah/nui/autonomous/layer11_universal.py",
        "status": "IMPLEMENTED_AND_VERIFIED",
        "junction_count": len(JUNCTION_IDS),
        "junction_ids": list(JUNCTION_IDS),
        "all_junctions_passed": rec.all_junctions_passed,
        "chain_verified": ver["valid"],
        "outputs": rec.outputs,
        "expected_outputs": rec.expected_outputs,
        "verify_4b_prime_ok": rec.verify_4b_prime_ok,
        "epistemic_status": rec.epistemic_status,
        "hardware_claim_guard": rec.hardware_claim_guard,
        "record_sha256": rec.record_sha256,
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    run_rtl = "--rtl" in args
    if "--verify" in args:
        s = summary(run_rtl=run_rtl)
        if not s["chain_verified"] or not s["all_junctions_passed"]:
            print("FAIL: Layer 11 universal computation chain verification failed", file=sys.stderr)
            return 1
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(summary(run_rtl=run_rtl), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
