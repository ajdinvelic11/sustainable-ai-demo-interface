import { ApiError, apiUrl, request } from "./client";
import type { CurrentDemoResponse, DemoEvent, DemoRunState, DemoStartResponse, ResetStaleResponse, SiteInfo } from "../types/api";

export function getSites() {
  return request<SiteInfo[]>("/api/system/sites");
}

export function startDemoRun() {
  return request<DemoStartResponse>("/api/demo-runs/start", { method: "POST" });
}

export function getCurrentDemoRun() {
  return request<CurrentDemoResponse>("/api/demo-runs/current");
}

export function getDemoRun(demoRunId: number) {
  return request<DemoRunState>(`/api/demo-runs/${demoRunId}`);
}

export function getDemoEvents(demoRunId: number) {
  return request<DemoEvent[]>(`/api/demo-runs/${demoRunId}/events`);
}

export function resetStaleDemoState(failOpenCommands: boolean) {
  return request<ResetStaleResponse>("/api/demo-runs/reset-stale", {
    method: "POST",
    body: JSON.stringify({ confirm: true, fail_open_commands: failOpenCommands }),
  });
}

export async function exportDemoCertificate(demoRunId: number): Promise<{ blob: Blob; filename: string }> {
  let response: Response;
  try {
    response = await fetch(apiUrl(`/api/demo-runs/${demoRunId}/certificate`), {
      method: "GET",
      credentials: "include",
    });
  } catch (error) {
    throw new ApiError("Backend is not reachable.", undefined, error);
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    const message = typeof detail === "string" ? detail : payload?.message || `Certificate export failed with status ${response.status}.`;
    throw new ApiError(message, response.status, payload);
  }

  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  return {
    blob: await response.blob(),
    filename: match?.[1] || `sustainable-ai-training-certificate-${demoRunId}.json`,
  };
}
