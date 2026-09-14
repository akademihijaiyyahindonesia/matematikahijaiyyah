// sd_card_model.v — a card that answers, so the controller can be wrong.
//
// A testbench that drives hcpu_sdio.v and watches its own outputs proves that
// the module agrees with itself. What it cannot show is whether a real card
// would have understood a word of it. This model is the other side of the
// wire: it decodes the 48-bit command frames, checks their CRC7, answers in
// the response format each command actually uses, and moves 512-byte blocks
// with a CRC16 it computes itself.
//
// It is deliberately strict where the standard is strict:
//
//   * a command frame whose CRC7 is wrong is ignored, not answered
//   * a command that arrives before the previous one's Ncc has elapsed is
//     ignored, not answered -- see below
//   * CMD17 and CMD24 are ignored unless CMD7 selected this card
//   * ACMD41 reports "still busy" a few times before reporting ready, which is
//     what a real card does and what makes the controller's retry loop real
//   * a written block whose CRC16 does not match is refused with 101, and the
//     data is NOT stored
//
// Each of those is a way for the controller to be wrong that a permissive
// model would hide.
//
// ── Ncc, and why it is the one timing rule this model does keep ─
// The standard gives the card at least EIGHT idle clocks between one command
// and the next. This model used to ignore that, and the cost was not
// theoretical: hcpu_sdio.v sent CMD8 with a gap of ZERO after CMD0, this model
// answered anyway, twelve checks stayed green, and the real card on the board
// said nothing at all -- E_CMD8, a full 100 ms timeout, four runs.
//
// So a command whose start bit arrives before NCC_MIN idle clocks have passed
// is now DROPPED, exactly as a real card drops it: no response, no state
// change, and `n_ncc_reject` counts it so a bench can assert on the refusal
// rather than only on the silence that follows.
//
// ── what it is still not ────────────────────────────────────────
// Not a timing model anywhere else. Ncr/Nwr are held at legal minimums rather
// than swept, and the card never stretches the clock. It answers the protocol,
// not the datasheet's worst case.

