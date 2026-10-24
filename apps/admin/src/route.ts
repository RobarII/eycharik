import { useCallback, useEffect, useState } from "react";

/**
 * The URL hash is the router, and the query string is the screen state.
 *
 * A queue nobody can link to is a queue nobody shares, so filters live in the hash: `#/questions?
 * status=answered` opens the same list in another browser. Navigation pushes a history entry;
 * a filter change replaces the current one, so the back button never walks through keystrokes.
 *
 * An address the cabinet does not know becomes `notFound`, never a silent overview: a stale link
 * must say so instead of showing the first screen as if the link worked.
 */
export type RouteName =
  | "overview"
  | "runs"
  | "run"
  | "questions"
  | "risk"
  | "knowledge"
  | "notFound";

export interface Route {
  name: RouteName;
  id?: string;
  params: URLSearchParams;
}

const SECTIONS: readonly Exclude<RouteName, "run" | "notFound">[] = [
  "overview",
  "runs",
  "questions",
  "risk",
  "knowledge",
];

export function parseRoute(hash: string): Route {
  const raw = hash.replace(/^#\/?/, "");
  const [path = "", query = ""] = raw.split("?");
  const params = new URLSearchParams(query);
  if (path.startsWith("run/")) {
    const id = path.slice("run/".length);
    return id ? { name: "run", id, params } : { name: "runs", params };
  }
  // An empty hash is the front door; anything else must name a section we can draw.
  if (!path) return { name: "overview", params };
  const name = SECTIONS.find((section) => section === path);
  return name ? { name, params } : { name: "notFound", params };
}

export function routeHash(route: Route): string {
  const path = route.name === "run" && route.id ? `run/${route.id}` : route.name;
  const query = route.params.toString();
  return `#/${path}${query ? `?${query}` : ""}`;
}

/** Set a parameter, or drop it when the value is empty: `?status=` is noise, not a state. */
export function setParam(params: URLSearchParams, key: string, value: string): void {
  if (value) params.set(key, value);
  else params.delete(key);
}

export interface Router {
  route: Route;
  navigate: (path: string) => void;
  setParams: (mutate: (params: URLSearchParams) => void) => void;
}

export function useRoute(): Router {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));

  useEffect(() => {
    const sync = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  const navigate = useCallback((path: string) => {
    window.location.hash = `#/${path}`;
  }, []);

  const setParams = useCallback((mutate: (params: URLSearchParams) => void) => {
    const next = parseRoute(window.location.hash);
    mutate(next.params);
    const hash = routeHash(next);
    if (hash === window.location.hash) return;
    window.history.replaceState(null, "", hash);
    // `replaceState` is silent by design; tell the subscribers the address changed.
    window.dispatchEvent(new Event("hashchange"));
  }, []);

  return { route, navigate, setParams };
}
