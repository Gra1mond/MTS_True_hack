import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        page: 'var(--color-bg-page)',
        surface: 'var(--color-bg-white)',
        sidebar: 'var(--color-bg-sidebar)',
        'chat-active': 'var(--color-bg-chat-active)',
        ink: {
          DEFAULT: 'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)',
          muted: 'var(--color-text-muted)',
        },
        accent: 'var(--color-accent)',
        border: {
          DEFAULT: 'var(--color-border)',
        },
        input: 'var(--color-input-border)',
        codebg: 'var(--color-code-bg)',
        diff: {
          red: 'var(--color-diff-red-bg)',
          green: 'var(--color-diff-green-bg)',
        },
        constraints: {
          bg: 'var(--color-constraints-bg)',
          border: 'var(--color-constraints-border)',
          title: 'var(--color-constraints-title)',
        },
        icon: {
          header: 'var(--color-icon-header)',
        },
      },
      fontFamily: {
        sans: ['var(--font-ui)'],
        mono: ['var(--font-mono)'],
      },
      maxWidth: {
        composer: '802px',
      },
      width: {
        sidebar: '284px',
        'sidebar-collapsed': '56px',
      },
    },
  },
  plugins: [],
} satisfies Config
