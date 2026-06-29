/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        parchment: '#F7F4EF',
        'parchment-border': '#E8E4DC',
        navy: '#1A1A2E',
        accent: '#4F46E5',
        'accent-hover': '#4338CA',
        muted: '#6B7280',
      },
      fontFamily: {
        display: ['DM Serif Display', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
      boxShadow: {
        paper: '2px 2px 0px #E8E4DC, 4px 4px 0px #DDD8CE',
        'paper-hover': '3px 3px 0px #D5D0C6, 6px 6px 0px #CAC5BB',
      },
    },
  },
  plugins: [],
}
