// ============================================================================
// Atom addresses, sent over the wire — tb_gowin_loader_nui.v
// ============================================================================
//
// nui_embedding.hasm (L_JIM, L_KHA, CGET, ADD/SUB, PRINT) has only ever been
// proved one way: baked into the bitstream at synthesis, the same as
// test_bsm.hasm's default board image. tb_gowin_loader.v has only ever sent
// one program over the wire: payload.hasm's three MOVI/HALT words, small on
// purpose, there to prove the boot path itself rather than any real
// computation.
//
// Neither proves what this does: that a program built from LETTER opcodes --
// nui/atom.py's own addresses, L_JIM = 0xE4, L_KHA = 0xE6, the same integers
// that name a row in the Master Table and a ROM address in this same
// pipeline -- runs correctly when it arrives DYNAMICALLY, through the loader,
// rather than existing in the bitstream from the start. The boot path was
// proved letter-blind (three arithmetic words); the letter accumulation was
// proved bitstream-resident (nui_embedding.hasm's own bench). This is the
// first bench where both are true in the same run: an atom-addressed program,
// delivered over the wire.
//
// Board built with loader.hex, exactly tb_gowin_loader.v's own setup;
// nui_embedding.hasm's assembled words sent as the payload, exactly
// payload.hasm's own wire protocol; the resulting PRINT output decoded by an
// independently-timed UART receiver, exactly tb_hcpu_nui_embedding.v's own
// pattern. Three benches' own techniques, none of their own claims repeated.

`timescale 1ns/1ps
`include "hcpu_pkg.vh"

module tb_gowin_loader_nui;
    localparam real    HALF_PERIOD = 18.5;          // 27 MHz
    localparam integer BAUD        = 115200;
    localparam real    BIT_NS      = 1_000_000_000.0 / BAUD;

    reg  clk_27m = 1'b0;
    reg  btn_rst_n = 1'b0;
    reg  uart_rxd = 1'b1;                            // idle high
    wire uart_txd;
    wire [5:0] led;

    always #HALF_PERIOD clk_27m = ~clk_27m;

    hcpu_gowin_top #(
        .USE_PLL      (0),
        .BAUD         (BAUD),
        .PROGRAM_HEX  ("loader.hex")
    ) u_board (
        .clk_27m   (clk_27m),
        .btn_rst_n (btn_rst_n),
        .uart_rxd  (uart_rxd),
        .uart_txd  (uart_txd),
        .led       (led)
    );

    integer errors = 0;
    task check(input cond, input [255:0] what);
        begin
            if (!cond) begin $display("  GAGAL: %0s", what); errors = errors + 1; end
        end
    endtask

    // ── transmit one byte to the loader, LSB first ──────────────
    task send_byte(input [7:0] b);
        integer i;
        begin
            uart_rxd = 1'b0;  #BIT_NS;                // start
            for (i = 0; i < 8; i = i + 1) begin
                uart_rxd = b[i]; #BIT_NS;             // LSB first
            end
            uart_rxd = 1'b1;  #BIT_NS;                // stop
        end
    endtask

    reg [7:0] payload [0:255];
    integer   n_bytes, i;

    // ── Independent UART receiver for the loaded program's own PRINT
    // output — tb_hcpu_nui_embedding.v's own pattern, timed from BIT_NS,
    // not from the RTL, decoding uart_txd only after the loader has
    // handed control to the loaded program.
    reg [7:0] received [0:63];
    integer   count = 0;
    integer   bit_i;
    reg [7:0] shifted;

    initial begin
        forever begin
            @(negedge uart_txd);
            #(BIT_NS * 1.5);
            for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
                shifted[bit_i] = uart_txd;
                #BIT_NS;
            end
            if (count < 64) begin
                received[count] = shifted;
                count = count + 1;
            end
        end
    end

    initial begin
        $readmemh("nui_payload.txt", payload);
        n_bytes = 4 + 4 * 48;                          // 4 count + 48 words

        repeat (20) @(posedge clk_27m);
        btn_rst_n = 1'b1;
        repeat (200) @(posedge clk_27m);

        for (i = 0; i < n_bytes; i = i + 1)
            send_byte(payload[i]);

        // The loader spins on RX_STATUS and hands over via ERET once the
        // last word lands; the loaded program then runs its own CGET/ADD
        // chain and five PRINTs. Same margin tb_hcpu_nui_embedding.v uses
        // for the PRINTs themselves, plus room for the wire transfer that
        // bench never had to do (196 bytes at 115200 baud is itself
        // ~17,000 clocks at 27 MHz).
        repeat (80000) @(posedge clk_27m);

        // Ground truth: python3 -c "from hijaiyyah.core.master_table import
        // MASTER_TABLE as M; from hijaiyyah.nui.features import
        // vector_features as v; print(v([a+b for a,b in
        // zip(M.get_by_char('ج').vector, M.get_by_char('خ').vector)]))"
        // -- (2, 2, 2, 6, 6), the same case nui/atom.py's own test cross-
        // checks against this program's header.
        if (count < 10) begin
            $display("  GAGAL: kurang dari 10 byte muncul sebelum tenggat (got %0d)", count);
            errors = errors + 1;
        end else begin
            check(received[0] == "2", "byte 0 (titik)");
            check(received[1] == 8'h0A, "byte 1 (newline)");
            check(received[2] == "2", "byte 2 (garis)");
            check(received[3] == 8'h0A, "byte 3 (newline)");
            check(received[4] == "2", "byte 4 (lengkung)");
            check(received[5] == 8'h0A, "byte 5 (newline)");
            check(received[6] == "6", "byte 6 (theta)");
            check(received[7] == 8'h0A, "byte 7 (newline)");
            check(received[8] == "6", "byte 8 (rho)");
            check(received[9] == 8'h0A, "byte 9 (newline)");
        end

        // And it really did arrive through the wire, not sit in the
        // bitstream from the start: the same write-port proof
        // tb_gowin_loader.v runs for payload.hasm's three words, here for
        // all 48.
        check(u_board.u_hcpu.u_mmio.imem_waddr == 64 + 48,
              "alamat tulis harus maju tepat 48 kali");

        if (errors == 0)
            $display("PASS: tb_gowin_loader_nui — L_JIM/L_KHA dimuat lewat kabel, dijalankan, dan mencetak 2\\n2\\n2\\n6\\n6\\n lewat UART sungguhan");
        else begin
            $display("FAIL: tb_gowin_loader_nui — %0d gagal", errors);
            $fatal(1);
        end
        $finish;
    end
endmodule
