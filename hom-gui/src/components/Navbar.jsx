import { Link, useLocation } from 'react-router-dom';
import { useLocale } from '../store/useLocale';

export default function Navbar() {
  const { pathname } = useLocation();
  const { lang, setLang } = useLocale();

  const links = [
    { to: '/', label: '01. Home', match: (p) => p === '/' },
    { to: '/origin', label: '02. Origin', match: (p) => p.startsWith('/origin') },
    { to: '/mathematics', label: '03. Mathematics', match: (p) => p.startsWith('/mathematics') },
    { to: '/explorer', label: '04. Explorer', match: (p) => p.startsWith('/explorer') },
    { to: '/laboratory', label: '05. Laboratory', match: (p) => p.startsWith('/laboratory') || p === '/lab' },
    { to: '/computing', label: '06. Computing', match: (p) => p.startsWith('/computing') || p === '/system' },
    { to: '/research', label: '07. Research', match: (p) => p.startsWith('/research') },
    { to: '/documentation', label: '08. Documentation', match: (p) => p.startsWith('/documentation') || p === '/docs' },
  ];

  return (
    <nav className="glass sticky top-0 z-50 border-b border-hom-border/50">
      <div className="max-w-7xl mx-auto px-4 md:px-8 flex items-center justify-between h-16 gap-4">
        <Link to="/" className="flex items-center shrink-0 pl-2 md:pl-6">
          <img
            src={import.meta.env.BASE_URL + 'hijaiyyah-mathematic-logo.png'}
            alt="Hijaiyyah Mathematic"
            className="h-9 md:h-10 w-auto object-contain"
          />
        </Link>

        <div className="flex items-center gap-1 overflow-x-auto hide-scrollbar">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`px-2.5 py-1.5 rounded-lg text-[10px] font-mono whitespace-nowrap transition-all ${
                link.match(pathname)
                  ? 'nav-tab-futuristic-active'
                  : 'text-hom-muted hover:text-hom-text hover:bg-hom-panel/50'
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Link
            to="/simulator"
            className="px-3 py-1.5 rounded-lg bg-hom-accent/20 border border-hom-accent/50 text-hom-accent text-[10px] font-mono font-bold hover:bg-hom-accent/30 transition-all whitespace-nowrap"
          >
            Launch HOM
          </Link>
          <div className="flex items-center rounded-lg bg-hom-panel/50 border border-hom-border/50 p-0.5 text-[9px] font-mono">
            <button
              onClick={() => setLang('en')}
              className={`px-2 py-1 rounded-md transition-all ${
                lang === 'en' ? 'bg-hom-accent/20 text-hom-accent' : 'text-hom-muted hover:text-hom-text'
              }`}
            >
              EN
            </button>
            <button
              onClick={() => setLang('id')}
              className={`px-2 py-1 rounded-md transition-all ${
                lang === 'id' ? 'bg-hom-accent/20 text-hom-accent' : 'text-hom-muted hover:text-hom-text'
              }`}
            >
              ID
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
