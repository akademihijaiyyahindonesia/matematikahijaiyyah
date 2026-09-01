// hijaiyyah_deserialiser.v — CMASS: bits to bytes at a discovered boundary.
//
// One bit per clock arrives with no byte boundary, because a wire does not
// carry one. `phase` says which clock starts a byte; software finds it by
// index of coincidence, once per stream rather than per clock, and the
// measurement that settled that is in src/hijaiyyah/crypto/node_counter.py.
//
// Split out of hijaiyyah_wave.v so the full system can reuse it rather than
// carry a second copy -- the same reason everything else here has one home.

`default_nettype none

module hijaiyyah_deserialiser (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [2:0] phase,
    input  wire       bit_valid,
    input  wire       bit_in,
    output reg        byte_valid,
    output reg  [7:0] byte_out
);

    reg [2:0] clocks;               // bit index within the byte
    reg [7:0] shifter;
    reg       started;
    reg [2:0] skipped;

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
                    // The first data bit enters at the TOP and shifts down,
                    // exactly like every bit after it. Putting it at [0]
                    // instead -- {7'h00, bit_in} -- meant the very next shift
                    // pushed it straight out, so only the FIRST byte of a
                    // stream came out wrong and every byte after it was right.
                    // tb_hijaiyyah_wave passed 78/78 with this bug present,
                    // because a classifier over 64-byte windows cannot see one
                    // wrong byte. Only assembling lanes and comparing them
                    // against cube.py exposed it.
                    shifter <= {bit_in, 7'h00};
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


endmodule

`default_nettype wire
