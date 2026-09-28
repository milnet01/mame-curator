import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const API_TARGET = "http://127.0.0.1:8080";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    tsconfigPaths: true,
  },
  build: {
    // mame-curator-1108: the budget that matters is P06's initial-JS
    // limit of 350 kB gzipped (docs/specs/P06-frontend-mvp.md), which
    // `npm run size` enforces (mame-curator-1120). This
    // warning counts raw minified bytes and fired at 500 kB while the
    // entry chunk was ~163 kB gzipped. Every route, Library included, is
    // already lazy (App.tsx), so the entry chunk is the shared shell.
    chunkSizeWarningLimit: 700,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: API_TARGET, changeOrigin: true },
      "/media": { target: API_TARGET, changeOrigin: true },
    },
  },
});
