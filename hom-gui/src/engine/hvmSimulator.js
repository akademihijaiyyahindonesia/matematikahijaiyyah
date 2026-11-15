// HVM — Interactive Hybit Virtual Machine & H-ISA Cycle-Accurate Simulator
// Synchronized 100% with Python `hijaiyyah.hisa.machine.HISAMachine`,
// `hijaiyyah.hisa.opcodes.OpCode`, `hijaiyyah.vm.verify_control_flow`,
// and `rtl/scripts/build_container.py` (`HPG1 v2` + `4-B'`).
//
// Execution Provenance Rule:
//   Web execution is strictly labeled `SIMULATED (Web HVM)` and is never
//   conflated with `ON-BOARD VERIFIED (Tang Nano 20K)`.

import { MASTER_TABLE } from './masterTable.js';
import { checkAllGuards, allGuardsPass } from './guards.js';

export const EXECUTION_PROVENANCE = {
  SIMULATED: {
    id: 'SIMULATED',
    badge: 'SIMULATED · Web HVM',
    description: 'Cycle-accurate software simulation in browser (not FPGA hardware execution)',
  },
  ON_BOARD_REFERENCE: {
    id: 'ON_BOARD_REFERENCE',
    badge: 'ON-BOARD VERIFIED · Tang Nano 20K Reference',
    description: 'Reference telemetry recorded from physical Gowin GW2AR-18C silicon',
  },
};

export const OPCODE_BY_NAME = {
  NOP: 0x00,
  HALT: 0x01,
  MOV: 0x03,
  MOVI: 0x04,
  HNRM2: 0x06,
  HDIST: 0x07,
  ERET: 0x08,
  SYSCALL: 0x09,
  FRD: 0x0A,
  FWR: 0x0B,
  ADD: 0x10,
  ADDI: 0x11,
  SUB: 0x12,
  MUL: 0x14,
  CMP: 0x20,
  CMPI: 0x21,
  JMP: 0x22,
  JEQ: 0x23,
  JNE: 0x24,
  JGD: 0x29,
  JNGD: 0x2A,
  JGP: 0x2B,
  JGF: 0x2C,
  JNP: 0x2D,
  CALL: 0x2E,
  RET: 0x2F,
  LOAD: 0x30,
  STORE: 0x31,
  PUSH: 0x32,
  POP: 0x33,
  HLOAD: 0x40,
  HCADD: 0x42,
  CSUB: 0x43,
  CGET: 0x44,
  CSET: 0x45,
  CMOV: 0x46,
  CZERO: 0x47,
  CEQ: 0x48,
  CDOT: 0x49,
  VNORM: 0x4A,
  VDIST: 0x4B,
  CRHO: 0x4C,
  CU: 0x4D,
  CTHETA: 0x4E,
  CMOD4: 0x4F,
  HPACK: 0x50,
  HCRC: 0x51,
  HDOT: 0x52,
  HEXMT: 0x55,
  HDCMP: 0x56,
  HSER: 0x57,
  HDES: 0x58,
  VSCL: 0x59,
  HGRD: 0x60,
  HCHK: 0x68,
  CHASH: 0x70,
  CSIGN: 0x72,
  HPROJ: 0x80,
  VPROJ_T: 0x88,
  VPROJ_N: 0x89,
  VPROJ_K: 0x8A,
  VPROJ_Q: 0x8B,
  PRINT: 0xA0,
  PRINTH: 0xA1,
  EMITS: 0xA2,
  AND: 0xB0,
  OR: 0xB1,
  XOR: 0xB2,
  NOT: 0xB3,
  SHL: 0xB4,
  SHR: 0xB5,
  ANDI: 0xB6,
  ORI: 0xB7,
  XORI: 0xB8,
  SHLI: 0xB9,
  SHRI: 0xBA,
  L_ALIF: 0xE0,
  L_BA: 0xE1,
  L_TA: 0xE2,
  L_TSA: 0xE3,
  L_JIM: 0xE4,
  L_HA: 0xE5,
  L_KHA: 0xE6,
  L_DAL: 0xE7,
  L_DZAL: 0xE8,
  L_RA: 0xE9,
  L_ZAY: 0xEA,
  L_SIN: 0xEB,
  L_SYIN: 0xEC,
  L_SHAD: 0xED,
  L_DHAD: 0xEE,
  L_THA: 0xEF,
  L_ZHA: 0xF0,
  L_AIN: 0xF1,
  L_GHAIN: 0xF2,
  L_FA: 0xF3,
  L_QAF: 0xF4,
  L_KAF: 0xF5,
  L_LAM: 0xF6,
  L_MIM: 0xF7,
  L_NUN: 0xF8,
  L_WAW: 0xF9,
  L_HAA: 0xFA,
  L_YA: 0xFB,
  HALT_ERR: 0xFF,
};

