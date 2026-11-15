/* ═══════════════════════════════════════════════════════════════════
   HOM v1.2.0 — HC IDE & HVM INTERACTIVE WEB SIMULATOR (P2-A / P2-B / P2-C)
   Hijaiyyah Scientific Computing Environment
   Palette: Midnight #071426 · Surface #10243A · Cyan #26C6DA · Gold #D6AF57 · Text #EAF2FA
   ═══════════════════════════════════════════════════════════════════ */

import { useState, useRef } from 'react';
import { compileHCOrHCell, HC_WEB_EXAMPLES } from '../engine/hcCompiler.js';
import { HVMSimulator, EXECUTION_PROVENANCE } from '../engine/hvmSimulator.js';
import { checkAllGuards } from '../engine/guards.js';

const HREG_SLOTS = [
  'Θ̂', 'Na', 'Nb', 'Nd',
  'Kp', 'Kx', 'Ks', 'Ka', 'Kc',
  'Qp', 'Qx', 'Qs', 'Qa', 'Qc',
  'AN', 'AK', 'AQ', 'H*',
];

const PIPELINE_STEPS = [
  { id: 'STAGE_1', num: '01', name: 'HC / .hcell Source', sub: 'Lexer · Parser · Orthographic' },
  { id: 'STAGE_2', num: '02', name: 'CellIR & Semantic', sub: 'Node Graph · Types · 2-Layer Proof' },
  { id: 'STAGE_3', num: '03', name: 'Compiler / H-ISA', sub: '4-B′ Verifier · HPG1 v2' },
  { id: 'STAGE_4', num: '04', name: 'HVM Simulator', sub: 'Step · Run · Pause · Reset' },
  { id: 'STAGE_5', num: '05', name: 'Trace & Results', sub: 'Registers · Guards · Outputs' },
];

