/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        hom: {
          bg: '#071426',       // Midnight primary canvas
          panel: '#10243A',    // Surface card/panel background
          border: '#1C3552',   // Clean structural border
          accent: '#26C6DA',   // Cyan scientific primary accent
          gold: '#D6AF57',     // Gold secondary metric accent
          green: '#2ECC71',    // Verified / Guard Pass green
          red: '#EF5350',      // Fault / Violation red
          purple: '#7E57C2',   // Subtle system accent
          text: '#EAF2FA',     // Crisp clinical text
          muted: '#8AA0B8',    // Muted slate-blue secondary text
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Consolas', 'monospace'],
        sans: ['"Inter"', '"Segoe UI"', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 4px 16px rgba(38, 198, 218, 0.12)',
        'glow-gold': '0 4px 16px rgba(214, 175, 87, 0.12)',
        'glow-green': '0 4px 16px rgba(46, 204, 113, 0.12)',
      },
    },
  },
  plugins: [],
};
