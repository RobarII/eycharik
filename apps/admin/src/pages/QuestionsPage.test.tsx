import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { assignQuestion, fetchQuestions, fetchRuns, resolveQuestion } from "../api";
import type { Question, RunSummary } from "../types";
import { SessionProvider, sessionFor } from "../session";
import { QuestionsPage } from "./QuestionsPage";

type Tested = "questions.read" | "questions.resolve" | "questions.assign";

function session(capabilities: Tested[]) {
  return sessionFor({
    role: "recruiter",
    subject: "rec-1",
    scope: { recruiter_id: "rec-1", department: null },
    capabilities,
    expires_at: null,
  });
}

vi.mock("../api", () => ({
  assignQuestion: vi.fn(),
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
  updated_at: "2026-10-24T09:00:00Z",
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
  assignee: null,
};

function renderPage(
  capabilities: Tested[] = ["questions.read", "questions.resolve", "questions.assign"],
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <SessionProvider value={session(capabilities)}>
        <QuestionsPage onOpenRun={vi.fn()} onUnauthorized={vi.fn()} />
      </SessionProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(fetchQuestions).mockResolvedValue({ items: [question], total: 1, next_cursor: null });
  vi.mocked(fetchRuns).mockResolvedValue({ items: [run], total: 1, next_cursor: null });
  vi.mocked(resolveQuestion).mockResolvedValue({
    id: 7,
    employee_id: "e-1",
    answered: true,
    resolved_at: "2026-10-24T10:00:00Z",
    resolved_by: "rec-1",
  });
  vi.mocked(assignQuestion).mockResolvedValue({
    id: 7,
    employee_id: "e-1",
    assignee: "rec-1",
  });
});

describe("QuestionsPage", () => {
  it("shows the question with its author and run context", async () => {
    renderPage();

    expect(await screen.findByText("Когда начнёт действовать ДМС?")).toBeInTheDocument();
    expect(screen.getByText("Анна Петрова")).toBeInTheDocument();
    expect(screen.getByText("Оператор · Производство")).toBeInTheDocument();
    expect(screen.getByText("Нет источника")).toBeInTheDocument();
    expect(fetchQuestions).toHaveBeenCalledWith({
      status: "unanswered",
      assignee: "any",
      cursor: null,
      limit: 50,
    });
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
      total: 1,
      next_cursor: null,
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

  it("offers no reply button to a role that may not resolve", async () => {
    renderPage(["questions.read"]);

    expect(await screen.findByText(/Когда начнёт действовать ДМС/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ответить в MAX" })).not.toBeInTheDocument();
    expect(screen.getByText(/нет этого права/)).toBeInTheDocument();
  });

  it("claims a question for the signed-in recruiter", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: "Забрать себе" }));

    await waitFor(() => {
      expect(assignQuestion).toHaveBeenCalledWith(7, "rec-1");
    });
  });

  it("gives the question back instead of claiming it twice", async () => {
    vi.mocked(fetchQuestions).mockResolvedValue({
      items: [{ ...question, assignee: "rec-1" }],
      total: 1,
      next_cursor: null,
    });
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("Ваш вопрос")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Снять с себя" }));

    await waitFor(() => {
      expect(assignQuestion).toHaveBeenCalledWith(7, null);
    });
  });

  it("shows another's name without offering the claim button to a role that may not assign", async () => {
    vi.mocked(fetchQuestions).mockResolvedValue({
      items: [{ ...question, assignee: "rec-2" }],
      total: 1,
      next_cursor: null,
    });
    renderPage(["questions.read", "questions.resolve"]);

    expect(await screen.findByText("rec-2")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Забрать себе/ })).not.toBeInTheDocument();
  });

  it("shows an empty state rather than a blank page", async () => {
    vi.mocked(fetchQuestions).mockResolvedValue({ items: [], total: 0, next_cursor: null });

    renderPage();

    expect(await screen.findByText("Очередь пуста")).toBeInTheDocument();
  });
});