export default function Simulator() {
  const [selectedExample, setSelectedExample] = useState('1. بسم Benchmark (HC v1.0)');
  const [source, setSource] = useState(HC_WEB_EXAMPLES['1. بسم Benchmark (HC v1.0)']);
  const [nativeLetterOps, setNativeLetterOps] = useState(true);
  const [nativeHdot, setNativeHdot] = useState(false);
  const [tamperChecksum, setTamperChecksum] = useState(false);
  const [activeIdeTab, setActiveIdeTab] = useState('cellir'); // 'cellir' | 'hisa' | 'hpg1'
  const [selectedHreg, setSelectedHreg] = useState(0);

  // Initial static compilation of default example (does NOT auto-run HVM)
  const [compilation, setCompilation] = useState(() =>
    compileHCOrHCell(HC_WEB_EXAMPLES['1. بسم Benchmark (HC v1.0)'], {
      useNativeLetterOpcodes: true,
    }),
  );

  const hvmRef = useRef(
    new HVMSimulator(compilation.ok ? compilation.words : []),
  );
  const [vmState, setVmState] = useState(() => hvmRef.current.getState());

  const handleLoadExample = (name) => {
    const src = HC_WEB_EXAMPLES[name] || '';
    setSelectedExample(name);
    setSource(src);
    const comp = compileHCOrHCell(src, {
      useNativeLetterOpcodes: nativeLetterOps,
      useNativeHdot: nativeHdot,
      tamperChecksum,
    });
    setCompilation(comp);
    hvmRef.current.loadProgram(comp.ok ? comp.words : []);
    setVmState(hvmRef.current.getState());
  };

  const handleCompileAndLoad = () => {
    const comp = compileHCOrHCell(source, {
      useNativeLetterOpcodes: nativeLetterOps,
      useNativeHdot: nativeHdot,
      tamperChecksum,
    });
    setCompilation(comp);
    hvmRef.current.loadProgram(comp.ok ? comp.words : []);
    setVmState(hvmRef.current.getState());
  };

  const handleStep = () => {
    if (!compilation.ok) return;
    hvmRef.current.step();
    setVmState(hvmRef.current.getState());
  };

  const handleRunAll = () => {
    if (!compilation.ok) return;
    hvmRef.current.run(5000);
    setVmState(hvmRef.current.getState());
  };

  const handlePause = () => {
    hvmRef.current.pause();
    setVmState(hvmRef.current.getState());
  };

  const handleReset = () => {
    hvmRef.current.reset();
    setVmState(hvmRef.current.getState());
  };

  const sourceLines = source.split('\n');
  const activeHvec = vmState.hreg[selectedHreg] || Array.from({ length: 18 }, () => 0);
  const activeGuards = checkAllGuards(activeHvec);
  const hstarConsistency = 2 * activeHvec[17] <= activeHvec[0];

  return (
    <div className="space-y-6 max-w-[1440px] mx-auto text-[#EAF2FA]">

      {/* ─── TOP HEADER & PROVENANCE BADGES ─── */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between border-b border-[#1C3552] pb-4 gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#EAF2FA] font-sans">
            HC IDE &amp; HVM Interactive Simulator
          </h1>
          <p className="text-xs text-[#8AA0B8] mt-1 font-mono">
            Hijaiyyah Scientific Computing Environment · HOM v1.2.0 · Dataset Seal: HM-28-v1.0-HC18D
          </p>
        </div>

        {/* Strict Separation: SIMULATED vs ON-BOARD VERIFIED */}
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="inline-flex items-center gap-1.5 text-xs font-mono font-bold px-3 py-1.5 rounded border border-[#26C6DA] bg-[#10243A] text-[#26C6DA]"
            title={EXECUTION_PROVENANCE.SIMULATED.description}
          >
            ● {EXECUTION_PROVENANCE.SIMULATED.badge}
          </span>
          <span
            className="inline-flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded border border-[#1C3552] bg-[#071426] text-[#8AA0B8]"
            title="Browser execution does not claim physical FPGA execution"
          >
            FPGA Status: Separate Hardware Target (Not Claimed in Web Sim)
          </span>
        </div>
      </div>

      {/* ─── P2-C: 5-STAGE INTEGRATED PIPELINE BAR ─── */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2.5">
        {PIPELINE_STEPS.map((st, idx) => {
          let ok = compilation.ok;
          if (idx === 0) ok = compilation.failedStage !== 'STAGE_1_PARSE';
          if (idx === 1) ok = compilation.failedStage !== 'STAGE_1_PARSE' && compilation.failedStage !== 'STAGE_2_SEMANTIC';
          if (idx === 3 || idx === 4) ok = compilation.ok && !vmState.trap;
          return (
            <div
              key={st.id}
              className="rounded border border-[#1C3552] bg-[#10243A] px-3.5 py-2.5 flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono font-bold text-[#D6AF57]">{st.num}</span>
                <span
                  className="text-[10px] font-mono font-bold"
                  style={{ color: ok ? '#2ECC71' : '#EF5350' }}
                >
                  {ok ? '✓ PASS' : '✗ FAULT'}
                </span>
              </div>
              <div className="text-xs font-bold text-[#EAF2FA] mt-1">{st.name}</div>
              <div className="text-[10px] text-[#8AA0B8] font-mono">{st.sub}</div>
            </div>
          );
        })}
      </div>

      {/* ─── CONTROL TOOLBAR ─── */}
      <div className="rounded-lg border border-[#1C3552] bg-[#10243A] p-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-mono text-[#8AA0B8]">Program:</span>
          <select
            value={selectedExample}
            onChange={(e) => handleLoadExample(e.target.value)}
            className="bg-[#071426] border border-[#1C3552] rounded px-3 py-1.5 text-xs font-mono text-[#EAF2FA]"
          >
            {Object.keys(HC_WEB_EXAMPLES).map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>

          <label className="inline-flex items-center gap-1.5 text-xs font-mono text-[#EAF2FA] ml-2">
            <input
              type="checkbox"
              checked={nativeLetterOps}
              onChange={(e) => setNativeLetterOps(e.target.checked)}
            />
            0xE0–0xFB Letter Ops
          </label>

          <label className="inline-flex items-center gap-1.5 text-xs font-mono text-[#EAF2FA] ml-2">
            <input
              type="checkbox"
              checked={nativeHdot}
              onChange={(e) => setNativeHdot(e.target.checked)}
            />
            HDOT (0x52)
          </label>

          <label className="inline-flex items-center gap-1.5 text-xs font-mono text-[#D6AF57] ml-2">
            <input
              type="checkbox"
              checked={tamperChecksum}
              onChange={(e) => setTamperChecksum(e.target.checked)}
            />
            Tamper CHECKSUM32
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleCompileAndLoad}
            className="px-3.5 py-1.5 rounded bg-[#26C6DA] text-[#071426] font-semibold text-xs font-sans hover:opacity-90"
          >
            Compile &amp; Load HVM
          </button>
          <button
            onClick={handleStep}
            disabled={!compilation.ok || vmState.halted}
            className="px-3 py-1.5 rounded border border-[#26C6DA] bg-[#071426] text-[#26C6DA] font-mono text-xs disabled:opacity-40"
          >
            ⏭ Step
          </button>
          <button
            onClick={handleRunAll}
            disabled={!compilation.ok || vmState.halted}
            className="px-3.5 py-1.5 rounded border border-[#2ECC71] bg-[#071426] text-[#2ECC71] font-mono font-bold text-xs disabled:opacity-40"
          >
            ▶ Run
          </button>
          <button
            onClick={handlePause}
            className="px-3 py-1.5 rounded border border-[#D6AF57] bg-[#071426] text-[#D6AF57] font-mono text-xs"
          >
            ⏸ Pause
          </button>
          <button
            onClick={handleReset}
            className="px-3 py-1.5 rounded border border-[#1C3552] bg-[#071426] text-[#EAF2FA] font-mono text-xs"
          >
            ⟳ Reset
          </button>
        </div>
      </div>

      {/* ─── MAIN WORKSPACE GRID: P2-A (HC IDE) + P2-B (HVM SIMULATOR) ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">

        {/* ═══ LEFT COLUMN (5 cols): P2-A HC / .hcell SOURCE EDITOR & DIAGNOSTICS ═══ */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <div className="rounded-lg border border-[#1C3552] bg-[#10243A] overflow-hidden flex flex-col">
            <div className="bg-[#071426] px-4 py-2.5 border-b border-[#1C3552] flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#8AA0B8]">
                SOURCE EDITOR (HC v1.0 / .hcell)
              </span>
              <span className="text-xs font-mono text-[#D6AF57]">
                {compilation.sourceLanguage === 'hc_v1' ? 'HC v1.0 Mode' : 'Native .hcell Mode'} · {sourceLines.length} lines
              </span>
            </div>

            <div className="flex bg-[#050E1B] min-h-[260px]">
              {/* Line Number Gutter */}
              <div className="select-none bg-[#0C1C30] text-[#8AA0B8] font-mono text-xs py-3 px-2.5 text-right border-r border-[#1C3552]">
                {sourceLines.map((_, i) => (
                  <div
                    key={i}
                    className={`leading-6 ${
                      !compilation.ok && compilation.errorLine === i + 1
                        ? 'text-[#EF5350] font-bold'
                        : ''
                    }`}
                  >
                    {String(i + 1).padStart(2, '0')}
                  </div>
                ))}
              </div>

              {/* Editable Source Textarea */}
              <textarea
                value={source}
                onChange={(e) => setSource(e.target.value)}
                spellCheck={false}
                className="flex-1 bg-transparent text-[#EAF2FA] font-mono text-xs p-3 leading-6 focus:outline-none resize-y min-h-[260px]"
              />
            </div>

            {/* Inline Syntax / Semantic Error Banner with Line & Column */}
            {!compilation.ok && (
              <div className="bg-[#EF5350]/15 border-t border-[#EF5350] px-4 py-2.5 text-xs font-mono text-[#EF5350]">
                <div className="font-bold">
                  ✗ {compilation.errorType} at Line {compilation.errorLine || 1}, Col {compilation.errorCol || 1}
                </div>
                <div className="mt-0.5 text-[#EAF2FA]">{compilation.errorMessage}</div>
              </div>
            )}
          </div>

          {/* Stage-by-Stage Compiler & Checksum Diagnostics */}
          <div className="rounded-lg border border-[#1C3552] bg-[#10243A] p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-[#26C6DA]">
                COMPILER &amp; 4-B′ DIAGNOSTICS (STAGES 1–4)
              </span>
              <span
                className="text-xs font-mono font-bold"
                style={{ color: compilation.ok ? '#2ECC71' : '#EF5350' }}
              >
                {compilation.ok ? '4 / 4 STAGES PASS' : `HALTED AT ${compilation.failedStage}`}
              </span>
            </div>
            <div className="space-y-1.5 font-mono text-[11px] bg-[#050E1B] p-3 rounded border border-[#1C3552]">
              {(compilation.diagnostics || []).map((d, i) => (
                <div
                  key={i}
                  style={{
                    color: d.startsWith('[PASS]')
                      ? '#2ECC71'
                      : d.startsWith('[FAIL]')
                        ? '#EF5350'
                        : '#D6AF57',
                  }}
                >
                  {d}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ═══ RIGHT COLUMN (7 cols): CELLIR / H-ISA / HPG1 + HVM SIMULATOR ═══ */}
        <div className="lg:col-span-7 flex flex-col gap-4">

          {/* Upper Panel: Tabbed CellIR Inspector | H-ISA Bytecode | HPG1 v2 Container */}
          <div className="rounded-lg border border-[#1C3552] bg-[#10243A] overflow-hidden">
            <div className="bg-[#071426] px-4 py-2 border-b border-[#1C3552] flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                {[
                  { id: 'cellir', label: `CellIR Inspector (${compilation.nodes?.length || 0})` },
                  { id: 'hisa', label: `H-ISA Bytecode (${compilation.words?.length || 0} words)` },
                  { id: 'hpg1', label: 'HPG1 v2 Container' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveIdeTab(tab.id)}
                    className={`px-3 py-1 rounded text-xs font-mono font-semibold transition-colors ${
                      activeIdeTab === tab.id
                        ? 'bg-[#26C6DA] text-[#071426]'
                        : 'bg-[#10243A] text-[#8AA0B8] hover:text-[#EAF2FA]'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-2 text-[10px] font-mono">
                <span className="px-2 py-0.5 rounded bg-[#071426] border border-[#1C3552] text-[#2ECC71]">
                  Parsed
                </span>
                <span className="px-2 py-0.5 rounded bg-[#071426] border border-[#1C3552] text-[#2ECC71]">
                  Semantic OK
                </span>
                <span className="px-2 py-0.5 rounded bg-[#071426] border border-[#1C3552] text-[#2ECC71]">
                  Guard OK
                </span>
              </div>
            </div>

            <div className="p-3 max-h-[230px] overflow-y-auto bg-[#050E1B]">
              {activeIdeTab === 'cellir' && (
                <table className="w-full text-xs font-mono border-collapse">
                  <thead>
                    <tr className="text-left text-[#26C6DA] border-b border-[#1C3552]">
                      <th className="py-1.5 px-2">Cell ID</th>
                      <th className="py-1.5 px-2">Operation</th>
                      <th className="py-1.5 px-2">Type</th>
                      <th className="py-1.5 px-2">In H (G1–T2)</th>
                      <th className="py-1.5 px-2">8-Bit Safe</th>
                      <th className="py-1.5 px-2">Source Glyphs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(compilation.nodes || []).map((nd) => (
                      <tr key={nd.cellId} className="border-b border-[#1C3552]/50">
                        <td className="py-1 px-2 text-[#EAF2FA]">{nd.cellId}</td>
                        <td className="py-1 px-2 text-[#D6AF57]">{nd.op}</td>
                        <td className="py-1 px-2 text-[#EAF2FA]">{nd.outputType}</td>
                        <td className="py-1 px-2 text-[#2ECC71]">
                          {nd.provenInH ? 'PASS' : 'DYNAMIC'}
                        </td>
                        <td className="py-1 px-2 text-[#26C6DA]">
                          {nd.hardware8BitSafe ? 'SAFE' : 'RUNTIME'}
                        </td>
                        <td className="py-1 px-2 text-[#EAF2FA]">{nd.sourceGlyphs}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {activeIdeTab === 'hisa' && (
                <table className="w-full text-xs font-mono border-collapse">
                  <thead>
                    <tr className="text-left text-[#26C6DA] border-b border-[#1C3552]">
                      <th className="py-1.5 px-2">PC</th>
                      <th className="py-1.5 px-2">Hex Word</th>
                      <th className="py-1.5 px-2">Target</th>
                      <th className="py-1.5 px-2">Disassembly</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(compilation.decodedWords || []).map((dw) => {
                      const isCurrentPc = vmState.pc === dw.index && !vmState.halted;
                      return (
                        <tr
                          key={dw.index}
                          className={`border-b border-[#1C3552]/50 ${
                            isCurrentPc ? 'bg-[#26C6DA]/20' : ''
                          }`}
                        >
                          <td className="py-1 px-2 text-[#D6AF57]">
                            {isCurrentPc ? `▶ ${dw.index}` : dw.index}
                          </td>
                          <td className="py-1 px-2 text-[#2ECC71]">{dw.hex}</td>
                          <td className="py-1 px-2 text-[#26C6DA]">
                            {dw.isRtl ? 'RTL (HCPU)' : 'SW-ONLY'}
                          </td>
                          <td className="py-1 px-2 text-[#EAF2FA]">{dw.disassembly}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}

              {activeIdeTab === 'hpg1' && compilation.hpg1 && (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-1">
                  {[
                    ['MAGIC', `${compilation.hpg1.magicHex} ('HPG1')`],
                    ['VERSION', String(compilation.hpg1.version)],
                    ['WORDS', String(compilation.hpg1.programWords)],
                    ['LOAD_ADDR', compilation.hpg1.loadAddrHex],
                    ['ENTRY', compilation.hpg1.entryAddrHex],
                    ['CHECKSUM32', compilation.hpg1.checksumHex],
                  ].map(([k, v]) => (
                    <div
                      key={k}
                      className="rounded border border-[#1C3552] bg-[#10243A] p-2.5 font-mono"
                    >
                      <div className="text-[10px] text-[#8AA0B8]">{k}</div>
                      <div
                        className="text-sm font-bold mt-1"
                        style={{
                          color:
                            k === 'CHECKSUM32'
                              ? compilation.hpg1Verify?.checksumValid
                                ? '#2ECC71'
                                : '#EF5350'
                              : '#EAF2FA',
                        }}
                      >
                        {v}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Lower Panel: P2-B HVM INTERACTIVE SIMULATOR (Registers, Guards, Outputs, Trace) */}
          <div className="rounded-lg border border-[#1C3552] bg-[#10243A] p-4 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#1C3552] pb-2.5">
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold uppercase tracking-wider text-[#26C6DA]">
                  HVM CPU STATE &amp; REGISTER VIEWER
                </span>
                <span className="text-xs font-mono text-[#D6AF57]">
                  PC: {vmState.pc} · Cycle: {vmState.cycle} · Status:{' '}
                  {vmState.trap ? 'TRAP' : vmState.halted ? 'HALTED' : 'READY'}
                </span>
              </div>
              <div className="flex items-center gap-2 font-mono text-xs">
                <span
                  className={`px-2 py-0.5 rounded border ${
                    vmState.flags.GUARD_PASS
                      ? 'border-[#2ECC71] text-[#2ECC71]'
                      : 'border-[#EF5350] text-[#EF5350]'
                  }`}
                >
                  SR.GUARD_PASS: {vmState.flags.GUARD_PASS ? '1 (PASS)' : '0 (FAIL)'}
                </span>
                <span className="px-2 py-0.5 rounded border border-[#1C3552] text-[#8AA0B8]">
                  Z={vmState.flags.Z ? 1 : 0} · LT={vmState.flags.LT ? 1 : 0}
                </span>
              </div>
            </div>

            {/* Scalar GPRs R0–R7 + Output Stream */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
              <div className="md:col-span-8 grid grid-cols-4 gap-2">
                {vmState.gpr.slice(0, 8).map((val, idx) => {
                  const changed = vmState.lastDelta?.changedGpr?.includes(idx);
                  return (
                    <div
                      key={idx}
                      className={`rounded border px-2.5 py-1.5 font-mono text-xs ${
                        changed
                          ? 'border-[#26C6DA] bg-[#26C6DA]/15'
                          : 'border-[#1C3552] bg-[#071426]'
                      }`}
                    >
                      <span className="text-[#8AA0B8]">R{idx}: </span>
                      <span className="text-[#EAF2FA] font-bold">{val}</span>
                    </div>
                  );
                })}
              </div>

              {/* HVM Output Stream Box */}
              <div className="md:col-span-4 rounded border border-[#1C3552] bg-[#050E1B] p-2.5 font-mono">
                <div className="text-[10px] text-[#D6AF57] font-bold uppercase">
                  HVM Output Stream (PRINT 0xA0)
                </div>
                <div className="text-sm font-bold text-[#2ECC71] mt-1">
                  {vmState.outputs.length > 0
                    ? `[ ${vmState.outputs.join(', ')} ]`
                    : '— (No outputs yet)'}
                </div>
              </div>
            </div>

            {/* 18D Hybit Register Inspector (H0–H3) & 6 Canonical Guards */}
            <div className="rounded border border-[#1C3552] bg-[#071426] p-3 space-y-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-mono text-[#8AA0B8] mr-1">Inspect H-Reg:</span>
                  {[0, 1, 2, 3].map((hIdx) => {
                    const changed = vmState.lastDelta?.changedHreg?.includes(hIdx);
                    return (
                      <button
                        key={hIdx}
                        onClick={() => setSelectedHreg(hIdx)}
                        className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold border ${
                          selectedHreg === hIdx
                            ? 'bg-[#26C6DA] text-[#071426] border-[#26C6DA]'
                            : changed
                              ? 'border-[#D6AF57] text-[#D6AF57]'
                              : 'border-[#1C3552] text-[#8AA0B8]'
                        }`}
                      >
                        H{hIdx}
                      </button>
                    );
                  })}
                </div>

                {/* Live G1–G4, T1–T2 + 2H* <= Theta Badges */}
                <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
                  {activeGuards.map((g) => (
                    <span
                      key={g.id}
                      title={g.formula}
                      className={`px-2 py-0.5 rounded border ${
                        g.pass
                          ? 'border-[#2ECC71]/50 text-[#2ECC71]'
                          : 'border-[#EF5350] text-[#EF5350]'
                      }`}
                    >
                      {g.id}:{g.pass ? '✓' : '✗'}
                    </span>
                  ))}
                  <span
                    className={`px-2 py-0.5 rounded border ${
                      hstarConsistency
                        ? 'border-[#26C6DA]/50 text-[#26C6DA]'
                        : 'border-[#D6AF57] text-[#D6AF57]'
                    }`}
                  >
                    2H*≤Θ̂:{hstarConsistency ? '✓' : '✗'}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-6 sm:grid-cols-9 gap-1.5 font-mono text-[11px]">
                {HREG_SLOTS.map((slot, sIdx) => (
                  <div
                    key={slot}
                    className="rounded bg-[#10243A] border border-[#1C3552] px-1.5 py-1 text-center"
                  >
                    <div className="text-[9px] text-[#8AA0B8]">{slot}</div>
                    <div
                      className={`font-bold ${
                        activeHvec[sIdx] !== 0 ? 'text-[#26C6DA]' : 'text-[#EAF2FA]'
                      }`}
                    >
                      {activeHvec[sIdx]}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Execution Trace Log */}
            <div className="rounded border border-[#1C3552] bg-[#050E1B] p-3">
              <div className="text-[10px] font-mono font-bold uppercase text-[#8AA0B8] mb-1.5">
                H-ISA Execution Trace ({vmState.trace.length} retired instructions)
              </div>
              <div className="max-h-[120px] overflow-y-auto space-y-1 font-mono text-[11px]">
                {vmState.trace.length === 0 ? (
                  <div className="text-[#8AA0B8]">
                    Machine idle at PC=0. Click &apos;⏭ Step&apos; or &apos;▶ Run&apos; to execute instructions.
                  </div>
                ) : (
                  vmState.trace.map((tr) => (
                    <div key={tr.cycle} className="flex items-center gap-3">
                      <span className="text-[#8AA0B8]">[{String(tr.cycle).padStart(3, '0')}]</span>
                      <span className="text-[#D6AF57]">PC={tr.pc}</span>
                      <span className="text-[#26C6DA]">{tr.hex}</span>
                      <span className="text-[#EAF2FA]">{tr.description}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
