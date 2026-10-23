import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { fetchRun, offboardEmployee } from "../api";
import { ArrowLeftIcon } from "../components/Icons";
import { StatusPill } from "../components/Pills";
import { Progress } from "../components/Progress";
import { ErrorNote, SkeletonRows } from "../components/States";
import {
  countLabel,
  describeEvent,
  eventLabel,
  formatDate,
  formatDateTime,
  initials,
  reasonLabel,
} from "../format";
import { useUnauthorized } from "../useUnauthorized";
import { useSession } from "../session";
import { SCENARIO_LABELS } from "../config";

export function RunDetailPage({
  runId,
  onBack,
  onUnauthorized,
}: {
  runId: string;
  onBack: () => void;
  onUnauthorized: () => void;
}) {
  const queryClient = useQueryClient();
  const { can } = useSession();
  const query = useQuery({
    queryKey: ["run", runId],
    queryFn: () => fetchRun(runId),
    refetchInterval: 15_000,
  });
  useUnauthorized(query.error, onUnauthorized);

  return (
    <section className="page">
      <button type="button" className="back" onClick={onBack}>
        <ArrowLeftIcon width={16} height={16} />
        Все сотрудники
      </button>

      {query.isPending ? <SkeletonRows rows={4} /> : null}
      {query.isError && query.error.name !== "Unauthorized" ? (
        <ErrorNote error={query.error} onRetry={() => void query.refetch()} />
      ) : null}

      {query.data ? (
        <>
          <header className="detail-head">
            <div className="detail-identity">
              <span className="avatar avatar-lg" aria-hidden="true">
                {initials(query.data.name)}
              </span>
              <div>
                <h1>{query.data.name}</h1>
                <p className="muted">
                  {query.data.role} · {query.data.department}
                </p>
              </div>
            </div>
            <div className="detail-actions">
              <StatusPill status={query.data.status} />
              {can("employees.offboard") && query.data.status !== "completed" ? (
                <OffboardButton
                  employeeId={query.data.employee_id}
                  name={query.data.name}
                  onDone={() => {
                    void queryClient.invalidateQueries({ queryKey: ["runs"] });
                    void queryClient.invalidateQueries({ queryKey: ["questions"] });
                  }}
                  onUnauthorized={onUnauthorized}
                  onBack={onBack}
                />
              ) : null}
            </div>
          </header>

          <div className="detail-grid">
            <section className="card">
              <h2>Прогресс</h2>
              <Progress
                step={query.data.step_number}
                total={query.data.steps_total}
                completed={query.data.status === "completed"}
              />
              <dl className="facts">
                <div>
                  <dt>Текущий шаг</dt>
                  <dd>{query.data.step_title ?? query.data.step_id}</dd>
                </div>
                <div>
                  <dt>Сценарий</dt>
                  <dd>
                    {SCENARIO_LABELS[query.data.scenario] ?? query.data.scenario} · v
                    {query.data.scenario_version}
                  </dd>
                </div>
                <div>
                  <dt>В сценарии с</dt>
                  <dd>{formatDate(query.data.entered_at)}</dd>
                </div>
                <div>
                  <dt>Обращение</dt>
                  <dd>{query.data.tone === "informal" ? "На «ты»" : "На «вы»"}</dd>
                </div>
                <div>
                  <dt>Сотрудник в MAX</dt>
                  <dd>{query.data.employee_id}</dd>
                </div>
              </dl>
              {query.data.step_message ? (
                <blockquote className="step-message">{query.data.step_message}</blockquote>
              ) : null}
            </section>

            <section className="card">
              <div className="card-head">
                <h2>Что спрашивал</h2>
                <span className="card-note">
                  {countLabel(query.data.questions.length, "вопрос", "вопроса", "вопросов")}
                </span>
              </div>
              {query.data.questions.length === 0 ? (
                <p className="muted">Вопросов пока не было.</p>
              ) : (
                <ul className="question-list">
                  {query.data.questions.map((question) => (
                    <li key={`${question.asked_at}-${question.text}`}>
                      <p className="question-text">{question.text}</p>
                      <p className="question-meta">
                        <span
                          className={`pill ${question.answered ? "pill-done" : "pill-warn"}`}
                        >
                          {question.answered ? "Отвечен" : reasonLabel(question.reason)}
                        </span>
                        <time dateTime={question.asked_at}>
                          {formatDateTime(question.asked_at)}
                        </time>
                      </p>
                      {question.citations.length > 0 ? (
                        <p className="citations">
                          {question.citations.map((citation) => (
                            <code key={citation}>{citation}</code>
                          ))}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <section className="card">
            <div className="card-head">
              <h2>Хронология</h2>
              <span className="card-note">
                {countLabel(query.data.events.length, "событие", "события", "событий")}
              </span>
            </div>
            {query.data.events.length === 0 ? (
              <p className="muted">Событий пока нет.</p>
            ) : (
              <ol className="timeline">
                {query.data.events.map((event, index) => {
                  const details = describeEvent(event.name, event.fields);
                  return (
                    <li key={`${event.at}-${event.name}-${index}`}>
                      <time dateTime={event.at}>{formatDateTime(event.at)}</time>
                      <div>
                        <p className="timeline-name">{eventLabel(event.name)}</p>
                        {details ? <p className="timeline-detail">{details}</p> : null}
                      </div>
                    </li>
                  );
                })}
              </ol>
            )}
          </section>
        </>
      ) : null}
    </section>
  );
}

/**
 * Ending an onboarding is destructive and irreversible: it deletes the transcript.
 *
 * So the button does not act on the first click. It opens the consequences — what is deleted, what
 * survives in the audit — and waits for a second, deliberate press.
 */
function OffboardButton({
  employeeId,
  name,
  onDone,
  onUnauthorized,
  onBack,
}: {
  employeeId: string;
  name: string;
  onDone: () => void;
  onUnauthorized: () => void;
  onBack: () => void;
}) {
  const [armed, setArmed] = useState(false);
  const mutation = useMutation({
    mutationFn: () => offboardEmployee(employeeId),
    onSuccess: onDone,
  });

  useUnauthorized(mutation.error, onUnauthorized);

  if (mutation.isSuccess) {
    const { questions_deleted: questions, messages_deleted: messages } = mutation.data;
    return (
      <div className="note note-ok" role="status">
        <p>
          {name} офборджен: удалено {countLabel(questions, "вопрос", "вопроса", "вопросов")},{" "}
          {countLabel(messages, "сообщение", "сообщения", "сообщений")}.
        </p>
        <button type="button" className="link-button" onClick={onBack}>
          К списку сотрудников
        </button>
      </div>
    );
  }

  if (!armed) {
    return (
      <button type="button" className="button button-quiet" onClick={() => setArmed(true)}>
        Офбордить
      </button>
    );
  }

  return (
    <div className="confirm">
      <p className="confirm-text">
        Переписка {name} будет удалена сразу, сценарий закрыт. В аудите останутся только факты
        удаления. Отменить это нельзя.
      </p>
      <div className="confirm-actions">
        <button
          type="button"
          className="button button-danger"
          disabled={mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {mutation.isPending ? "Удаляем…" : "Да, офбордить"}
        </button>
        <button type="button" className="button button-quiet" onClick={() => setArmed(false)}>
          Отмена
        </button>
      </div>
      {mutation.isError ? <ErrorNote error={mutation.error} /> : null}
    </div>
  );
}
