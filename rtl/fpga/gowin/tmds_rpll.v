// Open-source PLL generated with gowin_pll for Tang Nano 20K.
// 27 MHz input -> 371.25 MHz TMDS serial clock for 1280x720@60 HDMI.

module TMDS_rPLL (
    input wire  clkin,
    output wire clkout,
    output wire lock
);
    rPLL #(
        .FCLKIN("27.0"),
        .IDIV_SEL(3),
        .FBDIV_SEL(54),
        .ODIV_SEL(2)
    ) pll (
        .CLKOUTP(), .CLKOUTD(), .CLKOUTD3(),
        .RESET(1'b0), .RESET_P(1'b0), .CLKFB(1'b0),
        .FBDSEL(6'b0), .IDSEL(6'b0), .ODSEL(6'b0),
        .PSDA(4'b0), .DUTYDA(4'b0), .FDLY(4'b0),
        .CLKIN(clkin), .CLKOUT(clkout), .LOCK(lock)
    );
endmodule
