import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { fetchRuns } from "../api";
import { SearchIcon } from "../components/Icons";
import { Progress } from "../components/Progress";
import { StatusPill } from "../components/Pills";
import { EmptyState, ErrorNote, SkeletonRows } from "../components/States";
import { useUnauthorized } from "../useUnauthorized";
import { daysSince, formatDateTime, initials } from "../format";
import type { RunSummary } from "../types";

type Filter = "active" | "completed" | "all";

export function RunsPage({
  onOpen,
  onUnauthorized,
}: {
  onOpen: (runId: string) => void;
  onUnauthorized: () => void;
}) {
  const [filter, setFilter] = useState<Filter>("active");
  const [search, setSearch] = useState("");
  const query = useQuery({
    queryKey: ["runs"],
    queryFn: () => fetchRuns(),
    refetchInterval: 15_000,
  });

  useUnauthorized(query.error, onUnauthorized);

  const items = useMemo(() => {
    const all = query.data?.items ?? [];
    const term = search.trim().toLowerCase();
    return all.filter((run) => {
      const matchesFilter = filter === "all" || run.status === filter;
      const matchesSearch =
        !term ||
        [run.name, run.role, run.department, run.employee_id]
          .join(" ")
          .toLowerCase()
          .includes(term);
      return matchesFilter && matchesSearch;
    });
  }, [query.data, filter, search]);

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
          {query.isSuccess ? `${items.length} в выборке` : "…"}
        </div>
      </header>

      <div className="toolbar">
        <div className="segmented" role="tablist" aria-label="Фильтр по статусу">
          {(
            [
              ["active", "В процессе"],
              ["completed", "Завершённые"],
              ["all", "Все"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={filter === value}
              className={filter === value ? "segment segment-on" : "segment"}
              onClick={() => setFilter(value)}
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
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Имя, роль, подразделение"
          />
        </label>
      </div>

      {query.isPending ? <SkeletonRows /> : null}
      {query.isError && query.error.name !== "Unauthorized" ? (
        <ErrorNote message={query.error.message} onRetry={() => void query.refetch()} />
      ) : null}
      {query.isSuccess && items.length === 0 ? (
        <EmptyState title="Пока никого нет">
          Сотрудник появится здесь, когда напишет боту в MAX и начнёт онбординг.
        </EmptyState>
      ) : null}

      {items.length > 0 ? (
        <ul className="run-list">
          {items.map((run) => (
            <RunCard key={run.run_id} run={run} onOpen={onOpen} />
          ))}
        </ul>
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
          <span className="run-time" title={formatDateTime(run.entered_at)}>
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
