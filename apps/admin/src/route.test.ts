import { describe, expect, it } from "vitest";

import { parseRoute, routeHash, setParam } from "./route";

describe("parseRoute", () => {
  it("reads the section and the query", () => {
    const route = parseRoute("#/questions?status=answered");

    expect(route.name).toBe("questions");
    expect(route.params.get("status")).toBe("answered");
  });

  it("keeps the run id and its parameters", () => {
    const route = parseRoute("#/run/abc?tab=timeline");

    expect(route.name).toBe("run");
    expect(route.id).toBe("abc");
    expect(route.params.get("tab")).toBe("timeline");
  });

  it("says so when the address names no section", () => {
    expect(parseRoute("#/nonsense").name).toBe("notFound");
    expect(parseRoute("#/runs/extra").name).toBe("notFound");
  });

  it("treats the bare hash as the front door", () => {
    expect(parseRoute("").name).toBe("overview");
    expect(parseRoute("#/").name).toBe("overview");
  });

  it("treats a run without an id as the list", () => {
    expect(parseRoute("#/run/").name).toBe("runs");
  });
});

describe("routeHash", () => {
  it("round-trips a route with parameters", () => {
    const route = parseRoute("#/runs?status=completed&q=%D0%BF%D0%B5%D1%82%D1%80");

    expect(routeHash(route)).toBe("#/runs?status=completed&q=%D0%BF%D0%B5%D1%82%D1%80");
    expect(parseRoute(routeHash(route)).params.get("q")).toBe("петр");
  });

  it("drops the question mark when there are no parameters", () => {
    expect(routeHash({ name: "risk", params: new URLSearchParams() })).toBe("#/risk");
  });
});

describe("setParam", () => {
  it("deletes a parameter that became empty instead of leaving a bare key", () => {
    const params = new URLSearchParams("status=answered");

    setParam(params, "status", "");

    expect(params.toString()).toBe("");
  });

  it("replaces a value in place", () => {
    const params = new URLSearchParams("status=answered");

    setParam(params, "status", "unanswered");

    expect(params.get("status")).toBe("unanswered");
  });
});
