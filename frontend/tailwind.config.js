const c = (name) => `rgb(var(--${name}) / <alpha-value>)`

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    fontSize: {
      xs: ['12px', '16px'],
      sm: ['13px', '18px'],
      base: ['14px', '20px'],
      md: ['16px', '24px'],
      lg: ['20px', '28px'],
      xl: ['24px', '32px'],
      '2xl': ['32px', '40px'],
    },
    extend: {
      colors: {
        background: c('background'),
        surface: c('surface'),
        raised: c('surface-raised'),
        line: c('border'),
        fg: c('text'),
        muted: c('text-muted'),
        accent: c('accent'),
        ok: c('status-ok'),
        warning: c('status-warning'),
        critical: c('status-critical'),
        paused: c('status-paused'),
      },
      borderRadius: { control: '6px', panel: '10px' },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
}
