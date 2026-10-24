// @vitest-environment node
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

const nginx = readFileSync(new URL("../nginx.conf", import.meta.url), "utf8");
const dockerfile = readFileSync(new URL("../Dockerfile", import.meta.url), "utf8");
const release = readFileSync(
  new URL("../../../.github/workflows/release.yml", import.meta.url),
  "utf8",
);
const deploy = readFileSync(
  new URL("../../../.github/workflows/deploy.yml", import.meta.url),
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
    expect(release).toContain('echo "sha=$(git rev-parse HEAD)"');
    expect(release).toMatch(/build-args: \|\n\s+VITE_BUILD_ID=\$\{\{ steps\.rev\.outputs\.sha \}\}/);
  });

  it("is published under the commit it was built from, never under a moving branch", () => {
    expect(release).toMatch(/}-\$\{\{ matrix\.name \}\}:sha-\$\{\{ steps\.rev\.outputs\.sha \}\}/);
    expect(release).not.toContain(":latest");
  });
});

describe("the release workflow", () => {
  it("compiles nothing when it promotes a version", () => {
    // `imagetools create` copies a manifest; `build-push-action` runs once, in the `build` job.
    expect(release).toContain("docker buildx imagetools create --tag");
    expect((release.match(/docker\/build-push-action/g) ?? []).length).toBe(1);
  });

  it("takes the version from a human ref and refuses anything else", () => {
    expect(release).toContain("scripts/release_version.py --ref");
    expect(release).not.toContain('git tag -a');
    expect(release).not.toContain('git push origin "refs/tags/');
  });

  it("builds a push to main and promotes a tag, and never both", () => {
    expect(release).toContain("branches: [main]");
    expect(release).toContain("tags: [\"v*\"]");
    expect(release).toContain("if: github.event_name == 'push' && github.ref_type == 'branch'");
    expect(release).toContain("'push' && github.ref_type == 'tag'");
  });

  it("fails when the digest for that commit was never published", () => {
    expect(release).toContain("imagetools inspect");
    expect(release).toContain("is not in the registry");
  });
});

describe("the deploy workflow", () => {
  it("is reached by a version tag, not by a merge into main", () => {
    expect(deploy).toContain("startsWith(github.event.workflow_run.head_branch, 'v')");
  });

  it("refuses a commit without the gate, even from a manual run", () => {
    expect(deploy).toContain('select(.name == "gate" and .conclusion == "success")');
  });

  it("refuses a commit whose images are not published", () => {
    expect(deploy).toContain("docker manifest inspect");
  });
});
