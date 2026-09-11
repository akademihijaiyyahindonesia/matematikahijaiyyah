"""NUI's trained side: a small PyTorch model over the letter codex.

hijaiyyah.ai is NUI as an LLM persona -- Hermes/Qwen over Ollama, briefed on
this project and grounded with real documents via CONTEXT. This package is
NUI's other half: an actual trained neural network, whose input embedding
for each of the 28 Hijaiyyah letters is not learned from scratch but taken
from the letter's own measured geometry -- Nuqthah (points), Khat (lines),
Qaws (curves), and the turning pair (Theta-hat, rho) that
cosmic-codex-jim/ and guards.py already established are real, guard-checked
quantities, not an invented feature scheme.

The task these features are tested against is real and non-trivial: does a
sequence of letters, accumulated into a register the way
rtl/programs/letters.hasm actually does it, reach a MAXIMUM-period exomatrix
over GF(2) -- the same primitivity property cosmic-codex-jim/MACHINE.md
measured for Jim and Kha, generalised here to sums rather than single
letters. It is not linearly recoverable from the accumulated vector, so it
is a genuine test of whether the 5-number geometric embedding carries enough
signal, not a task any reasonable representation would solve for free.

See ``README.md`` in this directory for what was measured and what was not.
"""
