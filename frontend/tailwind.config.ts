import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // GitHub Primer Design System Colors
        gh: {
          // Canvas (Backgrounds)
          'canvas-default': 'var(--gh-canvas-default)',
          'canvas-overlay': 'var(--gh-canvas-overlay)',
          'canvas-inset': 'var(--gh-canvas-inset)',
          'canvas-subtle': 'var(--gh-canvas-subtle)',
          
          // Foreground (Text)
          'fg-default': 'var(--gh-fg-default)',
          'fg-muted': 'var(--gh-fg-muted)',
          'fg-subtle': 'var(--gh-fg-subtle)',
          'fg-onEmphasis': 'var(--gh-fg-onEmphasis)',
          
          // Border
          'border-default': 'var(--gh-border-default)',
          'border-muted': 'var(--gh-border-muted)',
          'border-subtle': 'var(--gh-border-subtle)',
          
          // Accent (Primary Blue)
          'accent-fg': 'var(--gh-accent-fg)',
          'accent-emphasis': 'var(--gh-accent-emphasis)',
          'accent-muted': 'var(--gh-accent-muted)',
          'accent-subtle': 'var(--gh-accent-subtle)',
          
          // Success (Green)
          'success-fg': 'var(--gh-success-fg)',
          'success-emphasis': 'var(--gh-success-emphasis)',
          'success-muted': 'var(--gh-success-muted)',
          'success-subtle': 'var(--gh-success-subtle)',
          
          // Danger (Red)
          'danger-fg': 'var(--gh-danger-fg)',
          'danger-emphasis': 'var(--gh-danger-emphasis)',
          'danger-muted': 'var(--gh-danger-muted)',
          'danger-subtle': 'var(--gh-danger-subtle)',
          
          // Warning (Yellow)
          'attention-fg': 'var(--gh-attention-fg)',
          'attention-emphasis': 'var(--gh-attention-emphasis)',
          'attention-muted': 'var(--gh-attention-muted)',
          'attention-subtle': 'var(--gh-attention-subtle)',
          
          // Neutral
          'neutral-muted': 'var(--gh-neutral-muted)',
          'neutral-subtle': 'var(--gh-neutral-subtle)',
        }
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Noto Sans',
          'Helvetica',
          'Arial',
          'sans-serif',
          'Apple Color Emoji',
          'Segoe UI Emoji',
        ],
        mono: [
          'ui-monospace',
          'SFMono-Regular',
          'SF Mono',
          'Menlo',
          'Consolas',
          'Liberation Mono',
          'monospace',
        ],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1.25rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['0.875rem', { lineHeight: '1.5rem' }],
        'lg': ['1rem', { lineHeight: '1.5rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
      },
      borderRadius: {
        'DEFAULT': '6px',
        'md': '6px',
        'lg': '8px',
      },
    },
  },
  plugins: [],
}

export default config