export const NAME_BY_OPCODE = Object.fromEntries(
  Object.entries(OPCODE_BY_NAME).map(([k, v]) => [v, k]),
);

export const RTL_IMPLEMENTED_CODES = new Set([
  0x00, 0x01, 0x03, 0x04, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B,
  0x10, 0x11, 0x12, 0x14,
  0x20, 0x21, 0x22, 0x23, 0x24, 0x29, 0x2A, 0x2E, 0x2F,
  0x30, 0x31, 0x32, 0x33,
  0x40, 0x42, 0x44, 0x45, 0x46, 0x47, 0x48, 0x4C, 0x4D, 0x4E, 0x4F,
  0x50, 0x51, 0x52,
  0x60,
  0xA0, 0xA2,
  0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA,
  ...Array.from({ length: 28 }, (_, i) => 0xE0 + i),
  0xFF,
]);

// 256-bit allowed opcode bitmap (8 × 32-bit chunks) matching hos_prog_load.hasm (4-B')
export const OVERLAY_OPCODE_MASKS = [
  0x00170EDB,
  0x0003C61F,
  0x0007F1F5,
  0x00000001,
  0x00000000,
  0x07FF0005,
  0x00000000,
  0x0FFFFFFF,
];

export function sext12(imm) {
  const val = imm & 0xFFF;
  return (val & 0x800) ? (val - 0x1000) : val;
}

export function encodeWord(opcode, dst = 0, src1 = 0, src2 = 0, imm = 0) {
  return (
    (((opcode & 0xFF) << 24) |
      ((dst & 0xF) << 20) |
      ((src1 & 0xF) << 16) |
      ((src2 & 0xF) << 12) |
      (imm & 0xFFF)) >>>
    0
  );
}

export function decodeWord(raw) {
  const u = raw >>> 0;
  const opcode = (u >>> 24) & 0xFF;
  const dst = (u >>> 20) & 0xF;
  const src1 = (u >>> 16) & 0xF;
  const src2 = (u >>> 12) & 0xF;
  const imm = u & 0xFFF;
  const name = NAME_BY_OPCODE[opcode] || `UNKNOWN_0x${opcode.toString(16).toUpperCase()}`;
  const isRtl = RTL_IMPLEMENTED_CODES.has(opcode);
  return {
    raw: u,
    hex: `0x${u.toString(16).toUpperCase().padStart(8, '0')}`,
    opcode,
    name,
    dst,
    src1,
    src2,
    imm,
    isRtl,
    disassembly: `${name} dst=${dst} src1=${src1} src2=${src2} imm=${imm}${isRtl ? '' : ' ; software-only'}`,
  };
}

export function computeU(v18) {
  return v18[10] + v18[11] + v18[12] + 4 * v18[13];
}

export function computeRho(v18) {
  return v18[0] - computeU(v18);
}

// ── Static 4-B′ Control Flow & Overlay Verifier ────────────────

