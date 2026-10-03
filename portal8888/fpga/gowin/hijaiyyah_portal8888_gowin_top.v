// hijaiyyah_portal8888_gowin_top.v -- Portal 8888 v1 on the Tang Nano 20K, over the UART.
//
// Ten pins, the same as rtl/fpga/gowin/hijaiyyah_hmac_gowin_top.v: clk_27m,
// btn_rst_n, uart_rxd, uart_txd, led[5:0]. Same constraint file
// (rtl/fpga/gowin/hcpu_gowin.cst), same edge-detected reset.
//
// The board has no Ethernet port, so a frame reaches the Portal's PHY byte
// stream from the host, one UART byte per PHY byte. What is real on the board
// is the capture, the SHA-256 of the frame, the HMAC seal, the per-corner
// chain and the head anchor; what is not is the wire the frame arrived on.
//
// Protocol, 8N1, one command and one reply; the host waits for the reply.
// Multi-byte fields are big-endian.
//
//     host -> board                             board -> host
//     'K' slot(1) key block(64)                 'S' status(1)
//     'L'                                       'S' status(1)
//     'T' utc_sec(4) uncert_ns(4)               'S' status(1)
//     'F' port(1) length(2) frame(length)       'R' body(125) tag(32)   sealed
//                                               'D' flags(1)            dropped
//     'A'                                       'A' round(4) root(32) tagA..tagD(4 x 32)
//     anything else, or 'F' with length 0       '?'
//
//     status = {locked, provisioned, 1'b0, written[4:0]}
//     flags  = bit 0: the frame overflowed the 9,216-byte buffer
//
// Limits, stated:
//   - The keys come from the host, so the host knows them: a laboratory
//     provisioning, not a root of trust. A slot is write-once and the lock
//     holds until reset or reconfiguration.
//   - There is no PPS pin. pps is tied low, so every record carries
//     T_source = 0 (free-running) on the UTC second the host provisioned.
//   - A UART byte that arrives while a reply is being sent is not read.
//
// LEDs, active low: led[0] waiting for a command, led[1] a frame is streaming
// or being sealed, led[2] sending a reply, led[3] provisioned and locked,
// led[5] a UART frame error was seen (sticky).

