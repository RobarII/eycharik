import { describe, expect, it } from "vitest";

import { isStale } from "./version";

describe("isStale", () => {
  it("is true when the server names a different build", () => {
    expect(isStale("abc1234", "def5678")).toBe(true);
  });

  it("is false when the server names the build we are running", () => {
    expect(isStale("abc1234", "abc1234")).toBe(false);
  });

  it("never guesses from a body it could not read", () => {
    expect(isStale("abc1234", undefined)).toBe(false);
    expect(isStale("abc1234", null)).toBe(false);
    expect(isStale("abc1234", "")).toBe(false);
    expect(isStale("abc1234", 42)).toBe(false);
  });
});
