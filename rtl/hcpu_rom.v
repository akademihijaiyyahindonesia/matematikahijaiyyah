// ============================================================================
// HCPU Master Table ROM — hcpu_rom.v
// 28 letters + 6 negative vectors × 18 components × 8 bits, 144-bit entries
// Pre-unpacked from hm28.rom for single-cycle HLOAD
// (c) 2026 Maulana Amratulloh — HM-28-v1.2-HC18D
// ============================================================================
//
// Data source: data/hm28.json (SHA-256 sealed)
// Component layout: comp[i] = data_out[8*i +: 8]
//   comp[0]=Θ̂, comp[1]=Na, ..., comp[17]=Ψ
//
// Usage: addr = letter index (1–28) or negative vector (31–36),
//        data_out = 144-bit codex vector
// Combinational read (no clock needed) for single-cycle HLOAD.
//

`include "hcpu_pkg.vh"

module hcpu_rom (
    input  wire [`ROM_ADDR_W-1:0]  addr,       // 1–28 huruf, 31–36 negatif
    output reg  [`HREG_W-1:0]      data_out,   // 144-bit codex vector
    output reg                     valid       // 1 if addr in [1,28]
                                               // 31..36 = vektor negatif, valid=1
);

    // Component packing macro: {comp[17], comp[16], ..., comp[1], comp[0]}
    // So comp[i] = data_out[8*i +: 8]

    always @(*) begin
        valid = 1'b1;
        case (addr)
            // ── Index 1: Alif (ا) ──
            //  [Θ̂=0, Na=0, Nb=0, Nd=0, Kp=1, Kx=0, Ks=0, Ka=0, Kc=0,
            //   Qp=0, Qx=0, Qs=0, Qa=0, Qc=0, AN=0, AK=1, AQ=0, Ψ=0]
            6'd1:  data_out = {8'd0,8'd0,8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd0,8'd0,8'd0,8'd0,8'd0,8'd1,8'd0,8'd0,
                               8'd0,8'd0};

            // ── Index 2: Ba (ب) ──
            //  [2,0,0,1,0,1,0,0,0,1,0,0,0,0,1,1,1,0]
            6'd2:  data_out = {8'd0,8'd1,8'd1,8'd1,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd0,8'd0,8'd0,8'd1,8'd0,8'd1,8'd0,
                               8'd0,8'd2};

            // ── Index 3: Ta (ت) ──
            //  [2,2,0,0,0,1,0,0,0,1,0,0,0,0,2,1,1,0]
            6'd3:  data_out = {8'd0,8'd1,8'd1,8'd2,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd0,8'd0,8'd0,8'd1,8'd0,8'd0,8'd0,
                               8'd2,8'd2};

            // ── Index 4: Tsa (ث) ──
            //  [2,3,0,0,0,1,0,0,0,1,0,0,0,0,3,1,1,0]
            6'd4:  data_out = {8'd0,8'd1,8'd1,8'd3,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd0,8'd0,8'd0,8'd1,8'd0,8'd0,8'd0,
                               8'd3,8'd2};

            // ── Index 5: Jim (ج) ──
            //  [3,0,1,0,0,1,0,0,0,1,0,0,0,0,1,1,1,0]
            6'd5:  data_out = {8'd0,8'd1,8'd1,8'd1,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd0,8'd0,8'd0,8'd1,8'd0,8'd0,8'd1,
                               8'd0,8'd3};

            // ── Index 6: Ha (ح) ──
            //  [3,0,0,0,0,1,0,0,0,1,0,0,0,0,0,1,1,0]
            6'd6:  data_out = {8'd0,8'd1,8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd0,8'd0,8'd0,8'd1,8'd0,8'd0,8'd0,
                               8'd0,8'd3};

            // ── Index 7: Kha (خ) ──
            //  [3,1,0,0,0,1,0,0,0,1,0,0,0,0,1,1,1,0]
            6'd7:  data_out = {8'd0,8'd1,8'd1,8'd1,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd0,8'd0,8'd0,8'd1,8'd0,8'd0,8'd0,
                               8'd1,8'd3};

            // ── Index 8: Dal (د) ──
            //  [1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,0]
            6'd8:  data_out = {8'd0,8'd1,8'd0,8'd0,8'd0,8'd1,8'd0,8'd0,
                               8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd0,8'd1};

            // ── Index 9: Dzal (ذ) ──
            //  [1,1,0,0,0,0,0,0,0,0,0,0,1,0,1,0,1,0]
            6'd9:  data_out = {8'd0,8'd1,8'd0,8'd1,8'd0,8'd1,8'd0,8'd0,
                               8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd1};

            // ── Index 10: Ra (ر) ──
            //  [1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,0]
            6'd10: data_out = {8'd0,8'd1,8'd0,8'd0,8'd0,8'd0,8'd1,8'd0,
                               8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd0,8'd1};

            // ── Index 11: Zay (ز) ──
            //  [1,1,0,0,0,0,0,0,0,0,0,1,0,0,1,0,1,0]
            6'd11: data_out = {8'd0,8'd1,8'd0,8'd1,8'd0,8'd0,8'd1,8'd0,
                               8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd1};

            // ── Index 12: Sin (س) ──
            //  [4,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,3,0]
            6'd12: data_out = {8'd0,8'd3,8'd0,8'd0,8'd0,8'd0,8'd0,8'd2,
                               8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd0,8'd4};

            // ── Index 13: Syin (ش) ──
            //  [4,3,0,0,0,0,0,0,0,1,2,0,0,0,3,0,3,0]
            6'd13: data_out = {8'd0,8'd3,8'd0,8'd3,8'd0,8'd0,8'd0,8'd2,
                               8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd3,8'd4};

            // ── Index 14: Shad (ص) ──
            //  [6,0,0,0,0,0,0,0,0,1,0,0,0,1,0,0,2,0]
            6'd14: data_out = {8'd0,8'd2,8'd0,8'd0,8'd1,8'd0,8'd0,8'd0,
                               8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd0,8'd6};

            // ── Index 15: Dhad (ض) ──
            //  [6,1,0,0,0,0,0,0,0,1,0,0,0,1,1,0,2,0]
            6'd15: data_out = {8'd0,8'd2,8'd0,8'd1,8'd1,8'd0,8'd0,8'd0,
                               8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd6};

            // ── Index 16: Tha (ط) ──
            //  [4,0,0,0,0,0,1,0,0,0,0,0,0,1,0,1,1,0]
            6'd16: data_out = {8'd0,8'd1,8'd1,8'd0,8'd1,8'd0,8'd0,8'd0,
                               8'd0,8'd0,8'd0,8'd1,8'd0,8'd0,8'd0,8'd0,
                               8'd0,8'd4};

            // ── Index 17: Zha (ظ) ──
            //  [4,1,0,0,0,0,1,0,0,0,0,0,0,1,1,1,1,0]
            6'd17: data_out = {8'd0,8'd1,8'd1,8'd1,8'd1,8'd0,8'd0,8'd0,
                               8'd0,8'd0,8'd0,8'd1,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd4};

            // ── Index 18: Ain (ع) ──
            //  [3,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,2,0]
            6'd18: data_out = {8'd0,8'd2,8'd0,8'd0,8'd0,8'd0,8'd0,8'd1,
                               8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd0,8'd3};

            // ── Index 19: Ghain (غ) ──
            //  [3,1,0,0,0,0,0,0,0,1,1,0,0,0,1,0,2,0]
            6'd19: data_out = {8'd0,8'd2,8'd0,8'd1,8'd0,8'd0,8'd0,8'd1,
                               8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd3};

            // ── Index 20: Fa (ف) ──
            //  [5,1,0,0,0,1,0,0,0,1,0,0,0,1,1,1,2,0]
            6'd20: data_out = {8'd0,8'd2,8'd1,8'd1,8'd1,8'd0,8'd0,8'd0,
                               8'd1,8'd0,8'd0,8'd0,8'd1,8'd0,8'd0,8'd0,
                               8'd1,8'd5};

            // ── Index 21: Qaf (ق) ──
            //  [6,2,0,0,0,0,0,0,0,1,0,0,0,1,2,0,2,0]
            6'd21: data_out = {8'd0,8'd2,8'd0,8'd2,8'd1,8'd0,8'd0,8'd0,
                               8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd2,8'd6};

            // ── Index 22: Kaf (ك) ──
            //  [2,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0,1]
            6'd22: data_out = {8'd1,8'd0,8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd0,8'd0,8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd0,8'd2};

            // ── Index 23: Lam (ل) ──
            //  [1,0,0,0,0,1,0,0,0,1,0,0,0,0,0,1,1,0]
            6'd23: data_out = {8'd0,8'd1,8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd0,8'd0,8'd0,8'd1,8'd0,8'd0,8'd0,
                               8'd0,8'd1};

            // ── Index 24: Mim (م) ──
            //  [4,0,0,0,0,0,0,0,1,0,0,0,0,1,0,1,1,0]
            6'd24: data_out = {8'd0,8'd1,8'd1,8'd0,8'd1,8'd0,8'd0,8'd0,
                               8'd0,8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd0,8'd4};

            // ── Index 25: Nun (ن) ──
            //  [2,1,0,0,0,0,0,0,0,1,0,0,0,0,1,0,1,0]
            6'd25: data_out = {8'd0,8'd1,8'd0,8'd1,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd1,8'd2};

            // ── Index 26: Waw (و) ──
            //  [5,0,0,0,0,0,0,0,0,0,0,1,0,1,0,0,2,0]
            6'd26: data_out = {8'd0,8'd2,8'd0,8'd0,8'd1,8'd0,8'd1,8'd0,
                               8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd0,8'd5};

            // ── Index 27: Haa (هـ) ──
            //  [8,0,0,0,0,0,0,0,1,0,0,0,0,2,0,1,2,0]
            6'd27: data_out = {8'd0,8'd2,8'd1,8'd0,8'd2,8'd0,8'd0,8'd0,
                               8'd0,8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd0,8'd8};

            // ── Index 28: Ya (ي) ──
            //  [3,0,0,2,0,0,0,0,0,1,1,0,0,0,2,0,2,0]
            6'd28: data_out = {8'd0,8'd2,8'd0,8'd2,8'd0,8'd0,8'd0,8'd1,
                               8'd1,8'd0,8'd0,8'd0,8'd0,8'd0,8'd2,8'd0,
                               8'd0,8'd3};

            // ── Index 31: Test Negative (Corrupt Vector) ──
            //  [Θ̂=1, Na=0, Nb=0, Nd=0, Kp=0, Kx=0, Ks=0, Ka=0, Kc=0,
            //   Qp=0, Qx=0, Qs=0, Qa=0, Qc=2, AN=0, AK=0, AQ=2, Ψ=0]
            //
            // Fails G4 and only G4, per Bab III §IIIK.3.1: U = 4·Qc = 8,
            // so rho = 1 - 8 = -7 and (theta >= u_val) is FALSE.
            //
            // A_Q is 2, not 0, on purpose. G3 checks A_Q == sum(Q); leaving
            // it 0 would trip G3 as well and guard_pass would fall for a
            // reason the pipeline test cannot distinguish from G4. Isolating
            // G4 is the whole point of this entry — it is the one guard that
            // is a cross-constraint rather than a sum-check, and the only
            // one no other negative case at this level exercises.
            //
            // Used strictly for Hardware Pipeline Validation checks.
            6'd31: data_out = {8'd0,8'd2,8'd0,8'd0,8'd2,8'd0,8'd0,8'd0,
                               8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,8'd0,
                               8'd0,8'd1};

            // -- Index 32: Negative G1 (Corrupt Vector) --
            // A_N=0 sementara Na=1 -- sum-check zona titik gagal.
            // Diverifikasi terhadap full_guard_check: gagal G1 dan HANYA G1,
            // dengan alasan yang sama seperti indeks 31 -- kegagalan yang bisa
            // diatribusikan ke satu guard, bukan sekadar "guard menolak".
            6'd32: data_out = {8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                               8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                               8'd1, 8'd0};
            // -- Index 33: Negative G2 (Corrupt Vector) --
            // A_K=0 sementara Kp=1 -- sum-check garis gagal. Kp dipilih,
            // bukan Ks atau Kc, supaya T1 dan T2 tetap hampa.
            // Diverifikasi terhadap full_guard_check: gagal G2 dan HANYA G2,
            // dengan alasan yang sama seperti indeks 31 -- kegagalan yang bisa
            // diatribusikan ke satu guard, bukan sekadar "guard menolak".
            6'd33: data_out = {8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                               8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd1, 8'd0, 8'd0,
                               8'd0, 8'd0};
            // -- Index 34: Negative G3 (Corrupt Vector) --
            // A_Q=0 sementara Qp=1 -- sum-check lengkung gagal. Qp tidak masuk U,
            // jadi G4 tidak ikut jatuh.
            // Diverifikasi terhadap full_guard_check: gagal G3 dan HANYA G3,
            // dengan alasan yang sama seperti indeks 31 -- kegagalan yang bisa
            // diatribusikan ke satu guard, bukan sekadar "guard menolak".
            6'd34: data_out = {8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                               8'd1, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                               8'd0, 8'd0};
            // -- Index 35: Negative T1 (Corrupt Vector) --
            // Ks>0 tanpa Qc. A_K=1 sengaja diisi supaya G2 lulus dan
            // kegagalan murni T1.
            // Diverifikasi terhadap full_guard_check: gagal T1 dan HANYA T1,
            // dengan alasan yang sama seperti indeks 31 -- kegagalan yang bisa
            // diatribusikan ke satu guard, bukan sekadar "guard menolak".
            6'd35: data_out = {8'd0, 8'd0, 8'd1, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                               8'd0, 8'd0, 8'd0, 8'd1, 8'd0, 8'd0, 8'd0, 8'd0,
                               8'd0, 8'd0};
            // -- Index 36: Negative T2 (Corrupt Vector) --
            // Kc>0 tanpa Qc. A_K=1 sengaja diisi supaya G2 lulus dan
            // kegagalan murni T2.
            // Diverifikasi terhadap full_guard_check: gagal T2 dan HANYA T2,
            // dengan alasan yang sama seperti indeks 31 -- kegagalan yang bisa
            // diatribusikan ke satu guard, bukan sekadar "guard menolak".
            6'd36: data_out = {8'd0, 8'd0, 8'd1, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                               8'd0, 8'd1, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0,
                               8'd0, 8'd0};
            default: begin
                data_out = {`HREG_W{1'b0}};
                valid    = 1'b0;
            end
        endcase
    end

endmodule
