// ============================================================================
// HMCL Architectural Alternatives & Paket 8 Three-Profile Verification Bench
// ============================================================================
// Verifies:
//   - Alternative A1: Hardware Sticky Prefix Guard & Coupled H*
//   - Alternative A2 / Paket 8 Three-Profile Codex ALU Architecture:
//       * Profile A (CODEX_PROFILE=0): ASIC Shared 14-Lane MAC
//       * Profile B (CODEX_PROFILE=1): Tang Nano 20K Hard-DSP (14x MULT9X9)
//       * Profile C (CODEX_PROFILE=2): Tang Nano 20K No-DSP (Dedicated 14-Lane
//         Nibble-Split Squarer + 14-Cycle Iterative Shift-Add HDOT)
//   - Exhaustive 65,536 unsigned byte operand pairs (a, b) in [0, 255]^2 for:
//       * abs_diff(a, b) = |a - b|
//       * a^2 (HNRM2)
//       * (a - b)^2 (HDIST)
//       * a * b (HDOT across Profile 0, Profile 1, and 14-cycle Profile 2)
//   - One-hot lane isolation (lanes 0..13 active, lanes 14..17 ignored)
//   - Multi-lane seeded PRNG randomized differential sweep (512 x 14-lane vectors)
//   - Multi-cycle completion (14 cycles), stall hold, and full HCPU pipeline
//     stall handshake for Profile C iterative HDOT
//   - Target capability gating (HDOT_ENABLE=0) and SD_PRESCAN invalid opcode
//     rejection (Alternative A3)
// ============================================================================

