# ============================================================================
# HCPU Testbench Makefile — iverilog + vvp
# (c) 2026 Maulana Amratulloh
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
        sim_letters sim_trap_hreg sim_hfs_syscall sim_hfs_persist sim_subroutine sim_syscall_io sim_branch_trap_race sim_hos \
        sim_nui_embedding sim_loader_nui sim_video_timing sim_shell \
        sim_redirect_shadow sim_epc_eret sim_flags_ctx sim_emits \
        sim_hfs_lifecycle sim_sdio sim_sdio_prog \
        sim_text_render sim_telemetry sim_dashboard sim_page_key clean

# Six of these benches existed with no target at all: tb_hcpu_trap,
# tb_hcpu_mmio, tb_hcpu_timer, tb_hcpu_uart_rx, tb_gowin_top and
# tb_gowin_loader could only be run by hand. RTL_SRC was already fixed to glob
# rather than list, for exactly this reason -- but the LIST OF BENCHES was
# still hand-written, so the trap unit's own bench was unreachable from `make`
# while traps, supervisor mode, memory protection and syscall were all built
# on top of it.
all: sim_rom sim_guard sim_codex_alu sim_hisab sim_top sim_kernel \
     sim_trap sim_mmio sim_timer sim_uart_rx sim_board sim_loader \
     sim_letters sim_trap_hreg sim_hfs_syscall sim_hfs_persist sim_subroutine sim_syscall_io sim_branch_trap_race sim_hos \
     sim_nui_embedding sim_loader_nui sim_video_timing sim_shell \
     sim_redirect_shadow sim_epc_eret sim_flags_ctx sim_emits \
     sim_hfs_lifecycle sim_sdio sim_sdio_prog \
     sim_text_render sim_telemetry sim_dashboard sim_page_key

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
	rm -f *.vvp *.vcd blank_text.hex program.hex loader.hex payload.txt kernel.hex shell.hex flags_ctx.hex hfs_lifecycle.hex letters.hex trap_hreg.hex shell_hfs.hex shell_persist.hex subroutine.hex syscall_io.hex hos_demo.hex nui_embedding.hex nui_payload.txt

# ── H-Kernel on the full pipeline ───────────────────────────────
# The board wrapper, not hcpu_top, because the wrapper is what holds the
# instruction memory the kernel is baked into.
sim_kernel: tb_hcpu_kernel.vvp kernel.hex
	$(VVP) $<

# The shell: a user process that reads the serial line, and a kernel that
# serves the read. Commands go in on uart_rxd as real bytes.
sim_shell: tb_hcpu_shell.vvp shell.hex
	$(VVP) $<

# The two cycles after a taken branch, where a maskable interrupt saves zero.
# sim_branch_trap_race covers the cycle they share; this covers the shadow.
sim_redirect_shadow: tb_hcpu_trap_redirect_shadow.vvp
	$(VVP) $<

# How much distance a handler needs between writing TRAP_EPC and returning.
# The answer has to be none; sim_trap check 18 asks the unit the same thing.
sim_epc_eret: tb_hcpu_trap_epc_eret.vvp
	$(VVP) $<

# FLAGS belongs to the process. Two patterns, two processes, a timer between.
sim_flags_ctx: tb_hcpu_flags_ctx.vvp flags_ctx.hex
	$(VVP) $<

# The character path: EMITS, one ASCII byte per word, zero word ends it.
sim_emits: tb_hcpu_emits.vvp
	$(VVP) $<

# M4.1: the four operations of a filesystem, in one file's life.
sim_hfs_lifecycle: tb_hcpu_hfs_lifecycle.vvp hfs_lifecycle.hex
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

# HOS: heap, guarded HFS, HAR -- pure software over HAL, no new opcode.
sim_hos: tb_hcpu_hos.vvp hos_demo.hex
	$(VVP) $<

hos_demo.hex: $(RTL_DIR)/programs/hos_demo.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

tb_hcpu_hos.vvp: $(TB_DIR)/tb_hcpu_hos.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

# NUI's physics embedding sum (titik/garis/lengkung/theta/rho), on the real
# pipeline -- letter accumulation + CGET + ADD/SUB, no new opcode.
sim_nui_embedding: tb_hcpu_nui_embedding.vvp nui_embedding.hex
	$(VVP) $<

nui_embedding.hex: $(RTL_DIR)/programs/nui_embedding.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

tb_hcpu_nui_embedding.vvp: $(TB_DIR)/tb_hcpu_nui_embedding.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

tb_hcpu_subroutine.vvp: $(TB_DIR)/tb_hcpu_subroutine.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

trap_hreg.hex: $(RTL_DIR)/programs/trap_hreg.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

