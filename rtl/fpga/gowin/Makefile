# ============================================================================
# HCPU on the Tang Nano 20K — open-source Gowin flow
# (c) 2026 Maulana Amratulloh
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
#
# The board is the Tang Nano 20K (GW2AR-LV18QN88C8/I7), 20,736 LUT4: the
# design routes there at 67%. See cosmictera-build/ROADMAP.md for how this
# board was chosen and what is still open.

DEVICE   = GW2AR-LV18QN88C8/I7
FAMILY   = GW2A-18C
BOARD    = tangnano20k

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
#   gowin_pack        pip install apycula, or the copy oss-cad-suite ships --
#                     found the same way as nextpnr below. Looking only on
#                     PATH made `make tools` report it MISSING on the machine
#                     that built every bitstream this repo has flashed.
#   openFPGALoader    brew install openfpgaloader
#   nextpnr-himbaechel  not in Homebrew and not quick to build -- it comes from
#                     a prebuilt oss-cad-suite, referenced by path rather than
#                     by sourcing its environment, because that environment
#                     shadows the yosys and python this project already uses.
OSS_CAD  ?= $(HOME)/opt/oss-cad-suite
NEXTPNR  ?= $(firstword $(wildcard $(OSS_CAD)/bin/nextpnr-himbaechel) \
                        $(shell command -v nextpnr-himbaechel 2>/dev/null))
GOWIN_PACK ?= $(firstword $(shell command -v gowin_pack 2>/dev/null) \
                          $(wildcard $(OSS_CAD)/bin/gowin_pack))
LOADER     ?= openFPGALoader

# The wrapper plus every hcpu_*.v, found rather than listed. The hand-written
# list here went stale exactly the way rtl/tb/Makefile's did: hcpu_mmio.v and
# hcpu_trap.v were added to the design and not to this list, so `make sim`,
# `make synth` and `make bitstream` all failed with "Unknown module type" --
# and would have failed on the day the board arrived, not before.
SOURCES  = hcpu_gowin_top.v $(wildcard $(RTL_DIR)/hcpu_*.v)

.PHONY: all sim synth bitstream flash bridge send clean \
        display_synth display_bitstream display_flash \
        sim_kabah kabah_synth kabah_bitstream kabah_flash \
        sim_hmac hmac_synth hmac_bitstream hmac_flash \
        hdmi_synth hdmi_bitstream hdmi_flash hdmi_bridge \
        kabah_hdmi_synth kabah_hdmi_bitstream kabah_hdmi_flash

# HDMI wrappers are compile/synthesis experiments only. They are deliberately
# not part of `bitstream` or `flash` until nextpnr can pack the GW2AR
# differential TLVDS outputs without aborting.

all: sim

# ── Program image ───────────────────────────────────────────────
# Written as plain ASCII. The Xilinx copy of this file was UTF-16, which
# $readmemh refuses outright — the instruction memory stayed uninitialised and
# nothing said so.
# program.hex follows the VALUE of PROGRAM, not only its mtime. With only
# `program.hex: $(PROGRAM)`, `make bridge` compared a test_bsm image against
# loader.hasm's timestamp, found the image newer, and called it up to date --
# so the "loader" bitstream would have baked test_bsm and ignored the wire.
# Measured: `make -n PROGRAM=../../programs/loader.hasm program.hex` answered
# "up to date" over a 9-word test_bsm image. The stamp changes only when the
# path does, which is exactly when the image has to be rebuilt.
program.stamp: FORCE
	@echo "$(PROGRAM)" | cmp -s - $@ || echo "$(PROGRAM)" > $@

#
# A PROGRAM that is already an image (.hex) is copied, not assembled. The image
# a bench ran -- rtl/tb/shell_persist.hex, a shell with a probe injected by
# rtl/scripts/inject_probe.py -- has no .hasm that assembles to it, and asm2hex
# fed a hex answers `unknown mnemonic '04500000'`. Copying keeps the board's
# image byte-identical to the one the bench verified.
program.hex: $(PROGRAM) program.stamp
ifeq ($(suffix $(PROGRAM)),.hex)
	cp $< $@
else
	$(PYTHON) $(RTL_DIR)/scripts/asm2hex.py $< > $@
endif

.PHONY: FORCE
FORCE:

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

