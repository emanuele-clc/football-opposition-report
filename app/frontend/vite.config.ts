import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the API runs on python -X utf8 app/run.py (port 8765).
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8765", "/sheets": "http://127.0.0.1:8765" } },
});
