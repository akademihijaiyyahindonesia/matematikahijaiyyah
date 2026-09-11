#!/usr/bin/env python3
"""The NUI pipeline, runnable directly from this folder: python3 NUI/pipeline.py

Not a copy of the library -- this script imports the real code from
src/hijaiyyah/nui/ (needs `pip install .[nui]` for PyTorch) and walks
through every stage out loud, so "where is the program" has a single,
concrete answer: run this file.

    Stage 1  FEATURES    each of the 28 letters -> 5 numbers: titik, garis,
                          lengkung, theta, rho (Nuqthah/Khat/Qaws/Theta-hat/
                          rho, read from the sealed Master Table)
    Stage 2  DATASET      real letter accumulation (HREG[0] += v(letter),
                          exactly rtl/programs/letters.hasm), labelled by
                          real GF(2) exomatrix primitivity
    Stage 3  MODEL        multihot(28) -> embedding -> sum -> MLP -> logit,
                          four embedding variants (physics, exomatrix,
                          baseline-5, baseline-25)
    Stage 4  TRAIN & EVAL train all four, calibrate for the true ~4.5%
                          positive rate, report honestly
    Stage 5  CLOCKWORK    node-by-node, not a neural network -- one letter's
                          own opcode per clock tick, GF(2) matrix
                          composition, squeezed to one true/false bit at
                          the end (see NUI/ROADMAP.md's "clockwork" and
                          "atom" sections); closes with freeze_load(),
                          the loader's wire protocol mocked so the same
                          physical claim tb_gowin_loader_nui.v proves in
                          seconds checks again in milliseconds

Full run: 4,000 sequences, 500 epochs per variant, ~15-20s. Use --quick for
a fast 20-second sanity pass through all four stages instead (a few hundred
sequences, 60 epochs) -- illustrative, not the numbers NUI/README.md quotes.
Stage 5 does not scale with --quick; it is two letters, deterministic, the
same regardless.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hijaiyyah.hisa.assembler import assemble
from hijaiyyah.nui.atom import atom_for
from hijaiyyah.nui.clockwork import automate, channels, rank_permutations, run_rack
from hijaiyyah.nui.dataset import Dataset, Example, build_dataset
from hijaiyyah.nui.features import all_letter_features
from hijaiyyah.nui.freeze import (
    HCPU_CLK_HZ,
    UART_BAUD,
    bit_period_seconds,
    clock_period_seconds,
    clocks_per_uart_bit,
    executed_letters,
    freeze_load,
    mock_wire,
    rack_heartbeat_clocks,
    rack_heartbeat_seconds,
    uart_bit_midpoint_clocks,
    wire_bytes_per_second,
    wire_seconds,
)
from hijaiyyah.nui.model import LetterAccumulatorNet, multihot
from hijaiyyah.nui.rack import RACK, chip_for
from hijaiyyah.nui.train import (
    EXOMATRIX_DIM,
    PHYSICS_DIM,
    prior_correction,
    report,
    train_one,
)


def stage1_features() -> None:
    print("── Stage 1: FEATURES ──────────────────────────────────────")
    features = all_letter_features()
    for ch in ("ا", "ج", "خ"):  # Alif, Jim, Kha -- the letters this repo
        f = features[ch]        # already has other measured facts about
        print(f"  {ch}  titik={f.titik} garis={f.garis} lengkung={f.lengkung} "
              f"theta={f.theta} ({f.theta * 90}°) rho={f.rho}")
    print(f"  ... {len(features)} letters total, read from the sealed Master Table\n")


def stage2_dataset(sequences: int) -> Tuple[Dataset, float]:
    print("── Stage 2: DATASET ───────────────────────────────────────")
    dataset = build_dataset(sequences=sequences, seed=0)
    natural_rate = sum(e.label for e in dataset.natural) / len(dataset.natural)
    print(f"  {len(dataset.train)} balanced training examples")
    print(f"  {len(dataset.natural)} natural-distribution examples "
          f"({natural_rate:.1%} positive -- primitive is genuinely rare)")
    print(f"  {len(dataset.real_corpus)} prefixes of rtl/programs/letters.hasm's "
          f"own real accumulation order\n")
    return dataset, natural_rate


def stage3_model() -> None:
    print("── Stage 3: MODEL ─────────────────────────────────────────")
    net = LetterAccumulatorNet(kind="physics")
    demo = Example(letter_indices=(4, 6), label=True)  # Jim, Kha
    logit = net(multihot([demo]))
    print(f"  physics embedding: {PHYSICS_DIM} dims, frozen, from Stage 1's numbers")
    print(f"  exomatrix embedding: {EXOMATRIX_DIM} dims, frozen, from "
          f"core.exomatrix.build_exomatrix -- what crypto/cube.py seeds the "
          f"Ka'bah S-box from")
    print(f"  forward(Jim + Kha) -> raw logit {logit.item():+.3f} "
          f"(untrained, illustrative only)\n")


def stage4_train_and_eval(dataset: Dataset, natural_rate: float, epochs: int) -> None:
    print("── Stage 4: TRAIN & EVAL ──────────────────────────────────")
    bias = prior_correction(natural_rate)
    print(f"  prior-correction bias: {bias:+.3f} "
          f"(trained at 50% positive, natural is {natural_rate:.1%})")

    physics_model = train_one(kind="physics", dataset=dataset, epochs=epochs)
    report("physics (frozen, 5-dim geometric)", physics_model, dataset, bias=bias)

    baseline5_model = train_one(kind="baseline", embed_dim=PHYSICS_DIM,
                                 dataset=dataset, epochs=epochs)
    report("baseline-5 (trained, 5-dim random init)", baseline5_model, dataset, bias=bias)

    exomatrix_model = train_one(kind="exomatrix", dataset=dataset, epochs=epochs)
    report("exomatrix (frozen, 25-dim -- Ka'bah's S-box seed structure)",
           exomatrix_model, dataset, bias=bias)

    baseline25_model = train_one(kind="baseline", embed_dim=EXOMATRIX_DIM,
                                  dataset=dataset, epochs=epochs)
    report("baseline-25 (trained, 25-dim random init)", baseline25_model, dataset, bias=bias)


def stage5_clockwork() -> None:
    """Not a neural network -- no weights, nothing trained. A deterministic
    node-by-node mechanism (NUI/ROADMAP.md calls this "clockwork"): each
    node is one letter's own address (opcode -- the same ROM address real
    HCPU silicon indexes with, nui.atom), clocked one at a time in sequence
    order, never all at once the way an LLM's attention reads a whole
    sequence. What comes out the end is not a matrix or a probability, a
    single true/false bit -- squeezed out, not predicted. This stage is a
    demonstration; NUI/ROADMAP.md's own wording is that it becomes a
    wrapper later, the same role hcpu_gowin_top.v plays over hcpu_top.v --
    a narrow, clean interface over the mechanism, not the mechanism itself.
    """
    print("── Stage 5: CLOCKWORK -- rack, chip, node, channel, bitstream ──")
    print(f"  rack: {len(RACK)} chips, Master Table order -- each chip is one "
          f"node (address) carrying its own point/line/curve data")
    j = chip_for("ج")
    print(f"  chip 'ج': node opcode={hex(j.opcode)}  point={j.point} line={j.line} "
          f"curve={j.curve} theta={j.theta} rho={j.rho}")

    letters = ("ج", "خ", "م")
    a = automate(letters, ground="primitive")
    root = atom_for(a.boot_char)
    print(f"  root (boot node): {a.boot_char}  opcode={hex(root.opcode)}  "
          f"(same ROM address as real HCPU silicon -- nui.atom)")
    for tick in a.ticks:
        print(f"  clock tick {tick.step}: node={tick.char} opcode={hex(tick.opcode)}  "
              f"rank={tick.rank} full_rank={tick.full_rank} primitive={tick.primitive}")
    for ch in channels(a.ticks):
        print(f"  channel: {ch.from_node} -> {ch.to_node}")
    print(f"  emit (bitstream out, one bit): ground={a.ground!r} -> {a.emitted}")

    rack_ticks = run_rack()
    rack_primitive = sum(1 for t in rack_ticks if t.primitive)
    print(f"  run_rack(): all {len(rack_ticks)} chips, one canonical clock run, "
          f"Master Table order -- {rack_primitive}/{len(rack_ticks)} ticks "
          f"land on a primitive running state")
    print("  compose_step: GF(2) matrix multiply, no HCPU instruction -- versus "
          "nui_embedding.hasm's v18 SUM (L_<letter>/CGET/ADD, real HCPU opcodes)")

    root = Path(__file__).resolve().parents[1] / "rtl" / "programs" / "nui_embedding.hasm"
    start = time.perf_counter()
    machine = freeze_load(root.read_text(encoding="utf-8"), base_dir=root.parent)
    elapsed = time.perf_counter() - start
    print(f"  freeze_load(nui_embedding.hasm): loader's own wire protocol, mocked -- "
          f"no RTL simulator, no real clock -- output={machine.output}, "
          f"imem_waddr={machine.imem_waddr} ({elapsed * 1000:.1f} ms, versus seconds "
          f"for rtl/tb/tb_gowin_loader_nui.v's real bit-serial UART simulation)")

    words = assemble(root.read_text(encoding="utf-8"), base_dir=root.parent)
    stream_bytes = len(mock_wire(words))
    real_seconds = wire_seconds(stream_bytes)
    print(f"  loader boosting -- real wire speed (rtl/hcpu_uart_rx.v, "
          f"{wire_bytes_per_second():.0f} bytes/s @ 115200 baud, 8N1): "
          f"{stream_bytes} bytes would take {real_seconds * 1000:.2f} ms over the "
          f"real board's UART, versus the {elapsed * 1000:.1f} ms freeze_load just "
          f"took in Python -- that gap IS the dim/lit distinction: interpreter speed "
          f"is not a claim about Hz, the real wire's Hz is computed here directly, "
          f"not measured")

    ratio = clocks_per_uart_bit()
    print(f"  signal pulling, one level down: one real UART bit holds its level for "
          f"{bit_period_seconds() * 1e6:.2f} us @ {UART_BAUD} baud, but one real HCPU "
          f"clock edge (rtl/fpga/gowin/hcpu_gowin_top.v's own {HCPU_CLK_HZ:,} Hz "
          f"crystal) takes only {clock_period_seconds() * 1e9:.1f} ns -- {ratio}x "
          f"faster, the exact DIVISOR rtl/hcpu_uart_rx.v samples each bit's middle "
          f"with. That ratio is the real 'cosmic speed' gap in this system: not a "
          f"figure of speech, a number computed from the same two constants the "
          f"chip itself divides.")
    print("  step deliberately NOT taken: turning freeze_load's own step count into "
          "a boot-execution latency by multiplying it against a clock period. "
          "hisa/machine.py's own REG_COUNTER comment says why not -- this interpreter "
          "does not model the pipeline's timing, so that number belongs to real "
          "hardware's own CYCLES= UART report (hcpu_gowin_top.v), not to Python")

    midpoint = uart_bit_midpoint_clocks()
    heartbeat_clocks = rack_heartbeat_clocks()
    heartbeat_seconds = rack_heartbeat_seconds()
    print(f"  clocking speed test -- midpoint sampling (rtl/hcpu_uart_rx.v's own HALF "
          f"= DIVISOR/2, 'so the first sample lands in the middle of the start bit'): "
          f"clock {midpoint} of {clocks_per_uart_bit()} into every real UART bit")
    print(f"  rack heartbeat: all {len(RACK)} nodes, one real byte each, back to back "
          f"over the wire -- {len(RACK)} x 10 bits/byte x {clocks_per_uart_bit()} "
          f"clocks/bit = {heartbeat_clocks:,} real HCPU clock clicks "
          f"({heartbeat_seconds * 1000:.3f} ms), versus wire_seconds()'s idealised "
          f"{wire_seconds(len(RACK)) * 1000:.3f} ms -- close but not identical, "
          f"because real hardware counts whole clock clicks, not fractional baud")
    total_bits = heartbeat_clocks // ratio
    print(f"  ...and dividing that back out by the cosmic speed ratio ({ratio}x) "
          f"recovers exactly the bit count the byte/bit counting started from: "
          f"{heartbeat_clocks:,} clocks / {ratio} clocks-per-bit = {total_bits} bits "
          f"== {len(RACK)} bytes x 10 bits/byte, exactly -- the byte/bit count and "
          f"the cosmic-speed ratio are two readings of the same latency, not two "
          f"different numbers that happen to agree")

    letters_hasm = Path(__file__).resolve().parents[1] / "rtl" / "programs" / "letters.hasm"
    letters_machine = freeze_load(letters_hasm.read_text(encoding="utf-8"),
                                   base_dir=letters_hasm.parent)
    fired = executed_letters(letters_machine)
    order_survived = fired[-len(RACK):] == [c.char for c in RACK]
    print(f"  does the rack's order survive the wire? freeze_load(letters.hasm) -- "
          f"{len(fired)} letters actually fired (read off machine.trace, not the "
          f"source), last {len(RACK)} == RACK's own Master Table order: "
          f"{order_survived} -- a wrong byte order, write, or ERET handoff would "
          f"show up here as a scrambled sequence even if the final H0 (order-"
          f"insensitive addition) still looked fine")

    scores = rank_permutations(count=1000, seed=0)
    zero_final_rank = sum(1 for s in scores if s.final_rank == 0)
    top = scores[0]
    print(f"  rank_permutations(): 1000 random orderings of the rack's own 28 letters, "
          f"ranked by full-rank ticks -- top score {top.full_rank_ticks} full_rank "
          f"ticks, {top.primitive_ticks} primitive ticks, final_rank={top.final_rank}; "
          f"{zero_final_rank}/1000 orderings end at final_rank 0 (same as "
          f"run_rack()'s own Master Table order) -- composing all 28 exomatrices "
          f"drives the running GF(2) matrix singular almost regardless of order\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true",
                         help="fast illustrative pass (300 sequences, 60 epochs) "
                              "instead of the full 4000/500 run")
    args = parser.parse_args()

    sequences = 300 if args.quick else 4000
    epochs = 60 if args.quick else 500

    stage1_features()
    dataset, natural_rate = stage2_dataset(sequences)
    stage3_model()
    stage4_train_and_eval(dataset, natural_rate, epochs)
    stage5_clockwork()


if __name__ == "__main__":
    main()
