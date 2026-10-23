import { createContext, useContext } from "react";

import type { AdminIdentity, Capability } from "./types";

export interface Session {
  identity: AdminIdentity;
  /** The current subject, as the server spells it in `assignee`. */
  subject: string;
  /** The only place the cabinet asks what it may render. Never re-derive this from the role. */
  can: (capability: Capability) => boolean;
}

const SessionContext = createContext<Session | null>(null);

export const SessionProvider = SessionContext.Provider;

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (session === null) {
    throw new Error("useSession() must be used inside a SessionProvider");
  }
  return session;
}

export function sessionFor(identity: AdminIdentity): Session {
  return {
    identity,
    subject: identity.subject,
    can: (capability) => identity.capabilities.includes(capability),
  };
}
