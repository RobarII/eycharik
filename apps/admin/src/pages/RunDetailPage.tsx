import { useQuery } from "@tanstack/react-query";

import { fetchRun } from "../api";
import { ArrowLeftIcon } from "../components/Icons";
import { StatusPill } from "../components/Pills";
import { Progress } from "../components/Progress";
import { ErrorNote, SkeletonRows } from "../components/States";
import {
  countLabel,
  eventLabel,
  fieldText,
  formatDate,
  formatDateTime,
  initials,
  reasonLabel,
  stepLabel,
  tagLabel,
} from "../format";
import { useUnauthorized } from "../useUnauthorized";
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
        <ErrorNote message={query.error.message} onRetry={() => void query.refetch()} />
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
            <StatusPill status={query.data.status} />
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
                  const step = fieldText(event.fields["step"]);
                  const previous = fieldText(event.fields["previous_step"]);
                  const stepTitle = fieldText(event.fields["step_title"]);
                  const current = stepTitle ?? (step ? stepLabel(step) : null);
                  const reason = fieldText(event.fields["reason"]);
                  const rawTags = event.fields["tags"];
                  const tags = Array.isArray(rawTags)
                    ? rawTags.map((tag) => tagLabel(String(tag))).join(", ")
                    : fieldText(rawTags);
                  const reasons = fieldText(event.fields["reasons"]);
                  const level = fieldText(event.fields["level"]);
                  const risk =
                    event.name === "risk_assessed"
                      ? [
                          level
                            ? `уровень: ${
                                level === "high"
                                  ? "высокий"
                                  : level === "medium"
                                    ? "средний"
                                    : level
                              }`
                            : null,
                          tags ? `темы: ${tags}` : null,
                          reasons,
                        ].filter((value): value is string => Boolean(value))
                      : [];
                  const details = [
                    step && previous
                      ? `${stepLabel(previous)} → ${current ?? step}`
                      : current,
                    ...risk,
                    reason ? reasonLabel(reason) : null,
                    fieldText(event.fields["accepted"]) === "false" ? "не принят" : null,
                  ].filter((value): value is string => Boolean(value));
                  return (
                    <li key={`${event.at}-${event.name}-${index}`}>
                      <time dateTime={event.at}>{formatDateTime(event.at)}</time>
                      <div>
                        <p className="timeline-name">{eventLabel(event.name)}</p>
                        {details.length > 0 ? (
                          <p className="timeline-detail">{details.join(" · ")}</p>
                        ) : null}
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
