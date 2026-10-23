import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchRun, offboardEmployee } from "../api";
import type { Capability, RunDetail } from "../types";
import { SessionProvider, sessionFor } from "../session";
import { RunDetailPage } from "./RunDetailPage";

vi.mock("../api", () => ({ fetchRun: vi.fn(), offboardEmployee: vi.fn() }));

const run: RunDetail = {
  run_id: "run-1",
  employee_id: "3001",
  name: "Пётр Петров",
  role: "Оператор",
  department: "Производство",
  step_id: "documents",
  step_title: "Документы",
  step_number: 2,
  steps_total: 6,
  entered_at: "2026-10-20T09:00:00Z",
  updated_at: "2026-10-23T09:00:00Z",
  status: "active",
  step_message: null,
  scenario: "onboarding_plant",
  scenario_version: 2,
  tone: "formal",
  events: [
    {
      at: "2026-10-20T09:05:00Z",
      name: "step_transition",
      fields: { step: "documents", previous_step: "welcome", step_title: "Документы" },
    },
  ],
  questions: [],
};

function renderPage(capabilities: Capability[]) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <SessionProvider
        value={sessionFor({
          role: capabilities.includes("employees.offboard") ? "hr_admin" : "recruiter",
          subject: "rec-1",
          scope: { recruiter_id: "rec-1", department: null },
          capabilities,
          expires_at: null,
        })}
      >
        <RunDetailPage runId="run-1" onBack={vi.fn()} onUnauthorized={vi.fn()} />
      </SessionProvider>
    </QueryClientProvider>,
  );
}

describe("RunDetailPage", () => {
  beforeEach(() => {
    vi.mocked(fetchRun).mockReset();
    vi.mocked(fetchRun).mockResolvedValue(run);
    vi.mocked(offboardEmployee).mockReset();
  });

  it("tells the timeline in the recruiter's words", async () => {
    renderPage(["runs.read"]);

    expect(await screen.findByText("Знакомство → Документы")).toBeInTheDocument();
    expect(screen.getByText(/Завод \(ГТП\) · v2/)).toBeInTheDocument();
  });

  it("does not offer offboarding to a recruiter", async () => {
    renderPage(["runs.read"]);

    await screen.findByText("Пётр Петров");
    expect(screen.queryByRole("button", { name: "Офбордить" })).not.toBeInTheDocument();
  });

  it("warns before deleting the transcript and only then calls the API", async () => {
    vi.mocked(offboardEmployee).mockResolvedValue({
      employee_id: "3001",
      questions_deleted: 2,
      messages_deleted: 9,
      runs_closed: 1,
      audit_redacted: 3,
    });
    renderPage(["runs.read", "employees.offboard"]);

    await userEvent.click(await screen.findByRole("button", { name: "Офбордить" }));
    expect(offboardEmployee).not.toHaveBeenCalled();
    expect(screen.getByText(/Переписка Пётр Петров будет удалена сразу/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Да, офбордить" }));

    expect(await screen.findByText(/удалено 2 вопроса, 9 сообщений/)).toBeInTheDocument();
    expect(offboardEmployee).toHaveBeenCalledWith("3001");
  });

  it("lets the recruiter think again", async () => {
    renderPage(["runs.read", "employees.offboard"]);

    await userEvent.click(await screen.findByRole("button", { name: "Офбордить" }));
    await userEvent.click(screen.getByRole("button", { name: "Отмена" }));

    expect(screen.queryByRole("button", { name: "Да, офбордить" })).not.toBeInTheDocument();
    expect(offboardEmployee).not.toHaveBeenCalled();
  });
});
