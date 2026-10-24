import { reasonLabel } from "../format";

export function StatusPill({ status }: { status: "active" | "completed" }) {
  return (
    <span className={`pill ${status === "active" ? "pill-active" : "pill-done"}`}>
      {status === "active" ? "В процессе" : "Завершён"}
    </span>
  );
}

export function AnswerPill({
  answered,
  declined = false,
}: {
  answered: boolean;
  declined?: boolean;
}) {
  if (declined) {
    return <span className="pill pill-muted">Отклонён</span>;
  }
  return (
    <span className={`pill ${answered ? "pill-done" : "pill-warn"}`}>
      {answered ? "Отвечен" : "Ждёт ответа"}
    </span>
  );
}

export function ReasonPill({ reason }: { reason: string }) {
  return <span className="pill pill-muted">{reasonLabel(reason)}</span>;
}
