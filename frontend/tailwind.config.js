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
        forge: {
          bg: "#0B0F17",
          card: "#111827",
          hover: "#1E293B",
          border: "#1F2937",
          muted: "#94A3B8",
          text: "#F8FAFC",
          cyan: "#06B6D4",
          "cyan-light": "#22D3EE",
          violet: "#8B5CF6",
          "violet-light": "#A78BFA",
          danger: "#EF4444",
          warning: "#F59E0B",
          success: "#10B981",
        },
      },
    },
  },
  plugins: [],
}
