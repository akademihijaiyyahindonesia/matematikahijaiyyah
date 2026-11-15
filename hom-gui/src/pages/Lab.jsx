import { useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { MASTER_TABLE } from '../engine/masterTable';
import LetterCard from '../components/LetterCard';
import useStore from '../store/useStore';
import GlassPanel from '../components/GlassPanel';
import VectorDisplay from '../components/VectorDisplay';
import FormulaBlock from '../components/FormulaBlock';
import GuardBadge from '../components/GuardBadge';
import { useLocale } from '../store/useLocale';

const LAB_OPS = [
  { id: 'agm', code: 'AGM', name: 'Aggregametric', desc: 'String Codex Σv₁₈ & Turning Conservation' },
  { id: 'nvm', code: 'NVM', name: 'Normvektor', desc: 'Quadratic Form Q(v₁₄), Dot Gradient & Rasm Fibres' },
  { id: 'inm', code: 'INM', name: 'Intrametric', desc: 'Euclidean Distance d₁₄, Cosine & Gram Inner Product' },
  { id: 'vtm', code: 'VTM', name: 'Vektronometry', desc: 'Simplex Ratios r_N + r_K + r_Q = 1 & Angle α' },
  { id: 'exm', code: 'EXM', name: 'Exometric', desc: '5×5 Exomatrix Frobenius Energy Φ(h) & Syzygies R1–R5' },
  { id: 'blm', code: 'BLM', name: 'Boolean & Lattice', desc: 'Support Binary Vector, Jaccard & Meet/Join Closure' },
];

const OP_ALIASES = {
  agm: 'agm',
  aggregametric: 'agm',
  nvm: 'nvm',
  nmv: 'nvm',
  normvektor: 'nvm',
  inm: 'inm',
  itm: 'inm',
  intrametric: 'inm',
  vtm: 'vtm',
  vektronometry: 'vtm',
  exm: 'exm',
  exometric: 'exm',
  blm: 'blm',
  csgi: 'blm',
};

export default function Lab() {
  const { op } = useParams();
  const rawOp = (op || 'agm').toLowerCase();
  const activeOp = OP_ALIASES[rawOp] || rawOp;
  const [input, setInput] = useState('بسم');
  const [letterA, setLetterA] = useState(MASTER_TABLE[1]?.char || 'ب');
  const [letterB, setLetterB] = useState(MASTER_TABLE[2]?.char || 'ت');
  const { runLab, labResult } = useStore();
  const { t, lang } = useLocale();

  const handleRun = () => runLab(input);

  const pairAnalysis = useMemo(() => {
    const a = MASTER_TABLE.find((e) => e.char === letterA) || MASTER_TABLE[0];
    const b = MASTER_TABLE.find((e) => e.char === letterB) || MASTER_TABLE[1];
    const v14a = a.v18.slice(0, 14);
    const v14b = b.v18.slice(0, 14);
    const norm2a = v14a.reduce((s, x) => s + x * x, 0);
    const norm2b = v14b.reduce((s, x) => s + x * x, 0);
    const dot = v14a.reduce((s, x, i) => s + x * v14b[i], 0);
    const dist2 = v14a.reduce((s, x, i) => s + (x - v14b[i]) ** 2, 0);
    const cos = norm2a > 0 && norm2b > 0 ? dot / (Math.sqrt(norm2a) * Math.sqrt(norm2b)) : 0;
    const dotGrad = [b.v18[1] - a.v18[1], b.v18[2] - a.v18[2], b.v18[3] - a.v18[3]];
    const sameRasm =
      a.v18[0] === b.v18[0] &&
      a.v18.slice(4, 14).every((val, idx) => val === b.v18[idx + 4]);
    const meet18 = a.v18.map((x, i) => Math.min(x, b.v18[i]));
    const join18 = a.v18.map((x, i) => Math.max(x, b.v18[i]));
    const joinU = join18[10] + join18[11] + join18[12] + 4 * join18[13];
    const joinG4Pass = join18[0] >= joinU;
    return { a, b, norm2a, norm2b, dot, dist2, cos, dotGrad, sameRasm, meet18, join18, joinG4Pass };
  }, [letterA, letterB]);

  return (
    <div className="space-y-10">
      {/* ═══════════════ LABORATORY HEADER & OP TABS ═══════════════ */}
      <section className="space-y-4">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-widest text-hom-accent">
              05. Interactive Algebra Laboratory · 6 Canonical Algebras
            </div>
            <h1 className="text-3xl font-bold text-hom-text mt-1">
              {lang === 'id' ? 'Laboratorium Aljabar & Normvektor Hijaiyyah' : 'Hijaiyyah Algebra & Normvektor Laboratory'}
            </h1>
            <p className="text-sm text-hom-muted mt-1">
              {lang === 'id'
                ? 'Uji langsung 6 aljabar operasional (AGM, NVM/Normvektor, INM, VTM, EXM, BLM) pada ruang vektor Hybit 18D.'
                : 'Interactively test the 6 operational algebras (AGM, NVM/Normvektor, INM, VTM, EXM, BLM) on the 18D Hybit vector space.'}
            </p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {LAB_OPS.map((item) => (
              <Link
                key={item.id}
                to={`/laboratory/${item.id}`}
                className={`px-3 py-1.5 rounded-lg text-[10px] font-mono border transition-all ${
                  activeOp === item.id
                    ? 'bg-hom-accent/20 border-hom-accent text-hom-accent font-bold'
                    : 'bg-hom-panel/40 border-hom-border/40 text-hom-muted hover:text-hom-text'
                }`}
              >
                {item.code} · {item.name}
              </Link>
            ))}
          </div>
        </div>

        {/* Pairwise / Normvektor / Intrametric / Lattice Interactive Inspector */}
        <GlassPanel
          title={`Active Module: ${LAB_OPS.find((x) => x.id === activeOp)?.name || 'Aggregametric'} (${activeOp.toUpperCase()})`}
          badge="Live 18D Operator"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-mono text-hom-muted mb-1">Huruf Pertama (h₁)</label>
              <select
                value={letterA}
                onChange={(e) => setLetterA(e.target.value)}
                className="w-full bg-hom-bg border border-hom-border rounded-lg px-3 py-2 text-sm text-hom-text font-mono"
              >
                {MASTER_TABLE.map((e) => (
                  <option key={e.id} value={e.char}>
                    #{String(e.id).padStart(2, '0')} {e.char} — {e.name} (Θ̂={e.v18[0]})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-mono text-hom-muted mb-1">Huruf Kedua (h₂)</label>
              <select
                value={letterB}
                onChange={(e) => setLetterB(e.target.value)}
                className="w-full bg-hom-bg border border-hom-border rounded-lg px-3 py-2 text-sm text-hom-text font-mono"
              >
                {MASTER_TABLE.map((e) => (
                  <option key={e.id} value={e.char}>
                    #{String(e.id).padStart(2, '0')} {e.char} — {e.name} (Θ̂={e.v18[0]})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3 rounded-lg bg-hom-bg/60 border border-hom-border/40">
              <div className="text-hom-muted">Q(h₁) = ‖v₁₄(h₁)‖²</div>
              <div className="text-lg font-bold text-hom-accent mt-1">{pairAnalysis.norm2a}</div>
            </div>
            <div className="p-3 rounded-lg bg-hom-bg/60 border border-hom-border/40">
              <div className="text-hom-muted">Q(h₂) = ‖v₁₄(h₂)‖²</div>
              <div className="text-lg font-bold text-hom-gold mt-1">{pairAnalysis.norm2b}</div>
            </div>
            <div className="p-3 rounded-lg bg-hom-bg/60 border border-hom-border/40">
              <div className="text-hom-muted">d₁₄(h₁, h₂)² &amp; cos θ</div>
              <div className="text-lg font-bold text-hom-green mt-1">
                {pairAnalysis.dist2} <span className="text-xs text-hom-muted">({pairAnalysis.cos.toFixed(3)})</span>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-hom-bg/60 border border-hom-border/40">
              <div className="text-hom-muted">ΔN Dot Gradient / Rasm</div>
              <div className="text-sm font-bold text-hom-text mt-1">
                [{pairAnalysis.dotGrad.join(', ')}] · {pairAnalysis.sameRasm ? 'SAME RASM' : 'DIFF RASM'}
              </div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <VectorDisplay label={`meet min(h₁,h₂)`} vector={pairAnalysis.meet18} />
            <VectorDisplay label={`join max(h₁,h₂) [G4:${pairAnalysis.joinG4Pass ? 'PASS' : 'FAIL'}]`} vector={pairAnalysis.join18} />
          </div>
        </GlassPanel>
      </section>

      {/* ═══════════════ AGGREGAMETRIC LAB ═══════════════ */}
      <section className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold">{t('Aggregametric Lab')}</h2>
          <p className="text-sm text-hom-muted mt-1">
            {t('Enter Arabic text to compute string codex · Aggregametric (AGM) operation')}
          </p>
        </div>

        <GlassPanel>
          <div className="flex gap-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t('Enter Hijaiyyah text...')}
              className="flex-1 bg-hom-bg border border-hom-border rounded-lg px-4 py-2.5 text-lg arabic-letter text-hom-text focus:border-hom-accent/50 focus:outline-none transition-colors"
              dir="rtl"
            />
            <button
              onClick={handleRun}
              className="px-6 py-2.5 rounded-lg bg-hom-accent text-black font-semibold text-sm hover:shadow-glow transition-all"
            >
              {t('Compute Σ')}
            </button>
          </div>
        </GlassPanel>

        {labResult && (
          <div className="space-y-4">
            <GlassPanel title={t('Aggregametric Result')} badge={`${labResult.letterCount} ${t('letters')}`} glow>
              <div className="arabic-letter text-3xl text-center mb-4 neon-text" dir="rtl">
                {labResult.text}
              </div>
              <VectorDisplay label="Σ_w v₁₈" vector={labResult.codex} />
            </GlassPanel>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <GlassPanel title={t('Turning Decomposition')} badge="AGM">
                <div className="space-y-3 font-mono text-sm">
                  <div className="flex justify-between">
                    <span className="text-hom-muted">Σ_w Θ̂</span>
                    <span className="text-hom-accent font-bold">{labResult.theta}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-hom-muted">Σ_w U</span>
                    <span className="text-hom-gold">{labResult.U}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-hom-muted">Σ_w ρ</span>
                    <span className="text-hom-green">{labResult.rho}</span>
                  </div>
                  <div className="glow-line" />
                  <FormulaBlock
                    tex={`\\Sigma_w \\hat{\\Theta} = \\Sigma_w U + \\Sigma_w \\rho \\;\\Rightarrow\\; ${labResult.theta} = ${labResult.U} + ${labResult.rho}`}
                    display
                  />
                </div>
              </GlassPanel>

              <GlassPanel
                title={t('Identity Preservation')}
                badge={labResult.allPreserved ? t('ALL PASS') : t('FAIL')}
                glow={labResult.allPreserved ? 'green' : undefined}
              >
                <div className="space-y-2">
                  <GuardBadge guard={{ id: 'Θ̂=U+ρ', pass: labResult.identityPreserved, formula: `${labResult.theta}=${labResult.U}+${labResult.rho}` }} />
                  <GuardBadge guard={{ id: 'ρ≥0', pass: labResult.rho >= 0, formula: `ρ=${labResult.rho}` }} />
                  <GuardBadge guard={{ id: 'G1', pass: labResult.g1, formula: 'A_N = Σ N_j' }} />
                  <GuardBadge guard={{ id: 'G2', pass: labResult.g2, formula: 'A_K = Σ K_j' }} />
                  <GuardBadge guard={{ id: 'G3', pass: labResult.g3, formula: 'A_Q = Σ Q_j' }} />
                </div>
              </GlassPanel>
            </div>
          </div>
        )}
      </section>

      {/* ═══════════════ LETTER EXPLORER ═══════════════ */}
      <section>
        <div className="mb-6">
          <h2 className="text-2xl font-bold">{t('Start Exploring')}</h2>
          <p className="text-sm text-hom-muted mt-1">
            {t('Browse all 28 canonical Hijaiyyah letters · Click to inspect full codex profile')}
          </p>
        </div>
        <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-7 gap-3">
          {MASTER_TABLE.map((entry) => (
            <LetterCard key={entry.char} entry={entry} />
          ))}
        </div>
      </section>
    </div>
  );
}
