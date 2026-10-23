import { ApiError, Unauthorized } from "./api";

/**
 * One place where a failure becomes Russian.
 *
 * The API speaks English on purpose (workspace rule), so a status code decides the sentence and the
 * server's `detail` is only appended where it names a field the user can fix. Nothing here echoes a
 * token: the server never puts one in a message.
 */
const BY_STATUS: Record<number, string> = {
  400: "Сервер не принял запрос. Обновите страницу.",
  403: "Недостаточно прав для этого действия.",
  404: "Не найдено: запись могла быть удалена или закрыта.",
  409: "Запись уже изменилась в другом окне. Показываю актуальные данные.",
  413: "Файл больше допустимого размера.",
  415: "Формат не поддерживается. Нужен PDF или PPTX.",
  429: "Слишком много попыток. Подождите минуту.",
};

const VALIDATION = /^(upload|doc|frontmatter)[:.]/i;

export function errorText(error: Error): string {
  if (error instanceof Unauthorized) return "Доступ истёк. Войдите снова.";
  if (error instanceof ApiError) {
    if (error.status === 422 && VALIDATION.test(error.message)) {
      return `Документ не прошёл проверку схемы. ${error.message}`;
    }
    if (error.status === 422) return `Сервер отклонил данные: ${error.message}`;
    const known = BY_STATUS[error.status];
    if (known) return known;
    if (error.status >= 500) return "Сервер ошибся. Повторите через минуту.";
    return error.message;
  }
  // `fetch` rejects with a TypeError when the request never reached the server.
  if (error instanceof TypeError) return "Сервер не отвечает. Проверьте соединение.";
  return error.message;
}

/** A conflict needs a refetch, not just a message: something changed under our feet. */
export function isConflict(error: Error): boolean {
  return error instanceof ApiError && error.status === 409;
}

export function isForbidden(error: Error): boolean {
  return error instanceof ApiError && error.status === 403;
}
