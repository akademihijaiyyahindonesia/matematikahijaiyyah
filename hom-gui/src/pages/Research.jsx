import GlassPanel from '../components/GlassPanel';
import { CANONICAL_CONTRACT } from '../config/siteArchitecture';

export default function Research() {
  const pubs = [
    {
      kind: 'Books & Monographs',
      title: 'Matematika Hijaiyyah — Edisi v.1.1.1 (BAB I & II)',
      author: 'Maulana Amratulloh',
      venue: CANONICAL_CONTRACT.publisher,
      status: 'Edisi Kanonik · Terverifikasi HM-28',
    },
    {
      kind: 'Scientific Journal',
      title: 'Matematika Hijaiyyah: 28 Bentuk Huruf Kanonik sebagai Codex Integer 18 Dimensi, dari Fondasi Formal sampai Prosesor di FPGA',
      author: 'Maulana Amratulloh',
      venue: `${CANONICAL_CONTRACT.hmclExpansion} (HMCL)`,
      status: 'Naskah Telaah · Paritas 74/0/29',
    },
    {
      kind: 'Technical Reports',
      title: 'Laporan Validasi Papan Tang Nano 20K: Burn-In 72 Jam, HFS, HPG1 v2, Ka’bah HMAC-L3, & Jamrah O(1)',
      author: 'HMCL Hardware & NUI Team',
      venue: 'cosmictera-build/PAPAN.md',
      status: 'Terukur di Papan Fisik',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <div className="text-[11px] font-mono uppercase tracking-widest text-hom-accent">
          Research &amp; Publications · HMCL
        </div>
        <h1 className="text-3xl font-bold text-hom-text mt-1">Pusat Publikasi Ilmiah &amp; Laboratorium</h1>
        <p className="text-sm text-hom-muted mt-1">
          {CANONICAL_CONTRACT.hmclExpansion} ({CANONICAL_CONTRACT.hmclExpansionId}) · {CANONICAL_CONTRACT.publisher}
        </p>
      </div>

      <div className="space-y-4">
        {pubs.map((p) => (
          <GlassPanel key={p.title} title={p.kind} badge={p.status}>
            <h2 className="text-lg font-bold text-hom-text">{p.title}</h2>
            <div className="text-xs font-mono text-hom-gold mt-1">{p.author} · {p.venue}</div>
          </GlassPanel>
        ))}
      </div>
    </div>
  );
}
