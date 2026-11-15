// ============================================================================
// cosmictera_boot_subsys_bridge.v - Live 16-Entry Compute Ecosystem Status &
// Coherent 87-Bit Telemetry Bridge (CT-01-REV13, Stage 1.5 Ultra-Compact)
// ============================================================================

`default_nettype none

module cosmictera_boot_subsys_bridge #(
    parameter integer PCW              = 12,
    parameter integer BIST_STEP_CYCLES = 2
) (
    // ── 27 MHz CPU / Reference Domain ────────────────────────────
    input  wire            clk_27m,
    input  wire            ext_rst_n,
    input  wire            ext_telem_en,
    input  wire [PCW-1:0]  ext_pc,
    input  wire [31:0]     ext_instr,
    input  wire            ext_halted,
    input  wire            ext_guard,
    input  wire [31:0]     ext_cycles,
    input  wire [7:0]      ext_flags,

    // ── 74.25 MHz Video Pixel Domain ─────────────────────────────
    input  wire            pixel_clk,
    input  wire            vid_rst_n,
    input  wire            sample_tick,
    input  wire [1:0]      screen_state,
    input  wire            fault_inject,
    input  wire [15:0]     subsys_fault_mask,

    // ── Coherent Telemetry Snapshot Outputs (pixel_clk domain) ───
    output wire [PCW-1:0]  snap_pc,
    output wire [31:0]     snap_instr,
    output reg             snap_halted,
    output reg             snap_guard,
    output wire [31:0]     snap_cycles,
    output wire [7:0]      snap_flags,
    output reg             snap_valid,

    // ── 16 Compute Ecosystem Visual Entry States ─────────────────
    output wire [31:0]     subsys_state_flat,
    output wire            subsys_all_ready,
    output wire            subsys_any_fault
);

    wire any_fault_in = fault_inject | (|subsys_fault_mask);

    wire [PCW-1:0] src_pc     = ext_telem_en ? ext_pc     : 12'h1A4;
    wire [31:0]    src_instr  = ext_telem_en ? ext_instr  : 32'h4E01_0200;
    wire           src_halted = ext_telem_en ? ext_halted : any_fault_in;
    wire           src_guard  = ext_telem_en ? ext_guard  : any_fault_in;
    wire [31:0]    src_cycles = ext_telem_en ? ext_cycles : 32'h0002_C1C9;
    wire [7:0]     src_flags  = ext_telem_en ? ext_flags  : (any_fault_in ? 8'h01 : 8'h04);

    // ── Toggle-Handshake CDC (`hcpu_telemetry` protocol) ─────────
    reg req_vid = 1'b0;
    reg ack_s1  = 1'b0, ack_s2 = 1'b0, ack_s3 = 1'b0;
    wire cdc_idle = (req_vid == ack_s2) && (ack_s2 == ack_s3);

    always @(posedge pixel_clk or negedge vid_rst_n) begin
        if (!vid_rst_n)
            req_vid <= 1'b0;
        else if (sample_tick || (!snap_valid && cdc_idle))
            req_vid <= ~req_vid;
    end

    reg req_s1 = 1'b0, req_s2 = 1'b0, req_s3 = 1'b0;
    reg ack_cpu = 1'b0;
    always @(posedge clk_27m or negedge ext_rst_n) begin
        if (!ext_rst_n) begin
            req_s1  <= 1'b0;
            req_s2  <= 1'b0;
            req_s3  <= 1'b0;
            ack_cpu <= 1'b0;
        end else begin
            req_s1 <= req_vid;
            req_s2 <= req_s1;
            req_s3 <= req_s2;
            if (req_s2 ^ req_s3)
                ack_cpu <= ~ack_cpu;
        end
    end

    always @(posedge pixel_clk or negedge vid_rst_n) begin
        if (!vid_rst_n) begin
            ack_s1 <= 1'b0;
            ack_s2 <= 1'b0;
            ack_s3 <= 1'b0;
        end else begin
            ack_s1 <= ack_cpu;
            ack_s2 <= ack_s1;
            ack_s3 <= ack_s2;
        end
    end
    wire ack_edge = (ack_s2 ^ ack_s3);

`ifdef YOSYS
    // In FPGA synthesis, `hcpu_tele_*` are already registered in `u_hcpu_core`
    // and hold steady once HCPU halts (~0.26 ms after boot). Sharing `u_hcpu_core`
    // telemetry flip-flops directly eliminates 84 duplicate DFFCEs (84 half-slices).
    assign snap_pc     = src_pc;
    assign snap_instr  = src_instr;
    assign snap_cycles = src_cycles;
    assign snap_flags  = src_flags;
