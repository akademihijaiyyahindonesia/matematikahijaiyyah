`timescale 1ns/1ps
`include "hcpu_pkg.vh"

// Behavioral stubs for Gowin primitives used by hcpu_hdmi_top in simulation
module TMDS_rPLL (
    input  wire clkin,
    output reg  clkout = 1'b0,
    output reg  lock   = 1'b1
);
    always @(posedge clkin or negedge clkin) clkout <= ~clkout;
endmodule

module CLKDIV (
    input  wire RESETN,
    input  wire HCLKIN,
    output reg  CLKOUT = 1'b0,
    input  wire CALIB
);
    parameter DIV_MODE = "5";
    parameter GSREN    = "false";
    always @(posedge HCLKIN or negedge HCLKIN) begin
        if (!RESETN) CLKOUT <= 1'b0;
        else         CLKOUT <= ~CLKOUT;
    end
endmodule

module DVI_TX_Top (
    input  wire       I_rst_n,
    input  wire       I_serial_clk,
    input  wire       I_rgb_clk,
    input  wire       I_rgb_vs,
    input  wire       I_rgb_hs,
    input  wire       I_rgb_de,
    input  wire [7:0] I_rgb_r,
    input  wire [7:0] I_rgb_g,
    input  wire [7:0] I_rgb_b,
    output wire       tmds_clk_serial,
    output wire [2:0] tmds_data_serial
);
    assign tmds_clk_serial  = I_rgb_clk & I_rst_n;
    assign tmds_data_serial = {I_rgb_de, I_rgb_vs, I_rgb_hs};
endmodule