export function verifyControlFlow4BPrime(words, loadAddr = 0x900) {
  const n = words.length;
  if (n === 0) {
    return { valid: false, firstBad: 0, reason: 'code section is empty (0 instruction words)' };
  }
  if (n > 1792) {
    return { valid: false, firstBad: 0, reason: 'invalid: WORDS over overlay staging buffer' };
  }

  for (let idx = 0; idx < n; idx += 1) {
    const w = words[idx] >>> 0;
    const op = (w >>> 24) & 0xFF;
    const imm = w & 0xFFF;
    const chunk = op >>> 5;
    const bit = (OVERLAY_OPCODE_MASKS[chunk] >>> (op & 31)) & 1;
    if (!bit) {
      if (op === 0x32) return { valid: false, firstBad: idx, reason: `invalid: forbidden opcode PUSH at word ${idx}` };
      if (op === 0x33) return { valid: false, firstBad: idx, reason: `invalid: forbidden opcode POP at word ${idx}` };
      if (op === 0x08) return { valid: false, firstBad: idx, reason: `unverified: dynamic control transfer ERET at word ${idx}` };
      return { valid: false, firstBad: idx, reason: `invalid: illegal opcode 0x${op.toString(16)} at word ${idx}` };
    }
    if (op === 0x22 || op === 0x2E) {
      if (op === 0x2E && idx === n - 1) {
        return { valid: false, firstBad: idx, reason: `invalid: CALL at final word ${idx} falls past end` };
      }
      const target = imm >= loadAddr ? imm - loadAddr : imm;
      if (target < 0 || target >= n) {
        return { valid: false, firstBad: idx, reason: `invalid: absolute target ${imm} at word ${idx} outside program` };
      }
    } else if (op === 0x23 || op === 0x24 || op === 0x29 || op === 0x2A) {
      if (idx === n - 1) {
        return { valid: false, firstBad: idx, reason: `invalid: conditional branch at final word ${idx} falls past end` };
      }
      const target = idx + sext12(imm);
      if (target < 0 || target >= n) {
        return { valid: false, firstBad: idx, reason: `invalid: relative target ${target} at word ${idx} outside program` };
      }
    }
  }

  // Worklist reachability check from word 0
  const visited = new Set();
  const worklist = [0];
  while (worklist.length > 0) {
    const idx = worklist.shift();
    if (visited.has(idx)) continue;
    visited.add(idx);

    const w = words[idx] >>> 0;
    const op = (w >>> 24) & 0xFF;
    const imm = w & 0xFFF;

    if (op === 0x01 || op === 0xFF || op === 0x2F || op === 0x08) {
      continue;
    }

    let successors = [];
    if (op === 0x22) {
      const target = imm >= loadAddr ? imm - loadAddr : imm;
      successors = [target];
    } else if (op === 0x23 || op === 0x24 || op === 0x29 || op === 0x2A) {
      successors = [idx + sext12(imm), idx + 1];
    } else if (op === 0x2E) {
      const target = imm >= loadAddr ? imm - loadAddr : imm;
      successors = [target, idx + 1];
    } else {
      successors = [idx + 1];
    }

    for (const succ of successors) {
      if (succ < 0 || succ >= n) {
        return {
          valid: false,
          firstBad: idx,
          reason: `word ${idx}: ${NAME_BY_OPCODE[op] || op} falls through to word ${succ} past program bounds [0, ${n}) without a valid terminator`,
        };
      }
      if (!visited.has(succ)) worklist.push(succ);
    }
  }

  return { valid: true, firstBad: null, reason: 'loaded' };
}

// ── HPG1 v2 Container Builder & CHECKSUM32 Verifier ────────────

export function buildHPG1Container(baseZeroWords, relocIndices = [], loadAddr = 0x900) {
  const MAGIC = 0x48504731; // 'HPG1'
  const VERSION = 2;
  const n = baseZeroWords.length;
  const relocCnt = relocIndices.length;
  const entryAddr = loadAddr;

  const container = [
    MAGIC,
    VERSION,
    n,
    loadAddr,
    entryAddr,
    relocCnt,
    0,
    ...relocIndices,
    ...baseZeroWords.map((w) => w >>> 0),
  ];

  const sectorCount = Math.ceil(container.length / 128);
  const sector16Record = [1, 1, 17, sectorCount];

  let sum = 0;
  for (const w of sector16Record) sum = (sum + (w >>> 0)) >>> 0;
  for (let i = 0; i < container.length; i += 1) {
    if (i === 6) continue;
    sum = (sum + (container[i] >>> 0)) >>> 0;
  }
  container[6] = sum >>> 0;

  const relocatedWords = baseZeroWords.map((w, idx) =>
    relocIndices.includes(idx) ? ((w + loadAddr) >>> 0) : (w >>> 0),
  );

  return {
    magic: MAGIC,
    magicHex: '0x48504731',
    version: VERSION,
    programWords: n,
    loadAddr,
    loadAddrHex: `0x${loadAddr.toString(16).toUpperCase()}`,
    entryAddr,
    entryAddrHex: `0x${entryAddr.toString(16).toUpperCase()}`,
    relocCount: relocCnt,
    relocationIndices: relocIndices,
    checksum32: container[6] >>> 0,
    checksumHex: `0x${(container[6] >>> 0).toString(16).toUpperCase().padStart(8, '0')}`,
    sector16Record,
    containerWords: container,
    relocatedWords,
  };
}

