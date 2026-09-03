# ============================================================================
# HCPU Testbench Makefile — iverilog + vvp
# (c) 2026 HMCL
# ============================================================================

# -g2012 enables $fatal, which is how a failing testbench exits non-zero.
IVERILOG  = iverilog -g2012
VVP       = vvp
GTKWAVE   = gtkwave

# Source directories
RTL_DIR   = ..
TB_DIR    = .
INC       = -I$(RTL_DIR)

# RTL sources (order matters for dependencies)
# Every hcpu_*.v in the parent, found rather than listed. The hand-written
# list went stale twice without anyone noticing: hcpu_mmio.v and hcpu_trap.v
# were added to the design and never added here, so tb_hcpu_top stopped
# elaborating and its integration assertions silently stopped running. The
# Python side globs, so it kept passing -- two lists, one truth, and the one
# that was maintained by hand is the one that drifted.
RTL_SRC   = $(wildcard $(RTL_DIR)/hcpu_*.v)

# ── Simulation targets ──────────────────────────────────────────

.PHONY: all sim_rom sim_guard sim_codex_alu sim_hisab sim_top sim_kernel \
        sim_trap sim_mmio sim_timer sim_uart_rx sim_board sim_loader \
     sim_letters sim_subroutine sim_syscall_io sim_branch_trap_race \
        sim_letters sim_subroutine sim_syscall_io sim_branch_trap_race sim_subroutine clean

# Six of these benches existed with no target at all: tb_hcpu_trap,
# tb_hcpu_mmio, tb_hcpu_timer, tb_hcpu_uart_rx, tb_gowin_top and
# tb_gowin_loader could only be run by hand. RTL_SRC was already fixed to glob
# rather than list, for exactly this reason -- but the LIST OF BENCHES was
# still hand-written, so the trap unit's own bench was unreachable from `make`
# while traps, supervisor mode, memory protection and syscall were all built
# on top of it.
all: sim_rom sim_guard sim_codex_alu sim_hisab sim_top sim_kernel \
     sim_trap sim_mmio sim_timer sim_uart_rx sim_board sim_loader \
     sim_letters sim_subroutine sim_syscall_io sim_branch_trap_race

sim_rom: tb_rom.vvp
	$(VVP) $<

tb_rom.vvp: $(TB_DIR)/tb_rom.v $(RTL_DIR)/hcpu_rom.v
	$(IVERILOG) $(INC) -o $@ $^

sim_guard: tb_guard.vvp
	$(VVP) $<

tb_guard.vvp: $(TB_DIR)/tb_guard.v $(RTL_DIR)/hcpu_rom.v $(RTL_DIR)/hcpu_guard.v
	$(IVERILOG) $(INC) -o $@ $^

sim_codex_alu: tb_codex_alu.vvp
	$(VVP) $<

tb_codex_alu.vvp: $(TB_DIR)/tb_codex_alu.v $(RTL_DIR)/hcpu_rom.v $(RTL_DIR)/hcpu_codex_alu.v
	$(IVERILOG) $(INC) -o $@ $^

sim_hisab: tb_hisab.vvp
	$(VVP) $<

tb_hisab.vvp: $(TB_DIR)/tb_hisab.v $(RTL_DIR)/hcpu_rom.v $(RTL_DIR)/hcpu_guard.v $(RTL_DIR)/hcpu_hisab.v
	$(IVERILOG) $(INC) -o $@ $^

sim_top: tb_hcpu_top.vvp
	$(VVP) $<

tb_hcpu_top.vvp: $(TB_DIR)/tb_hcpu_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

# ── Waveform viewing ────────────────────────────────────────────

wave_rom:      sim_rom;      $(GTKWAVE) tb_rom.vcd &
wave_guard:    sim_guard;    $(GTKWAVE) tb_guard.vcd &
wave_alu:      sim_codex_alu;$(GTKWAVE) tb_codex_alu.vcd &
wave_hisab:    sim_hisab;    $(GTKWAVE) tb_hisab.vcd &
wave_top:      sim_top;      $(GTKWAVE) tb_hcpu_top.vcd &

