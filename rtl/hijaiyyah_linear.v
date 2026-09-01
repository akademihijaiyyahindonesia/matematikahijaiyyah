// hijaiyyah_linear.v — theta then rho-pi, the round's linear layer.
//
// GENERATED from src/hijaiyyah/crypto/cube.py. Do not hand-edit: RHO and PI
// below come from the sealed cube, and a hand-edit is how the RTL and the
// Python stop agreeing. Regenerate with
//     python3 tools/gen_linear_rtl.py
//
// Pure wiring and XOR -- every lane rotation is a bit-select, costing nothing
// -- but "pure XOR" is not the same as "free". Synthesised, this layer is
// **2560 LUT4**, because each of 1600 output bits folds in two column
// parities as well as its own lane. That is more than a 25-byte substitution
// router (2023 LUT4), and it corrects the loose reasoning that first
// motivated the ramal schedule.
//
// The trade still holds, and now with numbers instead of a hand-wave. Against
// a full 200-byte substitution at 15,200 LUT4:
//
//     walk  [1,1,1]   3 linear + 3 sub   =  7,680 + 45,600 = 53,280 LUT4
//     ramal [2,1]     3 linear + 2 sub   =  7,680 + 30,400 = 38,080 LUT4
//
// a 28.5% saving. Time-multiplexed -- which is what actually fits a Tang Nano
// 9K, at 25 bytes per clock -- the same trade reads in clocks: 3 + 3x8 = 27
// against 3 + 2x8 = 19, a 30% saving. Buying a linear layer to sell a
// substitution layer is a good trade because the two are an order of
// magnitude apart, not because one of them is free.
//
//   theta   parity of each column, folded with a neighbour's rotated parity
//           D[x] = C[x-1] XOR rotl(C[x+1], 1)   <- both neighbours, every round
//   rho     lane i rotates left by RHO[i] = i(i+1)/2 mod 64
//   pi      lane i moves to PI[i] = 5(i mod 5) + ((i div 5) + 3(i mod 5)) mod 5
//
// Combinational: one propagation delay, no clock, no state. Checked against
// cube.linear_layer over 64 random states by rtl/tb/tb_hijaiyyah_linear.v.
// Three sabotages were induced before trusting that testbench -- a shifted rho
// rotation, a swapped pi destination, and a dropped theta neighbour -- and all
// three are caught. The first attempt at the rho sabotage silently matched
// nothing and reported PASS, which is its own lesson about sabotage tests.

