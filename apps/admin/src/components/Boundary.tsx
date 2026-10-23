import { Component, type ErrorInfo, type ReactNode } from "react";

interface BoundaryState {
  error: Error | null;
}

/**
 * A crashed screen shows a way out instead of a white page.
 *
 * React unmounts the whole tree after a render error, so without this a single bad field turns the
 * cabinet blank and the recruiter loses the tab. The boundary keeps the shell alive: it offers a
 * reload, and in development it also prints the stack.
 */
export class Boundary extends Component<{ children: ReactNode }, BoundaryState> {
  override state: BoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): BoundaryState {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("cabinet crashed", error, info.componentStack);
  }

  override render(): ReactNode {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div className="state state-crash" role="alert">
        <p className="state-title">Экран не открылся</p>
        <p className="state-text">
          Данные не потеряны: это ошибка отрисовки. Обновите страницу — если повторяется,
          сообщите команде и приложите текст ниже.
        </p>
        <pre className="state-detail">{error.message}</pre>
        <button
          type="button"
          className="button button-primary"
          onClick={() => this.setState({ error: null })}
        >
          Попробовать снова
        </button>
      </div>
    );
  }
}
