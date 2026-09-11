# Hybit Local AI

`hybit-ai` runs small HC-style programs against an Ollama model on the local
machine. It does not require an API key or a cloud service.

## NUI: the persona both local models run under

Every `.hcai` program that does not specify its own `SYSTEM` line gets the
same default persona, **NUI (Natural Universal Intelligence)** — not a
narrow hybit-only assistant, but one briefed on the whole stack: the
mathematics (the 28-letter Master Table and its 18-dimensional hybit
vector), the language and machine (HISA, HCPU), the system software
(H-Kernel, HOS), and the cryptography (Ka'bah). The exact text lives in
`HybitAIProgram`'s `system` default in
[`src/hijaiyyah/ai/runtime.py`](../src/hijaiyyah/ai/runtime.py) — read it
there rather than here, so this doc cannot drift from the code that actually
sends it.

Two local models carry it, checked with `ollama list`:

- `hermes3:8b` — [`examples/local_ai.hcai`](../examples/local_ai.hcai), a
  question about the mathematics.
- `qwen3-coder:30b` — [`examples/qwen_local_ai.hcai`](../examples/qwen_local_ai.hcai),
  a question that reaches into the RTL/program side, since that half of
  NUI's mandate is what a coder model is best placed to answer.

Both examples spell the persona out explicitly in their own `SYSTEM` line
rather than relying on the code default, in keeping with this program format
being self-contained and auditable on its own.

### CONTEXT: what makes the persona true rather than aspirational

A paragraph describing NUI's mandate is not the same thing as NUI having
studied anything. Asked about Hybit with no `CONTEXT` loaded, `hermes3:8b`
answered honestly that it had no file access and needed documentation —
correct behaviour for an empty context list, not a shortfall in the model.
`CONTEXT <path>` fixes the actual gap: it reads a file from this repository
and puts its full text in front of the model before the conversation's `ASK`
prompts, so answers can cite real material instead of the one-paragraph
summary. It can appear more than once; each file is added in order.

```text
CONTEXT Hybit/Bab_III_Hybit_Paradigma_Komputasi_Ketiga.md
```

The path is resolved against the repository root and must stay inside it —
`../../etc/passwd` or an absolute path is rejected, not silently ignored —
and each file is capped at 200,000 bytes so one oversized or unrelated file
cannot quietly crowd out everything else in a small model's context window.
Both examples now load real material this way: the hermes example studies
the canonical Hybit chapter before answering a question about the v18
vector, and the qwen example studies `cosmictera-build/ON.md`'s HOS section
*and* the actual `rtl/programs/hos.hasm` source before answering a question
about why `hos_har_get` is built from compile-time `HLOAD` blocks rather
than a register-indexed one — the technology program itself, not a
paraphrase of it.

## Run

```bash
source .venv-mac/bin/activate
hybit-ai examples/local_ai.hcai         # hermes3:8b
hybit-ai examples/qwen_local_ai.hcai    # qwen3-coder:30b
```

The default endpoint is `http://127.0.0.1:11434`.

## Program format

```text
MODEL hermes3:8b
SYSTEM You are a precise Hybit Mathematics assistant.
HLOAD ا
HGRD
ASK Explain the loaded hybit.
PRINT
```

Supported instructions are `MODEL`, `SYSTEM`, `CONTEXT`, `HLOAD`, `HGRD`,
`ASK`, and `PRINT`. `HLOAD` resolves a canonical letter through the sealed
master table, and the runtime validates its guard constraints before
sending prompts. Omitting `SYSTEM` falls back to the NUI default above;
omitting `CONTEXT` means NUI answers from the persona paragraph alone.

The application is intentionally auditable: it does not execute arbitrary
Python or shell commands from a program file. Use the existing HC/HASM/HVM
pipeline when you need full machine-level execution.