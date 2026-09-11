# NUI, trained: does the letter's own geometry help?

`hijaiyyah.ai` is NUI as a persona over Hermes/Qwen. This is NUI's other
half — an actual trained model — built to test one specific claim: that
decomposing each of the 28 letters into **titik** (points, Nuqthah), **garis**
(lines, Khat), and **lengkung** (curves, Qaws), plus the turning pair
(Theta-hat, rho), is a useful embedding for a network to learn from — not
just a description, a feature representation that is compared against a
same-size trainable baseline on a real task.

Every one of those five numbers is read off the sealed Master Table and
`guards.py` — G1 (`A_N`), G2 (`A_K`), G3 (`A_Q`) and the turning identity
`rho = Theta-hat - U` (Definition 11.2.1, Bab III). Nothing here invents a
feature scheme; `features.py` only reads one that already exists and is
already guard-checked.

**One precision correction the folder `cosmic-codex-jim/` already needed
once, repeated here because it is easy to get wrong again:** 270° is Jim's
*total* turning (Theta-hat), not "its curve value." Jim's own curve
component `U` is 0 — none of its 270° is explained by Qaws at all. Treat
(titik, garis, lengkung) as three independent counts and (theta, rho) as a
separate turning summary.

## The task

`cosmic-codex-jim/MACHINE.md` measured that Jim's and Kha's 5×5 exomatrices,
read as linear maps over GF(2), have **maximum multiplicative order** — 31,
a primitive/maximum-length-LFSR property. That computation
(`hijaiyyah.core.exomatrix.matrix_order`, lifted out of a test-only helper
for this module) generalizes past single letters: accumulate several
letters into a register the way `rtl/programs/letters.hasm` really does it
(`HREG[0] += v(letter)` per letter opcode), and the resulting sum has its
own exomatrix, its own GF(2) period, and its own primitive/not-primitive
answer.

**The task:** given the *set* of letters accumulated so far in a prefix of
a sequence, predict whether the result is primitive. Order does not affect
the label — v18 addition commutes, and guards.py already calls the
guard-valid set "closed under addition" — which is why the model sums a
per-letter embedding rather than using a recurrent encoder: summing is the
actual operation being modeled, not a simplification of one.

This is **not** a task any reasonable representation solves for free.
Primitivity of a characteristic polynomial over GF(2) is a genuinely
nonlinear function of all 25 exomatrix entries; a 5-number linear summary
cannot recover it exactly, so any signal a model finds has to come from
correlation, not exact reconstruction.

## What was measured

`python3 -m hijaiyyah.nui.train` (4,000 random accumulation sequences →
76,822 balanced training prefixes, 17,220 natural-distribution prefixes held
out, plus all 28 prefixes of `letters.hasm`'s own real accumulation order;
500 epochs, Adam, all four models same architecture and hyperparameters,
differing only in embedding):

| | physics (frozen, 5-dim) | baseline-5 (trained) | exomatrix (frozen, 25-dim) | baseline-25 (trained) |
|---|---:|---:|---:|---:|
| trainable parameters | 385 | 525 | 705 | 1,405 |
| natural: always-negative accuracy | 0.955 | 0.955 | 0.955 | 0.955 |
| natural: raw accuracy (threshold 0.5) | 0.741 | 0.669 | 0.459 | 0.703 |
| natural: **calibrated** accuracy | 0.961 | 0.960 | 0.955 | 0.958 |
| natural: calibrated precision | 0.970 | 0.789 | **1.000** | 0.637 |
| natural: calibrated recall | 0.125 | 0.136 | **0.004** | **0.157** |
| real corpus (28 prefixes, 2 positive): calibrated | 0/2 caught | 0/2 caught | 0/2 caught | 0/2 caught |

**exomatrix is the fourth embedding, and it is where CosmicTera and NUI
actually already share code.** `src/hijaiyyah/crypto/cube.py`'s
`build_cube()` stacks each of the 28 letters' full 5×5 exomatrix
(`core.exomatrix.build_exomatrix` — the same function, not a re-derivation)
and `cube_digest()` hashes the result to seed the Ka'bah S-box. Freezing
that same 25-cell structure as an embedding — instead of the 5-number
(titik, garis, lengkung, theta, rho) summary — asks a direct question: does
the material Ka'bah's own cryptography is built from carry more signal for
this unrelated task than the summary does?

**No.** Precision is perfect (1.000 — every positive prediction it makes is
correct) but recall collapses to 0.004: it catches essentially none of the
true positives, the most conservative of all four variants by a wide
margin. A plain *trainable* 25-dimensional embedding with no geometric or
cryptographic prior at all (baseline-25) has the best recall of anything
tested, 0.157. More raw structure, frozen, did not help — capacity and the
freedom to fit mattered more than which specific real quantity supplied the
starting point.

