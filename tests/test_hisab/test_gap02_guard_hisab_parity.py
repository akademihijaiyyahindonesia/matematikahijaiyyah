"""
GAP-02 Verification: Canonical Guard & HISAB Parity Across Python, RTL Guard,
RTL HISAB, and Integrated HCPU Simulation.

Verifies that rtl/hcpu_hisab.v derives its guard_status strictly from the
canonical rtl/hcpu_guard.v (R1 — one truth, one place), with:
  1. Zero duplicate U, rho, or sum_n/sum_k/sum_q formulas in hcpu_hisab.v.
  2. Removal of the obsolete is_kaf override in hcpu_hisab.v.
  3. Full-width (10/11/12-bit) arithmetic without 8-bit truncation aliasing.
  4. Canonical coupled H* enforcement (H* == Ka and 2*H* <= Theta_hat).
  5. Strict invariant: (guard_status == 0x3F) <=> (guard_pass == 1) across all
     valid, invalid, Kaf, boundary, overflow/signedness, G1-G4, T1-T2, and H*
     test vectors in both standalone RTL and integrated HCPU pipeline execution.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

import pytest

from hijaiyyah.core.guards import compute_rho, compute_U, full_guard_check
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.machine import ROM_NEGATIVE_VECTORS

ROOT = Path(__file__).resolve().parents[2]
RTL_DIR = ROOT / "rtl"
HISAB_V = RTL_DIR / "hcpu_hisab.v"
GUARD_V = RTL_DIR / "hcpu_guard.v"


def canonical_guard_eval(vec: Sequence[int]) -> Tuple[bool, int, int, int]:
    """
    Evaluate canonical HCPU guard contract on an 18-component vector (each 0..255):
      Returns (guard_pass, guard_status_byte, u_val, rho_signed).
    """
    v = [int(x) & 0xFF for x in vec]
    fg = full_guard_check(v)
    g1 = int(fg["G1"])
    g2 = int(fg["G2"])
    g3 = int(fg["G3"])
    g4 = int(fg["G4"])
    t1 = int(fg["T1"])
    t2 = int(fg["T2"])
    hstar_ok = (v[17] == v[7]) and (v[17] <= (v[0] >> 1))
    guard_pass = bool(g1 and g2 and g3 and g4 and t1 and t2 and hstar_ok)
    raw6 = (t2 << 5) | (t1 << 4) | (g4 << 3) | (g3 << 2) | (g2 << 1) | g1
    guard_status = 0x00 if (raw6 == 0x3F and not guard_pass) else raw6
    u_val = compute_U(v)
    rho_val = compute_rho(v)
    return guard_pass, guard_status, u_val, rho_val


def pack_vec_144_hex(vec: List[int]) -> str:
    """Format 18x8-bit vector as 144-bit Verilog hex literal (c[17] MSB .. c[0] LSB)."""
    val = 0
    for idx, comp in enumerate(vec):
        val |= (int(comp) & 0xFF) << (8 * idx)
    return f"144'h{val:036X}"


def test_hcpu_hisab_contains_no_duplicate_guard_formulas_or_is_kaf() -> None:
    """R1 & GAP-02 static verification: hcpu_hisab.v instantiates hcpu_guard and
    contains no independent U_val, sum_n/k/q, or is_kaf override in active RTL."""
    raw = HISAB_V.read_text(encoding="utf-8")
    code_only = "\n".join(
        line.split("//", 1)[0] for line in raw.splitlines()
    )
    assert "hcpu_guard" in code_only, "hcpu_hisab.v must instantiate canonical hcpu_guard"
    for forbidden in ("is_kaf", "sum_n", "sum_k", "sum_q", "U_val"):
        assert forbidden not in code_only, (
            f"Duplicate formula or legacy exception '{forbidden}' still present in hcpu_hisab.v"
        )


def test_Comprehensive_Vectors_Python_vs_RTL_Guard_vs_RTL_HISAB() -> None:
    """
    Build and run an Icarus Verilog testbench comparing Python canonical reference,
    rtl/hcpu_guard.v, and rtl/hcpu_hisab.v across 46 comprehensive vectors:
      - Vectors 0..27: All 28 canonical Hijaiyyah letters (Alif..Ya, including Kaf #22)
      - Vectors 28..33: All 6 ROM negative test vectors (indices 31..36: G4, G1, G2, G3, T1, T2)
      - Vector 34: Corrupt legacy is_kaf vector (Theta=2, Kc=1, Qc=0, AK=1, AQ=0, H*=0) -> T2 fail
      - Vector 35: G1 8-bit truncation overflow (Na=200, Nb=56, Nd=0, AN=0 -> sum_n=256) -> G1 fail
      - Vector 36: G2 8-bit truncation overflow (Kp=200, Kx=56, AK=0 -> sum_k=256) -> G2 fail
      - Vector 37: G3 8-bit truncation overflow (Qp=200, Qx=56, AQ=0 -> sum_q=256) -> G3 fail
      - Vector 38: G4 8-bit truncation overflow on U (Theta=0, Qc=64, AQ=64 -> U=256, rho=-256) -> G4 fail
      - Vector 39: G4 maximum valid boundary (Theta=255, Qx=255, AQ=255 -> U=255, rho=0) -> PASS
      - Vector 40: G4 signed negative boundary (Theta=254, Qx=255, AQ=255 -> U=255, rho=-1) -> G4 fail
      - Vector 41: H* violation H* != Ka (Theta=4, Kp=1, AK=1, H*=1, Ka=0) -> H* fail (status=0x00)
      - Vector 42: H* violation H*=0 when Ka=1 (Theta=4, Ka=1, AK=1, H*=0) -> H* fail (status=0x00)
      - Vector 43: H* violation 2*H* > Theta_hat (Theta=1, Ka=1, AK=1, H*=1) -> H* fail (status=0x00)
      - Vector 44: H* valid upper boundary 2*H* == Theta_hat (Theta=4, Ka=2, AK=2, H*=2) -> PASS
      - Vector 45: Monoid identity all-zero vector -> PASS
    """
    vectors: List[Tuple[str, List[int]]] = []

    # 1. All 28 canonical letters (including Kaf at index 22)
    for entry in MASTER_TABLE.all_entries():
        vectors.append((f"Letter_{entry.index:02d}_{entry.name}", list(entry.vector)))

    # 2. All 6 ROM negative vectors (indices 31..36)
    for rom_idx, (vec_tuple, tag) in sorted(ROM_NEGATIVE_VECTORS.items()):
        vectors.append((f"ROM_Neg_{rom_idx}_{tag}", list(vec_tuple)))

    # 3. Legacy corrupt is_kaf vector: Theta=2, Kc=1, Qc=0, AK=1, AQ=0, H*=0
    vectors.append(("Corrupt_Legacy_is_kaf_T2_Fail", [2, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0]))

    # 4. 8-bit truncation overflow vectors (sum = 256, low 8 bits = 0)
    vectors.append(("Overflow_G1_sumN_256_AN_0", [0, 200, 56, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]))
    vectors.append(("Overflow_G2_sumK_256_AK_0", [0, 0, 0, 0, 200, 56, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]))
    vectors.append(("Overflow_G3_sumQ_256_AQ_0", [200, 0, 0, 0, 0, 0, 0, 0, 0, 200, 56, 0, 0, 0, 0, 0, 0, 0]))
    vectors.append(("Overflow_G4_U_256_Theta_0", [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 64, 0, 0, 64, 0]))

    # 5. Arithmetic & signedness boundaries
    vectors.append(("Boundary_G4_U_255_Theta_255_rho_0", [255, 0, 0, 0, 0, 0, 0, 0, 0, 0, 255, 0, 0, 0, 0, 0, 255, 0]))
    vectors.append(("Boundary_G4_U_255_Theta_254_rho_neg1", [254, 0, 0, 0, 0, 0, 0, 0, 0, 0, 255, 0, 0, 0, 0, 0, 255, 0]))

    # 6. Coupled H* structural guard vectors
    vectors.append(("HStar_Fail_H1_Ka0", [4, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1]))
    vectors.append(("HStar_Fail_H0_Ka1", [4, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0]))
    vectors.append(("HStar_Fail_2H_gt_Theta", [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1]))
    vectors.append(("HStar_Pass_2H_eq_Theta", [4, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 2]))
    vectors.append(("Monoid_Zero_Identity", [0] * 18))

    tb_lines = [
        '`include "hcpu_pkg.vh"',
        "module tb_gap02;",
        "    reg  [143:0] vec_in;",
        "    wire         guard_pass;",
        "    wire         g1, g2, g3, g4, t1, t2;",
        "    wire [31:0]  u_val, rho_val;",
        "    wire [31:0]  pack0, pack1, pack2, crc_out;",
        "    wire [7:0]   guard_status;",
        "    wire         done;",
        "    integer      fails;",
        "",
        "    hcpu_guard #(.PIPELINE_GUARD(0)) u_guard (",
        "        .clk(1'b0), .rst_n(1'b1), .vec(vec_in),",
        "        .guard_pass(guard_pass), .g1_pass(g1), .g2_pass(g2),",
        "        .g3_pass(g3), .g4_pass(g4), .t1_pass(t1), .t2_pass(t2),",
        "        .u_value(u_val), .rho_value(rho_val)",
        "    );",
        "",
        "    hcpu_hisab u_hisab (",
        "        .op(2'd0), .vec_in(vec_in), .gpr_s1(32'd0), .gpr_s2(32'd0),",
        "        .extra_byte(8'd0), .pack_word0(pack0), .pack_word1(pack1),",
        "        .pack_word2(pack2), .guard_status(guard_status),",
        "        .crc_out(crc_out), .done(done)",
        "    );",
        "",
        "    initial begin",
        "        fails = 0;",
    ]

    for idx, (label, vec) in enumerate(vectors):
        exp_pass, exp_status, exp_u, exp_rho = canonical_guard_eval(vec)
        exp_rho_u32 = exp_rho & 0xFFFFFFFF
        v_hex = pack_vec_144_hex(vec)
        tb_lines.extend([
            f"        // Case {idx}: {label}",
            f"        vec_in = {v_hex}; #1;",
            f"        if (guard_pass !== 1'b{int(exp_pass)} || guard_status !== 8'h{exp_status:02X} || "
            f"u_val !== 32'd{exp_u} || rho_val !== 32'h{exp_rho_u32:08X} || "
            f"((guard_status == 8'h3F) !== guard_pass) || pack2[15:8] !== guard_status) begin",
            f'            $display("FAIL {label}: pass=%b(exp %b) status=0x%02X(exp 0x%02X) u=%0d rho=%0d", '
            f"guard_pass, 1'b{int(exp_pass)}, guard_status, 8'h{exp_status:02X}, u_val, $signed(rho_val));",
            "            fails = fails + 1;",
            "        end",
        ])

    tb_lines.extend([
        '        if (fails == 0) $display("GAP02_PARITY_PASS: %0d/46 vectors verified", 46);',
        '        else $fatal(1, "GAP02_PARITY_FAIL: %0d failures", fails);',
        "        $finish(0);",
        "    end",
        "endmodule",
    ])

    with tempfile.TemporaryDirectory() as tmp:
        tb_file = Path(tmp) / "tb_gap02.v"
        vvp_file = Path(tmp) / "tb_gap02.vvp"
        tb_file.write_text("\n".join(tb_lines), encoding="utf-8")
        comp = subprocess.run(
            ["/opt/homebrew/bin/iverilog", "-g2012", "-I", str(RTL_DIR),
             "-o", str(vvp_file), str(tb_file), str(GUARD_V), str(HISAB_V)],
            capture_output=True, text=True, check=True,
        )
        assert comp.returncode == 0, comp.stderr
        sim = subprocess.run(
            ["/opt/homebrew/bin/vvp", str(vvp_file)],
            capture_output=True, text=True, check=True,
        )
        assert "GAP02_PARITY_PASS: 46/46 vectors verified" in sim.stdout, sim.stdout


def test_HCPU_Integrated_Pipeline_Guard_and_HISAB_Consistency() -> None:
    """
    Run integrated HCPU pipeline (hcpu_top) with a program that tests:
      1. Canonical Kaf (HLOAD #22): HGRD sets FLAG_G=1, HPACK word2[15:8] == 0x3F
      2. Corrupt legacy is_kaf constructed via CZERO + CSET (Theta=2, Kc=1, Qc=0, AK=1):
         HGRD sets FLAG_G=0, HPACK word2[15:8] == 0x1F (!= 0x3F)
      3. 8-bit U overflow (Theta=0, Qc=64, AQ=64 -> U=256):
         HGRD sets FLAG_G=0, HPACK word2[15:8] == 0x37 (!= 0x3F), CU=256, CRHO=-256
      4. H* violation (Theta=4, Kp=1, AK=1, H*=1, Ka=0):
         HGRD sets FLAG_G=0, HPACK word2[15:8] == 0x00 (!= 0x3F)
    """
    from hijaiyyah.hisa.assembler import assemble

    prog_src = """
        ; Case 1: Canonical Kaf (index 22)
        HLOAD   H1, #22
        HGRD    H1
        FRD     R1              ; R1 = 1 (FLAG_G = 1)
        HPACK   R2, H1, R2      ; id_s2=2 -> pack_word2 (0x00003F01 -> guard_status = 0x3F)

        ; Case 2: Legacy corrupt is_kaf (Theta=2, Kc=1, Qc=0, AK=1, AQ=0, H*=0)
        CZERO   H2
        MOVI    R0, #2
        CSET    H2, R0, #0      ; Theta = 2
        MOVI    R0, #1
        CSET    H2, R0, #8      ; Kc = 1
        CSET    H2, R0, #15     ; AK = 1
        HGRD    H2
        FRD     R3              ; R3 = 0 (FLAG_G = 0)
        HPACK   R4, H2, R2      ; id_s2=2 -> 0x00001F00 (guard_status = 0x1F, T2=0)

        ; Case 3: 8-bit U truncation overflow (Theta=0, Qc=64, AQ=64 -> U=256)
        CZERO   H3
        MOVI    R0, #64
        CSET    H3, R0, #13     ; Qc = 64
        CSET    H3, R0, #16     ; AQ = 64
        HGRD    H3
        FRD     R5              ; R5 = 0 (FLAG_G = 0)
        HPACK   R6, H3, R2      ; id_s2=2 -> 0x00003700 (guard_status = 0x37, G4=0)
        CU      R7, H3          ; R7 = 256
        CRHO    R8, H3          ; R8 = -256 (0xFFFFFF00)

        ; Case 4: H* violation (Theta=4, Kp=1, AK=1, H*=1, Ka=0)
        CZERO   H4
        MOVI    R0, #4
        CSET    H4, R0, #0      ; Theta = 4
        MOVI    R0, #1
        CSET    H4, R0, #4      ; Kp = 1
        CSET    H4, R0, #15     ; AK = 1
        CSET    H4, R0, #17     ; H* = 1 (while Ka = 0)
        HGRD    H4
        FRD     R9              ; R9 = 0 (FLAG_G = 0)
        HPACK   R10, H4, R2     ; id_s2=2 -> 0x00000001 (guard_status = 0x00, gated by H*)
        HALT
    """
    words = assemble(prog_src)

    tb_top_lines = [
        '`include "hcpu_pkg.vh"',
        "module tb_gap02_top;",
        "    reg clk = 0;",
        "    always #5 clk = ~clk;",
        "    reg rst_n = 0;",
        "    wire [11:0] imem_addr;",
        "    wire        imem_ce;",
        "    reg  [31:0] imem_data;",
        "    wire        halted, guard_led, uart_tx;",
        "    reg  [4:0]  dbg_addr = 0;",
        "    wire [31:0] dbg_data;",
        "    wire [7:0]  dbg_flags;",
        "    reg  [31:0] rom [0:63];",
        "    integer i;",
        "",
        "    hcpu_top #(.USE_DSP(0), .CODEX_PROFILE(2)) u_dut (",
        "        .clk(clk), .rst_n(rst_n),",
        "        .imem_addr(imem_addr), .imem_ce(imem_ce), .imem_data(imem_data),",
        "        .imem_we(), .imem_waddr(), .imem_wdata(),",
        "        .uart_rx(1'b1), .uart_tx(uart_tx), .halted(halted), .guard_led(guard_led),",
        "        .sd_clk(), .sd_cmd_out(), .sd_cmd_oe(), .sd_cmd_in(1'b1),",
        "        .sd_dat_out(), .sd_dat_oe(), .sd_dat_in(1'b1),",
        "        .dbg_gpr_raddr(dbg_addr), .dbg_gpr_rdata(dbg_data), .dbg_flags(dbg_flags)",
        "    );",
        "",
        "    always @(posedge clk) if (imem_ce) imem_data <= rom[imem_addr[5:0]];",
        "",
        "    initial begin",
        "        for (i = 0; i < 64; i = i + 1) rom[i] = 32'd0;",
    ]
    for idx, w in enumerate(words):
        tb_top_lines.append(f"        rom[{idx}] = 32'h{w:08X};")

    tb_top_lines.extend([
        "        #20 rst_n = 1;",
        "        for (i = 0; i < 500 && !halted; i = i + 1) @(posedge clk);",
        "        if (!halted) $fatal(1, \"HCPU did not halt\");",
        "        dbg_addr = 5'd1; #1; if ((dbg_data & 1) !== 1) $fatal(1, \"Case 1 R1=%h\", dbg_data);",
        "        dbg_addr = 5'd2; #1; if (dbg_data[15:8] !== 8'h3F) $fatal(1, \"Case 1 R2=%h\", dbg_data);",
        "        dbg_addr = 5'd3; #1; if ((dbg_data & 1) !== 0) $fatal(1, \"Case 2 R3=%h\", dbg_data);",
        "        dbg_addr = 5'd4; #1; if (dbg_data[15:8] !== 8'h1F) $fatal(1, \"Case 2 R4=%h\", dbg_data);",
        "        dbg_addr = 5'd5; #1; if ((dbg_data & 1) !== 0) $fatal(1, \"Case 3 R5=%h\", dbg_data);",
        "        dbg_addr = 5'd6; #1; if (dbg_data[15:8] !== 8'h37) $fatal(1, \"Case 3 R6=%h\", dbg_data);",
        "        dbg_addr = 5'd7; #1; if (dbg_data !== 32'd256) $fatal(1, \"Case 3 R7=%h\", dbg_data);",
        "        dbg_addr = 5'd8; #1; if (dbg_data !== 32'hFFFFFF00) $fatal(1, \"Case 3 R8=%h\", dbg_data);",
        "        dbg_addr = 5'd9; #1; if ((dbg_data & 1) !== 0) $fatal(1, \"Case 4 R9=%h\", dbg_data);",
        "        dbg_addr = 5'd10; #1; if (dbg_data[15:8] !== 8'h00) $fatal(1, \"Case 4 R10=%h\", dbg_data);",
        '        $display("GAP02_HCPU_INTEGRATED_PASS");',
        "        $finish(0);",
        "    end",
        "endmodule",
    ])

    rtl_sources = [str(p) for p in sorted(RTL_DIR.glob("hcpu_*.v"))]
    with tempfile.TemporaryDirectory() as tmp:
        tb_file = Path(tmp) / "tb_gap02_top.v"
        vvp_file = Path(tmp) / "tb_gap02_top.vvp"
        tb_file.write_text("\n".join(tb_top_lines), encoding="utf-8")
        comp = subprocess.run(
            ["/opt/homebrew/bin/iverilog", "-g2012", "-I", str(RTL_DIR),
             "-o", str(vvp_file), str(tb_file), *rtl_sources],
            capture_output=True, text=True, check=True,
        )
        assert comp.returncode == 0, comp.stderr
        sim = subprocess.run(
            ["/opt/homebrew/bin/vvp", str(vvp_file)],
            capture_output=True, text=True, check=True,
        )
        assert "GAP02_HCPU_INTEGRATED_PASS" in sim.stdout, sim.stdout
