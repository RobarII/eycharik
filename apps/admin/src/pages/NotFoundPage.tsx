/**
 * An address the cabinet cannot read gets a straight answer.
 *
 * The alternative — falling back to the overview — teaches a recruiter that their bookmarked link
 * worked, while they are looking at somebody else's queue. The shell stays around the screen, so
 * leaving is one click, not a back-button guess.
 */
export function NotFoundPage({ onHome }: { onHome: () => void }) {
  return (
    <section className="page">
      <header className="page-head">
        <div className="page-head-text">
          <p className="eyebrow">404</p>
          <h1>Такой страницы нет</h1>
          <p className="muted">
            Ссылка устарела или в адресе опечатка. Разделы кабинета — слева.
          </p>
        </div>
      </header>
      <button type="button" className="button button-primary" onClick={onHome}>
        К обзору
      </button>
    </section>
  );
}
