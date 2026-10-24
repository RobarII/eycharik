import { useQuery } from "@tanstack/react-query";

/**
 * What build of the cabinet this tab is running, and whether a newer one has landed.
 *
 * `index.html` and `version.json` are served `no-store`, the assets are content-addressed, so a
 * deploy is safe while tabs are open — but the tab keeps running the old code until it is told.
 * The check is cheap and it is the only way a recruiter learns that a fixed screen is now fixed.
 */
export const BUILD_ID: string = __BUILD_ID__;

const VERSION_URL = "/version.json";

/** How often an idle, focused cabinet looks for a new build. */
const POLL_MS = 5 * 60_000;

interface Release {
  build: string;
}

/** `null` means "the server did not answer usefully", never "up to date". */
export function isStale(build: string, remote: unknown): boolean {
  return typeof remote === "string" && remote !== "" && remote !== build;
}

async function loadBuild(): Promise<string> {
  const response = await fetch(`${VERSION_URL}?build=${encodeURIComponent(BUILD_ID)}`, {
    cache: "no-store",
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`version ${response.status}`);
  const body = (await response.json().catch(() => null)) as Partial<Release> | null;
  const build = body?.build;
  if (typeof build !== "string") throw new Error("version: malformed body");
  return build;
}

export function useReleaseCheck(enabled: boolean): { stale: boolean; reload: () => void } {
  const query = useQuery({
    queryKey: ["release"],
    queryFn: loadBuild,
    enabled,
    refetchInterval: POLL_MS,
    // A failed check is not a user-facing error: the cabinet keeps working and tries again later.
    retry: false,
    staleTime: 60_000,
  });

  return {
    stale: query.isSuccess && isStale(BUILD_ID, query.data),
    // A new build may ship a new snapshot of the data; a reload is the honest way to take both.
    reload: () => window.location.reload(),
  };
}
