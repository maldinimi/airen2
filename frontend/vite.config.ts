import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Mode dev: Vite meneruskan /api ke kontainer api. Produksi: nginx (lihat nginx.conf).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: { "/api": { target: process.env.API_URL ?? "http://api:8000", changeOrigin: false } },
    watch: { usePolling: true, interval: 500 }, // bind mount Windows/OneDrive tidak mengirim event berkas
  },
  build: { chunkSizeWarningLimit: 1500 },
});
