const dateTime = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

const dateOnly = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "long",
  year: "numeric",
});

export function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : dateTime.format(date);
}

export function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : dateOnly.format(date);
}

export function daysSince(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  const days = Math.max(0, Math.floor((Date.now() - date.getTime()) / 86_400_000));
  if (days === 0) return "сегодня";
  if (days === 1) return "1 день";
  return `${days} дн.`;
}

export const reasonLabels: Record<string, string> = {
  no_sources: "Нет источника",
  low_confidence: "Низкая уверенность",
  restricted: "Ограниченный доступ",
  out_of_scope: "Вне компетенции",
  timeout: "Нет ответа",
  manual: "Нужен человек",
  unavailable: "Модель недоступна",
  answered: "Ответ получен",
};

export const eventLabels: Record<string, string> = {
  run_started: "Онбординг начался",
  step_transition: "Переход по шагам",
  escalation_requested: "Передано рекрутеру",
  run_completed: "Онбординг завершён",
  answer_completed: "Ответ сформирован",
  answer_rejected: "Ответ отклонён",
  answer_unavailable: "Модель недоступна",
  run_already_active: "Повторный старт",
  event_without_run: "Событие без сценария",
  webhook_without_sender: "Событие без отправителя",
  answer_skipped: "Ответ пропущен",
  action_ignored: "Действие пропущено",
};

export function reasonLabel(reason: string): string {
  return reasonLabels[reason] ?? reason;
}

export function eventLabel(name: string): string {
  return eventLabels[name] ?? name;
}

export function fieldText(value: unknown): string | null {
  if (value === null || value === undefined || value === "") return null;
  if (Array.isArray(value)) return value.map(String).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
