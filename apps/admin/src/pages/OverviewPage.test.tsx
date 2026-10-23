import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchDigest, fetchOverview, fetchQuestions, fetchRuns } from "../api";
import type { RunSummary } from "../types";
import { OverviewPage } from "./OverviewPage";

vi.mock("../api", () => ({
  fetchOverview: vi.fn(),
  fetchRuns: vi.fn(),
  fetchQuestions: vi.fn(),
  fetchDigest: vi.fn(),
}));

const run: RunSummary = {
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
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <OverviewPage
        onOpenRun={vi.fn()}
        onNavigate={vi.fn()}
        onUnauthorized={vi.fn()}
      />
    </QueryClientProvider>,
  );
}

describe("OverviewPage", () => {
  beforeEach(() => {
    vi.mocked(fetchOverview).mockResolvedValue({
      active_runs: 12,
      completed_runs: 40,
      high_risk: 2,
      medium_risk: 5,
      unanswered_questions: 3,
      resolved_questions: 60,
      top_tags: [{ tag: "workload", count: 4 }],
      since: "2026-10-17T00:00:00Z",
    });
    vi.mocked(fetchRuns).mockResolvedValue({ items: [run], next_cursor: null, total: 12 });
    vi.mocked(fetchQuestions).mockResolvedValue({ items: [], next_cursor: null, total: 3 });
    vi.mocked(fetchDigest).mockResolvedValue({ items: [], since: "2026-10-17T00:00:00Z" });
  });

  it("counts the cohort, not the page it loaded", async () => {
    renderPage();

    expect(await screen.findByText("12 сотрудников")).toBeInTheDocument();
    expect(screen.getByText("40")).toBeInTheDocument();
  });

  it("says which numbers are a snapshot and which are a week", async () => {
    renderPage();

    await screen.findByText("12 сотрудников");
    expect(screen.getAllByText("Прямо сейчас, без окна")).toHaveLength(3);
    expect(screen.getByText(/за семь дней/)).toBeInTheDocument();
  });

  it("groups the cohort by the step they are stuck on", async () => {
    renderPage();

    expect(await screen.findByText("Документы")).toBeInTheDocument();
  });
});
