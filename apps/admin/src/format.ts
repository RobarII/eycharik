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

/** A size a recruiter can judge: "842 КБ" is a photo, "12 МБ" is a scan. */
export function formatBytes(size: number): string {
  if (size < 1024) return `${size} Б`;
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} КБ`;
  return `${(size / (1024 * 1024)).toFixed(1).replace(".", ",")} МБ`;
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
  run_restarted: "Повторный старт",
  event_without_run: "Событие без сценария",
  webhook_without_sender: "Событие без отправителя",
  answer_skipped: "Ответ пропущен",
  action_ignored: "Действие пропущено",
  risk_assessed: "Оценка риска",
  risk_escalated: "Риск передан рекрутёру",
  sentiment_classified: "Настроение оценено",
  knowledge_ingested: "Документ проиндексирован",
};

/** Why a document cannot be downloaded, in the cabinet's words rather than a status code. */
export function fileStatusLabel(status: string): string {
  switch (status) {
    case "rejected":
      return "не принят";
    case "failed":
      return "не получен";
    case "unavailable":
      return "без файла";
    default:
      return status;
  }
}

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

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export const tagLabels: Record<string, string> = {
  access: "Доступы",
  manager: "Руководитель",
  colleagues: "Команда",
  workload: "Нагрузка",
  clarity: "Ясность задач",
  integration: "Адаптация",
  hr: "HR",
  it: "ИТ",
  other: "Другое",
};

export function tagLabel(tag: string): string {
  return tagLabels[tag] ?? tag;
}

export function plural(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

export function countLabel(
  n: number,
  one: string,
  few: string,
  many: string,
): string {
  return `${n} ${plural(n, one, few, many)}`;
}

export const stepLabels: Record<string, string> = {
  welcome: "Знакомство",
  documents_checklist: "Документы",
  day_before: "Готовность к первому дню",
  first_day: "Первый день",
  access_check: "Проверка доступов",
  access_help: "Проблема с доступами",
  territory_map: "Территория",
  lunch: "Обед",
  contacts: "Контакты",
  presentation: "О компании",
  first_day_end: "Итог первого дня",
  day_three_plan: "План адаптации",
  day_three_survey: "Опрос третьего дня",
  week_two_plan: "Вторая неделя",
  week_two_survey: "Опрос двух недель",
  month_two_plan: "Второй месяц",
  month_two_survey: "Опрос второго месяца",
  probation_reminder: "Испытательный срок",
  probation_survey: "Итоги испытательного срока",
  done: "Завершение",
};

export function stepLabel(step: string): string {
  return stepLabels[step] ?? step;
}

const RISK_LEVELS: Record<string, string> = {
  low: "низкий",
  medium: "средний",
  high: "высокий",
};

/**
 * One line of the run timeline: what happened, in the recruiter's words.
 *
 * Lives here rather than in the page because the rules are the interesting part — a step name is
 * translated, a risk event carries level, topics and reasons, a rejected answer says so — and they
 * deserve a test without mounting React.
 */
export function describeEvent(name: string, fields: Record<string, unknown>): string {
  const step = fieldText(fields["step"]);
  const previous = fieldText(fields["previous_step"]);
  const stepTitle = fieldText(fields["step_title"]);
  const current = stepTitle ?? (step ? stepLabel(step) : null);
  const reason = fieldText(fields["reason"]);
  const rawTags = fields["tags"];
  const tags = Array.isArray(rawTags)
    ? rawTags.map((tag) => tagLabel(String(tag))).join(", ")
    : fieldText(rawTags);
  const reasons = fieldText(fields["reasons"]);
  const level = fieldText(fields["level"]);

  const risk =
    name === "risk_assessed"
      ? [
          level ? `уровень: ${RISK_LEVELS[level] ?? level}` : null,
          tags ? `темы: ${tags}` : null,
          reasons,
        ]
      : [];

  return [
    step && previous ? `${stepLabel(previous)} → ${current ?? step}` : current,
    ...risk,
    reason ? reasonLabel(reason) : null,
    fieldText(fields["accepted"]) === "false" ? "не принят" : null,
  ]
    .filter((value): value is string => Boolean(value))
    .join(" · ");
}