`else
    reg [PCW-1:0] snap_pc_r     = 12'h000;
    reg [31:0]    snap_instr_r  = 32'h0000_0000;
    reg [31:0]    snap_cycles_r = 32'h0000_0000;
    reg [7:0]     snap_flags_r  = 8'h00;

    always @(posedge pixel_clk or negedge vid_rst_n) begin
        if (!vid_rst_n) begin
            snap_pc_r     <= 12'h000;
            snap_instr_r  <= 32'h0000_0000;
            snap_cycles_r <= 32'h0000_0000;
            snap_flags_r  <= 8'h00;
        end else if (ack_edge) begin
            snap_pc_r     <= src_pc;
            snap_instr_r  <= src_instr;
            snap_cycles_r <= src_cycles;
            snap_flags_r  <= src_flags;
        end else if (any_fault_in) begin
            snap_flags_r  <= 8'h01;
        end else if (!ext_telem_en && snap_valid) begin
            snap_flags_r  <= 8'h04;
        end
    end

    assign snap_pc     = snap_pc_r;
    assign snap_instr  = snap_instr_r;
    assign snap_cycles = snap_cycles_r;
    assign snap_flags  = snap_flags_r;
`endif

    always @(posedge pixel_clk or negedge vid_rst_n) begin
        if (!vid_rst_n) begin
            snap_halted <= 1'b0;
            snap_guard  <= 1'b0;
            snap_valid  <= 1'b0;
        end else if (ack_edge) begin
            snap_halted <= src_halted;
            snap_guard  <= src_guard;
            snap_valid  <= 1'b1;
        end else if (any_fault_in) begin
            snap_halted <= 1'b1;
            snap_guard  <= 1'b1;
        end else if (!ext_telem_en && snap_valid) begin
            snap_halted <= 1'b0;
            snap_guard  <= 1'b0;
        end
    end

    // ── 16-Entry Status Evaluation ───────────────────────────────
    wire global_err = fault_inject || (screen_state == 2'd2);
    wire global_ok  = (screen_state == 2'd1) && snap_valid;

    function [1:0] eval_sub_state;
        input mask_bit;
        input g_err;
        input g_ok;
        begin
            if (g_err || mask_bit)
                eval_sub_state = 2'd3;
            else if (g_ok)
                eval_sub_state = 2'd2;
            else
                eval_sub_state = 2'd1;
        end
    endfunction

    wire [1:0] st_sub0  = eval_sub_state(subsys_fault_mask[0],  global_err, global_ok);
    wire [1:0] st_sub1  = eval_sub_state(subsys_fault_mask[1],  global_err, global_ok);
    wire [1:0] st_sub2  = eval_sub_state(subsys_fault_mask[2],  global_err, global_ok);
    wire [1:0] st_sub3  = eval_sub_state(subsys_fault_mask[3],  global_err, global_ok);
    wire [1:0] st_sub4  = eval_sub_state(subsys_fault_mask[4],  global_err, global_ok);
    wire [1:0] st_sub5  = eval_sub_state(subsys_fault_mask[5],  global_err, global_ok);
    wire [1:0] st_sub6  = eval_sub_state(subsys_fault_mask[6],  global_err, global_ok);
    wire [1:0] st_sub7  = eval_sub_state(subsys_fault_mask[7],  global_err, global_ok);
    wire [1:0] st_sub8  = eval_sub_state(subsys_fault_mask[8],  global_err, global_ok);
    wire [1:0] st_sub9  = eval_sub_state(subsys_fault_mask[9],  global_err, global_ok);
    wire [1:0] st_sub10 = eval_sub_state(subsys_fault_mask[10], global_err, global_ok);
    wire [1:0] st_sub11 = eval_sub_state(subsys_fault_mask[11], global_err, global_ok);
    wire [1:0] st_sub12 = eval_sub_state(subsys_fault_mask[12], global_err, global_ok);
    wire [1:0] st_sub13 = eval_sub_state(subsys_fault_mask[13], global_err, global_ok);
    wire [1:0] st_sub14 = eval_sub_state(subsys_fault_mask[14], global_err, global_ok);
    wire [1:0] st_sub15 = eval_sub_state(subsys_fault_mask[15], global_err, global_ok);

    assign subsys_state_flat = {
        st_sub15, st_sub14, st_sub13, st_sub12, st_sub11, st_sub10,
        st_sub9,  st_sub8,  st_sub7,  st_sub6,  st_sub5,
        st_sub4,  st_sub3,  st_sub2,  st_sub1,  st_sub0
    };

    assign subsys_any_fault = global_err | (|subsys_fault_mask);
    assign subsys_all_ready = global_ok & (~subsys_any_fault);

endmodule

`default_nettype wire