`default_nettype none

module sd_card_model #(
    parameter integer SECTORS   = 16,     // how much of a card to pretend to be
    parameter integer ACMD41_BUSY = 3,    // times it says "not ready yet"
    parameter         HIGH_CAP  = 1'b1,   // OCR bit 30: block addressing
    parameter integer NCC_MIN   = 8       // idle clocks owed between commands
) (
    input  wire sd_clk,
    input  wire cmd_line,                 // the resolved CMD line
    output reg  cmd_out,
    output reg  cmd_oe,
    input  wire dat_line,                 // the resolved DAT0 line
    output reg  dat_out,
    output reg  dat_oe
);

    localparam [15:0] RCA = 16'hAAAA;

    reg [7:0] mem [0:SECTORS*512-1];

    reg [47:0] frame;
    reg [5:0]  cmd_idx;
    reg [31:0] cmd_arg;
    reg        app_cmd;                   // CMD55 came immediately before
    reg        selected;
    reg [31:0] busy_left;
    integer    i;

    // Counts what the card was actually asked to do, so a bench can assert on
    // the card's side of the conversation rather than only the host's.
    integer n_cmd0, n_cmd8, n_acmd41, n_cmd2, n_cmd3, n_cmd7, n_cmd16;
    integer n_read, n_write, n_crc_reject, n_bad_crc7;

    // Ncc bookkeeping. `idle_clks` is counted in the receive loop itself
    // rather than by a second process, so there is no cross-process read of a
    // counter on the same edge that writes it. `gap_after_cmd0` remembers the
    // one boundary that was broken, so a bench can assert the number and not
    // merely that nothing was refused.
    integer n_ncc_reject;
    integer idle_clks;
    integer gap_after_cmd0;
    reg     last_was_cmd0;

    function [6:0] crc7_of;
        input [39:0] m;
        integer k;
        reg [6:0] c;
        begin
            c = 7'd0;
            for (k = 39; k >= 0; k = k - 1)
                c = {c[5:0], 1'b0} ^ ((c[6] ^ m[k]) ? 7'h09 : 7'h00);
            crc7_of = c;
        end
    endfunction

    task send_response;
        input [135:0] value;
        input integer len;
        integer k;
        begin
            // Ncr: the card waits a couple of clocks before it answers. Two is
            // the legal minimum and the one a controller is most likely to get
            // wrong by starting to listen too late.
            repeat (2) @(posedge sd_clk);
            cmd_oe = 1'b1;
            for (k = len - 1; k >= 0; k = k - 1) begin
                @(negedge sd_clk);
                cmd_out = value[k];
            end
            @(negedge sd_clk);
            cmd_out = 1'b1;
            cmd_oe  = 1'b0;
        end
    endtask

    function [47:0] r1;
        input [5:0] idx;
        input [31:0] status;
        reg [39:0] head;
        begin
            head = {2'b00, idx, status};
            head[39:38] = 2'b00;          // start 0, direction 0 (card -> host)
            r1 = {head, crc7_of(head), 1'b1};
        end
    endfunction

    // ── receive one command frame ───────────────────────────────
    task get_frame;
        integer k;
        begin
            frame[47] = 1'b0;
            for (k = 46; k >= 0; k = k - 1) begin
                @(posedge sd_clk);
                frame[k] = cmd_line;
            end
            cmd_idx = frame[45:40];
            cmd_arg = frame[39:8];
        end
    endtask

    // ── a block out, and a block in ─────────────────────────────
    task send_block;
        input [31:0] lba;
        integer k, b;
        reg [15:0] crc;
        reg [7:0]  byte_v;
        begin
            repeat (4) @(negedge sd_clk);
            dat_oe  = 1'b1;
            dat_out = 1'b0;               // start bit
            crc = 16'd0;
            for (b = 0; b < 512; b = b + 1) begin
                byte_v = mem[lba*512 + b];
                for (k = 7; k >= 0; k = k - 1) begin
                    @(negedge sd_clk);
                    dat_out = byte_v[k];
                    crc = {crc[14:0], 1'b0} ^ ((crc[15] ^ byte_v[k]) ? 16'h1021
                                                                    : 16'h0000);
                end
            end
            for (k = 15; k >= 0; k = k - 1) begin
                @(negedge sd_clk);
                dat_out = crc[k];
            end
            @(negedge sd_clk);
            dat_out = 1'b1;               // end bit
            @(negedge sd_clk);
            dat_oe = 1'b0;
        end
    endtask

    task recv_block;
        input [31:0] lba;
        integer k, b;
        reg [15:0] crc, crc_rx;
        reg [7:0]  byte_v;
        reg [7:0]  staging [0:511];
        begin
            // Wait for the host's start bit.
            @(posedge sd_clk);
            while (dat_line !== 1'b0) @(posedge sd_clk);
            crc = 16'd0;
            for (b = 0; b < 512; b = b + 1) begin
                for (k = 7; k >= 0; k = k - 1) begin
                    @(posedge sd_clk);
                    byte_v[k] = dat_line;
                    crc = {crc[14:0], 1'b0} ^ ((crc[15] ^ dat_line) ? 16'h1021
                                                                   : 16'h0000);
                end
                staging[b] = byte_v;
            end
            crc_rx = 16'd0;
            for (k = 15; k >= 0; k = k - 1) begin
                @(posedge sd_clk);
                crc_rx = {crc_rx[14:0], dat_line};
            end
            @(posedge sd_clk);            // the host's end bit

            // The verdict, and it is not a formality: a block that fails here
            // must NOT reach mem, or a corrupt write would read back clean.
            repeat (2) @(negedge sd_clk);
            dat_oe  = 1'b1;
            dat_out = 1'b0;               // status start bit
            if (crc_rx == crc) begin
                for (b = 0; b < 512; b = b + 1)
                    mem[lba*512 + b] = staging[b];
                @(negedge sd_clk); dat_out = 1'b0;
                @(negedge sd_clk); dat_out = 1'b1;
                @(negedge sd_clk); dat_out = 1'b0;   // 010 = accepted
            end else begin
                n_crc_reject = n_crc_reject + 1;
                @(negedge sd_clk); dat_out = 1'b1;
                @(negedge sd_clk); dat_out = 1'b0;
                @(negedge sd_clk); dat_out = 1'b1;   // 101 = CRC error
            end
            @(negedge sd_clk); dat_out = 1'b1;       // status end bit
            // Programming: DAT0 held low, which is the whole reason a
            // controller must wait instead of firing the next command.
            @(negedge sd_clk); dat_out = 1'b0;
            repeat (16) @(negedge sd_clk);
            dat_out = 1'b1;
            @(negedge sd_clk);
            dat_oe = 1'b0;
        end
    endtask

    reg [31:0] ocr;
    reg [135:0] cid;

    initial begin
        cmd_oe = 1'b0; cmd_out = 1'b1;
        dat_oe = 1'b0; dat_out = 1'b1;
        app_cmd = 1'b0; selected = 1'b0;
        busy_left = ACMD41_BUSY;
        n_cmd0 = 0; n_cmd8 = 0; n_acmd41 = 0; n_cmd2 = 0; n_cmd3 = 0;
        n_cmd7 = 0; n_cmd16 = 0; n_read = 0; n_write = 0;
        n_crc_reject = 0; n_bad_crc7 = 0;
        n_ncc_reject = 0; idle_clks = 0;
        gap_after_cmd0 = -1; last_was_cmd0 = 1'b0;
        for (i = 0; i < SECTORS*512; i = i + 1) mem[i] = 8'h00;

        // R2 is 136 bits: start, direction, six reserved ones, CID[127:1],
        // end. The reserved field is all ones and the CRC lives inside the
        // CID's own last byte, which is why nothing here computes one.
        cid = {2'b00, 6'b111111,
               127'h1234_5678_9ABC_DEF0_1122_3344_5566_7788, 1'b1};

        forever begin
            // ── how many clocks passed before this command arrived ──
            // Counted here, in the receiving process itself. `idle_clks` is
            // clocks since the PREVIOUS FRAME'S END BIT, which for a command
            // the card answered includes the response it sent -- those are
            // always far past the minimum, so the only boundary this number
            // ever decides is the one after a command with no response at all.
            // That is CMD0, and that is the boundary that was broken.
            idle_clks = 0;
            @(posedge sd_clk);
            while (cmd_oe || cmd_line !== 1'b0) begin
                idle_clks = idle_clks + 1;
                @(posedge sd_clk);
            end

            begin
                get_frame;

                if (last_was_cmd0 && gap_after_cmd0 < 0)
                    gap_after_cmd0 = idle_clks;
                last_was_cmd0 = 1'b0;

                if (idle_clks < NCC_MIN) begin
                    // Too soon. A real card is still finishing with the last
                    // command and never hears this one, so neither does this
                    // one: no response, no state change, and the silence that
                    // follows is the host's problem to notice.
                    n_ncc_reject = n_ncc_reject + 1;
                end else if (crc7_of(frame[47:8]) !== frame[7:1]) begin
                    // A frame the card cannot trust is a frame it never heard.
                    n_bad_crc7 = n_bad_crc7 + 1;
                end else begin
                    case (cmd_idx)
                    6'd0: begin
                        n_cmd0   = n_cmd0 + 1;
                        selected = 1'b0;
                        app_cmd  = 1'b0;
                        // CMD0 sends no response, so the next command's gap is
                        // the host's alone to provide. Remember to measure it.
                        last_was_cmd0 = 1'b1;
                    end
                    6'd8: begin
                        n_cmd8 = n_cmd8 + 1;
                        // R7 echoes voltage and check pattern in the argument.
                        send_response({88'd0, 2'b00, 6'd8, cmd_arg,
                                       crc7_of({2'b00, 6'd8, cmd_arg}), 1'b1},
                                      48);
                    end
                    6'd55: begin
                        app_cmd = 1'b1;
                        send_response({88'd0, r1(6'd55, 32'h0000_0120)}, 48);
                    end
                    6'd41: begin
                        if (app_cmd) begin
                            n_acmd41 = n_acmd41 + 1;
                            if (busy_left > 0) begin
                                busy_left = busy_left - 1;
                                ocr = {1'b0, 1'b0, 30'h00FF_8000};
                            end else begin
                                ocr = {1'b1, HIGH_CAP, 30'h00FF_8000};
                            end
                            // R3 carries no CRC: the field is all ones.
                            send_response({88'd0, 2'b00, 6'b111111, ocr,
                                           7'b1111111, 1'b1}, 48);
                        end
                        app_cmd = 1'b0;
                    end
                    6'd2: begin
                        n_cmd2 = n_cmd2 + 1;
                        send_response(cid, 136);
                    end
                    6'd3: begin
                        n_cmd3 = n_cmd3 + 1;
                        send_response({88'd0, 2'b00, 6'd3, RCA, 16'h0500,
                                       crc7_of({2'b00, 6'd3, RCA, 16'h0500}),
                                       1'b1}, 48);
                    end
                    6'd7: begin
                        n_cmd7   = n_cmd7 + 1;
                        selected = (cmd_arg[31:16] == RCA);
                        send_response({88'd0, r1(6'd7, 32'h0000_0700)}, 48);
                    end
                    6'd16: begin
                        n_cmd16 = n_cmd16 + 1;
                        send_response({88'd0, r1(6'd16, 32'h0000_0900)}, 48);
                    end
                    6'd17: begin
                        // An unselected card says nothing at all. That silence
                        // is the point: it is what makes CMD7 load-bearing.
                        if (selected) begin
                            n_read = n_read + 1;
                            send_response({88'd0, r1(6'd17, 32'h0000_0900)}, 48);
                            send_block(HIGH_CAP ? cmd_arg : (cmd_arg >> 9));
                        end
                    end
                    6'd24: begin
                        if (selected) begin
                            n_write = n_write + 1;
                            send_response({88'd0, r1(6'd24, 32'h0000_0900)}, 48);
                            recv_block(HIGH_CAP ? cmd_arg : (cmd_arg >> 9));
                        end
                    end
                    default: ;
                    endcase
                    if (cmd_idx != 6'd55) app_cmd = 1'b0;
                end
            end
        end
    end
endmodule

`default_nettype wire
