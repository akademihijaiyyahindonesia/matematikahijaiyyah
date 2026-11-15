// HC v1.0 & Hijaiyyah Cells (.hcell) Web Compiler Engine
// Implements:
//   1. Lexer & Parser for both HC v1.0 (`let`, `fn`, `while`, `if`, `'ب'`, `.theta()`, etc.)
//      and native `.hcell` (`:=`, `⊢`, `↦`, `⟪...⟫`, `Θ̂`, `U`, `ρ`, `‖...‖²`, `d₂²`, `⟨...⟩`).
//   2. Orthographic Policy Check (`FORBIDDEN_LOOKALIKES` such as 'ة' U+0629, 'أ' U+0623)
//      with exact `L<line>:<col>` diagnostics.
//   3. Shared `CellIR` builder & `SemanticAnalyzer` with Two-Layer Six-Guard Proof
//      (Layer A: G1–G4, T1–T2 closure over N_0^18; Layer B: 8-bit prefix bound <= 255 & H* == Ka).
//   4. H-ISA Backend Codegen (`CellHISABackend` parity), `4-B′` static verifier, and `HPG1 v2` packager.

import { MASTER_TABLE, getLetterByChar } from './masterTable.js';
import { allGuardsPass, checkAllGuards } from './guards.js';
import {
  OPCODE_BY_NAME,
  encodeWord,
  decodeWord,
  verifyControlFlow4BPrime,
  buildHPG1Container,
  verifyHPG1Container,
} from './hvmSimulator.js';

export const FORBIDDEN_LOOKALIKES = {
  'ة': 'Ta Marbuthah (U+0629) — not in canonical H_28',
  'أ': 'Alif with Hamzah Above (U+0623) — use canonical Alif ا (U+0627)',
  'إ': 'Alif with Hamzah Below (U+0625) — use canonical Alif ا (U+0627)',
  'آ': 'Alif Maddah (U+0622) — use canonical Alif ا (U+0627)',
  'ى': 'Alif Maqsurah (U+0649) — use canonical Ya ي (U+064A)',
  'ؤ': 'Waw with Hamzah (U+0624) — use canonical Waw و (U+0648)',
  'ئ': 'Ya with Hamzah (U+0626) — use canonical Ya ي (U+064A)',
  'ك': null, // canonical
  'ک': 'Persian Keheh (U+06A9) — use canonical Kaf ك (U+0643)',
  'ي': null, // canonical
  'ی': 'Persian Farsi Yeh (U+06CC) — use canonical Ya ي (U+064A)',
  'ه': 'Bare Heh (U+0647) without Tatweel — canonical Haa is هـ',
};

const ARABIC_INDIC_MAP = {
  '٠': '0',
  '١': '1',
  '٢': '2',
  '٣': '3',
  '٤': '4',
  '٥': '5',
  '٦': '6',
  '٧': '7',
  '٨': '8',
  '٩': '9',
};

function normalizeDigits(str) {
  return str.replace(/[٠-٩]/g, (ch) => ARABIC_INDIC_MAP[ch] ?? ch);
}

function parseCanonicalLettersFromString(text) {
  const letters = [];
  let i = 0;
  while (i < text.length) {
    const ch = text[i];
    if (/\s/.test(ch)) {
      i += 1;
      continue;
    }
    if (text.slice(i, i + 2) === 'هـ') {
      letters.push('هـ');
      i += 2;
      continue;
    }
    const entry = getLetterByChar(ch);
    if (entry) {
      letters.push(entry.char);
      i += 1;
      continue;
    }
    if (ch === 'ه') {
      letters.push('هـ');
      i += 1;
      continue;
    }
    throw new Error(`Unknown non-H_28 character '${ch}' in letter sequence`);
  }
  return letters;
}

function checkOrthographicPolicy(source, isHcCompat) {
  const lines = source.split('\n');
  for (let idx = 0; idx < lines.length; idx += 1) {
    const rawLine = lines[idx];
    const codePart = rawLine.split('//')[0];
    for (let col = 0; col < codePart.length; col += 1) {
      const ch = codePart[col];
      if (ch === 'ه' && codePart[col + 1] === 'ـ') {
        col += 1;
        continue;
      }
      const reason = FORBIDDEN_LOOKALIKES[ch];
      if (reason) {
        const err = new Error(`L${idx + 1}:${col + 1}: Forbidden lookalike '${ch}' (${reason})`);
        err.line = idx + 1;
        err.col = col + 1;
        err.type = 'UnicodePolicyError';
        throw err;
      }
    }
    if (!isHcCompat) {
      // Check for unapproved Latin variable identifiers in native .hcell
      const cleaned = codePart
        .replace(/Θ̂|d₂²|H\*|U|ρ/g, ' ')
        .replace(/\/\/.*$/, '');
      const latinMatch = cleaned.match(/\b(let|fn|while|if|else|println|return|[a-zA-Z_][a-zA-Z0-9_]*)\b/);
      if (latinMatch) {
        const col = codePart.indexOf(latinMatch[0]) + 1;
        const err = new Error(
          `L${idx + 1}:${col}: Latin identifier/keyword '${latinMatch[0]}' is forbidden in native .hcell mode (enable HC v1.0 Mode for .hc syntax)`,
        );
        err.line = idx + 1;
        err.col = col;
        err.type = 'HCellLexerError';
        throw err;
      }
    }
  }
}