# A handler that runs ONE codex instruction, and whether the caller's H0
# comes back. Red before hcpu_regfile.v banked the codex by privilege; the
# program's header carries why it uses Kaf and nothing else.
tb_hcpu_trap_hreg.vvp: $(TB_DIR)/tb_hcpu_trap_hreg.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^
sim_trap_hreg: tb_hcpu_trap_hreg.vvp trap_hreg.hex
	$(VVP) $<

letters.hex: $(RTL_DIR)/programs/letters.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

tb_hcpu_letters.vvp: $(TB_DIR)/tb_hcpu_letters.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

kernel.hex: $(RTL_DIR)/programs/kernel.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

tb_hcpu_kernel.vvp: $(TB_DIR)/tb_hcpu_kernel.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

# shell.hasm includes hal.hasm, so the HAL is a prerequisite of the image even
# though asm2hex.py is only ever handed the one file.
SHELL_DEPS = $(RTL_DIR)/programs/shell.hasm $(RTL_DIR)/programs/hal.hasm \
             $(RTL_DIR)/programs/hos.hasm $(RTL_DIR)/programs/hos_hctx.hasm \
             $(RTL_DIR)/programs/hos_hfs_disk.hasm $(RTL_DIR)/programs/hal_sd.hasm

shell.hex: $(SHELL_DEPS)
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

# shell.hasm with pid 0 redirected to an HFS probe -- in this image only. The
# shipped shell has no process that calls its own HFS syscalls; this bench
# supplies one. Depends on everything shell.hex does, plus the probe and the
# injector, so a change to any of them rebuilds it instead of running stale.
# 0x800, not 0x400: the shell grew past 1,024 words when it gained the card
# layer, and inject_probe.py refuses a probe that would land inside the image.
PROBE_BASE = 0x800

shell_hfs.hex: $(SHELL_DEPS) $(TB_DIR)/hfs_syscall_probe.hasm $(RTL_DIR)/scripts/inject_probe.py
	python3 $(RTL_DIR)/scripts/inject_probe.py $(RTL_DIR)/programs/shell.hasm proc0 \
	    $(TB_DIR)/hfs_syscall_probe.hasm $(PROBE_BASE) > $@

tb_hcpu_hfs_syscall.vvp: $(TB_DIR)/tb_hcpu_hfs_syscall.v $(TB_DIR)/sd_card_model.v \
                         $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^
sim_hfs_syscall: tb_hcpu_hfs_syscall.vvp shell_hfs.hex
	$(VVP) $<

# The same shell, booted twice, with data RAM zeroed between the boots and the
# card model left alone. The probe decides what to do from whether file 0
# already exists.
shell_persist.hex: $(SHELL_DEPS) $(TB_DIR)/hfs_persist_probe.hasm $(RTL_DIR)/scripts/inject_probe.py
	python3 $(RTL_DIR)/scripts/inject_probe.py $(RTL_DIR)/programs/shell.hasm proc0 \
	    $(TB_DIR)/hfs_persist_probe.hasm $(PROBE_BASE) > $@

tb_hcpu_hfs_persist.vvp: $(TB_DIR)/tb_hcpu_hfs_persist.v $(TB_DIR)/sd_card_model.v \
                         $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^
sim_hfs_persist: tb_hcpu_hfs_persist.vvp shell_persist.hex
	$(VVP) $<

tb_hcpu_shell.vvp: $(TB_DIR)/tb_hcpu_shell.v $(TB_DIR)/sd_card_model.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

tb_hcpu_trap_redirect_shadow.vvp: $(TB_DIR)/tb_hcpu_trap_redirect_shadow.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

tb_hcpu_trap_epc_eret.vvp: $(TB_DIR)/tb_hcpu_trap_epc_eret.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

flags_ctx.hex: $(RTL_DIR)/programs/flags_ctx.hasm $(RTL_DIR)/programs/hal.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

tb_hcpu_flags_ctx.vvp: $(TB_DIR)/tb_hcpu_flags_ctx.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

tb_hcpu_emits.vvp: $(TB_DIR)/tb_hcpu_emits.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

hfs_lifecycle.hex: $(RTL_DIR)/programs/hfs_lifecycle.hasm $(RTL_DIR)/programs/hos.hasm $(RTL_DIR)/programs/hal.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

tb_hcpu_hfs_lifecycle.vvp: $(TB_DIR)/tb_hcpu_hfs_lifecycle.v $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

# ── unit benches ────────────────────────────────────────────────
sim_trap: tb_hcpu_trap.vvp
	$(VVP) $<
sim_sdio: tb_hcpu_sdio.vvp
	$(VVP) $<
sim_sdio_prog: tb_hcpu_sdio_prog.vvp sdio_write.hex
	$(VVP) $<

