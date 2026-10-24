import { useIsFetching, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ComponentType,
  type ReactNode,
  type SVGProps,
} from "react";

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
import { Boundary } from "./components/Boundary";
import { EmptyState } from "./components/States";
import { TokenGate } from "./components/TokenGate";
import { UpdateBanner } from "./components/UpdateBanner";
import { SessionProvider, sessionFor } from "./session";
import { KnowledgePage } from "./pages/KnowledgePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OverviewPage } from "./pages/OverviewPage";
import { QuestionsPage } from "./pages/QuestionsPage";
import { RiskPage } from "./pages/RiskPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { RunsPage } from "./pages/RunsPage";
import { useOnline } from "./useOnline";
import { useUnauthorized } from "./useUnauthorized";
import { BUILD_ID, useReleaseCheck } from "./version";
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
  notFound: "Страница не найдена",
};

function sectionLocked(name: Route["name"]): ReactNode {
  return (
    <EmptyState title={`${TITLES[name]}: нет доступа`}>
      Ваша роль не открывает этот раздел. Права выдаёт HR-администратор.
    </EmptyState>
  );
}

const NAV: ReadonlyArray<{
  name: Exclude<Route["name"], "run" | "notFound">;
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

  const online = useOnline();
  const release = useReleaseCheck(me.isSuccess);
  const mainRef = useRef<HTMLElement>(null);
  // The first paint of the shell is not a navigation: focus stays where the gate left it.
  const navigated = useRef(false);

  useEffect(() => {
    document.title = me.isSuccess
      ? `${TITLES[route.name]} — ${TENANT.name}`
      : `Вход в кабинет — ${TENANT.name}`;
  }, [me.isSuccess, route.name]);

  useEffect(() => {
    if (!navigated.current) {
      navigated.current = true;
      return;
    }
    // The hash swaps the screen without a reload, so focus would stay on the link we just left.
    mainRef.current?.focus({ preventScroll: true });
  }, [route.name, route.id]);

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
  // `run` belongs to the people list; an unknown address belongs to no section at all.
  const section = route.name === "run" ? "runs" : route.name;
  const active = visible.find((item) => item.name === section)?.name ?? null;
  const expires = me.data.expires_at;

  let screen: ReactNode;
  if (route.name === "notFound") {
    screen = <NotFoundPage onHome={() => navigate("overview")} />;
  } else if (route.name === "run" && route.id) {
    screen = session.can("runs.read") ? (
      <RunDetailPage
        runId={route.id}
        onBack={() => navigate("runs")}
        onUnauthorized={() => void logout()}
      />
    ) : (
      sectionLocked("run")
    );
  } else if (route.name === "overview" || route.name === "runs") {
    screen = !session.can("runs.read") ? (
      sectionLocked(route.name)
    ) : route.name === "overview" ? (
      <OverviewPage
        onOpenRun={(id) => navigate(`run/${id}`)}
        onNavigate={navigate}
        onUnauthorized={() => void logout()}
      />
    ) : (
      <RunsPage onOpen={(id) => navigate(`run/${id}`)} onUnauthorized={() => void logout()} />
    );
  } else if (route.name === "risk") {
    // A section the role cannot read says so; a blank main reads as a broken screen.
    screen = session.can("analytics.read") ? (
      <RiskPage
        onOpenRun={(id) => navigate(`run/${id}`)}
        onUnauthorized={() => void logout()}
      />
    ) : (
      sectionLocked("risk")
    );
  } else if (route.name === "knowledge") {
    screen = session.can("knowledge.read") ? (
      <KnowledgePage onUnauthorized={() => void logout()} />
    ) : (
      sectionLocked("knowledge")
    );
  } else {
    screen = session.can("questions.read") ? (
      <QuestionsPage
        onOpenRun={(id) => navigate(`run/${id}`)}
        onUnauthorized={() => void logout()}
      />
    ) : (
      sectionLocked("questions")
    );
  }

  return (
    <SessionProvider value={session}>
      <div className="app">
        <UpdateBanner offline={!online} stale={release.stale} onReload={release.reload} />
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
            <p className="sidebar-build" title="Версия сборки: назовите её в обращении к команде">
              {BUILD_ID}
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

          {/* A crash inside a screen must not take the shell: the nav stays, the key resets it. */}
          <main
            id="main"
            className="main"
            tabIndex={-1}
            ref={mainRef}
            aria-label={TITLES[route.name]}
          >
            <Boundary key={`${route.name}:${route.id ?? ""}`}>{screen}</Boundary>
          </main>
        </div>
      </div>
    </SessionProvider>
  );
}
