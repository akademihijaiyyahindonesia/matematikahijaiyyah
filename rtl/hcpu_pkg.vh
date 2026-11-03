// ============================================================================
// HCPU Parameter Header — hcpu_pkg.vh
// Hijaiyyah Core Processing Unit — Verilog-2001 Compatible
// (c) 2026 Maulana Amratulloh — HM-28-v1.2-HC18D
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

// Return addresses live on their OWN stack, not the PUSH/POP one. The data
// stack is a synchronous-read array so a pop's value arrives a stage late,
// which is fine for POP -- it writes a register -- and useless for RET, which
// needs its target while it is still in Execute. Reading the data stack
// combinationally would work and would also cost the design its block RAM:
// hcpu_memory.v records that an async read turns the array into 8,392
// flip-flops, and the board is already over its LUT budget.
//
// So a small dedicated array, read combinationally, and RET resolves in
// Execute exactly like a branch -- no third redirect source, no new priority
// question against traps. It costs one property: PUSH and CALL do not share a
// stack, so a subroutine cannot return to an address it pushed by hand. It
// buys the mirror of that: PUSH/POP inside a subroutine cannot corrupt the
// return path, however unbalanced they are.
`define RA_DEPTH        32          // return-address stack entries
`define RA_PTR_W        6

// ── Master Table ────────────────────────────────────────────────
`define ROM_LETTERS     28          // 28 Hijaiyyah letters
`define ROM_ADDR_W      6           // 28 huruf + 6 vektor negatif (31..36)

// ── Instruction field positions ─────────────────────────────────
// [31:24] OP  [23:20] DST  [19:16] S1  [15:12] S2  [11:0] IMM
// Named OPCODE_*, not OP_*: everything else spelled `OP_<NAME>` in this file
// is an opcode, so these two -- which are bit positions of the opcode FIELD --
// were counted as opcodes by every tool that greps for `define OP_`. That put
// 74 in an inventory table where the answer is 72.
`define OPCODE_MSB      31
`define OPCODE_LSB      24
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
`define C_HSTAR         17          // H*  — the free tag no guard constrains.
                                    // Named H* and not psi: psi is taken, and it means
                                    // the compiler that injects guards (Psi-Injector),
                                    // which is a different thing entirely. constants.py
                                    // has always called this slot H*; the RTL had not.

// ────────────────────────────────────────────────────────────────
// OPCODES — Tier 1 (Fase 1 FPGA)
// ────────────────────────────────────────────────────────────────

// System & Control (0x00–0x0F)
`define OP_NOP          8'h00
`define OP_HALT         8'h01
`define OP_MOV          8'h03       // DST ← S1
`define OP_MOVI         8'h04       // DST ← zero_ext(IMM)
`define OP_ERET         8'h08       // PC ← trap epc; leave trap
`define OP_SYSCALL      8'h09       // deliberate trap: ask supervisor
// H-ISA v1.1. FLAGS was reachable only by the J-forms, so a context switch
// could not save it -- and a process preempted between a CMP and the branch
// that reads it lost its comparison to the handler's own.
`define OP_FRD          8'h0A       // GPR[DST] ← FLAGS, zero-extended
`define OP_FWR          8'h0B       // FLAGS ← GPR[S1][7:0]

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
`define OP_CALL         8'h2E       // push PC+1 on the return stack; PC ← IMM
`define OP_RET          8'h2F       // PC ← pop of the return stack
`define OP_JGD          8'h29       // if G=1: PC ← PC + sign_ext(IMM)
`define OP_JNGD         8'h2A       // if G=0: PC ← PC + sign_ext(IMM)

// Memory (0x30–0x3F)
`define OP_LOAD         8'h30       // DST ← DataRAM[S1 + IMM]
`define OP_STORE        8'h31       // DataRAM[S2 + IMM] ← S1
`define OP_PUSH         8'h32       // stack ← S1
`define OP_POP          8'h33       // DST ← stack

// Codex Operations — Hybit Native (0x40–0x5F)
`define OP_HLOAD        8'h40       // H[DST] ← ROM[IMM]  (huruf 1–28, vektor negatif 31–36)
`define OP_CGET        8'h44       // GPR[DST] ← H[S1][IMM]   (component 0–17)
`define OP_CSET        8'h45       // H[DST][IMM] ← GPR[S1]   (component 0–17)
`define OP_CMOV        8'h46       // H[DST] ← H[S1]          (copy codex)
`define OP_CZERO       8'h47       // H[DST] ← 0              (monoid identity)
`define OP_CEQ         8'h48       // FLAGS.Z ← (H[S1] == H[S2])
`define OP_CRHO        8'h4C       // GPR[DST] ← ρ(H[S1]) = Θ̂ − U   (signed)
`define OP_CU          8'h4D       // GPR[DST] ← U(H[S1]) = Qx+Qs+Qa+4·Qc
`define OP_CTHETA      8'h4E       // GPR[DST] ← Θ̂(H[S1]) = H[S1][7:0]
`define OP_CMOD4       8'h4F       // GPR[DST] ← Θ̂(H[S1]) mod 4
`define OP_HCADD        8'h42       // H[DST] ← H[S1] + H[S2]  (18×add)
`define OP_HGRD         8'h60       // Guard G1–G4,T1–T2,H* on H[S1] → GUARD flag
`define OP_HNRM2        8'h06       // GPR[DST] ← ‖H[S1]‖²₁₄
`define OP_HDIST        8'h07       // GPR[DST] ← ‖H[S1]−H[S2]‖²₁₄

// HISAB Protocol Operations (0x50–0x5F)
`define OP_HPACK        8'h50       // HISAB nibble-pack: H[S1] → GPR[DST]=pack[31:0]
                                    //   DST+1=pack[63:32], DST+2=byte8+guard
