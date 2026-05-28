import { useEffect, useState } from "react";
import { demoStreamUrl } from "../api/client";
import type { DemoState } from "../types/api";

export function useDemoStream(enabled: boolean) {
  const [state, setState] = useState<DemoState | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const eventSource = new EventSource(demoStreamUrl(), { withCredentials: true });
    eventSource.addEventListener("open", () => {
      setConnected(true);
      setError(null);
    });
    eventSource.addEventListener("demo-state", (event) => {
      setState(JSON.parse(event.data) as DemoState);
    });
    eventSource.addEventListener("error", () => {
      setConnected(false);
      setError("Live stream is reconnecting.");
    });
    return () => eventSource.close();
  }, [enabled]);

  return { state, connected, error };
}

