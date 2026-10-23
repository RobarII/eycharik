import type { IncomingMessage, ServerResponse } from "node:http";

import type { Plugin } from "vite";

import * as demo from "./data";

function send(response: ServerResponse, status: number, body: unknown): void {
  response.statusCode = status;
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  response.setHeader("Cache-Control", "no-store");
  response.end(JSON.stringify(body));
}

async function readJson(request: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) chunks.push(Buffer.from(chunk as Uint8Array));
  const text = Buffer.concat(chunks).toString("utf8");
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

function limitOf(url: URL, fallback: number, max: number): number {
  const parsed = Number(url.searchParams.get("limit") ?? fallback);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(1, Math.trunc(parsed)));
}

const SESSION_COOKIE = "onboarding_session";

function cookieToken(request: IncomingMessage): string | null {
  const header = request.headers.cookie ?? "";
  for (const part of header.split(";")) {
    const [name, ...rest] = part.trim().split("=");
    if (name === SESSION_COOKIE) return decodeURIComponent(rest.join("="));
  }
  return null;
}

async function handle(
  request: IncomingMessage,
  response: ServerResponse,
  next: () => void,
): Promise<void> {
  const url = new URL(request.url ?? "/", "http://localhost");
  const path = url.pathname;

  if (path === "/healthz" || path === "/readyz") {
    send(response, 200, { status: "ok" });
    return;
  }
  if (!path.startsWith("/admin/api/")) {
    next();
    return;
  }

  // The cabinet signs in with a cookie; `Authorization` stays for curl and the existing tests.
  const presented =
    (request.headers.authorization ?? "").replace(/^Bearer\s+/i, "") || cookieToken(request) || "";

  if (request.method === "POST" && path === "/admin/api/session") {
    const body = (await readJson(request)) as { token?: unknown } | null;
    const candidate = typeof body?.token === "string" ? body.token.trim() : "";
    if (!demo.TOKENS[candidate]) {
      send(response, 401, { detail: "unknown token" });
      return;
    }
    response.statusCode = 204;
    response.setHeader(
      "Set-Cookie",
      `${SESSION_COOKIE}=${encodeURIComponent(candidate)}; HttpOnly; SameSite=Strict; Path=/admin/api; Max-Age=43200`,
    );
    response.end();
    return;
  }

  if (request.method === "DELETE" && path === "/admin/api/session") {
    response.statusCode = 204;
    response.setHeader(
      "Set-Cookie",
      `${SESSION_COOKIE}=; HttpOnly; SameSite=Strict; Path=/admin/api; Max-Age=0`,
    );
    response.end();
    return;
  }

  const role = demo.TOKENS[presented];
  if (!role) {
    send(response, 401, { detail: "unauthorized" });
    return;
  }

  if (request.method === "GET" && path === "/admin/api/me") {
    send(response, 200, demo.identity(role));
    return;
  }

  if (request.method === "GET" && path === "/admin/api/runs") {
    const limit = limitOf(url, 50, 200);
    send(response, 200, { items: demo.runs(role).slice(0, limit) });
    return;
  }

  const runMatch = /^\/admin\/api\/runs\/([^/]+)$/.exec(path);
  if (request.method === "GET" && runMatch?.[1]) {
    const detail = demo.runDetail(role, decodeURIComponent(runMatch[1]));
    if (!detail) {
      send(response, 404, { detail: "run not found" });
      return;
    }
    send(response, 200, detail);
    return;
  }

  if (request.method === "GET" && path === "/admin/api/questions") {
    const status = url.searchParams.get("status") ?? "unanswered";
    if (!["unanswered", "answered", "all"].includes(status)) {
      send(response, 422, { detail: "status must be unanswered, answered or all" });
      return;
    }
    send(response, 200, demo.questions(role, status, limitOf(url, 50, 500)));
    return;
  }

  if (request.method === "GET" && path === "/admin/api/analytics/overview") {
    send(response, 200, demo.overview(role));
    return;
  }

  if (request.method === "GET" && path === "/admin/api/digest/weekly") {
    send(response, 200, demo.digest(role));
    return;
  }

  if (request.method === "GET" && path === "/admin/api/knowledge") {
    send(response, 200, demo.knowledge(role));
    return;
  }

  if (request.method === "POST" && path === "/admin/api/knowledge") {
    if (role !== "hr_admin") {
      send(response, 403, { detail: "only hr_admin may change the knowledge base" });
      return;
    }
    const body = (await readJson(request)) as { text?: unknown } | null;
    const text = typeof body?.text === "string" ? body.text : "";
    if (text.length < 20) {
      send(response, 422, { detail: "upload: text is required" });
      return;
    }
    const result = demo.upload(text);
    send(response, result.status, result.body);
    return;
  }

  send(response, 405, { detail: "method not allowed" });
}

/**
 * Serves the documented demo cohort on `/admin/api/*` during `vite --mode preview`.
 * It is never part of a production build: `apply: "serve"` keeps it out of `vite build`.
 */
export function previewApi(): Plugin {
  return {
    name: "onboarding-demo-api",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        void handle(request, response, next);
      });
    },
  };
}
