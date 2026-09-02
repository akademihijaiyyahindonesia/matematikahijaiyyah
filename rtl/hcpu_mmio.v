// hcpu_mmio.v — the peripherals given an address, so a program can reach them.
//
// A receiver and a timer that nothing can call are two modules, not two
// capabilities. This is what turns them into something `LOAD` and `STORE`
// can talk to.
//
// THE MAP. The data space is 4096 words; the top sixteen are peripherals and
// everything below is RAM. One comparator decides, which is why the top of
// the space and not a scattered set of addresses.
//
//   0xFF0  R   UART RX data      reading it clears `ready`
//   0xFF1  R   UART RX status    bit0 ready · bit1 framing error
//   0xFF2  R   UART TX status    bit0 busy
//   0xFF4  R   timer counter     free-running
//   0xFF5  RW  timer compare
//   0xFF6  R   timer status      bit0 expired      W: clears it
//
// TRANSMIT IS NOT HERE. The PRINT instruction already drives hcpu_uart_tx,
// and a second driver on the same port is a bus conflict rather than a
// feature. Only its status is readable, so a program can tell whether a
// PRINT is still going out.
//
// LATENCY MATCHES THE RAM, and this is the part that would break quietly if
// it did not. The RAM's read is registered — data arrives one cycle after the
// address — so peripheral reads are registered too, and the select is held
// alongside. Returning a peripheral value combinationally would make `LOAD`
// mean something different depending on which address it read, and every
// program that mixed the two would be subtly wrong.
//
// A write to a peripheral must not also land in RAM. `ram_we` is gated, not
// merely ignored: an address decoded as a peripheral is not a RAM address.

`default_nettype none

`include "hcpu_pkg.vh"

module hcpu_mmio #(
    parameter CLK_HZ = 27_000_000,
    parameter BAUD   = 115200
) (
    input  wire                    clk,
    input  wire                    rst_n,

    // ── CPU side, the bus the memory stage already drives ───────
    input  wire                    re,
    input  wire                    we,
    input  wire [`DATA_ADDR_W-1:0] addr,
    input  wire [`XLEN-1:0]        wdata,
    output wire [`XLEN-1:0]        rdata,

    // ── RAM side ────────────────────────────────────────────────
    output wire                    ram_re,
    output wire                    ram_we,
    output wire [`DATA_ADDR_W-1:0] ram_addr,
    output wire [`XLEN-1:0]        ram_wdata,
    input  wire [`XLEN-1:0]        ram_rdata,

    // ── the world ───────────────────────────────────────────────
    input  wire                    uart_rx_in,
    input  wire                    uart_tx_busy
);

    localparam [`DATA_ADDR_W-1:0] PERIPH_BASE = 12'hFF0;

    localparam [3:0] REG_RX_DATA   = 4'h0;
    localparam [3:0] REG_RX_STATUS = 4'h1;
    localparam [3:0] REG_TX_STATUS = 4'h2;
    localparam [3:0] REG_COUNTER   = 4'h4;
    localparam [3:0] REG_COMPARE   = 4'h5;
    localparam [3:0] REG_TIMER_ST  = 4'h6;

    wire       is_periph = (addr >= PERIPH_BASE);
    wire [3:0] reg_sel   = addr[3:0];

    assign ram_re    = re & ~is_periph;
    assign ram_we    = we & ~is_periph;
    assign ram_addr  = addr;
    assign ram_wdata = wdata;

    // ── receiver ────────────────────────────────────────────────
    wire [7:0] rx_byte;
    wire       rx_strobe, rx_err;

    hcpu_uart_rx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) u_rx (
        .clk(clk), .rst_n(rst_n), .rx_in(uart_rx_in),
        .rx_data(rx_byte), .rx_valid(rx_strobe), .rx_frame_err(rx_err));

    // One byte of holding, and an overrun flag rather than a silent drop. A
    // byte that arrives before the last was read has to be reported: losing
    // it quietly is the failure that looks like a protocol bug for a week.
    reg [7:0] rx_held;
    reg       rx_ready, rx_held_err, rx_overrun;

    wire rx_read = re & is_periph & (reg_sel == REG_RX_DATA);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_held     <= 8'h00;
            rx_ready    <= 1'b0;
            rx_held_err <= 1'b0;
            rx_overrun  <= 1'b0;
        end else begin
            if (rx_strobe) begin
                rx_held     <= rx_byte;
                rx_held_err <= rx_err;
                rx_ready    <= 1'b1;
                if (rx_ready) rx_overrun <= 1'b1;
            end else if (rx_read) begin
                rx_ready   <= 1'b0;
                rx_overrun <= 1'b0;
            end
        end
    end

    // ── timer ───────────────────────────────────────────────────
    wire [31:0] tmr_counter, tmr_compare;
    wire        tmr_expired;

    wire timer_write = we & is_periph;

    hcpu_timer u_timer (
        .clk(clk), .rst_n(rst_n),
        .compare_in(wdata),
        .compare_we(timer_write & (reg_sel == REG_COMPARE)),
        .clear     (timer_write & (reg_sel == REG_TIMER_ST)),
        .counter(tmr_counter), .compare(tmr_compare), .expired(tmr_expired));

    // ── read data, registered to match the RAM ──────────────────
    reg [`XLEN-1:0] periph_rdata;
    reg             periph_sel;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            periph_rdata <= {`XLEN{1'b0}};
            periph_sel   <= 1'b0;
        end else begin
            periph_sel <= re & is_periph;
            case (reg_sel)
                REG_RX_DATA:   periph_rdata <= {24'd0, rx_held};
                REG_RX_STATUS: periph_rdata <= {29'd0, rx_overrun,
                                                rx_held_err, rx_ready};
                REG_TX_STATUS: periph_rdata <= {31'd0, uart_tx_busy};
                REG_COUNTER:   periph_rdata <= tmr_counter;
                REG_COMPARE:   periph_rdata <= tmr_compare;
                REG_TIMER_ST:  periph_rdata <= {31'd0, tmr_expired};
                default:       periph_rdata <= {`XLEN{1'b0}};
            endcase
        end
    end

    assign rdata = periph_sel ? periph_rdata : ram_rdata;

endmodule

`default_nettype wire
