import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the UI talks to the FastAPI backend through this proxy,
// so no CORS configuration is needed. Override the target with NOVA_API_TARGET.
const target = process.env.NOVA_API_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": { target, changeOrigin: true } } },
  preview: { port: 4173, proxy: { "/api": { target, changeOrigin: true } } },
});