export function verifyHPG1Container(pkg) {
  let sum = 0;
  for (const w of pkg.sector16Record) sum = (sum + (w >>> 0)) >>> 0;
  for (let i = 0; i < pkg.containerWords.length; i += 1) {
    if (i === 6) continue;
    sum = (sum + (pkg.containerWords[i] >>> 0)) >>> 0;
  }
  const stored = pkg.containerWords[6] >>> 0;
  const checksumValid = sum === stored;
  const cf = verifyControlFlow4BPrime(pkg.relocatedWords, pkg.loadAddr);
  return {
    checksumValid,
    computedChecksum32: sum >>> 0,
    storedChecksum32: stored,
    overlay4BOk: cf.valid,
    overlay4BReason: cf.reason,
    ok: checksumValid && cf.valid,
  };
}

// ── Interactive Cycle-Accurate HVM Simulator Class ─────────────

export class HVMSimulator {
  constructor(words = []) {
    this.code = words.map((w) => w >>> 0);
    this.reset();
  }

  loadProgram(words) {
    this.code = words.map((w) => w >>> 0);
    this.reset();
  }

  reset() {
    this.pc = 0;
    this.cycle = 0;
    this.halted = false;
    this.paused = false;
    this.trap = null;
    this.gpr = Array.from({ length: 16 }, () => 0);
    this.hreg = Array.from({ length: 16 }, () => Array.from({ length: 18 }, () => 0));
    this.memory = new Map();
    this.callStack = [];
    this.dataStack = [];
    this.flags = {
      Z: false,
      N: false,
      C: false,
      LT: false,
      GUARD_PASS: true,
    };
    this.outputs = [];
    this.trace = [];
    this.lastDelta = {
      changedGpr: [],
      changedHreg: [],
      changedMem: [],
      guardDetail: null,
    };
  }

  encodeFlagsByte() {
    let b = 0;
    if (this.flags.GUARD_PASS) b |= 0x01;
    if (this.flags.Z) b |= 0x02;
    if (this.flags.C) b |= 0x04;
    if (this.flags.LT || this.flags.N) b |= 0x08;
    return b & 0xFF;
  }

  decodeFlagsByte(b) {
    this.flags.GUARD_PASS = Boolean(b & 0x01);
    this.flags.Z = Boolean(b & 0x02);
    this.flags.C = Boolean(b & 0x04);
    this.flags.LT = Boolean(b & 0x08);
    this.flags.N = Boolean(b & 0x08);
  }

