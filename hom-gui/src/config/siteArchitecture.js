/**
 * Technical Architecture & Design System Configuration — hijaiyyahmathematic.tech (P1)
 * Single Source of Truth: Master Table HM-28-v1.0-HC18D
 */

export const DESIGN_TOKENS = {
  colors: {
    midnight: '#071426',
    surface: '#10243A',
    cyan: '#26C6DA',
    gold: '#D6AF57',
    text: '#EAF2FA',
  },
  fonts: {
    sans: "'Inter', 'Segoe UI', system-ui, sans-serif",
    mono: "'JetBrains Mono', 'Consolas', monospace",
    arabic: "'Scheherazade New', 'Amiri', serif",
  },
};

export const CANONICAL_CONTRACT = {
  datasetId: 'HM-28-v1.0-HC18D',
  datasetShape: '28 × 18 = 504',
  nonzeroCells: 148,
  rankM14: 14,
  sealPrefix: 'f82d3859',
  hybitExpansion: 'Hijaiyyah Hyperdimensional Bit Integration Technology',
  hmclExpansion: 'Hijaiyyah Mathematical Computing Laboratory',
  hmclExpansionId: 'Laboratorium Komputasi Matematis Hijaiyyah',
  publisher: 'AMRA Publishing — Yayasan Amratulloh International Academy',
  hisaCatalog: {
    totalUniqueOpcodes: 105,
    rtlImplemented: 84,
    softwareOnly: 21,
    letterOpcodes: 28,
  },
  epistemicLabels: {
    VF: 'Verified Formally',
    CC: 'Computationally Confirmed',
    DP: 'Design Property',
    EH: 'Engineering Hypothesis',
    AT: 'Aspirational Target',
  },
};

export const MAIN_NAVIGATION = [
  { id: '01', key: 'home', label: 'Home', path: '/', exact: true },
  {
    id: '02',
    key: 'origin',
    label: 'Origin',
    path: '/origin',
    children: [
      { label: 'Origin Protocol', path: '/origin/protocol' },
      { label: 'Canonical 28 Letterforms', path: '/origin/canonical-28' },
      { label: 'KFGQPC Glyph Source', path: '/origin/kfgqpc' },
      { label: 'CSGI & MainPath Extraction', path: '/origin/csgi-mainpath' },
      { label: 'SHA-256 Dataset Seal', path: '/origin/dataset-seal' },
    ],
  },
  {
    id: '03',
    key: 'mathematics',
    label: 'Mathematics',
    path: '/mathematics',
    children: [
      { label: 'Formal Foundation (BAB I)', path: '/mathematics/foundation' },
      { label: '18D Hybit Codex', path: '/mathematics/hybit-18d' },
      { label: 'Master Table HM-28', path: '/mathematics/master-table' },
      { label: 'Six Canonical Guards (G1–G4, T1–T2)', path: '/mathematics/guards' },
      { label: 'Algebraic Structure (V, +, 0)', path: '/mathematics/algebra' },
      { label: 'Theorems & Proofs', path: '/mathematics/theorems' },
    ],
  },
  {
    id: '04',
    key: 'explorer',
    label: 'Explorer',
    path: '/explorer',
    children: [
      { label: '28 Letter Explorer', path: '/explorer' },
      { label: '18D Codex Viewer', path: '/explorer/codex' },
      { label: 'Letter Comparison', path: '/explorer/compare' },
      { label: 'Distance Matrix (378 Pairs)', path: '/explorer/distance-matrix' },
    ],
  },
  {
    id: '05',
    key: 'laboratory',
    label: 'Laboratory',
    path: '/laboratory',
    children: [
      { label: 'Vektronometry (VTM)', path: '/laboratory/vektronometry' },
      { label: 'Normvektor (NMV)', path: '/laboratory/normvektor' },
      { label: 'Aggregametric (AGM)', path: '/laboratory/aggregametric' },
      { label: 'Intrametric (ITM)', path: '/laboratory/intrametric' },
      { label: 'Exometric (EXM)', path: '/laboratory/exometric' },
      { label: 'CSGI / Geometry Lab', path: '/laboratory/csgi' },
    ],
  },
  {
    id: '06',
    key: 'computing',
    label: 'Computing',
    path: '/computing',
    children: [
      { label: 'HC Language & .hcell', path: '/computing/hc-language' },
      { label: 'HCC Compiler & CellIR', path: '/computing/compiler-cellir' },
      { label: '4-B′ Control Flow Verifier', path: '/computing/verifier-4b' },
      { label: 'HPG1 v2 Container', path: '/computing/hpg1' },
      { label: 'H-ISA (105 Opcodes)', path: '/computing/h-isa' },
      { label: 'HVM Virtual Machine', path: '/computing/hvm' },
      { label: 'HCPU & FPGA Implementation', path: '/computing/hcpu-fpga' },
      { label: 'HOM Platform', path: '/computing/hom' },
    ],
  },
  {
    id: '07',
    key: 'research',
    label: 'Research',
    path: '/research',
    children: [
      { label: 'Scientific Journal', path: '/research/journal' },
      { label: 'Books & Monographs', path: '/research/books' },
      { label: 'Research Papers', path: '/research/papers' },
      { label: 'Technical Reports', path: '/research/reports' },
      { label: 'HMCL Laboratory', path: '/research/hmcl' },
    ],
  },
  {
    id: '08',
    key: 'documentation',
    label: 'Documentation',
    path: '/documentation',
    children: [
      { label: 'Theory & Mathematical Reference', path: '/documentation/theory' },
      { label: 'Master Table & Guard Spec', path: '/documentation/master-table' },
      { label: 'HC & H-ISA Reference', path: '/documentation/h-isa' },
      { label: 'API Documentation & Tutorials', path: '/documentation/api' },
      { label: 'Dataset Downloads & Release Notes', path: '/documentation/downloads' },
    ],
  },
];
