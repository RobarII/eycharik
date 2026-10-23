import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

import { previewApi } from "./preview/plugin";

export default defineConfig(({ mode }) => ({
  plugins: [react(), ...(mode === "preview" ? [previewApi()] : [])],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/admin/api": {
        target: process.env.VITE_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: { outDir: "dist", sourcemap: false },
}));