`default_nettype none

module hijaiyyah_portal8888_gowin_top #(
    parameter BAUD = 115200
) (
    input  wire        clk_27m,
    input  wire        btn_rst_n,
    input  wire        uart_rxd,
    output wire        uart_txd,
    output wire [5:0]  led
);

    localparam SYS_HZ = 27_000_000;

    // ── Reset: edge-detected, as in hijaiyyah_hmac_gowin_top.v ──
    reg [2:0] rst_sync = 3'b000;
    reg [1:0] btn_q    = 2'b00;
    wire      sys_rst_n = rst_sync[2];

    always @(posedge clk_27m) begin
        btn_q <= {btn_q[0], btn_rst_n};
        if (btn_q[1] & ~btn_q[0])
            rst_sync <= 3'b000;
        else
            rst_sync <= {rst_sync[1:0], 1'b1};
    end

    // ── UART ────────────────────────────────────────────────────
    wire [7:0] rx_data;
    wire       rx_valid, rx_frame_err;
    reg  [7:0] tx_data;
    reg        tx_start;
    wire       tx_busy;

    hcpu_uart_rx #(.CLK_HZ(SYS_HZ), .BAUD(BAUD)) u_rx (
        .clk(clk_27m), .rst_n(sys_rst_n), .rx_in(uart_rxd),
        .rx_data(rx_data), .rx_valid(rx_valid), .rx_frame_err(rx_frame_err));

    hcpu_uart_tx #(.CLK_HZ(SYS_HZ), .BAUD(BAUD)) u_tx (
        .clk(clk_27m), .rst_n(sys_rst_n), .tx_data(tx_data),
        .tx_start(tx_start), .tx_out(uart_txd), .tx_busy(tx_busy));

    // ── Command state ───────────────────────────────────────────
    localparam [3:0] S_CMD = 4'd0, S_KSLOT = 4'd1, S_KEY = 4'd2, S_TIME = 4'd3,
                     S_SETTLE = 4'd4, S_FPORT = 4'd5, S_FLEN = 4'd6,
                     S_FDATA = 4'd7, S_FWAIT = 4'd8, S_AWAIT = 4'd9,
                     S_SEND = 4'd10;
    localparam [1:0] SEL_SHORT = 2'd0, SEL_REC = 2'd1, SEL_ANC = 2'd2;

    reg [3:0]   st;
    reg [7:0]   n;
    reg [2:0]   slot;
    reg [63:0]  tbuf;
    reg [1:0]   fport;
    reg [15:0]  flen, fcnt;
    reg         prov_lock, prov_time;
    reg         seen_done, seen_drop, seen_over;
    reg [7:0]   rep_type, rep_short, rep_len;
    reg [1:0]   rep_sel;
    reg         rep_head;
    reg         frame_err;

    // ── The Portal ──────────────────────────────────────────────
    wire         provisioned, provision_locked, p_busy, p_ready;
    wire [4:0]   provision_written;
    wire         record_done, record_dropped, overflow_drop;
    wire [999:0] sealed_body;
    wire [255:0] sealed_tag, anc_root, tagA, tagB, tagC, tagD;
    wire [31:0]  anc_round;

    // One UART byte is one PHY byte, on the clock it is received.
    wire p_valid = (st == S_FDATA) && rx_valid;
    wire p_last  = (fcnt == flen - 16'd1);
    // One UART byte is one key byte too: the Portal counts the 64 of a slot.
    wire k_valid = (st == S_KEY) && rx_valid;

    hijaiyyah_portal8888 u_portal (
        .clk(clk_27m), .rst_n(sys_rst_n), .pps(1'b0),
        .provision_time(prov_time), .provision_utc_sec(tbuf[63:32]),
        .provision_uncert_ns(tbuf[31:0]),
        .phy_port(fport), .phy_byte_valid(p_valid), .phy_byte(rx_data), .phy_last(p_last),
        .prov_valid(k_valid), .prov_slot(slot), .prov_byte(rx_data), .prov_lock(prov_lock),
        .provisioned(provisioned), .provision_locked(provision_locked),
        .provision_written(provision_written), .busy(p_busy), .ready(p_ready),
        .record_done(record_done), .record_dropped(record_dropped),
        .overflow_drop(overflow_drop),
        .sealed_body(sealed_body), .sealed_tag(sealed_tag),
        .anc_round(anc_round), .anc_root(anc_root),
        .tagA(tagA), .tagB(tagB), .tagC(tagC), .tagD(tagD));

    wire [7:0] status = {provision_locked, provisioned, 1'b0, provision_written};

    // ── Reply: a type byte, then the payload, most significant byte first ──
    wire [1255:0] rec_out = {sealed_body, sealed_tag};
    wire [1311:0] anc_out = {anc_round, anc_root, tagA, tagB, tagC, tagD};
    wire [7:0] rep_byte = (rep_sel == SEL_REC) ? rec_out[1255 - n * 8 -: 8] :
                          (rep_sel == SEL_ANC) ? anc_out[1311 - n * 8 -: 8] : rep_short;

    always @(posedge clk_27m or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            st <= S_CMD; n <= 8'd0; slot <= 3'd0; tbuf <= 64'd0;
            fport <= 2'd0; flen <= 16'd0; fcnt <= 16'd0;
            prov_lock <= 1'b0; prov_time <= 1'b0;
            seen_done <= 1'b0; seen_drop <= 1'b0; seen_over <= 1'b0;
            rep_type <= 8'h00; rep_short <= 8'h00; rep_len <= 8'd0;
            rep_sel <= SEL_SHORT; rep_head <= 1'b0; frame_err <= 1'b0;
            tx_start <= 1'b0; tx_data <= 8'h00;
        end else begin
            prov_lock <= 1'b0; prov_time <= 1'b0;
            tx_start   <= 1'b0;
            if (rx_valid && rx_frame_err) frame_err <= 1'b1;
            if (record_done)    seen_done <= 1'b1;
            if (record_dropped) seen_drop <= 1'b1;
            if (overflow_drop)  seen_over <= 1'b1;

            case (st)
                S_CMD: if (rx_valid) begin
                    n <= 8'd0;
                    case (rx_data)
                        8'h4B: st <= S_KSLOT;                               // 'K'
                        8'h4C: begin prov_lock <= 1'b1; st <= S_SETTLE; end // 'L'
                        8'h54: st <= S_TIME;                                // 'T'
                        8'h46: st <= S_FPORT;                               // 'F'
                        8'h41: st <= S_AWAIT;                               // 'A'
                        default: begin
                            rep_type <= 8'h3F; rep_sel <= SEL_SHORT; rep_len <= 8'd0;
                            rep_head <= 1'b1; st <= S_SEND;
                        end
                    endcase
                end

                // A slot outside 0..4 is passed as 7, which the Portal ignores.
                S_KSLOT: if (rx_valid) begin
                    slot <= (rx_data < 8'd5) ? rx_data[2:0] : 3'd7;
                    n <= 8'd0; st <= S_KEY;
                end

                S_KEY: if (rx_valid) begin
                    n   <= n + 8'd1;
                    if (n == 8'd63) begin n <= 8'd0; st <= S_SETTLE; end
                end

                S_TIME: if (rx_valid) begin
                    tbuf <= {tbuf[55:0], rx_data};
                    n    <= n + 8'd1;
                    if (n == 8'd7) begin prov_time <= 1'b1; n <= 8'd0; st <= S_SETTLE; end
                end

                // The pulse reaches the Portal, the Portal's state moves, then
                // the status is read.
                S_SETTLE: begin
                    n <= n + 8'd1;
                    if (n == 8'd2) begin
                        rep_type <= 8'h53; rep_short <= status; rep_sel <= SEL_SHORT;
                        rep_len <= 8'd1; rep_head <= 1'b1; n <= 8'd0; st <= S_SEND;
                    end
                end

                S_FPORT: if (rx_valid) begin
                    fport <= rx_data[1:0]; n <= 8'd0; st <= S_FLEN;
                end

                S_FLEN: if (rx_valid) begin
                    flen <= {flen[7:0], rx_data};
                    n    <= n + 8'd1;
                    if (n == 8'd1) begin
                        n <= 8'd0;
                        if ({flen[7:0], rx_data} == 16'd0) begin
                            rep_type <= 8'h3F; rep_sel <= SEL_SHORT; rep_len <= 8'd0;
                            rep_head <= 1'b1; st <= S_SEND;
                        end else begin
                            fcnt <= 16'd0;
                            seen_done <= 1'b0; seen_drop <= 1'b0; seen_over <= 1'b0;
                            st <= S_FDATA;
                        end
                    end
                end

                S_FDATA: if (rx_valid) begin
                    fcnt <= fcnt + 16'd1;
                    if (p_last) st <= S_FWAIT;
                end

                S_FWAIT: if (seen_done) begin
                    rep_type <= 8'h52; rep_sel <= SEL_REC; rep_len <= 8'd157;
                    rep_head <= 1'b1; n <= 8'd0; st <= S_SEND;
                end else if (seen_drop) begin
                    rep_type <= 8'h44; rep_short <= {7'd0, seen_over}; rep_sel <= SEL_SHORT;
                    rep_len <= 8'd1; rep_head <= 1'b1; n <= 8'd0; st <= S_SEND;
                end

                // The anchor is read only when the Portal is idle, so a round
                // that is still being sealed is never read half-way.
                S_AWAIT: if (!p_busy) begin
                    rep_type <= 8'h41; rep_sel <= SEL_ANC; rep_len <= 8'd164;
                    rep_head <= 1'b1; n <= 8'd0; st <= S_SEND;
                end

                S_SEND: if (!tx_busy && !tx_start) begin
                    if (rep_head) begin
                        tx_data <= rep_type; tx_start <= 1'b1; rep_head <= 1'b0;
                    end else if (n == rep_len) begin
                        st <= S_CMD;
                    end else begin
                        tx_data <= rep_byte; tx_start <= 1'b1; n <= n + 8'd1;
                    end
                end

                default: st <= S_CMD;
            endcase
        end
    end

    assign led = ~{frame_err, 1'b0, provisioned, (st == S_SEND),
                   (st == S_FDATA || st == S_FWAIT), (st == S_CMD)};

endmodule

`default_nettype wire
