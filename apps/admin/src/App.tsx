import { useIsFetching, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState, type ComponentType, type SVGProps } from "react";

import { Unauthorized, closeSession, fetchMe, fetchOverview, openSession } from "./api";
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
import { SessionProvider, sessionFor } from "./session";
import { KnowledgePage } from "./pages/KnowledgePage";
import { OverviewPage } from "./pages/OverviewPage";
import { QuestionsPage } from "./pages/QuestionsPage";
import { RiskPage } from "./pages/RiskPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { RunsPage } from "./pages/RunsPage";
import { useUnauthorized } from "./useUnauthorized";
import { errorText } from "./errors";
import { REFRESH, ROLE_LABELS, TENANT } from "./config";
import { useRoute, type Route } from "./route";
import { formatDateTime } from "./format";
import type { Capability } from "./types";

const TITLES: Record<Route["name"], string> = {
  overview: "Обзор",
  runs: "Сотрудники",
  run: "Карточка сотрудника",
  questions: "Вопросы",
  risk: "Риски",
  knowledge: "База знаний",
};

const NAV: ReadonlyArray<{
  name: Exclude<Route["name"], "run">;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  capability: Capability;
}> = [
  { name: "overview", label: "Обзор", icon: OverviewIcon, capability: "runs.read" },
  { name: "runs", label: "Сотрудники", icon: UsersIcon, capability: "runs.read" },
  { name: "questions", label: "Вопросы", icon: ChatIcon, capability: "questions.read" },
  { name: "risk", label: "Риски", icon: RiskIcon, capability: "analytics.read" },
  { name: "knowledge", label: "Знания", icon: BookIcon, capability: "knowledge.read" },
];

export function App() {
  const queryClient = useQueryClient();
  const { route, navigate } = useRoute();
  const fetching = useIsFetching();
  // A new epoch is a new identity: it retires the cached one so the shell cannot outlive a logout.
  const [epoch, setEpoch] = useState(0);

  // The cookie is the session; this query only discovers who it belongs to.
  const me = useQuery({
    queryKey: ["me", epoch],
    queryFn: fetchMe,
    retry: (count, error) => !(error instanceof Unauthorized) && count < 2,
    staleTime: 5 * 60_000,
  });

  const overview = useQuery({
    queryKey: ["overview"],
    queryFn: fetchOverview,
    enabled: me.isSuccess,
    refetchInterval: REFRESH.overview,
  });

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [route]);

  const logout = useCallback(async () => {
    await closeSession().catch(() => undefined);
    queryClient.clear();
    window.location.hash = "";
    // `clear()` drops the data but the observer of the old key keeps its last result; a new key
    // makes it ask again, and the answer is now 401.
    setEpoch((value) => value + 1);
  }, [queryClient]);

  const login = useCallback(
    async (token: string) => {
      await openSession(token);
      try {
        // Fail before the shell opens, so a bad token never renders an empty cabinet.
        await fetchMe();
        queryClient.clear();
        setEpoch((value) => value + 1);
      } catch (failure) {
        await closeSession().catch(() => undefined);
        throw failure;
      }
    },
    [queryClient],
  );

  useUnauthorized(overview.error, () => void logout());

  if (me.isPending) {
    return (
      <main className="gate">
        <p className="gate-status" role="status">
          Проверяем доступ…
        </p>
      </main>
    );
  }

  if (me.isError) {
    if (me.error instanceof Unauthorized) return <TokenGate onSubmit={login} />;
    return (
      <main className="gate">
        <section className="gate-card gate-card-single">
          <p className="eyebrow">Нет связи</p>
          <h1 className="gate-title">Кабинет не смог открыться</h1>
          <p className="gate-lead">{errorText(me.error)}</p>
          <button type="button" className="button button-primary" onClick={() => void me.refetch()}>
            Повторить
          </button>
        </section>
      </main>
    );
  }

  const session = sessionFor(me.data);
  const visible = NAV.filter((item) => session.can(item.capability));
  const activeName = visible.some((item) => item.name === (route.name === "run" ? "runs" : route.name))
    ? route.name
    : (visible[0]?.name ?? "overview");
  const active = activeName === "run" ? "runs" : activeName;
  const expires = me.data.expires_at;

  return (
    <SessionProvider value={session}>
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
              <p className="brand-name">{TENANT.name}</p>
              <p className="brand-sub">{TENANT.subtitle}</p>
            </div>
          </div>

          <nav className="nav" aria-label="Разделы кабинета">
            {visible.map(({ name, label, icon: Icon }) => {
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
            <p className="sidebar-role">
              {ROLE_LABELS[me.data.role] ?? me.data.role}
              {expires ? (
                <span className="sidebar-expiry">до {formatDateTime(expires)}</span>
              ) : null}
            </p>
            <button type="button" className="logout" onClick={() => void logout()}>
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
                onClick={() => void logout()}
              >
                <LogoutIcon width={17} height={17} />
              </button>
            </div>
          </header>

          <main id="main" className="main">
            {route.name === "overview" && session.can("runs.read") ? (
              <OverviewPage
                onOpenRun={(id) => navigate(`run/${id}`)}
                onNavigate={navigate}
                onUnauthorized={() => void logout()}
              />
            ) : null}
            {route.name === "runs" && session.can("runs.read") ? (
              <RunsPage
                onOpen={(id) => navigate(`run/${id}`)}
                onUnauthorized={() => void logout()}
              />
            ) : null}
            {route.name === "run" && route.id && session.can("runs.read") ? (
              <RunDetailPage
                runId={route.id}
                onBack={() => navigate("runs")}
                onUnauthorized={() => void logout()}
              />
            ) : null}
            {route.name === "risk" && session.can("analytics.read") ? (
              <RiskPage
                onOpenRun={(id) => navigate(`run/${id}`)}
                onUnauthorized={() => void logout()}
              />
            ) : null}
            {route.name === "knowledge" && session.can("knowledge.read") ? (
              <KnowledgePage onUnauthorized={() => void logout()} />
            ) : null}
            {route.name === "questions" && session.can("questions.read") ? (
              <QuestionsPage
                onOpenRun={(id) => navigate(`run/${id}`)}
                onUnauthorized={() => void logout()}
              />
            ) : null}
          </main>
        </div>
      </div>
    </SessionProvider>
  );
}