# ── Clean ───────────────────────────────────────────────────────

clean:
	rm -f *.vvp *.vcd program.hex loader.hex payload.txt kernel.hex letters.hex subroutine.hex syscall_io.hex

# ── H-Kernel on the full pipeline ───────────────────────────────
# The board wrapper, not hcpu_top, because the wrapper is what holds the
# instruction memory the kernel is baked into.
sim_kernel: tb_hcpu_kernel.vvp kernel.hex
	$(VVP) $<

# The twenty-eight letter opcodes. Nothing executed one until this bench.
sim_letters: tb_hcpu_letters.vvp letters.hex
	$(VVP) $<

# CALL and RET. The spec reserved them; nothing implemented them until now.
sim_subroutine: tb_hcpu_subroutine.vvp subroutine.hex
	$(VVP) $<

subroutine.hex: $(RTL_DIR)/programs/subroutine.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

# I/O through the kernel. PRINT is privileged, so this is the only way out.
sim_syscall_io: tb_hcpu_syscall_io.vvp syscall_io.hex
	$(VVP) $<

syscall_io.hex: $(RTL_DIR)/programs/syscall_io.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

tb_hcpu_syscall_io.vvp: $(TB_DIR)/tb_hcpu_syscall_io.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

# A taken branch and a maskable interrupt resolving the same Execute cycle.
# Direct hcpu_top instantiation, like tb_hcpu_top.v -- this is about the wire
# between Execute's branch resolution and the trap unit's own input, not
# about the board wrapper.
sim_branch_trap_race: tb_hcpu_branch_trap_race.vvp
	$(VVP) $<

tb_hcpu_branch_trap_race.vvp: $(TB_DIR)/tb_hcpu_branch_trap_race.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

tb_hcpu_subroutine.vvp: $(TB_DIR)/tb_hcpu_subroutine.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

letters.hex: $(RTL_DIR)/programs/letters.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

tb_hcpu_letters.vvp: $(TB_DIR)/tb_hcpu_letters.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

kernel.hex: $(RTL_DIR)/programs/kernel.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

tb_hcpu_kernel.vvp: $(TB_DIR)/tb_hcpu_kernel.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

# ── unit benches ────────────────────────────────────────────────
sim_trap: tb_hcpu_trap.vvp
	$(VVP) $<
sim_mmio: tb_hcpu_mmio.vvp
	$(VVP) $<
sim_timer: tb_hcpu_timer.vvp
	$(VVP) $<
sim_uart_rx: tb_hcpu_uart_rx.vvp
	$(VVP) $<

tb_hcpu_trap.vvp tb_hcpu_mmio.vvp tb_hcpu_timer.vvp tb_hcpu_uart_rx.vvp: \
  tb_%.vvp: $(TB_DIR)/tb_%.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

# ── board benches ───────────────────────────────────────────────
sim_board: tb_gowin_top.vvp program.hex
	$(VVP) $<
sim_loader: tb_gowin_loader.vvp loader.hex payload.txt
	$(VVP) $<

tb_gowin_top.vvp tb_gowin_loader.vvp: tb_%.vvp: \
  $(TB_DIR)/tb_%.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

program.hex: $(RTL_DIR)/programs/test_bsm.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

loader.hex: $(RTL_DIR)/programs/loader.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

# The loader's input is a BYTE stream, not a word image, so it goes through
# send_program.py -- the same host tool a board would be fed from -- and then
# into the one-byte-per-token form $readmemh reads. Without this rule the
# bench could not run from a clean checkout at all: nothing produced its input.
payload.txt: $(RTL_DIR)/programs/payload.hasm
	python3 $(RTL_DIR)/scripts/send_program.py $< | od -An -v -tx1 | tr -s ' ' '\n' | grep . > $@
