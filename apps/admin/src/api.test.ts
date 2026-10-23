import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getToken, resolveQuestion, setToken, Unauthorized } from "./api";

const fetchMock = vi.fn();

function reply(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("token", () => {
  it("persists the token under the documented key and clears it", () => {
    setToken("secret");
    expect(localStorage.getItem("onboarding.admin.token")).toBe("secret");
    expect(getToken()).toBe("secret");

    setToken("");
    expect(getToken()).toBe("");
    expect(localStorage.getItem("onboarding.admin.token")).toBeNull();
  });
});

describe("resolveQuestion", () => {
  it("posts the reply with the bearer token", async () => {
    setToken("recruiter-token");
    fetchMock.mockResolvedValue(
      reply({
        id: 7,
        employee_id: "e-1",
        answered: true,
        resolved_at: "2026-10-24T10:00:00Z",
        resolved_by: "rec-1",
      }),
    );

    const result = await resolveQuestion(7, "ДМС с первого дня");

    expect(result.id).toBe(7);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/admin/api/questions/7/resolve");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ text: "ДМС с первого дня" }));
    expect(init.headers).toMatchObject({ Authorization: "Bearer recruiter-token" });
  });

  it("turns 401 into Unauthorized so the gate can clear the token", async () => {
    fetchMock.mockResolvedValue(new Response("", { status: 401 }));

    await expect(resolveQuestion(7, "текст")).rejects.toBeInstanceOf(Unauthorized);
  });

  it("surfaces the API detail on a conflict", async () => {
    fetchMock.mockResolvedValue(reply({ detail: "question 7 is already resolved" }, 409));

    await expect(resolveQuestion(7, "текст")).rejects.toThrow(
      "question 7 is already resolved",
    );
  });

  it("encodes the id into the path", async () => {
    fetchMock.mockResolvedValue(reply({}));

    await resolveQuestion(41, "текст");

    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toBe("/admin/api/questions/41/resolve");
  });
});
