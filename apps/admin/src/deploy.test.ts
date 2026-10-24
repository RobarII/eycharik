// @vitest-environment node
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

const nginx = readFileSync(new URL("../nginx.conf", import.meta.url), "utf8");

describe("the cabinet's nginx server", () => {
  it("ships a content security policy that forbids inline scripts and foreign origins", () => {
    expect(nginx).toContain("Content-Security-Policy $csp always");
    expect(nginx).toContain("script-src 'self'");
    expect(nginx).not.toContain("script-src 'self' 'unsafe-inline'");
    expect(nginx).toContain("connect-src 'self'");
    expect(nginx).toContain("frame-ancestors 'none'");
  });

  it("sets the other headers a logged-in cabinet needs", () => {
    expect(nginx).toContain('X-Content-Type-Options "nosniff"');
    expect(nginx).toContain('Referrer-Policy "no-referrer"');
    expect(nginx).toContain('X-Frame-Options "DENY"');
  });

  it("keeps the HTML and the API responses out of any cache", () => {
    expect(nginx).toContain('Cache-Control "no-store"');
    expect(nginx).toContain("max-age=31536000, immutable");
  });

  it("keeps the build id out of any cache, or a stale tab would never learn it is stale", () => {
    expect(nginx).toContain("location = /version.json");
    expect(nginx).toMatch(/location = \/version\.json \{[^}]*Cache-Control "no-store"/s);
  });

  it("resolves the API per request so a restart does not leave a stale address", () => {
    expect(nginx).toContain("resolver 127.0.0.11 valid=10s ipv6=off;");
    expect(nginx).toContain("proxy_pass http://$api_upstream:8000$request_uri;");
  });
});
