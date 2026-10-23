import { useQuery } from "@tanstack/react-query";

import { fetchDigest, fetchOverview } from "../api";
import { EmptyState, ErrorNote, SkeletonRows } from "../components/States";
import { useUnauthorized } from "../useUnauthorized";
import { formatDateTime } from "../format";

const TAG_LABELS: Record<string, string> = {
  access: "Доступы",
  manager: "Руководитель",
  team: "Команда",
  workload: "Нагрузка",
  adaptation: "Адаптация",
  it: "ИТ",
  documents: "Документы",
  motivation: "Мотивация",
  safety: "Безопасность",
  compensation: "Оплата",
};

export function RiskPage({ onUnauthorized }: { onUnauthorized: () => void }) {
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
        <div>
          <h1>Риски адаптации</h1>
          <p className="muted">
            Что модель услышала в ответах и что из этого требует человека. Окно — семь дней.
          </p>
        </div>
        <div className="page-count" aria-live="polite">
          {digest.isSuccess ? `${digest.data.items.length} сигналов` : "…"}
        </div>
      </header>

      {overview.isError ? (
        <ErrorNote
          message={overview.error.message}
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
              {TAG_LABELS[tag.tag] ?? tag.tag} · {tag.count}
            </span>
          ))}
        </p>
      ) : null}

      <h2 className="section-title">Дайджест недели</h2>
      {digest.isLoading ? <SkeletonRows rows={4} /> : null}
      {digest.isError ? (
        <ErrorNote message={digest.error.message} onRetry={() => void digest.refetch()} />
      ) : null}
      {digest.isSuccess && digest.data.items.length === 0 ? (
        <EmptyState title="Сигналов нет">
          Ни один ответ за неделю не поднял риск до среднего или высокого.
        </EmptyState>
      ) : null}
      {digest.isSuccess && digest.data.items.length > 0 ? (
        <ul className="digest">
          {digest.data.items.map((item) => (
            <li key={`${item.employee_id}-${item.step_id}-${item.at}`} className="digest-row">
              <div className="digest-main">
                <div className="digest-head">
                  <span className={`pill ${item.level === "high" ? "pill-warn" : "pill-muted"}`}>
                    {item.level === "high" ? "Высокий" : "Средний"}
                  </span>
                  <strong>{item.employee_name}</strong>
                  <span className="muted">{item.department}</span>
                </div>
                <p className="digest-reasons">{item.reasons.join("; ") || "без формулировки"}</p>
                <p className="digest-meta">
                  шаг {item.step_id} · {formatDateTime(item.at)}
                </p>
              </div>
              <div className="digest-tags">
                {item.tags.map((tag) => (
                  <span key={tag} className="tag">
                    {TAG_LABELS[tag] ?? tag}
                  </span>
                ))}
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
