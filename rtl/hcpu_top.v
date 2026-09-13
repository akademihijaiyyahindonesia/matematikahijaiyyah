// ============================================================================
// HCPU Top-Level — hcpu_top.v
// Hijaiyyah Core Processing Unit — 5-stage pipeline with forwarding
// (c) 2026 Maulana Amratulloh — HM-28-v1.2-HC18D / Tier 1.5
// ============================================================================
//
// Architecture: Fetch → Decode → Execute → Memory → Writeback
// Forwarding: EX→ID, MEM→ID (GPR + H-Reg bypass)
// Stall: PRINT blocking
// Flush: Taken branch (1-cycle penalty)
//
// External interfaces:
//   - imem_*: Instruction memory (synchronous ROM)
//   - uart_tx: UART transmit pin
//   - halted: Processor halted indicator
//   - guard_led: GUARD flag indicator
//

`include "hcpu_pkg.vh"

module hcpu_top #(
    parameter CLK_HZ  = `SYS_CLK_HZ,
    parameter BAUD    = `UART_BAUD,
    parameter USE_DSP = 1  // 1 = FPGA (DSP48), 0 = ASIC (shift-add)
)(
    input  wire        clk,
    input  wire        rst_n,

    // ── Instruction memory interface ────────────────────────────
    output wire [`CODE_ADDR_W-1:0] imem_addr,
    output wire                    imem_ce,       // BRAM clock-enable
    input  wire [`ILEN-1:0]        imem_data,

    // ── Instruction memory write port ───────────────────────────
    // Harvard is kept for execution: fetch keeps its own read-only port above.
    // This is the privileged path a loader uses, and the reason the board
    // stops being a fixed-function device. It is reachable only through the
    // peripheral window, so user mode cannot touch it.
    output wire                    imem_we,
    output wire [`CODE_ADDR_W-1:0] imem_waddr,
    output wire [`ILEN-1:0]        imem_wdata,

    // ── External I/O ────────────────────────────────────────────
    // `uart_rx` idles high, and every existing instantiation leaves it
    // unconnected — an unconnected input reads as z, which the receiver's
    // synchroniser would latch as x and never leave IDLE. It is pulled up
    // internally instead, so a wrapper that does not drive it behaves exactly
    // as it did before this port existed.
    input  wire        uart_rx,
    output wire        uart_tx,
    output wire        halted,
    output wire        guard_led,     // Current GUARD flag state

    // ── Debug / Wishbone GPR read-back ──────────────────────────
    input  wire [4:0]  dbg_gpr_raddr,
    output wire [`XLEN-1:0] dbg_gpr_rdata,
    output wire [7:0]  dbg_flags
);

    // ════════════════════════════════════════════════════════════
    //  Internal wires
    // ════════════════════════════════════════════════════════════

    // Pipeline control
    wire pc_stall, id_stall, ex_stall;
    wire if_flush, id_flush;
    wire load_use_hazard, store_load_hazard;
    wire branch_taken_w;
    wire [`XLEN-1:0] branch_target_w;

    // ── Trap redirect ───────────────────────────────────────────
    // A trap is a branch the program did not write, so it joins the same
    // redirect path and gets the same flush. It takes priority for FETCHING:
    // whatever a branch decided this cycle is discarded in favour of the trap
    // vector. That part is fine, and always was.
    //
    // What the priority does NOT do, and what the comment here used to claim
    // it did ("a branch that loses to a trap is re-fetched from epc on
    // return"), is preserve the branch's OWN effect for the return address.
    // A maskable interrupt's epc was simply `if_pc` -- Fetch's own PC, which
    // is a SPECULATIVE sequential PC+1, one stage ahead of Execute. A branch
    // resolves IN Execute, so at the exact cycle a trap and a taken branch
    // coincide, `if_pc` already shows the branch's FALL-THROUGH address, not
    // its target -- Execute has not corrected Fetch's guess yet, and the trap
    // fires before it gets the chance to. On return, execution resumed as if
    // the branch had NOT been taken, even though it was, and even though a
    // CALL's return-address-stack push (a real side effect, gated on nothing
    // but `id_is_call`) had ALREADY committed that same cycle regardless.
    // Found through the guard daemon in kernel.hasm -- a JGD that had just
    // passed its guard resumed on the "guard failed" path, once in 400,000
    // cycles -- and reproduced on demand in
    // tb_hcpu_branch_trap_race.v, sweeping a timer deadline against a fixed
    // JMP until it lands on Execute's cycle rather than relying on that kind
    // of luck.
    //
    // The fix: when Execute is ALSO resolving a taken branch this cycle, the
    // "next instruction that has not happened yet" is not Fetch's stale
    // guess -- it is the branch's OWN target, because the branch's effect is
    // already final. Re-fetching the branch instruction itself (what the old
    // comment described) was considered and rejected: that would mean
    // re-reading FLAGS on resume, which are not part of a saved context
    // (rtl/programs/kernel.hasm's own header lists what is not saved), so a
    // handler's own comparisons could silently change the branch's outcome
    // between the first attempt and the replay. Resuming at the target
    // instead depends on nothing but what already committed.
    wire trap_redirect_w, trap_in_trap_w, trap_is_eret_w;
    wire trap_in_user_w, trap_priv_fault_w, trap_mem_fault_w, trap_syscall_w;
    wire [`DATA_ADDR_W-1:0] mem_base_w, mem_limit_w;
    wire [`XLEN-1:0] trap_target_w;
    wire trap_reg_we_w, trap_src_timer_w, trap_src_rx_w;
    wire [3:0] trap_reg_sel_w;
    wire [`XLEN-1:0] trap_reg_wdata_w, trap_reg_rdata_w;

    wire redirect_taken  = trap_redirect_w | branch_taken_w;
    wire [`XLEN-1:0] redirect_target =
        trap_redirect_w ? trap_target_w : branch_target_w;


    // Fetch → Decode
    wire [`ILEN-1:0] if_instruction;
    wire [`XLEN-1:0] if_pc;
    wire if_pc_valid;

    // Decode → Execute
    wire [7:0]  id_opcode;
    wire [3:0]  id_dst, id_s1, id_s2;
    wire [11:0] id_imm;
    wire [`XLEN-1:0]  id_gpr_s1, id_gpr_s2;
    wire [`HREG_W-1:0] id_hreg_s1, id_hreg_s2;
    wire [`XLEN-1:0]  id_pc;
    wire id_gpr_we, id_hreg_we, id_mem_read, id_mem_write;
    wire id_is_branch, id_is_jump, id_is_codex;
    wire id_is_call, id_is_ret;
    wire id_is_halt, id_is_print, id_is_push, id_is_pop;
    wire id_is_emits;

    // Forwarded values (from forwarding unit)
    wire [`XLEN-1:0]   fwd_gpr_s1, fwd_gpr_s2;
    wire [`HREG_W-1:0] fwd_hreg_s1, fwd_hreg_s2;

    // HISAB serializer outputs
    wire [`XLEN-1:0] hisab_pack0, hisab_pack1, hisab_pack2, hisab_crc;
    wire [7:0]       hisab_guard_status;

    // Execute → Memory
    wire [7:0]  ex_opcode;
    wire [3:0]  ex_dst;
    wire [`XLEN-1:0]   ex_gpr_result;
    wire [`HREG_W-1:0] ex_hreg_result;
    wire ex_gpr_we, ex_hreg_we;
    wire [7:0] ex_flags_new;
    wire ex_flags_we, ex_is_halt, ex_is_print;
    wire [`XLEN-1:0] ex_print_data;
    wire ex_is_emits;
    wire [`DATA_ADDR_W-1:0] ex_emits_addr;
    wire ex_is_push, ex_is_pop;
    wire [`XLEN-1:0] ex_push_data;
    wire ex_mem_read, ex_mem_write;
    wire [`DATA_ADDR_W-1:0] ex_mem_addr;
    wire [`XLEN-1:0] ex_mem_wdata;

    // Memory → Writeback
    wire [3:0]  mem_dst;
    wire [`XLEN-1:0]   mem_gpr_result;
    wire [`HREG_W-1:0] mem_hreg_result;
    wire mem_gpr_we, mem_hreg_we;
    wire [7:0] mem_flags_new;
    wire mem_flags_we, mem_is_halt;

    // Writeback → Register file
    wire wb_gpr_we, wb_hreg_we, wb_flags_we, wb_halt;
    wire [4:0]  wb_gpr_waddr;
    wire [`XLEN-1:0]  wb_gpr_wdata;
    wire [3:0]  wb_hreg_waddr;
    wire [`HREG_W-1:0] wb_hreg_wdata;
    wire [7:0]  wb_flags;

    // Register file read wires
    wire [4:0]  gpr_raddr1, gpr_raddr2;
    wire [`XLEN-1:0]  gpr_rdata1, gpr_rdata2;
    wire [3:0]  hreg_raddr1, hreg_raddr2;
    wire [`HREG_W-1:0] hreg_rdata1, hreg_rdata2;
    wire [7:0]  flags_out;
    wire [`XLEN-1:0] pc_out;

    // ROM
    wire [`ROM_ADDR_W-1:0] rom_addr;
    wire [`HREG_W-1:0]     rom_data;
    wire                   rom_valid;

    // Guard
    wire [`HREG_W-1:0] guard_vec;
    wire guard_pass, g1, g2, g3, g4, t1, t2;
    // U and rho come out of the guard as values, so CU and CRHO read the one
    // definition the guard already holds instead of a second copy (R1).
    wire [`XLEN-1:0] guard_u, guard_rho;

    // Codex ALU
    wire [2:0]  calu_op;
    wire [11:0] calu_index;
    wire [`HREG_W-1:0] calu_src1, calu_src2;
    wire [`XLEN-1:0]   calu_scl;
    wire [`HREG_W-1:0] calu_result_vec;
    wire [`XLEN-1:0]   calu_result_scl;
    wire               calu_done;

    // UART
    wire uart_busy;
    reg  uart_start;
    reg  [7:0] uart_data;

    // Data RAM
    wire                    dram_re;
    wire                    dram_we;
    wire [`DATA_ADDR_W-1:0] dram_addr;
    wire [`XLEN-1:0]        dram_wdata;
    wire [`XLEN-1:0]        dram_rdata;

    // Declared here rather than beside hcpu_mmio's instantiation, which is
    // where they used to sit: the EMITS state machine above reads `ram_rdata`,
    // and Verilog wants a wire declared before it is used.
    wire                    ram_re;
    wire                    ram_we;
    wire [`DATA_ADDR_W-1:0] ram_addr;
    wire [`XLEN-1:0]        ram_wdata;
    wire [`XLEN-1:0]        ram_rdata;

    // ════════════════════════════════════════════════════════════
    //  UART TX — print handling
    // ════════════════════════════════════════════════════════════

    // Simple byte-by-byte decimal print FSM
    reg [2:0] print_state;
    reg [`XLEN-1:0] print_val;
    reg [3:0] digit_cnt;
    reg [7:0] digits [0:9];
    reg [3:0] digit_idx;
    reg       print_active;

    // ── Decimal conversion for PRINT ────────────────────────────
    // Left as `/ 10` and `% 10` deliberately. A hand-written shift-add
    // reciprocal was tried here and measured worse on both counts under
    // synth_gowin: 10,836 LUTs against 8,871, and a longest topological path
    // of 1,149 against 927. Yosys already lowers division by a constant into
    // a better circuit than the textbook trick, so the obvious optimisation
    // is a pessimisation. Re-measure before changing this.

    localparam P_IDLE   = 3'd0;
    localparam P_CONV   = 3'd1;
    localparam P_SEND   = 3'd2;
    localparam P_WAIT   = 3'd3;
    localparam P_NEWLN  = 3'd4;

    // ── EMITS: the character path ───────────────────────────────
    // Three more states on the SAME state machine, driving the SAME
    // transmitter. hcpu_mmio.v refuses a second driver on this port -- "a
    // second driver on the same port is a bus conflict rather than a feature"
    // -- and that refusal is respected here: nothing new reaches
    // hcpu_uart_tx, the machine that already did just learned another source.
    //
    // One ASCII byte per 32-bit word, a zero word ends it, and the address is
    // a WORD address so the next character is at addr + 1 (§13.1.1). The read
    // is registered, so S_ADDR presents the address and S_CHAR reads it back
    // the cycle after -- the same one-cycle shape LOAD has.
    localparam P_S_ADDR = 3'd5;
    localparam P_S_CHAR = 3'd6;
    localparam P_S_WAIT = 3'd7;

    reg [`DATA_ADDR_W-1:0] str_addr;
    reg                    emits_busy;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            print_state <= P_IDLE;
            uart_start  <= 1'b0;
            uart_data   <= 8'h00;
            print_active <= 1'b0;
            digit_cnt   <= 4'd0;
            digit_idx   <= 4'd0;
            print_val   <= 0;
            str_addr    <= {`DATA_ADDR_W{1'b0}};
            emits_busy  <= 1'b0;
        end else begin
            uart_start <= 1'b0;

            case (print_state)
                P_IDLE: begin
                    print_active <= 1'b0;
                    emits_busy   <= 1'b0;
                    if (ex_is_print && !ex_stall) begin
                        print_val    <= ex_print_data;
                        print_active <= 1'b1;
                        digit_cnt    <= 4'd0;
                        print_state  <= P_CONV;
                    end else if (ex_is_emits && !ex_stall) begin
                        str_addr     <= ex_emits_addr;
                        print_active <= 1'b1;   // the pipeline waits, as for PRINT
                        emits_busy   <= 1'b1;   // and the RAM port is ours
                        print_state  <= P_S_ADDR;
                    end
                end

                P_CONV: begin
                    if (print_val == 0 && digit_cnt == 0) begin
                        digits[0]   <= 8'h30;  // '0'
                        digit_cnt   <= 4'd1;
                        print_state <= P_SEND;
                        digit_idx   <= 4'd0;
                    end else if (print_val > 0) begin
                        digits[digit_cnt] <= 8'h30 + print_val % 10;
                        print_val         <= print_val / 10;
                        digit_cnt         <= digit_cnt + 1;
                    end else begin
                        digit_idx   <= digit_cnt - 1;
                        print_state <= P_SEND;
                    end
                end

                P_SEND: begin
                    if (!uart_busy) begin
                        uart_data  <= digits[digit_idx];
                        uart_start <= 1'b1;
                        print_state <= P_WAIT;
                    end
                end

                P_WAIT: begin
                    if (!uart_busy && !uart_start) begin
                        if (digit_idx == 0) begin
                            print_state <= P_NEWLN;
                        end else begin
                            digit_idx   <= digit_idx - 1;
                            print_state <= P_SEND;
                        end
                    end
                end

                P_NEWLN: begin
                    if (!uart_busy) begin
                        uart_data   <= 8'h0A;  // '\n'
                        uart_start  <= 1'b1;
                        print_state <= P_IDLE;
                    end
                end

                // ── EMITS, one word at a time ───────────────────
                P_S_ADDR: begin
                    // The address is out this cycle; the word arrives next.
                    print_state <= P_S_CHAR;
                end

                P_S_CHAR: begin
                    if (ram_rdata == {`XLEN{1'b0}}) begin
                        // The terminator. No trailing newline: PRINT adds one
                        // because it prints a number, but a string carries its
                        // own ending if it wants one -- which is what lets a
                        // prompt sit and wait on the same line.
                        print_state <= P_IDLE;
                    end else if (!uart_busy) begin
                        uart_data   <= ram_rdata[7:0];
                        uart_start  <= 1'b1;
                        print_state <= P_S_WAIT;
                    end
                end

                P_S_WAIT: begin
                    if (!uart_busy && !uart_start) begin
                        str_addr    <= str_addr + 1'b1;   // the next WORD
                        print_state <= P_S_ADDR;
                    end
                end

                default: print_state <= P_IDLE;
            endcase
        end
    end

    // ════════════════════════════════════════════════════════════
    //  Module instantiations
    // ════════════════════════════════════════════════════════════

    // ── Fetch ───────────────────────────────────────────────────
    hcpu_fetch u_fetch (
        .clk            (clk),
        .rst_n          (rst_n),
        .stall          (pc_stall),
        .flush          (if_flush),
        .branch_taken   (redirect_taken),
        .branch_target  (redirect_target),
        .imem_addr      (imem_addr),
        .imem_ce        (imem_ce),
        .imem_data      (imem_data),
        .if_instruction (if_instruction),
        .if_pc          (if_pc),
        .pc_valid       (if_pc_valid)
    );

    // ── Decode ──────────────────────────────────────────────────
    hcpu_decode u_decode (
        .clk            (clk),
        .rst_n          (rst_n),
        .stall          (id_stall),
        .flush             (id_flush),
        .ex_mem_read       (ex_mem_read),
        .ex_mem_write      (ex_mem_write),
        .ex_dst            (ex_dst),
        .ex_mem_addr       (ex_mem_addr),
        .load_use_hazard   (load_use_hazard),
        .store_load_hazard (store_load_hazard),
        .if_instruction (if_instruction),
        .if_pc          (if_pc),
        .gpr_raddr1     (gpr_raddr1),
        .gpr_raddr2     (gpr_raddr2),
        .gpr_rdata1     (gpr_rdata1),
        .gpr_rdata2     (gpr_rdata2),
        .hreg_raddr1    (hreg_raddr1),
        .hreg_raddr2    (hreg_raddr2),
        .hreg_rdata1    (hreg_rdata1),
        .hreg_rdata2    (hreg_rdata2),
        .id_opcode      (id_opcode),
        .id_dst         (id_dst),
        .id_s1          (id_s1),
        .id_s2          (id_s2),
        .id_imm         (id_imm),
        .id_gpr_s1      (id_gpr_s1),
        .id_gpr_s2      (id_gpr_s2),
        .id_hreg_s1     (id_hreg_s1),
        .id_hreg_s2     (id_hreg_s2),
        .id_pc          (id_pc),
        .id_gpr_we      (id_gpr_we),
        .id_hreg_we     (id_hreg_we),
        .id_mem_read    (id_mem_read),
        .id_mem_write   (id_mem_write),
        .id_is_branch   (id_is_branch),
        .id_is_jump     (id_is_jump),
        .id_is_call     (id_is_call),
        .id_is_ret      (id_is_ret),
        .id_is_codex    (id_is_codex),
        .id_is_halt     (id_is_halt),
        .id_is_print    (id_is_print),
        .id_is_emits    (id_is_emits),
        .id_is_push     (id_is_push),
        .id_is_pop      (id_is_pop)
    );

    // ── Forwarding Unit ─────────────────────────────────────────
    hcpu_forward u_forward (
        .id_s1          (id_s1),
        .id_s2          (id_s2),
        .rf_gpr_s1      (id_gpr_s1),
        .rf_gpr_s2      (id_gpr_s2),
        .rf_hreg_s1     (id_hreg_s1),
        .rf_hreg_s2     (id_hreg_s2),
        .ex_gpr_we      (ex_gpr_we),
        .ex_hreg_we     (ex_hreg_we),
        .ex_dst         (ex_dst),
        .ex_gpr_result  (ex_gpr_result),
        .ex_hreg_result (ex_hreg_result),
        .mem_gpr_we     (mem_gpr_we),
        .mem_hreg_we    (mem_hreg_we),
        .mem_dst        (mem_dst),
        .mem_gpr_result (mem_gpr_result),
        .mem_hreg_result(mem_hreg_result),
        .fwd_gpr_s1     (fwd_gpr_s1),
        .fwd_gpr_s2     (fwd_gpr_s2),
        .fwd_hreg_s1    (fwd_hreg_s1),
        .fwd_hreg_s2    (fwd_hreg_s2)
    );

    // ── Execute ─────────────────────────────────────────────────
    hcpu_execute #(.USE_DSP(USE_DSP)) u_execute (
        .clk            (clk),
        .rst_n          (rst_n),
        .stall          (ex_stall),
        .flush          (1'b0),
        .id_opcode      (id_opcode),
        .id_dst         (id_dst),
        .id_s1          (id_s1),
        .id_s2          (id_s2),
        .id_imm         (id_imm),
        // Use FORWARDED values instead of raw register reads
        .id_gpr_s1      (fwd_gpr_s1),
        .id_gpr_s2      (fwd_gpr_s2),
        .id_hreg_s1     (fwd_hreg_s1),
        .id_hreg_s2     (fwd_hreg_s2),
        .id_pc          (id_pc),
        .id_gpr_we      (id_gpr_we),
        .id_hreg_we     (id_hreg_we),
        .id_is_branch   (id_is_branch),
        .id_is_jump     (id_is_jump),
        .id_is_call     (id_is_call),
        .id_is_ret      (id_is_ret),
        .id_is_codex    (id_is_codex),
        .id_is_halt     (id_is_halt),
        .id_is_print    (id_is_print),
        .id_is_emits    (id_is_emits),
        .id_is_push     (id_is_push),
        .id_is_pop      (id_is_pop),
        .current_flags  (flags_out),
        .rom_addr       (rom_addr),
        .rom_data       (rom_data),
        .rom_valid      (rom_valid),
        .guard_vec      (guard_vec),
        .guard_pass     (guard_pass),
        .guard_u        (guard_u),
        .guard_rho      (guard_rho),
        .calu_op        (calu_op),
        .calu_index     (calu_index),
        .calu_src1      (calu_src1),
        .calu_src2      (calu_src2),
        .calu_scl       (calu_scl),
        .calu_result_vec(calu_result_vec),
        .calu_result_scl(calu_result_scl),
        // HISAB serializer
        .hisab_pack0    (hisab_pack0),
        .hisab_pack1    (hisab_pack1),
        .hisab_pack2    (hisab_pack2),
        .hisab_crc      (hisab_crc),
        .ex_opcode      (ex_opcode),
        .ex_dst         (ex_dst),
        .ex_gpr_result  (ex_gpr_result),
        .ex_hreg_result (ex_hreg_result),
        .ex_gpr_we      (ex_gpr_we),
        .ex_hreg_we     (ex_hreg_we),
        .ex_flags_new   (ex_flags_new),
        .ex_flags_we    (ex_flags_we),
        .ex_is_halt     (ex_is_halt),
        .ex_is_print    (ex_is_print),
        .ex_is_emits    (ex_is_emits),
        .ex_emits_addr  (ex_emits_addr),
        .ex_print_data  (ex_print_data),
        .ex_is_push     (ex_is_push),
        .ex_is_pop      (ex_is_pop),
        .ex_push_data   (ex_push_data),
        .branch_taken   (branch_taken_w),
        .branch_target  (branch_target_w),
        .is_eret        (trap_is_eret_w),
        .in_user        (trap_in_user_w),
        .priv_fault     (trap_priv_fault_w),
        .mem_base       (mem_base_w),
        .mem_limit      (mem_limit_w),
        .mem_fault      (trap_mem_fault_w),
        .is_syscall     (trap_syscall_w),
        // Data RAM
        .id_mem_read    (id_mem_read),
        .id_mem_write   (id_mem_write),
        .ex_mem_read    (ex_mem_read),
        .ex_mem_write   (ex_mem_write),
        .ex_mem_addr    (ex_mem_addr),
        .ex_mem_wdata   (ex_mem_wdata)
    );

    // ── Memory ──────────────────────────────────────────────────
    hcpu_memory u_memory (
        .clk            (clk),
        .rst_n          (rst_n),
        .stall          (ex_stall),
        .ex_opcode      (ex_opcode),
        .ex_dst         (ex_dst),
        .ex_gpr_result  (ex_gpr_result),
        .ex_hreg_result (ex_hreg_result),
        .ex_gpr_we      (ex_gpr_we),
        .ex_hreg_we     (ex_hreg_we),
        .ex_flags_new   (ex_flags_new),
        .ex_flags_we    (ex_flags_we),
        .ex_is_halt     (ex_is_halt),
        .ex_is_push     (ex_is_push),
        .ex_is_pop      (ex_is_pop),
        .ex_push_data   (ex_push_data),
        .ex_mem_read    (ex_mem_read),
        .ex_mem_write   (ex_mem_write),
        .ex_mem_addr    (ex_mem_addr),
        .ex_mem_wdata   (ex_mem_wdata),
        .dram_re        (dram_re),
        .dram_we        (dram_we),
        .dram_addr      (dram_addr),
        .dram_wdata     (dram_wdata),
        .dram_rdata     (dram_rdata),
        .mem_dst        (mem_dst),
        .mem_gpr_result (mem_gpr_result),
        .mem_hreg_result(mem_hreg_result),
        .mem_gpr_we     (mem_gpr_we),
        .mem_hreg_we    (mem_hreg_we),
        .mem_flags_new  (mem_flags_new),
        .mem_flags_we   (mem_flags_we),
        .mem_is_halt    (mem_is_halt)
    );

    // ── Writeback ───────────────────────────────────────────────
    hcpu_writeback u_writeback (
        .mem_dst        (mem_dst),
        .mem_gpr_result (mem_gpr_result),
        .mem_hreg_result(mem_hreg_result),
        .mem_gpr_we     (mem_gpr_we),
        .mem_hreg_we    (mem_hreg_we),
        .mem_flags_new  (mem_flags_new),
        .mem_flags_we   (mem_flags_we),
        .mem_is_halt    (mem_is_halt),
        .wb_gpr_we      (wb_gpr_we),
        .wb_gpr_waddr   (wb_gpr_waddr),
        .wb_gpr_wdata   (wb_gpr_wdata),
        .wb_hreg_we     (wb_hreg_we),
        .wb_hreg_waddr  (wb_hreg_waddr),
        .wb_hreg_wdata  (wb_hreg_wdata),
        .wb_flags_we    (wb_flags_we),
        .wb_flags       (wb_flags),
        .wb_halt        (wb_halt)
    );

    // ── Register file ───────────────────────────────────────────
    hcpu_regfile u_regfile (
        .clk         (clk),
        .rst_n       (rst_n),
        .gpr_raddr1  (gpr_raddr1),
        .gpr_raddr2  (gpr_raddr2),
        .gpr_rdata1  (gpr_rdata1),
        .gpr_rdata2  (gpr_rdata2),
        .gpr_we      (wb_gpr_we),
        .gpr_waddr   (wb_gpr_waddr),
        .gpr_wdata   (wb_gpr_wdata),
        .hreg_raddr1 (hreg_raddr1),
        .hreg_raddr2 (hreg_raddr2),
        .hreg_rdata1 (hreg_rdata1),
        .hreg_rdata2 (hreg_rdata2),
        .hreg_we     (wb_hreg_we),
        .hreg_waddr  (wb_hreg_waddr),
        .hreg_wdata  (wb_hreg_wdata),
        .flags_we    (wb_flags_we),
        .flags_in    (wb_flags),
        .flags_out   (flags_out),
        .pc_we       (1'b0),
        .pc_in       ({`XLEN{1'b0}}),
        .pc_out      (pc_out),
        // Debug / Wishbone read-back
        .dbg_gpr_raddr (dbg_gpr_raddr),
        .dbg_gpr_rdata (dbg_gpr_rdata),
        .dbg_flags     (dbg_flags)
    );

    // ── Master Table ROM ────────────────────────────────────────
    hcpu_rom u_rom (
        .addr     (rom_addr),
        .data_out (rom_data),
        .valid    (rom_valid)
    );

    // ── Guard checker ───────────────────────────────────────────
    hcpu_guard #(.PIPELINE_GUARD(0)) u_guard (
        .clk        (clk),
        .rst_n      (rst_n),
        .vec        (guard_vec),
        .guard_pass (guard_pass),
        .g1_pass    (g1),
        .g2_pass    (g2),
        .g3_pass    (g3),
        .g4_pass    (g4),
        .t1_pass    (t1),
        .t2_pass    (t2),
        .u_value    (guard_u),
        .rho_value  (guard_rho)
    );

    // ── Codex ALU ───────────────────────────────────────────────
    hcpu_codex_alu u_codex_alu (
        .op         (calu_op),
        .index      (calu_index),
        .src1       (calu_src1),
        .src2       (calu_src2),
        .src_scl    (calu_scl),
        .result_vec (calu_result_vec),
        .result_scl (calu_result_scl),
        .done       (calu_done)
    );

    // ── HISAB Serializer ─────────────────────────────────────────
    hcpu_hisab u_hisab (
        .op          (2'd0),             // Always HPACK mode (CRC is computed alongside)
        .vec_in      (fwd_hreg_s1),      // Forwarded H-Reg S1
        .gpr_s1      (fwd_gpr_s1),
        .gpr_s2      (fwd_gpr_s2),
        .extra_byte  (8'd0),
        .pack_word0  (hisab_pack0),
        .pack_word1  (hisab_pack1),
        .pack_word2  (hisab_pack2),
        .guard_status(hisab_guard_status),
        .crc_out     (hisab_crc),
        .done        ()                  // Always 1 (single-cycle)
    );

    // ── UART TX ─────────────────────────────────────────────────
    hcpu_uart_tx #(
        .CLK_HZ (CLK_HZ),
        .BAUD   (BAUD)
    ) u_uart (
        .clk      (clk),
        .rst_n    (rst_n),
        .tx_data  (uart_data),
        .tx_start (uart_start),
        .tx_out   (uart_tx),
        .tx_busy  (uart_busy)
    );

    // ── Memory-mapped I/O, then the RAM behind it ───────────────
    //
    // The decoder sits between the memory stage and the RAM rather than
    // beside it: the top sixteen words of the data space are peripherals and
    // everything below is memory, so `LOAD` and `STORE` reach the receiver
    // and the timer with no new instruction.
    wire                    uart_rx_pulled = (uart_rx === 1'b0) ? 1'b0 : 1'b1;

    hcpu_mmio #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) u_mmio (
        .clk          (clk),
        .rst_n        (rst_n),
        .re           (dram_re),
        .we           (dram_we),
        .addr         (dram_addr),
        .wdata        (dram_wdata),
        .rdata        (dram_rdata),
        .ram_re       (ram_re),
        .ram_we       (ram_we),
        .ram_addr     (ram_addr),
        .ram_wdata    (ram_wdata),
        .ram_rdata    (ram_rdata),
        .uart_rx_in   (uart_rx_pulled),
        .uart_tx_busy (uart_busy),
        .trap_reg_we    (trap_reg_we_w),
        .trap_reg_sel   (trap_reg_sel_w),
        .trap_reg_wdata (trap_reg_wdata_w),
        .trap_reg_rdata (trap_reg_rdata_w),
        .src_timer      (trap_src_timer_w),
        .src_uart_rx    (trap_src_rx_w),
        .mem_base       (mem_base_w),
        .mem_limit      (mem_limit_w),
        .imem_we        (imem_we),
        .imem_waddr     (imem_waddr),
        .imem_wdata     (imem_wdata)
    );

    // ── Trap unit ───────────────────────────────────────────────
    // `pc_valid` WAS TIED HIGH, on the premise that hcpu_fetch always presents
    // a PC and on a flush presents the redirect target rather than nothing.
    // The premise was false and the comment here named its own consequence:
    // "if the front end ever gains a state with no meaningful PC, this has to
    // become that state's inverse or a trap will return into a bubble."
    //
    // It has such a state, and always did. hcpu_fetch answers a redirect by
    // setting `if_pc <= 0` and `fetch_valid <= 0` -- its way of saying it is
    // presenting nothing -- and needs two cycles to refill. A maskable
    // interrupt landing in those two cycles read the zero as an ADDRESS and
    // saved it as the place to resume, so the process came back at 0, which is
    // boot code, in user mode, where its first peripheral store faulted it for
    // ever. kernel.hasm's process A froze at 337 that way from the day the
    // scheduler was built, and its bench never asked whether A was moving.
    //
    // Measured before: sixty deadlines swept against a three-instruction loop,
    // twenty-one of them saved zero -- every one that landed in the shadow.
    // On the board, eight samples of rtl/programs/trap_shadow.hasm answered
    // 0 0 88 89 88 0 0 88 with the loop at 88.
    //
    // So `pc_valid` is now that state's inverse, exactly as the old comment
    // asked for: hcpu_fetch writes it in the same places it writes `if_pc`,
    // under the name this module already used for it. A trap does not fire while the front end is empty; it
    // fires a cycle or two later with a real PC to name. Nothing is lost by
    // the wait -- the timer's `expired` is a sticky level, not a pulse.
    //
    // `src_illegal` IS TIED OFF. The cause is defined so that adding it later
    // does not renumber the others, but nothing raises it yet: the machine's
    // only illegal-instruction path is HALT_ERR on a bad ROM index, and turning
    // a halt into a trap is a semantic change, not part of adding traps.
    // tests/test_integrity/test_traps.py pins it at zero so it cannot be
    // mistaken for something that works.
    hcpu_trap u_trap (
        .clk           (clk),
        .rst_n         (rst_n),
        .src_timer     (trap_src_timer_w),
        .src_uart_rx   (trap_src_rx_w),
        .src_illegal   (1'b0),
        .src_priv      (trap_priv_fault_w),
        .src_mem       (trap_mem_fault_w),
        .src_syscall   (trap_syscall_w),
        // What a maskable interrupt should resume at: the branch's own
        // target if Execute is taking one THIS cycle (its effect is already
        // final), else Fetch's ordinary sequential guess. Declared here,
        // right before use, because it needs `if_pc` -- declared later in
        // this file, in the Fetch -> Decode section -- and Verilog wires
        // have no forward-declaration the way the `wire redirect_target`
        // block above this could rely on for signals already in scope there.
        .pc_now        (branch_taken_w ? branch_target_w : if_pc),
        .pc_valid      (if_pc_valid),
        .pc_fault      (id_pc),
        .reg_we        (trap_reg_we_w),
        .reg_sel       (trap_reg_sel_w),
        .reg_wdata     (trap_reg_wdata_w),
        .reg_rdata     (trap_reg_rdata_w),
        .eret          (trap_is_eret_w),
        .trap_redirect (trap_redirect_w),
        .trap_target   (trap_target_w),
        .in_trap       (trap_in_trap_w),
        .in_user       (trap_in_user_w)
    );

    // The RAM port is multiplexed, not duplicated. While EMITS runs the
    // pipeline is stalled exactly as it is for PRINT, so the memory stage is
    // issuing nothing and the port is free -- `emits_busy` is what says so.
    // A write is forced off in that window for the same reason: the only
    // thing EMITS does to memory is read it.
    hcpu_dataram u_dataram (
        .clk   (clk),
        .re    (emits_busy ? 1'b1    : ram_re),
        .we    (emits_busy ? 1'b0    : ram_we),
        .addr  (emits_busy ? str_addr : ram_addr),
        .wdata (ram_wdata),
        .rdata (ram_rdata)
    );

    // ── Controller ──────────────────────────────────────────────
    hcpu_controller u_controller (
        .clk             (clk),
        .rst_n           (rst_n),
        .ex_is_print     (print_active),
        .branch_taken      (redirect_taken),
        .wb_halt           (wb_halt),
        .load_use_hazard   (load_use_hazard),
        .store_load_hazard (store_load_hazard),
        .uart_busy         (uart_busy),
        .pc_stall        (pc_stall),
        .id_stall        (id_stall),
        .ex_stall        (ex_stall),
        .if_flush        (if_flush),
        .id_flush        (id_flush),
        .halted          (halted)
    );

    // ── Guard LED output ────────────────────────────────────────
    assign guard_led = flags_out[`FLAG_G];

endmodule
