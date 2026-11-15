/* ═══════════════════════════════════════════════════════════════
   HIJAIYYAH SCIENTIFIC COMPUTING ENVIRONMENT — SYSTEM OVERVIEW
   HOM v1.2.0 · Commit 920f3e61 · HM-28-v1.0-HC18D
   Palette: Midnight #071426 · Surface #10243A · Cyan #26C6DA · Gold #D6AF57 · Text #EAF2FA
   ═══════════════════════════════════════════════════════════════ */

const STATUS = {
  OP:   { label: 'Operasional',    icon: '●', color: '#2ECC71', bg: 'rgba(46,204,113,0.10)',  border: '#1C3552' },
  SPEC: { label: 'Terspesifikasi', icon: '◐', color: '#D6AF57', bg: 'rgba(214,175,87,0.10)',  border: '#1C3552' },
  ASP:  { label: 'Aspirasional',   icon: '○', color: '#26C6DA', bg: 'rgba(38,198,218,0.10)',  border: '#1C3552' },
};

const METRIC_CARDS = [
  { label: 'Canonical Letters', value: '28 / 28', sub: 'HM-28 dataset', color: '#26C6DA' },
  { label: 'Hybit Dimensions',  value: '18D',     sub: '504 integer values', color: '#D6AF57' },
  { label: 'H-ISA Catalog',     value: '105',     sub: '84 RTL · 21 SW-only', color: '#26C6DA' },
  { label: 'Canonical Guards',  value: '6',       sub: 'G1–G4 · T1–T2', color: '#2ECC71' },
];

const PIPELINE_STAGES = [
  { num: '01', name: 'HC / .hcell', sub: 'Orthographic & EBNF Source' },
  { num: '02', name: 'CellIR',      sub: 'DAG/CFG & Two-Layer Proof' },
  { num: '03', name: '4-B′',        sub: 'Static Control Flow & Mask' },
  { num: '04', name: 'HPG1 v2',     sub: '7-Word Header & CHECKSUM32' },
  { num: '05', name: 'HVM / HCPU',  sub: '3-Way Parity Execution' },
];

function SectionTitle({ children, sub }) {
  return (
    <div className="mb-5">
      <h2 className="text-lg md:text-xl font-bold text-[#EAF2FA] tracking-tight font-sans">
        {children}
      </h2>
      {sub && <p className="text-xs text-[#8AA0B8] mt-1 font-mono">{sub}</p>}
    </div>
  );
}

function StatusBadge({ status }) {
  const s = STATUS[status];
  return (
    <span
      className="inline-flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-0.5 rounded border"
      style={{ color: s.color, borderColor: s.border, backgroundColor: s.bg }}
    >
      <span>{s.icon}</span>
      <span>{s.label}</span>
    </span>
  );
}

function InstructionChip({ name, color = '#26C6DA' }) {
  return (
    <span
      className="inline-block text-[11px] font-mono font-semibold px-2.5 py-1 rounded border mr-1.5 mb-1.5"
      style={{ color, borderColor: '#1C3552', backgroundColor: '#071426' }}
    >
      {name}
    </span>
  );
}

