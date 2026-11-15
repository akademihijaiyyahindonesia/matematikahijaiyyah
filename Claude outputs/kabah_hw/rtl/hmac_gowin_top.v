// hmac_gowin_top.v — HMAC-SHA256 on the Tang Nano 20K, over the UART.
//
// Ten pins, the same as hijaiyyah_kabah_gowin_top.v: clk_27m, btn_rst_n,
// uart_rxd, uart_txd, led[5:0]. Same constraint file (hcpu_gowin.cst), same
// edge-detected reset (pin 87 = MODE1 is held low on this board).
//
// Protocol, one request per frame, 115200 8N1:
//
//     host -> board   64 bytes  key block (K, zero-padded; keys <= 64 bytes)
//                      2 bytes  message length L, big-endian
//                      L bytes  message
//     board -> host   32 bytes  HMAC-SHA256(K, message)
//                      4 bytes  clocks the HMAC engine spent busy, big-endian
//
// The clock count is the engine's own work (start to done, minus clocks spent
// waiting for the next UART byte), so it measures the logic, not the cable.
//
// LEDs, active low: led[0] waiting for key, led[1] message streaming,
// led[2] sending the result, led[5] a UART frame error was seen (sticky).

`default_nettype none

module hmac_gowin_top #(
    parameter BAUD = 115200
) (
    input  wire        clk_27m,
    input  wire        btn_rst_n,
    input  wire        uart_rxd,
    output wire        uart_txd,
    output wire [5:0]  led
);

    localparam SYS_HZ = 27_000_000;

    // ── Reset: edge-detected, as in hijaiyyah_kabah_gowin_top.v ──
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

    // One-deep receive buffer: a byte every ~2,344 clocks, a block costs 66.
    reg       rx_pend;
    reg [7:0] rx_byte;
    reg       frame_err;
    wire      rx_take;

    always @(posedge clk_27m or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            rx_pend <= 1'b0; rx_byte <= 8'h00; frame_err <= 1'b0;
        end else begin
            if (rx_valid) begin
                rx_byte <= rx_data;
                rx_pend <= 1'b1;
                if (rx_frame_err) frame_err <= 1'b1;
            end else if (rx_take) begin
                rx_pend <= 1'b0;
            end
        end
    end

    // ── HMAC engine ─────────────────────────────────────────────
    reg          h_start;
    reg  [511:0] key;
    wire         h_ready, h_idle, h_done;
    wire [255:0] mac;

    localparam [2:0] S_KEY = 3'd0, S_LEN = 3'd1, S_GO = 3'd2, S_MSG = 3'd3,
                     S_FIN = 3'd4, S_WAIT = 3'd5, S_SEND = 3'd6;
    reg [2:0]  st;
    reg [6:0]  n;           // bytes counted in S_KEY / S_LEN / S_SEND
    reg [15:0] len;
    reg [287:0] out;        // mac || cycles, shifted out MSB first
    reg [31:0] busy_clk;

    wire msg_byte = (st == S_MSG) && rx_pend && h_ready && (len != 16'd0);
    wire h_finish = (st == S_FIN) && h_ready;

    assign rx_take = (st == S_KEY || st == S_LEN) ? rx_pend : msg_byte;

    hmac_sha256 u_hmac (
        .clk(clk_27m), .rst_n(sys_rst_n), .start(h_start), .key(key),
        .byte_valid(msg_byte), .byte_in(rx_byte), .byte_ready(h_ready),
        .finish(h_finish), .idle(h_idle), .done(h_done), .mac(mac));

    // Engine work: busy and not stalled on the cable.
    wire stalled = (st == S_MSG) && h_ready && !rx_pend;

    always @(posedge clk_27m or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            st <= S_KEY; n <= 7'd0; len <= 16'd0; key <= 512'd0;
            h_start <= 1'b0; tx_start <= 1'b0; tx_data <= 8'h00;
            out <= 288'd0; busy_clk <= 32'd0;
        end else begin
            h_start  <= 1'b0;
            tx_start <= 1'b0;
            if ((st == S_MSG || st == S_FIN || st == S_WAIT) && !stalled)
                busy_clk <= busy_clk + 32'd1;

            case (st)
                S_KEY: if (rx_pend) begin
                    key <= {key[503:0], rx_byte};
                    n   <= n + 7'd1;
                    if (n == 7'd63) begin n <= 7'd0; st <= S_LEN; end
                end

                S_LEN: if (rx_pend) begin
                    len <= {len[7:0], rx_byte};
                    n   <= n + 7'd1;
                    if (n == 7'd1) begin n <= 7'd0; st <= S_GO; end
                end

                S_GO: if (h_idle) begin
                    h_start  <= 1'b1;
                    busy_clk <= 32'd0;
                    st       <= S_MSG;
                end

                S_MSG: begin
                    if (msg_byte) len <= len - 16'd1;
                    else if (len == 16'd0) st <= S_FIN;
                end

                S_FIN: if (h_ready) st <= S_WAIT;

                S_WAIT: if (h_done) begin
                    out <= {mac, busy_clk};
                    n   <= 7'd0;
                    st  <= S_SEND;
                end

                S_SEND: if (!tx_busy && !tx_start) begin
                    if (n == 7'd36) begin
                        st <= S_KEY; n <= 7'd0;
                    end else begin
                        tx_data  <= out[287:280];
                        tx_start <= 1'b1;
                        out      <= {out[279:0], 8'h00};
                        n        <= n + 7'd1;
                    end
                end

                default: st <= S_KEY;
            endcase
        end
    end

    assign led = ~{frame_err, 2'b00, (st == S_SEND),
                   (st == S_MSG || st == S_FIN || st == S_WAIT), (st == S_KEY)};

endmodule

`default_nettype wire
