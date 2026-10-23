import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchRuns } from "../api";
import type { RunSummary } from "../types";
import { RunsPage } from "./RunsPage";

vi.mock("../api", () => ({ fetchRuns: vi.fn() }));

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
      <RunsPage onOpen={() => undefined} onUnauthorized={() => undefined} />
    </QueryClientProvider>,
  );
}

describe("RunsPage", () => {
  beforeEach(() => {
    vi.mocked(fetchRuns).mockReset();
    window.location.hash = "#/runs";
  });

  it("prints the whole cohort size, not the size of the page", async () => {
    vi.mocked(fetchRuns).mockResolvedValue({ items: [run], next_cursor: "next", total: 128 });

    renderPage();

    expect(await screen.findByText("Пётр Петров")).toBeInTheDocument();
    expect(screen.getByText("1 из 128")).toBeInTheDocument();
  });

  it("asks the server for the active runs and sends the search along", async () => {
    vi.mocked(fetchRuns).mockResolvedValue({ items: [], next_cursor: null, total: 0 });

    renderPage();
    await userEvent.type(screen.getByRole("searchbox"), "петр");

    await waitFor(() =>
      expect(fetchRuns).toHaveBeenLastCalledWith(
        expect.objectContaining({ status: "active", q: "петр" }),
      ),
    );
    expect(window.location.hash).toContain("q=%D0%BF%D0%B5%D1%82%D1%80");
  });

  it("loads the next page with the cursor the server returned", async () => {
    vi.mocked(fetchRuns)
      .mockResolvedValueOnce({ items: [run], next_cursor: "next", total: 2 })
      .mockResolvedValueOnce({
        items: [{ ...run, run_id: "run-2", name: "Анна Аннова" }],
        next_cursor: null,
        total: 2,
      });

    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Показать ещё" }));

    expect(await screen.findByText("Анна Аннова")).toBeInTheDocument();
    expect(fetchRuns).toHaveBeenLastCalledWith(expect.objectContaining({ cursor: "next" }));
    expect(screen.queryByRole("button", { name: "Показать ещё" })).not.toBeInTheDocument();
  });

  it("offers no pager on a single page", async () => {
    vi.mocked(fetchRuns).mockResolvedValue({ items: [run], next_cursor: null, total: 1 });

    renderPage();
    await screen.findByText("Пётр Петров");

    expect(screen.queryByRole("button", { name: "Показать ещё" })).not.toBeInTheDocument();
  });

  it("explains an empty search instead of claiming an empty cohort", async () => {
    vi.mocked(fetchRuns).mockResolvedValue({ items: [], next_cursor: null, total: 0 });
    window.location.hash = "#/runs?q=%D0%BF%D0%B5%D1%82%D1%80";

    renderPage();

    expect(await screen.findByText("Ничего не найдено")).toBeInTheDocument();
    expect(screen.queryByText("Пока никого нет")).not.toBeInTheDocument();
  });
});
