import { useQuery } from "@tanstack/react-query";

import { fetchDigest, fetchOverview } from "../api";
import { EmptyState, ErrorNote, SkeletonRows } from "../components/States";
import { useUnauthorized } from "../useUnauthorized";
import { formatDateTime, tagLabel, countLabel } from "../format";

export function RiskPage({
  onOpenRun,
  onUnauthorized,
}: {
  onOpenRun: (runId: string) => void;
  onUnauthorized: () => void;
}) {
  const overview = useQuery({
    queryKey: ["overview"],
    queryFn: () => fetchOverview(),
    refetchInterval: 30_000,
  });
  const digest = useQuery({
    queryKey: ["digest"],
    queryFn: () => fetchDigest(7),
    refetchInterval: 30_000,
  });

  useUnauthorized(overview.error ?? digest.error, onUnauthorized);

  return (
    <section className="page">
      <header className="page-head">
        <div className="page-head-text">
          <p className="eyebrow">Риск-радар</p>
          <h1>Риски адаптации</h1>
          <p className="muted">
            Что модель услышала в ответах и что из этого требует человека. Окно — семь дней.
          </p>
        </div>
        <div className="page-count" aria-live="polite">
          {digest.isSuccess
            ? countLabel(digest.data.items.length, "сигнал", "сигнала", "сигналов")
            : "…"}
        </div>
      </header>

      {overview.isError ? (
        <ErrorNote
          error={overview.error}
          onRetry={() => void overview.refetch()}
        />
      ) : null}

      <div className="stat-grid">
        <Stat label="В процессе" value={overview.data?.active_runs} />
        <Stat label="Завершили" value={overview.data?.completed_runs} />
        <Stat label="Высокий риск" value={overview.data?.high_risk} tone="warn" />
        <Stat label="Средний риск" value={overview.data?.medium_risk} />
        <Stat label="Ждут ответа" value={overview.data?.unanswered_questions} />
      </div>

      {overview.isSuccess && overview.data.top_tags.length > 0 ? (
        <p className="tag-row">
          <span className="muted">Частые темы:</span>
          {overview.data.top_tags.map((tag) => (
            <span key={tag.tag} className="tag">
              {tagLabel(tag.tag)} · {tag.count}
            </span>
          ))}
        </p>
      ) : null}

      <h2 className="section-title">Дайджест недели</h2>
      {digest.isLoading ? <SkeletonRows rows={4} /> : null}
      {digest.isError ? (
        <ErrorNote error={digest.error} onRetry={() => void digest.refetch()} />
      ) : null}
      {digest.isSuccess && digest.data.items.length === 0 ? (
        <EmptyState title="Сигналов нет">
          Ни один ответ за неделю не поднял риск до среднего или высокого.
        </EmptyState>
      ) : null}
      {digest.isSuccess && digest.data.items.length > 0 ? (
        <ul className="digest">
          {digest.data.items.map((item) => (
            <li
              key={`${item.employee_id}-${item.step_id}-${item.at}`}
              className={item.level === "high" ? "digest-row digest-row-high" : "digest-row"}
            >
              <div className="digest-main">
                <div className="digest-head">
                  <span className={`pill ${item.level === "high" ? "pill-warn" : "pill-muted"}`}>
                    {item.level === "high" ? "Высокий" : "Средний"}
                  </span>
                  <strong>{item.employee_name}</strong>
                  <span className="muted">{item.department}</span>
                </div>
                {item.quote ? <p className="digest-quote">«{item.quote}»</p> : null}
                <p className="digest-reasons">{item.reasons.join("; ") || "без формулировки"}</p>
                <p className="digest-meta">
                  {item.step_title} · {formatDateTime(item.at)}
                </p>
              </div>
              <div className="digest-tags">
                {item.tags.map((tag) => (
                  <span key={tag} className="tag">
                    {tagLabel(tag)}
                  </span>
                ))}
                {item.run_id ? (
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => onOpenRun(item.run_id)}
                  >
                    Открыть
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | undefined;
  tone?: "warn";
}) {
  return (
    <div className={tone === "warn" && value ? "stat stat-warn" : "stat"}>
      <span className="stat-value">{value ?? "…"}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}
