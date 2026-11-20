/** @type {import('tailwindcss').Config} */
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: token("bg"),
        surface: token("surface"),
        surface2: token("surface-2"),
        surface3: token("surface-3"),
        line: token("line"),
        ink: token("ink"),
        ink2: token("ink-2"),
        muted: token("muted"),
        accent: token("accent"),
        accent2: token("accent-2"),
        good: token("good"),
        warn: token("warn"),
        bad: token("bad"),
        info: token("info"),
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "0 1px 0 0 rgb(255 255 255 / 0.03) inset, 0 8px 24px -12px rgb(0 0 0 / 0.45)",
        glow: "0 0 0 1px rgb(var(--accent) / 0.35), 0 8px 30px -8px rgb(var(--accent) / 0.45)",
      },
      keyframes: {
        "fade-in": { from: { opacity: 0, transform: "translateY(4px)" }, to: { opacity: 1, transform: "none" } },
        breathe: { "0%,100%": { transform: "scale(1)", opacity: 0.9 }, "50%": { transform: "scale(1.04)", opacity: 1 } },
        ripple: { "0%": { transform: "scale(0.9)", opacity: 0.55 }, "100%": { transform: "scale(1.6)", opacity: 0 } },
        spin: { to: { transform: "rotate(360deg)" } },
      },
      animation: {
        "fade-in": "fade-in 220ms ease-out",
        breathe: "breathe 4s ease-in-out infinite",
        ripple: "ripple 1.6s ease-out infinite",
        "spin-slow": "spin 2.4s linear infinite",
      },
    },
  },
  plugins: [],
};
