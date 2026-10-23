import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";

import { fetchRuns, getToken, setToken } from "./api";
import { TokenGate } from "./components/TokenGate";
import { QuestionsPage } from "./pages/QuestionsPage";
import { RiskPage } from "./pages/RiskPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { RunsPage } from "./pages/RunsPage";

type Route =
  | { name: "runs" }
  | { name: "run"; id: string }
  | { name: "questions" }
  | { name: "risk" };

function parseRoute(hash: string): Route {
  const path = hash.replace(/^#\/?/, "");
  if (path.startsWith("run/")) {
    const id = path.slice("run/".length);
    return id ? { name: "run", id } : { name: "runs" };
  }
  if (path === "questions") return { name: "questions" };
  if (path === "risk") return { name: "risk" };
  return { name: "runs" };
}

function navigate(path: string): void {
  window.location.hash = `#/${path}`;
}

export function App() {
  const queryClient = useQueryClient();
  const [token, setTokenState] = useState(getToken());
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));

  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const logout = useCallback(() => {
    setToken("");
    setTokenState("");
    queryClient.clear();
    window.location.hash = "";
  }, [queryClient]);

  const login = useCallback(async (value: string) => {
    setToken(value);
    try {
      await fetchRuns(1);
    } catch (error) {
      setToken("");
      throw error;
    }
    setTokenState(value);
  }, []);

  if (!token) return <TokenGate onSubmit={login} />;

  const active = route.name === "runs" || route.name === "run" ? "runs" : route.name;

  return (
    <div className="shell">
      <a className="skip" href="#main">
        К содержимому
      </a>
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">ПП</span>
          <div>
            <p className="brand-name">ПОЛИПЛАСТИК</p>
            <p className="brand-sub">Онбординг</p>
          </div>
        </div>
        <nav className="nav" aria-label="Разделы кабинета">
          <button
            type="button"
            className={active === "runs" ? "nav-link nav-link-on" : "nav-link"}
            aria-current={active === "runs" ? "page" : undefined}
            onClick={() => navigate("runs")}
          >
            Сотрудники
          </button>
          <button
            type="button"
            className={active === "questions" ? "nav-link nav-link-on" : "nav-link"}
            aria-current={active === "questions" ? "page" : undefined}
            onClick={() => navigate("questions")}
          >
            Вопросы
          </button>
          <button
            type="button"
            className={active === "risk" ? "nav-link nav-link-on" : "nav-link"}
            aria-current={active === "risk" ? "page" : undefined}
            onClick={() => navigate("risk")}
          >
            Риски
          </button>
        </nav>
        <button type="button" className="link-button" onClick={logout}>
          Выйти
        </button>
      </header>

      <main id="main" className="main">
        {route.name === "runs" ? (
          <RunsPage onOpen={(id) => navigate(`run/${id}`)} onUnauthorized={logout} />
        ) : null}
        {route.name === "run" ? (
          <RunDetailPage
            runId={route.id}
            onBack={() => navigate("runs")}
            onUnauthorized={logout}
          />
        ) : null}
        {route.name === "risk" ? <RiskPage onUnauthorized={logout} /> : null}
        {route.name === "questions" ? (
          <QuestionsPage
            onOpenRun={(id) => navigate(`run/${id}`)}
            onUnauthorized={logout}
          />
        ) : null}
      </main>

      <footer className="footer">
        <span>Внутренний кабинет · демо-стенд</span>
        <span>Данные обновляются автоматически</span>
      </footer>
    </div>
  );
}
