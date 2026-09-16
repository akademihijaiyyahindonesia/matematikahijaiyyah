// hcpu_compositor.v — the character for a cell, chosen as the beam arrives.
//
// What this replaces, and why. M5.2A built the screen the usual way: a painter
// wrote 128 cells per frame into a 16,384 x 16 text RAM, and the renderer read
// that RAM back. It simulated correctly and nextpnr refused to place it --
// 16,882 LUT4 against a control of 15,933 that places and routes with zero
// violations. The storage was not free in the way storage usually is: a RAM
// with a write port is a RAM, eleven BSRAM blocks of it, and it sits in the
// middle of the fabric between the CPU and the video path.
//
// So the RAM goes and nothing above it changes. Same 160 x 90 geometry, same
// six telemetry fields, same pages, same headline. The character simply is not
// stored any more -- it is decided:
//
//     cell address ──┬──► layout ROM        (labels, rules, NOT INSTRUMENTED)
//                    └──► this module       (the live fields)
//                              │
//                         one of the two wins, per cell
//
// The layout ROM is read-only, which is the whole point: no write port, no
// painter, no sequencer, and a memory the tools may place as ROM.
//
// ── the override is a window test, not a lookup ─────────────────
// Eight fields, each a run of cells starting at a known address. A cell is
// live if it falls inside one of those runs, and its position in the field is
// the offset. Eight comparisons against a 14-bit address, and the winner
// feeds one mux. Only one can match -- the generator lays them out apart --
// so the priority order below is a tie-break that never happens.
//
// ── what it still refuses to invent ─────────────────────────────
// `snap_valid` low means no snapshot has been taken yet, and STATE then reads
// NOT INSTRUMENTED rather than RUNNING. Every field the hardware does not
// expose has no window here at all: it is in the layout ROM, spelled out, and
// this module never touches it.

`default_nettype none

`include "hcpu_dashboard_pos.vh"

