// hcpu_timer.v — a free-running counter and one compare.
//
// The second prerequisite. Without a clock a program can only respond to what
// it is handed; it cannot wait, time out, or be preempted, and every one of
// those is something an operating system exists to do.
//
// Deliberately the smallest thing that is still useful: a 32-bit counter that
// never stops, one compare register, and a sticky flag when they meet. No
// prescaler, no modes, no auto-reload — those are conveniences, and each is a
// place for the interpreter and the pipeline to disagree.
//
// The flag is STICKY and cleared by writing, not by reading. A flag cleared by
// reading cannot be polled by two pieces of code: the first read consumes the
// event and the second sees nothing. Clearing on write makes the consumer say
// so explicitly.

`default_nettype none

module hcpu_timer (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [31:0] compare_in,
    input  wire        compare_we,   // set the compare value
    input  wire        clear,        // clear the expired flag
    output reg  [31:0] counter,
    output reg  [31:0] compare,
    output reg         expired
);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            counter <= 32'd0;
            compare <= 32'hFFFF_FFFF;
            expired <= 1'b0;
        end else begin
            counter <= counter + 32'd1;

            if (compare_we) begin
                compare <= compare_in;
                expired <= 1'b0;          // a new deadline is not already met
            end else if (clear) begin
                expired <= 1'b0;
            end else if (counter == compare) begin
                expired <= 1'b1;
            end
        end
    end

endmodule

`default_nettype wire