# ── M5 display: four benches under the dashboard ────────────────
# The layout image and its field addresses are generated, never edited and
# never copied: hcpu_dashboard.v `includes the .vh, so it must exist before
# iverilog reads a line, and the text RAM reads the .hex at elaboration.
$(RTL_DIR)/hcpu_dashboard.hex $(RTL_DIR)/hcpu_dashboard_pos.vh: \
		$(RTL_DIR)/scripts/gen_dashboard.py
	python3 $< >/dev/null

# The renderer's own bench writes the cells it checks, so it must start from
# a blank screen rather than from the dashboard underneath it.
blank_text.hex:
	python3 -c "open('$@','w').write('0020\n'*16384)"

sim_text_render: tb_hcpu_text_render.vvp blank_text.hex
	$(VVP) $<
sim_telemetry: tb_hcpu_telemetry.vvp
	$(VVP) $<
sim_dashboard: tb_hcpu_dashboard.vvp
	$(VVP) $<
sim_page_key: tb_hcpu_page_key.vvp
	$(VVP) $<

tb_hcpu_text_render.vvp: $(TB_DIR)/tb_hcpu_text_render.v \
                         $(RTL_DIR)/hcpu_video_timing.v $(RTL_DIR)/hcpu_text_ram.v \
                         $(RTL_DIR)/hcpu_font_rom.v $(RTL_DIR)/hcpu_text_render.v
	$(IVERILOG) $(INC) -o $@ $^
tb_hcpu_telemetry.vvp: $(TB_DIR)/tb_hcpu_telemetry.v $(RTL_DIR)/hcpu_telemetry.v
	$(IVERILOG) $(INC) -o $@ $^
tb_hcpu_dashboard.vvp: $(TB_DIR)/tb_hcpu_dashboard.v $(RTL_DIR)/hcpu_compositor.v \
                       $(RTL_DIR)/hcpu_dashboard_pos.vh
	$(IVERILOG) $(INC) -o $@ $(TB_DIR)/tb_hcpu_dashboard.v $(RTL_DIR)/hcpu_compositor.v
tb_hcpu_page_key.vvp: $(TB_DIR)/tb_hcpu_page_key.v $(RTL_DIR)/hcpu_page_key.v
	$(IVERILOG) $(INC) -o $@ $^
sim_mmio: tb_hcpu_mmio.vvp
	$(VVP) $<
sim_timer: tb_hcpu_timer.vvp
	$(VVP) $<
sim_uart_rx: tb_hcpu_uart_rx.vvp
	$(VVP) $<
sim_video_timing: tb_hcpu_video_timing.vvp
	$(VVP) $<

tb_hcpu_sdio.vvp: $(TB_DIR)/tb_hcpu_sdio.v $(TB_DIR)/sd_card_model.v \
                  $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

# M4.2 through the machine: the same card, reached by LOAD and STORE from a
# program running on the pipeline rather than by the module's own ports. The
# board wrapper is in the source list because it is what holds the instruction
# memory the program is baked into.
sdio_write.hex: $(RTL_DIR)/programs/sdio_write.hasm
	python3 $(RTL_DIR)/scripts/asm2hex.py $< > $@

tb_hcpu_sdio_prog.vvp: $(TB_DIR)/tb_hcpu_sdio_prog.v $(TB_DIR)/sd_card_model.v \
                       $(RTL_DIR)/fpga/gowin/hcpu_gowin_top.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

tb_hcpu_trap.vvp tb_hcpu_mmio.vvp tb_hcpu_timer.vvp tb_hcpu_uart_rx.vvp \
tb_hcpu_video_timing.vvp: \
  tb_%.vvp: $(TB_DIR)/tb_%.v $(RTL_SRC)
	$(IVERILOG) $(INC) -o $@ $^

# ── board benches ───────────────────────────────────────────────
sim_board: tb_gowin_top.vvp program.hex
	$(VVP) $<
sim_loader: tb_gowin_loader.vvp loader.hex payload.txt
	$(VVP) $<
sim_loader_nui: tb_gowin_loader_nui.vvp loader.hex nui_payload.txt
	$(VVP) $<

tb_gowin_top.vvp tb_gowin_loader.vvp tb_gowin_loader_nui.vvp: tb_%.vvp: \
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

# Same wire format as payload.txt, different program: nui_embedding.hasm's
# own 48 words (L_JIM, L_KHA, CGET/ADD/SUB, five PRINTs), sent as something
# the loader delivers rather than something synthesised into the bitstream.
nui_payload.txt: $(RTL_DIR)/programs/nui_embedding.hasm
	python3 $(RTL_DIR)/scripts/send_program.py $< | od -An -v -tx1 | tr -s ' ' '\n' | grep . > $@
