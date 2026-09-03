// ============================================================================
// HCPU Execute Stage — hcpu_execute.v
// Scalar ALU, codex ALU, guard checker, branch resolution
// (c) 2026 HMCL — HM-28-v1.2-HC18D
// ============================================================================

`include "hcpu_pkg.vh"

module hcpu_execute #(
    parameter USE_DSP = 1   // 1 = FPGA (DSP48), 0 = ASIC (shift-add)
)(
    input  wire                    clk,
    input  wire                    rst_n,

    // ── Pipeline control ────────────────────────────────────────
    input  wire                    stall,
    input  wire                    flush,

    // ── Input from Decode ───────────────────────────────────────
    input  wire [7:0]              id_opcode,
    input  wire [3:0]              id_dst,
    input  wire [3:0]              id_s1,
    input  wire [3:0]              id_s2,
    input  wire [11:0]             id_imm,
    input  wire [`XLEN-1:0]        id_gpr_s1,
    input  wire [`XLEN-1:0]        id_gpr_s2,
    input  wire [`HREG_W-1:0]      id_hreg_s1,
    input  wire [`HREG_W-1:0]      id_hreg_s2,
    input  wire [`XLEN-1:0]        id_pc,
    input  wire                    id_gpr_we,
    input  wire                    id_hreg_we,
    input  wire                    id_is_branch,
    input  wire                    id_is_jump,
    input  wire                    id_is_call,
    input  wire                    id_is_ret,
    input  wire                    id_is_codex,
    input  wire                    id_is_halt,
    input  wire                    id_is_print,
    input  wire                    id_is_push,
    input  wire                    id_is_pop,
    input  wire [7:0]              current_flags,

    // ── Master Table ROM ────────────────────────────────────────
    output wire [`ROM_ADDR_W-1:0]  rom_addr,
    input  wire [`HREG_W-1:0]      rom_data,
    input  wire                    rom_valid,

    // ── Guard checker interface ─────────────────────────────────
    output wire [`HREG_W-1:0]      guard_vec,
    input  wire                    guard_pass,

    // ── Codex ALU interface ─────────────────────────────────────
    output wire [2:0]              calu_op,
    output wire [11:0]             calu_index,
    output wire [`HREG_W-1:0]      calu_src1,
    output wire [`HREG_W-1:0]      calu_src2,
    input  wire [`HREG_W-1:0]      calu_result_vec,
    input  wire [`XLEN-1:0]        calu_result_scl,

    // ── HISAB serializer interface ───────────────────────────
    input  wire [`XLEN-1:0]        hisab_pack0,
    input  wire [`XLEN-1:0]        hisab_pack1,
    input  wire [`XLEN-1:0]        hisab_pack2,
    input  wire [`XLEN-1:0]        hisab_crc,

    // ── Output to Memory/Writeback ──────────────────────────────
    output reg  [7:0]              ex_opcode,
    output reg  [3:0]              ex_dst,
    output reg  [`XLEN-1:0]        ex_gpr_result,
    output reg  [`HREG_W-1:0]      ex_hreg_result,
    output reg                     ex_gpr_we,
    output reg                     ex_hreg_we,
    output reg  [7:0]              ex_flags_new,
    output reg                     ex_flags_we,
    output reg                     ex_is_halt,
    output reg                     ex_is_print,
    output reg  [`XLEN-1:0]        ex_print_data,
    output reg                     ex_is_push,
    output reg                     ex_is_pop,
    output reg  [`XLEN-1:0]        ex_push_data,

    // ── Branch output to Fetch ──────────────────────────────────
    output reg                     branch_taken,
    output reg  [`XLEN-1:0]        branch_target,

    // ERET redirects the fetch exactly the way a branch does, so it is
    // resolved here with the branches. A flush sets id_opcode to NOP, so this
    // cannot fire on a bubble. Like branch_taken it is held while the stage
    // is stalled, which is harmless: both redirects are idempotent.
    output wire                    is_eret,

    // ── Privilege ───────────────────────────────────────────────
    // The fault is raised HERE, not in the peripheral decoder, for one
    // reason: this is the last stage that still knows the PC. A fault
    // detected in Memory would have no instruction to point at, and an
    // exception that cannot name where it happened is not much of an
    // exception. Detecting it here also means the access never leaves the
    // stage -- it is suppressed rather than performed and undone.
    input  wire                    in_user,
    output wire                    priv_fault,

    // The protection window, checked here for the same reason the privilege
    // check is here: this is the last stage that still knows the PC.
    input  wire [`DATA_ADDR_W-1:0] mem_base,
    input  wire [`DATA_ADDR_W-1:0] mem_limit,
    output wire                    mem_fault,

    // SYSCALL is the one boundary crossing user mode may make. It is not a
    // fault, so it is not gated on in_user: a supervisor may call itself.
    output wire                    is_syscall,

    // ── Data RAM control (passed through to memory stage) ──────
    input  wire                    id_mem_read,
    input  wire                    id_mem_write,
    output reg                     ex_mem_read,
    output reg                     ex_mem_write,
    output reg  [`DATA_ADDR_W-1:0] ex_mem_addr,    // Computed address
    output reg  [`XLEN-1:0]        ex_mem_wdata    // Data to write
);

    // ── Sign-extend immediate (for branches, ADDI) ──────────────
    wire [`XLEN-1:0] imm_sext = {{20{id_imm[11]}}, id_imm};
    wire [`XLEN-1:0] imm_zext = {{20{1'b0}}, id_imm};

    // ── Scalar ALU ──────────────────────────────────────────────
    reg [`XLEN-1:0] alu_result;
    reg [7:0]       alu_flags;
    reg             alu_flags_we;

    // ── MUL: configurable multiplier (FPGA DSP or ASIC shift-add) ──
    wire [`XLEN-1:0] mul_result;
    hcpu_mul #(.USE_DSP(USE_DSP)) u_mul (
        .a      (id_gpr_s1),
        .b      (id_gpr_s2),
        .result (mul_result)
    );

    always @(*) begin
        alu_result   = {`XLEN{1'b0}};
        alu_flags    = current_flags;
        alu_flags_we = 1'b0;

        case (id_opcode)
            `OP_MOV:  alu_result = id_gpr_s1;
            `OP_MOVI: alu_result = imm_zext;
            `OP_ADD:  alu_result = id_gpr_s1 + id_gpr_s2;
            `OP_ADDI: alu_result = id_gpr_s1 + imm_sext;
            `OP_SUB:  alu_result = id_gpr_s1 - id_gpr_s2;
            `OP_MUL:  alu_result = mul_result;

            // Bitwise and shift. Shift amounts take the low five bits only:
            // a shift of 32 or more has no natural answer on a 32-bit
            // machine, and leaving it undefined lets this pipeline and the
            // interpreter disagree about the same program. Logical
            // immediates are zero-extended -- ANDI must mask, and a
            // sign-extended mask is not a mask.
            `OP_AND:  alu_result = id_gpr_s1 & id_gpr_s2;
            `OP_OR:   alu_result = id_gpr_s1 | id_gpr_s2;
            `OP_XOR:  alu_result = id_gpr_s1 ^ id_gpr_s2;
            `OP_NOT:  alu_result = ~id_gpr_s1;
            `OP_SHL:  alu_result = id_gpr_s1 << id_gpr_s2[4:0];
            `OP_SHR:  alu_result = id_gpr_s1 >> id_gpr_s2[4:0];
            `OP_ANDI: alu_result = id_gpr_s1 & imm_zext;
            `OP_ORI:  alu_result = id_gpr_s1 | imm_zext;
            `OP_XORI: alu_result = id_gpr_s1 ^ imm_zext;
            `OP_SHLI: alu_result = id_gpr_s1 << imm_zext[4:0];
            `OP_SHRI: alu_result = id_gpr_s1 >> imm_zext[4:0];
            `OP_CMP, `OP_CMPI: begin
                alu_flags_we = 1'b1;
                // Compute S1 - S2/IMM for flag setting
                if (id_opcode == `OP_CMPI)
                    alu_result = id_gpr_s1 - imm_sext;
                else
                    alu_result = id_gpr_s1 - id_gpr_s2;
                // Set flags
                alu_flags[`FLAG_Z]  = (alu_result == 0);
                alu_flags[`FLAG_LT] = alu_result[`XLEN-1];  // Sign bit
            end
            default: alu_result = {`XLEN{1'b0}};
        endcase
    end

    // ── Codex operation routing ─────────────────────────────────
    // A letter instruction names its ROM entry with its own opcode. The ROM
    // is 1-indexed by letter, so the offset gets one added to it.
    wire is_letter = (id_opcode >= `LETTER_OP_FIRST) &&
                     (id_opcode <= `LETTER_OP_LAST);
    wire [`ROM_ADDR_W-1:0] letter_index =
        (id_opcode - `LETTER_OP_FIRST) + 1'b1;
    assign rom_addr  = is_letter ? letter_index : id_imm[`ROM_ADDR_W-1:0];
    assign guard_vec = id_hreg_s1;

    // Codex ALU operation select
    assign calu_op   = (id_opcode == `OP_HCADD || is_letter) ? 3'd0 :
                       (id_opcode == `OP_HNRM2) ? 3'd1 :
                       (id_opcode == `OP_HDIST) ? 3'd2 :
                       (id_opcode == `OP_CGET) ? 3'd3 : 3'd0;
    // CGET names its component in the immediate.
    assign calu_index = id_imm;
    assign calu_src1 = id_hreg_s1;
    // The letter itself is the second operand, straight off the ROM. This is
    // the one new path the instruction needed: everything else -- the adder,
    // the H-Reg write, the accumulator -- was already here.
    assign calu_src2 = is_letter ? rom_data : id_hreg_s2;

    // Codex result mux
    reg [`HREG_W-1:0] codex_hvec;
    reg [`XLEN-1:0]   codex_gpr;

    always @(*) begin
        codex_hvec = {`HREG_W{1'b0}};
        codex_gpr  = {`XLEN{1'b0}};
        case (id_opcode)
            `OP_HLOAD: codex_hvec = rom_data;
            `OP_HCADD: codex_hvec = calu_result_vec;
            `OP_HNRM2: codex_gpr  = calu_result_scl;
            `OP_HDIST: codex_gpr  = calu_result_scl;
            `OP_CGET: codex_gpr  = calu_result_scl;
            // HISAB word select. §IIIM.3.1 gives HPACK as
            // GPR[DST] <- nibble_pack(H[S1])[S2], words 0-2. Only word 0 was
            // ever selected: pack_word1 and pack_word2 were wired up to the
            // top level and never read, so the processor could emit the first
            // four bytes of a nine-byte frame and no more. A word past 2
            // names nothing and yields zero, as CGET does.
            `OP_HPACK: codex_gpr  = (id_s2 == 4'd0) ? hisab_pack0 :
                                    (id_s2 == 4'd1) ? hisab_pack1 :
                                    (id_s2 == 4'd2) ? hisab_pack2 :
                                                      {`XLEN{1'b0}};
            `OP_HCRC:  codex_gpr  = hisab_crc;    // HISAB: CRC32 digest
            // The letters land here, and this is the ONLY default. There used
            // to be a second one in the middle of the case carrying this line,
            // which Verilog does not allow and which no simulator resolves the
            // same way: iverilog took the trailing `default: ;`, so every one
            // of the twenty-eight letter opcodes wrote nothing. The Python
            // machine has no case statement and computed the right answer, and
            // RTL_IMPLEMENTED said the opcodes were done because it is a
            // declaration rather than a measurement -- so nothing disagreed.
            // ||Ba+Sin+Mim||^2 is 112 through HLOAD/HCADD and was 0 through
            // the letters.
            default:   if (is_letter) codex_hvec = calu_result_vec;
        endcase
    end

    // ── Flags forwarding ────────────────────────────────────────
    // Forward flags from the instruction currently being computed
    // in EX (combinational), or from the EX pipeline register
    // (previous instruction), or from the register file.
    wire [7:0] forwarded_flags;
    assign forwarded_flags = (alu_flags_we)  ? alu_flags     :  // CMP in EX now
                             (ex_flags_we)   ? ex_flags_new  :  // CMP just left EX
                             current_flags;                      // Register file

    wire eret_decoded = (id_opcode == `OP_ERET);
    assign is_syscall = (id_opcode == `OP_SYSCALL);

    // The address this instruction would touch, computed the same way the
    // pipeline register below computes it. One truth would be better, but the
    // register is clocked and this has to be combinational.
    wire [`DATA_ADDR_W-1:0] would_addr =
        (id_mem_write ? (id_gpr_s2 + imm_sext) : (id_gpr_s1 + imm_sext))
        & {`DATA_ADDR_W{1'b1}};

    // Privileged acts: touching the peripheral window, returning from a trap,
    // HALT, and PRINT.
    //
    // PRINT was not on this list, and that was a hole rather than a gap. It is
    // the machine's only output path, so user mode could write to the serial
    // line with nothing between it and the wire -- two processes printing
    // interleave their characters and no one arbitrates. "User mode cannot do
    // I/O" was never true here; what was true is that its I/O was unmediated,
    // which is worse. It goes through the kernel now, by SYSCALL.
    wire touches_window = (id_mem_read | id_mem_write)
                          && (would_addr >= `PERIPH_BASE);
    assign priv_fault = in_user && (touches_window || eret_decoded || id_is_halt
                                    || id_is_print);

    // Ordinary RAM is open to user mode -- the boundary is the window, not
    // memory -- but only inside [base, limit). A peripheral address is
    // already refused by priv_fault, so it is excluded here rather than
    // reported twice.
    assign mem_fault = in_user && (id_mem_read | id_mem_write)
                       && !touches_window
                       && ((would_addr < mem_base) || (would_addr >= mem_limit));

    // A faulting ERET must not also return. Without this the one instruction
    // that changes privilege would still change it while reporting that it
    // was not allowed to -- user code would escape by executing an ERET and
    // letting the fault it raised be handled afterwards.
    assign is_eret = eret_decoded && !in_user;

    // ── Return-address stack ────────────────────────────────────
    // Its own array, read combinationally, so RET has its target while it is
    // still here and resolves exactly like a branch. See hcpu_pkg.vh for why
    // it is not the PUSH/POP stack.
    reg  [`CODE_ADDR_W-1:0] ra_stack [0:`RA_DEPTH-1];
    reg  [`RA_PTR_W-1:0]    ra_sp;
    wire [`CODE_ADDR_W-1:0] ra_top = ra_stack[ra_sp - 1'b1];

    // [HC-04] return stack overflow, [HC-05] underflow. The book's HCHECK
    // codes stop at HC-03; these two are additions of the same class, and
    // they halt the way HC-01..HC-03 do rather than jumping somewhere
    // arbitrary -- a RET with nothing to return to has no correct target, and
    // inventing one is how a fault becomes a wild branch.
    wire ra_overflow  = id_is_call && (ra_sp >= `RA_DEPTH);
    wire ra_underflow = id_is_ret  && (ra_sp == {`RA_PTR_W{1'b0}});
    wire ra_fault     = ra_overflow || ra_underflow;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            ra_sp <= {`RA_PTR_W{1'b0}};
        else if (!stall && !ra_fault) begin
            if (id_is_call) ra_sp <= ra_sp + 1'b1;
            if (id_is_ret)  ra_sp <= ra_sp - 1'b1;
        end
    end

    // Clock-only, like the data stack and for the same reason: an array
    // touched inside an async-reset block cannot map to a memory primitive.
    always @(posedge clk)
        if (!stall && id_is_call && !ra_overflow)
            ra_stack[ra_sp] <= id_pc[`CODE_ADDR_W-1:0] + 1'b1;

    // ── Branch resolution ───────────────────────────────────────
    always @(*) begin
        branch_taken  = 1'b0;
        branch_target = {`XLEN{1'b0}};

        if (id_is_jump) begin
            branch_taken  = 1'b1;
            branch_target = imm_zext;  // Absolute jump
        end else if (id_is_call && !ra_overflow) begin
            branch_taken  = 1'b1;
            branch_target = imm_zext;  // Absolute, like JMP
        end else if (id_is_ret && !ra_underflow) begin
            branch_taken  = 1'b1;
            branch_target = {{(`XLEN-`CODE_ADDR_W){1'b0}}, ra_top};
        end else if (id_is_branch) begin
            case (id_opcode)
                `OP_JEQ:  branch_taken = forwarded_flags[`FLAG_Z];
                `OP_JNE:  branch_taken = ~forwarded_flags[`FLAG_Z];
                `OP_JGD:  branch_taken = forwarded_flags[`FLAG_G];
                `OP_JNGD: branch_taken = ~forwarded_flags[`FLAG_G];
                default:  branch_taken = 1'b0;
            endcase
            branch_target = id_pc + imm_sext;  // Relative branch
        end
    end

    // ── Pipeline register to Memory/Writeback ───────────────────
    always @(posedge clk or negedge rst_n) begin
        // Async reset and synchronous flush clear the same registers, but
        // they must stay in separate branches: `flush` is not in the
        // sensitivity list, so folding it into the async-reset condition
        // makes the block un-inferrable (yosys: "Multiple edge sensitive
        // events found for this signal").
        if (!rst_n) begin
            ex_opcode      <= `OP_NOP;
            ex_dst         <= 4'd0;
            ex_gpr_result  <= {`XLEN{1'b0}};
            ex_hreg_result <= {`HREG_W{1'b0}};
            ex_gpr_we      <= 1'b0;
            ex_hreg_we     <= 1'b0;
            ex_flags_new   <= 8'h00;
            ex_flags_we    <= 1'b0;
            ex_is_halt     <= 1'b0;
            ex_is_print    <= 1'b0;
            ex_print_data  <= {`XLEN{1'b0}};
            ex_is_push     <= 1'b0;
            ex_is_pop      <= 1'b0;
            ex_push_data   <= {`XLEN{1'b0}};
            ex_mem_read    <= 1'b0;
            ex_mem_write   <= 1'b0;
            ex_mem_addr    <= {`DATA_ADDR_W{1'b0}};
            ex_mem_wdata   <= {`XLEN{1'b0}};
        end else if (flush) begin
            ex_opcode      <= `OP_NOP;
            ex_dst         <= 4'd0;
            ex_gpr_result  <= {`XLEN{1'b0}};
            ex_hreg_result <= {`HREG_W{1'b0}};
            ex_gpr_we      <= 1'b0;
            ex_hreg_we     <= 1'b0;
            ex_flags_new   <= 8'h00;
            ex_flags_we    <= 1'b0;
            ex_is_halt     <= 1'b0;
            ex_is_print    <= 1'b0;
            ex_print_data  <= {`XLEN{1'b0}};
            ex_is_push     <= 1'b0;
            ex_is_pop      <= 1'b0;
            ex_push_data   <= {`XLEN{1'b0}};
            ex_mem_read    <= 1'b0;
            ex_mem_write   <= 1'b0;
            ex_mem_addr    <= {`DATA_ADDR_W{1'b0}};
            ex_mem_wdata   <= {`XLEN{1'b0}};
        end else if (!stall) begin
            ex_opcode   <= id_opcode;
            ex_dst      <= id_dst;
            ex_is_print <= id_is_print & ~priv_fault;
            ex_is_push  <= id_is_push;
            ex_is_pop   <= id_is_pop;

            // ── HCHECK: Runtime Invariant Traps ─────────────────
            // [HC-01] HLOAD with invalid ROM index → HALT_ERR
            //         ROM returns valid=0 for out-of-range indices.
            //         Suppress H-Reg write and force halt.
            if (id_is_codex && id_opcode == `OP_HLOAD && !rom_valid) begin
                ex_is_halt  <= 1'b1;   // HALT_ERR
                ex_gpr_we   <= 1'b0;   // No side effects
                ex_hreg_we  <= 1'b0;
                ex_mem_write <= 1'b0;
            end else begin
                ex_is_halt  <= (id_is_halt & ~priv_fault) | ra_fault;
            end

            // GPR result selection
            if (id_is_codex && (id_opcode == `OP_HNRM2 || id_opcode == `OP_HDIST ||
                                id_opcode == `OP_CGET ||
                                id_opcode == `OP_HPACK || id_opcode == `OP_HCRC))
                ex_gpr_result <= codex_gpr;
            else if (id_is_pop)
                ex_gpr_result <= {`XLEN{1'b0}};  // Filled by memory stage
            else
                ex_gpr_result <= alu_result;

            // H-Reg result
            ex_hreg_result <= codex_hvec;

            // Write enables
            ex_gpr_we  <= id_gpr_we;
            ex_hreg_we <= id_hreg_we;

            // Flags
            if (id_opcode == `OP_HGRD) begin
                // Guard check — update GUARD flag
                ex_flags_new <= {current_flags[7:1], guard_pass};
                ex_flags_we  <= 1'b1;
            end else if (alu_flags_we) begin
                ex_flags_new <= alu_flags;
                ex_flags_we  <= 1'b1;
            end else begin
                ex_flags_new <= current_flags;
                ex_flags_we  <= 1'b0;
            end

            // Print data (GPR[S1] value)
            ex_print_data <= id_gpr_s1;

            // Push data (GPR[S1] value)
            ex_push_data <= id_gpr_s1;

            // Data RAM LOAD/STORE
            // A faulting access is not performed. The trap fires in the same
            // cycle, so letting the write through and undoing it later would
            // mean a peripheral had already seen it.
            ex_mem_read  <= id_mem_read  & ~priv_fault & ~mem_fault;
            ex_mem_write <= id_mem_write & ~priv_fault & ~mem_fault;
            // LOAD: addr = GPR[S1] + IMM  (DST <- MEM[S1+IMM])
            // STORE: addr = GPR[S2] + IMM  (MEM[S2+IMM] <- GPR[S1])
            if (id_mem_write)
                ex_mem_addr <= (id_gpr_s2 + imm_sext) & {{(`XLEN-`DATA_ADDR_W){1'b0}}, {`DATA_ADDR_W{1'b1}}};
            else
                ex_mem_addr <= (id_gpr_s1 + imm_sext) & {{(`XLEN-`DATA_ADDR_W){1'b0}}, {`DATA_ADDR_W{1'b1}}};
            ex_mem_wdata <= id_gpr_s1;  // STORE writes GPR[S1]
        end
    end

endmodule
