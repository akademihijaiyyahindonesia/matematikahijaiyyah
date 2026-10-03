# ============================================================================
# Portal 8888 -- simulation and synthesis measurements, iverilog + vvp + yosys
# ============================================================================
#   make            vectors, every bench, R3 of the reference, the legacy system run
#                   and the Tang Nano 20K wrapper through its UART pins
#   make ref        the software models and attack campaigns (ref/*.py)
#   make synth      yosys synth_gowin -nodsp cell counts per module (no PnR)
#   make vcd        the legacy system run again, dumping every signal
#
# Generated files go to build/ (gitignored). The HMAC engine is the repo's own,
# read from ../rtl -- the folder carries no copy of it.

# -g2012 enables $fatal, which is how a failing testbench exits non-zero.
IVERILOG = iverilog -g2012
VVP      = vvp -n
PY       = python3
B        = build
R        = ../rtl
HMAC     = $(R)/hijaiyyah_hmac.v $(R)/hijaiyyah_sha256_stream.v $(R)/hijaiyyah_sha256_core.v

# The Portal's own design, named once. sim_portal, sim_system and synth all
# elaborate the same thing, and two hand-written copies is exactly how
# sim_system came to miss ingress_parse_v1 and fail with "Unknown module type"
# -- the same way rtl/fpga/gowin/Makefile's source list went stale when
# hcpu_mmio.v and hcpu_trap.v were added to the design and not to the list.
PORTAL_RTL = rtl/hijaiyyah_portal8888.v rtl/hijaiyyah_timestamp.v \
             rtl/ingress_parse_v1.v $(HMAC)

.PHONY: all sim ref synth vcd clean r3 sim_timestamp sim_jim sim_ingress \
        sim_ingress_v1 sim_portal sim_system sim_gowin_top sim_gowin_top_115200 \
        portal8888_synth portal8888_bitstream portal8888_flash

all: sim
sim: sim_timestamp sim_jim sim_ingress sim_ingress_v1 sim_portal r3 sim_system sim_gowin_top

$(B)/.vectors: ref/vectors.py ref/model.py ref/packets.py
	$(PY) ref/vectors.py $(B)
	@touch $@

sim_timestamp:
	@mkdir -p $(B)
	$(IVERILOG) -o $(B)/ts.vvp tb/tb_timestamp.v rtl/hijaiyyah_timestamp.v
	$(VVP) $(B)/ts.vvp

sim_jim: $(B)/.vectors
	$(IVERILOG) -o $(B)/jim.vvp tb/tb_jim.v rtl/jim_sync.v rtl/jim_index.v
	$(VVP) $(B)/jim.vvp

sim_ingress: $(B)/.vectors
	$(IVERILOG) -o $(B)/ingress.vvp tb/tb_ingress.v rtl/ingress_parse.v
	$(VVP) $(B)/ingress.vvp

sim_ingress_v1:
	$(PY) ref/portal_ref.py vec $(B)
	$(IVERILOG) -s tb_ingress_v1 -o $(B)/ingress_v1.vvp tb/tb_ingress_v1.v rtl/ingress_parse_v1.v
	$(VVP) $(B)/ingress_v1.vvp

sim_portal:
	@mkdir -p $(B)
	$(PY) ref/portal_ref.py vec $(B)
	$(IVERILOG) -s tb_portal8888_v1 -o $(B)/p8.vvp tb/tb_portal8888_v1.v $(PORTAL_RTL)
	$(VVP) $(B)/p8.vvp

# The legacy four-corner top (hijaiyyah_portal8888_legacy_unwired, 64-byte
# corner body), kept beside v1 in the same file. The bench itself does not
# judge the tags: portal_sys_check.py recomputes
# every byte with hashlib/hmac and exits non-zero on any mismatch
sim_system:
	@mkdir -p $(B)
	$(PY) ref/portal_sys_keys.py > $(B)/portal_sys_keys.txt
	rm -f $(B)/portal_sys_result.txt
	$(IVERILOG) -o $(B)/ps.vvp tb/tb_portal8888_system.v $(PORTAL_RTL)
	$(VVP) $(B)/ps.vvp $(PLUSARGS)
	$(PY) ref/portal_sys_check.py

r3: sim_portal
	$(PY) ref/r3.py

vcd:
	$(MAKE) sim_system PLUSARGS=+vcd

ref:
	cd ref && $(PY) portal.py && $(PY) scenarios.py && $(PY) campaign.py 300 \
	    && $(PY) attack_prov.py && $(PY) evidence_report.py && $(PY) findmy.py \
	    && $(PY) tstamp.py && $(PY) geo.py

