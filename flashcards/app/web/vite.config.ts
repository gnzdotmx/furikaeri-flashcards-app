import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      // Avoid CORS headaches in dev; API still enforces allowlist.
      "/api": {
        target: "http://api:8000",
        changeOrigin: true,
      },
      "/audio": {
        target: "http://api:8000",
        changeOrigin: true,
      },
    },
  },
});