# ── Ka'bah wrapper: same board, different top ───────────────────
# hijaiyyah_kabah_gowin_top.v narrows hijaiyyah_kabah_top.v's 1,665-bit
# interface to the same 10 pins hcpu_gowin_top.v uses -- clk_27m, btn_rst_n,
# uart_rxd, uart_txd, led[5:0] -- so it shares this Makefile's DEVICE,
# FAMILY, BOARD and even hcpu_gowin.cst verbatim; only TOP and its sources
# differ, no wrapper is written for a second board.
KABAH_TOP     = hijaiyyah_kabah_gowin_top
# Not $(wildcard $(RTL_DIR)/hijaiyyah_*.v): that would also pull in
# hijaiyyah_ramal_core.v, hijaiyyah_sbox_router.v and hijaiyyah_wave.v --
# retired or alternate implementations this wrapper does not instantiate
# (see their own file headers -- ramal_core and sbox_router are the designs
# ramal_impulse and sbox replaced). hcpu_gowin_top.v's own wildcard is safe
# because HCPU has no such retired siblings under hcpu_*.v; Ka'bah's family
# does, so this list is written out instead, matching exactly what
# tests/test_integrity/test_place_and_route.py already builds and runs.
KABAH_SOURCES = $(KABAH_TOP).v $(RTL_DIR)/hijaiyyah_kabah_top.v \
                $(RTL_DIR)/hijaiyyah_deserialiser.v $(RTL_DIR)/hijaiyyah_jamrah_gate.v \
                $(RTL_DIR)/hijaiyyah_node_counter.v $(RTL_DIR)/hijaiyyah_sponge.v \
                $(RTL_DIR)/hijaiyyah_ramal_impulse.v $(RTL_DIR)/hijaiyyah_rotate_core.v \
                $(RTL_DIR)/hijaiyyah_linear.v $(RTL_DIR)/hijaiyyah_sbox.v \
                $(RTL_DIR)/hijaiyyah_round_constants.v \
                $(RTL_DIR)/hcpu_uart_rx.v $(RTL_DIR)/hcpu_uart_tx.v

# Layer 3 in the UART slot (owner, 3 October 2026): the slot's own build
# defines KABAH_WITH_HMAC, and the wrapper then signs each reply with
# HMAC-SHA256 under a public test key. Ka'bah over HDMI and the combined top
# read KABAH_SOURCES and define nothing, so they build the wrapper as it was.
#
# It is done with a target-specific KABAH_SOURCES, added below the list and
# touching no line that was here before: for these two targets alone the list
# is led by kabah_with_hmac.vh, which defines the macro for the files read
# after it, and followed by the three layer-3 sources. The recipes of
# sim_kabah and kabah_synth are the lines they always were. A -D flag could
# not do it: iverilog takes none after its first source file.
KABAH_L3_DEFINE  = kabah_with_hmac.vh
KABAH_L3_SOURCES = $(RTL_DIR)/hijaiyyah_hmac.v $(RTL_DIR)/hijaiyyah_sha256_stream.v \
                   $(RTL_DIR)/hijaiyyah_sha256_core.v
sim_kabah kabah_synth: KABAH_SOURCES := $(KABAH_L3_DEFINE) $(KABAH_SOURCES) $(KABAH_L3_SOURCES)

# No program.hex: the wrapper's protocol is fixed (128 bytes in, 200 out),
# not a loaded program. But the testbench does $readmemh two want-vectors by
# a path relative to the repo root ("rtl/tb/kabah_uart_want.hex") -- it was
# only ever run that way, from test_place_and_route.py's subprocess with
# cwd=ROOT. This Makefile runs from rtl/fpga/gowin/, so the vvp step has to
# change to the repo root itself rather than leave the path broken.
sim_kabah:
	iverilog -g2012 -I $(RTL_DIR) -o tb_kabah_gowin_top.vvp \
	    $(RTL_DIR)/tb/tb_hijaiyyah_kabah_gowin_top.v $(KABAH_SOURCES)
	cd $(RTL_DIR)/.. && vvp rtl/fpga/gowin/tb_kabah_gowin_top.vvp

