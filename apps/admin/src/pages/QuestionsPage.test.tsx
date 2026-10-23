import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchQuestions, fetchRuns, resolveQuestion } from "../api";
import type { Question, RunSummary } from "../types";
import { QuestionsPage } from "./QuestionsPage";

vi.mock("../api", () => ({
  fetchQuestions: vi.fn(),
  fetchRuns: vi.fn(),
  resolveQuestion: vi.fn(),
}));

const run: RunSummary = {
  run_id: "run-1",
  employee_id: "e-1",
  name: "Анна Петрова",
  role: "Оператор",
  department: "Производство",
  step_id: "day_one",
  step_title: "Первый день",
  step_number: 3,
  steps_total: 20,
  entered_at: "2026-10-20T09:00:00Z",
  status: "active",
};

const question: Question = {
  id: 7,
  employee_id: "e-1",
  employee_name: "Анна Петрова",
  text: "Когда начнёт действовать ДМС?",
  answered: false,
  reason: "no_sources",
  citations: [],
  asked_at: "2026-10-24T09:00:00Z",
  resolved_at: null,
  resolved_by: null,
};

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <QuestionsPage onOpenRun={vi.fn()} onUnauthorized={vi.fn()} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(fetchQuestions).mockResolvedValue({ items: [question] });
  vi.mocked(fetchRuns).mockResolvedValue({ items: [run] });
  vi.mocked(resolveQuestion).mockResolvedValue({
    id: 7,
    employee_id: "e-1",
    answered: true,
    resolved_at: "2026-10-24T10:00:00Z",
    resolved_by: "rec-1",
  });
});

describe("QuestionsPage", () => {
  it("shows the question with its author and run context", async () => {
    renderPage();

    expect(await screen.findByText("Когда начнёт действовать ДМС?")).toBeInTheDocument();
    expect(screen.getByText("Анна Петрова")).toBeInTheDocument();
    expect(screen.getByText("Оператор · Производство")).toBeInTheDocument();
    expect(screen.getByText("Нет источника")).toBeInTheDocument();
    expect(fetchQuestions).toHaveBeenCalledWith("unanswered");
  });

  it("sends the reply to the API and closes the form", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: "Ответить в MAX" }));
    const textarea = screen.getByLabelText(/Ответ сотруднику/);
    await user.type(textarea, "ДМС действует с первого рабочего дня.");
    await user.click(screen.getByRole("button", { name: "Отправить" }));

    await waitFor(() => {
      expect(resolveQuestion).toHaveBeenCalledWith(7, "ДМС действует с первого рабочего дня.");
    });
    await waitFor(() => {
      expect(screen.queryByLabelText(/Ответ сотруднику/)).not.toBeInTheDocument();
    });
  });

  it("does not submit an empty reply", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: "Ответить в MAX" }));
    expect(screen.getByRole("button", { name: "Отправить" })).toBeDisabled();
    expect(resolveQuestion).not.toHaveBeenCalled();
  });

  it("shows the resolution instead of the form once the question is closed", async () => {
    vi.mocked(fetchQuestions).mockResolvedValue({
      items: [
        {
          ...question,
          answered: true,
          resolved_at: "2026-10-24T10:00:00Z",
          resolved_by: "rec-1",
        },
      ],
    });

    renderPage();

    expect(await screen.findByText(/Закрыт/)).toBeInTheDocument();
    expect(screen.getByText(/rec-1/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ответить в MAX" })).not.toBeInTheDocument();
  });

  it("shows an empty state rather than a blank page", async () => {
    vi.mocked(fetchQuestions).mockResolvedValue({ items: [] });

    renderPage();

    expect(await screen.findByText("Очередь пуста")).toBeInTheDocument();
  });
});
