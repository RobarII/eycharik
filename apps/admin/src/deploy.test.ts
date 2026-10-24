// @vitest-environment node
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

const nginx = readFileSync(new URL("../nginx.conf", import.meta.url), "utf8");
const dockerfile = readFileSync(new URL("../Dockerfile", import.meta.url), "utf8");
const release = readFileSync(
  new URL("../../../.github/workflows/release.yml", import.meta.url),
  "utf8",
);

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

describe("the admin image", () => {
  it("takes the build id as a build argument, because its context has no .git", () => {
    expect(dockerfile).toContain("ARG VITE_BUILD_ID=");
    expect(dockerfile).toContain("ENV VITE_BUILD_ID=$VITE_BUILD_ID");
  });

  it("receives the released commit from the workflow", () => {
    expect(release).toContain("short=$(git rev-parse --short HEAD)");
    expect(release).toMatch(/build-args: \|\n\s+VITE_BUILD_ID=\$\{\{ needs\.version\.outputs\.short \}\}/);
  });

  it("is built from the commit the version job resolved, not from a moving branch", () => {
    expect(release).toMatch(/ref: \$\{\{ needs\.version\.outputs\.sha \}\}/);
    expect(release).toMatch(/-\$\{\{ matrix\.name \}\}:\$\{\{ needs\.version\.outputs\.sha \}\}/);
  });

  it("tags the push to main only after both images were pushed", () => {
    expect(release).toContain("branches: [main]");
    expect(release).toContain("needs: [version, build]");
    expect(release).toContain(
      "if: github.event_name == 'push' && github.ref == 'refs/heads/main'",
    );
    expect(release).toContain('git push origin "refs/tags/$VERSION"');
  });

  it("leaves an existing tag alone, so a re-run does not invent a version", () => {
    expect(release).toMatch(/if git rev-parse -q --verify "refs\/tags\/\$VERSION"/);
  });
});
