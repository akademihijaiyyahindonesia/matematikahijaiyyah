# ============================================================================
# HCPU on the Tang Nano 9K — open-source Gowin flow
# (c) 2026 HMCL
# ============================================================================
#
# Mirrors rtl/fpga/xilinx/Makefile. Two targets matter:
#
#   make sim        simulate the board wrapper and decode its UART output
#   make bitstream  synthesise, place, route and pack
#
# `sim` needs only Icarus Verilog and runs anywhere. `bitstream` needs the
# open-source Gowin chain:
#
#   brew install yosys                      # or the distro package
#   pip install apycula                     # gowin_pack
#   # nextpnr-himbaechel: build from source, or use a prebuilt oss-cad-suite
#
# The vendor Gowin IDE is the alternative; point it at the same sources.

DEVICE   = GW1NR-LV9QN88PC6/I5
FAMILY   = GW1N-9C
BOARD    = tangnano9k

RTL_DIR  = ../..
TOP      = hcpu_gowin_top
# What gets baked into the bitstream. `make bridge` swaps this for the loader,
# after which the bitstream stops being one program and becomes the thing that
# accepts any program over the wire -- which is the point of the board.
PROGRAM ?= $(RTL_DIR)/programs/test_bsm.hasm
PYTHON  ?= python3

# The three tools the bitstream needs, overridable so the build does not care
# where they were installed:
#
#   gowin_pack        pip install apycula      (lands in the project venv)
#   openFPGALoader    brew install openfpgaloader
#   nextpnr-himbaechel  not in Homebrew and not quick to build -- it comes from
#                     a prebuilt oss-cad-suite, referenced by path rather than
#                     by sourcing its environment, because that environment
#                     shadows the yosys and python this project already uses.
OSS_CAD  ?= $(HOME)/opt/oss-cad-suite
NEXTPNR  ?= $(firstword $(wildcard $(OSS_CAD)/bin/nextpnr-himbaechel) \
                        $(shell command -v nextpnr-himbaechel 2>/dev/null))
GOWIN_PACK ?= gowin_pack
LOADER     ?= openFPGALoader

# The wrapper plus every hcpu_*.v, found rather than listed. The hand-written
# list here went stale exactly the way rtl/tb/Makefile's did: hcpu_mmio.v and
# hcpu_trap.v were added to the design and not to this list, so `make sim`,
# `make synth` and `make bitstream` all failed with "Unknown module type" --
# and would have failed on the day the board arrived, not before.
SOURCES  = hcpu_gowin_top.v $(wildcard $(RTL_DIR)/hcpu_*.v)

.PHONY: all sim synth bitstream flash bridge send clean

all: sim

# ── Program image ───────────────────────────────────────────────
# Written as plain ASCII. The Xilinx copy of this file was UTF-16, which
# $readmemh refuses outright — the instruction memory stayed uninitialised and
# nothing said so.
program.hex: $(PROGRAM)
	$(PYTHON) $(RTL_DIR)/scripts/asm2hex.py $< > $@

# ── Simulation ──────────────────────────────────────────────────
# Runs the wrapper at the board's real 27 MHz and decodes the serial pin at
# 115200, so a mis-parameterised clock fails here rather than on the desk.
sim: program.hex
	iverilog -g2012 -I $(RTL_DIR) -o tb_gowin_top.vvp \
	    $(RTL_DIR)/tb/tb_gowin_top.v $(SOURCES)
	vvp tb_gowin_top.vvp

# ── Synthesis, place and route, pack ────────────────────────────
# -nodsp because gowin_pack cannot pack the MULT9X9 that synth_gowin infers:
# `KeyError: 'IRBY_IREG0BL_0'`, an attribute apycula's chipdb does not carry.
# nextpnr places it happily, so the failure only appears at the last step, and
# the suite's own gowin_pack fails identically -- it is the packer, not a
# version mismatch. The multiplies come from hcpu_codex_alu's squared norm and
# distance as much as from hcpu_mul, so USE_DSP=0 alone does not avoid them.
# Drop the flag once apycula packs DSPs; the LUT cost is measured in the header
# of hcpu_gowin_top.v.
YOSYS_FLAGS ?= -nodsp

synth: program.hex
	yosys -p "read_verilog -I $(RTL_DIR) $(SOURCES); \
	          synth_gowin $(YOSYS_FLAGS) -top $(TOP) -json $(TOP).json"

$(TOP)_pnr.json: synth
	@test -n "$(NEXTPNR)" || { echo "nextpnr-himbaechel not found."; \
	    echo "Set OSS_CAD=<path to oss-cad-suite> or put it on PATH."; exit 1; }
	$(NEXTPNR) --json $(TOP).json --write $@ \
	    --device $(DEVICE) --vopt cst=hcpu_gowin.cst \
	    --vopt family=$(FAMILY)

bitstream: $(TOP)_pnr.json
	$(GOWIN_PACK) -d $(FAMILY) -o $(TOP).fs $<

flash: bitstream
	$(LOADER) -b $(BOARD) $(TOP).fs

# What is installed, and what is not. Run this first on a new machine.
.PHONY: tools
tools:
	@printf '%-22s %s\n' yosys           "$$(command -v yosys           || echo MISSING)"
	@printf '%-22s %s\n' iverilog        "$$(command -v iverilog        || echo MISSING)"
	@printf '%-22s %s\n' nextpnr-himbaechel "$(if $(NEXTPNR),$(NEXTPNR),MISSING)"
	@printf '%-22s %s\n' gowin_pack      "$$(command -v $(GOWIN_PACK)   || echo MISSING)"
	@printf '%-22s %s\n' openFPGALoader  "$$(command -v $(LOADER)       || echo MISSING)"

# ── The bridge ──────────────────────────────────────────────────
# Build and flash a bitstream whose baked program is the loader. After this,
# changing a program costs a second instead of a synthesis run.
bridge:
	$(MAKE) PROGRAM=$(RTL_DIR)/programs/loader.hasm flash

# Send a program to a board already running the loader:
#     make send PORT=/dev/tty.usbserial-X PROG=../../programs/trap_timer.hasm
PORT ?=
PROG ?= $(RTL_DIR)/programs/trap_timer.hasm
send:
	@test -n "$(PORT)" || { echo "set PORT=<serial device>"; exit 1; }
	$(PYTHON) $(RTL_DIR)/scripts/send_program.py $(PORT) $(PROG)

clean:
	rm -f program.hex loader.hex payload.txt *.json *.fs *.vvp *.vcd
