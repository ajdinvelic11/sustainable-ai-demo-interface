import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          base: "#07111f",
          raised: "#0c1728",
          panel: "#101d31",
          line: "#22324a"
        },
        signal: {
          cyan: "#18d3ff",
          blue: "#5aa7ff",
          green: "#54e38e",
          amber: "#f6c453",
          red: "#ff5d73"
        }
      },
      boxShadow: {
        panel: "0 20px 70px rgba(0, 0, 0, 0.35)"
      }
    }
  },
  plugins: []
} satisfies Config;

