// jim_index.v -- Jim's face as a linear map over GF(5): the block index.
// v' = M v mod 5, M = Jim's exomatrix (cosmic-codex-jim/MACHINE.md s.1).
// From (1,0,0,0,0) the orbit has period 3124 (maximum, 5^5 - 1).
`default_nettype none
module jim_index (
    input  wire clk, input wire rst_n, input wire step,
    output reg [2:0] d0, d1, d2, d3, d4
);
    // x mod 5 for x in 0..24, as a table: the arithmetic % made yosys build
    // a divider (146 ALU cells) for a function of five input bits.
    function [2:0] m5; input [4:0] x;
        case (x)
            5'd0: m5 = 3'd0;
            5'd1: m5 = 3'd1;
            5'd2: m5 = 3'd2;
            5'd3: m5 = 3'd3;
            5'd4: m5 = 3'd4;
            5'd5: m5 = 3'd0;
            5'd6: m5 = 3'd1;
            5'd7: m5 = 3'd2;
            5'd8: m5 = 3'd3;
            5'd9: m5 = 3'd4;
            5'd10: m5 = 3'd0;
            5'd11: m5 = 3'd1;
            5'd12: m5 = 3'd2;
            5'd13: m5 = 3'd3;
            5'd14: m5 = 3'd4;
            5'd15: m5 = 3'd0;
            5'd16: m5 = 3'd1;
            5'd17: m5 = 3'd2;
            5'd18: m5 = 3'd3;
            5'd19: m5 = 3'd4;
            5'd20: m5 = 3'd0;
            5'd21: m5 = 3'd1;
            5'd22: m5 = 3'd2;
            5'd23: m5 = 3'd3;
            5'd24: m5 = 3'd4;
            default: m5 = 3'd0;
        endcase
    endfunction
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin d0 <= 3'd1; d1 <= 0; d2 <= 0; d3 <= 0; d4 <= 0; end
        else if (step) begin
            d0 <= m5(5'd3 * {2'd0, d0} + 5'd3 * {2'd0, d2});      // row (3,0,3,0,0)
            d1 <= m5({2'd0, d1} + {2'd0, d4});          // row (0,1,0,0,1)
            d2 <= m5({2'd0, d1});       // row (0,1,0,0,0)
            d3 <= m5({2'd0, d0});       // row (1,0,0,0,0)
            d4 <= m5({2'd0, d3} + {2'd0, d4});          // row (0,0,0,1,1)
        end
    end
endmodule
`default_nettype wire
