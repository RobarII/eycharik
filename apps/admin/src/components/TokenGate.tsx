import { useState, type FormEvent } from "react";

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
        <div className="brand">
          <span className="brand-mark">ПП</span>
          <div>
            <p className="brand-name">ПОЛИПЛАСТИК</p>
            <p className="brand-sub">Онбординг новых сотрудников</p>
          </div>
        </div>
        <h1>Кабинет рекрутера</h1>
        <p className="muted">
          Прогресс новичков, вопросы без ответа и точки, где нужен человек. Доступ выдаёт
          администратор HR.
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
            {busy ? "Проверяем…" : "Войти"}
          </button>
        </form>
        <p className="gate-footnote">
          Токен хранится только в этом браузере и передаётся в заголовке Authorization.
        </p>
      </section>
    </main>
  );
}
