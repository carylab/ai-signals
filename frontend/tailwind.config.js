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
          50:  '#f0f4ff',
          100: '#e0e9ff',
          200: '#c5d3f8',
          500: '#3b5bdb',
          600: '#2f4ac5',
          700: '#2541a8',
          900: '#1a2d6b',
        },
        surface: {
          DEFAULT: '#ffffff',
          muted:   '#f8f9fa',
          subtle:  '#f1f3f5',
          border:  '#dee2e6',
        },
      },
      typography: (theme) => ({
        DEFAULT: {
          css: {
            maxWidth: '70ch',
            color: theme('colors.gray.800'),
            a: { color: theme('colors.brand.600') },
            'h1,h2,h3': { color: theme('colors.gray.900') },
          },
        },
      }),
    },
  },
  plugins: [require('@tailwindcss/typography')],
};