  step() {
    if (this.halted) return null;
    if (this.pc < 0 || this.pc >= this.code.length) {
      this.halted = true;
      this.trap = `PC out of bounds (${this.pc})`;
      return null;
    }

    const pcBefore = this.pc;
    const raw = this.code[pcBefore] >>> 0;
    const ins = decodeWord(raw);
    const { opcode, dst, src1, src2, imm } = ins;

    const changedGpr = [];
    const changedHreg = [];
    const changedMem = [];
    let guardDetail = null;
    let desc = '';

    this.pc += 1;
    this.cycle += 1;

    if (opcode === 0x00) {
      desc = 'NOP';
    } else if (opcode === 0x01) {
      this.halted = true;
      desc = 'HALT';
    } else if (opcode === 0x03) {
      this.gpr[dst] = this.gpr[src1] | 0;
      changedGpr.push(dst);
      desc = `MOV R${dst} ← R${src1} (${this.gpr[dst]})`;
    } else if (opcode === 0x04) {
      this.gpr[dst] = sext12(imm);
      changedGpr.push(dst);
      desc = `MOVI R${dst} ← ${this.gpr[dst]}`;
    } else if (opcode === 0x06 || opcode === 0x4A) {
      const h = this.hreg[src1];
      let sumSq = 0;
      for (let i = 0; i < 14; i += 1) sumSq += h[i] * h[i];
      this.gpr[dst] = sumSq;
      changedGpr.push(dst);
      desc = `HNRM2 R${dst} ← ‖H${src1}‖₁₄² = ${sumSq}`;
    } else if (opcode === 0x07 || opcode === 0x4B) {
      const a = this.hreg[src1];
      const b = this.hreg[src2];
      let d2 = 0;
      for (let i = 0; i < 14; i += 1) {
        const diff = a[i] - b[i];
        d2 += diff * diff;
      }
      this.gpr[dst] = d2;
      changedGpr.push(dst);
      desc = `HDIST R${dst} ← d₂²(H${src1}, H${src2}) = ${d2}`;
    } else if (opcode === 0x0A) {
      this.gpr[dst] = this.encodeFlagsByte();
      changedGpr.push(dst);
      desc = `FRD R${dst} ← FLAGS (0x${this.gpr[dst].toString(16)})`;
    } else if (opcode === 0x0B) {
      this.decodeFlagsByte(this.gpr[src1] & 0xFF);
      desc = `FWR FLAGS ← R${src1} (G=${this.flags.GUARD_PASS ? 1 : 0})`;
    } else if (opcode === 0x10) {
      this.gpr[dst] = (this.gpr[src1] + this.gpr[src2]) | 0;
      changedGpr.push(dst);
      desc = `ADD R${dst} ← R${src1} + R${src2} = ${this.gpr[dst]}`;
    } else if (opcode === 0x11) {
      this.gpr[dst] = (this.gpr[src1] + sext12(imm)) | 0;
      changedGpr.push(dst);
      desc = `ADDI R${dst} ← R${src1} + ${sext12(imm)} = ${this.gpr[dst]}`;
    } else if (opcode === 0x12) {
      this.gpr[dst] = (this.gpr[src1] - this.gpr[src2]) | 0;
      changedGpr.push(dst);
      desc = `SUB R${dst} ← R${src1} − R${src2} = ${this.gpr[dst]}`;
    } else if (opcode === 0x14) {
      this.gpr[dst] = Math.imul(this.gpr[src1], this.gpr[src2]);
      changedGpr.push(dst);
      desc = `MUL R${dst} ← R${src1} × R${src2} = ${this.gpr[dst]}`;
    } else if (opcode === 0x20) {
      const a = this.gpr[src1];
      const b = this.gpr[src2];
      this.flags.Z = a === b;
      this.flags.LT = a < b;
      this.flags.N = a < b;
      desc = `CMP R${src1}(${a}), R${src2}(${b}) → Z=${this.flags.Z ? 1 : 0}, LT=${this.flags.LT ? 1 : 0}`;
    } else if (opcode === 0x21) {
      const a = this.gpr[src1];
      const b = sext12(imm);
      this.flags.Z = a === b;
      this.flags.LT = a < b;
      this.flags.N = a < b;
      desc = `CMPI R${src1}(${a}), ${b} → Z=${this.flags.Z ? 1 : 0}, LT=${this.flags.LT ? 1 : 0}`;
    } else if (opcode === 0x22) {
      this.pc = imm;
      desc = `JMP → word ${imm}`;
    } else if (opcode === 0x23) {
      const offset = sext12(imm);
      if (this.flags.Z) this.pc = pcBefore + offset;
      desc = `JEQ ${offset >= 0 ? '+' : ''}${offset} (${this.flags.Z ? 'TAKEN' : 'NOT TAKEN'})`;
    } else if (opcode === 0x24) {
      const offset = sext12(imm);
      if (!this.flags.Z) this.pc = pcBefore + offset;
      desc = `JNE ${offset >= 0 ? '+' : ''}${offset} (${!this.flags.Z ? 'TAKEN' : 'NOT TAKEN'})`;
    } else if (opcode === 0x29) {
      const offset = sext12(imm);
      if (this.flags.GUARD_PASS) this.pc = pcBefore + offset;
      desc = `JGD ${offset >= 0 ? '+' : ''}${offset} (${this.flags.GUARD_PASS ? 'TAKEN' : 'NOT TAKEN'})`;
    } else if (opcode === 0x2A) {
      const offset = sext12(imm);
      if (!this.flags.GUARD_PASS) this.pc = pcBefore + offset;
      desc = `JNGD ${offset >= 0 ? '+' : ''}${offset} (${!this.flags.GUARD_PASS ? 'TAKEN' : 'NOT TAKEN'})`;
    } else if (opcode === 0x2E) {
      if (this.callStack.length >= 28) {
        this.halted = true;
        this.trap = 'HC-01: Return-address stack overflow (> 28)';
        desc = this.trap;
      } else {
        this.callStack.push(this.pc);
        this.pc = imm;
        desc = `CALL → word ${imm} (ret=${pcBefore + 1})`;
      }
    } else if (opcode === 0x2F) {
      if (this.callStack.length === 0) {
        this.halted = true;
        this.trap = 'HC-01: RET on empty call stack';
        desc = this.trap;
      } else {
        this.pc = this.callStack.pop();
        desc = `RET → word ${this.pc}`;
      }
    } else if (opcode === 0x30) {
      const addr = (this.gpr[src1] + sext12(imm)) & 0xFFF;
      this.gpr[dst] = this.memory.get(addr) || 0;
      changedGpr.push(dst);
      desc = `LOAD R${dst} ← MEM[0x${addr.toString(16)}] (${this.gpr[dst]})`;
    } else if (opcode === 0x31) {
      const addr = (this.gpr[src1] + sext12(imm)) & 0xFFF;
      const val = this.gpr[src2] | 0;
      this.memory.set(addr, val);
      changedMem.push({ addr, val });
      desc = `STORE MEM[0x${addr.toString(16)}] ← R${src2} (${val})`;
    } else if (opcode === 0x40) {
      const idx = imm > 0 ? imm : this.gpr[src1];
      const entry = MASTER_TABLE[idx - 1];
      if (!entry) {
        this.halted = true;
        this.trap = `HC-04: Invalid HLOAD index ${idx}`;
        desc = this.trap;
      } else {
        this.hreg[dst] = [...entry.v18];
        changedHreg.push(dst);
        desc = `HLOAD H${dst} ← #${idx} ${entry.char} (${entry.name})`;
      }
    } else if (opcode === 0x42) {
      const a = this.hreg[src1];
      const b = this.hreg[src2];
      this.hreg[dst] = a.map((v, i) => v + b[i]);
      changedHreg.push(dst);
      desc = `HCADD H${dst} ← H${src1} + H${src2} (Θ̂=${this.hreg[dst][0]})`;
    } else if (opcode === 0x44) {
      const slot = imm & 0x1F;
      this.gpr[dst] = this.hreg[src1][slot] ?? 0;
      changedGpr.push(dst);
      desc = `CGET R${dst} ← H${src1}[${slot}] (${this.gpr[dst]})`;
    } else if (opcode === 0x45) {
      const slot = imm & 0x1F;
      const next = [...this.hreg[dst]];
      next[slot] = this.gpr[src1] & 0xFF;
      this.hreg[dst] = next;
      changedHreg.push(dst);
      desc = `CSET H${dst}[${slot}] ← R${src1} (${next[slot]})`;
    } else if (opcode === 0x46) {
      this.hreg[dst] = [...this.hreg[src1]];
      changedHreg.push(dst);
      desc = `CMOV H${dst} ← H${src1}`;
    } else if (opcode === 0x47) {
      this.hreg[dst] = Array.from({ length: 18 }, () => 0);
      changedHreg.push(dst);
      desc = `CZERO H${dst} ← 0`;
    } else if (opcode === 0x48) {
      const a = this.hreg[src1];
      const b = this.hreg[src2];
      this.flags.Z = a.every((v, i) => v === b[i]);
      desc = `CEQ H${src1}, H${src2} → Z=${this.flags.Z ? 1 : 0}`;
    } else if (opcode === 0x4C) {
      this.gpr[dst] = computeRho(this.hreg[src1]);
      changedGpr.push(dst);
      desc = `CRHO R${dst} ← ρ(H${src1}) = ${this.gpr[dst]}`;
    } else if (opcode === 0x4D) {
      this.gpr[dst] = computeU(this.hreg[src1]);
      changedGpr.push(dst);
      desc = `CU R${dst} ← U(H${src1}) = ${this.gpr[dst]}`;
    } else if (opcode === 0x4E) {
      this.gpr[dst] = this.hreg[src1][0];
      changedGpr.push(dst);
      desc = `CTHETA R${dst} ← Θ̂(H${src1}) = ${this.gpr[dst]}`;
    } else if (opcode === 0x4F) {
      this.gpr[dst] = this.hreg[src1][0] % 4;
      changedGpr.push(dst);
      desc = `CMOD4 R${dst} ← Θ̂(H${src1}) mod 4 = ${this.gpr[dst]}`;
    } else if (opcode === 0x52 || opcode === 0x49) {
      const a = this.hreg[src1];
      const b = this.hreg[src2];
      let dot = 0;
      for (let i = 0; i < 14; i += 1) dot += a[i] * b[i];
      this.gpr[dst] = dot;
      changedGpr.push(dst);
      desc = `HDOT R${dst} ← ⟨H${src1}, H${src2}⟩₁₄ = ${dot}`;
    } else if (opcode === 0x60) {
      const vec = this.hreg[src1];
      const checks = checkAllGuards(vec);
      const pass = allGuardsPass(vec);
      this.flags.GUARD_PASS = pass;
      guardDetail = { register: `H${src1}`, pass, checks };
      desc = `HGRD H${src1} → ${pass ? 'PASS ✓ (G1–G4, T1–T2)' : 'FAIL ✗'}`;
    } else if (opcode === 0xA0) {
      // PRINT supports either src1 or dst encoding depending on assembler form
      const regIdx = src1 !== 0 ? src1 : dst;
      const val = this.gpr[regIdx];
      this.outputs.push(val);
      desc = `PRINT R${regIdx} → ${val}`;
    } else if (opcode >= 0xE0 && opcode <= 0xFB) {
      const letterIdx = opcode - 0xE0;
      const entry = MASTER_TABLE[letterIdx];
      this.hreg[0] = this.hreg[0].map((v, i) => v + entry.v18[i]);
      changedHreg.push(0);
      desc = `${ins.name} (${entry.char}) → H0 ← H0 + v₁₈(${entry.char}) (Θ̂=${this.hreg[0][0]})`;
    } else if (opcode === 0xB0) {
      this.gpr[dst] = this.gpr[src1] & this.gpr[src2];
      changedGpr.push(dst);
      desc = `AND R${dst} ← R${src1} & R${src2}`;
    } else if (opcode === 0xB1) {
      this.gpr[dst] = this.gpr[src1] | this.gpr[src2];
      changedGpr.push(dst);
      desc = `OR R${dst} ← R${src1} | R${src2}`;
    } else if (opcode === 0xB2) {
      this.gpr[dst] = this.gpr[src1] ^ this.gpr[src2];
      changedGpr.push(dst);
      desc = `XOR R${dst} ← R${src1} ^ R${src2}`;
    } else if (opcode === 0xB6) {
      this.gpr[dst] = this.gpr[src1] & (imm & 0xFFF);
      changedGpr.push(dst);
      desc = `ANDI R${dst} ← R${src1} & 0x${imm.toString(16)}`;
    } else if (opcode === 0xB8) {
      this.gpr[dst] = this.gpr[src1] ^ (imm & 0xFFF);
      changedGpr.push(dst);
      desc = `XORI R${dst} ← R${src1} ^ 0x${imm.toString(16)}`;
    } else if (opcode === 0xB9) {
      this.gpr[dst] = this.gpr[src1] << (imm & 31);
      changedGpr.push(dst);
      desc = `SHLI R${dst} ← R${src1} << ${imm & 31}`;
    } else if (opcode === 0xBA) {
      this.gpr[dst] = this.gpr[src1] >>> (imm & 31);
      changedGpr.push(dst);
      desc = `SHRI R${dst} ← R${src1} >>> ${imm & 31}`;
    } else {
      this.halted = true;
      this.trap = `HC-05: Unimplemented opcode 0x${opcode.toString(16).toUpperCase()}`;
      desc = this.trap;
    }

    this.lastDelta = { changedGpr, changedHreg, changedMem, guardDetail };
    const entry = {
      cycle: this.cycle,
      pc: pcBefore,
      hex: ins.hex,
      opcode: ins.name,
      description: desc,
      guardPass: this.flags.GUARD_PASS,
      changedGpr,
      changedHreg,
      trap: this.trap,
    };
    this.trace.push(entry);
    return entry;
  }

  run(maxCycles = 5000) {
    this.paused = false;
    let steps = 0;
    while (!this.halted && !this.paused && steps < maxCycles) {
      const res = this.step();
      if (!res) break;
      steps += 1;
    }
    if (steps >= maxCycles && !this.halted) {
      this.trap = `Execution paused after reaching maxCycles (${maxCycles})`;
    }
    return this.getState();
  }

  pause() {
    this.paused = true;
  }

  getState() {
    return {
      provenance: EXECUTION_PROVENANCE.SIMULATED,
      pc: this.pc,
      cycle: this.cycle,
      halted: this.halted,
      paused: this.paused,
      trap: this.trap,
      flags: { ...this.flags },
      gpr: [...this.gpr],
      hreg: this.hreg.map((r) => [...r]),
      memory: Array.from(this.memory.entries()).map(([addr, val]) => ({ addr, val })),
      outputs: [...this.outputs],
      trace: [...this.trace],
      lastDelta: this.lastDelta,
    };
  }
}