module tb_physical_buttons_fault_recovery;
    reg        clk_27m   = 1'b0;
    reg        btn_rst_n = 1'b0; // S2 (Pin 87): idle LOW (0), active HIGH (1)
    reg        mode_key  = 1'b0; // S1 (Pin 88): idle LOW (0), active HIGH (1)
    reg        uart_rxd  = 1'b1;
    wire       uart_txd;
    wire [5:0] led;
    wire       tmds_clk_p;
    wire [2:0] tmds_data_p;
    wire       sd_clk;
    wire       sd_cmd;
    wire [3:0] sd_dat;

    // 27 MHz clock (~37 ns period; use 10 ns half-period in sim)
    always #10 clk_27m = ~clk_27m;

    // Instantiate DUT with fast debounce/long-hold parameters for testbench verification
    hcpu_hdmi_top #(
        .FONT_HEX       ("/Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_font8x8.hex"),
        .DASH_HEX       ("/Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_dashboard.hex"),
        .DASH_LOWER_HEX ("/Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_dashboard_lower.hex"),
        .HOLO_HEX       ("/Users/AMRA/hijaiyyah-mathematics/rtl/hcpu_nui_holo.hex"),
        .BTN_ACTIVE_HIGH(1'b1),
        .BTN_DEB_CLKS   (8),
        .BTN_LONG_CLKS  (40)
    ) dut (
        .clk_27m    (clk_27m),
        .btn_rst_n  (btn_rst_n),
        .mode_key   (mode_key),
        .uart_rxd   (uart_rxd),
        .uart_txd   (uart_txd),
        .led        (led),
        .tmds_clk_p (tmds_clk_p),
        .tmds_data_p(tmds_data_p),
        .sd_clk     (sd_clk),
        .sd_cmd     (sd_cmd),
        .sd_dat     (sd_dat)
    );

    integer pass_cnt = 0;
    integer fail_cnt = 0;

    task check_cond(input cond, input [511:0] label);
        begin
            if (cond) begin
                pass_cnt = pass_cnt + 1;
                $display("  [PASS] %0s", label);
            end else begin
                fail_cnt = fail_cnt + 1;
                $display("  [FAIL] %0s (ctrl_state=%0d, fault_latched=%0b, fault_code=%0d, rec_res=%0d, last_ev=%0d)",
                         label, dut.ctrl_state, dut.fault_latched, dut.fault_code, dut.recovery_result, dut.last_btn_event);
            end
        end
    endtask

    task wait_clks(input integer n);
        integer i;
        begin
            for (i = 0; i < n; i = i + 1) @(posedge clk_27m);
        end
    endtask

    reg [31:0] cyc_before, cyc_after;
    reg [11:0] h_before, h_after;

    initial begin
        $display("========================================================================");
        $display(" COSMICTERA 12-SCENARIO PHYSICAL BUTTON & FAULT RECOVERY TESTBENCH");
        $display("========================================================================");

        // Force staged reset release quickly in simulation
        force dut.pll_qual_27m   = 1'b1;
        force dut.clkdiv_rst_n   = 1'b1;
        force dut.oser_rel_27m   = 1'b1;
        force dut.timing_rel_27m = 1'b1;
        wait_clks(30);

        // Verify initial boot state: loader.hasm is running, ctrl_state == RUNNING (0),
        // and NO false GUARD: FAULT even though u_hcpu.tele_guard == 0 before OP_HGRD!
        check_cond(dut.ctrl_state == 3'd0 && dut.true_guard_fault == 1'b0 && dut.page == 4'd0,
                   "BOOT: Initial RUNNING state with zero false GUARD: FAULT during loader.hasm");

        // --------------------------------------------------------------------
        // SCENARIO 1: S1 ditekan saat RUNNING -> PAUSED -> STOPPED, CPU freezes, HDMI stays active
        // --------------------------------------------------------------------
        $display("--- Scenario 1: S1 pressed during RUNNING ---");
        mode_key = 1'b1; // Press S1
        wait_clks(14);   // Wait past 2-FF + 8-cycle debounce
        check_cond(dut.ctrl_state == 3'd2 && dut.last_btn_event == 3'd1 && dut.true_guard_fault == 1'b0,
                   "SCENARIO 1A: S1 press transitions RUNNING -> PAUSED (EV_BTN_USER_STOP) without GUARD FAULT");
        mode_key = 1'b0; // Release S1
        wait_clks(14);
        cyc_before = dut.tele_cycles;
        h_before   = dut.h_count;
        wait_clks(20);
        cyc_after  = dut.tele_cycles;
        h_after    = dut.h_count;
        check_cond(dut.ctrl_state == 3'd1 && (cyc_after == cyc_before) && (h_after != h_before),
                   "SCENARIO 1B: S1 release transitions PAUSED -> STOPPED; HCPU cycles freeze while HDMI pixel timing continues");

        // Resume to RUNNING by pressing S1 again from clean STOPPED
        mode_key = 1'b1; wait_clks(14);
        mode_key = 1'b0; wait_clks(14);
        check_cond(dut.ctrl_state == 3'd0 && dut.last_btn_event == 3'd2,
                   "SCENARIO 1C: S1 press from clean STOPPED resumes RUNNING (EV_BTN_USER_RESUME)");

        // --------------------------------------------------------------------
        // SCENARIO 2: S1 ditekan saat HALTED -> STOPPED cleanly
        // --------------------------------------------------------------------
        $display("--- Scenario 2: S1 pressed during normal HALTED ---");
        force dut.rtm_seen_normal_halt = 1'b1;
        force dut.tele_halted          = 1'b1;
        wait_clks(6);
        mode_key = 1'b1; wait_clks(14);
        mode_key = 1'b0; wait_clks(14);
        check_cond(dut.ctrl_state == 3'd1 && dut.last_btn_event == 3'd1 && dut.true_guard_fault == 1'b0,
                   "SCENARIO 2: S1 pressed during normal HALTED enters STOPPED cleanly without fault");
        release dut.tele_halted;
        release dut.rtm_seen_normal_halt;
        // Recover back to RUNNING via S2
        btn_rst_n = 1'b1; wait_clks(14);
        btn_rst_n = 1'b0; wait_clks(40);

        // --------------------------------------------------------------------
        // SCENARIO 3: S1 ditekan saat FAULT -> S1 still stops CPU (never deadlocks)
        // --------------------------------------------------------------------
        $display("--- Scenario 3: S1 pressed during FAULT ---");
        dut.sim_fault_source_active = 1'b1;
        wait_clks(6);
        check_cond(dut.ctrl_state == 3'd4 && dut.fault_latched == 1'b1,
                   "SCENARIO 3A: Fault source triggers CTRL_FAULT (4) with fault_latched=1");
        mode_key = 1'b1; wait_clks(14);
        mode_key = 1'b0; wait_clks(14);
        check_cond(dut.ctrl_state == 3'd1 && dut.last_btn_event == 3'd1,
                   "SCENARIO 3B: S1 overrides CTRL_FAULT -> CTRL_STOPPED (USER STOP works even during FAULT)");
        dut.sim_fault_source_active = 1'b0;
        btn_rst_n = 1'b1; wait_clks(14);
        btn_rst_n = 1'b0; wait_clks(40);

        // --------------------------------------------------------------------
        // SCENARIO 4: S1 ditekan dan dilepas berulang kali -> deterministic toggle
        // --------------------------------------------------------------------
        $display("--- Scenario 4: S1 pressed and released repeatedly ---");
        mode_key = 1'b1; wait_clks(14); mode_key = 1'b0; wait_clks(14); // -> STOPPED
        mode_key = 1'b1; wait_clks(14); mode_key = 1'b0; wait_clks(14); // -> RUNNING
        mode_key = 1'b1; wait_clks(14); mode_key = 1'b0; wait_clks(14); // -> STOPPED
        check_cond(dut.ctrl_state == 3'd1 && dut.true_guard_fault == 1'b0 && dut.page == 4'd0,
                   "SCENARIO 4: Repeated S1 press/release deterministically toggles RUNNING <-> STOPPED with page=0");

        // --------------------------------------------------------------------
        // SCENARIO 5: S2 ditekan saat STOPPED -> RESETTING -> READY -> RUNNING
        // --------------------------------------------------------------------
        $display("--- Scenario 5: S2 pressed during STOPPED ---");
        btn_rst_n = 1'b1; wait_clks(14);
        check_cond(dut.ctrl_state == 3'd3 && dut.last_btn_event == 3'd3,
                   "SCENARIO 5A: S2 press from STOPPED enters CTRL_RESETTING (3) with EV_BTN_USER_RESET");
        btn_rst_n = 1'b0;
        wait_clks(35);
        check_cond(dut.ctrl_state == 3'd0 && dut.recovery_result == 3'd2 && dut.true_guard_fault == 1'b0,
                   "SCENARIO 5B: S2 reset completes RESETTING -> READY -> RUNNING with REC_OK_READY");

        // --------------------------------------------------------------------
        // SCENARIO 6 & 7: S2 ditekan saat penyebab FAULT masih aktif -> FAULT LATCHED
        //                 & S2 ditekan saat FAULT LATCHED sementara penyebab masih aktif
        // --------------------------------------------------------------------
        $display("--- Scenarios 6 & 7: S2 pressed while fault source is STILL ACTIVE & during FAULT LATCHED ---");
        dut.sim_fault_source_active = 1'b1;
        wait_clks(6);
        // Scenario 7: Press S2 while fault source is still active
        btn_rst_n = 1'b1; wait_clks(14);
        btn_rst_n = 1'b0; wait_clks(14);
        check_cond(dut.ctrl_state == 3'd5 && dut.fault_latched == 1'b1 && dut.recovery_result == 3'd3 && dut.last_btn_event == 3'd5,
                   "SCENARIO 7: S2 pressed while fault source is still active refuses fake clear -> CTRL_FAULT_LATCHED (5)");
        // Scenario 6: Press S2 again while already in FAULT LATCHED with fault still active
        btn_rst_n = 1'b1; wait_clks(14);
        btn_rst_n = 1'b0; wait_clks(14);
        check_cond(dut.ctrl_state == 3'd5 && dut.fault_latched == 1'b1 && dut.recovery_result == 3'd3,
                   "SCENARIO 6: S2 pressed during FAULT LATCHED with active fault stays in CTRL_FAULT_LATCHED");

        // --------------------------------------------------------------------
        // SCENARIO 8 & 12: S2 ditekan setelah penyebab FAULT tidak lagi aktif ->
        //                  RESETTING -> READY -> kembali ke RUNNING setelah recovery
        // --------------------------------------------------------------------
        $display("--- Scenarios 8 & 12: S2 pressed after fault source becomes INACTIVE -> returns to RUNNING ---");
        dut.sim_fault_source_active = 1'b0; // Fault cause removed!
        wait_clks(4);
        btn_rst_n = 1'b1; wait_clks(14);
        check_cond(dut.ctrl_state == 3'd3 && dut.last_btn_event == 3'd4,
                   "SCENARIO 8: S2 pressed after fault cause clears enters CTRL_RESETTING with EV_BTN_FAULT_REC");
        btn_rst_n = 1'b0;
        wait_clks(35);
        cyc_before = dut.tele_cycles;
        wait_clks(12);
        cyc_after  = dut.tele_cycles;
        check_cond(dut.ctrl_state == 3'd0 && dut.fault_latched == 1'b0 && dut.fault_code == 3'd0 && (cyc_after > cyc_before),
                   "SCENARIO 12: After recovery, fault_latched=0 and HCPU resumes active execution in CTRL_RUNNING");

        // --------------------------------------------------------------------
        // SCENARIO 9: S1 dan S2 ditekan bersamaan -> S1 STOP priority wins
        // --------------------------------------------------------------------
        $display("--- Scenario 9: S1 and S2 pressed simultaneously ---");
        mode_key  = 1'b1;
        btn_rst_n = 1'b1;
        wait_clks(14);
        check_cond(dut.ctrl_state == 3'd1 && dut.last_btn_event == 3'd6,
                   "SCENARIO 9: Simultaneous S1+S2 gives highest priority to S1 STOP (CTRL_STOPPED, EV_BTN_S1_S2_STOP)");
        mode_key  = 1'b0;
        btn_rst_n = 1'b0;
        wait_clks(14);
        // Resume via S1
        mode_key = 1'b1; wait_clks(14); mode_key = 1'b0; wait_clks(14);

        // --------------------------------------------------------------------
        // SCENARIO 10: Bounce pada tombol -> filtered out by debounce counter
        // --------------------------------------------------------------------
        $display("--- Scenario 10: Button bounce filtering ---");
        repeat (5) begin
            mode_key = 1'b1; wait_clks(3); // < 8-cycle debounce threshold
            mode_key = 1'b0; wait_clks(3);
        end
        wait_clks(10);
        check_cond(dut.ctrl_state == 3'd0 && dut.s1_deb == 1'b0,
                   "SCENARIO 10: Sub-threshold switch bounce on S1 is completely filtered without false state change");

        // --------------------------------------------------------------------
        // SCENARIO 11: Tombol ditahan lama (Long Hold) -> single edge, no oscillation
        // --------------------------------------------------------------------
        $display("--- Scenario 11: Long button hold without state oscillation ---");
        cyc_before[7:0] = dut.s1_press_cnt;
        mode_key   = 1'b1;
        wait_clks(70); // Hold > BTN_LONG_CLKS (40)
        check_cond(dut.ctrl_state == 3'd2 && dut.s1_long_lat == 1'b1 && (dut.s1_press_cnt == cyc_before[7:0] + 8'd1),
                   "SCENARIO 11A: Long hold on S1 triggers exactly 1 press event and latches s1_long_lat without oscillation");
        mode_key   = 1'b0;
        wait_clks(14);
        check_cond(dut.ctrl_state == 3'd1,
                   "SCENARIO 11B: Releasing S1 after long hold settles cleanly into CTRL_STOPPED");

        // --------------------------------------------------------------------
        // NUI-CENTERED MONITOR VERIFICATION: Dual-BSRAM 90-row + Hologram ROM
        // --------------------------------------------------------------------
        $display("--- NUI-Centered Monitor 90-Row & Hologram ROM Verification ---");
        check_cond(dut.nui_holo_rom[13'd2080] != 8'h00 || dut.nui_holo_rom[13'd4128] != 8'h00,
                   "NUI HOLOGRAM ROM: 128x128 4-bit NUI Brain & Orbital Core BSRAM populated");

        $display("========================================================================");
        $display(" SUMMARY: %0d PASSED, %0d FAILED", pass_cnt, fail_cnt);
        $display("========================================================================");
        if (fail_cnt != 0) $finish(1);
        $finish(0);
    end
endmodule
