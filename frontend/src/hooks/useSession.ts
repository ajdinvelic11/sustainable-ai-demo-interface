import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { AuthConfig, SessionUser } from "../types/api";

type SessionState = {
  loading: boolean;
  authenticated: boolean;
  user: SessionUser | null;
  demoAuthMode: boolean;
  authConfig: AuthConfig | null;
  error: string | null;
  refresh: () => Promise<void>;
  login: (token: string) => Promise<void>;
  logout: () => Promise<void>;
};

export function useSession(): SessionState {
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState<SessionUser | null>(null);
  const [demoAuthMode, setDemoAuthMode] = useState(false);
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [config, me] = await Promise.all([api.authConfig(), api.me()]);
      setAuthConfig(config);
      setAuthenticated(me.authenticated);
      setUser(me.user);
      setDemoAuthMode(me.demo_auth_mode);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load session.");
      setAuthenticated(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const login = useCallback(
    async (token: string) => {
      setError(null);
      try {
        await api.verify(token);
        await refresh();
      } catch (err) {
        if (err instanceof ApiError) {
          throw err;
        }
        throw new Error(err instanceof Error ? err.message : "Login failed.");
      }
    },
    [refresh]
  );

  const logout = useCallback(async () => {
    await api.logout();
    setAuthenticated(false);
    setUser(null);
    await refresh();
  }, [refresh]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { loading, authenticated, user, demoAuthMode, authConfig, error, refresh, login, logout };
}

