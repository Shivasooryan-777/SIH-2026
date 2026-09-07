/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#09090B",
        surface: {
          DEFAULT: "#131316",
          hover: "#1C1C21",
        },
        border: {
          DEFAULT: "#26262B",
        },
        text: {
          primary: "#F4F4F5",
          secondary: "#A1A1AA",
          tertiary: "#71717A",
        },
        accent: {
          DEFAULT: "#29B6C2",
          glow: "#6EE7E0",
        },
        semantic: {
          positive: "#22A97A", // FixNow
          wait: "#E8A33D",     // Wait / Elevated
          risk: "#E4574C",     // High risk
        },
        landing: {
          start: "#05070D",
          end: "#0E1626",
          scrim: "#050708",
          text: "#F5F5F4",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      borderRadius: {
        "2xl": "1rem",
      },
      boxShadow: {
        "accent-glow": "0 0 35px -5px rgba(41, 182, 194, 0.25)",
      },
    },
  },
  plugins: [],
};
