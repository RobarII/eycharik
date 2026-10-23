import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// jsdom has no layout, so the shell's "scroll to top on navigation" is a no-op here. The node
// environment (a test that only reads files) has no `window` at all.
if (typeof window !== "undefined") window.scrollTo = vi.fn();

afterEach(() => {
  cleanup();
});