kabah_synth:
	yosys -p "read_verilog -I $(RTL_DIR) $(KABAH_SOURCES); \
	          synth_gowin $(YOSYS_FLAGS) -top $(KABAH_TOP) -json $(KABAH_TOP).json"

$(KABAH_TOP)_pnr.json: kabah_synth
	@test -n "$(NEXTPNR)" || { echo "nextpnr-himbaechel not found."; \
	    echo "Set OSS_CAD=<path to oss-cad-suite> or put it on PATH."; exit 1; }
	$(NEXTPNR) --json $(KABAH_TOP).json --write $@ \
	    --device $(DEVICE) --vopt cst=hcpu_gowin.cst \
	    --vopt family=$(FAMILY)

kabah_bitstream: $(KABAH_TOP)_pnr.json
	$(GOWIN_PACK) -d $(FAMILY) -o $(KABAH_TOP).fs $<

kabah_flash: kabah_bitstream
	$(LOADER) -b $(BOARD) $(KABAH_TOP).fs

# ── HMAC-SHA256: Ka'bah lapis 3 in logic, one bitstream ──────────
# The layer that carries Ka'bah's security (HMAC-SHA256, until now only
# hmac.new in src/hijaiyyah/crypto/signing.py) as its own 10-pin slot, the
# same shape as kabah_*: same constraint file, same UART, same reset. The
# three benches run from the repo root because they read their golden
# vectors from rtl/tb/ (rtl/tb/gen_hmac_vectors.py writes them). They are
# not in `make -C rtl/tb all`, exactly like sim_kabah, so the counted RTL
# assertion total is untouched; tests/test_integrity/test_hmac_rtl.py runs them.
HMAC_TOP     = hijaiyyah_hmac_gowin_top
HMAC_SOURCES = $(HMAC_TOP).v $(RTL_DIR)/hijaiyyah_hmac.v \
               $(RTL_DIR)/hijaiyyah_sha256_stream.v $(RTL_DIR)/hijaiyyah_sha256_core.v \
               $(RTL_DIR)/hcpu_uart_rx.v $(RTL_DIR)/hcpu_uart_tx.v

sim_hmac:
	iverilog -g2012 -o tb_hijaiyyah_sha256_stream.vvp \
	    $(RTL_DIR)/tb/tb_hijaiyyah_sha256_stream.v \
	    $(RTL_DIR)/hijaiyyah_sha256_stream.v $(RTL_DIR)/hijaiyyah_sha256_core.v
	iverilog -g2012 -o tb_hijaiyyah_hmac.vvp \
	    $(RTL_DIR)/tb/tb_hijaiyyah_hmac.v $(RTL_DIR)/hijaiyyah_hmac.v \
	    $(RTL_DIR)/hijaiyyah_sha256_stream.v $(RTL_DIR)/hijaiyyah_sha256_core.v
	iverilog -g2012 -o tb_hijaiyyah_hmac_gowin_top.vvp \
	    $(RTL_DIR)/tb/tb_hijaiyyah_hmac_gowin_top.v $(HMAC_SOURCES)
	cd $(RTL_DIR)/.. && vvp rtl/fpga/gowin/tb_hijaiyyah_sha256_stream.vvp
	cd $(RTL_DIR)/.. && vvp rtl/fpga/gowin/tb_hijaiyyah_hmac.vvp
	cd $(RTL_DIR)/.. && vvp rtl/fpga/gowin/tb_hijaiyyah_hmac_gowin_top.vvp

hmac_synth:
	yosys -p "read_verilog -I $(RTL_DIR) $(HMAC_SOURCES); \
	          synth_gowin $(YOSYS_FLAGS) -top $(HMAC_TOP) -json $(HMAC_TOP).json"

$(HMAC_TOP)_pnr.json: hmac_synth
	@test -n "$(NEXTPNR)" || { echo "nextpnr-himbaechel not found."; \
	    echo "Set OSS_CAD=<path to oss-cad-suite> or put it on PATH."; exit 1; }
	$(NEXTPNR) --json $(HMAC_TOP).json --write $@ \
	    --device $(DEVICE) --vopt cst=hcpu_gowin.cst \
	    --vopt family=$(FAMILY)

hmac_bitstream: $(HMAC_TOP)_pnr.json
	$(GOWIN_PACK) -d $(FAMILY) -o $(HMAC_TOP).fs $<

