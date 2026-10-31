// ============================================================================
// HMCL Architectural Alternatives Verification Testbench
// Verifies A1 (Hardware Sticky Prefix Guard & Coupled H*),
//          A2 (Native OP_HDOT 20-bit single-cycle inner product + extreme lane tests),
//          A3 (Streaming SDIO Checksum32 & 4-B' Pre-Scan)
// against HMCL predictions and Baseline 3a6aeef.
// ============================================================================

`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_hmcl_rtl_alternatives;

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

    // ── Direct Unit Under Test 2: hcpu_codex_alu (A1 add_ovf + A2 HDOT) ──
    reg  [2:0]         u_alu_op;
    reg  [11:0]        u_alu_idx;
    reg  [`HREG_W-1:0] u_alu_s1, u_alu_s2;
    reg  [`XLEN-1:0]   u_alu_scl;
    wire [`HREG_W-1:0] u_alu_res_vec;
    wire [`XLEN-1:0]   u_alu_res_scl;
    wire               u_alu_add_ovf;
    wire               u_alu_done;

    hcpu_codex_alu u_alu_dut (
        .op         (u_alu_op),
        .index      (u_alu_idx),
        .src1       (u_alu_s1),
        .src2       (u_alu_s2),
        .src_scl    (u_alu_scl),
        .result_vec (u_alu_res_vec),
        .result_scl (u_alu_res_scl),
        .add_ovf    (u_alu_add_ovf),
        .done       (u_alu_done)
    );

    // ── Direct Unit Under Test 3: hcpu_mmio + hcpu_sdio (A3 SD_CSUM & SD_PRESCAN) ──
    reg         clk;
    reg         rst_n;
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

    initial clk = 0;
    always #5 clk = ~clk;

    integer pass_cnt, fail_cnt, i;
    reg [31:0] expected_csum;

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

    reg [31:0] rd_csum, rd_prescan;

    initial begin
        pass_cnt   = 0;
        fail_cnt   = 0;
        u_grd_vec  = 144'd0;
        u_alu_op   = 3'd0;
        u_alu_idx  = 12'd0;
        u_alu_s1   = 144'd0;
        u_alu_s2   = 144'd0;
        u_alu_scl  = 32'd0;
        rst_n      = 1'b0;
        mmio_re    = 1'b0;
        mmio_we    = 1'b0;
        mmio_addr  = 12'd0;
        mmio_wdata = 32'd0;

        #20;
        rst_n = 1'b1;
        #20;

        // ====================================================================
        // TEST 1: Alternative A1 — Coupled H* in hcpu_guard.v
        // ====================================================================
        // 1a. 127 x Kaf: Theta=254, Ka=127, AK=127, H*=127 -> PASS
        u_grd_vec = 144'd0;
        u_grd_vec[0*8 +: 8]  = 8'd254; // Theta
        u_grd_vec[7*8 +: 8]  = 8'd127; // Ka
        u_grd_vec[15*8 +: 8] = 8'd127; // A_K
        u_grd_vec[17*8 +: 8] = 8'd127; // H*
        #1;
        check_cond(u_grd_pass === 1'b1, "A1_127xKaf_pass");

        // 1b. 128 x Kaf (8-bit wrapped): Theta=0, Ka=128, AK=128, H*=128 -> FAIL (H* > Theta/2)
        u_grd_vec[0*8 +: 8]  = 8'd0;   // Theta wrapped 256 -> 0
        u_grd_vec[7*8 +: 8]  = 8'd128; // Ka
        u_grd_vec[15*8 +: 8] = 8'd128; // A_K
        u_grd_vec[17*8 +: 8] = 8'd128; // H*
        #1;
        check_cond(u_grd_pass === 1'b0, "A1_128xKaf_rejected_by_hw_hgrd");

        // 1c. Ba with H* forged to 1 while Ka=0, Theta=2 -> FAIL (H* != Ka)
        u_grd_vec = 144'd0;
        u_grd_vec[0*8 +: 8]  = 8'd2;   // Theta
        u_grd_vec[2*8 +: 8]  = 8'd1;   // Nb
        u_grd_vec[4*8 +: 8]  = 8'd1;   // Kp
        u_grd_vec[14*8 +: 8] = 8'd1;   // A_N
        u_grd_vec[15*8 +: 8] = 8'd1;   // A_K
        u_grd_vec[17*8 +: 8] = 8'd1;   // H* forged to 1 (Ka=0)
        #1;
        check_cond(u_grd_pass === 1'b0, "A1_Ba_forged_Hstar_rejected");

        // 1d. 18-lane carry-out detection in hcpu_codex_alu: 255xAlif + 1xAlif (Kp=255+1, AK=255+1)
        u_alu_op = 3'd0; // ALU_HCADD
        u_alu_s1 = 144'd0;
        u_alu_s2 = 144'd0;
        u_alu_s1[4*8 +: 8]  = 8'd255; // Kp = 255
        u_alu_s1[15*8 +: 8] = 8'd255; // AK = 255
        u_alu_s2[4*8 +: 8]  = 8'd1;   // Kp = 1
        u_alu_s2[15*8 +: 8] = 8'd1;   // AK = 1
        #1;
        check_cond(u_alu_add_ovf === 1'b1, "A1_256xAlif_add_ovf_detected");

        // 1e. 254xAlif + 1xAlif -> add_ovf == 0
        u_alu_s1[4*8 +: 8]  = 8'd254;
        u_alu_s1[15*8 +: 8] = 8'd254;
        #1;
        check_cond(u_alu_add_ovf === 1'b0, "A1_255xAlif_no_ovf");

        // ====================================================================
        // TEST 2: Alternative A2 — Native 20-bit OP_HDOT (ALU_HDOT = 3'd6)
        //         + Extreme Per-Lane & Signedness Verification
        // ====================================================================
        // 2a. Canonical Ba (2,0,1,0,1,0...) and Mim (6,0,0,0,1,1,0,0,0,1,0,0,0,1...)
        //     <Ba, Mim>_14 = 2*6 + 1*1 = 13
        u_alu_op = 3'd6; // ALU_HDOT
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
        #1;
        check_cond(u_alu_res_scl === 32'd13, "A2_HDOT_Ba_Mim_eq_13");

        // 2b. High-component vector where a[0]+b[0] = 200+100 = 300 > 255
        //     (8-bit polarization wraps 300->44, giving wrong answer, whereas A2 gives 20,000!)
        u_alu_s1 = 144'd0;
        u_alu_s2 = 144'd0;
        u_alu_s1[0*8 +: 8] = 8'd200;
        u_alu_s2[0*8 +: 8] = 8'd100;
        #1;
        check_cond(u_alu_res_scl === 32'd20000, "A2_HDOT_200x100_eq_20000_no_wrap");

        // 2c. Full-scale 14-lane maximum: all 14 lanes = 255 x 255 -> 14 * 65025 = 910,350
        //     Also verify upper 12 bits [31:20] are zero-extended (unsigned GPR result).
        for (i = 0; i < 14; i = i + 1) begin
            u_alu_s1[i*8 +: 8] = 8'd255;
            u_alu_s2[i*8 +: 8] = 8'd255;
        end
        #1;
        check_cond(u_alu_res_scl === 32'd910350 && u_alu_res_scl[31:20] === 12'd0,
                   "A2_HDOT_max_14x255x255_eq_910350_unsigned_zero_ext");

        // 2d. Extreme orthogonal lanes: 0x00 x 0xFF on lanes 0..6, 0xFF x 0x00 on lanes 7..13 -> 0
        u_alu_s1 = 144'd0;
        u_alu_s2 = 144'd0;
        for (i = 0; i < 7; i = i + 1) begin
            u_alu_s1[i*8 +: 8]       = 8'h00;
            u_alu_s2[i*8 +: 8]       = 8'hFF;
            u_alu_s1[(i+7)*8 +: 8]   = 8'hFF;
            u_alu_s2[(i+7)*8 +: 8]   = 8'h00;
        end
        #1;
        check_cond(u_alu_res_scl === 32'd0, "A2_HDOT_orthogonal_00xFF_FFx00_eq_0");

        // 2e. Unsigned MSB byte test: 0x80 (128) x 0xFF (255) on lane 13
        //     If treated as signed (-128 * -1 = +128), it would fail; unsigned is 128 * 255 = 32,640!
        u_alu_s1 = 144'd0;
        u_alu_s2 = 144'd0;
        u_alu_s1[13*8 +: 8] = 8'h80; // 128 unsigned
        u_alu_s2[13*8 +: 8] = 8'hFF; // 255 unsigned
        #1;
        check_cond(u_alu_res_scl === 32'd32640, "A2_HDOT_unsigned_0x80x0xFF_eq_32640");

        // 2f. 14-lane isolation: lanes 14..17 (A_N, A_K, A_Q, H*) set to 0xFF must NOT affect <a,b>_14
        u_alu_s1 = 144'd0;
        u_alu_s2 = 144'd0;
        u_alu_s1[0*8 +: 8]  = 8'd3;
        u_alu_s2[0*8 +: 8]  = 8'd5;
        u_alu_s1[14*8 +: 8] = 8'hFF;
        u_alu_s1[15*8 +: 8] = 8'hFF;
        u_alu_s1[16*8 +: 8] = 8'hFF;
        u_alu_s1[17*8 +: 8] = 8'hFF;
        u_alu_s2[14*8 +: 8] = 8'hFF;
        u_alu_s2[15*8 +: 8] = 8'hFF;
        u_alu_s2[16*8 +: 8] = 8'hFF;
        u_alu_s2[17*8 +: 8] = 8'hFF;
        #1;
        check_cond(u_alu_res_scl === 32'd15, "A2_HDOT_ignores_lanes_14_to_17");

        // 2g. Unified MAC regression on HDIST: |0 - 255|^2 + |255 - 0|^2 = 65025 + 65025 = 130,050
        u_alu_op = 3'd2; // ALU_HDIST
        u_alu_s1 = 144'd0;
        u_alu_s2 = 144'd0;
        u_alu_s1[0*8 +: 8]  = 8'h00;
        u_alu_s2[0*8 +: 8]  = 8'hFF;
        u_alu_s1[13*8 +: 8] = 8'hFF;
        u_alu_s2[13*8 +: 8] = 8'h00;
        #1;
        check_cond(u_alu_res_scl === 32'd130050, "A2_HDIST_extreme_00_FF_symmetry_eq_130050");

        // ====================================================================
        // TEST 3: Alternative A3 — Streaming SDIO Checksum32 & 4-B' Pre-Scan
        // ====================================================================
        // 3a. Write a clean 128-word sector (all legal user-mode opcodes: MOVI 0x04, ADD 0x10)
        // Reset buffer index via SD_CONTROL (0xFE4) bit 0 = 1
        mmio_write_word(12'hFE4, 32'h0000_0001);
        expected_csum = 32'd0;
        for (i = 0; i < 128; i = i + 1) begin
            // Word with legal opcode 0x04 (MOVI) and payload i+1
            mmio_write_word(12'hFE3, {8'h04, 12'd0, i[11:0] + 12'd1});
            expected_csum = expected_csum + {8'h04, 12'd0, i[11:0] + 12'd1};
        end
        mmio_read_word(12'hFE5, rd_csum);
        mmio_read_word(12'hFE6, rd_prescan);
        check_cond(rd_csum === expected_csum, "A3_SD_CSUM_matches_128word_sector");
        check_cond(rd_prescan[1:0] === 2'b00, "A3_SD_PRESCAN_clean_sector_pass");

        // 3b. Write a sector with a forbidden HALT (0x01) at word 12 (in HPG1 body >= 7)
        mmio_write_word(12'hFE4, 32'h0000_0001);
        expected_csum = 32'd0;
        for (i = 0; i < 128; i = i + 1) begin
            if (i == 12) begin
                mmio_write_word(12'hFE3, 32'h0100_0000); // Forbidden HALT (0x01) in user overlay
                expected_csum = expected_csum + 32'h0100_0000;
            end else begin
                mmio_write_word(12'hFE3, 32'h0000_0000); // NOP (0x00)
            end
        end
        mmio_read_word(12'hFE5, rd_csum);
        mmio_read_word(12'hFE6, rd_prescan);
        check_cond(rd_csum === expected_csum, "A3_SD_CSUM_bad_sector_matches");
        check_cond(rd_prescan[0] === 1'b1, "A3_SD_PRESCAN_all_bad_flag_set");
        check_cond(rd_prescan[1] === 1'b1, "A3_SD_PRESCAN_body_bad_flag_set");
        check_cond(rd_prescan[14:8] === 7'd12, "A3_SD_PRESCAN_first_idx_eq_12");
        check_cond(rd_prescan[23:16] === 8'd1, "A3_SD_PRESCAN_bad_cnt_eq_1");
        check_cond(rd_prescan[31:24] === 8'h01, "A3_SD_PRESCAN_first_opc_eq_0x01");

        $display("========================================");
        $display("HMCL RTL Alternatives: %0d PASS, %0d FAIL", pass_cnt, fail_cnt);
        $display("========================================");
        $finish;
    end

endmodule
