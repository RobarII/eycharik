import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { UseMutationResult } from "@tanstack/react-query";
import { useState } from "react";

import { fetchQuestions, fetchRuns, resolveQuestion } from "../api";
import { ArrowUpRightIcon } from "../components/Icons";
import { AnswerPill, ReasonPill } from "../components/Pills";
import { EmptyState, ErrorNote, SkeletonRows } from "../components/States";
import { countLabel, formatDateTime, initials } from "../format";
import type { Question, ResolvedQuestion, RunSummary } from "../types";
import { useUnauthorized } from "../useUnauthorized";
import { useSession } from "../session";
import { REFRESH } from "../config";
import { setParam, useRoute } from "../route";

type Status = "unanswered" | "answered" | "all";

const TABS: ReadonlyArray<readonly [Status, string]> = [
  ["unanswered", "Без ответа"],
  ["all", "Все"],
  ["answered", "Отвеченные"],
];

function readStatus(value: string | null): Status {
  return TABS.some(([status]) => status === value) ? (value as Status) : "unanswered";
}

export function QuestionsPage({
  onOpenRun,
  onUnauthorized,
}: {
  onOpenRun: (runId: string) => void;
  onUnauthorized: () => void;
}) {
  const { route, setParams } = useRoute();
  const status = readStatus(route.params.get("status"));
  const { can } = useSession();
  const query = useInfiniteQuery({
    queryKey: ["questions", status],
    queryFn: ({ pageParam }) => fetchQuestions({ status, cursor: pageParam, limit: 50 }),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
    refetchInterval: REFRESH.questions,
  });
  const runs = useQuery({
    queryKey: ["runs", "directory"],
    queryFn: () => fetchRuns({ status: "all", limit: 200 }),
    staleTime: 60_000,
  });
  const queryClient = useQueryClient();
  const resolve = useMutation({
    mutationFn: ({ id, text }: { id: number; text: string }) => resolveQuestion(id, text),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["questions"] });
      await queryClient.invalidateQueries({ queryKey: ["overview"] });
      await queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
  });
  useUnauthorized(query.error, onUnauthorized);
  useUnauthorized(resolve.error, onUnauthorized);

  const byEmployee = new Map<string, RunSummary>(
    (runs.data?.items ?? []).map((run) => [run.employee_id, run]),
  );
  const items = query.data?.pages.flatMap((page) => page.items) ?? [];
  const total = query.data?.pages[0]?.total ?? 0;

  return (
    <section className="page">
      <header className="page-head">
        <div className="page-head-text">
          <p className="eyebrow">Очередь</p>
          <h1>Вопросы сотрудников</h1>
          <p className="muted">
            Всё, что бот не смог закрыть сам. Ответьте здесь — сообщение уйдёт сотруднику в MAX, а
            вопрос закроется.
          </p>
        </div>
        <div className="page-count" aria-live="polite">
          {query.isSuccess ? countLabel(total, "вопрос", "вопроса", "вопросов") : "…"}
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
              onClick={() =>
                setParams((params) =>
                  setParam(params, "status", value === "unanswered" ? "" : value),
                )
              }
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
      {query.isSuccess && items.length === 0 ? (
        <EmptyState title="Очередь пуста">
          Вопросы появятся здесь, когда ассистент передаст их человеку.
        </EmptyState>
      ) : null}

      {items.length > 0 ? (
        <ul className="question-cards">
          {items.map((question) => (
            <QuestionCard
              key={question.id}
              question={question}
              run={byEmployee.get(question.employee_id)}
              onOpenRun={onOpenRun}
              resolve={resolve}
              canResolve={can("questions.resolve")}
            />
          ))}
        </ul>
      ) : null}

      {query.hasNextPage ? (
        <div className="page-more">
          <button
            type="button"
            className="button button-quiet"
            disabled={query.isFetchingNextPage}
            onClick={() => void query.fetchNextPage()}
          >
            {query.isFetchingNextPage ? "Загружаем…" : "Показать ещё"}
          </button>
        </div>
      ) : null}
    </section>
  );
}

type ResolveMutation = UseMutationResult<
  ResolvedQuestion,
  Error,
  { id: number; text: string }
>;

function QuestionCard({
  question,
  run,
  onOpenRun,
  resolve,
  canResolve,
}: {
  question: Question;
  run: RunSummary | undefined;
  onOpenRun: (runId: string) => void;
  resolve: ResolveMutation;
  canResolve: boolean;
}) {
  return (
    <li className="card question-card">
      <div className="question-head">
        <div className="question-identity">
          <span className="avatar avatar-sm" aria-hidden="true">
            {initials(question.employee_name)}
          </span>
          <div>
            <p className="question-author">{question.employee_name}</p>
            <p className="muted small">
              {run ? `${run.role} · ${run.department}` : "Профиль не найден"}
            </p>
          </div>
        </div>
        <AnswerPill answered={question.answered} />
      </div>
      <p className="question-text">{question.text}</p>
      <div className="question-foot">
        <ReasonPill reason={question.reason} />
        <time dateTime={question.asked_at}>{formatDateTime(question.asked_at)}</time>
        {run ? (
          <button type="button" className="link-button" onClick={() => onOpenRun(run.run_id)}>
            Открыть сотрудника
            <ArrowUpRightIcon width={13} height={13} />
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
      {question.answered && question.resolved_at ? (
        <p className="muted small">
          Закрыт {formatDateTime(question.resolved_at)}
          {question.resolved_by ? ` · ${question.resolved_by}` : ""}
        </p>
      ) : null}
      {!question.answered && canResolve ? (
        <ReplyForm question={question} resolve={resolve} />
      ) : null}
      {!question.answered && !canResolve ? (
        <p className="muted small">
          Отвечать на вопросы может рекрутёр или HR — у вашей роли нет этого права.
        </p>
      ) : null}
    </li>
  );
}

function ReplyForm({
  question,
  resolve,
}: {
  question: Question;
  resolve: ResolveMutation;
}) {
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const submitting = resolve.isPending && resolve.variables?.id === question.id;

  if (!open) {
    return (
      <div className="resolve">
        <button type="button" className="button button-primary" onClick={() => setOpen(true)}>
          Ответить в MAX
        </button>
      </div>
    );
  }

  return (
    <form
      className="resolve"
      onSubmit={(event) => {
        event.preventDefault();
        if (!text.trim()) return;
        resolve.mutate(
          { id: question.id, text },
          {
            onSuccess: () => {
              setText("");
              setOpen(false);
            },
          },
        );
      }}
    >
      <label htmlFor={`reply-${question.id}`} className="muted small">
        Ответ сотруднику. Он увидит его в MAX, вопрос закроется.
      </label>
      <textarea
        id={`reply-${question.id}`}
        value={text}
        rows={3}
        maxLength={2000}
        placeholder="Например: «ДМС начинает действовать с первого рабочего дня. Подробности пришлю в чат»."
        onChange={(event) => setText(event.target.value)}
      />
      <div className="resolve-actions">
        <button type="submit" className="button button-primary" disabled={submitting || !text.trim()}>
          {submitting ? "Отправляю…" : "Отправить"}
        </button>
        <button
          type="button"
          className="link-button"
          onClick={() => {
            setOpen(false);
            setText("");
          }}
        >
          Отмена
        </button>
        {resolve.error && resolve.variables?.id === question.id && resolve.error.name !== "Unauthorized" ? (
          <span className="error-text" role="alert">
            {resolve.error.message}
          </span>
        ) : null}
      </div>
    </form>
  );
}
