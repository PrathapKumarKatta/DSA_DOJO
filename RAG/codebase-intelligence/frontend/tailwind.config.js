/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f7ff",
          100: "#e0effe",
          200: "#b9ddfe",
          300: "#7cc1fd",
          400: "#36a1fa",
          500: "#0c83eb",
          600: "#0267c7",
          700: "#0352a1",
          800: "#074685",
          900: "#0c3b6e",
          950: "#082548",
        },
        dark: {
          50: "#1e222b",
          100: "#181b22",
          200: "#13161c",
          300: "#0f1116",
          400: "#0a0c10",
        }
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Menlo", "Monaco", "Consolas", "monospace"],
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      }
    },
  },
  plugins: [],
}
