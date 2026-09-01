// hijaiyyah_wave.v — the wave's line-rate stages: bits in, findings out.
//
// Bits arrive one per clock with no byte boundary. This deserialises them at a
// given phase and drives the node counter, so a window's class and its
// recovered XOR key come out every WINDOW bytes at full rate.
//
// WHAT IS HERE AND WHAT IS NOT, because a pipeline diagram that overstates its
// own extent is the most convincing wrong thing a design can carry.
//
//   stage 1a  phase discovery      NOT here. Finding the byte boundary needs
//                                  an index-of-coincidence histogram -- 256
//                                  bins, one block RAM -- and it runs once
//                                  per stream, not per clock. Software finds
//                                  it; `phase` is an input.
//   stage 1b  deserialise at phase  here, 8 clocks per byte.
//   stage 2   classify + key        here, via hijaiyyah_node_counter.
//   stage 3   canonical report      here only as the output wires; the packing
//                                  is software.
//   stage 4   HMAC-SHA256           NOT here. There is no SHA-256 core in this
//                                  repository. Layer 3 is software, and the
//                                  findings are unauthenticated until it runs.
//
// So this module produces findings at line rate and does not authenticate
// them. That split is the honest one: the part that must keep up with the
// wire is here, and the part that carries the security is where it has been
// reviewed.

`default_nettype none

module hijaiyyah_wave #(
    parameter integer WINDOW = 64
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [2:0] phase,        // byte boundary, discovered in software
    input  wire       bit_valid,
    input  wire       bit_in,
    output wire       found_valid,
    output wire [1:0] found_class,
    output wire [7:0] found_key
);

    // ---- stage 1b: deserialise, LSB first, starting at `phase` ----------
    reg [2:0] clocks;               // bit index within the byte
    reg [7:0] shifter;
    reg       started;
    reg [2:0] skipped;

    reg       byte_valid;
    reg [7:0] byte_out;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            clocks     <= 3'd0;
            shifter    <= 8'h00;
            started    <= 1'b0;
            skipped    <= 3'd0;
            byte_valid <= 1'b0;
            byte_out   <= 8'h00;
        end else if (bit_valid) begin
            if (!started) begin
                // Drop clocks until the boundary the caller found.
                byte_valid <= 1'b0;
                if (skipped == phase) begin
                    started <= 1'b1;
                    shifter <= {7'h00, bit_in};
                    clocks  <= 3'd1;
                end else begin
                    skipped <= skipped + 3'd1;
                end
            end else begin
                shifter <= {bit_in, shifter[7:1]};
                clocks  <= clocks + 3'd1;
                if (clocks == 3'd7) begin
                    byte_valid <= 1'b1;
                    byte_out   <= {bit_in, shifter[7:1]};
                end else begin
                    byte_valid <= 1'b0;
                end
            end
        end else begin
            byte_valid <= 1'b0;
        end
    end

    // ---- stage 2: classify and recover ---------------------------------
    hijaiyyah_node_counter #(.WINDOW(WINDOW)) u_counter (
        .clk         (clk),
        .rst_n       (rst_n),
        .valid_in    (byte_valid),
        .byte_in     (byte_out),
        .valid_out   (found_valid),
        .class_out   (found_class),
        .xor_key_out (found_key)
    );

endmodule

`default_nettype wire