`default_nettype none

module hijaiyyah_linear (
    input  wire [1599:0] in_state,
    output wire [1599:0] out_state
);

    wire [63:0] lane [0:24];
    genvar g;
    generate
        for (g = 0; g < 25; g = g + 1) begin : split
            assign lane[g] = in_state[g*64 +: 64];
        end
    endgenerate

    // ---- theta: column parity, folded with both neighbours -------------
    wire [63:0] parity0 = lane[0] ^ lane[5] ^ lane[10] ^ lane[15] ^ lane[20];
    wire [63:0] parity1 = lane[1] ^ lane[6] ^ lane[11] ^ lane[16] ^ lane[21];
    wire [63:0] parity2 = lane[2] ^ lane[7] ^ lane[12] ^ lane[17] ^ lane[22];
    wire [63:0] parity3 = lane[3] ^ lane[8] ^ lane[13] ^ lane[18] ^ lane[23];
    wire [63:0] parity4 = lane[4] ^ lane[9] ^ lane[14] ^ lane[19] ^ lane[24];

    wire [63:0] fold0 = parity4 ^ {parity1[62:0], parity1[63:63]};
    wire [63:0] fold1 = parity0 ^ {parity2[62:0], parity2[63:63]};
    wire [63:0] fold2 = parity1 ^ {parity3[62:0], parity3[63:63]};
    wire [63:0] fold3 = parity2 ^ {parity4[62:0], parity4[63:63]};
    wire [63:0] fold4 = parity3 ^ {parity0[62:0], parity0[63:63]};

    wire [63:0] th0 = lane[0] ^ fold0;
    wire [63:0] th1 = lane[1] ^ fold1;
    wire [63:0] th2 = lane[2] ^ fold2;
    wire [63:0] th3 = lane[3] ^ fold3;
    wire [63:0] th4 = lane[4] ^ fold4;
    wire [63:0] th5 = lane[5] ^ fold0;
    wire [63:0] th6 = lane[6] ^ fold1;
    wire [63:0] th7 = lane[7] ^ fold2;
    wire [63:0] th8 = lane[8] ^ fold3;
    wire [63:0] th9 = lane[9] ^ fold4;
    wire [63:0] th10 = lane[10] ^ fold0;
    wire [63:0] th11 = lane[11] ^ fold1;
    wire [63:0] th12 = lane[12] ^ fold2;
    wire [63:0] th13 = lane[13] ^ fold3;
    wire [63:0] th14 = lane[14] ^ fold4;
    wire [63:0] th15 = lane[15] ^ fold0;
    wire [63:0] th16 = lane[16] ^ fold1;
    wire [63:0] th17 = lane[17] ^ fold2;
    wire [63:0] th18 = lane[18] ^ fold3;
    wire [63:0] th19 = lane[19] ^ fold4;
    wire [63:0] th20 = lane[20] ^ fold0;
    wire [63:0] th21 = lane[21] ^ fold1;
    wire [63:0] th22 = lane[22] ^ fold2;
    wire [63:0] th23 = lane[23] ^ fold3;
    wire [63:0] th24 = lane[24] ^ fold4;

    // ---- rho and pi: rotate each lane, then move it -------------------
    assign out_state[0*64 +: 64] = th0;
    assign out_state[8*64 +: 64] = {th1[62:0], th1[63:63]};
    assign out_state[11*64 +: 64] = {th2[60:0], th2[63:61]};
    assign out_state[19*64 +: 64] = {th3[57:0], th3[63:58]};
    assign out_state[22*64 +: 64] = {th4[53:0], th4[63:54]};
    assign out_state[1*64 +: 64] = {th5[48:0], th5[63:49]};
    assign out_state[9*64 +: 64] = {th6[42:0], th6[63:43]};
    assign out_state[12*64 +: 64] = {th7[35:0], th7[63:36]};
    assign out_state[15*64 +: 64] = {th8[27:0], th8[63:28]};
    assign out_state[23*64 +: 64] = {th9[18:0], th9[63:19]};
    assign out_state[2*64 +: 64] = {th10[8:0], th10[63:9]};
    assign out_state[5*64 +: 64] = {th11[61:0], th11[63:62]};
    assign out_state[13*64 +: 64] = {th12[49:0], th12[63:50]};
    assign out_state[16*64 +: 64] = {th13[36:0], th13[63:37]};
    assign out_state[24*64 +: 64] = {th14[22:0], th14[63:23]};
    assign out_state[3*64 +: 64] = {th15[7:0], th15[63:8]};
    assign out_state[6*64 +: 64] = {th16[55:0], th16[63:56]};
    assign out_state[14*64 +: 64] = {th17[38:0], th17[63:39]};
    assign out_state[17*64 +: 64] = {th18[20:0], th18[63:21]};
    assign out_state[20*64 +: 64] = {th19[1:0], th19[63:2]};
    assign out_state[4*64 +: 64] = {th20[45:0], th20[63:46]};
    assign out_state[7*64 +: 64] = {th21[24:0], th21[63:25]};
    assign out_state[10*64 +: 64] = {th22[2:0], th22[63:3]};
    assign out_state[18*64 +: 64] = {th23[43:0], th23[63:44]};
    assign out_state[21*64 +: 64] = {th24[19:0], th24[63:20]};

endmodule

`default_nettype wire
