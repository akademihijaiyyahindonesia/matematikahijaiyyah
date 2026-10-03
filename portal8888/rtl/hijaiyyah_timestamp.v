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
    parameter integer PPM_WARN = 100,
    parameter integer HOLDOVER_PPM = 50
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               pps,        // 1-clk pulse at each UTC second
    input  wire               provision_time,
    input  wire [31:0]        provision_utc_sec,
    input  wire [31:0]        provision_uncert_ns,
    output reg  [31:0]        sec,         // provisioned UTC seconds
    output reg  [31:0]        tick,        // clk ticks since last PPS
    output reg                locked,      // a PPS arrived within the last ~1.5 s
    output reg                holdover,    // running on the crystal alone
    output reg  signed [31:0] ppm_est,     // measured crystal error vs PPS
    output reg                ppm_warn,    // |ppm_est| > PPM_WARN
    output reg  [1:0]         time_source, // 0 free, 2 GPS-PPS
    output reg  [31:0]        uncert_ns
);
    localparam [31:0] TIMEOUT = TPS + TPS/2;    // 1.5 s with no PPS -> holdover
    reg [31:0] since_pps;
    reg [31:0] base_uncert_ns, growing_uncert_ns, uncert_remainder;
    reg advanced_since_pps;

    // crystal error this second, in ppm (combinational from the tick count)
    wire [31:0] absdev = (since_pps > TPS) ? (since_pps - TPS) : (TPS - since_pps);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sec <= 32'd0; tick <= 32'd0; since_pps <= 32'd0;
            locked <= 1'b0; holdover <= 1'b1; ppm_est <= 32'sd0; ppm_warn <= 1'b0;
            time_source <= 2'd0; uncert_ns <= 32'd0;
            base_uncert_ns <= 32'd0; growing_uncert_ns <= 32'd0;
            uncert_remainder <= 32'd0; advanced_since_pps <= 1'b0;
        end else begin
            if (provision_time) begin
                sec <= provision_utc_sec; tick <= 32'd0; since_pps <= 32'd0;
                locked <= 1'b0; holdover <= 1'b1; ppm_est <= 32'sd0; ppm_warn <= 1'b0;
                time_source <= 2'd0; uncert_ns <= provision_uncert_ns;
                base_uncert_ns <= provision_uncert_ns;
                growing_uncert_ns <= provision_uncert_ns;
                uncert_remainder <= 32'd0; advanced_since_pps <= 1'b0;
            end else if (pps) begin
                if (!advanced_since_pps) sec <= sec + 32'd1;
                ppm_est   <= (since_pps > TIMEOUT) ? 32'sd0 :
                             ($signed({1'b0, since_pps}) - TPS) * 32'sd1000000 / TPS;
                ppm_warn  <= (since_pps > TIMEOUT) ? 1'b1 :
                             (absdev * 32'd1000000 / TPS) > PPM_WARN;
                tick      <= 32'd0;
                since_pps <= 32'd0;
                locked    <= 1'b1;
                holdover  <= 1'b0;
                time_source <= 2'd2;
                uncert_ns <= base_uncert_ns;
                growing_uncert_ns <= base_uncert_ns;
                uncert_remainder <= 32'd0;
                advanced_since_pps <= 1'b0;
            end else begin
                if (tick == TPS-1) begin
                    tick <= 32'd0;
                    sec <= sec + 32'd1;
                    advanced_since_pps <= 1'b1;
                end else tick <= tick + 32'd1;
                since_pps <= since_pps + 32'd1;
                if (uncert_remainder + HOLDOVER_PPM*1000 >= TPS) begin
                    uncert_remainder <= uncert_remainder + HOLDOVER_PPM*1000 - TPS;
                    growing_uncert_ns <= growing_uncert_ns + 32'd1;
                end else uncert_remainder <= uncert_remainder + HOLDOVER_PPM*1000;
                if (since_pps >= TIMEOUT) begin
                    locked <= 1'b0; holdover <= 1'b1;
                    time_source <= 2'd0;
                    uncert_ns <= growing_uncert_ns;
                end
            end
        end
    end
endmodule
`default_nettype wire
