// hcpu_uart_rx.v — the receive half, which did not exist.
//
// The design could talk and not listen. That is enough to print a result and
// not enough for anything to *ask* for one: without input there is nothing
// for an operating system to mediate, no command to dispatch, no event to
// schedule against. This is the first of the six prerequisites.
//
// 8N1, no parity, no flow control. The line idles high; a falling edge starts
// a frame.
//
// SAMPLING AT BIT CENTRES, and it is the whole correctness argument. After a
// falling edge the receiver waits HALF a bit period, so the first sample
// lands in the middle of the start bit rather than on its edge — where a
// clock a few percent off still reads the right value. Sampling on edges
// works in simulation with a perfect clock and fails on a desk.
//
// The start bit is re-checked at that midpoint. A single noise glitch on an
// idle line produces a falling edge and nothing else; without the re-check it
// would be read as a frame and eight bits of noise delivered as data.

`default_nettype none

module hcpu_uart_rx #(
    parameter CLK_HZ = 27_000_000,
    parameter BAUD   = 115200
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rx_in,        // the line
    output reg  [7:0] rx_data,      // the byte, valid with rx_valid
    output reg        rx_valid,     // one clock per received byte
    output reg        rx_frame_err  // stop bit was not high
);

    localparam integer DIVISOR = CLK_HZ / BAUD;
    localparam integer HALF    = DIVISOR / 2;
    localparam integer CNT_W   = $clog2(DIVISOR + 1);

    localparam [1:0] IDLE = 2'd0, START = 2'd1, DATA = 2'd2, STOP = 2'd3;

    reg [1:0]       state;
    reg [CNT_W-1:0] count;
    reg [2:0]       index;
    reg [7:0]       shifter;

    // Two flops against metastability. The line is asynchronous to this
    // clock; sampling it directly puts a metastable value into the state
    // machine, which is the kind of fault that appears once an hour on a
    // desk and never in simulation.
    reg rx_meta, rx_sync;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) {rx_meta, rx_sync} <= 2'b11;
        else        {rx_meta, rx_sync} <= {rx_in, rx_meta};
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state        <= IDLE;
            count        <= {CNT_W{1'b0}};
            index        <= 3'd0;
            shifter      <= 8'h00;
            rx_data      <= 8'h00;
            rx_valid     <= 1'b0;
            rx_frame_err <= 1'b0;
        end else begin
            rx_valid     <= 1'b0;
            rx_frame_err <= 1'b0;

            case (state)
                IDLE: begin
                    if (!rx_sync) begin          // falling edge: possible start
                        state <= START;
                        count <= {CNT_W{1'b0}};
                    end
                end

                START: begin
                    if (count == HALF[CNT_W-1:0] - 1) begin
                        if (!rx_sync) begin      // still low at mid-bit
                            state <= DATA;
                            count <= {CNT_W{1'b0}};
                            index <= 3'd0;
                        end else begin
                            state <= IDLE;       // a glitch, not a frame
                        end
                    end else begin
                        count <= count + 1'b1;
                    end
                end

                DATA: begin
                    if (count == DIVISOR[CNT_W-1:0] - 1) begin
                        count   <= {CNT_W{1'b0}};
                        shifter <= {rx_sync, shifter[7:1]};   // LSB first
                        if (index == 3'd7) state <= STOP;
                        else               index <= index + 1'b1;
                    end else begin
                        count <= count + 1'b1;
                    end
                end

                STOP: begin
                    if (count == DIVISOR[CNT_W-1:0] - 1) begin
                        count        <= {CNT_W{1'b0}};
                        state        <= IDLE;
                        rx_data      <= shifter;
                        rx_valid     <= 1'b1;
                        rx_frame_err <= ~rx_sync;   // stop bit must be high
                    end else begin
                        count <= count + 1'b1;
                    end
                end
            endcase
        end
    end

endmodule

`default_nettype wire
