// hcpu_sdio.v — the TF card, in native SD 1-bit mode.
//
// Every byte this machine has ever stored died at power-off. HFS has four
// named operations and no medium that outlives the supply: data RAM is BSRAM,
// and the SDRAM the package carries is volatile too, so neither can answer
// "is it still there tomorrow". The card slot on the board can, and this is
// the module that reaches it.
//
// ── the mode is native SDIO, not SPI ────────────────────────────
// Owner's decision, 13 September 2026: SDIO 1-bit first, 4-bit once the path
// is stable. Native mode costs an identification sequence that SPI mode does
// not have -- CMD2/CMD3/CMD7 below -- and buys the 4-bit widening later
// without changing the card's state machine or this module's shape.
//
// DAT1..DAT3 are not touched here and are deliberately not tri-stated by this
// module. The wrapper parks them; widening to 4-bit is a change to the data
// phases only, which is the point of choosing this mode first.
//
// ── the sequence, and why it is longer than five commands ───────
// The bench proves CMD0, CMD8, ACMD41, CMD17 and CMD24. The card needs four
// more to get there, and they are not optional:
//
//   74+ clocks   the card's own power-up requirement, CMD held high
//   CMD0         GO_IDLE_STATE          -- no response at all
//   CMD8         SEND_IF_COND, 0x1AA    -- R7; a v1 card stays silent
//   ACMD41       CMD55 then CMD41       -- R3; repeated until OCR bit31 = 1
//   CMD2         ALL_SEND_CID           -- R2, 136 bits
//   CMD3         SEND_RELATIVE_ADDR     -- R6, and the card names itself
//   CMD7         SELECT_CARD, RCA<<16   -- without it CMD17 is ignored
//   CMD16        SET_BLOCKLEN, 512      -- harmless on SDHC, required on SDSC
//
// In SPI mode a card answers CMD17 straight after initialisation. In native
// mode an unselected card answers nothing, and the symptom is a read that
// times out rather than one that fails -- which is why they are here and not
// left for the board to teach us.
//
// ── OCR bit 30 decides what the sector argument means ───────────
// CMD17/CMD24 take a BYTE address on a standard-capacity card and a BLOCK
// number on a high-capacity one. `ccs` remembers which, and the argument is
// shifted by 9 only when it must be. Getting this backwards reads sector 0 of
// a 2 GB card for every request and looks like a card that works.
//
// ── clocking ────────────────────────────────────────────────────
// Initialisation runs at or below 400 kHz because the card requires it, then
// the divider drops to the transfer rate. Outputs change on the falling edge
// of sd_clk and inputs are sampled on the rising edge, which is the card's
// timing, not a preference.
//
// ── tri-state stays at the wrapper ──────────────────────────────
// CMD and DAT0 are open bidirectional lines on the card. This module exposes
// out/oe/in separately so it can be simulated without a bus resolver, and the
// wrapper -- the only place that knows it is talking to a pad -- makes the
// inout. rtl/tb/tb_hcpu_sdio.v drives the other side with a card model.

