/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './generator/templates/**/*.html',
    './generator/**/*.py',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'github-canvas-default': '#ffffff',
        'github-canvas-subtle': '#f6f8fa',
        'github-border-default': '#d1d9e0',
        'github-fg-default': '#24292f',
        'github-fg-muted': '#656d76',
        'github-accent-fg': '#0969da',
        'github-success-fg': '#2da44e',
        'github-dark-canvas-default': '#0d1117',
        'github-dark-canvas-subtle': '#161b22',
        'github-dark-border-default': '#30363d',
        'github-dark-fg-default': '#f0f6fc',
        'github-dark-fg-muted': '#7d8590',
        'github-dark-accent-fg': '#58a6ff',
        'github-dark-success-fg': '#3fb950',
      }
    }
  },
  plugins: [],
}
