/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'graph-bg': '#1e1e1e',
        'panel-bg': '#252526',
        'border': '#3c3c3c',
        'text-primary': '#cccccc',
        'text-secondary': '#858585',
        'accent': '#0e639c',
        'accent-hover': '#1177bb',
        'node-function': '#4fc3f7',
        'node-class': '#81c784',
        'node-module': '#ffb74d',
        'node-variable': '#ce93d8',
        'node-parameter': '#90a4ae',
        'node-callsite': '#f48fb1',
        'node-type': '#fff176',
        'edge-calls': '#4fc3f7',
        'edge-inherits': '#81c784',
        'edge-imports': '#ffb74d',
        'diff-added': '#2ea043',
        'diff-removed': '#f85149',
        'diff-modified': '#d29922',
      },
    },
  },
  plugins: [],
}
