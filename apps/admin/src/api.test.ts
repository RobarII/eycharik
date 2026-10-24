import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  Unauthorized,
  closeSession,
  fetchMe,
  offboardEmployee,
  openSession,
  resolveQuestion,
} from "./api";
import { errorText, isConflict } from "./errors";

const fetchMock = vi.fn();

function reply(body: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("session", () => {
  it("posts the token once and never puts it in a header", async () => {
    fetchMock.mockResolvedValue(reply(null, 204));

    await openSession("secret");

    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/admin/api/v1/session");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ token: "secret" }));
    expect(init.credentials).toBe("same-origin");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
  });

  it("signs out with a DELETE and no body", async () => {
    fetchMock.mockResolvedValue(reply(null, 204));

    await closeSession();

    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/admin/api/v1/session");
    expect(init.method).toBe("DELETE");
  });
});

describe("failures", () => {
  it("turns a 401 into Unauthorized so the shell drops the session", async () => {
    fetchMock.mockResolvedValue(reply({ detail: "unknown token" }, 401));

    await expect(fetchMe()).rejects.toBeInstanceOf(Unauthorized);
  });

  it("keeps the status of a refused write", async () => {
    fetchMock.mockResolvedValue(reply({ detail: "only hr_admin may change the knowledge base" }, 403));

    const failure = await offboardEmployee("1001").catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(ApiError);
    expect((failure as ApiError).status).toBe(403);
    expect(errorText(failure as Error)).toBe("Недостаточно прав для этого действия.");
  });

  it("recognises a conflict as a reason to refetch", async () => {
    fetchMock.mockResolvedValue(reply({ detail: "question already resolved" }, 409));

    const failure = await resolveQuestion(7, "text").catch((error: unknown) => error);

    expect(isConflict(failure as Error)).toBe(true);
    expect(errorText(failure as Error)).toContain("другом окне");
  });
});

describe("requests", () => {
  it("resolves a question with a json body", async () => {
    fetchMock.mockResolvedValue(
      reply({
        id: 7,
        employee_id: "1001",
        answered: true,
        resolved_at: "2026-10-24T10:00:00Z",
        resolved_by: "rec-1",
      }),
    );

    const resolved = await resolveQuestion(7, "reply");

    expect(resolved.answered).toBe(true);
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/admin/api/v1/questions/7/resolve");
    expect(init.body).toBe(JSON.stringify({ text: "reply" }));
  });

  it("offboards through a DELETE on the employee", async () => {
    fetchMock.mockResolvedValue(
      reply({
        employee_id: "1001",
        questions_deleted: 2,
        messages_deleted: 1,
        runs_closed: 1,
        audit_redacted: 3,
      }),
    );

    const result = await offboardEmployee("1001");

    expect(result.runs_closed).toBe(1);
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/admin/api/v1/employees/1001");
    expect(init.method).toBe("DELETE");
  });

  it("reports the caller's identity", async () => {
    fetchMock.mockResolvedValue(
      reply({
        role: "recruiter",
        subject: "rec-1",
        scope: { recruiter_id: "rec-1", department: null },
        capabilities: ["runs.read"],
        expires_at: null,
      }),
    );

    const me = await fetchMe();

    expect(me.role).toBe("recruiter");
    expect(me.capabilities).toEqual(["runs.read"]);
  });
});
