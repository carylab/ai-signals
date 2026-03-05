/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        brand: {
          50:  '#e8fff8',
          100: '#c0ffe9',
          200: '#7affd2',
          300: '#00ffb3',
          400: '#00e69e',
          500: '#00cc8b',
          600: '#00a870',
          700: '#007a51',
          800: '#004d33',
          900: '#002619',
        },
        cyan: {
          400: '#22d3ee',
          500: '#06b6d4',
        },
        surface: {
          DEFAULT: '#0a0e1a',
          muted:   '#0d1220',
          subtle:  '#111827',
          card:    '#111827',
          border:  '#1e2d45',
          hover:   '#162033',
        },
        text: {
          primary:   '#f1f5f9',
          secondary: '#b8c7d9',
          muted:     '#6b829a',
          accent:    '#00ffb3',
        },
      },
      backgroundImage: {
        'grid-pattern': "linear-gradient(rgba(0,255,179,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,179,0.03) 1px, transparent 1px)",
        'glow-green': 'radial-gradient(ellipse at center, rgba(0,255,179,0.15) 0%, transparent 70%)',
        'glow-cyan': 'radial-gradient(ellipse at center, rgba(34,211,238,0.1) 0%, transparent 70%)',
        'header-gradient': 'linear-gradient(180deg, rgba(10,14,26,0.98) 0%, rgba(10,14,26,0.95) 100%)',
      },
      backgroundSize: {
        'grid': '40px 40px',
      },
      boxShadow: {
        'neon-green': '0 0 10px rgba(0,255,179,0.3), 0 0 20px rgba(0,255,179,0.1)',
        'neon-cyan':  '0 0 10px rgba(34,211,238,0.3), 0 0 20px rgba(34,211,238,0.1)',
        'card':       '0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.03)',
        'card-hover': '0 4px 16px rgba(0,0,0,0.5), inset 0 1px 0 rgba(0,255,179,0.05)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'scan': 'scan 4s linear infinite',
      },
      keyframes: {
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
      },
      typography: () => ({
        DEFAULT: {
          css: {
            maxWidth: '70ch',
            color: '#94a3b8',
            a: { color: '#00ffb3' },
            'h1,h2,h3': { color: '#e2e8f0' },
          },
        },
      }),
    },
  },
  plugins: [require('@tailwindcss/typography')],
};
