/* Vite settings. In development the calls go to the backend on port 8765 (python -X utf8 app/run.py). */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8765", "/sheets": "http://127.0.0.1:8765" } },
});
