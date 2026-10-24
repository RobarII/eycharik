import { useEffect, useState } from "react";

/**
 * Whether the browser believes it has a network right now.
 *
 * The cabinet already refetches on focus and on reconnect; this hook exists so the screen can say
 * so out loud instead of looking frozen. `navigator.onLine` is a hint, not a guarantee — a captive
 * portal reports `true` — so the banner only ever claims "we lost the network", never "we have it".
 */
export function useOnline(): boolean {
  const [online, setOnline] = useState(() => navigator.onLine !== false);

  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);

  return online;
}
