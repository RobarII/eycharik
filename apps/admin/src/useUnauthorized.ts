import { useEffect } from "react";

export function useUnauthorized(error: Error | null, onUnauthorized: () => void): void {
  useEffect(() => {
    if (error?.name === "Unauthorized") onUnauthorized();
  }, [error, onUnauthorized]);
}
