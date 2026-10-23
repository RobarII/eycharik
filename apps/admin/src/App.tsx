import { useIsFetching, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState, type ComponentType, type SVGProps } from "react";

import { fetchOverview, fetchRuns, getToken, setToken } from "./api";
import {
  BookIcon,
  ChatIcon,
  LogoutIcon,
  LogoMark,
  OverviewIcon,
  RefreshIcon,
  RiskIcon,
  UsersIcon,
} from "./components/Icons";
import { TokenGate } from "./components/TokenGate";
import { KnowledgePage } from "./pages/KnowledgePage";
import { OverviewPage } from "./pages/OverviewPage";
import { QuestionsPage } from "./pages/QuestionsPage";
import { RiskPage } from "./pages/RiskPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { RunsPage } from "./pages/RunsPage";
import { useUnauthorized } from "./useUnauthorized";

type RouteName = "overview" | "runs" | "run" | "questions" | "risk" | "knowledge";

type Route = { name: RouteName; id?: string };

const TITLES: Record<RouteName, string> = {
  overview: "Обзор",
  runs: "Сотрудники",
  run: "Карточка сотрудника",
  questions: "Вопросы",
  risk: "Риски",
  knowledge: "База знаний",
};

const NAV: ReadonlyArray<{
  name: Exclude<RouteName, "run">;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
}> = [
  { name: "overview", label: "Обзор", icon: OverviewIcon },
  { name: "runs", label: "Сотрудники", icon: UsersIcon },
  { name: "questions", label: "Вопросы", icon: ChatIcon },
  { name: "risk", label: "Риски", icon: RiskIcon },
  { name: "knowledge", label: "Знания", icon: BookIcon },
];

function parseRoute(hash: string): Route {
  const path = hash.replace(/^#\/?/, "");
  if (path.startsWith("run/")) {
    const id = path.slice("run/".length);
    return id ? { name: "run", id } : { name: "runs" };
  }
  if (path === "runs") return { name: "runs" };
  if (path === "questions") return { name: "questions" };
  if (path === "risk") return { name: "risk" };
  if (path === "knowledge") return { name: "knowledge" };
  return { name: "overview" };
}

function navigate(path: string): void {
  window.location.hash = `#/${path}`;
}

export function App() {
  const queryClient = useQueryClient();
  const [token, setTokenState] = useState(getToken());
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));
  const fetching = useIsFetching();

  const overview = useQuery({
    queryKey: ["overview"],
    queryFn: fetchOverview,
    enabled: Boolean(token),
    refetchInterval: 30_000,
  });

  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [route]);

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

  useUnauthorized(overview.error, logout);

  if (!token) return <TokenGate onSubmit={login} />;

  const active = route.name === "run" ? "runs" : route.name;

  return (
    <div className="app">
      <a className="skip" href="#main">
        К содержимому
      </a>

      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <LogoMark width={22} height={22} />
          </span>
          <div className="brand-text">
            <p className="brand-name">ПОЛИПЛАСТИК</p>
            <p className="brand-sub">Онбординг в MAX</p>
          </div>
        </div>

        <nav className="nav" aria-label="Разделы кабинета">
          {NAV.map(({ name, label, icon: Icon }) => {
            const on = active === name;
            const badge = name === "questions" ? overview.data?.unanswered_questions : undefined;
            return (
              <button
                key={name}
                type="button"
                className={on ? "nav-link nav-link-on" : "nav-link"}
                aria-current={on ? "page" : undefined}
                title={label}
                onClick={() => navigate(name)}
              >
                <span className="nav-icon">
                  <Icon />
                </span>
                <span className="nav-label">{label}</span>
                {badge ? (
                  <span className="nav-count" aria-label={`${badge} без ответа`}>
                    {badge}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-foot">
          <button type="button" className="logout" onClick={logout}>
            <LogoutIcon width={17} height={17} />
            <span>Выйти</span>
          </button>
        </div>
      </aside>

      <div className="content">
        <header className="topbar">
          <div className="crumb">
            <span>Кабинет рекрутера</span>
            <span className="crumb-sep" aria-hidden="true">
              /
            </span>
            <strong>{TITLES[route.name]}</strong>
          </div>
          <div className="topbar-actions">
            <button
              type="button"
              className="icon-button"
              title="Обновить данные"
              aria-label="Обновить данные"
              disabled={fetching > 0}
              onClick={() => void queryClient.invalidateQueries()}
            >
              <RefreshIcon className={fetching > 0 ? "spin" : undefined} width={17} height={17} />
            </button>
            <button
              type="button"
              className="icon-button mobile-logout"
              title="Выйти"
              aria-label="Выйти"
              onClick={logout}
            >
              <LogoutIcon width={17} height={17} />
            </button>
          </div>
        </header>

        <main id="main" className="main">
          {route.name === "overview" ? (
            <OverviewPage
              onOpenRun={(id) => navigate(`run/${id}`)}
              onNavigate={navigate}
              onUnauthorized={logout}
            />
          ) : null}
          {route.name === "runs" ? (
            <RunsPage onOpen={(id) => navigate(`run/${id}`)} onUnauthorized={logout} />
          ) : null}
          {route.name === "run" && route.id ? (
            <RunDetailPage
              runId={route.id}
              onBack={() => navigate("runs")}
              onUnauthorized={logout}
            />
          ) : null}
          {route.name === "risk" ? (
            <RiskPage onOpenRun={(id) => navigate(`run/${id}`)} onUnauthorized={logout} />
          ) : null}
          {route.name === "knowledge" ? <KnowledgePage onUnauthorized={logout} /> : null}
          {route.name === "questions" ? (
            <QuestionsPage
              onOpenRun={(id) => navigate(`run/${id}`)}
              onUnauthorized={logout}
            />
          ) : null}
        </main>
      </div>
    </div>
  );
}
