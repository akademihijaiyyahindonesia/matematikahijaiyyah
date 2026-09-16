// tb_hcpu_dashboard.v — the compositor picks a character, and only where it should.
//
// M5.2A built this screen with a painter and a text RAM, and nextpnr refused
// to place it. M5.2B decides the character as the beam arrives instead: the
// layout ROM holds everything fixed and hcpu_compositor.v overrides the eight
// live fields. This bench moved with it, and checks the same three things it
// always did -- what, where, and nothing else.
//
// ── where is the half that matters ──────────────────────────────
// A wrong character is visible. A character claimed for the wrong CELL is not:
// it lands on a label and quietly destroys the text that says what the number
// beside it means. So most of what follows is about `hit` -- the signal that
// says "this cell is mine" -- and the address windows behind it.
//
// The windows are sixteen cells wide and start on multiples of sixteen, which
// is why rtl/scripts/gen_dashboard.py puts every value at column 16. This
// bench walks the whole 14,400-cell screen and counts, so a window that
// overlapped a label or ran past its field would be caught by arithmetic
// rather than by someone looking at a monitor.

`timescale 1ns/1ps
`default_nettype none

`include "hcpu_dashboard_pos.vh"

module tb_hcpu_dashboard;

    reg [13:0] cell_addr = 14'd0;
    reg [3:0]  page = 4'd0;
    reg [11:0] snap_pc = 12'h1A3;
    reg [31:0] snap_instr = 32'hDEADBEEF;
    reg        snap_halted = 1'b0;
    reg        snap_guard = 1'b0;
    reg [31:0] snap_cycles = 32'h0012_3456;
    reg [7:0]  snap_flags = 8'h5C;
    reg        snap_valid = 1'b1;

    wire       hit;
    wire [7:0] ch;
    wire [3:0] at;

    hcpu_compositor #(.PCW(12)) dut (
        .cell_addr(cell_addr), .page(page),
        .snap_pc(snap_pc), .snap_instr(snap_instr), .snap_halted(snap_halted),
        .snap_guard(snap_guard), .snap_cycles(snap_cycles),
        .snap_flags(snap_flags), .snap_valid(snap_valid),
        .hit(hit), .ch(ch), .at(at)
    );

    integer errors = 0;
    task check(input cond, input [255:0] what);
        begin
            if (!cond) begin
                $display("  GAGAL: %0s", what);
                errors = errors + 1;
            end else
                $display("  ok   : %0s", what);
        end
    endtask

    task at_cell;                      // settle the combinational path
        input [13:0] a;
        begin
            cell_addr = a;
            #1;
        end
    endtask

    integer i;
    reg ok_field;
    integer hits;

    initial begin
        $display("=== tb_hcpu_dashboard: compositor memilih sel, bukan menulisnya ===");

        // ── PC: "0X" then three nibbles of 0x1A3 ────────────────
        ok_field = 1'b1;
        at_cell(`DASH_PC_ADDR + 0); if (ch !== "0" || !hit) ok_field = 1'b0;
        at_cell(`DASH_PC_ADDR + 1); if (ch !== "X") ok_field = 1'b0;
        at_cell(`DASH_PC_ADDR + 2); if (ch !== "1") ok_field = 1'b0;
        at_cell(`DASH_PC_ADDR + 3); if (ch !== "A") ok_field = 1'b0;
        at_cell(`DASH_PC_ADDR + 4); if (ch !== "3") ok_field = 1'b0;
        check(ok_field, "PC tercetak 0X1A3");

        ok_field = 1'b1;
        for (i = 2; i < 10; i = i + 1) begin
            at_cell(`DASH_INSTR_ADDR + i[3:0]);
            case (i)
                2: if (ch !== "D") ok_field = 1'b0;
                3: if (ch !== "E") ok_field = 1'b0;
                4: if (ch !== "A") ok_field = 1'b0;
                5: if (ch !== "D") ok_field = 1'b0;
                6: if (ch !== "B") ok_field = 1'b0;
                7: if (ch !== "E") ok_field = 1'b0;
                8: if (ch !== "E") ok_field = 1'b0;
                9: if (ch !== "F") ok_field = 1'b0;
            endcase
        end
        check(ok_field, "INSTR tercetak DEADBEEF");

        ok_field = 1'b1;
        at_cell(`DASH_CYCLE_ADDR + 6); if (ch !== "3") ok_field = 1'b0;
        at_cell(`DASH_CYCLE_ADDR + 7); if (ch !== "4") ok_field = 1'b0;
        at_cell(`DASH_CYCLE_ADDR + 8); if (ch !== "5") ok_field = 1'b0;
        at_cell(`DASH_CYCLE_ADDR + 9); if (ch !== "6") ok_field = 1'b0;
        check(ok_field, "CYCLE tercetak 123456");

        ok_field = 1'b1;
        at_cell(`DASH_FLAGS_ADDR + 2); if (ch !== "5") ok_field = 1'b0;
        at_cell(`DASH_FLAGS_ADDR + 3); if (ch !== "C") ok_field = 1'b0;
        check(ok_field, "FLAGS tercetak 5C");

        // ── STATE, and the colour that travels with it ──────────
        ok_field = 1'b1;
        at_cell(`DASH_STATE_ADDR + 0);
        if (ch !== "R" || at !== 4'd3) ok_field = 1'b0;      // GREEN
        at_cell(`DASH_STATE_ADDR + 6); if (ch !== "G") ok_field = 1'b0;
        check(ok_field, "STATE RUNNING, hijau");

        snap_halted = 1'b1;
        snap_guard  = 1'b1;
        ok_field = 1'b1;
        at_cell(`DASH_STATE_ADDR + 0);
        if (ch !== "H" || at !== 4'd5) ok_field = 1'b0;      // RED
        at_cell(`DASH_STATE_ADDR + 5); if (ch !== "D") ok_field = 1'b0;
        at_cell(`DASH_GUARD_ADDR + 0);
        if (ch !== "F" || at !== 4'd5) ok_field = 1'b0;
        check(ok_field, "HALTED dan FAULT, merah");
        snap_halted = 1'b0;
        snap_guard  = 1'b0;

        // ── the page digit owns ONE cell ────────────────────────
        page = 4'd3;
        at_cell(`DASH_PAGE_ADDR);
        check(hit && ch == "3", "digit halaman tercetak 3");

        ok_field = 1'b1;
        for (i = 1; i < 6; i = i + 1) begin
            at_cell(`DASH_PAGE_ADDR + i[3:0]);
            if (hit) ok_field = 1'b0;
        end
        check(ok_field, "digit halaman: satu sel saja");

        // ── the banner follows the page ─────────────────────────
        ok_field = 1'b1;
        at_cell(`DASH_BANNER_ADDR + 0);  if (ch !== "N") ok_field = 1'b0;
        at_cell(`DASH_BANNER_ADDR + 15); if (ch !== "D") ok_field = 1'b0;
        check(ok_field, "halaman 3: NOT INSTRUMENTED");

        page = 4'd0;
        at_cell(`DASH_BANNER_ADDR + 0);
        check(hit && ch == " ", "halaman 0: banner kosong");

        // ── no snapshot, no claim ───────────────────────────────
        // Every live field, not just STATE. A display node with no CPU behind
        // it must not print PC as 0X000: that is a value, it looks like a
        // value, and there is nothing behind it.
        snap_valid = 1'b0;
        ok_field = 1'b1;
        at_cell(`DASH_STATE_ADDR + 0); if (ch !== "N") ok_field = 1'b0;
        at_cell(`DASH_PC_ADDR    + 0); if (ch !== "N") ok_field = 1'b0;
        at_cell(`DASH_PC_ADDR    + 4); if (ch !== "I") ok_field = 1'b0;
        at_cell(`DASH_INSTR_ADDR + 0); if (ch !== "N") ok_field = 1'b0;
        at_cell(`DASH_CYCLE_ADDR + 0); if (ch !== "N") ok_field = 1'b0;
        at_cell(`DASH_FLAGS_ADDR + 0); if (ch !== "N") ok_field = 1'b0;
        at_cell(`DASH_GUARD_ADDR + 0); if (ch !== "N") ok_field = 1'b0;
        check(ok_field, "tanpa snapshot: enam field NI");

        // The page digit is not telemetry and must still be real.
        page = 4'd5;
        at_cell(`DASH_PAGE_ADDR);
        check(hit && ch == "5", "halaman tetap nyata tanpa CPU");
        page = 4'd0;
        snap_valid = 1'b1;

        // ── THE WHOLE SCREEN: how many cells does it claim? ─────
        // Six fields of sixteen, the banner's sixteen, and one page digit.
        // If a window overlapped a label or ran past its field, this number
        // moves -- and nothing else in this bench would notice.
        hits = 0;
        for (i = 0; i < 14400; i = i + 1) begin
            at_cell(i[13:0]);
            if (hit) hits = hits + 1;
        end
        $display("  sel diklaim compositor: %0d", hits);
        check(hits == 113, "113 sel diklaim, sisanya ROM");

        if (errors == 0)
            $display("tb_hcpu_dashboard: SEMUA LULUS (13 pemeriksaan)");
        else
            $display("tb_hcpu_dashboard: %0d GAGAL", errors);
        $finish;
    end

endmodule

`default_nettype wire
