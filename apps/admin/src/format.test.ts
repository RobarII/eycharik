import { afterEach, describe, expect, it, vi } from "vitest";

import { daysSince, formatDate, formatDateTime, reasonLabel } from "./format";

afterEach(() => {
  vi.useRealTimers();
});

describe("formatDate", () => {
  it("prints a Russian date with the year", () => {
    expect(formatDate("2026-10-24T10:00:00Z")).toMatch(/24 октября 2026/);
  });

  it("shows a dash instead of an invalid date", () => {
    expect(formatDate("not-a-date")).toBe("—");
  });
});

describe("formatDateTime", () => {
  it("keeps the time of the instant", () => {
    expect(formatDateTime("2026-10-24T10:30:00Z")).toMatch(/24 окт\..*, 1[03]:30/);
  });
});

describe("daysSince", () => {
  it("counts whole days from the instant, not from midnight", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-24T12:00:00Z"));

    expect(daysSince("2026-10-24T09:00:00Z")).toBe("сегодня");
    expect(daysSince("2026-10-23T09:00:00Z")).toBe("1 день");
    expect(daysSince("2026-10-19T09:00:00Z")).toBe("5 дн.");
  });

  it("never returns a negative age", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-24T12:00:00Z"));

    expect(daysSince("2026-10-25T12:00:00Z")).toBe("сегодня");
  });

  it("handles an invalid date", () => {
    expect(daysSince("nope")).toBe("—");
  });
});

describe("reasonLabel", () => {
  it("translates a known reason and passes an unknown one through", () => {
    expect(reasonLabel("no_sources")).toBe("Нет источника");
    expect(reasonLabel("vendor_specific")).toBe("vendor_specific");
  });
});
