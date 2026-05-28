import { useEffect, useState } from "react";

import { apiUrl } from "../api/client";
import type { CurrentDemoResponse } from "../types/api";

export function useDemoStream(enabled: boolean) {
  const [state, setState] = useState<CurrentDemoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const source = new EventSource(apiUrl("/api/demo-runs/stream"), { withCredentials: true });
    source.addEventListener("open", () => {
      setConnected(true);
      setError(null);
    });
    source.addEventListener("state", (event) => {
      setState(JSON.parse((event as MessageEvent).data));
    });
    source.addEventListener("error", () => {
      setConnected(false);
      setError("Live stream disconnected. The dashboard will reconnect automatically.");
    });
    return () => source.close();
  }, [enabled]);

  return { state, error, connected };
}
