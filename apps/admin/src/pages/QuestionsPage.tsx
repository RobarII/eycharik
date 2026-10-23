import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchQuestions, fetchRuns } from "../api";
import { AnswerPill, ReasonPill } from "../components/Pills";
import { EmptyState, ErrorNote, SkeletonRows } from "../components/States";
import { formatDateTime } from "../format";
import type { Question, RunSummary } from "../types";
import { useUnauthorized } from "../useUnauthorized";

type Status = "unanswered" | "answered" | "all";

const TABS: ReadonlyArray<readonly [Status, string]> = [
  ["unanswered", "Без ответа"],
  ["all", "Все"],
  ["answered", "Отвеченные"],
];

export function QuestionsPage({
  onOpenRun,
  onUnauthorized,
}: {
  onOpenRun: (runId: string) => void;
  onUnauthorized: () => void;
}) {
  const [status, setStatus] = useState<Status>("unanswered");
  const query = useQuery({
    queryKey: ["questions", status],
    queryFn: () => fetchQuestions(status),
    refetchInterval: 15_000,
  });
  const runs = useQuery({ queryKey: ["runs"], queryFn: () => fetchRuns() });
  useUnauthorized(query.error, onUnauthorized);

  const byEmployee = new Map<string, RunSummary>(
    (runs.data?.items ?? []).map((run) => [run.employee_id, run]),
  );

  return (
    <section className="page">
      <header className="page-head">
        <div>
          <h1>Вопросы сотрудников</h1>
          <p className="muted">
            Всё, что бот не смог закрыть сам. Разберите вопрос и вернитесь к сотруднику в MAX.
          </p>
        </div>
        <div className="page-count" aria-live="polite">
          {query.isSuccess ? `${query.data.items.length} в выборке` : "…"}
        </div>
      </header>

      <div className="toolbar">
        <div className="segmented" role="tablist" aria-label="Фильтр вопросов">
          {TABS.map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={status === value}
              className={status === value ? "segment segment-on" : "segment"}
              onClick={() => setStatus(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {query.isPending ? <SkeletonRows /> : null}
      {query.isError && query.error.name !== "Unauthorized" ? (
        <ErrorNote message={query.error.message} onRetry={() => void query.refetch()} />
      ) : null}
      {query.isSuccess && query.data.items.length === 0 ? (
        <EmptyState title="Очередь пуста">
          Вопросы появятся здесь, когда ассистент передаст их человеку.
        </EmptyState>
      ) : null}

      {query.data && query.data.items.length > 0 ? (
        <ul className="question-cards">
          {query.data.items.map((question) => (
            <QuestionCard
              key={`${question.asked_at}-${question.employee_id}-${question.text}`}
              question={question}
              run={byEmployee.get(question.employee_id)}
              onOpenRun={onOpenRun}
            />
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function QuestionCard({
  question,
  run,
  onOpenRun,
}: {
  question: Question;
  run: RunSummary | undefined;
  onOpenRun: (runId: string) => void;
}) {
  return (
    <li className="card question-card">
      <div className="question-head">
        <div>
          <p className="question-author">{question.employee_name}</p>
          <p className="muted small">
            {run ? `${run.role} · ${run.department}` : "Профиль не найден"}
          </p>
        </div>
        <AnswerPill answered={question.answered} />
      </div>
      <p className="question-text">{question.text}</p>
      <div className="question-foot">
        <ReasonPill reason={question.reason} />
        <time dateTime={question.asked_at}>{formatDateTime(question.asked_at)}</time>
        {run ? (
          <button type="button" className="link-button" onClick={() => onOpenRun(run.run_id)}>
            Открыть сотрудника →
          </button>
        ) : null}
      </div>
      {question.citations.length > 0 ? (
        <p className="citations">
          {question.citations.map((citation) => (
            <code key={citation}>{citation}</code>
          ))}
        </p>
      ) : null}
    </li>
  );
}
