import { Link } from 'react-router-dom';
import GlassPanel from '../components/GlassPanel';
import FormulaBlock from '../components/FormulaBlock';
import { CANONICAL_CONTRACT } from '../config/siteArchitecture';

export default function Mathematics() {
  const guards = [
    ['G1', 'A_N = N_a + N_b + N_d', 'Konservasi agregat titik (Nuqṭah)'],
    ['G2', 'A_K = K_p + K_x + K_s + K_a + K_c', 'Konservasi agregat garis (Khaṭṭ)'],
    ['G3', 'A_Q = Q_p + Q_x + Q_s + Q_a + Q_c', 'Konservasi agregat lengkung (Qaws)'],
    ['G4', 'ρ = Θ̂ − U ≥ 0,  U = Q_x + Q_s + Q_a + 4Q_c', 'Kekekalan belokan lintasan utama'],
    ['T1', 'K_s > 0 ⇒ Q_c ≥ 1', 'Kendala topologis garis-kurva tertutup'],
    ['T2', 'K_c > 0 ⇒ Q_c ≥ 1', 'Kendala topologis segmen penghubung'],
  ];

  const ops = [
    ['Vektronometry (VTM)', 'r_N + r_K + r_Q = 1', 'VF · CC', '/laboratory/vektronometry'],
    ['Normvektor (NMV)', '‖Δ‖₂² = Δ_Θ̂² + ‖Δ_N‖₂² + ‖Δ_K‖₂² + ‖Δ_Q‖₂²', 'VF · CC', '/laboratory/normvektor'],
    ['Aggregametric (AGM)', 'Cod₁₈(u ∘ v) = Cod₁₈(u) + Cod₁₈(v)', 'VF · CC', '/laboratory/aggregametric'],
    ['Intrametric (ITM)', 'd₂²(h₁, h₂) = ‖h₁‖₂² + ‖h₂‖₂² − 2⟨h₁, h₂⟩', 'VF · CC', '/laboratory/intrametric'],
    ['Exometric (EXM)', 'Φ(h) = ‖E(h)‖_F > ‖v₁₄(h)‖₂²', 'CC', '/laboratory/exometric'],
  ];

  return (
    <div className="space-y-6">
      <div>
        <div className="text-[11px] font-mono uppercase tracking-widest text-hom-gold">
          Formal Theory · BAB I &amp; BAB II
        </div>
        <h1 className="text-3xl font-bold text-hom-text mt-1">Fondasi Formal &amp; Aljabar Hybit 18D</h1>
        <p className="text-sm text-hom-muted mt-1">
          {CANONICAL_CONTRACT.hybitExpansion} · Monoid Komutatif (𝒱, +, 0) · rank(M₁₄) = 14.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <GlassPanel title="Codex 18D &amp; Ruang Hybit" badge="VF">
          <p className="text-xs text-hom-muted mb-3">
            Setiap huruf kanonik h ∈ ℋ₂₈ dipetakan secara injektif ke vektor bilangan bulat tak negatif 18 komponen:
          </p>
          <FormulaBlock tex="v_{18}(h) = [\hat{\Theta} \mid N \mid K \mid Q \mid A_N, A_K, A_Q \mid H^*] \in \mathbb{N}_0^{18}" display />
          <p className="text-xs text-hom-muted mt-3">
            Jarak Euclides terkecil antarhuruf adalah √2 (13 pasangan), dan seluruh 378 pasangan huruf terbedakan secara unik.
          </p>
        </GlassPanel>

        <GlassPanel title="Enam Guard Kanonik O(1)" badge="VF · PAPAN">
          <div className="space-y-2 text-xs font-mono">
            {guards.map(([id, expr, desc]) => (
              <div key={id} className="flex justify-between gap-3 border-b border-hom-border/20 pb-1.5">
                <span className="text-hom-accent font-bold">{id}</span>
                <span className="text-hom-text">{expr}</span>
                <span className="text-hom-muted text-[10px] hidden sm:inline">{desc}</span>
              </div>
            ))}
          </div>
        </GlassPanel>
      </div>

      <GlassPanel title="Lima Operasi Metrik-Vektorial (BAB II)" badge="Σ-MV">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {ops.map(([name, formula, label, href]) => (
            <Link key={name} to={href} className="block rounded-xl border border-hom-border/30 bg-hom-bg/50 p-4 hover:border-hom-accent/50 transition-all">
              <div className="flex justify-between items-center mb-2">
                <span className="font-bold text-sm text-hom-text">{name}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-hom-accent/10 text-hom-accent">{label}</span>
              </div>
              <div className="text-xs font-mono text-hom-gold">{formula}</div>
            </Link>
          ))}
        </div>
      </GlassPanel>
    </div>
  );
}
