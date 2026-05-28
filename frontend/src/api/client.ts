import type { AuthConfig, DemoEvent, DemoState, MeResponse, SiteInfo, StartDemoResponse } from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

type ApiErrorPayload = {
  detail?: unknown;
  message?: string;
};

export class ApiError extends Error {
  status: number;
  payload: ApiErrorPayload | null;

  constructor(message: string, status: number, payload: ApiErrorPayload | null) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const payload = typeof body === "object" ? (body as ApiErrorPayload) : { message: String(body) };
    const detail = payload.detail;
    const message =
      typeof detail === "string"
        ? detail
        : typeof payload.message === "string"
          ? payload.message
          : `Request failed with HTTP ${response.status}`;
    throw new ApiError(message, response.status, payload);
  }
  return body as T;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });
  return parseResponse<T>(response);
}

export const api = {
  authConfig: () => apiFetch<AuthConfig>("/api/auth/config"),
  me: () => apiFetch<MeResponse>("/api/auth/me"),
  verify: (token: string) =>
    apiFetch<MeResponse>("/api/auth/verify", {
      method: "POST",
      body: JSON.stringify({ token })
    }),
  logout: () =>
    apiFetch<{ ok: boolean }>("/api/auth/logout", {
      method: "POST",
      body: JSON.stringify({})
    }),
  sites: () => apiFetch<SiteInfo[]>("/api/system/sites"),
  currentRun: () => apiFetch<DemoState>("/api/demo-runs/current"),
  run: (demoRunId: number) => apiFetch<DemoState>(`/api/demo-runs/${demoRunId}`),
  events: (demoRunId: number) => apiFetch<DemoEvent[]>(`/api/demo-runs/${demoRunId}/events`),
  startDemo: () =>
    apiFetch<StartDemoResponse>("/api/demo-runs/start", {
      method: "POST",
      body: JSON.stringify({})
    }),
  resetStale: (markOpenCommandsFailed: boolean, reason: string) =>
    apiFetch<{ reset_demo_runs: number; reset_commands: number; message: string }>("/api/demo-runs/reset-stale", {
      method: "POST",
      body: JSON.stringify({
        confirm: true,
        mark_open_commands_failed: markOpenCommandsFailed,
        reason
      })
    })
};

export function demoStreamUrl(): string {
  return `${API_BASE}/api/demo-runs/stream`;
}

