export function Progress({
  step,
  total,
  completed,
}: {
  step: number;
  total: number;
  completed: boolean;
}) {
  const safeTotal = Math.max(total, 1);
  const current = completed ? safeTotal : Math.min(Math.max(step, 0), safeTotal);
  return (
    <div className="progress" aria-label={`Шаг ${current} из ${safeTotal}`}>
      <div className="progress-track">
        <div
          className={`progress-fill${completed ? " progress-fill-done" : ""}`}
          style={{ width: `${(current / safeTotal) * 100}%` }}
        />
      </div>
      <span className="progress-label">
        {completed ? `${safeTotal} из ${safeTotal}` : `${current} из ${safeTotal}`}
      </span>
    </div>
  );
}