export default function System() {
  return (
    <div className="space-y-8 max-w-6xl mx-auto text-[#EAF2FA]">

      {/* ─── TOP SCIENTIFIC HEADER ─── */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between border-b border-[#1C3552] pb-5">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-[#EAF2FA] font-sans">
            System Overview
          </h1>
          <p className="text-sm text-[#8AA0B8] mt-1 font-sans">
            Hijaiyyah Scientific Computing Environment · HOM v1.2.0 · HM-28-v1.0-HC18D
          </p>
        </div>
        <div className="mt-3 md:mt-0">
          <span className="inline-flex items-center gap-2 text-xs font-mono font-bold px-3.5 py-1.5 rounded border border-[#1C3552] bg-[#10243A] text-[#2ECC71]">
            ● SYSTEM READY
          </span>
        </div>
      </div>

      {/* ═══════════ 4 PRIMARY METRIC CARDS ═══════════ */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {METRIC_CARDS.map((card) => (
          <div
            key={card.label}
            className="rounded-lg border border-[#1C3552] bg-[#10243A] p-5"
          >
            <div className="text-[11px] uppercase tracking-wider font-semibold text-[#8AA0B8]">
              {card.label}
            </div>
            <div
              className="text-3xl font-bold font-mono mt-2 mb-1"
              style={{ color: card.color }}
            >
              {card.value}
            </div>
            <div className="text-xs font-mono text-[#EAF2FA]">
              {card.sub}
            </div>
          </div>
        ))}
      </section>

      {/* ═══════════ 5-STAGE COMPUTATIONAL PIPELINE ═══════════ */}
      <section className="rounded-lg border border-[#1C3552] bg-[#10243A] p-6">
        <SectionTitle sub="End-to-End Formal Verification & Silicon Execution Path (.hcell → CellIR → 4-B′ → HPG1 v2 → HVM/HCPU)">
          Computational Pipeline
        </SectionTitle>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {PIPELINE_STAGES.map((st) => (
            <div
              key={st.num}
              className="rounded border border-[#1C3552] bg-[#071426] p-4 flex flex-col justify-between"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono font-bold text-[#D6AF57]">{st.num}</span>
                <span className="text-[10px] font-mono text-[#2ECC71]">● READY</span>
              </div>
              <div className="text-base font-bold text-[#EAF2FA] font-sans">{st.name}</div>
              <div className="text-[11px] text-[#8AA0B8] mt-1">{st.sub}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════ H-ISA INSTRUCTION CATALOG (105 OPCODES) ═══════════ */}
      <section className="rounded-lg border border-[#1C3552] bg-[#10243A] p-6">
        <SectionTitle sub="Synchronized with src/hijaiyyah/hisa/opcodes.py: 105 unique opcodes · 84 RTL-implemented · 21 software-only · 17 aliases">
          H-ISA Instruction Architecture
        </SectionTitle>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { cat: 'System & Scalars (RTL)', color: '#26C6DA', ops: ['NOP','HALT','MOV','MOVI','HNRM2','HDIST','ERET','SYSCALL','FRD','FWR','HALT_ERR'] },
            { cat: 'Arithmetic & Bitwise (RTL)', color: '#2ECC71', ops: ['ADD','ADDI','SUB','MUL','AND','OR','XOR','NOT','SHL','SHR','ANDI','ORI','XORI','SHLI','SHRI'] },
            { cat: 'Control Flow & Memory (RTL)', color: '#D6AF57', ops: ['CMP','CMPI','JMP','JEQ','JNE','JGD','JNGD','CALL','RET','LOAD','STORE','PUSH','POP'] },
            { cat: 'Codex & HISAB (RTL)', color: '#26C6DA', ops: ['HLOAD','HCADD','CGET','CSET','CMOV','CZERO','CEQ','CRHO','CU','CTHETA','CMOD4','HPACK','HCRC','HDOT'] },
            { cat: 'Guards, I/O & Letters (RTL)', color: '#2ECC71', ops: ['HGRD','PRINT','EMITS','L_ALIF..L_YA (28 opcodes 0xE0–0xFB)'] },
            { cat: 'Software-Only (21 in HVM)', color: '#D6AF57', ops: ['JGP','JGF','JNP','CSUB','CDOT','VNORM','VDIST','HEXMT','HDCMP','HSER','HDES','VSCL','HCHK','CHASH','CSIGN','HPROJ','VPROJ_T','VPROJ_N','VPROJ_K','VPROJ_Q','PRINTH'] },
          ].map((group) => (
            <div
              key={group.cat}
              className="rounded border border-[#1C3552] bg-[#071426] p-4"
            >
              <div
                className="text-xs font-mono font-bold uppercase tracking-wider mb-3"
                style={{ color: group.color }}
              >
                {group.cat}
              </div>
              <div className="flex flex-wrap">
                {group.ops.map((op) => (
                  <InstructionChip key={op} name={op} color={group.color} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════ FORMAL VERIFICATION & SYSTEM SUBSYSTEMS ═══════════ */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-lg border border-[#1C3552] bg-[#10243A] p-6">
          <SectionTitle sub="Mathematical & Structural Integrity">
            Formal Verification Suite
          </SectionTitle>
          <div className="space-y-3 text-xs font-mono">
            {[
              ['Canonical Guards (G1–G4, T1–T2)', '168 / 168 PASS (+ 2H* ≤ Θ̂ check)'],
              ['Static 4-B′ & HPG1 v2 CHECKSUM32', '80-opcode bitmap · depth ≤ 28 · K-8/K-10'],
              ['Master Table SHA-256 Seals', '5 / 5 verified (JSON, 252B, 504B, RTL, .hb)'],
              ['Pairwise Injectivity (v₁₈)', '378 / 378 unique pairs'],
              ['Exomatrix R1–R5 Audit', '140 / 140 relations verified'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-[#1C3552] pb-2">
                <span className="text-[#8AA0B8]">{k}</span>
                <span className="text-[#2ECC71] font-bold">{v}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-[#1C3552] bg-[#10243A] p-6">
          <SectionTitle sub="Silicon RTL (Gowin GW2AR-18C · Tang Nano 20K · 27 MHz)">
            HCPU Phase 2.0 & System Stack
          </SectionTitle>
          <div className="space-y-3 text-xs font-mono">
            {[
              ['HCPU Pipeline', '5-Stage (IF · ID · EX · MEM · WB) · CODEX_PROFILE=2'],
              ['FPGA Resource Utilization', '15,453 LUT4 (74%) · 5,166 DFF (33%) · 18 BSRAM'],
              ['Hardware Burn-In', '72 Hours PASS · 168.62M cycles · 0 board errors'],
              ['HOS & HFS (HFS1 v1)', 'Syscalls 1–9 · SD card sectors 1–3 & 16–20'],
              ['HOM Desktop Environment', '15 modular workbenches + System Overview sidebar'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-[#1C3552] pb-2">
                <span className="text-[#8AA0B8]">{k}</span>
                <span className="text-[#EAF2FA]">{v}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════ COMPONENT STATUS MATRIX ═══════════ */}
      <section className="rounded-lg border border-[#1C3552] bg-[#10243A] p-6">
        <SectionTitle sub="Aggregate implementation status across software and hardware layers">
          System Component Matrix
        </SectionTitle>

        <div className="overflow-x-auto rounded border border-[#1C3552]">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-[#071426] border-b border-[#1C3552]">
                <th className="text-left py-3 px-4 text-xs font-mono uppercase text-[#26C6DA]">Status</th>
                <th className="text-left py-3 px-4 text-xs font-mono uppercase text-[#26C6DA]">Components</th>
              </tr>
            </thead>
            <tbody>
              {[
                {
                  status: 'OP',
                  components: 'HCPU RTL (84 opcodes), .hcell, CellIR, 4-B′ Verifier, HPG1 v2 (CHECKSUM32), HC v1.0, HCC, HASM, .hbc, HVM, HOS, HFS, H-Kernel, CSGI, Guard (G1–G4, T1–T2), HCHECK, HISAB, HAR, Ψ-Compiler, MasterTable, ROM, SHA-256, HOM Desktop GUI (Sidebar + 15 Workbenches)',
                },
                {
                  status: 'SPEC',
                  components: '21 software-only H-ISA opcodes executed in HVM (CDOT, CSUB, HEXMT, HDCMP, HSER, HDES, VSCL, HCHK, CHASH, CSIGN, HPROJ, VPROJ_*, PRINTH, JGP/JGF/JNP)',
                },
                {
                  status: 'ASP',
                  components: 'HCPU Photonic (DoF Phase/WDM/TDM/OAM/Polarization exploration)',
                },
              ].map((row) => (
                <tr key={row.status} className="border-b border-[#1C3552]">
                  <td className="py-3 px-4 align-top">
                    <StatusBadge status={row.status} />
                  </td>
                  <td className="py-3 px-4 text-xs text-[#EAF2FA] font-mono leading-relaxed">
                    {row.components}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Footer */}
      <div className="text-center py-4 text-xs text-[#8AA0B8] font-mono">
        HIJAIYYAH SCIENTIFIC COMPUTING ENVIRONMENT · HOM v1.2.0 · HM-28-v1.0-HC18D · © 2026 Maulana Amratulloh
      </div>
    </div>
  );
}