`default_nettype none

module hcpu_sdio #(
    parameter CLK_HZ    = 27_000_000,
    parameter INIT_HZ   =    400_000,   // the card's own ceiling before ACMD41
    parameter XFER_HZ   =  6_750_000,   // after initialisation
    // How long to wait for a response or a data start bit before calling it a
    // failure. A card may legitimately take milliseconds; a missing card takes
    // for ever, and for ever is not an answer a kernel can use.
    parameter TIMEOUT   =  2_700_000,   // 100 ms at 27 MHz
    // Ncc: idle SD clocks the card is owed between one command and the next.
    // The standard's minimum is 8. A parameter rather than a literal so the
    // bench can set it to 7 and watch the card model refuse the command --
    // a gate is only a gate if breaking it turns something red.
    parameter NCC_CLOCKS = 8
) (
    input  wire        clk,
    input  wire        rst_n,

    // ── command port ────────────────────────────────────────────
    input  wire        start,          // one pulse
    input  wire [1:0]  op,             // 1 = init, 2 = read block, 3 = write
    input  wire [31:0] sector,         // block number (LBA)
    output reg         busy,
    output reg         ok,             // last command finished cleanly
    output reg         err,            // last command failed
    output reg  [3:0]  err_code,       // which step failed
    output reg         card_ready,     // a card answered init
    // SD_CONTROL bits 3:2. Halves the transfer clock each step, so a card that
    // will not run at the default has somewhere to go without a rebuild. It is
    // read at the end of initialisation, not mid-transfer.
    input  wire [1:0]  div_sel,

    // ── sector buffer, 128 words = 512 bytes ────────────────────
    // Word 0 holds the first four bytes of the block, most significant byte
    // first: buf[31:24] is byte 0. The card is byte-serial and MSB-first, so
    // any other packing would have to reverse something twice.
    input  wire        buf_we,
    input  wire        buf_re,
    input  wire [6:0]  buf_addr,
    input  wire [31:0] buf_wdata,
    output reg  [31:0] buf_rdata,

    // ── the card ────────────────────────────────────────────────
    output reg         sd_clk,
    output reg         cmd_out,
    output reg         cmd_oe,
    input  wire        cmd_in,
    output reg         dat_out,
    output reg         dat_oe,
    input  wire        dat_in
);

    // ── error codes, so a failure says which step ───────────────
    localparam [3:0] E_NONE     = 4'd0,
                     E_CMD8     = 4'd1,   // no R7: not an SD v2 card
                     E_ACMD41   = 4'd2,   // never left idle
                     E_CID      = 4'd3,
                     E_RCA      = 4'd4,
                     E_SELECT   = 4'd5,
                     E_BLOCKLEN = 4'd6,
                     E_READ_CMD = 4'd7,   // CMD17 refused
                     E_READ_DAT = 4'd8,   // no data start bit
                     E_READ_CRC = 4'd9,   // block arrived corrupt
                     E_WRITE_CMD= 4'd10,
                     E_WRITE_ACK= 4'd11,  // CRC status was not 010
                     E_NOT_INIT = 4'd12;  // read/write before a good init

    localparam integer INIT_DIV = (CLK_HZ / INIT_HZ) / 2;
    localparam integer XFER_DIV = (CLK_HZ / XFER_HZ) / 2;
    localparam integer DIV_W    = $clog2((INIT_DIV + 1) * 8) + 1;
    localparam integer TO_W     = $clog2(TIMEOUT + 1);

    // ── clock generator ─────────────────────────────────────────
    // `tick_fall` is where this module drives; `tick_rise` is where it
    // samples. Both are single-cycle pulses in the system clock domain, so
    // nothing here runs on a divided clock -- the card's clock is data, not a
    // clock domain.
    reg  [DIV_W-1:0] divider;
    reg  [DIV_W-1:0] div_cnt;
    wire             tick = (div_cnt == 0);
    reg              clk_en;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            div_cnt <= 0;
            sd_clk  <= 1'b0;
        end else if (!clk_en) begin
            div_cnt <= divider;
            sd_clk  <= 1'b0;
        end else if (div_cnt == 0) begin
            div_cnt <= divider;
            sd_clk  <= ~sd_clk;
        end else begin
            div_cnt <= div_cnt - 1'b1;
        end
    end

    wire tick_rise = clk_en && tick && ~sd_clk;   // sd_clk is about to go high
    wire tick_fall = clk_en && tick &&  sd_clk;   // ... and about to go low

    // ── CRC7 for commands, CRC16 for data ───────────────────────
    // x^7 + x^3 + 1 and x^16 + x^12 + x^5 + 1. Both are computed one bit at a
    // time as the bit moves, so neither needs the message buffered twice.
    function [6:0] crc7_step;
        input [6:0] c;
        input       b;
        begin
            crc7_step = {c[5:0], 1'b0} ^ ((c[6] ^ b) ? 7'h09 : 7'h00);
        end
    endfunction

    function [15:0] crc16_step;
        input [15:0] c;
        input        b;
        begin
            crc16_step = {c[14:0], 1'b0} ^ ((c[15] ^ b) ? 16'h1021 : 16'h0000);
        end
    endfunction

    // ── the sector buffer: 128 words, block RAM ─────────────────
    // 512 bytes, exactly one sector, and it stays in BSRAM. The board tried to
    // talk both of us out of that and neither answer was better:
    //
    //   as BSRAM with a combinational write path  -- 8 hold violations, all on
    //       one net: a LUT computing sbuf_we feeding the block's ADB1 pin
    //   as distributed LUT RAM                    -- the hold rule disappears
    //       and a 128:1 read mux appears, +656 LUT4, 16,213 total, and
    //       nextpnr cannot place it. The same wall CDOT hit at 16,015.
    //
    // So the size was never the problem and moving the array was never the
    // fix. THE WRITE CONTROL IS REGISTERED instead: what reaches the block is
    // a flip-flop output, not a combinational function that can glitch on its
    // way there. Owner's decision, 14 September 2026.
    //
    // The cost is one cycle of write latency INSIDE this module, and it is
    // invisible from the MMIO side: nothing ever reads a buffer word in the
    // cycle after writing it. The card fills the buffer and the CPU drains it,
    // or the CPU fills it and the card drains it -- never both at once, which
    // is what `busy` is for.
    reg [31:0] sbuf [0:127];

    // The write port, one cycle behind the request and driven by nothing else.
    reg [6:0]  wr_addr;
    reg [31:0] wr_data;
    reg        wr_en;

    // The read port keeps its combinational select: the violation was on the
    // write side only, and registering this one would put the buffer a cycle
    // behind every LOAD of SD_DATA -- the whole sector shifted by one word.
    reg [6:0]  rd_addr;

    // What the state machine wants from the buffer while a transfer runs.
    reg [6:0]  fsm_addr;
    reg [31:0] fsm_wdata;
    reg        fsm_we;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_en   <= 1'b0;
            wr_addr <= 7'd0;
            wr_data <= 32'd0;
        end else begin
            wr_en   <= busy ? fsm_we    : buf_we;
            wr_addr <= busy ? fsm_addr  : buf_addr;
            wr_data <= busy ? fsm_wdata : buf_wdata;
        end
    end

    always @(posedge clk) begin
        if (wr_en) sbuf[wr_addr] <= wr_data;
        buf_rdata <= sbuf[rd_addr];
    end

    // ── state ───────────────────────────────────────────────────
    localparam [4:0] S_IDLE      = 5'd0,
                     S_POWERUP   = 5'd1,
                     S_CMD_SETUP = 5'd2,
                     S_CMD_SEND  = 5'd3,
                     S_RESP_WAIT = 5'd4,
                     S_RESP_RECV = 5'd5,
                     S_RESP_DONE = 5'd6,
                     S_DAT_WAIT  = 5'd7,
                     S_DAT_RECV  = 5'd8,
                     S_DAT_CRC   = 5'd9,
                     S_WR_GAP    = 5'd10,
                     S_WR_START  = 5'd11,
                     S_WR_DATA   = 5'd12,
                     S_WR_CRC    = 5'd13,
                     S_WR_END    = 5'd14,
                     S_WR_ACK    = 5'd15,
                     S_WR_BUSY   = 5'd16,
                     S_FINISH    = 5'd17,
                     S_FAIL      = 5'd18,
                     S_CMD_GAP   = 5'd19;

    reg [4:0]   state;
    reg [4:0]   step;             // where in the init script
    reg [1:0]   op_r;
    reg [31:0]  sector_r;
    reg [15:0]  rca;
    reg         ccs;              // OCR bit30: block addressing

    reg [47:0]  cmd_sh;
    reg [135:0] resp_sh;
    reg [7:0]   bit_cnt;
    reg [7:0]   gap_cnt;          // idle SD clocks counted before a command
    reg [12:0]  dat_cnt;
    reg [6:0]   crc7;
    reg [15:0]  crc16;
    reg [15:0]  crc16_rx;
    reg [31:0]  word_sh;
    reg [TO_W-1:0] timeout;
    reg [7:0]   resp_len;         // 48 or 136
    reg [5:0]   cmd_index;
    reg [2:0]   ack_sh;
    reg [19:0]  acmd41_tries;

    // ── the CPU-side buffer port ────────────────────────────────
    // Only reachable while the controller is idle; a read or write during a
    // transfer would fight the FSM for the same array. `busy` is what a driver
    // polls, and this is the reason it must.
    always @(*) rd_addr = busy ? fsm_addr : buf_addr;

    // ── command assembly ────────────────────────────────────────
    // start bit 0, direction 1, six index bits, 32 argument bits, CRC7, end 1.
    // The CRC is computed over the first 40 bits as they leave, so it is never
    // a second pass over the same value.
    task load_cmd;
        input [5:0]  idx;
        input [31:0] arg;
        begin
            cmd_sh    <= {2'b01, idx, arg, 8'h01};
            cmd_index <= idx;
            crc7      <= 7'd0;
            bit_cnt   <= 8'd0;
        end
    endtask

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state        <= S_IDLE;
            step         <= 5'd0;
            busy         <= 1'b0;
            ok           <= 1'b0;
            err          <= 1'b0;
            err_code     <= E_NONE;
            clk_en       <= 1'b0;
            divider      <= INIT_DIV[DIV_W-1:0];
            cmd_out      <= 1'b1;
            cmd_oe       <= 1'b1;
            dat_out      <= 1'b1;
            dat_oe       <= 1'b0;
            rca          <= 16'd0;
            ccs          <= 1'b0;
            card_ready   <= 1'b0;
            fsm_we       <= 1'b0;
            acmd41_tries <= 20'd0;
            gap_cnt      <= 8'd0;
        end else begin
            fsm_we <= 1'b0;

            case (state)

            // ── waiting for work ────────────────────────────────
            S_IDLE: begin
                clk_en  <= 1'b0;
                cmd_oe  <= 1'b1;
                cmd_out <= 1'b1;
                dat_oe  <= 1'b0;
                if (start) begin
                    op_r     <= op;
                    sector_r <= sector;
                    busy     <= 1'b1;
                    ok       <= 1'b0;
                    err      <= 1'b0;
                    err_code <= E_NONE;
                    timeout  <= TIMEOUT[TO_W-1:0];
                    if (op == 2'd1) begin
                        divider      <= INIT_DIV[DIV_W-1:0];
                        card_ready   <= 1'b0;
                        acmd41_tries <= 20'd0;
                        bit_cnt      <= 8'd0;
                        clk_en       <= 1'b1;
                        state        <= S_POWERUP;
                    end else if (!card_ready) begin
                        // A read before a good init is a defect in the driver,
                        // and saying so is cheaper than a timeout that looks
                        // like a broken card.
                        err_code <= E_NOT_INIT;
                        state    <= S_FAIL;
                    end else begin
                        clk_en <= 1'b1;
                        step   <= (op == 2'd2) ? 5'd10 : 5'd12;
                        state  <= S_CMD_SETUP;
                    end
                end
            end

            // ── 74+ clocks with CMD high, the card's requirement ─
            S_POWERUP: begin
                cmd_oe  <= 1'b1;
                cmd_out <= 1'b1;
                if (tick_fall) begin
                    if (bit_cnt >= 8'd80) begin
                        step  <= 5'd0;
                        state <= S_CMD_SETUP;
                    end else begin
                        bit_cnt <= bit_cnt + 1'b1;
                    end
                end
            end

            // ── pick the command this step sends ────────────────
            // The line is RELEASED here rather than taken, because what
            // follows is the gap, not the frame. It is taken again at the end
            // of S_CMD_GAP, one period before the start bit goes out.
            S_CMD_SETUP: begin
                timeout <= TIMEOUT[TO_W-1:0];
                cmd_oe  <= 1'b0;
                gap_cnt <= 8'd0;
                case (step)
                5'd0:  begin load_cmd(6'd0,  32'h0000_0000); resp_len <= 8'd0;   end
                5'd1:  begin load_cmd(6'd8,  32'h0000_01AA); resp_len <= 8'd48;  end
                5'd2:  begin load_cmd(6'd55, 32'h0000_0000); resp_len <= 8'd48;  end
                5'd3:  begin load_cmd(6'd41, 32'h4010_0000); resp_len <= 8'd48;  end
                5'd4:  begin load_cmd(6'd2,  32'h0000_0000); resp_len <= 8'd136; end
                5'd5:  begin load_cmd(6'd3,  32'h0000_0000); resp_len <= 8'd48;  end
                5'd6:  begin load_cmd(6'd7,  {rca, 16'h0000}); resp_len <= 8'd48; end
                5'd7:  begin load_cmd(6'd16, 32'd512);       resp_len <= 8'd48;  end
                5'd10: begin
                    load_cmd(6'd17, ccs ? sector_r : (sector_r << 9));
                    resp_len <= 8'd48;
                end
                5'd12: begin
                    load_cmd(6'd24, ccs ? sector_r : (sector_r << 9));
                    resp_len <= 8'd48;
                end
                default: begin load_cmd(6'd0, 32'd0); resp_len <= 8'd0; end
                endcase
                state <= S_CMD_GAP;
            end

            // ── 48 bits out, MSB first, CRC7 filled as it goes ──
            S_CMD_SEND: begin
                if (tick_fall) begin
                    cmd_out <= cmd_sh[47];
                    if (bit_cnt < 8'd40)
                        crc7 <= crc7_step(crc7, cmd_sh[47]);
                    if (bit_cnt == 8'd39)
                        cmd_sh <= {crc7_step(crc7, cmd_sh[47]), 1'b1, 40'd0};
                    else
                        cmd_sh <= {cmd_sh[46:0], 1'b1};
                    if (bit_cnt == 8'd47) begin
                        bit_cnt <= 8'd0;
                        if (resp_len == 8'd0) begin
                            // CMD0 is answered by nothing, so the host releases
                            // the line and goes straight on. The clocks the
                            // next command is owed are counted in S_CMD_GAP,
                            // which every command now passes through.
                            cmd_oe <= 1'b0;
                            state  <= S_RESP_DONE;
                        end else begin
                            cmd_oe <= 1'b0;
                            state  <= S_RESP_WAIT;
                        end
                    end else begin
                        bit_cnt <= bit_cnt + 1'b1;
                    end
                end
            end

            // ── the clocks every command is owed before it ──────
            // EVERY command passes through here, and the measurement is why.
            // The standard asks for eight idle clocks before a command: after
            // another command (Ncc) and after a response (Nrc). This module
            // provided NEITHER -- and the first measurement of it said only
            // CMD0 was affected, because it counted from one frame's start to
            // the next and so counted the card's own 48-bit response as though
            // it were idle time. Counted properly, as clocks where nobody
            // drives the line, the gap was ZERO at every boundary: the card
            // model refused CMD55 at gap 0 the moment it was taught to care.
            //
            // CMD is RELEASED, not driven high: the board carries a 10 kΩ
            // pull-up on that line (Tang Nano 20K 3921 schematic), so idle is
            // the card's own idea of idle rather than one the host asserts.
            // tick_fall counts whole SD clock periods -- the unit the standard
            // states these in, not system clocks, which at 27 MHz would be
            // sixty-eight times too short.
            S_CMD_GAP: begin
                cmd_oe <= 1'b0;
                if (tick_fall) begin
                    if (gap_cnt >= NCC_CLOCKS - 1) begin
                        // Take the line one period early, so the start bit
                        // leaves on a driven line rather than on a pull-up.
                        cmd_oe <= 1'b1;
                        state  <= S_CMD_SEND;
                    end else begin
                        gap_cnt <= gap_cnt + 1'b1;
                    end
                end
            end

            // ── the response's start bit ────────────────────────
            S_RESP_WAIT: begin
                cmd_oe <= 1'b0;
                if (tick_rise) begin
                    if (cmd_in == 1'b0) begin
                        resp_sh <= {135'd0, 1'b0};
                        bit_cnt <= 8'd1;
                        crc7    <= crc7_step(7'd0, 1'b0);
                        state   <= S_RESP_RECV;
                    end
                end
                if (timeout == 0) begin
                    case (step)
                    5'd1:  err_code <= E_CMD8;
                    5'd3:  err_code <= E_ACMD41;
                    5'd4:  err_code <= E_CID;
                    5'd5:  err_code <= E_RCA;
                    5'd6:  err_code <= E_SELECT;
                    5'd7:  err_code <= E_BLOCKLEN;
                    5'd10: err_code <= E_READ_CMD;
                    5'd12: err_code <= E_WRITE_CMD;
                    default: err_code <= E_ACMD41;
                    endcase
                    state <= S_FAIL;
                end else begin
                    timeout <= timeout - 1'b1;
                end
            end

            S_RESP_RECV: begin
                if (tick_rise) begin
                    resp_sh <= {resp_sh[134:0], cmd_in};
                    if (bit_cnt == resp_len - 1) begin
                        bit_cnt <= 8'd0;
                        state   <= S_RESP_DONE;
                    end else begin
                        bit_cnt <= bit_cnt + 1'b1;
                    end
                end
            end

            // ── what the answer meant ───────────────────────────
            S_RESP_DONE: begin
                cmd_oe  <= 1'b1;
                cmd_out <= 1'b1;
                case (step)
                5'd0: begin step <= 5'd1; state <= S_CMD_SETUP; end
                5'd1: begin
                    // R7 echoes the check pattern -- and it echoes it in the
                    // ARGUMENT, resp_sh[39:8], whose low byte is [15:8]. Read
                    // at [7:0] this compares the CRC7 and the end bit against
                    // 0xAA instead, which no correct card would ever satisfy:
                    // every card would look like a v1 card.
                    if (resp_sh[15:8] == 8'hAA) begin
                        step  <= 5'd2;
                        state <= S_CMD_SETUP;
                    end else begin
                        err_code <= E_CMD8;
                        state    <= S_FAIL;
                    end
                end
                5'd2: begin step <= 5'd3; state <= S_CMD_SETUP; end
                5'd3: begin
                    // R3 is the OCR: bit31 says initialisation finished, bit30
                    // says the card counts in blocks rather than bytes.
                    if (resp_sh[39]) begin
                        ccs   <= resp_sh[38];
                        step  <= 5'd4;
                        state <= S_CMD_SETUP;
                    end else if (acmd41_tries == 20'hFFFFF) begin
                        err_code <= E_ACMD41;
                        state    <= S_FAIL;
                    end else begin
                        acmd41_tries <= acmd41_tries + 1'b1;
                        step         <= 5'd2;   // CMD55 again, then CMD41
                        state        <= S_CMD_SETUP;
                    end
                end
                5'd4: begin step <= 5'd5; state <= S_CMD_SETUP; end
                5'd5: begin
                    rca   <= resp_sh[39:24];
                    step  <= 5'd6;
                    state <= S_CMD_SETUP;
                end
                5'd6: begin step <= 5'd7; state <= S_CMD_SETUP; end
                5'd7: begin
                    // Initialisation is over; the card may be clocked fast now.
                    divider    <= XFER_DIV[DIV_W-1:0] << div_sel;
                    card_ready <= 1'b1;
                    state      <= S_FINISH;
                end
                5'd10: begin
                    dat_cnt <= 13'd0;
                    crc16   <= 16'd0;
                    timeout <= TIMEOUT[TO_W-1:0];
                    state   <= S_DAT_WAIT;
                end
                5'd12: begin
                    bit_cnt <= 8'd0;
                    state   <= S_WR_GAP;
                end
                default: state <= S_FINISH;
                endcase
            end

            // ── reading a block ─────────────────────────────────
            S_DAT_WAIT: begin
                dat_oe <= 1'b0;
                if (tick_rise && dat_in == 1'b0) begin
                    dat_cnt <= 13'd0;
                    crc16   <= 16'd0;
                    state   <= S_DAT_RECV;
                end
                if (timeout == 0) begin
                    err_code <= E_READ_DAT;
                    state    <= S_FAIL;
                end else begin
                    timeout <= timeout - 1'b1;
                end
            end

            S_DAT_RECV: begin
                if (tick_rise) begin
                    word_sh <= {word_sh[30:0], dat_in};
                    crc16   <= crc16_step(crc16, dat_in);
                    if (dat_cnt[4:0] == 5'd31) begin
                        fsm_addr  <= dat_cnt[11:5];
                        fsm_wdata <= {word_sh[30:0], dat_in};
                        fsm_we    <= 1'b1;
                    end
                    if (dat_cnt == 13'd4095) begin
                        dat_cnt <= 13'd0;
                        state   <= S_DAT_CRC;
                    end else begin
                        dat_cnt <= dat_cnt + 1'b1;
                    end
                end
            end

            S_DAT_CRC: begin
                if (tick_rise) begin
                    crc16_rx <= {crc16_rx[14:0], dat_in};
                    if (dat_cnt == 13'd15) begin
                        // The card's CRC is the only thing standing between a
                        // corrupted block and a filesystem that trusts it.
                        if ({crc16_rx[14:0], dat_in} == crc16) begin
                            state <= S_FINISH;
                        end else begin
                            err_code <= E_READ_CRC;
                            state    <= S_FAIL;
                        end
                    end else begin
                        dat_cnt <= dat_cnt + 1'b1;
                    end
                end
            end

            // ── writing a block ─────────────────────────────────
            // Nwr: at least eight clocks between the response and the start
            // bit. Cards differ on how strictly they hold this; the standard
            // does not.
            S_WR_GAP: begin
                dat_oe  <= 1'b1;
                dat_out <= 1'b1;
                if (tick_fall) begin
                    if (bit_cnt >= 8'd8) begin
                        fsm_addr <= 7'd0;
                        dat_cnt  <= 13'd0;
                        crc16    <= 16'd0;
                        state    <= S_WR_START;
                    end else begin
                        bit_cnt <= bit_cnt + 1'b1;
                    end
                end
            end

            S_WR_START: begin
                if (tick_fall) begin
                    dat_out <= 1'b0;              // the start bit
                    word_sh <= buf_rdata;
                    state   <= S_WR_DATA;
                end
            end

            S_WR_DATA: begin
                if (tick_fall) begin
                    dat_out <= word_sh[31];
                    crc16   <= crc16_step(crc16, word_sh[31]);
                    word_sh <= {word_sh[30:0], 1'b0};
                    if (dat_cnt[4:0] == 5'd30) begin
                        // The next word must be on buf_rdata by the time this
                        // one runs out; the buffer's read is registered, so it
                        // is asked for one bit early.
                        fsm_addr <= dat_cnt[11:5] + 7'd1;
                    end
                    if (dat_cnt[4:0] == 5'd31)
                        word_sh <= buf_rdata;
                    if (dat_cnt == 13'd4095) begin
                        dat_cnt <= 13'd0;
                        state   <= S_WR_CRC;
                    end else begin
                        dat_cnt <= dat_cnt + 1'b1;
                    end
                end
            end

            S_WR_CRC: begin
                if (tick_fall) begin
                    dat_out <= crc16[15];
                    crc16   <= {crc16[14:0], 1'b0};
                    if (dat_cnt == 13'd15) begin
                        dat_cnt <= 13'd0;
                        state   <= S_WR_END;
                    end else begin
                        dat_cnt <= dat_cnt + 1'b1;
                    end
                end
            end

            S_WR_END: begin
                if (tick_fall) begin
                    dat_out <= 1'b1;              // the end bit
                    dat_oe  <= 1'b0;              // then let go of the line
                    bit_cnt <= 8'd0;
                    timeout <= TIMEOUT[TO_W-1:0];
                    state   <= S_WR_ACK;
                end
            end

            // ── the card's verdict on what it just received ─────
            // A start bit, three status bits, an end bit. 010 is accepted;
            // 101 is a CRC error and 110 is a write error, and both mean the
            // block did not land.
            S_WR_ACK: begin
                if (tick_rise) begin
                    if (bit_cnt == 8'd0) begin
                        if (dat_in == 1'b0) bit_cnt <= 8'd1;
                    end else if (bit_cnt <= 8'd3) begin
                        ack_sh  <= {ack_sh[1:0], dat_in};
                        bit_cnt <= bit_cnt + 1'b1;
                    end else begin
                        if (ack_sh == 3'b010) begin
                            state <= S_WR_BUSY;
                        end else begin
                            err_code <= E_WRITE_ACK;
                            state    <= S_FAIL;
                        end
                    end
                end
                if (timeout == 0) begin
                    err_code <= E_WRITE_ACK;
                    state    <= S_FAIL;
                end else begin
                    timeout <= timeout - 1'b1;
                end
            end

            // ── the card holds DAT0 low while it programs ───────
            // Returning before it lets go would let the next command reach a
            // card that is still writing -- which is how a filesystem loses
            // the block it thinks it just stored.
            S_WR_BUSY: begin
                if (tick_rise && dat_in == 1'b1)
                    state <= S_FINISH;
                if (timeout == 0) begin
                    err_code <= E_WRITE_ACK;
                    state    <= S_FAIL;
                end else begin
                    timeout <= timeout - 1'b1;
                end
            end

            // ── endings ─────────────────────────────────────────
            S_FINISH: begin
                busy   <= 1'b0;
                ok     <= 1'b1;
                err    <= 1'b0;
                clk_en <= 1'b0;
                dat_oe <= 1'b0;
                state  <= S_IDLE;
            end

            S_FAIL: begin
                busy   <= 1'b0;
                ok     <= 1'b0;
                err    <= 1'b1;
                clk_en <= 1'b0;
                dat_oe <= 1'b0;
                state  <= S_IDLE;
            end

            default: state <= S_IDLE;
            endcase
        end
    end

endmodule

`default_nettype wire
