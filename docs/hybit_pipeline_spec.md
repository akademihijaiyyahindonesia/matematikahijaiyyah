# Hybit Pipeline Specification

## Complete Architecture

```
.hc → HCC (6-stage) → .hasm → HASM (4-pass) → .hbc → HVM (5-component) → OUTPUT
                                                  ↑
Font (sealed) → Ψ-Compiler → .hgeo → HAR ────────┘
```

## Components

| Component | Function | Status |
|---|---|---|
| .hc | HC source code | OPERATIONAL |
| HCC | Compiler (Lex→Parse→Sem→Ψ→Gen→Asm) | PARTIAL |
| .hasm | H-ISA assembly text | SPECIFIED |
| HASM | Assembler (4-pass) | SPECIFIED |
| .hbc | Bytecode binary (magic "HBYT") | SPECIFIED |
| .hgeo | Geometry extraction per glyph | SPECIFIED |
| HAR | Alphabet registry (multi-alphabet) | PARTIAL |
| HVM | Virtual machine (5 components) | OPERATIONAL |
| Guard | Per-operation validation G1–G4 | OPERATIONAL |
| HCHECK | Periodic integrity monitor | SPECIFIED |
| HOS | Operating system | OPERATIONAL (heap, HFS, HAR as a service) |
| HFS | File system (guard-on-write) | OPERATIONAL (create/write/read/verify; no persistent medium) |
| H-Kernel | Kernel (18-wide alignment) | OPERATIONAL (4 of 4; three fixed slots) |

## Principle: No Overlap

Every component has exactly ONE function.
See README for the full non-overlap table.

© 2026 Maulana Amratulloh