`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hmcl_rtl_alternatives;

    reg clk;
    reg rst_n;
    initial clk = 1'b0;
    always #5 clk = ~clk;

    // ── Direct Unit Under Test 1: hcpu_guard (A1 coupled H*) ──────
    reg  [`HREG_W-1:0] u_grd_vec;
    wire               u_grd_pass;
    wire               u_g1, u_g2, u_g3, u_g4, u_t1, u_t2;
    wire [`XLEN-1:0]   u_val, rho_val;

    hcpu_guard #(.PIPELINE_GUARD(0)) u_guard_dut (
        .clk        (1'b0),
        .rst_n      (1'b1),
        .vec        (u_grd_vec),
        .guard_pass (u_grd_pass),
        .g1_pass    (u_g1),
        .g2_pass    (u_g2),
        .g3_pass    (u_g3),
        .g4_pass    (u_g4),
        .t1_pass    (u_t1),
        .t2_pass    (u_t2),
        .u_value    (u_val),
        .rho_value  (rho_val)
    );

    // ── Direct Unit Under Test 2: Three-Profile hcpu_codex_alu ────
    reg  [2:0]         u_alu_op;
    reg  [11:0]        u_alu_idx;
    reg  [`HREG_W-1:0] u_alu_s1, u_alu_s2;
    reg  [`XLEN-1:0]   u_alu_scl;
    reg                u_alu_stall;

    // Profile A: CODEX_PROFILE = 0 (ASIC Shared 14-Lane MAC)
    wire [`HREG_W-1:0] p0_res_vec;
    wire [`XLEN-1:0]   p0_res_scl;
    wire               p0_add_ovf, p0_done;

    hcpu_codex_alu #(
        .USE_DSP       (0),
        .CODEX_PROFILE (0),
        .HDOT_ENABLE   (1)
    ) u_alu_p0_asic (
        .clk        (clk),
        .rst_n      (rst_n),
        .stall      (u_alu_stall),
        .op         (u_alu_op),
        .index      (u_alu_idx),
        .src1       (u_alu_s1),
        .src2       (u_alu_s2),
        .src_scl    (u_alu_scl),
        .result_vec (p0_res_vec),
        .result_scl (p0_res_scl),
        .add_ovf    (p0_add_ovf),
        .done       (p0_done)
    );

    // Profile B: CODEX_PROFILE = 1 (Tang Nano 20K Hard-DSP)
    wire [`HREG_W-1:0] p1_res_vec;
    wire [`XLEN-1:0]   p1_res_scl;
    wire               p1_add_ovf, p1_done;

    hcpu_codex_alu #(
        .USE_DSP       (1),
        .CODEX_PROFILE (1),
        .HDOT_ENABLE   (1)
    ) u_alu_p1_dsp (
        .clk        (clk),
        .rst_n      (rst_n),
        .stall      (u_alu_stall),
        .op         (u_alu_op),
        .index      (u_alu_idx),
        .src1       (u_alu_s1),
        .src2       (u_alu_s2),
        .src_scl    (u_alu_scl),
        .result_vec (p1_res_vec),
        .result_scl (p1_res_scl),
        .add_ovf    (p1_add_ovf),
        .done       (p1_done)
    );

    // Profile C: CODEX_PROFILE = 2 (Tang Nano 20K No-DSP: Squarer + 14-Cycle Iterative HDOT)
    wire [`HREG_W-1:0] p2_res_vec;
    wire [`XLEN-1:0]   p2_res_scl;
    wire               p2_add_ovf, p2_done;

    hcpu_codex_alu #(
        .USE_DSP       (0),
        .CODEX_PROFILE (2),
        .HDOT_ENABLE   (1)
    ) u_alu_p2_nodsp (
        .clk        (clk),
        .rst_n      (rst_n),
        .stall      (u_alu_stall),
        .op         (u_alu_op),
        .index      (u_alu_idx),
        .src1       (u_alu_s1),
        .src2       (u_alu_s2),
        .src_scl    (u_alu_scl),
        .result_vec (p2_res_vec),
        .result_scl (p2_res_scl),
        .add_ovf    (p2_add_ovf),
        .done       (p2_done)
    );

    // Capability-Gated Profile (HDOT_ENABLE = 0)
    wire [`XLEN-1:0]   p2_nohdot_scl;
    wire               p2_nohdot_done;
    hcpu_codex_alu #(
        .USE_DSP       (0),
        .CODEX_PROFILE (2),
        .HDOT_ENABLE   (0)
    ) u_alu_p2_nohdot (
        .clk        (clk),
        .rst_n      (rst_n),
        .stall      (1'b0),
        .op         (u_alu_op),
        .index      (u_alu_idx),
        .src1       (u_alu_s1),
        .src2       (u_alu_s2),
        .src_scl    (u_alu_scl),
        .result_vec (),
        .result_scl (p2_nohdot_scl),
        .add_ovf    (),
        .done       (p2_nohdot_done)
    );

    // Decode Capability Gating (HDOT_ENABLE = 0 vs HDOT_ENABLE = 1)
    reg  [31:0] dec_instr;
    wire        dec_en1_is_codex, dec_en1_gpr_we, dec_en1_is_halt;
    wire [3:0]  dec_en1_dst;
    wire        dec_en0_is_codex, dec_en0_gpr_we, dec_en0_is_halt;
    wire [3:0]  dec_en0_dst;

    hcpu_decode #(.HDOT_ENABLE(1)) u_dec_en1 (
        .clk               (clk),
        .rst_n             (rst_n),
        .stall             (1'b0),
        .flush             (1'b0),
        .if_instruction    (dec_instr),
        .if_pc             (32'd0),
        .gpr_raddr1        (),
        .gpr_raddr2        (),
        .gpr_rdata1        (32'd0),
        .gpr_rdata2        (32'd0),
        .hreg_raddr1       (),
        .hreg_raddr2       (),
        .hreg_rdata1       (144'd0),
        .hreg_rdata2       (144'd0),
        .hreg_ovf_rdata1   (1'b0),
        .hreg_ovf_rdata2   (1'b0),
        .id_opcode         (),
        .id_dst            (dec_en1_dst),
        .id_s1             (),
        .id_s2             (),
        .id_imm            (),
        .id_gpr_s1         (),
        .id_gpr_s2         (),
        .id_hreg_s1        (),
        .id_hreg_s2        (),
        .id_hreg_ovf_s1    (),
        .id_hreg_ovf_s2    (),
        .id_pc             (),
        .id_gpr_we         (dec_en1_gpr_we),
        .id_hreg_we        (),
        .id_mem_read       (),
        .id_mem_write      (),
        .id_is_branch      (),
        .id_is_jump        (),
        .id_is_call        (),
        .id_is_ret         (),
        .id_is_codex       (dec_en1_is_codex),
        .id_is_halt        (dec_en1_is_halt),
        .id_is_print       (),
        .id_is_emits       (),
        .id_is_push        (),
        .id_is_pop         (),
        .ex_mem_read       (1'b0),
        .ex_mem_write      (1'b0),
        .ex_dst            (4'd0),
        .ex_mem_addr       (12'd0),
        .load_use_hazard   (),
        .store_load_hazard ()
    );

    hcpu_decode #(.HDOT_ENABLE(0)) u_dec_en0 (
        .clk               (clk),
        .rst_n             (rst_n),
        .stall             (1'b0),
        .flush             (1'b0),
        .if_instruction    (dec_instr),
        .if_pc             (32'd0),
        .gpr_raddr1        (),
        .gpr_raddr2        (),
        .gpr_rdata1        (32'd0),
        .gpr_rdata2        (32'd0),
        .hreg_raddr1       (),
        .hreg_raddr2       (),
        .hreg_rdata1       (144'd0),
        .hreg_rdata2       (144'd0),
        .hreg_ovf_rdata1   (1'b0),
        .hreg_ovf_rdata2   (1'b0),
        .id_opcode         (),
        .id_dst            (dec_en0_dst),
        .id_s1             (),
        .id_s2             (),
        .id_imm            (),
        .id_gpr_s1         (),
        .id_gpr_s2         (),
        .id_hreg_s1        (),
        .id_hreg_s2        (),
        .id_hreg_ovf_s1    (),
        .id_hreg_ovf_s2    (),
        .id_pc             (),
        .id_gpr_we         (dec_en0_gpr_we),
        .id_hreg_we        (),
        .id_mem_read       (),
        .id_mem_write      (),
        .id_is_branch      (),
        .id_is_jump        (),
        .id_is_call        (),
        .id_is_ret         (),
        .id_is_codex       (dec_en0_is_codex),
        .id_is_halt        (dec_en0_is_halt),
        .id_is_print       (),
        .id_is_emits       (),
        .id_is_push        (),
        .id_is_pop         (),
        .ex_mem_read       (1'b0),
        .ex_mem_write      (1'b0),
        .ex_dst            (4'd0),
        .ex_mem_addr       (12'd0),
        .load_use_hazard   (),
        .store_load_hazard ()
    );

    // ── Direct Unit Under Test 3: Full HCPU Pipeline with Profile C (CODEX_PROFILE=2) ──
    reg         cpu_rst_n;
    wire [11:0] cpu_imem_addr;
    wire        cpu_imem_ce;
    reg  [31:0] cpu_imem_rom [0:31];
    reg  [31:0] cpu_imem_data;
    wire        cpu_halted;
    reg  [4:0]  cpu_dbg_addr;
    wire [31:0] cpu_dbg_data;
    wire [7:0]  cpu_dbg_flags;

    always @(posedge clk) begin
        if (cpu_imem_ce)
            cpu_imem_data <= cpu_imem_rom[cpu_imem_addr[4:0]];
    end

    hcpu_top #(
        .CLK_HZ        (27_000_000),
        .BAUD          (115200),
        .USE_DSP       (0),
        .CODEX_PROFILE (2),
        .HDOT_ENABLE   (1)
    ) u_cpu_profile_c (
        .clk           (clk),
        .rst_n         (cpu_rst_n),
        .imem_addr     (cpu_imem_addr),
        .imem_ce       (cpu_imem_ce),
        .imem_data     (cpu_imem_data),
        .imem_we       (),
        .imem_waddr    (),
        .imem_wdata    (),
        .uart_rx       (1'b1),
        .uart_tx       (),
        .halted        (cpu_halted),
        .guard_led     (),
        .sd_clk        (),
        .sd_cmd_out    (),
        .sd_cmd_oe     (),
        .sd_cmd_in     (1'b1),
        .sd_dat_out    (),
        .sd_dat_oe     (),
        .sd_dat_in     (1'b1),
        .dbg_gpr_raddr (cpu_dbg_addr),
        .dbg_gpr_rdata (cpu_dbg_data),
        .dbg_flags     (cpu_dbg_flags)
    );

    // ── Direct Unit Under Test 4: hcpu_mmio + hcpu_sdio (A3 SD_CSUM & SD_PRESCAN) ──
    reg         mmio_re, mmio_we;
    reg  [11:0] mmio_addr;
    reg  [31:0] mmio_wdata;
    wire [31:0] mmio_rdata;

    hcpu_mmio #(.CLK_HZ(27_000_000), .BAUD(115200)) u_mmio_dut (
        .clk            (clk),
        .rst_n          (rst_n),
        .re             (mmio_re),
        .we             (mmio_we),
        .addr           (mmio_addr),
        .wdata          (mmio_wdata),
        .rdata          (mmio_rdata),
        .ram_re         (),
        .ram_we         (),
        .ram_addr       (),
        .ram_wdata      (),
        .ram_rdata      (32'd0),
        .uart_rx_in     (1'b1),
        .uart_tx_busy   (1'b0),
        .trap_reg_we    (),
        .trap_reg_sel   (),
        .trap_reg_wdata (),
        .trap_reg_rdata (32'd0),
        .src_timer      (),
        .src_uart_rx    (),
        .mem_base       (),
        .mem_limit      (),
        .imem_we        (),
        .imem_waddr     (),
        .imem_wdata     (),
        .sd_clk         (),
        .sd_cmd_out     (),
        .sd_cmd_oe      (),
        .sd_cmd_in      (1'b1),
        .sd_dat_out     (),
        .sd_dat_oe      (),
        .sd_dat_in      (1'b1)
    );

    wire comb_3way_eq = (p0_res_vec === p1_res_vec) && (p1_res_vec === p2_res_vec) &&
                        (p0_res_scl === p1_res_scl) && (p1_res_scl === p2_res_scl) &&
                        (p0_add_ovf === p1_add_ovf) && (p1_add_ovf === p2_add_ovf) &&
                        (p0_done    === 1'b1)       && (p1_done    === 1'b1) &&
                        (p2_done    === 1'b1);

    integer pass_cnt, fail_cnt;
    integer i, a_val, b_val, batch_idx, lane_idx, cyc_cnt;
    integer sq_err_cnt, diff_sq_err_cnt, abs_diff_err_cnt, prod_p01_err_cnt, prod_p2_err_cnt;
    integer rand_err_cnt, onehot_err_cnt;
    reg [31:0] expected_csum, rd_csum, rd_prescan;
    reg [31:0] ref_nrm2, ref_dist, ref_dot, exp_batch_dot;
    reg [31:0] prng_state;
    reg [7:0]  ra, rb;
    integer    diff_ab;

    task check_cond;
        input cond;
        input [255:0] label;
        begin
            if (cond) begin
                pass_cnt = pass_cnt + 1;
            end else begin
                fail_cnt = fail_cnt + 1;
                $display("FAIL: %0s", label);
            end
        end
    endtask

    // Helper: run 14-cycle iterative HDOT on u_alu_p2_nodsp and check done timing
    task run_p2_hdot_14cyc;
        output [31:0] res_out;
        output        timing_ok;
        integer c;
        begin
            u_alu_op    = 3'd6; // ALU_HDOT
            u_alu_stall = 1'b0;
            timing_ok   = 1'b1;
            #1;
            for (c = 0; c < 13; c = c + 1) begin
                if (p2_done !== 1'b0) timing_ok = 1'b0;
                @(posedge clk);
                #1;
            end
            // Cycle 14 (c == 13): p2_done must be 1'b1 and result_scl ready
            if (p2_done !== 1'b1) timing_ok = 1'b0;
            res_out = p2_res_scl;
            @(posedge clk);
            #1;
        end
    endtask

    task mmio_write_word;
        input [11:0] a;
        input [31:0] d;
        begin
            @(posedge clk);
            mmio_we    <= 1'b1;
            mmio_re    <= 1'b0;
            mmio_addr  <= a;
            mmio_wdata <= d;
            @(posedge clk);
            mmio_we    <= 1'b0;
        end
    endtask

    task mmio_read_word;
        input  [11:0] a;
        output [31:0] d;
        begin
            @(posedge clk);
            mmio_re   <= 1'b1;
            mmio_we   <= 1'b0;
            mmio_addr <= a;
            @(posedge clk);
            mmio_re   <= 1'b0;
            #1;
            d = mmio_rdata;
        end
    endtask

    reg [31:0] p2_dot_val;
    reg        p2_timing_ok;

    initial begin
        pass_cnt    = 0;
        fail_cnt    = 0;
        u_grd_vec   = 144'd0;
        u_alu_op    = 3'd0;
        u_alu_idx   = 12'd0;
        u_alu_s1    = 144'd0;
        u_alu_s2    = 144'd0;
        u_alu_scl   = 32'd0;
        u_alu_stall = 1'b0;
        dec_instr   = 32'd0;
        cpu_rst_n   = 1'b0;
        cpu_dbg_addr= 5'd0;
        rst_n       = 1'b0;
        mmio_re     = 1'b0;
        mmio_we     = 1'b0;
        mmio_addr   = 12'd0;
        mmio_wdata  = 32'd0;

        for (i = 0; i < 32; i = i + 1) cpu_imem_rom[i] = 32'd0;

        #20;
        rst_n = 1'b1;
        #20;

        // ====================================================================
        // TEST 1: Alternative A1 — Coupled H* in hcpu_guard.v & 18-lane carry
        // ====================================================================
        u_grd_vec = 144'd0;
        u_grd_vec[0*8 +: 8]  = 8'd254; // Theta
        u_grd_vec[7*8 +: 8]  = 8'd127; // Ka
        u_grd_vec[15*8 +: 8] = 8'd127; // A_K
        u_grd_vec[17*8 +: 8] = 8'd127; // H*
        #1;
        check_cond(u_grd_pass === 1'b1, "A1_127xKaf_pass");

        u_grd_vec[0*8 +: 8]  = 8'd0;   // Theta wrapped 256 -> 0
        u_grd_vec[7*8 +: 8]  = 8'd128; // Ka
        u_grd_vec[15*8 +: 8] = 8'd128; // A_K
        u_grd_vec[17*8 +: 8] = 8'd128; // H*
        #1;
        check_cond(u_grd_pass === 1'b0, "A1_128xKaf_rejected_by_hw_hgrd");

        u_grd_vec = 144'd0;
        u_grd_vec[0*8 +: 8]  = 8'd2;
        u_grd_vec[2*8 +: 8]  = 8'd1;
        u_grd_vec[4*8 +: 8]  = 8'd1;
        u_grd_vec[14*8 +: 8] = 8'd1;
        u_grd_vec[15*8 +: 8] = 8'd1;
        u_grd_vec[17*8 +: 8] = 8'd1;   // H* forged to 1 (Ka=0)
        #1;
        check_cond(u_grd_pass === 1'b0, "A1_Ba_forged_Hstar_rejected");

        u_alu_op = 3'd0; // ALU_HCADD
        u_alu_s1 = 144'd0;
        u_alu_s2 = 144'd0;
        u_alu_s1[4*8 +: 8]  = 8'd255;
        u_alu_s1[15*8 +: 8] = 8'd255;
        u_alu_s2[4*8 +: 8]  = 8'd1;
        u_alu_s2[15*8 +: 8] = 8'd1;
        #1;
        check_cond(p0_add_ovf === 1'b1 && comb_3way_eq, "A1_256xAlif_add_ovf_detected");

        u_alu_s1[4*8 +: 8]  = 8'd254;
        u_alu_s1[15*8 +: 8] = 8'd254;
        #1;
        check_cond(p0_add_ovf === 1'b0 && comb_3way_eq, "A1_255xAlif_no_ovf");

        // ====================================================================
        // TEST 2: Exhaustive 65,536 Unsigned Byte Operand Pairs (a, b) in [0..255]^2
        //         Verifies:
        //         - a^2 across all 256 byte values (Profile 0, 1, 2)
        //         - abs_diff(a, b) = |a - b| across all 65,536 pairs
        //         - (a - b)^2 across all 65,536 pairs (Profile 0, 1, 2)
        //         - a * b across all 65,536 pairs (Profile 0, Profile 1, and Profile 2)
        // ====================================================================
        sq_err_cnt      = 0;
        diff_sq_err_cnt = 0;
        abs_diff_err_cnt= 0;
        prod_p01_err_cnt= 0;
        prod_p2_err_cnt = 0;

        // 2a. Exhaustive 256 byte squarer check on HNRM2 across all 3 profiles
        u_alu_op = 3'd1; // ALU_HNRM2
        u_alu_s1 = 144'd0;
        u_alu_s2 = 144'd0;
        for (a_val = 0; a_val < 256; a_val = a_val + 1) begin
            u_alu_s1[0*8 +: 8] = a_val[7:0];
            #1;
            if (p0_res_scl !== (a_val * a_val) || !comb_3way_eq)
                sq_err_cnt = sq_err_cnt + 1;
        end
        check_cond(sq_err_cnt == 0, "P8_Exhaustive_256_a_sq_HNRM2_all_3_profiles");

        // 2b. Exhaustive 65,536 pairs (a, b) for abs_diff(a, b) and (a - b)^2 on HDIST
        //     across all 3 profiles (Profile 0, Profile 1, Profile 2)
        u_alu_op = 3'd2; // ALU_HDIST
        u_alu_s1 = 144'd0;
        u_alu_s2 = 144'd0;
        for (a_val = 0; a_val < 256; a_val = a_val + 1) begin
            for (b_val = 0; b_val < 256; b_val = b_val + 1) begin
                u_alu_s1[0*8 +: 8] = a_val[7:0];
                u_alu_s2[0*8 +: 8] = b_val[7:0];
                #1;
                diff_ab = (a_val >= b_val) ? (a_val - b_val) : (b_val - a_val);
                if (u_alu_p2_nodsp.abs_diff[0] !== diff_ab[7:0])
                    abs_diff_err_cnt = abs_diff_err_cnt + 1;
                if (p0_res_scl !== (diff_ab * diff_ab) || !comb_3way_eq)
                    diff_sq_err_cnt = diff_sq_err_cnt + 1;
            end
        end
        check_cond(abs_diff_err_cnt == 0, "P8_Exhaustive_65536_abs_diff_single_subtractor");
        check_cond(diff_sq_err_cnt == 0,  "P8_Exhaustive_65536_diff_sq_HDIST_all_3_profiles");

        // 2c. Exhaustive 65,536 pairs (a, b) for a * b on HDOT:
        //     - Direct single-pair check on Profile 0, Profile 1, and Profile 2 lane-0 multiplier
        //       (with u_alu_stall = 1'b1 so hdot_lane remains pinned at 0 during the #1 ticks)
        //     - Plus 4,682 x 14-lane full 14-cycle clocked HDOT runs covering all 65,536 pairs
        @(posedge clk);
        rst_n <= 1'b0;
        @(posedge clk);
        rst_n <= 1'b1;
        u_alu_op    = 3'd6; // ALU_HDOT
        u_alu_stall = 1'b1; // Hold hdot_lane == 0 during combinational #1 sweep
        u_alu_s1    = 144'd0;
        u_alu_s2    = 144'd0;
        #1;
        for (a_val = 0; a_val < 256; a_val = a_val + 1) begin
            for (b_val = 0; b_val < 256; b_val = b_val + 1) begin
                u_alu_s1[0*8 +: 8] = a_val[7:0];
                u_alu_s2[0*8 +: 8] = b_val[7:0];
                #1;
                if (p0_res_scl !== (a_val * b_val) || p1_res_scl !== (a_val * b_val))
                    prod_p01_err_cnt = prod_p01_err_cnt + 1;
                // At hdot_lane == 0, u_alu_p2_nodsp.g_profile_fpga_nodsp.cur_prod evaluates a * b
                if (u_alu_p2_nodsp.g_profile_fpga_nodsp.cur_prod !== (a_val * b_val))
                    prod_p2_err_cnt = prod_p2_err_cnt + 1;
            end
        end

        // Re-align to posedge clk with hdot_lane == 0 before 14-cycle clocked sweep
        u_alu_op    = 3'd0;
        u_alu_stall = 1'b0;
        @(posedge clk);
        #1;

        // Full 14-cycle clocked HDOT sweep packing all 65,536 pairs across 4,682 14-lane batches
        for (batch_idx = 0; batch_idx < 4682; batch_idx = batch_idx + 1) begin
            exp_batch_dot = 32'd0;
            for (lane_idx = 0; lane_idx < 14; lane_idx = lane_idx + 1) begin
                i = batch_idx * 14 + lane_idx;
                if (i < 65536) begin
                    a_val = (i >> 8) & 8'hFF;
                    b_val = i & 8'hFF;
                end else begin
                    a_val = 255;
                    b_val = 255;
                end
                u_alu_s1[lane_idx*8 +: 8] = a_val[7:0];
                u_alu_s2[lane_idx*8 +: 8] = b_val[7:0];
                exp_batch_dot = exp_batch_dot + (a_val * b_val);
            end
            run_p2_hdot_14cyc(p2_dot_val, p2_timing_ok);
            if (!p2_timing_ok || p2_dot_val !== exp_batch_dot ||
                p0_res_scl !== exp_batch_dot || p1_res_scl !== exp_batch_dot)
                prod_p2_err_cnt = prod_p2_err_cnt + 1;
        end
        check_cond(prod_p01_err_cnt == 0, "P8_Exhaustive_65536_mul_HDOT_Profile0_Profile1");
        check_cond(prod_p2_err_cnt == 0,  "P8_Exhaustive_65536_mul_HDOT_Profile2_14cycle");

        // ====================================================================
        // TEST 3: Extreme Per-Lane, Unsignedness, and One-Hot Lane Isolation
        // ====================================================================
        // 3a. Canonical Ba and Mim: <Ba, Mim>_14 = 13
        u_alu_s1 = 144'd0;
        u_alu_s2 = 144'd0;
        u_alu_s1[0*8 +: 8] = 8'd2;
        u_alu_s1[2*8 +: 8] = 8'd1;
        u_alu_s1[4*8 +: 8] = 8'd1;
        u_alu_s2[0*8 +: 8] = 8'd6;
        u_alu_s2[4*8 +: 8] = 8'd1;
        u_alu_s2[5*8 +: 8] = 8'd1;
        u_alu_s2[9*8 +: 8] = 8'd1;
        u_alu_s2[13*8 +: 8] = 8'd1;
        run_p2_hdot_14cyc(p2_dot_val, p2_timing_ok);
        check_cond(p0_res_scl === 32'd13 && p1_res_scl === 32'd13 &&
                   p2_dot_val === 32'd13 && p2_timing_ok,
                   "A2_HDOT_Ba_Mim_eq_13_all_3_profiles");

        // 3b. High-component vector 200 x 100 = 20,000 (no 8-bit wrap)
        u_alu_s1 = 144'd0;
        u_alu_s2 = 144'd0;
        u_alu_s1[0*8 +: 8] = 8'd200;
        u_alu_s2[0*8 +: 8] = 8'd100;
        run_p2_hdot_14cyc(p2_dot_val, p2_timing_ok);
        check_cond(p0_res_scl === 32'd20000 && p1_res_scl === 32'd20000 &&
                   p2_dot_val === 32'd20000 && p2_timing_ok,
                   "A2_HDOT_200x100_eq_20000_no_wrap");

        // 3c. Full-scale 14-lane maximum: 14 * 255 * 255 = 910,350, bits [31:20] == 0
        for (i = 0; i < 14; i = i + 1) begin
            u_alu_s1[i*8 +: 8] = 8'd255;
            u_alu_s2[i*8 +: 8] = 8'd255;
        end
        run_p2_hdot_14cyc(p2_dot_val, p2_timing_ok);
        check_cond(p0_res_scl === 32'd910350 && p1_res_scl === 32'd910350 &&
                   p2_dot_val === 32'd910350 && p2_dot_val[31:20] === 12'd0 && p2_timing_ok,
                   "A2_HDOT_max_14x255x255_eq_910350_unsigned_zero_ext");

        // 3d. Orthogonal lanes: 0x00 x 0xFF and 0xFF x 0x00 -> 0
        u_alu_s1 = 144'd0;
        u_alu_s2 = 144'd0;
        for (i = 0; i < 7; i = i + 1) begin
            u_alu_s1[i*8 +: 8]     = 8'h00;
            u_alu_s2[i*8 +: 8]     = 8'hFF;
            u_alu_s1[(i+7)*8 +: 8] = 8'hFF;
            u_alu_s2[(i+7)*8 +: 8] = 8'h00;
        end
        run_p2_hdot_14cyc(p2_dot_val, p2_timing_ok);
        check_cond(p0_res_scl === 32'd0 && p1_res_scl === 32'd0 &&
                   p2_dot_val === 32'd0 && p2_timing_ok,
                   "A2_HDOT_orthogonal_00xFF_FFx00_eq_0");

        // 3e. Unsigned MSB byte test: 0x80 (128) x 0xFF (255) = 32,640
        u_alu_s1 = 144'd0;
        u_alu_s2 = 144'd0;
        u_alu_s1[13*8 +: 8] = 8'h80;
        u_alu_s2[13*8 +: 8] = 8'hFF;
        run_p2_hdot_14cyc(p2_dot_val, p2_timing_ok);
        check_cond(p0_res_scl === 32'd32640 && p1_res_scl === 32'd32640 &&
                   p2_dot_val === 32'd32640 && p2_timing_ok,
                   "A2_HDOT_unsigned_0x80x0xFF_eq_32640");

        // 3f. One-hot lane isolation across all 18 lanes (0..13 active, 14..17 ignored)
        onehot_err_cnt = 0;
        for (lane_idx = 0; lane_idx < 18; lane_idx = lane_idx + 1) begin
            u_alu_s1 = 144'd0;
            u_alu_s2 = 144'd0;
            a_val = 17 + lane_idx * 11;
            b_val = 23 + lane_idx * 7;
            u_alu_s1[lane_idx*8 +: 8] = a_val[7:0];
            u_alu_s2[lane_idx*8 +: 8] = b_val[7:0];

            // Test HNRM2
            u_alu_op = 3'd1; #1;
            ref_nrm2 = (lane_idx < 14) ? (a_val * a_val) : 32'd0;
            if (p0_res_scl !== ref_nrm2 || !comb_3way_eq)
                onehot_err_cnt = onehot_err_cnt + 1;

            // Test HDIST
            u_alu_op = 3'd2; #1;
            diff_ab  = (a_val >= b_val) ? (a_val - b_val) : (b_val - a_val);
            ref_dist = (lane_idx < 14) ? (diff_ab * diff_ab) : 32'd0;
            if (p0_res_scl !== ref_dist || !comb_3way_eq)
                onehot_err_cnt = onehot_err_cnt + 1;

            // Test HDOT
            ref_dot = (lane_idx < 14) ? (a_val * b_val) : 32'd0;
            run_p2_hdot_14cyc(p2_dot_val, p2_timing_ok);
            if (p0_res_scl !== ref_dot || p1_res_scl !== ref_dot ||
                p2_dot_val !== ref_dot || !p2_timing_ok)
                onehot_err_cnt = onehot_err_cnt + 1;
        end
        check_cond(onehot_err_cnt == 0, "P8_OneHot_18lane_isolation_HNRM2_HDIST_HDOT");

        // ====================================================================
        // TEST 4: Multi-Lane Randomized Differential Sweep (512 Vectors, Fixed Seed)
        // ====================================================================
        rand_err_cnt = 0;
        prng_state   = 32'hC051_C008;
        for (batch_idx = 0; batch_idx < 512; batch_idx = batch_idx + 1) begin
            ref_nrm2 = 32'd0;
            ref_dist = 32'd0;
            ref_dot  = 32'd0;
            for (lane_idx = 0; lane_idx < 18; lane_idx = lane_idx + 1) begin
                prng_state = prng_state * 32'd1664525 + 32'd1013904223;
                ra = prng_state[23:16];
                prng_state = prng_state * 32'd1664525 + 32'd1013904223;
                rb = prng_state[23:16];
                u_alu_s1[lane_idx*8 +: 8] = ra;
                u_alu_s2[lane_idx*8 +: 8] = rb;
                if (lane_idx < 14) begin
                    ref_nrm2 = ref_nrm2 + (ra * ra);
                    diff_ab  = (ra >= rb) ? (ra - rb) : (rb - ra);
                    ref_dist = ref_dist + (diff_ab * diff_ab);
                    ref_dot  = ref_dot  + (ra * rb);
                end
            end
            // Check HNRM2 across all 3 profiles
            u_alu_op = 3'd1; #1;
            if (p0_res_scl !== ref_nrm2 || !comb_3way_eq)
                rand_err_cnt = rand_err_cnt + 1;

            // Check HDIST across all 3 profiles
            u_alu_op = 3'd2; #1;
            if (p0_res_scl !== ref_dist || !comb_3way_eq)
                rand_err_cnt = rand_err_cnt + 1;

            // Check HDOT across all 3 profiles
            run_p2_hdot_14cyc(p2_dot_val, p2_timing_ok);
            if (p0_res_scl !== ref_dot || p1_res_scl !== ref_dot ||
                p2_dot_val !== ref_dot || !p2_timing_ok)
                rand_err_cnt = rand_err_cnt + 1;
        end
        check_cond(rand_err_cnt == 0, "P8_Random512_14lane_differential_parity_all_3_profiles");

        // ====================================================================
        // TEST 5: Profile C Stall-Hold & Full HCPU Pipeline Iterative HDOT Test
        // ====================================================================
        // 5a. Verify that asserting stall=1 mid-HDOT freezes hdot_lane & hdot_acc
        for (i = 0; i < 14; i = i + 1) begin
            u_alu_s1[i*8 +: 8] = (i + 1);
            u_alu_s2[i*8 +: 8] = 8'd10;
        end
        // Expected sum: 10 * (1+2+...+14) = 10 * 105 = 1,050
        u_alu_op    = 3'd6;
        u_alu_stall = 1'b0;
        // Advance 5 cycles
        for (i = 0; i < 5; i = i + 1) @(posedge clk);
        #1;
        // Freeze with stall = 1 for 4 cycles
        u_alu_stall = 1'b1;
        for (i = 0; i < 4; i = i + 1) begin
            @(posedge clk);
            #1;
            if (p2_done !== 1'b0) fail_cnt = fail_cnt + 1;
        end
        // Release stall and advance remaining 8 cycles to reach cycle 14 (lane 13)
        u_alu_stall = 1'b0;
        for (i = 0; i < 8; i = i + 1) @(posedge clk);
        #1;
        check_cond(p2_done === 1'b1 && p2_res_scl === 32'd1050,
                   "P8_ProfileC_iterative_HDOT_stall_hold_and_resume");
        @(posedge clk);
        u_alu_op = 3'd0;
        #1;

        // 5b. Full HCPU Pipeline (CODEX_PROFILE=2) executing HLOAD, HDOT, dependent ADDI, HALT
        //     Program:
        //       0: HLOAD H1, #2       (0x40100002) -> Ba  (2,0,0,1,0,1,0,0,0,1,0,0,0,0...)
        //       1: HLOAD H2, #24      (0x40200018) -> Mim (4,0,0,0,0,0,0,0,1,0,0,0,0,1...)
        //       2: HDOT  R3, H1, H2   (0x4E312000) -> R3 = 2*4 = 8 (takes 14 cycles in EX!)
        //       3: ADDI  R4, R3, #7   (0x11430007) -> R4 = R3 + 7 = 15 (uses EX->ID forwarding!)
        //       4: HNRM2 R5, H2       (0x06520000) -> R5 = 16+1+1 = 18 (1 cycle in EX!)
        //       5: HDIST R6, H1, H2   (0x07612000) -> R6 = 4+1+1+1+1+1 = 9 (1 cycle in EX!)
        //       6: HALT               (0x01000000)
        cpu_imem_rom[0] = 32'h4010_0002;
        cpu_imem_rom[1] = 32'h4020_0018;
        cpu_imem_rom[2] = 32'h4E31_2000;
        cpu_imem_rom[3] = 32'h1143_0007;
        cpu_imem_rom[4] = 32'h0652_0000;
        cpu_imem_rom[5] = 32'h0761_2000;
        cpu_imem_rom[6] = 32'h0100_0000;

        cpu_rst_n = 1'b0;
        repeat (5) @(posedge clk);
        cpu_rst_n = 1'b1;
        cyc_cnt = 0;
        while (!cpu_halted && cyc_cnt < 100) begin
            @(posedge clk);
            cyc_cnt = cyc_cnt + 1;
        end
        repeat (3) @(posedge clk);
        #1;
        cpu_dbg_addr = 5'd3; #1;
        check_cond(cpu_halted === 1'b1 && cpu_dbg_data === 32'd8,
                   "P8_FullCPU_ProfileC_HDOT_R3_eq_8");
        cpu_dbg_addr = 5'd4; #1;
        check_cond(cpu_dbg_data === 32'd15,
                   "P8_FullCPU_ProfileC_dependent_ADDI_R4_eq_15");
        cpu_dbg_addr = 5'd5; #1;
        check_cond(cpu_dbg_data === 32'd18 && cyc_cnt == 25,
                   "P8_FullCPU_ProfileC_HNRM2_R5_eq_18_and_exact_25_cycles");
        cpu_dbg_addr = 5'd6; #1;
        check_cond(cpu_dbg_data === 32'd9,
                   "P8_FullCPU_ProfileC_HDIST_R6_eq_9");

        // ====================================================================
        // TEST 6: Target Capability Gating (HDOT_ENABLE=0) & A3 SDIO Pre-Scan
        // ====================================================================
        // 6a. Decode capability gating: OP_HDOT (0x4E312000) accepted when HDOT_ENABLE=1,
        //     rejected with id_is_halt=1, id_dst=4'hE, id_gpr_we=0 when HDOT_ENABLE=0
        dec_instr = 32'h4E31_2000;
        @(posedge clk);
        #1;
        check_cond(dec_en1_is_codex === 1'b1 && dec_en1_gpr_we === 1'b1 && dec_en1_is_halt === 1'b0 &&
                   dec_en0_is_codex === 1'b0 && dec_en0_gpr_we === 1'b0 && dec_en0_is_halt === 1'b1 &&
                   dec_en0_dst === 4'hE && p2_nohdot_scl === 32'd0 && p2_nohdot_done === 1'b1,
                   "P8_CapabilityGate_HDOT_ENABLE_0_rejects_0x4E");

        // 6b. Alternative A3: Clean 128-word sector (MOVI 0x04, HDOT 0x4E)
        mmio_write_word(12'hFE4, 32'h0000_0001);
        expected_csum = 32'd0;
        for (i = 0; i < 128; i = i + 1) begin
            mmio_write_word(12'hFE3, {8'h04, 12'd0, i[11:0] + 12'd1});
            expected_csum = expected_csum + {8'h04, 12'd0, i[11:0] + 12'd1};
        end
        mmio_read_word(12'hFE5, rd_csum);
        mmio_read_word(12'hFE6, rd_prescan);
        check_cond(rd_csum === expected_csum, "A3_SD_CSUM_matches_128word_sector");
        check_cond(rd_prescan[1:0] === 2'b00, "A3_SD_PRESCAN_clean_sector_pass");

        // 6c. Alternative A3: Sector with forbidden HALT (0x01) at word 12
        mmio_write_word(12'hFE4, 32'h0000_0001);
        expected_csum = 32'd0;
        for (i = 0; i < 128; i = i + 1) begin
            if (i == 12) begin
                mmio_write_word(12'hFE3, 32'h0100_0000);
                expected_csum = expected_csum + 32'h0100_0000;
            end else begin
                mmio_write_word(12'hFE3, 32'h0000_0000);
            end
        end
        mmio_read_word(12'hFE5, rd_csum);
        mmio_read_word(12'hFE6, rd_prescan);
        check_cond(rd_csum === expected_csum,           "A3_SD_CSUM_bad_sector_matches");
        check_cond(rd_prescan[0] === 1'b1,              "A3_SD_PRESCAN_all_bad_flag_set");
        check_cond(rd_prescan[1] === 1'b1,              "A3_SD_PRESCAN_body_bad_flag_set");
        check_cond(rd_prescan[14:8] === 7'd12,          "A3_SD_PRESCAN_first_idx_eq_12");
        check_cond(rd_prescan[23:16] === 8'd1,          "A3_SD_PRESCAN_bad_cnt_eq_1");
        check_cond(rd_prescan[31:24] === 8'h01,         "A3_SD_PRESCAN_first_opc_eq_0x01");

        $display("========================================");
        $display("HMCL RTL Alternatives: %0d PASS, %0d FAIL", pass_cnt, fail_cnt);
        $display("========================================");
        $finish;
    end

endmodule
