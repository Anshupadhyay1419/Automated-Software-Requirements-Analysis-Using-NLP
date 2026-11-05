import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Requests to /api go to the FastAPI backend, so no CORS setup is needed.
const backend = { target: "http://127.0.0.1:8000", changeOrigin: true };

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": backend } },
  preview: { port: 5173, proxy: { "/api": backend } },
});
