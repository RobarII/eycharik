import { useQuery } from "@tanstack/react-query";
import { useMemo, type ReactNode } from "react";

import { fetchDigest, fetchOverview, fetchQuestions, fetchRuns } from "../api";
import { REFRESH } from "../config";
import {
  ArrowUpRightIcon,
  ChatIcon,
  CheckIcon,
  RiskIcon,
  UsersIcon,
} from "../components/Icons";
import { StatusPill } from "../components/Pills";
import { ErrorNote } from "../components/States";
import {
  countLabel,
  daysSince,
  formatDateTime,
  initials,
  reasonLabel,
  tagLabel,
} from "../format";
import { useUnauthorized } from "../useUnauthorized";
import type { RunSummary } from "../types";

interface BarItem {
  id: string;
  label: string;
  value: number;
}

export function OverviewPage({
  onOpenRun,
  onNavigate,
  onUnauthorized,
}: {
  onOpenRun: (runId: string) => void;
  onNavigate: (path: string) => void;
  onUnauthorized: () => void;
}) {
  const overview = useQuery({
    queryKey: ["overview"],
    queryFn: fetchOverview,
    refetchInterval: REFRESH.overview,
  });
  const runs = useQuery({
    queryKey: ["runs", "cohort"],
    queryFn: () => fetchRuns({ status: "active", limit: 200 }),
    refetchInterval: REFRESH.runs,
  });
  const questions = useQuery({
    queryKey: ["questions", "unanswered", "overview"],
    queryFn: () => fetchQuestions({ status: "unanswered", limit: 4 }),
    refetchInterval: REFRESH.questions,
  });
  const digest = useQuery({
    queryKey: ["digest"],
    queryFn: () => fetchDigest(7),
    refetchInterval: REFRESH.digest,
  });

  const failure = overview.error ?? runs.error ?? digest.error ?? questions.error;
  useUnauthorized(failure, onUnauthorized);

  const steps = useMemo<BarItem[]>(() => {
    const map = new Map<string, { number: number; label: string; value: number }>();
    for (const run of runs.data?.items ?? []) {
      const existing = map.get(run.step_id);
      if (existing) existing.value += 1;
      else
        map.set(run.step_id, {
          number: run.step_number,
          label: run.step_title ?? run.step_id,
          value: 1,
        });
    }
    return [...map.entries()]
      .sort((a, b) => a[1].number - b[1].number)
      .map(([id, item]) => ({ id, label: item.label, value: item.value }));
  }, [runs.data]);

  const recent = useMemo(
    () =>
      [...(runs.data?.items ?? [])]
        .sort((a, b) => Date.parse(b.entered_at) - Date.parse(a.entered_at))
        .slice(0, 5),
    [runs.data],
  );

  function retry() {
    void overview.refetch();
    void runs.refetch();
    void questions.refetch();
    void digest.refetch();
  }

  return (
    <section className="page">
      <header className="page-head">
        <div className="page-head-text">
          <p className="eyebrow">Онбординг · срез на сейчас</p>
          <h1>Обзор онбординга</h1>
          <p className="muted">
            Где когорта сейчас, какие темы поднимаются в опросах и что ждёт ответа рекрутёра.
            Риски и темы считаются за последние семь дней — это подписано у каждой карточки.
          </p>
        </div>
        <div className="page-count" aria-live="polite">
          {runs.isSuccess
            ? countLabel(runs.data.total, "сотрудник", "сотрудника", "сотрудников")
            : "…"}
        </div>
      </header>

      {failure && failure.name !== "Unauthorized" ? (
        <ErrorNote error={failure} onRetry={retry} />
      ) : null}

      <div className="kpi-grid">
        <Kpi
          label="В процессе"
          value={overview.data?.active_runs}
          foot="Прямо сейчас, без окна"
          icon={<UsersIcon width={17} height={17} />}
        />
        <Kpi
          label="Завершили"
          value={overview.data?.completed_runs}
          foot="Прямо сейчас, без окна"
          icon={<CheckIcon width={17} height={17} />}
        />
        <Kpi
          label="Высокий риск"
          value={overview.data?.high_risk}
          foot={`${countLabel(
            overview.data?.medium_risk ?? 0,
            "средний риск",
            "средних риска",
            "средних рисков",
          )} за семь дней`}
          tone="warn"
          icon={<RiskIcon width={17} height={17} />}
        />
        <Kpi
          label="Ждут ответа"
          value={overview.data?.unanswered_questions}
          foot="Прямо сейчас, без окна"
          icon={<ChatIcon width={17} height={17} />}
        />
      </div>

      <div className="dash-grid">
        <section className="card card-fill">
          <div className="card-head">
            <h2>Этапы когорты</h2>
            <span className="card-note">Текущий шаг, все активные</span>
          </div>
          <CohortProgress runs={runs.data?.items ?? []} />
          {runs.isPending ? (
            <p className="empty-inline">Загружаем сотрудников…</p>
          ) : (
            <BarList items={steps} empty="Пока никого нет в сценарии." />
          )}
          <p className="card-foot">
            Прогресс считается по версии сценария, закреплённой за сотрудником, а не по ответам
            модели.
          </p>
        </section>

        <section className="card">
          <div className="card-head">
            <h2>Требуют внимания</h2>
            <button type="button" className="link-button" onClick={() => onNavigate("risk")}>
              Все риски
              <ArrowUpRightIcon width={13} height={13} />
            </button>
          </div>
          {digest.isPending ? <p className="empty-inline">Загружаем сигналы…</p> : null}
          {digest.isError ? <p className="empty-inline">Не удалось загрузить сигналы.</p> : null}
          {digest.isSuccess && digest.data.items.length === 0 ? (
            <p className="empty-inline">За семь дней нет средних и высоких рисков.</p>
          ) : null}
          {digest.isSuccess && digest.data.items.length > 0 ? (
            <ul className="attention-list">
              {digest.data.items.slice(0, 3).map((item) => (
                <li className="attention" key={`${item.employee_id}-${item.step_id}-${item.at}`}>
                  <div className="attention-head">
                    <span className={`pill ${item.level === "high" ? "pill-warn" : "pill-muted"}`}>
                      {item.level === "high" ? "Высокий" : "Средний"}
                    </span>
                    <span className="attention-name">{item.employee_name}</span>
                  </div>
                  <p className="attention-quote">
                    {item.quote ? `«${item.quote}»` : item.reasons.join("; ") || "Без формулировки"}
                  </p>
                  <p className="attention-meta">
                    {item.step_title} · {formatDateTime(item.at)}
                  </p>
                  {item.run_id ? (
                    <button
                      type="button"
                      className="link-button attention-link"
                      onClick={() => onOpenRun(item.run_id)}
                    >
                      Открыть карточку
                      <ArrowUpRightIcon width={13} height={13} />
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      </div>

      <div className="dash-grid">
        <section className="card card-fill">
          <div className="card-head">
            <h2>Вопросы без ответа</h2>
            <button type="button" className="link-button" onClick={() => onNavigate("questions")}>
              Вся очередь
              <ArrowUpRightIcon width={13} height={13} />
            </button>
          </div>
          {questions.isPending ? <p className="empty-inline">Загружаем очередь…</p> : null}
          {questions.isError ? (
            <p className="empty-inline">Не удалось загрузить вопросы.</p>
          ) : null}
          {questions.isSuccess && questions.data.items.length === 0 ? (
            <p className="empty-inline">Очередь пуста: ассистент закрывает вопросы сам.</p>
          ) : null}
          {questions.isSuccess && questions.data.items.length > 0 ? (
            <ul className="activity">
              {questions.data.items.map((question) => (
                <li
                  className="activity-row"
                  key={`${question.asked_at}-${question.employee_id}-${question.text}`}
                >
                  <span className="activity-avatar" aria-hidden="true">
                    {initials(question.employee_name)}
                  </span>
                  <span className="activity-main">
                    <span className="activity-name">
                      {question.employee_name}
                      <span className="pill pill-muted">{reasonLabel(question.reason)}</span>
                    </span>
                    <span className="activity-sub" title={question.text}>
                      {question.text}
                    </span>
                  </span>
                  <time className="activity-time" dateTime={question.asked_at}>
                    {formatDateTime(question.asked_at)}
                  </time>
                </li>
              ))}
            </ul>
          ) : null}
          <p className="card-foot">
            В очередь попадают вопросы без источника, с закрытым документом или низкой
            уверенностью модели.
          </p>
        </section>

        <section className="card">
          <div className="card-head">
            <h2>Темы недели</h2>
            <span className="card-note">По сигналам риска</span>
          </div>
          {overview.isPending ? <p className="empty-inline">Считаем темы…</p> : null}
          {overview.isError ? <p className="empty-inline">Не удалось загрузить темы.</p> : null}
          {overview.isSuccess && overview.data.top_tags.length === 0 ? (
            <p className="empty-inline">За семь дней темы не зафиксированы.</p>
          ) : null}
          {overview.isSuccess && overview.data.top_tags.length > 0 ? (
            <ul className="topic-list">
              {overview.data.top_tags.map((tag) => (
                <li key={tag.tag} className="topic-row">
                  <span>{tagLabel(tag.tag)}</span>
                  <span className="topic-count">{tag.count}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      </div>

      <section className="card">
        <div className="card-head">
          <h2>Новые сотрудники</h2>
          <button type="button" className="link-button" onClick={() => onNavigate("runs")}>
            Все сотрудники
            <ArrowUpRightIcon width={13} height={13} />
          </button>
        </div>
        {runs.isPending ? <p className="empty-inline">Загружаем сотрудников…</p> : null}
        {runs.isError ? <p className="empty-inline">Не удалось загрузить сотрудников.</p> : null}
        {runs.isSuccess && recent.length === 0 ? (
          <p className="empty-inline">
            Сотрудник появится здесь, когда напишет боту в MAX и начнёт онбординг.
          </p>
        ) : null}
        {recent.length > 0 ? (
          <ul className="activity">
            {recent.map((run) => (
              <li key={run.run_id}>
                <button
                  type="button"
                  className="activity-row activity-button"
                  onClick={() => onOpenRun(run.run_id)}
                >
                  <span className="activity-avatar" aria-hidden="true">
                    {initials(run.name)}
                  </span>
                  <span className="activity-main">
                    <span className="activity-name">
                      {run.name}
                      <StatusPill status={run.status} />
                    </span>
                    <span className="activity-sub">
                      {run.role} · {run.department} · {run.step_title ?? run.step_id}
                    </span>
                  </span>
                  <span
                    className="activity-time"
                    title={`В сценарии с ${formatDateTime(run.entered_at)}`}
                  >
                    {daysSince(run.entered_at)}
                  </span>
                  <span className="chevron" aria-hidden="true">
                    →
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </section>
  );
}

function BarList({ items, empty }: { items: BarItem[]; empty: string }) {
  if (items.length === 0) return <p className="empty-inline">{empty}</p>;
  const max = Math.max(...items.map((item) => item.value), 1);
  return (
    <ul className="bars">
      {items.map((item) => (
        <li className="bar-row" key={item.id}>
          <span className="bar-label" title={item.label}>
            {item.label}
          </span>
          <span className="bar-track" aria-hidden="true">
            <span
              className="bar-fill"
              style={{ width: `${Math.max(6, (item.value / max) * 100)}%` }}
            />
          </span>
          <span className="bar-value">{item.value}</span>
        </li>
      ))}
    </ul>
  );
}

function Kpi({
  label,
  value,
  foot,
  icon,
  tone,
}: {
  label: string;
  value: number | undefined;
  foot: string;
  icon: ReactNode;
  tone?: "warn";
}) {
  return (
    <div className={tone === "warn" ? "kpi kpi-warn" : "kpi"}>
      <div className="kpi-top">
        <span className="kpi-label">{label}</span>
        <span className="kpi-icon">{icon}</span>
      </div>
      <span className="kpi-value">{value ?? "—"}</span>
      <span className="kpi-foot">{foot}</span>
    </div>
  );
}

function CohortProgress({ runs }: { runs: RunSummary[] }) {
  if (runs.length === 0) return null;
  const total = Math.max(...runs.map((run) => run.steps_total), 1);
  const average = Math.round(
    runs.reduce((sum, run) => sum + Math.min(run.step_number, total), 0) / runs.length,
  );
  const percent = Math.round((average / total) * 100);
  return (
    <div
      className="cohort"
      role="group"
      aria-label={`Средний прогресс когорты: ${percent}%`}
    >
      <div className="cohort-head">
        <span className="cohort-label">Средний прогресс когорты</span>
        <strong className="cohort-value">{percent}%</strong>
      </div>
      <div className="cohort-track" aria-hidden="true">
        {Array.from({ length: total }, (_, index) => (
          <span
            key={index}
            className={index < average ? "cohort-tick cohort-tick-on" : "cohort-tick"}
          />
        ))}
      </div>
      <div className="cohort-foot">
        <span>Старт</span>
        <span>
          {average} из {total} шагов
        </span>
        <span>Финиш</span>
      </div>
    </div>
  );
}