hmac_flash: hmac_bitstream
	$(LOADER) -b $(BOARD) $(HMAC_TOP).fs

# ── HDMI: HCPU + loader + 1280x720 over TMDS, one bitstream ─────
# The recipe that built the bitstream the board ran with a monitor lit --
# rack slot 3, rtl/scripts/rack.py. It existed only as a remembered command
# (it wrote hdmi.json and hdmi_pnr.json, and those names are kept), and
# `make clean` deletes *.fs, so until this target a clean tree could not
# rebuild the one slot that drives a screen. Same tools and flags as
# `bitstream`; only the top, its extra sources and the constraint differ.
# The slot takes programs over the wire, so it is normally built with the
# loader baked in: `make hdmi_bridge`.
HDMI_TOP     = hcpu_hdmi_top
HDMI_SOURCES = $(HDMI_TOP).v dvi_tx_open.v tmds_rpll.v $(SOURCES)

# The dashboard layout and its field addresses are generated, never edited
# and never copied: one image, read from rtl/ by a path parameter. The .vh is
# `included by hcpu_dashboard.v, so it has to exist before yosys reads a line.
$(RTL_DIR)/hcpu_dashboard.hex $(RTL_DIR)/hcpu_dashboard_pos.vh: \
		$(RTL_DIR)/scripts/gen_dashboard.py
	$(PYTHON) $< >/dev/null

# Option A (owner, 5 November 2026): the HDMI slot instantiates
# hcpu_gowin_core #(.USE_DSP(1)) and synthesises without -nodsp so the
# 14-lane 8x8 MAC in hcpu_codex_alu and 32x32 multiply in hcpu_mul map to
# hard MULT9X9/MULT36X36 DSP blocks, freeing LUT4 headroom for the M5.2B
# display pipeline. Apycula 0.30+ in oss-cad-suite packs MULT9X9 cleanly.
hdmi_synth: YOSYS_FLAGS =
hdmi_synth: program.hex $(RTL_DIR)/hcpu_dashboard.hex $(RTL_DIR)/hcpu_dashboard_pos.vh
	yosys -p "read_verilog -I $(RTL_DIR) $(HDMI_SOURCES); \
	          synth_gowin $(YOSYS_FLAGS) -top $(HDMI_TOP) -json hdmi.json"

hdmi_pnr.json: hdmi_synth
	@test -n "$(NEXTPNR)" || { echo "nextpnr-himbaechel not found."; \
	    echo "Set OSS_CAD=<path to oss-cad-suite> or put it on PATH."; exit 1; }
	$(NEXTPNR) --json hdmi.json --write $@ \
	    --device $(DEVICE) --vopt cst=hcpu_hdmi.cst \
	    --vopt family=$(FAMILY)

hdmi_bitstream: hdmi_pnr.json
	$(GOWIN_PACK) -d $(FAMILY) -o $(HDMI_TOP).fs $<

hdmi_flash: hdmi_bitstream
	$(LOADER) -b $(BOARD) $(HDMI_TOP).fs

hdmi_bridge:
	$(MAKE) PROGRAM=$(RTL_DIR)/programs/loader.hasm hdmi_flash
	$(MAKE) PROGRAM=$(RTL_DIR)/programs/test_bsm.hasm program.hex

# ── M5.3a: the display node, on its own die ─────────────────────
# No HCPU inside. Two attempts at putting the dashboard in the CPU's
# placement were refused by nextpnr -- 16,882 and 16,849 LUT4 against a
# control of 15,933 that routes cleanly -- so the display became its own
# node. Shares hcpu_hdmi.cst: this top has no uart, no led and no card, and
# nextpnr reports those constraints as Info and carries on.
DISPLAY_TOP     = cosmictera_display_top
DISPLAY_SOURCES = $(DISPLAY_TOP).v dvi_tx_open.v tmds_rpll.v \
                  $(RTL_DIR)/hcpu_video_timing.v $(RTL_DIR)/hcpu_page_key.v \
                  $(RTL_DIR)/hcpu_layout_rom.v $(RTL_DIR)/hcpu_compositor.v \
                  $(RTL_DIR)/hcpu_font_rom.v $(RTL_DIR)/hcpu_text_render.v

