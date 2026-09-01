// hijaiyyah_round_constants.v — the 28 constants, from the sealed cube.
//
// GENERATED from src/hijaiyyah/crypto/cube.py. Regenerate with
//     python3 tools/gen_linear_rtl.py
//
// One per round. They break the round function's symmetry: without them every
// round would be the same permutation and a slide attack would apply.

`default_nettype none

module hijaiyyah_round_constants (
    input  wire [7:0]  round_index,
    output reg  [63:0] round_constant
);
    always @* begin
        case (round_index)
            8'd0: round_constant = 64'hC64C32A3ECA70B49;
            8'd1: round_constant = 64'hB72BDF05006F3A28;
            8'd2: round_constant = 64'hF9AA2B41E27CC650;
            8'd3: round_constant = 64'hB3CED002E626016D;
            8'd4: round_constant = 64'hAF155258B1B9B9B4;
            8'd5: round_constant = 64'hD5483A1A380FB718;
            8'd6: round_constant = 64'h7B577D2E7268F9D2;
            8'd7: round_constant = 64'hB97417BE227556EC;
            8'd8: round_constant = 64'hC73C304C35778800;
            8'd9: round_constant = 64'h4E9CAC294B5C0E39;
            8'd10: round_constant = 64'h2181F86D3A7894D0;
            8'd11: round_constant = 64'hC1F1F05D4BF970F6;
            8'd12: round_constant = 64'hA6435FAB2B0CBA07;
            8'd13: round_constant = 64'hBF4AB481E5AD79C4;
            8'd14: round_constant = 64'h541CDDE7B68EF854;
            8'd15: round_constant = 64'h6CF91A0B6232D35A;
            8'd16: round_constant = 64'hCBD26AC9B6FD8BF2;
            8'd17: round_constant = 64'h94AD8B1BF9F6C9C6;
            8'd18: round_constant = 64'hEEA49BE118C1775E;
            8'd19: round_constant = 64'h38C20916F3D57DB3;
            8'd20: round_constant = 64'h5AF7441BE44E4FF8;
            8'd21: round_constant = 64'h10699489E22D769F;
            8'd22: round_constant = 64'hF9D6EDBCDB0D878C;
            8'd23: round_constant = 64'h25FBC2AB1F1AF91E;
            8'd24: round_constant = 64'hEE63E8DBE30F6ACF;
            8'd25: round_constant = 64'hD286FAEB2A175E46;
            8'd26: round_constant = 64'h88F69618CB92381F;
            8'd27: round_constant = 64'hCAC488079927F913;
            default: round_constant = 64'h0000000000000000;
        endcase
    end
endmodule

`default_nettype wire
