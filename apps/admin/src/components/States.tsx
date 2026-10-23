import type { ReactNode } from "react";

import { errorText } from "../errors";

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="state">
      <p className="state-title">{title}</p>
      {children ? <p className="state-text">{children}</p> : null}
    </div>
  );
}

/**
 * A failure, in Russian.
 *
 * Every caller hands over the error itself, so no screen can leak the API's English `detail` and no
 * screen has to remember to translate. `role="alert"` announces it without stealing focus.
 */
export function ErrorNote({
  error,
  onRetry,
}: {
  error: Error;
  onRetry?: () => void;
}) {
  return (
    <div className="note note-error" role="alert">
      <span>{errorText(error)}</span>
      {onRetry ? (
        <button type="button" className="link-button" onClick={onRetry}>
          Повторить
        </button>
      ) : null}
    </div>
  );
}

export function SkeletonRows({ rows = 3 }: { rows?: number }) {
  return (
    <div className="skeleton-list" aria-hidden="true">
      {Array.from({ length: rows }, (_, index) => (
        <div className="skeleton-row" key={index}>
          <div className="skeleton skeleton-title" />
          <div className="skeleton skeleton-line" />
        </div>
      ))}
    </div>
  );
}
