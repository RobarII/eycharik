import { useState, type FormEvent } from "react";

import { CheckIcon, LogoMark } from "./Icons";

const POINTS = [
  "Прогресс каждого новичка по сценарию, а не по логам чата.",
  "Риски из опросов с цитатой и тегами — до того, как человек уйдёт.",
  "Очередь вопросов, где ассистент честно передал диалог человеку.",
];

export function TokenGate({
  onSubmit,
}: {
  onSubmit: (token: string) => Promise<void>;
}) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!value.trim()) {
      setError("Введите токен доступа");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onSubmit(value.trim());
    } catch {
      setError("Токен не подошёл. Проверьте его у администратора.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="gate">
      <section className="gate-card">
        <div className="gate-brand">
          <div className="gate-logo">
            <span className="brand-mark">
              <LogoMark width={22} height={22} />
            </span>
            <div className="brand-text">
              <p className="brand-name">ПОЛИПЛАСТИК</p>
              <p className="brand-sub">Онбординг в MAX</p>
            </div>
          </div>

          <h1 className="gate-title">Новичок не должен оставаться один на один с вопросами</h1>
          <p className="gate-lead">
            Кабинет показывает, где человек застрял, о чём спросил и где нужен рекрутёр, а не
            бот.
          </p>

          <ul className="gate-points">
            {POINTS.map((point) => (
              <li className="gate-point" key={point}>
                <span className="gate-point-mark">
                  <CheckIcon width={13} height={13} strokeWidth={2.4} />
                </span>
                {point}
              </li>
            ))}
          </ul>
        </div>

        <div className="gate-side">
          <p className="eyebrow">Кабинет рекрутера</p>
          <h2>Вход по токену</h2>
          <p className="muted">
            Доступ выдаёт администратор HR. Токен определяет, чьи карточки и вопросы вы увидите.
          </p>
          <form onSubmit={submit} className="gate-form">
            <label htmlFor="token">Токен доступа</label>
            <input
              id="token"
              type="password"
              autoComplete="off"
              spellCheck={false}
              value={value}
              onChange={(event) => setValue(event.target.value)}
              placeholder="Вставьте токен"
              aria-describedby={error ? "token-error" : undefined}
            />
            {error ? (
              <p className="form-error" id="token-error" role="alert">
                {error}
              </p>
            ) : null}
            <button type="submit" className="button button-primary" disabled={busy}>
              {busy ? "Проверяем…" : "Войти в кабинет"}
            </button>
          </form>
          <p className="gate-footnote">
            Токен хранится только в этом браузере и передаётся в заголовке Authorization. Сессии
            и cookie нет.
          </p>
        </div>
      </section>
    </main>
  );
}
