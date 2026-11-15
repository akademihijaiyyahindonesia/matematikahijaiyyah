export default function GuardBadge({ guard, name, passed }) {
  const item = guard || { id: name, pass: Boolean(passed), formula: passed ? 'PASS' : 'FAIL' };
  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-mono ${
        item.pass
          ? 'bg-hom-green/5 border-hom-green/20 text-hom-green'
          : 'bg-hom-red/5 border-hom-red/20 text-hom-red'
      }`}
    >
      <span className="font-bold">{item.id}</span>
      <span className={`w-2 h-2 rounded-full ${item.pass ? 'bg-hom-green' : 'bg-hom-red'}`} />
      <span className="text-hom-muted text-[10px] truncate">{item.formula}</span>
    </div>
  );
}