// ── Unified AST / Statement Parser for HC v1.0 and .hcell ──────

export function compileHCOrHCell(source, options = {}) {
  const {
    mode = 'auto', // 'auto' | 'hc' | 'hcell'
    useNativeLetterOpcodes = true,
    useNativeHdot = false,
    loadAddr = 0x900,
    tamperChecksum = false,
  } = options;

  const t0 = typeof performance !== 'undefined' ? performance.now() : Date.now();
  const trimmed = (source || '').trim();
  const isHcCompat =
    mode === 'hc' ||
    (mode === 'auto' && /\b(let|fn|println|while|if)\b/.test(trimmed));

  const diagnostics = [];
  if (!trimmed) {
    return {
      ok: false,
      failedStage: 'STAGE_1_PARSE',
      errorType: 'EmptySourceError',
      errorMessage: 'L1:1: Source code is empty',
      errorLine: 1,
      errorCol: 1,
      diagnostics: ['[FAIL] Stage 1 (INPUT): Source code is empty.'],
    };
  }

  try {
    checkOrthographicPolicy(source, isHcCompat);
  } catch (err) {
    return {
      ok: false,
      failedStage: 'STAGE_1_PARSE',
      errorType: err.type || 'UnicodePolicyError',
      errorMessage: err.message,
      errorLine: err.line || 1,
      errorCol: err.col || 1,
      diagnostics: [`[FAIL] Stage 1 (INPUT / Orthographic Policy): ${err.message}`],
    };
  }

  const nodes = [];
  const bindings = new Map(); // varName -> nodeId
  let nodeCounter = 0;

  function addNode(op, outputType, glyphs, line, col, extra = {}) {
    nodeCounter += 1;
    const prefix = {
      LETTER_CONST: 'ltr',
      WORD_ACCUM: 'wrd',
      SCALAR_CONST: 'lit',
      HYBIT_ADD: 'add',
      HYBIT_DELTA: 'dlt',
      SCALAR_ADD: 'sadd',
      SCALAR_SUB: 'ssub',
      SCALAR_MUL: 'smul',
      PROJ_THETA: 'op',
      PROJ_HSTAR: 'hst',
      PROJ_COMPONENT: 'cmp',
      TURNING_U: 'op',
      TURNING_RHO: 'op',
      MOD4_GATE: 'op',
      NORM2_V14: 'op',
      DIST2_V14: 'op',
      INNER_V14: 'op',
      GUARD_CHECK: 'grd',
      EMIT_OUTPUT: 'out',
    }[op] || 'cell';
    const cellId = `${prefix}${nodeCounter}`;
    const node = {
      cellId,
      op,
      outputType,
      sourceGlyphs: glyphs,
      line,
      col,
      inputs: extra.inputs || [],
      bindingName: extra.bindingName || null,
      immParam: extra.immParam ?? null,
      letterSequence: extra.letterSequence || [],
      staticVector: extra.staticVector || null,
      staticScalar: extra.staticScalar ?? null,
      maxComponent: extra.maxComponent ?? null,
      provenInH: Boolean(extra.provenInH),
      hardware8BitSafe: Boolean(extra.hardware8BitSafe),
      hstarCoupledBoundProven: Boolean(extra.hstarCoupledBoundProven),
      guardDischarged: Boolean(extra.guardDischarged),
    };
    nodes.push(node);
    if (node.bindingName) {
      bindings.set(node.bindingName, node);
    }
    return node;
  }

  function makeLetterNode(char, line, col, bindingName = null) {
    const entry = getLetterByChar(char);
    if (!entry) {
      const err = new Error(`L${line}:${col}: Unknown Hijaiyyah letter '${char}'`);
      err.line = line;
      err.col = col;
      err.type = 'HCellParseError';
      throw err;
    }
    return addNode('LETTER_CONST', 'hybit', char, line, col, {
      bindingName,
      immParam: entry.id,
      letterSequence: [entry.char],
      staticVector: [...entry.v18],
      maxComponent: Math.max(...entry.v18),
      provenInH: true,
      hardware8BitSafe: true,
      hstarCoupledBoundProven: true,
    });
  }

  function makeHybitSumChain(letters, line, col, bindingName = null, rawGlyphs = null) {
    if (letters.length === 1) {
      return makeLetterNode(letters[0], line, col, bindingName);
    }
    let accNode = makeLetterNode(letters[0], line, col, null);
    let seq = [letters[0]];
    for (let i = 1; i < letters.length; i += 1) {
      const rNode = makeLetterNode(letters[i], line, col, null);
      seq = [...seq, letters[i]];
      const vec = accNode.staticVector.map((v, k) => v + rNode.staticVector[k]);
      const maxComp = Math.max(...vec);
      const isLast = i === letters.length - 1;
      accNode = addNode(
        'HYBIT_ADD',
        'hybit',
        isLast && rawGlyphs ? rawGlyphs : seq.join(' + '),
        line,
        col,
        {
          bindingName: isLast ? bindingName : null,
          inputs: [accNode.cellId, rNode.cellId],
          letterSequence: seq,
          staticVector: vec,
          maxComponent: maxComp,
          provenInH: allGuardsPass(vec),
          hardware8BitSafe: maxComp <= 255,
          hstarCoupledBoundProven: maxComp <= 255 && vec[17] === vec[7] && 2 * vec[17] <= vec[0],
        },
      );
    }
    return accNode;
  }

  function evalExpr(exprStr, line, col, bindingName = null) {
    const expr = normalizeDigits(exprStr.trim());
    if (!expr) {
      const err = new Error(`L${line}:${col}: Unexpected empty expression`);
      err.line = line;
      err.col = col;
      err.type = 'HCellParseError';
      throw err;
    }

    // 1. Word accumulation literal ⟪...⟫ or hm::integral::string_integral("...")
    const wordMatch = expr.match(/^⟪([^⟫]+)⟫$/) || expr.match(/^hm::integral::string_integral\(\s*"([^"]+)"\s*\)$/);
    if (wordMatch) {
      const letters = parseCanonicalLettersFromString(wordMatch[1]);
      if (letters.length === 0) {
        const err = new Error(`L${line}:${col}: Word accumulation requires at least one letter`);
        err.line = line;
        err.col = col;
        err.type = 'HCellParseError';
        throw err;
      }
      const sumVec = Array.from({ length: 18 }, () => 0);
      let prefixSafe = true;
      for (const ch of letters) {
        const ent = getLetterByChar(ch);
        for (let k = 0; k < 18; k += 1) {
          sumVec[k] += ent.v18[k];
          if (sumVec[k] > 255) prefixSafe = false;
        }
      }
      const maxComp = Math.max(...sumVec);
      return addNode('WORD_ACCUM', 'hybit', expr, line, col, {
        bindingName,
        letterSequence: letters,
        staticVector: sumVec,
        maxComponent: maxComp,
        provenInH: allGuardsPass(sumVec),
        hardware8BitSafe: prefixSafe && maxComp <= 255,
        hstarCoupledBoundProven:
          prefixSafe && sumVec[17] === sumVec[7] && 2 * sumVec[17] <= sumVec[0],
      });
    }

    // 2. Quoted HC letter literal 'ب'
    const quotedLetter = expr.match(/^'([^']+)'$/);
    if (quotedLetter) {
      return makeLetterNode(quotedLetter[1].trim(), line, col, bindingName);
    }

    // 3. Direct single canonical Hijaiyyah letter
    if (getLetterByChar(expr)) {
      return makeLetterNode(expr, line, col, bindingName);
    }

    // 4. Integer literal
    if (/^-?\d+$/.test(expr)) {
      const val = parseInt(expr, 10);
      return addNode('SCALAR_CONST', 'scalar', expr, line, col, {
        bindingName,
        immParam: val,
        staticScalar: val,
      });
    }

    // 5. Differential Δ(a, b) or hm::differential::diff(a, b)
    const deltaMatch =
      expr.match(/^Δ\(\s*([^,]+)\s*,\s*([^)]+)\s*\)$/) ||
      expr.match(/^hm::differential::diff\(\s*([^,]+)\s*,\s*([^)]+)\s*\)$/);
    if (deltaMatch) {
      const left = evalExpr(deltaMatch[1], line, col);
      const right = evalExpr(deltaMatch[2], line, col);
      if (left.outputType !== 'hybit' || right.outputType !== 'hybit') {
        const err = new Error(
          `L${line}:${col}: Operation HYBIT_DELTA requires HYBIT operands, got (${left.outputType}, ${right.outputType})`,
        );
        err.line = line;
        err.col = col;
        err.type = 'CellSemanticError';
        throw err;
      }
      return addNode('HYBIT_DELTA', 'delta14', expr, line, col, {
        bindingName,
        inputs: [left.cellId, right.cellId],
        provenInH: false,
        hardware8BitSafe: false,
      });
    }

    // 6. Unary mathematical / method projections:
    //    Θ̂(x) / x.theta() | U(x) / x.U() | ρ(x) / x.rho() | ‖x‖² / x.norm2() | H*(x) / x.Hstar()
    const unaryPatterns = [
      { op: 'PROJ_THETA', re: /^(?:Θ̂|theta)\(\s*(.+)\s*\)$|^(.+)\.theta\(\)$/ },
      { op: 'TURNING_U', re: /^U\(\s*(.+)\s*\)$|^(.+)\.U\(\)$/ },
      { op: 'TURNING_RHO', re: /^(?:ρ|rho)\(\s*(.+)\s*\)$|^(.+)\.rho\(\)$/ },
      { op: 'NORM2_V14', re: /^‖\s*(.+)\s*‖(?:²|2)$|^(.+)\.norm2\(\)$|^hm::vectronometry::norm2\(\s*(.+)\s*\)$/ },
      { op: 'PROJ_HSTAR', re: /^H\*\(\s*(.+)\s*\)$|^(.+)\.Hstar\(\)$/ },
      { op: 'MOD4_GATE', re: /^Θ₄\(\s*(.+)\s*\)$|^(.+)\.mod4\(\)$/ },
    ];
    for (const pat of unaryPatterns) {
      const m = expr.match(pat.re);
      if (m) {
        const innerExpr = (m[1] || m[2] || m[3]).trim();
        const target = evalExpr(innerExpr, line, col);
        if (target.outputType !== 'hybit') {
          const err = new Error(
            `L${line}:${col} [${pat.op}]: requires operand of type hybit, got ${target.outputType} (${target.sourceGlyphs})`,
          );
          err.line = line;
          err.col = col;
          err.type = 'CellSemanticError';
          throw err;
        }
        return addNode(pat.op, 'scalar', expr, line, col, {
          bindingName,
          inputs: [target.cellId],
        });
      }
    }

    // 7. Component index x[slot]
    const idxMatch = expr.match(/^(.+)\[\s*(\d+)\s*\]$/);
    if (idxMatch) {
      const target = evalExpr(idxMatch[1], line, col);
      const slot = parseInt(idxMatch[2], 10);
      if (target.outputType !== 'hybit') {
        const err = new Error(`L${line}:${col}: Component projection requires hybit operand`);
        err.line = line;
        err.col = col;
        err.type = 'CellSemanticError';
        throw err;
      }
      if (slot < 0 || slot > 17) {
        const err = new Error(`L${line}:${col}: Component index ${slot} out of range 0..17`);
        err.line = line;
        err.col = col;
        err.type = 'CellSemanticError';
        throw err;
      }
      return addNode('PROJ_COMPONENT', 'scalar', expr, line, col, {
        bindingName,
        inputs: [target.cellId],
        immParam: slot,
      });
    }

    // 8. Binary distance d₂²(a, b) / a.dist2(b) / hm::geometry::euclidean_sq(a, b)
    const distMatch =
      expr.match(/^d₂²\(\s*([^,]+)\s*,\s*([^)]+)\s*\)$/) ||
      expr.match(/^hm::geometry::euclidean_sq\(\s*([^,]+)\s*,\s*([^)]+)\s*\)$/) ||
      expr.match(/^(.+)\.dist2\(\s*([^)]+)\s*\)$/);
    if (distMatch) {
      const aNode = evalExpr(distMatch[1], line, col);
      const bNode = evalExpr(distMatch[2], line, col);
      if (aNode.outputType !== 'hybit' || bNode.outputType !== 'hybit') {
        const err = new Error(
          `L${line}:${col}: DIST2_V14 requires two hybit operands, got (${aNode.outputType}, ${bNode.outputType})`,
        );
        err.line = line;
        err.col = col;
        err.type = 'CellSemanticError';
        throw err;
      }
      return addNode('DIST2_V14', 'scalar', expr, line, col, {
        bindingName,
        inputs: [aNode.cellId, bNode.cellId],
      });
    }

    // 9. Inner product ⟨a, b⟩ / a.dot(b)
    const dotMatch =
      expr.match(/^⟨\s*([^,]+)\s*,\s*([^⟩]+)\s*⟩(?:₁₄)?$/) ||
      expr.match(/^(.+)\.dot\(\s*([^)]+)\s*\)$/);
    if (dotMatch) {
      const aNode = evalExpr(dotMatch[1], line, col);
      const bNode = evalExpr(dotMatch[2], line, col);
      if (aNode.outputType !== 'hybit' || bNode.outputType !== 'hybit') {
        const err = new Error(
          `L${line}:${col}: INNER_V14 requires two hybit operands, got (${aNode.outputType}, ${bNode.outputType})`,
        );
        err.line = line;
        err.col = col;
        err.type = 'CellSemanticError';
        throw err;
      }
      return addNode('INNER_V14', 'scalar', expr, line, col, {
        bindingName,
        inputs: [aNode.cellId, bNode.cellId],
      });
    }

    // 10. Addition chain `a + b + c`
    if (expr.includes('+')) {
      const parts = expr.split('+').map((p) => p.trim());
      if (parts.some((p) => !p)) {
        const err = new Error(`L${line}:${col}: Invalid addition syntax in '${expr}'`);
        err.line = line;
        err.col = col;
        err.type = 'HCellParseError';
        throw err;
      }
      const unquoted = parts.map((p) => p.replace(/^'|'$/g, '').trim());
      if (unquoted.every((p) => getLetterByChar(p))) {
        return makeHybitSumChain(unquoted, line, col, bindingName, expr);
      }
      let acc = evalExpr(parts[0], line, col);
      for (let i = 1; i < parts.length; i += 1) {
        const rhs = evalExpr(parts[i], line, col);
        const isLast = i === parts.length - 1;
        if (acc.outputType !== rhs.outputType) {
          const err = new Error(
            `L${line}:${col}: Cannot add ${acc.outputType} and ${rhs.outputType}`,
          );
          err.line = line;
          err.col = col;
          err.type = 'CellSemanticError';
          throw err;
        }
        if (acc.outputType === 'hybit') {
          const vec =
            acc.staticVector && rhs.staticVector
              ? acc.staticVector.map((v, k) => v + rhs.staticVector[k])
              : null;
          const maxComp = vec ? Math.max(...vec) : null;
          acc = addNode('HYBIT_ADD', 'hybit', isLast ? expr : `${acc.sourceGlyphs} + ${rhs.sourceGlyphs}`, line, col, {
            bindingName: isLast ? bindingName : null,
            inputs: [acc.cellId, rhs.cellId],
            letterSequence:
              acc.letterSequence.length && rhs.letterSequence.length
                ? [...acc.letterSequence, ...rhs.letterSequence]
                : [],
            staticVector: vec,
            maxComponent: maxComp,
            provenInH: acc.provenInH && rhs.provenInH,
            hardware8BitSafe: Boolean(maxComp !== null && maxComp <= 255),
            hstarCoupledBoundProven: Boolean(
              vec && maxComp <= 255 && vec[17] === vec[7] && 2 * vec[17] <= vec[0],
            ),
          });
        } else if (acc.outputType === 'scalar') {
          acc = addNode('SCALAR_ADD', 'scalar', isLast ? expr : `${acc.sourceGlyphs} + ${rhs.sourceGlyphs}`, line, col, {
            bindingName: isLast ? bindingName : null,
            inputs: [acc.cellId, rhs.cellId],
          });
        } else {
          const err = new Error(
            `L${line}:${col}: Domain error — ${acc.outputType} is outside monoid H and cannot be added`,
          );
          err.line = line;
          err.col = col;
          err.type = 'CellSemanticError';
          throw err;
        }
      }
      return acc;
    }

    // 11. Variable reference
    if (bindings.has(expr)) {
      return bindings.get(expr);
    }

    const err = new Error(`L${line}:${col}: Unknown symbol or invalid expression '${expr}'`);
    err.line = line;
    err.col = col;
    err.type = 'HCellParseError';
    throw err;
  }

  // Parse line-by-line statements
  const rawLines = source.split('\n');
  let tokenEstimate = 0;

  try {
    for (let idx = 0; idx < rawLines.length; idx += 1) {
      const lineNum = idx + 1;
      const clean = rawLines[idx].split('//')[0].trim();
      if (!clean) continue;
      tokenEstimate += clean.split(/\s+/).length + 2;

      const stmt = clean.endsWith(';') ? clean.slice(0, -1).trim() : clean;

      // A. Guard check: `⊢ x` or `x.guard()`
      const guardMatch = stmt.match(/^⊢\s*(.+)$/) || stmt.match(/^(.+)\.guard\(\)$/);
      if (guardMatch) {
        const target = evalExpr(guardMatch[1].trim(), lineNum, 1);
        if (target.outputType !== 'hybit') {
          const err = new Error(
            `L${lineNum}:1: GUARD_CHECK (⊢ / .guard()) requires a hybit operand, got ${target.outputType}`,
          );
          err.line = lineNum;
          err.col = 1;
          err.type = 'CellSemanticError';
          throw err;
        }
        const discharged =
          target.provenInH && target.hardware8BitSafe && target.hstarCoupledBoundProven;
        addNode('GUARD_CHECK', 'bool', `⊢ ${target.sourceGlyphs}`, lineNum, 1, {
          inputs: [target.cellId],
          provenInH: target.provenInH,
          hardware8BitSafe: target.hardware8BitSafe,
          hstarCoupledBoundProven: target.hstarCoupledBoundProven,
          guardDischarged: discharged,
        });
        continue;
      }

      // B. Output emission: `↦ expr` or `println(expr)`
      const emitMatch = stmt.match(/^↦\s*(.+)$/) || stmt.match(/^println\(\s*(.+)\s*\)$/);
      if (emitMatch) {
        const valNode = evalExpr(emitMatch[1].trim(), lineNum, 1);
        if (valNode.outputType !== 'scalar') {
          const err = new Error(
            `L${lineNum}:1 [${valNode.cellId}]: EMIT_OUTPUT (↦ / println) requires a SCALAR operand, got ${valNode.outputType}`,
          );
          err.line = lineNum;
          err.col = 1;
          err.type = 'CellSemanticError';
          throw err;
        }
        addNode('EMIT_OUTPUT', 'void', `↦ ${valNode.sourceGlyphs}`, lineNum, 1, {
          inputs: [valNode.cellId],
        });
        continue;
      }

      // C. Variable binding: `let name = expr` or `name := expr` or `name = expr`
      const bindMatch =
        stmt.match(/^let\s+(?:mut\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*(?::\s*[a-zA-Z0-9_]+)?\s*=\s*(.+)$/) ||
        stmt.match(/^([^\s:=]+)\s*:=\s*(.+)$/) ||
        stmt.match(/^([^\s:=]+)\s*=\s*(.+)$/);
      if (bindMatch) {
        const varName = bindMatch[1].trim();
        const rhsExpr = bindMatch[2].trim();
        evalExpr(rhsExpr, lineNum, 1, varName);
        continue;
      }

      const err = new Error(`L${lineNum}:1: Unrecognized statement syntax '${stmt}'`);
      err.line = lineNum;
      err.col = 1;
      err.type = 'HCellParseError';
      throw err;
    }
  } catch (err) {
    const isSem = err.type === 'CellSemanticError';
    return {
      ok: false,
      failedStage: isSem ? 'STAGE_2_SEMANTIC' : 'STAGE_1_PARSE',
      errorType: err.type || 'HCellParseError',
      errorMessage: err.message,
      errorLine: err.line || 1,
      errorCol: err.col || 1,
      nodes,
      diagnostics: [
        `[FAIL] ${isSem ? 'Stage 2 (CELLIR Semantic)' : 'Stage 1 (INPUT Parse)'}: ${err.message}`,
      ],
    };
  }

  diagnostics.push(
    `[PASS] Stage 1 (INPUT): ${tokenEstimate} tokens → ${nodes.length} CellIR nodes (${isHcCompat ? 'HC v1.0' : 'Native .hcell'}).`,
  );

  // ── Stage 2: Semantic Summary ────────────────────────────────
  const guardNodes = nodes.filter((n) => n.op === 'GUARD_CHECK');
  const guardsDischarged = guardNodes.filter((n) => n.guardDischarged).length;
  const guardsRuntime = guardNodes.length - guardsDischarged;

  diagnostics.push(
    `[PASS] Stage 2 (CELLIR): ${nodes.length} nodes validated; guards discharged=${guardsDischarged}, runtime mandatory=${guardsRuntime}.`,
  );

  // ── Stage 3: H-ISA Codegen (Matching CellHISABackend) ────────
  const words = [];
  const assemblyLines = ['; Generated by HOM Web Compiler (CellHISABackend Parity)', 'main:'];
  const hregOf = new Map(); // cellId -> H-Reg index
  const gprOf = new Map(); // cellId -> GPR index
  let nextH = 1;
  let nativeLetterOps = 0;

  // Identify absorbed nodes in native letter chains
  const absorbed = new Set();
  const chainRoots = new Set();
  if (useNativeLetterOpcodes) {
    for (let i = nodes.length - 1; i >= 0; i -= 1) {
      const nd = nodes[i];
      if (absorbed.has(nd.cellId)) continue;
      if ((nd.op === 'HYBIT_ADD' || nd.op === 'WORD_ACCUM') && nd.letterSequence.length >= 2) {
        chainRoots.add(nd.cellId);
        // Check which inputs are only used inside this chain
        const collectChain = (curr) => {
          for (const inpId of curr.inputs) {
            const child = nodes.find((x) => x.cellId === inpId);
            if (!child) continue;
            const externalUses = nodes.filter(
              (other) => other.cellId !== curr.cellId && other.inputs.includes(inpId),
            );
            if (externalUses.length === 0) {
              absorbed.add(inpId);
            }
            collectChain(child);
          }
        };
        collectChain(nd);
      }
    }
  }

  function emitWord(opName, dst, s1, s2, imm, asmComment = '') {
    const code = OPCODE_BY_NAME[opName];
    words.push(encodeWord(code, dst, s1, s2, imm));
    assemblyLines.push(`        ${asmComment || `${opName} ${dst}, ${s1}, ${s2}, ${imm}`}`);
  }

  for (const nd of nodes) {
    if (absorbed.has(nd.cellId)) continue;

    if (chainRoots.has(nd.cellId) && nd.hardware8BitSafe) {
      const targetH = !hregOf.has('H0_USED') ? 0 : (nextH++ & 0xF);
      hregOf.set('H0_USED', true);
      emitWord('CZERO', 0, 0, 0, 0, 'CZERO   H0');
      for (const ch of nd.letterSequence) {
        const ent = getLetterByChar(ch);
        const lCode = 0xE0 + (ent.id - 1);
        const lName = Object.keys(OPCODE_BY_NAME).find((k) => OPCODE_BY_NAME[k] === lCode);
        emitWord(lName, 0, 0, 0, 0, `${ch}   ; ${lName} (0x${lCode.toString(16).toUpperCase()})`);
        nativeLetterOps += 1;
      }
      if (targetH !== 0) {
        emitWord('CMOV', targetH, 0, 0, 0, `CMOV    H${targetH}, H0`);
      }
      hregOf.set(nd.cellId, targetH);
    } else if (nd.op === 'WORD_ACCUM') {
      const h = nextH++ & 0xF;
      const firstEnt = getLetterByChar(nd.letterSequence[0]);
      emitWord('HLOAD', h, 0, 0, firstEnt.id, `HLOAD   H${h}, #${firstEnt.id}   ; ${firstEnt.char}`);
      for (let i = 1; i < nd.letterSequence.length; i += 1) {
        const ent = getLetterByChar(nd.letterSequence[i]);
        const tmpH = 15;
        emitWord('HLOAD', tmpH, 0, 0, ent.id, `HLOAD   H${tmpH}, #${ent.id}   ; ${ent.char}`);
        emitWord('HCADD', h, h, tmpH, 0, `HCADD   H${h}, H${h}, H${tmpH}`);
      }
      hregOf.set(nd.cellId, h);
    } else if (nd.op === 'LETTER_CONST') {
      const h = nextH++ & 0xF;
      const ent = MASTER_TABLE[nd.immParam - 1];
      emitWord('HLOAD', h, 0, 0, ent.id, `HLOAD   H${h}, #${ent.id}   ; ${ent.char} ${ent.name}`);
      hregOf.set(nd.cellId, h);
    } else if (nd.op === 'HYBIT_ADD') {
      const lh = hregOf.get(nd.inputs[0]) ?? 0;
      const rh = hregOf.get(nd.inputs[1]) ?? 1;
      const h = nextH++ & 0xF;
      emitWord('HCADD', h, lh, rh, 0, `HCADD   H${h}, H${lh}, H${rh}`);
      hregOf.set(nd.cellId, h);
    } else if (nd.op === 'SCALAR_CONST') {
      const r = 1;
      emitWord('MOVI', r, 0, 0, nd.immParam & 0xFFF, `MOVI    R${r}, #${nd.immParam}`);
      gprOf.set(nd.cellId, r);
    } else if (nd.op === 'SCALAR_ADD') {
      const lr = gprOf.get(nd.inputs[0]) ?? 1;
      const rr = gprOf.get(nd.inputs[1]) ?? 2;
      emitWord('ADD', 1, lr, rr, 0, `ADD     R1, R${lr}, R${rr}`);
      gprOf.set(nd.cellId, 1);
    } else if (nd.op === 'PROJ_THETA' || nd.op === 'PROJ_HSTAR' || nd.op === 'PROJ_COMPONENT') {
      const sh = hregOf.get(nd.inputs[0]) ?? 0;
      const slot = nd.op === 'PROJ_THETA' ? 0 : nd.op === 'PROJ_HSTAR' ? 17 : nd.immParam;
      emitWord('CGET', 1, sh, 0, slot, `CGET    R1, H${sh}, #${slot}`);
      gprOf.set(nd.cellId, 1);
    } else if (nd.op === 'TURNING_U') {
      const sh = hregOf.get(nd.inputs[0]) ?? 0;
      emitWord('CU', 1, sh, 0, 0, `CU      R1, H${sh}   ; B = U(h)`);
      gprOf.set(nd.cellId, 1);
    } else if (nd.op === 'TURNING_RHO') {
      const sh = hregOf.get(nd.inputs[0]) ?? 0;
      emitWord('CRHO', 1, sh, 0, 0, `CRHO    R1, H${sh}   ; R = ρ(h)`);
      gprOf.set(nd.cellId, 1);
    } else if (nd.op === 'MOD4_GATE') {
      const sh = hregOf.get(nd.inputs[0]) ?? 0;
      emitWord('CMOD4', 1, sh, 0, 0, `CMOD4   R1, H${sh}`);
      gprOf.set(nd.cellId, 1);
    } else if (nd.op === 'NORM2_V14') {
      const sh = hregOf.get(nd.inputs[0]) ?? 0;
      emitWord('HNRM2', 1, sh, 0, 0, `HNRM2   R1, H${sh}`);
      gprOf.set(nd.cellId, 1);
    } else if (nd.op === 'DIST2_V14') {
      const ah = hregOf.get(nd.inputs[0]) ?? 0;
      const bh = hregOf.get(nd.inputs[1]) ?? 1;
      emitWord('HDIST', 1, ah, bh, 0, `HDIST   R1, H${ah}, H${bh}`);
      gprOf.set(nd.cellId, 1);
    } else if (nd.op === 'INNER_V14') {
      const ah = hregOf.get(nd.inputs[0]) ?? 0;
      const bh = hregOf.get(nd.inputs[1]) ?? 1;
      if (useNativeHdot) {
        emitWord('HDOT', 1, ah, bh, 0, `HDOT    R1, H${ah}, H${bh}`);
      } else {
        const tmpH = 14;
        emitWord('HCADD', tmpH, ah, bh, 0, `HCADD   H${tmpH}, H${ah}, H${bh}`);
        emitWord('HNRM2', 1, tmpH, 0, 0, `HNRM2   R1, H${tmpH}`);
        emitWord('HNRM2', 2, ah, 0, 0, `HNRM2   R2, H${ah}`);
        emitWord('SUB', 1, 1, 2, 0, 'SUB     R1, R1, R2');
        emitWord('HNRM2', 2, bh, 0, 0, `HNRM2   R2, H${bh}`);
        emitWord('SUB', 1, 1, 2, 0, 'SUB     R1, R1, R2');
        emitWord('SHRI', 1, 1, 0, 1, 'SHRI    R1, R1, #1');
      }
      gprOf.set(nd.cellId, 1);
    } else if (nd.op === 'GUARD_CHECK') {
      const sh = hregOf.get(nd.inputs[0]) ?? 0;
      if (nd.guardDischarged) {
        assemblyLines.push(`        ; HGRD H${sh} elided statically (Layer A & Layer B proven)`);
      } else {
        emitWord('HGRD', 0, sh, 0, 0, `HGRD    H${sh}`);
      }
    } else if (nd.op === 'EMIT_OUTPUT') {
      const sr = gprOf.get(nd.inputs[0]) ?? 1;
      emitWord('PRINT', 0, sr, 0, 0, `PRINT   R${sr}`);
    }
  }

  emitWord('HALT', 0, 0, 0, 0, 'HALT');

  // Stage 3: Verify 4-B′ Control Flow
  const cfReport = verifyControlFlow4BPrime(words, loadAddr);
  if (!cfReport.valid) {
    diagnostics.push(`[FAIL] Stage 3 (VERIFY 4-B′): ${cfReport.reason}`);
    return {
      ok: false,
      failedStage: 'STAGE_3_CONTROL_FLOW_4B',
      errorType: 'ControlFlowVerificationError',
      errorMessage: cfReport.reason,
      nodes,
      words,
      assemblyLines,
      diagnostics,
    };
  }
  diagnostics.push(
    `[PASS] Stage 3 (VERIFY 4-B′): CFG valid (${words.length} words) & Overlay 4-B′ status='${cfReport.reason}'.`,
  );

  // Stage 4: HPG1 v2 Container & CHECKSUM32
  const hpg1 = buildHPG1Container(words, [], loadAddr);
  if (tamperChecksum && hpg1.containerWords.length > 7) {
    hpg1.containerWords[7] = (hpg1.containerWords[7] ^ 0x1) >>> 0;
  }
  const hpg1Verify = verifyHPG1Container(hpg1);
  if (!hpg1Verify.ok) {
    const msg = !hpg1Verify.checksumValid
      ? `CHECKSUM32 mismatch (stored=0x${hpg1Verify.storedChecksum32.toString(16).toUpperCase()}, computed=0x${hpg1Verify.computedChecksum32.toString(16).toUpperCase()})`
      : hpg1Verify.overlay4BReason;
    diagnostics.push(`[FAIL] Stage 4 (HPG1 v2 Integrity): ${msg}`);
    return {
      ok: false,
      failedStage: 'STAGE_4_HPG1_CHECKSUM',
      errorType: 'HPG1IntegrityError',
      errorMessage: msg,
      nodes,
      words,
      assemblyLines,
      hpg1,
      hpg1Verify,
      diagnostics,
    };
  }

  diagnostics.push(
    `[PASS] Stage 4 (HPG1 v2): MAGIC=${hpg1.magicHex} ('HPG1'), VERSION=${hpg1.version}, WORDS=${hpg1.programWords}, CHECKSUM32=${hpg1.checksumHex} (PASS).`,
  );

  const elapsedMs = (typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0;

  return {
    ok: true,
    failedStage: null,
    sourceLanguage: isHcCompat ? 'hc_v1' : 'hcell',
    tokenCount: tokenEstimate,
    elapsedMs: Number(elapsedMs.toFixed(2)),
    nodes,
    semanticSummary: {
      nodeCount: nodes.length,
      guardsTotal: guardNodes.length,
      guardsDischarged,
      guardsRuntime,
    },
    words,
    decodedWords: words.map((w, idx) => ({ index: idx, ...decodeWord(w) })),
    assemblyLines,
    assemblyText: assemblyLines.join('\n'),
    nativeLetterOps,
    cfReport,
    hpg1,
    hpg1Verify,
    diagnostics,
  };
}

export const HC_WEB_EXAMPLES = {
  '1. بسم Benchmark (HC v1.0)': `// HC v1.0 — Official ب + س + م Benchmark
let b = 'ب';
let s = 'س';
let m = 'م';
let bsm = b + s + m;
bsm.guard();
println(bsm.theta());
println(bsm.U());
println(bsm.rho());
println(bsm.norm2());
println(b.dist2(m));`,

  '2. بسم Benchmark (Native .hcell)': `// Native Hijaiyyah Cells (.hcell)
بسم := ب + س + م;
⊢ بسم;
↦ Θ̂(بسم);
↦ U(بسم);
↦ ρ(بسم);
↦ ‖بسم‖²;
↦ d₂²(ب, م);`,

  '3. Polarization vs Inner Product ⟨ج, هـ⟩': `// Compare inner product ⟨ج, هـ⟩₁₄ and norms
let jim = 'ج';
let haa = 'هـ';
let sum = jim + haa;
sum.guard();
println(jim.norm2());
println(haa.norm2());
println(jim.dot(haa));
println(jim.dist2(haa));`,

  '4. All 28 Letters Word Integral': `// Sum all 28 canonical Hijaiyyah letters (0xE0–0xFB)
ابجد := ⟪ا ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن و هـ ي⟫;
⊢ ابجد;
↦ Θ̂(ابجد);
↦ U(ابجد);
↦ ρ(ابجد);
↦ ‖ابجد‖²;`,

  '5. Diagnostic: Orthographic Policy Error (ة)': `// Ta Marbuthah 'ة' (U+0629) is outside H_28 -> L2:4 Error
طاقة := ب + س;
↦ Θ̂(طاقة);`,

  '6. Diagnostic: Semantic Domain Error (println Hybit)': `// println / ↦ requires SCALAR, not raw 18D HYBIT -> L3:1 Error
let bsm = 'ب' + 'س' + 'م';
println(bsm);`,
};
