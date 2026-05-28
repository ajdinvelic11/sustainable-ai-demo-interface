import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from "react";

import { getAuthConfig, getCurrentUser, logout as logoutRequest, verifyToken } from "../api/auth";
import { setCsrfToken } from "../api/client";
import type { AuthConfig, AuthResponse, AuthUser } from "../types/api";

interface AuthContextValue {
  authenticated: boolean;
  loading: boolean;
  user: AuthUser | null;
  config: AuthConfig | null;
  login: (token: string) => Promise<AuthResponse>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [config, setConfig] = useState<AuthConfig | null>(null);

  const applyAuth = (response: AuthResponse) => {
    setAuthenticated(response.authenticated);
    setUser(response.authenticated ? response.user : null);
    setCsrfToken(response.csrf_token ?? null);
  };

  const refresh = async () => {
    setLoading(true);
    try {
      const [authConfig, authResponse] = await Promise.all([getAuthConfig(), getCurrentUser()]);
      setConfig(authConfig);
      applyAuth(authResponse);
    } catch {
      setAuthenticated(false);
      setUser(null);
      setCsrfToken(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const login = async (token: string) => {
    const response = await verifyToken(token);
    applyAuth(response);
    return response;
  };

  const logout = async () => {
    try {
      await logoutRequest();
    } finally {
      setAuthenticated(false);
      setUser(null);
      setCsrfToken(null);
    }
  };

  const value = useMemo(
    () => ({ authenticated, loading, user, config, login, logout, refresh }),
    [authenticated, loading, user, config],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return value;
}