`define OP_HCRC         8'h51       // HISAB CRC32 digest: GPR[DST] ← CRC32(LETTER frame of H[S1])
`define OP_HDOT         8'h52       // GPR[DST] ← ⟨H[S1], H[S2]⟩₁₄   (20-bit unsigned)

// I/O (0xA0–0xAF)
`define OP_PRINT        8'hA0       // UART print GPR[S1] as decimal
// H-ISA v1.1. The slot and the name are v1.0's; v1.1 fixed the string's shape
// in RAM -- one ASCII byte per 32-bit word, a zero word ends it -- and this is
// the implementation. The address is a WORD address, so the next character is
// at addr + 1: this memory is 4096 x 32 bits and LOAD/STORE index it by word.
`define OP_EMITS        8'hA2       // print the string at IMM, one char/word

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


// ── Peripheral register map ─────────────────────────────────────
// Offsets from PERIPH_BASE (the top 16 words of data space). These lived as
// localparams inside hcpu_mmio.v, which meant the trap unit and the machine
// model would each have needed their own copy. One truth, one place.
//
// THE WINDOW AND THE BLOCK ARE TWO DIFFERENT NUMBERS since H-ISA v1.2.
// `PERIPH_WINDOW` is where RAM stops and peripherals begin; `PERIPH_BASE` is
// where these sixteen registers start, and it has not moved. Widening the
// window rather than relocating anything is what let the card arrive without
// touching a single address a running program already knows -- and one
// comparator still decides, which is the property hcpu_mmio.v was built on.
//
//   0xFE0-0xFEF  the SD block, five registers of sixteen
//   0xFF0-0xFFF  UART, timer, trap, memory window, imem port -- unchanged
//
// addr[4] tells the two blocks apart: 0 is the card, 1 is everything that was
// here before v1.2.
`define PERIPH_WINDOW    12'hFE0
`define PERIPH_BASE      12'hFF0
`define REG_RX_DATA       4'h0
`define REG_RX_STATUS     4'h1
`define REG_TX_STATUS     4'h2
`define REG_COUNTER       4'h4
`define REG_COMPARE       4'h5
`define REG_TIMER_ST      4'h6
`define REG_TRAP_VECTOR   4'h8       // handler address, writable
`define REG_TRAP_EPC      4'h9       // PC saved on entry, writable (for nesting)
`define REG_TRAP_CAUSE    4'hA       // cause of the trap taken, read-only
`define REG_TRAP_ENABLE   4'hB       // per-cause enable mask, writable
`define REG_TRAP_PENDING  4'hC       // per-cause pending bits, read-only
`define REG_TRAP_MODE     4'hD       // bit0 mode (RO), bit1 previous (RW)
`define REG_MEM_BASE      4'hE       // lowest data address user mode may touch
`define REG_MEM_LIMIT     4'hF       // one past the highest

