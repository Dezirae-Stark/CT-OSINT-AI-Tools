/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0a0b0d',
        'bg-secondary': '#111318',
        'bg-tertiary': '#1a1d24',
        'border-subtle': '#1f2330',
        'border-active': '#2d3447',
        'text-primary': '#e8eaf0',
        'text-secondary': '#8892a4',
        'text-dim': '#4a5568',
        'accent': '#3b82f6',
        'accent-secondary': '#6366f1',
      },
      fontFamily: {
        mono: ['"IBM Plex Mono"', '"JetBrains Mono"', 'monospace'],
        data: ['"JetBrains Mono"', 'monospace'],
        body: ['"Inter"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
