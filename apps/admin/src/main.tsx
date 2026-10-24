import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { App } from "./App";
import { Boundary } from "./components/Boundary";
import "./styles.css";

const client = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error) => !(error instanceof Error && error.name === "Unauthorized") && count < 2,
      refetchOnWindowFocus: true,
      // A laptop that slept in a meeting should not show yesterday's queue when it wakes.
      refetchOnReconnect: true,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <Boundary>
        <App />
      </Boundary>
    </QueryClientProvider>
  </React.StrictMode>,
);
