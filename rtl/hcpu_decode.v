// ============================================================================
// HCPU Decode Stage — hcpu_decode.v
// Instruction field extraction, register read, control signal generation
// (c) 2026 Maulana Amratulloh — HM-28-v1.2-HC18D
// ============================================================================

`include "hcpu_pkg.vh"

module hcpu_decode (
    input  wire                    clk,
    input  wire                    rst_n,

    // ── Pipeline control ────────────────────────────────────────
    input  wire                    stall,
    input  wire                    flush,

    // ── Input from Fetch ────────────────────────────────────────
    input  wire [`ILEN-1:0]        if_instruction,
    input  wire [`XLEN-1:0]        if_pc,

    // ── Register file read (combinational) ──────────────────────
    output wire [4:0]              gpr_raddr1,     // → regfile
    output wire [4:0]              gpr_raddr2,
    input  wire [`XLEN-1:0]        gpr_rdata1,     // ← regfile
    input  wire [`XLEN-1:0]        gpr_rdata2,
    output wire [3:0]              hreg_raddr1,    // → regfile
    output wire [3:0]              hreg_raddr2,
    input  wire [`HREG_W-1:0]      hreg_rdata1,    // ← regfile
    input  wire [`HREG_W-1:0]      hreg_rdata2,

    // ── Output to Execute (pipeline register) ───────────────────
    output reg  [7:0]              id_opcode,
    output reg  [3:0]              id_dst,
    output reg  [3:0]              id_s1,
    output reg  [3:0]              id_s2,
    output reg  [11:0]             id_imm,
    output reg  [`XLEN-1:0]        id_gpr_s1,     // GPR[S1] value
    output reg  [`XLEN-1:0]        id_gpr_s2,     // GPR[S2] value
    output reg  [`HREG_W-1:0]      id_hreg_s1,    // H-Reg[S1] value
    output reg  [`HREG_W-1:0]      id_hreg_s2,    // H-Reg[S2] value
    output reg  [`XLEN-1:0]        id_pc,         // PC of this instruction

    // ── Decoded control signals ─────────────────────────────────
    output reg                     id_gpr_we,     // Write to GPR
    output reg                     id_hreg_we,    // Write to H-Reg
    output reg                     id_mem_read,   // Load from data RAM
    output reg                     id_mem_write,  // Store to data RAM
    output reg                     id_is_branch,  // Branch instruction
    output reg                     id_is_jump,    // Unconditional jump
    output reg                     id_is_call,    // CALL: link then jump
    output reg                     id_is_ret,     // RET:  jump to the link
    output reg                     id_is_codex,   // Codex H-Reg operation
    output reg                     id_is_halt,    // HALT instruction
    output reg                     id_is_print,   // PRINT instruction
    output reg                     id_is_push,    // Stack push
    output reg                     id_is_pop,     // Stack pop

    // ── Input from Execute for Hazard Detection ──────────────────
    input  wire                    ex_mem_read,   // EX is doing a LOAD
    input  wire                    ex_mem_write,  // EX is doing a STORE
    input  wire [3:0]              ex_dst,        // EX destination
    input  wire [`DATA_ADDR_W-1:0] ex_mem_addr,   // EX computed memory address

    // ── Output to Controller ────────────────────────────────────
    output wire                    load_use_hazard,  // Load-use penalty
    output wire                    store_load_hazard // Store-load address conflict
);

    wire [7:0]  opcode = if_instruction[`OPCODE_MSB:`OPCODE_LSB];
    wire [3:0]  dst    = if_instruction[`DST_MSB:`DST_LSB];
    wire [3:0]  s1     = if_instruction[`S1_MSB:`S1_LSB];
    wire [3:0]  s2     = if_instruction[`S2_MSB:`S2_LSB];
    wire [11:0] imm    = if_instruction[`IMM_MSB:`IMM_LSB];

    // ── Operand Dependency Decode (combinational) ───────────────
    // Two independent case blocks: a single case statement cannot set both
    // id_uses_s1 and id_uses_s2 for the same opcode because Verilog case
    // only executes the first matching branch.
    reg id_uses_s1, id_uses_s2;
    always @(*) begin
        id_uses_s1 = 1'b0;
        id_uses_s2 = 1'b0;

        // S1 usage: instructions that read GPR[S1] or H-Reg[S1]
        case (opcode)
            `OP_MOV, `OP_ADD, `OP_SUB, `OP_MUL, `OP_CMP, `OP_ADDI, `OP_CMPI,
            `OP_AND, `OP_OR, `OP_XOR, `OP_NOT, `OP_SHL, `OP_SHR,
            `OP_ANDI, `OP_ORI, `OP_XORI, `OP_SHLI, `OP_SHRI,
            `OP_LOAD, `OP_STORE, `OP_HCADD, `OP_HGRD, `OP_HNRM2, `OP_HDIST,
            `OP_CGET, `OP_CSET,
            `OP_CMOV, `OP_CEQ, `OP_CRHO, `OP_CU, `OP_CMOD4,
            `OP_FWR,
            `OP_HPACK, `OP_HCRC,
            `OP_PRINT, `OP_PUSH: id_uses_s1 = 1'b1;
            default: ;
        endcase

        // S2 usage: instructions that read GPR[S2] or H-Reg[S2]
        case (opcode)
            `OP_ADD, `OP_SUB, `OP_MUL, `OP_CMP,
            `OP_AND, `OP_OR, `OP_XOR, `OP_SHL, `OP_SHR,
            `OP_STORE, `OP_HCADD, `OP_HDIST,
            `OP_CEQ: id_uses_s2 = 1'b1;
            default: ;
        endcase
    end

    // ── Load-Use Hazard Detection ───────────────────────────────
    // With BRAM-latency fetch, by the time LOAD reaches EX, the dependent
    // instruction has already entered decode. So we detect the hazard one
    // stage earlier: when LOAD is in the decode pipeline register (id_*)
    // and the current IF instruction (s1/s2) depends on the LOAD's dst.
    //
    // The flush-based stall mechanism then:
    //   1. Freezes fetch (hold IF instruction)
    //   2. Flushes decode (NOP into ID pipeline register)
    //   3. LOAD flows from decode → EX (because decode runs, not stalled)
    //   4. Next cycle: ADD enters decode, LOAD at EX → MEM, no stall
    //   5. ADD enters EX, LOAD at MEM → MEM forwarding supplies result
    //
    // POP counts as a load. It writes a register from memory with exactly the
    // LOAD's latency, but the condition tested `id_mem_read`, which only
    // OP_LOAD sets -- so `POP Rn` followed by a use of Rn read the previous
    // value. And `id_dst != 0` was a zero-register assumption this ISA does
    // not have: R0 is an ordinary register here, MOVI R0, 7 puts 7 in R0.
    // Exempting it meant the one hazard pattern a context switch is built out
    // of -- pop a register, store it -- was the one pattern with no interlock.
    assign load_use_hazard = (id_mem_read || id_is_pop) &&
                             ((id_uses_s1 && (s1 == id_dst)) ||
                              (id_uses_s2 && (s2 == id_dst)));

    // ── Store-to-Load Hazard Detection ───────────────────────────
    // If the EX stage is doing a STORE, and the decoded instruction
    // is a LOAD with the same computed address, stall 1 cycle to
    // ensure the STORE commits before the LOAD reads.
    wire id_is_load_op  = (opcode == `OP_LOAD);
    // Compute the current instruction's load address (S1 + IMM)
    wire [`XLEN-1:0] id_load_addr_raw = gpr_rdata1 + {{20{imm[11]}}, imm};
    wire [`DATA_ADDR_W-1:0] id_load_addr = id_load_addr_raw[`DATA_ADDR_W-1:0];

    assign store_load_hazard = ex_mem_write && id_is_load_op &&
                               (ex_mem_addr == id_load_addr);

    // Drive register file addresses (combinational, before clock)
    assign gpr_raddr1  = {1'b0, s1};
    assign gpr_raddr2  = {1'b0, s2};
    assign hreg_raddr1 = s1;
    // CSET modifies one component and keeps the other seventeen, so it has to
    // read the register it writes. S1 is a GPR index for CSET -- the value
    // being written -- so the codex comes through the second read port, with
    // its address pointed at DST.
    assign hreg_raddr2 = (opcode == `OP_CSET) ? dst : s2;

    // ── Pipeline register + control decode ──────────────────────
    always @(posedge clk or negedge rst_n) begin
        // Async reset and synchronous flush clear the same registers, but
        // they must stay in separate branches: `flush` is not in the
        // sensitivity list, so folding it into the async-reset condition
        // makes the block un-inferrable (yosys: "Multiple edge sensitive
        // events found for this signal").
        if (!rst_n) begin
            id_opcode    <= `OP_NOP;
            id_dst       <= 4'd0;
            id_s1        <= 4'd0;
            id_s2        <= 4'd0;
            id_imm       <= 12'd0;
            id_gpr_s1    <= {`XLEN{1'b0}};
            id_gpr_s2    <= {`XLEN{1'b0}};
            id_hreg_s1   <= {`HREG_W{1'b0}};
            id_hreg_s2   <= {`HREG_W{1'b0}};
            id_pc        <= {`XLEN{1'b0}};
            id_gpr_we    <= 1'b0;
            id_hreg_we   <= 1'b0;
            id_mem_read  <= 1'b0;
            id_mem_write <= 1'b0;
            id_is_branch <= 1'b0;
            id_is_jump   <= 1'b0;
            id_is_call   <= 1'b0;
            id_is_ret    <= 1'b0;
            id_is_codex  <= 1'b0;
            id_is_halt   <= 1'b0;
            id_is_print  <= 1'b0;
            id_is_push   <= 1'b0;
            id_is_pop    <= 1'b0;
        end else if (flush) begin
            id_opcode    <= `OP_NOP;
            id_dst       <= 4'd0;
            id_s1        <= 4'd0;
            id_s2        <= 4'd0;
            id_imm       <= 12'd0;
            id_gpr_s1    <= {`XLEN{1'b0}};
            id_gpr_s2    <= {`XLEN{1'b0}};
            id_hreg_s1   <= {`HREG_W{1'b0}};
            id_hreg_s2   <= {`HREG_W{1'b0}};
            id_pc        <= {`XLEN{1'b0}};
            id_gpr_we    <= 1'b0;
            id_hreg_we   <= 1'b0;
            id_mem_read  <= 1'b0;
            id_mem_write <= 1'b0;
            id_is_branch <= 1'b0;
            id_is_jump   <= 1'b0;
            id_is_call   <= 1'b0;
            id_is_ret    <= 1'b0;
            id_is_codex  <= 1'b0;
            id_is_halt   <= 1'b0;
            id_is_print  <= 1'b0;
            id_is_push   <= 1'b0;
            id_is_pop    <= 1'b0;
        end else if (!stall) begin
            // Latch fields
            id_opcode  <= opcode;
            id_dst     <= dst;
            id_s1      <= s1;
            id_s2      <= s2;
            id_imm     <= imm;
            id_gpr_s1  <= gpr_rdata1;
            id_gpr_s2  <= gpr_rdata2;
            id_hreg_s1 <= hreg_rdata1;
            id_hreg_s2 <= hreg_rdata2;
            id_pc      <= if_pc;

            // ── Control signal decode ───────────────────────────
            // Defaults
            id_gpr_we    <= 1'b0;
            id_hreg_we   <= 1'b0;
            id_mem_read  <= 1'b0;
            id_mem_write <= 1'b0;
            id_is_branch <= 1'b0;
            id_is_jump   <= 1'b0;
            id_is_call   <= 1'b0;
            id_is_ret    <= 1'b0;
            id_is_codex  <= 1'b0;
            id_is_halt   <= 1'b0;
            id_is_print  <= 1'b0;
            id_is_push   <= 1'b0;
            id_is_pop    <= 1'b0;

            case (opcode)
                `OP_NOP:    ;  // no-op

                `OP_HALT:   id_is_halt <= 1'b1;

                // FRD writes a GPR and reads none; FWR reads S1 and writes
                // no GPR at all -- its whole result is the flag register, the
                // way CMP's is.
                `OP_FRD:    id_gpr_we <= 1'b1;
                `OP_MOV:    id_gpr_we <= 1'b1;
                `OP_MOVI:   id_gpr_we <= 1'b1;

                `OP_ADD:    id_gpr_we <= 1'b1;
                `OP_ADDI:   id_gpr_we <= 1'b1;
                `OP_SUB:    id_gpr_we <= 1'b1;
                `OP_MUL:    id_gpr_we <= 1'b1;

                `OP_AND:    id_gpr_we <= 1'b1;
                `OP_OR:     id_gpr_we <= 1'b1;
                `OP_XOR:    id_gpr_we <= 1'b1;
                `OP_NOT:    id_gpr_we <= 1'b1;
                `OP_SHL:    id_gpr_we <= 1'b1;
                `OP_SHR:    id_gpr_we <= 1'b1;
                `OP_ANDI:   id_gpr_we <= 1'b1;
                `OP_ORI:    id_gpr_we <= 1'b1;
                `OP_XORI:   id_gpr_we <= 1'b1;
                `OP_SHLI:   id_gpr_we <= 1'b1;
                `OP_SHRI:   id_gpr_we <= 1'b1;

                `OP_CMP:    ;  // Only sets flags, no reg write
                `OP_CMPI:   ;
                // FWR is the same shape as CMP: its whole result is the flag
                // register, so it needs an arm here even though it sets
                // nothing. Without one it falls to the default below and the
                // machine HALTs on it -- which is what the default is for, and
                // is how this omission was found rather than shipped.
                `OP_FWR:    ;

                `OP_CALL:   id_is_call <= 1'b1;
                `OP_RET:    id_is_ret  <= 1'b1;
            `OP_JMP:    id_is_jump <= 1'b1;
                `OP_JEQ:    id_is_branch <= 1'b1;
                `OP_JNE:    id_is_branch <= 1'b1;
                `OP_JGD:    id_is_branch <= 1'b1;
                `OP_JNGD:   id_is_branch <= 1'b1;

                `OP_PUSH:   id_is_push <= 1'b1;
                `OP_POP:    begin id_is_pop <= 1'b1; id_gpr_we <= 1'b1; end
                `OP_LOAD:   begin id_mem_read <= 1'b1; id_gpr_we <= 1'b1; end
                `OP_STORE:  begin id_mem_write <= 1'b1; end

                `OP_HLOAD:  begin id_is_codex <= 1'b1; id_hreg_we <= 1'b1; end
                `OP_HCADD:  begin id_is_codex <= 1'b1; id_hreg_we <= 1'b1; end
                `OP_HGRD:   begin id_is_codex <= 1'b1; end  // Sets GUARD flag only
                `OP_HNRM2:  begin id_is_codex <= 1'b1; id_gpr_we <= 1'b1; end
                `OP_CGET:  begin id_is_codex <= 1'b1; id_gpr_we <= 1'b1; end
                // CSET writes H[DST] and reads it too. id_s2 is overwritten
                // with DST here -- the field is unused by this instruction,
                // and the forwarding unit compares ex_dst/mem_dst against
                // id_s2, so without it a CSET straight after a write to the
                // same H-Reg would modify the stale copy. Same shape as the
                // letter path below, which overwrites id_dst for the same
                // kind of reason.
                `OP_CSET:  begin
                    id_is_codex <= 1'b1;
                    id_hreg_we  <= 1'b1;
                    id_s2       <= dst;
                end
                // CMOV and CZERO write a whole codex; CZERO reads nothing at
                // all, which is why it is absent from both usage lists above.
                // Zero is the monoid's identity and passes every guard --
                // three sum-checks of 0 = 0, rho = 0, and T1/T2 vacuous -- so
                // it is a legitimate starting point for building a vector with
                // CSET, not merely an erase.
                `OP_CMOV:  begin id_is_codex <= 1'b1; id_hreg_we <= 1'b1; end
                `OP_CZERO: begin id_is_codex <= 1'b1; id_hreg_we <= 1'b1; end
                // CEQ writes no register: its whole result is the Z flag.
                `OP_CEQ:   begin id_is_codex <= 1'b1; end
                `OP_CRHO:  begin id_is_codex <= 1'b1; id_gpr_we <= 1'b1; end
                `OP_CU:    begin id_is_codex <= 1'b1; id_gpr_we <= 1'b1; end
                `OP_CMOD4: begin id_is_codex <= 1'b1; id_gpr_we <= 1'b1; end
                `OP_HDIST:  begin id_is_codex <= 1'b1; id_gpr_we <= 1'b1; end

                `OP_HPACK:  begin id_is_codex <= 1'b1; id_gpr_we <= 1'b1; end  // HISAB nibble-pack
                `OP_HCRC:   begin id_is_codex <= 1'b1; id_gpr_we <= 1'b1; end  // HISAB CRC32

                `OP_PRINT:  id_is_print <= 1'b1;

                // ERET sets nothing up here -- the redirect and the privilege
                // change are both resolved in Execute. But it MUST appear in
                // this case, because `default` means HALT_ERR: without it the
                // one instruction that returns from a trap also stopped the
                // machine, and it did, for several commits. Nothing caught it
                // because tb_hcpu_trap exercises the unit without a decoder
                // and the interpreter has no decode table at all -- ERET had
                // never run through the actual pipeline.
                `OP_ERET:   ;

                // SYSCALL likewise sets nothing up: the trap it raises is
                // resolved in Execute. But it MUST be here, because default
                // is HALT_ERR -- the same trap OP_ERET fell into.
                `OP_SYSCALL: ;

                default: begin
                    if (opcode >= `LETTER_OP_FIRST && opcode <= `LETTER_OP_LAST) begin
                        // A letter instruction. The ROM index is the opcode's
                        // own offset, the destination is H-Reg 0 because there
                        // is nothing to choose, and both source fields are
                        // already zero -- so id_hreg_s1 reads H0 without
                        // anything having to say so.
                        id_is_codex  <= 1'b1;
                        id_hreg_we   <= 1'b1;
                        id_dst       <= 4'd0;
                    end else begin
                    id_is_halt <= 1'b1;  // Unimplemented → HALT_ERR
                    id_dst     <= 4'hE;  // Arbitrary error code mark
                    id_gpr_we  <= 1'b0;
                    id_hreg_we <= 1'b0;
                    id_mem_write <= 1'b0;
                    end
                end
            endcase
        end
        // If stall: hold all outputs unchanged
    end

endmodule