**Calibration, and why it is needed.** Positives (primitive) are ~4.5% of
the natural distribution, but training data is class-balanced 50/50 (see
`dataset.py`) so the model has enough positive examples to learn from at
all. A model trained at a 50% prior and evaluated at 0.5 probability
threshold against a 4.5%-positive population scores *below* the trivial
always-negative rule on raw accuracy (0.74 and 0.67, against 0.955) despite
clearly-above-chance recall — the textbook signature of prior mismatch, not
evidence the features carry nothing. `train.py`'s `prior_correction` applies
the standard analytic log-odds shift for exactly this situation (King &
Zeng's rare-events correction) rather than a threshold hunted for on the
evaluation set.

**What that leaves, honestly:**

- **[CC] The physics embedding measurably helps precision.** 0.970 vs 0.789
  at comparable recall (0.125 vs 0.136), with *fewer* trainable parameters
  (385 vs 525 — the embedding itself costs zero trainable parameters when
  frozen). When this model predicts primitive, it is right 97% of the time.
- **[CC] Both models have low recall.** ~12-14% of true positives are
  caught. A 5-dimensional summed embedding is a real information bottleneck
  against a task whose ground truth depends on all 18 raw components, not
  their three group sums — confirmed directly: a from-scratch experiment
  with a full 18-dimension (uncompressed) embedding, run during development
  and not kept as a permanent variant, performed *worse* on raw accuracy
  than the 5-dim versions before calibration, and the gap did not close
  after it. The bottleneck is the training/architecture regime, not
  specifically the 5-number compression.
- **[EH] The real-corpus check (28 prefixes, 2 positive) caught neither.**
  With ~13% recall on the large natural set, missing 2 out of 2 on a set
  this small is unsurprising — not evidence the model generalizes to real
  programs, and not evidence it does not. Twenty-eight examples with two
  positives cannot support that claim either way; it is reported as what it
  is, a failed catch on the one genuinely real program in this repository
  that exercises the accumulation this task is about.
- **Not claimed:** that this generalizes past GF(2) exomatrix primitivity,
  past the specific 5-number decomposition, or that it says anything about
  letters beyond this one measured, reproducible task.

Reproduce with `pip install .[nui] && python3 -m hijaiyyah.nui.train`. Tests
in `tests/test_ai/test_nui.py` run a scaled-down version (300 sequences, 60
epochs) fast enough for routine test runs; they check that training beats
the naive baseline, not the exact numbers above, which only the full run
produces.

## Fase 1: one trunk, three tasks (`multitask.py`)

`NUI/ROADMAP.md` charts what comes after one classifier. Its first step,
built and measured, not just planned: the same embedding+sum trunk, three
heads instead of one -- `gf2_primitive` (this page's own task, carried
over), `gf5_primitive` (same question, modulus 5 instead of 2 --
`exomatrix.matrix_order(v, 5)`, no identity ties its answer to GF(2)'s),
and `rank` (`exomatrix.gf2_rank`, 0..5 -- a different KIND of question, not
a third yes/no).

**One planned task never got written as code.** Guard validity (G1-G4, T1,
T2) was the first idea for an auxiliary label, dropped after checking --
not assuming -- that every canonical letter passes every guard, and G1-G3
are linear identities (G4 a sum of non-negatives), so ANY accumulation of
canonical letters stays guard-valid: 2,000 random subsets, 100% pass, every
guard, every time. A label that never varies teaches a network nothing.

`python3 -m hijaiyyah.nui.multitask` (4,000 sequences, 500 epochs, balanced
on `gf2_primitive`, natural n=17,220):

| | physics (5, frozen) | baseline-5 (5, trained) | exomatrix (25, frozen) | baseline-25 (25, trained) |
|---|---:|---:|---:|---:|
| trainable parameters | 1,240 | 1,380 | 2,200 | 2,900 |
| `gf2_primitive` precision/recall | 0.970/0.125 | 0.955/0.137 | 1.000/0.004 | 0.536/0.144 |
| `gf5_primitive` precision/recall | 0.000/0.000 | 0.000/0.000 | 0.000/0.000 | **1.000/0.053** |
| `rank` accuracy (always-majority 0.397) | **0.516** | **0.606** | **0.536** | **0.684** |

**Three findings, three different directions:**

- **`rank` is the first real evidence one trunk carries signal across
  genuinely different questions.** All four variants beat the
  always-majority baseline, including `physics` -- 5 frozen numbers that
  were never trained to predict rank at all, only primitivity, yet the
  shared representation still helped a separate head learn it.
- **`gf5_primitive` nearly fails outright on three of four variants** --
  checked directly rather than assumed a calibration bug: raw
  (pre-calibration) probabilities never exceed 0.468 for any example, and
  the separation between positive and negative classes is real but tiny
  (mean 0.084 vs 0.056). Only `baseline-25` -- the most capacity, no prior
  at all -- gets any signal whatsoever. Modulus 5 is genuinely harder for
  this architecture to learn than modulus 2, at this scale.
- **`gf2_primitive` roughly reproduces Fase 0, not identically** -- joint
  training against three losses shifts optimisation dynamics versus
  training alone; `baseline-25`'s precision moves from 0.637 (Fase 0) to
  0.536 here, the rest stay close.

Reproduce with `python3 -m hijaiyyah.nui.multitask`. Tests in
`tests/test_ai/test_nui_multitask.py` (13, including the empirical guard
check above) run at a smaller scale for routine test runs; one of them
caught a wrong assumption of its own while being written -- Jim's own
exomatrix rank was assumed to be full rank (5) and is actually 4, fixed by
checking rather than asserting.
