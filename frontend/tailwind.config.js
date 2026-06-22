/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Space Grotesk", "sans-serif"],
        body: ["Manrope", "sans-serif"],
      },
      boxShadow: {
        card: "0 20px 50px rgba(0, 0, 0, 0.25)",
      },
      keyframes: {
        floatin: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        floatin: "floatin 0.35s ease-out",
      },
    },
  },
  plugins: [],
};
