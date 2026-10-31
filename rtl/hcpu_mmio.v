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
    input  wire                    uart_tx_busy,

    // ── trap unit ───────────────────────────────────────────────
    // The trap unit lives in the top, because it needs the fetch PC and the
    // ERET from Execute -- neither of which belongs on a peripheral bus. Its
    // registers are decoded here anyway, so the peripheral window has exactly
    // one decoder. Two would be two truths.
    output wire                    trap_reg_we,
    output wire [3:0]              trap_reg_sel,
    output wire [`XLEN-1:0]        trap_reg_wdata,
    input  wire [`XLEN-1:0]        trap_reg_rdata,
    output wire                    src_timer,
    output wire                    src_uart_rx,

    // ── Memory protection window ────────────────────────────────
    // Base and limit for user mode. Supervisor-only because they live in the
    // peripheral window, which is the whole reason that rule was drawn there
    // first: a user program that could move its own boundary has none.
    output reg  [`DATA_ADDR_W-1:0] mem_base,
    output reg  [`DATA_ADDR_W-1:0] mem_limit,

    // ── Instruction memory write port ───────────────────────────
    // Harvard is kept for EXECUTION -- fetch still has its own read-only port.
    // What this adds is a privileged write path, which is what a loader needs
    // and what nothing else may have.
    output wire                    imem_we,
    output reg  [`CODE_ADDR_W-1:0] imem_waddr,
    output wire [`ILEN-1:0]        imem_wdata,

    // ── the card ────────────────────────────────────────────────
    // Out/oe/in rather than inout: the pad is the wrapper's business, and
    // keeping the tri-state out of here is what lets both this module and
    // hcpu_sdio.v be simulated without a bus resolver.
    output wire                    sd_clk,
    output wire                    sd_cmd_out,
    output wire                    sd_cmd_oe,
    input  wire                    sd_cmd_in,
    output wire                    sd_dat_out,
    output wire                    sd_dat_oe,
    input  wire                    sd_dat_in
);

    // The map is in hcpu_pkg.vh. It used to be localparams here, which was
    // fine while this was the only module that decoded the window -- and stops
    // being fine the moment the trap unit needs the same numbers.
    localparam [`DATA_ADDR_W-1:0] PERIPH_BASE = `PERIPH_BASE;
    localparam [3:0] REG_RX_DATA   = `REG_RX_DATA;
    localparam [3:0] REG_RX_STATUS = `REG_RX_STATUS;
    localparam [3:0] REG_TX_STATUS = `REG_TX_STATUS;
    localparam [3:0] REG_COUNTER   = `REG_COUNTER;
    localparam [3:0] REG_COMPARE   = `REG_COMPARE;
    localparam [3:0] REG_TIMER_ST  = `REG_TIMER_ST;

    // THE WINDOW WIDENED; THE SIXTEEN DID NOT MOVE (H-ISA v1.2). One
    // comparator still decides RAM versus peripheral -- that property is why
    // the window sits at the top of the space and it is kept. What is new is
    // that the window holds two blocks, and addr[4] says which.
    //
    // Every decode below that used to read `is_periph` now reads `is_core`,
    // and that substitution is the whole risk of this change: reg_sel is
    // addr[3:0], so a write to SD_CONTROL at 0xFE4 carries the same four bits
    // as a write to the timer's compare register at 0xFF4. Left on
    // `is_periph`, mounting a card would have quietly rearmed the timer.
    wire       is_periph = (addr >= `PERIPH_WINDOW);
    wire       is_core   = is_periph &  addr[4];
    wire       is_sd     = is_periph & ~addr[4];
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

    wire rx_read = re & is_core & (reg_sel == REG_RX_DATA);

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

    wire timer_write = we & is_core;

    hcpu_timer u_timer (
        .clk(clk), .rst_n(rst_n),
        .compare_in(wdata),
        .compare_we(timer_write & (reg_sel == REG_COMPARE)),
        .clear     (timer_write & (reg_sel == REG_TIMER_ST)),
        .counter(tmr_counter), .compare(tmr_compare), .expired(tmr_expired));

    // ── memory protection window ────────────────────────────────
    // Limit resets to the top of data space, so a machine that never sets it
    // behaves exactly as it did before protection existed.
    wire base_we  = we & is_core & (reg_sel == `REG_MEM_BASE);
    wire limit_we = we & is_core & (reg_sel == `REG_MEM_LIMIT);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mem_base  <= {`DATA_ADDR_W{1'b0}};
            mem_limit <= {`DATA_ADDR_W{1'b1}};
        end else begin
            if (base_we)  mem_base  <= wdata[`DATA_ADDR_W-1:0];
            if (limit_we) mem_limit <= wdata[`DATA_ADDR_W-1:0];
        end
    end

    // ── trap register access ────────────────────────────────────
    // Named one by one, not as a range. The range was `>= REG_TRAP_VECTOR &&
    // <= REG_TRAP_PENDING`, which silently excluded REG_TRAP_MODE when that
    // register was added at 0xD -- one past the top of the range. The trap
    // unit implemented the register, the decoder never routed it, and nothing
    // caught it: tb_hcpu_trap drives the trap unit directly and the Python
    // machine decodes the address itself, so both sides agreed with the spec
    // while the path between them was missing. A range over an enum admits
    // only what existed when it was written.
    wire is_trap_reg = (reg_sel == `REG_TRAP_VECTOR)
                    || (reg_sel == `REG_TRAP_EPC)
                    || (reg_sel == `REG_TRAP_CAUSE)
                    || (reg_sel == `REG_TRAP_ENABLE)
                    || (reg_sel == `REG_TRAP_PENDING)
                    || (reg_sel == `REG_TRAP_MODE);
    assign trap_reg_we    = we & is_core & is_trap_reg;
    assign trap_reg_sel   = reg_sel;
    assign trap_reg_wdata = wdata;

    // The two level-sensitive sources. `expired` is sticky until written and
    // `rx_ready` stays up until the byte is read, which is exactly what a
    // level-triggered trap input has to be: a pulse would be missed whenever
    // the trap unit happened to be blocked.
    assign src_timer   = tmr_expired;
    assign src_uart_rx = rx_ready;

    // ── instruction memory write port ───────────────────────────
    // The address advances on every data write. A loader that had to store the
    // address each time would spend two instructions per word, and the loader
    // itself has to be small enough to fit in front of what it loads.
    assign imem_wdata = wdata;
    wire imem_addr_we = we & is_core & (reg_sel == `REG_IMEM_ADDR);
    wire imem_data_we = we & is_core & (reg_sel == `REG_IMEM_DATA);

    // imem_we MUST be combinational. Registering it would assert the write one
    // cycle after imem_waddr had already advanced, so every word would land at
    // the address after its own -- the whole program shifted by one, which on
    // hardware looks like a program that almost works.
    assign imem_we = imem_data_we;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            imem_waddr <= {`CODE_ADDR_W{1'b0}};
        end else begin
            if (imem_addr_we)
                imem_waddr <= wdata[`CODE_ADDR_W-1:0];
            else if (imem_data_we)
                imem_waddr <= imem_waddr + 1'b1;
        end
    end

    // ── the card, 0xFE0 block ───────────────────────────────────
    // Five registers. SD_DATA is the only one that moves anything: it reads
    // and writes the controller's own 128-word buffer and advances the index
    // itself, the same bargain REG_IMEM_DATA makes four registers above.
    reg [31:0] sd_sector;
    reg [6:0]  sd_index;
    reg [1:0]  sd_div;
    reg        sd_start;
    reg [1:0]  sd_op;
    reg        sd_soft_rst;

    wire sd_cmd_we   = we & is_sd & (reg_sel == `SD_CMD);
    wire sd_sect_we  = we & is_sd & (reg_sel == `SD_SECTOR);
    wire sd_data_we  = we & is_sd & (reg_sel == `SD_DATA);
    wire sd_data_re  = re & is_sd & (reg_sel == `SD_DATA);
    wire sd_ctrl_we  = we & is_sd & (reg_sel == `SD_CONTROL);

    wire        sd_busy, sd_ok, sd_err, sd_card_ready;
    wire [3:0]  sd_err_code;
    wire [31:0] sd_buf_rdata;
    wire [31:0] sd_sector_csum;
    wire [31:0] sd_prescan_status;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sd_sector   <= 32'd0;
            sd_index    <= 7'd0;
            sd_div      <= 2'd0;
            sd_start    <= 1'b0;
            sd_op       <= 2'd0;
            sd_soft_rst <= 1'b0;
        end else begin
            // START IS A PULSE, NEVER A LEVEL. Held high it would restart the
            // command the instant the last one finished, which on a card looks
            // like a controller that never stops talking.
            sd_start    <= 1'b0;
            sd_soft_rst <= 1'b0;

            if (sd_cmd_we) begin
                sd_start <= 1'b1;
                sd_op    <= wdata[1:0];
            end
            if (sd_sect_we) sd_sector <= wdata;

            if (sd_ctrl_we) begin
                sd_div <= wdata[3:2];
                if (wdata[0]) sd_index    <= 7'd0;
                if (wdata[1]) sd_soft_rst <= 1'b1;
            end else if (sd_data_we | sd_data_re) begin
                sd_index <= sd_index + 1'b1;
            end
        end
    end

    hcpu_sdio #(.CLK_HZ(CLK_HZ)) u_sdio (
        .clk(clk),
        // A controller reset also forgets that the card was initialised, so a
        // driver that resets must init again. That is the point of the bit.
        .rst_n(rst_n & ~sd_soft_rst),
        .start(sd_start), .op(sd_op), .sector(sd_sector),
        .busy(sd_busy), .ok(sd_ok), .err(sd_err), .err_code(sd_err_code),
        .card_ready(sd_card_ready),
        .div_sel(sd_div),
        .buf_we(sd_data_we), .buf_re(sd_data_re), .buf_addr(sd_index),
        .buf_wdata(wdata), .buf_rdata(sd_buf_rdata),
        .sector_csum(sd_sector_csum),
        .prescan_status(sd_prescan_status),
        .sd_clk(sd_clk),
        .cmd_out(sd_cmd_out), .cmd_oe(sd_cmd_oe), .cmd_in(sd_cmd_in),
        .dat_out(sd_dat_out), .dat_oe(sd_dat_oe), .dat_in(sd_dat_in)
    );

    // ── read data, registered to match the RAM ──────────────────
    reg [`XLEN-1:0] periph_rdata;
    reg             periph_sel;

    // SD_DATA DOES NOT GO THROUGH periph_rdata, and that is a timing fact
    // rather than a preference. The controller's buffer has a REGISTERED read,
    // like the RAM: present an index and the word arrives a cycle later.
    // Registering it a second time here would deliver every buffer word one
    // cycle after the LOAD that asked for it -- the whole sector shifted by
    // one, which is the same shape of defect the imem write port's comment
    // above describes, and just as invisible in a wave view unless you count.
    reg sd_data_sel;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            periph_rdata <= {`XLEN{1'b0}};
            periph_sel   <= 1'b0;
            sd_data_sel  <= 1'b0;
        end else begin
            periph_sel  <= re & is_periph;
            sd_data_sel <= sd_data_re;
            if (is_sd) begin
                case (reg_sel)
                    // bit3 says a card ANSWERED, not that a card is present:
                    // this pinout carries no card-detect line, so there is
                    // nothing to sense. Reported as it is rather than named
                    // after something the board cannot tell us.
                    `SD_STATUS:  periph_rdata <= {24'd0, sd_err_code,
                                                 sd_card_ready,
                                                 sd_err, sd_ok, sd_busy};
                    `SD_SECTOR:  periph_rdata <= sd_sector;
                    `SD_CONTROL: periph_rdata <= {28'd0, sd_div, 2'b00};
                    `SD_CSUM:    periph_rdata <= sd_sector_csum;
                    `SD_PRESCAN: periph_rdata <= sd_prescan_status;
                    default:     periph_rdata <= {`XLEN{1'b0}};
                endcase
            end else
            case (reg_sel)
                REG_RX_DATA:   periph_rdata <= {24'd0, rx_held};
                REG_RX_STATUS: periph_rdata <= {29'd0, rx_overrun,
                                                rx_held_err, rx_ready};
                REG_TX_STATUS: periph_rdata <= {31'd0, uart_tx_busy};
                REG_COUNTER:   periph_rdata <= tmr_counter;
                REG_COMPARE:   periph_rdata <= tmr_compare;
                REG_TIMER_ST:  periph_rdata <= {31'd0, tmr_expired};
                `REG_TRAP_VECTOR,
                `REG_TRAP_EPC,
                `REG_TRAP_CAUSE,
                `REG_TRAP_ENABLE,
                `REG_TRAP_PENDING,
                `REG_TRAP_MODE:    periph_rdata <= trap_reg_rdata;
                `REG_IMEM_ADDR:    periph_rdata <= {{(`XLEN-`CODE_ADDR_W){1'b0}},
                                                   imem_waddr};
                `REG_MEM_BASE:     periph_rdata <= {{(`XLEN-`DATA_ADDR_W){1'b0}},
                                                   mem_base};
                `REG_MEM_LIMIT:    periph_rdata <= {{(`XLEN-`DATA_ADDR_W){1'b0}},
                                                   mem_limit};
                default:       periph_rdata <= {`XLEN{1'b0}};
            endcase
        end
    end

    assign rdata = periph_sel ? (sd_data_sel ? sd_buf_rdata : periph_rdata)
                              : ram_rdata;

endmodule

`default_nettype wire
