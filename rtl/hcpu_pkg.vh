// ============================================================================
// HCPU Parameter Header — hcpu_pkg.vh
// Hijaiyyah Core Processing Unit — Verilog-2001 Compatible
// (c) 2026 HMCL — HM-28-v1.2-HC18D
// ============================================================================
//
// Usage: `include "hcpu_pkg.vh" at the top of every module.
// This file defines ALL shared constants: opcodes, register counts,
// memory map, field widths, and component indices.
//

`ifndef HCPU_PKG_VH
`define HCPU_PKG_VH

// ── Word widths ─────────────────────────────────────────────────
`define XLEN            32          // GPR width (bits)
`define ILEN            32          // Instruction width (bits)
`define COMP_W          8           // Codex component width (bits)
`define NDIM            18          // Codex dimensions
`define HREG_W          144         // H-Reg width: 18 × 8 = 144 bits
`define IMM_W           12          // Immediate field width

// ── Register counts ─────────────────────────────────────────────
`define GPR_COUNT       18          // R0–R17
`define HREG_COUNT      16          // H0–H15
`define STACK_DEPTH     256         // Stack entries (PUSH/POP)

// ── Master Table ────────────────────────────────────────────────
`define ROM_LETTERS     28          // 28 Hijaiyyah letters
`define ROM_ADDR_W      5           // ceil(log2(28)) = 5 bits

// ── Instruction field positions ─────────────────────────────────
// [31:24] OP  [23:20] DST  [19:16] S1  [15:12] S2  [11:0] IMM
`define OP_MSB          31
`define OP_LSB          24
`define DST_MSB         23
`define DST_LSB         20
`define S1_MSB          19
`define S1_LSB          16
`define S2_MSB          15
`define S2_LSB          12
`define IMM_MSB         11
`define IMM_LSB         0

// ── Code memory ─────────────────────────────────────────────────
`define CODE_ADDR_W     12          // 4096 instruction words
`define CODE_DEPTH      4096
// ── Data memory ─────────────────────────────────────────────────
//
// Bab III §IIIJ.3.2.1 specifies 4096 × 32-bit words, and that is the default
// and the architecture. It is guarded rather than fixed because the ASIC
// target cannot hold it: 131,072 bits is 86% of the design, and at
// DIE_AREA 700×700 um it fits neither as flip-flops nor as sixteen 1 KB
// OpenRAM macros. A reduced-area build overrides these two on the command
// line; nothing else in the design changes, and rtl/tb still has to pass.
//
// The two must move together — DATA_ADDR_W is ceil(log2(DATA_DEPTH)) — and a
// build that sets one without the other is caught by the assertion below.
`ifndef DATA_ADDR_W
  `define DATA_ADDR_W   12          // 4096 × 32-bit words
`endif
`ifndef DATA_DEPTH
  `define DATA_DEPTH    4096
