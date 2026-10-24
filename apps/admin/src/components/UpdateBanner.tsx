/**
 * One strip for the two things that change under the recruiter's hands and are not their fault.
 *
 * It sits above the shell because it belongs to the tab, not to a screen: a filter change must not
 * hide it. Offline wins over "new build" — reloading without a network only loses the page.
 */
export function UpdateBanner({
  offline,
  stale,
  onReload,
}: {
  offline: boolean;
  stale: boolean;
  onReload: () => void;
}) {
  if (!offline && !stale) return null;

  return (
    <div className={offline ? "banner banner-warn" : "banner"} role="status">
      {offline ? (
        <span>Нет сети. Данные на экране — последние полученные.</span>
      ) : (
        <>
          <span>Кабинет обновился. Перезагрузите страницу, чтобы увидеть новую версию.</span>
          <button type="button" className="link-button" onClick={onReload}>
            Перезагрузить
          </button>
        </>
      )}
    </div>
  );
}
