import { request } from "./client";
import type { AuthConfig, AuthResponse } from "../types/api";

export function getAuthConfig() {
  return request<AuthConfig>("/api/auth/config");
}

export function getCurrentUser() {
  return request<AuthResponse>("/api/auth/me");
}

export function verifyToken(token: string) {
  return request<AuthResponse>("/api/auth/verify", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export function logout() {
  return request<{ authenticated: false }>("/api/auth/logout", {
    method: "POST",
  });
}