// ── The card, 0xFE0 block ───────────────────────────────────────
// Owner's decision, 14 September 2026: the TF slot is HFS's persistent
// medium, reached by LOAD/STORE like every other peripheral rather than by a
// new opcode. That choice carries the privilege boundary with it -- the
// peripheral window IS the supervisor boundary, so a user program has no path
// to the card except through a syscall.
//
// SD_DATA advances its own index, the same bargain REG_IMEM_DATA already
// made: one store per word instead of two, and 512 bytes cost 128 stores.
`define SD_CMD            4'h0       // W: 1 = init, 2 = read, 3 = write
`define SD_STATUS         4'h1       // R: bit0 busy, 1 ok, 2 error, 3 present
`define SD_SECTOR         4'h2       // RW: the block number
`define SD_DATA           4'h3       // RW: one buffer word, index advances
`define SD_CONTROL        4'h4       // RW: bit0 reset index, bit1 reset ctrl
`define SD_CSUM           4'h5       // R: 32-bit streaming Checksum32 of last read sector (Alternative A3)
`define SD_PRESCAN        4'h6       // R: 4-B' opcode pre-scan status of last read sector (Alternative A3)
// 0xFE7-0xFEF remain free. Nine words of affordance, not a gap to fill.

// ── The boot path ───────────────────────────────────────────────
// Without these the program lives inside the bitstream: $readmemh puts it
// there at synthesis and imem_data is an INPUT to hcpu_top, so the CPU cannot
// write it. Changing a program meant rebuilding and reflashing, which makes
// the board a fixed-function device rather than something you develop on.
//
// A write to REG_IMEM_DATA stores one word and ADVANCES the address, so
// loading 4,096 words costs one store each instead of two. Both registers sit
// in the peripheral window, so they are already supervisor-only -- a user
// program that could write instruction memory would have no boundary at all.
`define REG_IMEM_ADDR     4'h3       // where the next word goes
`define REG_IMEM_DATA     4'h7       // write one word, address auto-advances

// ── Trap causes ─────────────────────────────────────────────────
// One bit per cause in ENABLE and PENDING; the CAUSE register holds the index,
// not the mask, so a handler can jump on it directly.
`define TRAP_TIMER        3'd0
`define TRAP_UART_RX      3'd1
`define TRAP_ILLEGAL      3'd2
`define TRAP_PRIV         3'd3       // privileged act attempted in user mode
`define TRAP_MEM          3'd4       // data access outside [base, limit)
`define TRAP_SYSCALL      3'd5       // SYSCALL — user asking, not user failing
`define TRAP_CAUSES       6           // how many are defined
// 6..7 remain reserved. The
// width is 8 so those can be added without moving anything.

// ── Privilege ───────────────────────────────────────────────────
// Two levels, and the peripheral window is the boundary: everything the trap
// unit, the timer and the UART expose lives there, so one rule covers all of
// them. User code reaches them through a syscall, which is the step after
// this one.
`define MODE_USER         1'b0
`define MODE_SUPER        1'b1

// TRAP_PRIV IS NOT MASKABLE, and that distinction is the whole point. A timer
// or a UART byte is an INTERRUPT: it arrives from outside, and software is
// entitled to say "not now" by clearing its enable bit. A privilege violation
// is an EXCEPTION: it is the instruction stream itself doing something it may
// not, and if the enable mask could suppress it then user code could disable
// the protection by writing one register -- which is exactly the thing being
// protected against.
`define TRAP_MASK_W       8

// ── The syscall boundary ────────────────────────────────────────
// SYSCALL is the ONE crossing user mode is allowed to make. Everything else in
// the peripheral window is refused; this is refused too, and then served.
//
// It is NON-MASKABLE with the other two exceptions, and for a sharper reason
// than theirs: a maskable syscall does not fault, it does NOTHING. User code
// would call, get no answer, and continue on a return value that was never
// written. A privilege violation that cannot fire is a hole; a syscall that
// cannot fire is a silent wrong answer.
//
// epc points AT the SYSCALL, like the other exceptions, so a handler must
// advance it by one to resume past the call. That is deliberate: pointing
// past it would remove the handler's only chance to refuse.


// ── Letter instructions, 0xE0-0xFB ──────────────────────────────
// One letter is the whole instruction: HREG[0] <- HREG[0] + v(letter).
// No register field, no immediate. The ROM index is the opcode's own low
// bits, and the accumulator is implicit because there is nothing to choose.
//
// Safe rather than merely short: the guard is closed under addition, so a
// program made of letters cannot leave the valid set. A word computes its
// own codex by being written.
`define LETTER_OP_FIRST 8'hE0
`define LETTER_OP_LAST   8'hFB
`define OP_L_ALIF     8'hE0       // ا
`define OP_L_BA       8'hE1       // ب
`define OP_L_TA       8'hE2       // ت
`define OP_L_TSA      8'hE3       // ث
`define OP_L_JIM      8'hE4       // ج
`define OP_L_HA       8'hE5       // ح
`define OP_L_KHA      8'hE6       // خ
`define OP_L_DAL      8'hE7       // د
`define OP_L_DZAL     8'hE8       // ذ
`define OP_L_RA       8'hE9       // ر
`define OP_L_ZAY      8'hEA       // ز
`define OP_L_SIN      8'hEB       // س
`define OP_L_SYIN     8'hEC       // ش
`define OP_L_SHAD     8'hED       // ص
`define OP_L_DHAD     8'hEE       // ض
`define OP_L_THA      8'hEF       // ط
`define OP_L_ZHA      8'hF0       // ظ
`define OP_L_AIN      8'hF1       // ع
`define OP_L_GHAIN    8'hF2       // غ
`define OP_L_FA       8'hF3       // ف
`define OP_L_QAF      8'hF4       // ق
`define OP_L_KAF      8'hF5       // ك
`define OP_L_LAM      8'hF6       // ل
`define OP_L_MIM      8'hF7       // م
`define OP_L_NUN      8'hF8       // ن
`define OP_L_WAW      8'hF9       // و
`define OP_L_HAA      8'hFA       // هـ
`define OP_L_YA       8'hFB       // ي

`endif // HCPU_PKG_VH