display_synth: $(RTL_DIR)/hcpu_display.hex $(RTL_DIR)/hcpu_dashboard_pos.vh
	yosys -p "read_verilog -I $(RTL_DIR) $(DISPLAY_SOURCES); \
	          synth_gowin $(YOSYS_FLAGS) -top $(DISPLAY_TOP) -json display.json"

display_pnr.json: display_synth
	$(NEXTPNR) --json display.json --write $@ \
	    --device $(DEVICE) --vopt cst=hcpu_hdmi.cst \
	    --vopt family=$(FAMILY)

display_bitstream: display_pnr.json
	$(GOWIN_PACK) -d $(FAMILY) -o $(DISPLAY_TOP).fs $<

display_flash: display_bitstream
	$(LOADER) -b $(BOARD) $(DISPLAY_TOP).fs

$(RTL_DIR)/hcpu_display.hex: $(RTL_DIR)/scripts/gen_dashboard.py
	$(PYTHON) $< >/dev/null

# ── Ka'bah over HDMI ────────────────────────────────────────────
# Never built until this target existed. First build, 11 September 2026:
# placed, routed and packed in 944 s, zero TLVDS cells, and the four TMDS
# IO cells carried exactly the names kabah_hdmi.cst constrains. Flashed, it
# ran Ka'bah correctly over the wire -- 2/2 frames, 400/400 bytes matching
# cube.py. Same video path as hcpu_hdmi_top.v around the Ka'bah wrapper
# instead of the HCPU one; no program.hex, for the same reason
# kabah_bitstream has none.
KABAH_HDMI_TOP     = kabah_hdmi_top
KABAH_HDMI_SOURCES = $(KABAH_HDMI_TOP).v dvi_tx_open.v tmds_rpll.v \
                     $(RTL_DIR)/hcpu_video_timing.v $(KABAH_SOURCES)

kabah_hdmi_synth:
	yosys -p "read_verilog -I $(RTL_DIR) $(KABAH_HDMI_SOURCES); \
	          synth_gowin $(YOSYS_FLAGS) -top $(KABAH_HDMI_TOP) -json kabah_hdmi.json"

kabah_hdmi_pnr.json: kabah_hdmi_synth
	@test -n "$(NEXTPNR)" || { echo "nextpnr-himbaechel not found."; \
	    echo "Set OSS_CAD=<path to oss-cad-suite> or put it on PATH."; exit 1; }
	$(NEXTPNR) --json kabah_hdmi.json --write $@ \
	    --device $(DEVICE) --vopt cst=kabah_hdmi.cst \
	    --vopt family=$(FAMILY)

kabah_hdmi_bitstream: kabah_hdmi_pnr.json
	$(GOWIN_PACK) -d $(FAMILY) -o $(KABAH_HDMI_TOP).fs $<

kabah_hdmi_flash: kabah_hdmi_bitstream
	$(LOADER) -b $(BOARD) $(KABAH_HDMI_TOP).fs

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
# program.hex is a sealed, tracked board image (see .gitignore beside this
# file): the CosmicTera manifest seals it and check_board_hex re-assembles it
# from PROGRAM's default. Baking the loader rewrites it, so every target that
# does puts the sealed image back after flashing -- asm2hex is deterministic,
# and regenerating the default program was measured byte-identical to the
# committed file. This never came up while `make bridge` was broken: with
# only an mtime to go on it called program.hex up to date and baked test_bsm
# instead. Fixed, it really wrote the loader image -- and the wrapper
# simulation read that and printed nothing.
bridge:
	$(MAKE) PROGRAM=$(RTL_DIR)/programs/loader.hasm flash
	$(MAKE) PROGRAM=$(RTL_DIR)/programs/test_bsm.hasm program.hex

# Send a program to a board already running the loader:
#     make send PORT=/dev/tty.usbserial-X PROG=../../programs/trap_timer.hasm
PORT ?=
PROG ?= $(RTL_DIR)/programs/trap_timer.hasm
send:
	@test -n "$(PORT)" || { echo "set PORT=<serial device>"; exit 1; }
	$(PYTHON) $(RTL_DIR)/scripts/send_program.py $(PORT) $(PROG)

clean:
	rm -f program.hex program.stamp loader.hex payload.txt *.json *.fs *.vvp *.vcd
