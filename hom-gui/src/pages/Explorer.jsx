import { Link } from 'react-router-dom';
import { MASTER_TABLE } from '../engine/masterTable';
import { CANONICAL_CONTRACT } from '../config/siteArchitecture';
import GlassPanel from '../components/GlassPanel';

export default function Explorer() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="text-[11px] font-mono uppercase tracking-widest text-hom-accent">
            Canonical Letter Explorer · {CANONICAL_CONTRACT.datasetId}
          </div>
          <h1 className="text-3xl font-bold text-hom-text mt-1">
            Eksplorasi 28 Huruf Kanonik &amp; Codex 18D
          </h1>
          <p className="text-sm text-hom-muted mt-1">
            Sumber data tunggal: Master Table {CANONICAL_CONTRACT.datasetShape} · SHA-256 {CANONICAL_CONTRACT.sealPrefix}… · Urutan 26–28: و (Waw), هـ (Haa), ي (Ya).
          </p>
        </div>
        <div className="flex gap-2 text-[10px] font-mono">
          <span className="px-2.5 py-1 rounded bg-hom-accent/10 text-hom-accent border border-hom-accent/30">CC · Confirmed</span>
          <span className="px-2.5 py-1 rounded bg-hom-gold/10 text-hom-gold border border-hom-gold/30">6 Guards O(1)</span>
        </div>
      </div>

      <GlassPanel title="Master Grid HM-28 (01–28)" badge="Read-Only Manifest">
        <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-7 gap-3">
          {MASTER_TABLE.map((entry) => (
            <Link
              key={entry.id}
              to={`/explorer/letter/${entry.slug}`}
              className="group rounded-xl border border-hom-border/40 bg-hom-bg/60 hover:border-hom-accent/60 hover:bg-hom-panel/60 p-3 text-center transition-all"
            >
              <div className="flex justify-between items-center text-[10px] font-mono text-hom-muted">
                <span>#{String(entry.id).padStart(2, '0')}</span>
                <span className="text-hom-gold">Θ̂={entry.v18[0]}</span>
              </div>
              <div className="arabic-letter text-4xl my-2 text-hom-text group-hover:text-hom-accent transition-colors">
                {entry.char}
              </div>
              <div className="text-xs font-semibold text-hom-text">{entry.name}</div>
              <div className="text-[9px] font-mono text-hom-muted mt-0.5">/{entry.slug}</div>
            </Link>
          ))}
        </div>
      </GlassPanel>
    </div>
  );
}
