import { useInfiniteQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";

import { fetchRuns, type RunStatus } from "../api";
import { SearchIcon } from "../components/Icons";
import { Progress } from "../components/Progress";
import { StatusPill } from "../components/Pills";
import { EmptyState, ErrorNote, SkeletonRows } from "../components/States";
import { useUnauthorized } from "../useUnauthorized";
import { daysSince, formatDateTime, initials } from "../format";
import { REFRESH } from "../config";
import { setParam, useRoute } from "../route";
import type { RunSummary } from "../types";

const FILTERS: ReadonlyArray<readonly [RunStatus, string]> = [
  ["active", "В процессе"],
  ["completed", "Завершённые"],
  ["all", "Все"],
];

const SEARCH_DELAY_MS = 250;

function readStatus(value: string | null): RunStatus {
  return FILTERS.some(([status]) => status === value) ? (value as RunStatus) : "active";
}

export function RunsPage({
  onOpen,
  onUnauthorized,
}: {
  onOpen: (runId: string) => void;
  onUnauthorized: () => void;
}) {
  const { route, setParams } = useRoute();
  const status = readStatus(route.params.get("status"));
  const search = route.params.get("q") ?? "";
  const [draft, setDraft] = useState(search);

  // The address bar is the state, so an external change (a shared link) wins over the draft.
  useEffect(() => setDraft(search), [search]);

  const commitSearch = useCallback(
    (value: string) => setParams((params) => setParam(params, "q", value.trim())),
    [setParams],
  );

  useEffect(() => {
    if (draft.trim() === search) return;
    const timer = setTimeout(() => commitSearch(draft), SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [draft, search, commitSearch]);

  const query = useInfiniteQuery({
    queryKey: ["runs", status, search],
    queryFn: ({ pageParam }) =>
      fetchRuns({ status, q: search, cursor: pageParam, limit: 50 }),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
    refetchInterval: REFRESH.runs,
  });

  useUnauthorized(query.error, onUnauthorized);

  const items = query.data?.pages.flatMap((page) => page.items) ?? [];
  const total = query.data?.pages[0]?.total ?? 0;
  const filtered = status !== "all" || search.length > 0;

  function changeStatus(next: RunStatus) {
    setParams((params) => setParam(params, "status", next === "active" ? "" : next));
  }

  return (
    <section className="page">
      <header className="page-head">
        <div className="page-head-text">
          <p className="eyebrow">Когорта</p>
          <h1>Новые сотрудники</h1>
          <p className="muted">
            Сценарий, шаг и время входа. Прогресс считается по версии сценария, закреплённой за
            сотрудником.
          </p>
        </div>
        <div className="page-count" aria-live="polite">
          {query.isSuccess ? `${items.length} из ${total}` : "…"}
        </div>
      </header>

      <div className="toolbar">
        <div className="segmented" role="tablist" aria-label="Фильтр по статусу">
          {FILTERS.map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={status === value}
              className={status === value ? "segment segment-on" : "segment"}
              onClick={() => changeStatus(value)}
            >
              {label}
            </button>
          ))}
        </div>
        <label className="search">
          <span className="visually-hidden">Поиск по сотрудникам</span>
          <SearchIcon className="search-icon" width={16} height={16} />
          <input
            type="search"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Имя, роль, подразделение"
          />
        </label>
      </div>

      {query.isPending ? <SkeletonRows /> : null}
      {query.isError && query.error.name !== "Unauthorized" ? (
        <ErrorNote message={query.error.message} onRetry={() => void query.refetch()} />
      ) : null}
      {query.isSuccess && items.length === 0 ? (
        filtered ? (
          <EmptyState title="Ничего не найдено">
            По этому фильтру сотрудников нет. Сбросьте поиск или выберите другой статус.
          </EmptyState>
        ) : (
          <EmptyState title="Пока никого нет">
            Сотрудник появится здесь, когда напишет боту в MAX и начнёт онбординг.
          </EmptyState>
        )
      ) : null}

      {items.length > 0 ? (
        <ul className="run-list">
          {items.map((run) => (
            <RunCard key={run.run_id} run={run} onOpen={onOpen} />
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

function RunCard({ run, onOpen }: { run: RunSummary; onOpen: (id: string) => void }) {
  return (
    <li>
      <button type="button" className="run-card" onClick={() => onOpen(run.run_id)}>
        <span className="avatar" aria-hidden="true">
          {initials(run.name)}
        </span>
        <span className="run-main">
          <span className="run-title">
            <strong>{run.name}</strong>
            <StatusPill status={run.status} />
          </span>
          <span className="run-meta">
            {run.role} · {run.department}
          </span>
          <span className="run-progress">
            <Progress
              step={run.step_number}
              total={run.steps_total}
              completed={run.status === "completed"}
            />
          </span>
        </span>
        <span className="run-side">
          <span className="run-step">Шаг: {run.step_title ?? run.step_id}</span>
          <span className="run-time" title={`В сценарии с ${formatDateTime(run.entered_at)}`}>
            {daysSince(run.entered_at)} в сценарии
          </span>
          <span className="chevron" aria-hidden="true">
            →
          </span>
        </span>
      </button>
    </li>
  );
}
