import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  Unauthorized,
  closeSession,
  fetchMe,
  fetchOverview,
  openSession,
} from "./api";
import type { AdminIdentity } from "./types";
import { App } from "./App";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    fetchMe: vi.fn(),
    openSession: vi.fn(),
    closeSession: vi.fn(),
    fetchOverview: vi.fn(),
    fetchRuns: vi.fn(),
    fetchQuestions: vi.fn(),
    fetchDigest: vi.fn(),
  };
});

const emptyOverview = {
  active_runs: 0,
  completed_runs: 0,
  high_risk: 0,
  medium_risk: 0,
  unanswered_questions: 0,
  resolved_questions: 0,
  top_tags: [],
  since: "2026-10-17T00:00:00Z",
};

function identity(capabilities: AdminIdentity["capabilities"], role = "recruiter"): AdminIdentity {
  return {
    role: role as AdminIdentity["role"],
    subject: "rec-1",
    scope: { recruiter_id: "rec-1", department: null },
    capabilities,
    expires_at: null,
  };
}

function renderApp() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}

describe("App", () => {
  beforeEach(() => {
    vi.mocked(fetchMe).mockReset();
    vi.mocked(openSession).mockReset();
    vi.mocked(closeSession).mockReset();
    vi.mocked(fetchOverview).mockReset();
    vi.mocked(fetchOverview).mockResolvedValue(emptyOverview as never);
    window.location.hash = "#/overview";
  });

  it("shows the gate when the cookie is gone instead of an empty cabinet", async () => {
    vi.mocked(fetchMe).mockRejectedValue(new Unauthorized());

    renderApp();

    expect(await screen.findByRole("button", { name: "Войти в кабинет" })).toBeInTheDocument();
  });

  it("opens a session from the gate and renders the shell", async () => {
    vi.mocked(fetchMe).mockRejectedValueOnce(new Unauthorized());
    renderApp();

    vi.mocked(fetchMe).mockResolvedValue(identity(["runs.read", "questions.read"]));
    vi.mocked(openSession).mockResolvedValue(undefined);
    await userEvent.type(await screen.findByLabelText("Токен доступа"), "secret-token");
    await userEvent.click(screen.getByRole("button", { name: "Войти в кабинет" }));

    await waitFor(() => expect(openSession).toHaveBeenCalledWith("secret-token"));
    await waitFor(() => expect(vi.mocked(fetchMe).mock.calls.length).toBeGreaterThan(1));
    expect(await screen.findByRole("button", { name: /Сотрудники/ })).toBeInTheDocument();
  });

  it("hides a section the role cannot read", async () => {
    vi.mocked(fetchMe).mockResolvedValue(identity(["runs.read"], "manager"));

    renderApp();

    await screen.findByRole("button", { name: /Обзор/ });
    expect(screen.queryByRole("button", { name: /Знания/ })).not.toBeInTheDocument();
    expect(screen.getByText("Руководитель подразделения")).toBeInTheDocument();
  });

  it("drops the session when the API says it expired", async () => {
    vi.mocked(fetchMe).mockResolvedValue(identity(["runs.read"]));
    vi.mocked(fetchOverview).mockRejectedValue(new Unauthorized());
    vi.mocked(closeSession).mockResolvedValue(undefined);

    renderApp();

    await waitFor(() => expect(closeSession).toHaveBeenCalled());
  });
});
