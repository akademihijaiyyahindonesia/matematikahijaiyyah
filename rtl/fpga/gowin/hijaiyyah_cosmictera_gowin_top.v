// ============================================================================
// Cosmictera combined top — hijaiyyah_cosmictera_gowin_top.v
// Target: Tang Nano 20K (GW2AR-LV18QN88C8/I7)
// (c) 2026 Maulana Amratulloh
// ============================================================================
//
// HCPU and Ka'bah on one chip, which cosmictera-build/ROADMAP.md's Fase 4
// calls an open question rather than a plan: 67% + 58% = 125% of the 20K's
// 20,736 LUT4 if the two are simply added, so they may not fit side by side
// at all without the design changing.
//
// THIS VERSION EXISTS TO MEASURE, NOT TO SHIP. It instantiates the two
// existing board wrappers whole, which means it also duplicates everything
// the roadmap wants shared -- two UART receivers, two transmitters, two
// reset synchronisers. That is deliberate: it is the worst case, and the
// worst case is the useful first number. If this fits, every shared version
// fits. If it does not, the gap it misses by says how much sharing has to
// buy, and that is a better starting point than guessing which economy to
// attempt first.
//
// What it is NOT yet: Ka'bah as a Hybit service. The roadmap's actual target
// is hcpu_top and hijaiyyah_kabah_top under one clock, one reset and one
// UART, with MMIO as the path HCPU uses to call Ka'bah -- the step that
// makes layer 5 of the seven-layer table real instead of two systems that
// happen to share a repository. `sel` below is a placeholder for that path,
// not a design decision: one core owns the serial line at a time.
//
`include "hcpu_pkg.vh"

module hijaiyyah_cosmictera_gowin_top (
    input  wire        clk_27m,
    input  wire        btn_rst_n,
    input  wire        sel,        // 0: HCPU owns the UART, 1: Ka'bah does
    input  wire        uart_rxd,
    output wire        uart_txd,
    output wire [5:0]  led
);

    wire       hcpu_txd;
    wire       kabah_txd;
    wire [5:0] hcpu_led;
    wire [5:0] kabah_led;

    // An idle UART line is high, so the core that does not own the line is
    // held at idle rather than fed the other one's traffic -- otherwise both
    // receivers would decode every byte and Ka'bah would absorb the loader's
    // protocol as data.
    hcpu_gowin_top u_hcpu (
        .clk_27m   (clk_27m),
        .btn_rst_n (btn_rst_n),
        .uart_rxd  (sel ? 1'b1 : uart_rxd),
        .uart_txd  (hcpu_txd),
        .led       (hcpu_led)
    );

    hijaiyyah_kabah_gowin_top u_kabah (
        .clk_27m   (clk_27m),
        .btn_rst_n (btn_rst_n),
        .uart_rxd  (sel ? uart_rxd : 1'b1),
        .uart_txd  (kabah_txd),
        .led       (kabah_led)
    );

    assign uart_txd = sel ? kabah_txd : hcpu_txd;
    assign led      = sel ? kabah_led : hcpu_led;

endmodule
