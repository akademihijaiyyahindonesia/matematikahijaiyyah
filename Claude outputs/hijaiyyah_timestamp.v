// hijaiyyah_timestamp.v -- UTC time, disciplined by a GPS pulse-per-second.
//
// A free-running counter only tells elapsed ticks; it drifts with the crystal
// (~4 s/day at 50 ppm) and has no absolute reference. This module locks the
// sub-second counter to a GPS PPS edge: every PPS bumps the second and resets
// the tick counter, so `sec` tracks UTC and `tick` is the offset within the
// current second. It also measures the crystal against PPS (ppm_est) and
// raises `holdover` when PPS is lost (then the timestamp runs on the crystal
// alone and its uncertainty grows).
//
// TPS = ticks per second = clk frequency. Real hardware: 27_000_000.
// Simulation uses a small TPS; the logic is identical.
`default_nettype none
module hijaiyyah_timestamp #(
    parameter integer TPS = 27_000_000,
    parameter integer PPM_WARN = 100
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               pps,        // 1-clk pulse at each UTC second
    output reg  [31:0]        sec,         // seconds since epoch start
    output reg  [31:0]        tick,        // clk ticks since last PPS
    output reg                locked,      // a PPS arrived within the last ~1.5 s
    output reg                holdover,    // running on the crystal alone
    output reg  signed [31:0] ppm_est,     // measured crystal error vs PPS
    output reg                ppm_warn     // |ppm_est| > PPM_WARN
);
    localparam [31:0] TIMEOUT = TPS + TPS/2;    // 1.5 s with no PPS -> holdover
    reg [31:0] since_pps;

    // crystal error this second, in ppm (combinational from the tick count)
    wire [31:0] absdev = (tick > TPS) ? (tick - TPS) : (TPS - tick);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sec <= 32'd0; tick <= 32'd0; since_pps <= 32'd0;
            locked <= 1'b0; holdover <= 1'b1; ppm_est <= 32'sd0; ppm_warn <= 1'b0;
        end else begin
            if (pps) begin
                ppm_est   <= ($signed({1'b0, tick}) - TPS) * 32'sd1000000 / TPS;
                ppm_warn  <= (absdev * 32'd1000000 / TPS) > PPM_WARN;
                sec       <= sec + 32'd1;
                tick      <= 32'd0;
                since_pps <= 32'd0;
                locked    <= 1'b1;
                holdover  <= 1'b0;
            end else begin
                tick      <= tick + 32'd1;
                since_pps <= since_pps + 32'd1;
                if (since_pps >= TIMEOUT) begin
                    locked <= 1'b0; holdover <= 1'b1;
                end
            end
        end
    end
endmodule
`default_nettype wire
