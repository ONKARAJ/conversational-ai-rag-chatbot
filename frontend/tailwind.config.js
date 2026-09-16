/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      // Every colour is a CSS variable defined in index.css, so the light and
      // dark themes share one set of class names.
      colors: {
        canvas: 'var(--canvas)',
        surface: 'var(--surface)',
        raised: 'var(--raised)',
        hairline: 'var(--hairline)',
        ink: 'var(--ink)',
        muted: 'var(--muted)',
        faint: 'var(--faint)',
        accent: 'var(--accent)',
        'accent-hover': 'var(--accent-hover)',
        'accent-soft': 'var(--accent-soft)',
        'accent-ink': 'var(--accent-ink)',
        grounded: 'var(--grounded)',
        'grounded-soft': 'var(--grounded-soft)',
        danger: 'var(--danger)',
        'danger-soft': 'var(--danger-soft)',
      },
      fontFamily: {
        sans: ['"Instrument Sans"', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      maxWidth: {
        thread: '46rem',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: 0, transform: 'translateY(4px)' },
          to: { opacity: 1, transform: 'none' },
        },
        blink: {
          '0%, 80%, 100%': { opacity: 0.25 },
          '40%': { opacity: 1 },
        },
      },
      animation: {
        'fade-in': 'fade-in 160ms ease-out',
        blink: 'blink 1.2s infinite',
      },
    },
  },
  plugins: [],
}
