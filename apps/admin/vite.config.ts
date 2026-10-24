import { execFileSync } from "node:child_process";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

import { previewApi } from "./preview/plugin";

/**
 * The build the tab is running.
 *
 * A commit is the only name an incident report can be matched against, so it is baked into the
 * bundle and also published as `/version.json`. The page keeps `no-store`, the assets are
 * content-addressed, so a deploy never breaks an open tab — it only makes it stale, and the tab can
 * say so instead of silently running year-old code.
 */
function buildId(): string {
  const explicit = process.env.VITE_BUILD_ID?.trim();
  if (explicit) return explicit;
  try {
    return execFileSync("git", ["rev-parse", "--short", "HEAD"], { encoding: "utf8" }).trim();
  } catch {
    return "dev";
  }
}

function releasePlugin(id: string): Plugin {
  const body = JSON.stringify({ build: id });
  return {
    name: "cabinet-release",
    configureServer(server) {
      server.middlewares.use("/version.json", (_request, response) => {
        response.setHeader("Content-Type", "application/json");
        response.setHeader("Cache-Control", "no-store");
        response.end(body);
      });
    },
    generateBundle() {
      this.emitFile({ type: "asset", fileName: "version.json", source: body });
    },
  };
}

export default defineConfig(({ mode }) => {
  const id = buildId();
  return {
    plugins: [react(), releasePlugin(id), ...(mode === "preview" ? [previewApi()] : [])],
    define: { __BUILD_ID__: JSON.stringify(id) },
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
  };
});