module hcpu_compositor #(
    parameter PCW = 12
) (
    input  wire [13:0] cell_addr,

    input  wire [3:0]  page,
    input  wire [PCW-1:0] snap_pc,
    input  wire [31:0]    snap_instr,
    input  wire           snap_halted,
    input  wire           snap_guard,
    input  wire [31:0]    snap_cycles,
    input  wire [7:0]     snap_flags,
    input  wire           snap_valid,

    output reg         hit,        // this cell is a live field
    output reg  [7:0]  ch,
    output reg  [3:0]  at
);

    localparam [3:0] C_DIM   = 4'd0, C_WHITE = 4'd1, C_CYAN  = 4'd2,
                     C_GREEN = 4'd3, C_YELLOW= 4'd4, C_RED   = 4'd5,
                     C_BLUE  = 4'd6, C_GOLD  = 4'd7;

    function [7:0] hexd;
        input [3:0] n;
        hexd = (n < 4'd10) ? (8'h30 + {4'd0, n}) : (8'h41 + {4'd0, n} - 8'd10);
    endfunction

    function [7:0] hex32;
        input [31:0] v;
        input [3:0]  p;
        case (p)
            4'd2: hex32 = hexd(v[31:28]);  4'd3: hex32 = hexd(v[27:24]);
            4'd4: hex32 = hexd(v[23:20]);  4'd5: hex32 = hexd(v[19:16]);
            4'd6: hex32 = hexd(v[15:12]);  4'd7: hex32 = hexd(v[11:8]);
            4'd8: hex32 = hexd(v[7:4]);    4'd9: hex32 = hexd(v[3:0]);
            default: hex32 = 8'h20;
        endcase
    endfunction

    function [7:0] ni_char;
        input [3:0] p;
        case (p)
            4'd0: ni_char = "N"; 4'd1: ni_char = "O"; 4'd2: ni_char = "T";
            4'd3: ni_char = " "; 4'd4: ni_char = "I"; 4'd5: ni_char = "N";
            4'd6: ni_char = "S"; 4'd7: ni_char = "T"; 4'd8: ni_char = "R";
            4'd9: ni_char = "U"; 4'd10: ni_char = "M"; 4'd11: ni_char = "E";
            4'd12: ni_char = "N"; 4'd13: ni_char = "T"; 4'd14: ni_char = "E";
            default: ni_char = "D";
        endcase
    endfunction

    // Each field is sixteen cells wide in the address map, so the offset is
    // the low four bits and the window test is one compare of the top ten.
    // The generator places every field on a multiple-of-sixteen boundary for
    // exactly this reason -- an arbitrary base would cost a subtractor each.
    wire [9:0] blk = cell_addr[13:4];
    wire [3:0] pos = cell_addr[3:0];

    localparam [9:0] BLK_STATE  = `DASH_STATE_ADDR  >> 4;
    localparam [9:0] BLK_PC     = `DASH_PC_ADDR     >> 4;
    localparam [9:0] BLK_INSTR  = `DASH_INSTR_ADDR  >> 4;
    localparam [9:0] BLK_CYCLE  = `DASH_CYCLE_ADDR  >> 4;
    localparam [9:0] BLK_FLAGS  = `DASH_FLAGS_ADDR  >> 4;
    localparam [9:0] BLK_GUARD  = `DASH_GUARD_ADDR  >> 4;
    localparam [9:0] BLK_PAGE   = `DASH_PAGE_ADDR   >> 4;
    localparam [9:0] BLK_BANNER = `DASH_BANNER_ADDR >> 4;

    localparam [3:0] OFF_PAGE = `DASH_PAGE_ADDR & 14'hF;

    // NO SNAPSHOT, NO NUMBERS -- and that applies to all six live fields, not
    // just STATE. Without it a display node with no CPU behind it prints PC as
    // 0X000 and CYCLE as 0X00000000: values, that look like values, and are
    // not. `snap_valid` stays low until telemetry has answered once, and until
    // then every live field spells out what it does not have.
    wire live = snap_valid;

    always @* begin
        hit = 1'b1;
        ch  = 8'h20;
        at  = C_DIM;

        if (blk == BLK_STATE) begin
            at = snap_halted ? C_RED : C_GREEN;
            if (!live) begin
                at = C_DIM;
                ch = ni_char(pos);
            end else case (pos)
                4'd0: ch = snap_halted ? "H" : "R";
                4'd1: ch = snap_halted ? "A" : "U";
                4'd2: ch = snap_halted ? "L" : "N";
                4'd3: ch = snap_halted ? "T" : "N";
                4'd4: ch = snap_halted ? "E" : "I";
                4'd5: ch = snap_halted ? "D" : "N";
                4'd6: ch = snap_halted ? " " : "G";
                default: ch = " ";
            endcase
        end else if (blk == BLK_PC) begin
            at = C_WHITE;
            if (!live) begin
                at = C_DIM;
                ch = ni_char(pos);
            end else case (pos)
                4'd0: ch = "0";  4'd1: ch = "X";
                4'd2: ch = hexd(snap_pc[11:8]);
                4'd3: ch = hexd(snap_pc[7:4]);
                4'd4: ch = hexd(snap_pc[3:0]);
                default: ch = " ";
            endcase
        end else if (blk == BLK_INSTR) begin
            at = C_WHITE;
            if (!live) begin
                at = C_DIM;
                ch = ni_char(pos);
            end else case (pos)
                4'd0: ch = "0";  4'd1: ch = "X";
                default: ch = hex32(snap_instr, pos);
            endcase
        end else if (blk == BLK_CYCLE) begin
            at = C_WHITE;
            if (!live) begin
                at = C_DIM;
                ch = ni_char(pos);
            end else case (pos)
                4'd0: ch = "0";  4'd1: ch = "X";
                default: ch = hex32(snap_cycles, pos);
            endcase
        end else if (blk == BLK_FLAGS) begin
            at = C_WHITE;
            if (!live) begin
                at = C_DIM;
                ch = ni_char(pos);
            end else case (pos)
                4'd0: ch = "0";  4'd1: ch = "X";
                4'd2: ch = hexd(snap_flags[7:4]);
                4'd3: ch = hexd(snap_flags[3:0]);
                default: ch = " ";
            endcase
        end else if (blk == BLK_GUARD) begin
            // guard_led is the live GUARD flag: high means a guard caught
            // something, so green is the case where it is low.
            at = snap_guard ? C_RED : C_GREEN;
            if (!live) begin
                at = C_DIM;
                ch = ni_char(pos);
            end else case (pos)
                4'd0: ch = snap_guard ? "F" : "O";
                4'd1: ch = snap_guard ? "A" : "K";
                4'd2: ch = snap_guard ? "U" : " ";
                4'd3: ch = snap_guard ? "L" : " ";
                4'd4: ch = snap_guard ? "T" : " ";
                default: ch = " ";
            endcase
        end else if (blk == BLK_PAGE && pos == OFF_PAGE) begin
            // One cell, not sixteen: the label sits beside it.
            at = C_WHITE;
            ch = hexd(page);
        end else if (blk == BLK_BANNER) begin
            at = C_YELLOW;
            ch = (page == 4'd0) ? 8'h20 : ni_char(pos);
        end else begin
            hit = 1'b0;
        end
    end

endmodule

`default_nettype wire