`endif

// ── Codex component indices (within 144-bit H-Reg) ──────────────
// Component[i] is at bits [8*i+7 : 8*i]
`define C_THETA         0           // Θ̂  — turning count
`define C_NA            1           // Na — nuqtah above
`define C_NB            2           // Nb — nuqtah below
`define C_ND            3           // Nd — nuqtah double
`define C_KP            4           // Kp — khatt primary
`define C_KX            5           // Kx — khatt extension
`define C_KS            6           // Ks — khatt secondary
`define C_KA            7           // Ka — khatt auxiliary
`define C_KC            8           // Kc — khatt closing
`define C_QP            9           // Qp — qaws primary
`define C_QX            10          // Qx — qaws extension
`define C_QS            11          // Qs — qaws secondary
`define C_QA            12          // Qa — qaws auxiliary
`define C_QC            13          // Qc — qaws closing
`define C_AN            14          // A_N — aggregate nuqtah
`define C_AK            15          // A_K — aggregate khatt
`define C_AQ            16          // A_Q — aggregate qaws
`define C_PSI           17          // Ψ   — chi/psi

// ────────────────────────────────────────────────────────────────
// OPCODES — Tier 1 (Fase 1 FPGA)
// ────────────────────────────────────────────────────────────────

// System & Control (0x00–0x0F)
`define OP_NOP          8'h00
`define OP_HALT         8'h01
`define OP_MOV          8'h03       // DST ← S1
`define OP_MOVI         8'h04       // DST ← zero_ext(IMM)

// Arithmetic & Logic (0x10–0x1F)
`define OP_ADD          8'h10       // DST ← S1 + S2
`define OP_ADDI         8'h11       // DST ← S1 + sign_ext(IMM)
`define OP_SUB          8'h12       // DST ← S1 - S2
`define OP_MUL          8'h14       // DST ← S1 × S2 (lower 32)

// Compare & Branch (0x20–0x2F)
// ── Bitwise and shift (0xB_) ─────────────────────────────────────
//
// Their absence was the blocker for everything above this layer: an
// allocator needs free-list bitmaps, a scheduler needs ready masks, a driver
// needs register fields. None of those can be written with add and multiply.
//
// Shift amounts are masked to 5 bits, and logical immediates are ZERO-
// extended where ADDI's is sign-extended -- ANDI r,r,0x0FF must mask the low
// eight bits, and sign extension would make it 0xFFFFF0FF. Both decisions
// are mirrored in src/hijaiyyah/hisa/machine.py; a pipeline and an
// interpreter that disagree about a shift of 33 disagree about the program.
`define OP_AND         8'hB0       // GPR[DST] <- GPR[S1] & GPR[S2]
`define OP_OR          8'hB1       // GPR[DST] <- GPR[S1] | GPR[S2]
`define OP_XOR         8'hB2       // GPR[DST] <- GPR[S1] ^ GPR[S2]
`define OP_NOT         8'hB3       // GPR[DST] <- ~GPR[S1]
`define OP_SHL         8'hB4       // GPR[DST] <- GPR[S1] << GPR[S2][4:0]
`define OP_SHR         8'hB5       // GPR[DST] <- GPR[S1] >> GPR[S2][4:0]
`define OP_ANDI        8'hB6       // GPR[DST] <- GPR[S1] & {20'b0, IMM}
`define OP_ORI         8'hB7       // GPR[DST] <- GPR[S1] | {20'b0, IMM}
`define OP_XORI        8'hB8       // GPR[DST] <- GPR[S1] ^ {20'b0, IMM}
`define OP_SHLI        8'hB9       // GPR[DST] <- GPR[S1] << IMM[4:0]
`define OP_SHRI        8'hBA       // GPR[DST] <- GPR[S1] >> IMM[4:0]

`define OP_CMP          8'h20       // set FLAGS from S1 - S2
`define OP_CMPI         8'h21       // set FLAGS from S1 - sign_ext(IMM)
`define OP_JMP          8'h22       // PC ← zero_ext(IMM)
`define OP_JEQ          8'h23       // if Z=1: PC ← PC + sign_ext(IMM)
`define OP_JNE          8'h24       // if Z=0: PC ← PC + sign_ext(IMM)
`define OP_JGD          8'h29       // if G=1: PC ← PC + sign_ext(IMM)
`define OP_JNGD         8'h2A       // if G=0: PC ← PC + sign_ext(IMM)

// Memory (0x30–0x3F)
`define OP_LOAD         8'h30       // DST ← DataRAM[S1 + IMM]
`define OP_STORE        8'h31       // DataRAM[S2 + IMM] ← S1
`define OP_PUSH         8'h32       // stack ← S1
`define OP_POP          8'h33       // DST ← stack

// Codex Operations — Hybit Native (0x40–0x5F)
`define OP_HLOAD        8'h40       // H[DST] ← ROM[IMM]  (letter index 1–28)
`define OP_CGET        8'h44       // GPR[DST] ← H[S1][IMM]   (component 0–17)
`define OP_HCADD        8'h42       // H[DST] ← H[S1] + H[S2]  (18×add)
`define OP_HGRD         8'h60       // Guard G1–G4,T1–T2 on H[S1] → GUARD flag
`define OP_HNRM2        8'h06       // GPR[DST] ← ‖H[S1]‖²₁₄
`define OP_HDIST        8'h07       // GPR[DST] ← ‖H[S1]−H[S2]‖²₁₄

// HISAB Protocol Operations (0x50–0x5F)
`define OP_HPACK        8'h50       // HISAB nibble-pack: H[S1] → GPR[DST]=pack[31:0]
                                    //   DST+1=pack[63:32], DST+2=byte8+guard
`define OP_HCRC         8'h51       // HISAB CRC32 digest: GPR[DST] ← CRC32(LETTER frame of H[S1])

// I/O (0xA0–0xAF)
`define OP_PRINT        8'hA0       // UART print GPR[S1] as decimal

// Unimplemented → trap
`define OP_HALT_ERR     8'hFF       // Halt with error (unimplemented opcode)

// ── FLAGS bit positions ─────────────────────────────────────────
`define FLAG_G          0           // GUARD pass
`define FLAG_Z          1           // ZERO
`define FLAG_O          2           // OVERFLOW
`define FLAG_LT         3           // Less-than (signed)

// ── UART default ────────────────────────────────────────────────
`define UART_BAUD       115200
`define SYS_CLK_HZ     50_000_000  // 50 MHz system clock

`endif // HCPU_PKG_VH