# Cell counts after synth_gowin, before place and route. The Portal top alone
# has more port bits than the board has pins; the placeable slot is the UART
# wrapper below (portal8888_bitstream).
SYN = $(B)/syn
synth:
	@mkdir -p $(SYN)
	yosys -q -p "read_verilog rtl/hijaiyyah_timestamp.v; synth_gowin -nodsp -top hijaiyyah_timestamp; tee -q -o $(SYN)/hijaiyyah_timestamp.stat stat"
	yosys -q -p "read_verilog rtl/jim_sync.v; synth_gowin -nodsp -top jim_sync; tee -q -o $(SYN)/jim_sync.stat stat"
	yosys -q -p "read_verilog rtl/jim_index.v; synth_gowin -nodsp -top jim_index; tee -q -o $(SYN)/jim_index.stat stat"
	yosys -q -p "read_verilog rtl/ingress_parse.v; synth_gowin -nodsp -top ingress_parse; tee -q -o $(SYN)/ingress_parse.stat stat"
	yosys -q -p "read_verilog rtl/ingress_parse_v1.v; synth_gowin -nodsp -top ingress_parse_v1; tee -q -o $(SYN)/ingress_parse_v1.stat stat"
	yosys -q -p "read_verilog rtl/hijaiyyah_portal8888.v rtl/hijaiyyah_timestamp.v rtl/ingress_parse_v1.v $(HMAC); synth_gowin -nodsp -top hijaiyyah_portal8888; tee -q -o $(SYN)/hijaiyyah_portal8888.stat stat"
	yosys -q -p "read_verilog $(HMAC); synth_gowin -nodsp -top hijaiyyah_hmac; tee -q -o $(SYN)/hijaiyyah_hmac.stat stat"
	$(PY) ref/synth_stat.py $(SYN)/*.stat

# -- Tang Nano 20K: the Portal behind a UART, ten pins ------------------------
# fpga/gowin/hijaiyyah_portal8888_gowin_top.v. The pins, the device and the
# constraint file are those of rtl/fpga/gowin/hijaiyyah_hmac_gowin_top.v. The
# bench judges nothing; ref/portal_uart.py recomputes every reply.
GTOP     = hijaiyyah_portal8888_gowin_top
GTOP_RTL = fpga/gowin/$(GTOP).v $(PORTAL_RTL) $(R)/hcpu_uart_rx.v $(R)/hcpu_uart_tx.v
GTB      = tb_hijaiyyah_portal8888_gowin_top
G        = $(B)/gowin
DEVICE   = GW2AR-LV18QN88C8/I7
FAMILY   = GW2A-18C
BOARD    = tangnano20k
CST      = $(R)/fpga/gowin/hcpu_gowin.cst
NEXTPNR    ?= nextpnr-himbaechel
GOWIN_PACK ?= gowin_pack
LOADER     ?= openFPGALoader

# every command of the scenario, at 10 clocks a bit
sim_gowin_top:
	@mkdir -p $(B)
	$(PY) ref/portal_uart.py vec $(B)
	$(IVERILOG) -s $(GTB) -o $(B)/gtop.vvp tb/$(GTB).v $(GTOP_RTL)
	$(VVP) $(B)/gtop.vvp
	$(PY) ref/portal_uart.py check $(B)

# the short scenario at the board's own 115200
sim_gowin_top_115200:
	@mkdir -p $(B)
	$(PY) ref/portal_uart.py vec $(B) short
	$(IVERILOG) -s $(GTB) -P$(GTB).BAUD=115200 -o $(B)/gtop_115200.vvp tb/$(GTB).v $(GTOP_RTL)
	$(VVP) $(B)/gtop_115200.vvp
	$(PY) ref/portal_uart.py check $(B) short

portal8888_synth:
	@mkdir -p $(G)
	yosys -q -p "read_verilog $(GTOP_RTL); synth_gowin -nodsp -top $(GTOP) -json $(G)/$(GTOP).json; tee -q -o $(G)/$(GTOP).stat stat"

$(G)/$(GTOP)_pnr.json: portal8888_synth
	$(NEXTPNR) --json $(G)/$(GTOP).json --write $@ --device $(DEVICE) \
	    --vopt cst=$(CST) --vopt family=$(FAMILY)

portal8888_bitstream: $(G)/$(GTOP)_pnr.json
	$(GOWIN_PACK) -d $(FAMILY) -o $(G)/$(GTOP).fs $<

# Loading the board is a laboratory step, run by a person on the owner's order.
portal8888_flash: portal8888_bitstream
	$(LOADER) -b $(BOARD) $(G)/$(GTOP).fs

clean:
	rm -rf $(B)
