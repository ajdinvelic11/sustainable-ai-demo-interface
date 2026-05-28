export class ApiError extends Error {
  status?: number;
  details?: unknown;

  constructor(message: string, status?: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

const rawBase = import.meta.env.VITE_API_BASE_URL || "";
export const API_BASE_URL = rawBase.replace(/\/$/, "");
let csrfToken: string | null = null;

export function setCsrfToken(token: string | null) {
  csrfToken = token;
}

export function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const method = (options.method || "GET").toUpperCase();
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && csrfToken && !headers.has("X-CSRF-Token")) {
    headers.set("X-CSRF-Token", csrfToken);
  }

  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      ...options,
      method,
      headers,
      credentials: "include",
    });
  } catch (error) {
    throw new ApiError("Backend is not reachable.", undefined, error);
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message
          ? detail.message
          : payload?.message || `Request failed with status ${response.status}.`;
    throw new ApiError(message, response.status, payload);
  }

  return (await response.json()) as T;
}
