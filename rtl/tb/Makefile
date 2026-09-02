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

.PHONY: all sim_rom sim_guard sim_codex_alu sim_hisab sim_top clean

all: sim_rom sim_guard sim_codex_alu sim_hisab sim_top

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
	rm -f *.vvp *.vcd
