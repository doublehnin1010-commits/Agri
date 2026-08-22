/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Noto Sans Myanmar",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        display: ["Oswald", "Noto Sans Myanmar", "ui-sans-serif", "sans-serif"],
      },
      colors: {
        cream: {
          50: "#F8FAF7",
          DEFAULT: "#F8FAF7",
          100: "#E8F5E9",
          200: "#DDE5DD",
        },
        brand: {
          50: "#E8F5E9",
          100: "#D7EED8",
          200: "#B7DDBA",
          300: "#8BC68F",
          400: "#5EAA63",
          500: "#388E3C",
          600: "#2E7D32",
          700: "#1B5E20",
          800: "#154A19",
          900: "#0F3512",
        },
        accent: {
          50: "#E8F5E9",
          100: "#E8F5E9",
          500: "#2E7D32",
          600: "#1B5E20",
        },
      },
      boxShadow: {
        soft: "0 18px 60px rgba(38, 50, 56, 0.10)",
      },
    },
  },
  plugins: [],
};

