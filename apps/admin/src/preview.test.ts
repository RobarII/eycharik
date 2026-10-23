// @vitest-environment node
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { CAPABILITIES } from "../preview/data";

/**
 * The preview builds its own API, so the capability lists live in two places. This test is the
 * seam: it reads the server's single source of truth and fails when the copies disagree, so the
 * demo cannot offer a button the real API would refuse.
 */
const AUTH = fileURLToPath(
  new URL("../../../apps/api/onboarding/api/auth.py", import.meta.url),
);

function serverCapabilities(): Record<string, string[]> {
  const source = readFileSync(AUTH, "utf8");
  const block = /CAPABILITIES: dict\[str, tuple\[str, \.\.\.\]\] = \{(.*?)\n\}/s.exec(source);
  if (!block?.[1]) throw new Error("CAPABILITIES not found in auth.py");
  const found: Record<string, string[]> = {};
  for (const match of block[1].matchAll(/"([a-z_]+)": \(([^)]*)\)/gs)) {
    found[match[1] as string] = [...(match[2] as string).matchAll(/"([^"]+)"/g)].map(
      (capability) => capability[1] as string,
    );
  }
  return found;
}

describe("preview capabilities", () => {
  it("matches the server's capability table", () => {
    const server = serverCapabilities();

    expect(server).toMatchObject(CAPABILITIES);
    for (const [role, capabilities] of Object.entries(CAPABILITIES)) {
      expect(server[role], `role ${role}`).toEqual([...capabilities]);
    }
  });
});
