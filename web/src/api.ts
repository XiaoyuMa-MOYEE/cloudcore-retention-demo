import type { Customer, Task } from "./types";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, credentials: "include" });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail;
    const issues = Array.isArray(detail?.errors)
      ? "\n" +
        detail.errors
          .map(
            (x: { row_number?: number; field?: string; problem?: string }) =>
              `Row ${x.row_number ?? "?"} · ${x.field}: ${x.problem}`,
          )
          .join("\n")
      : "";
    const message =
      typeof detail === "string"
        ? detail
        : (detail?.message || `Request failed (${response.status})`) + issues;
    throw new Error(message);
  }
  return body as T;
}

export const getSession = () => api<{ authenticated: boolean }>("/api/session");
export const login = (access_code: string) =>
  api("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ access_code }),
  });
export const logout = () => api("/api/logout", { method: "POST" });
export const getDemo = () =>
  api<{
    customers: Customer[];
    synthetic_data: boolean;
    human_approval_required: boolean;
  }>("/api/demo");
export const validateCsv = (file: File) => {
  const body = new FormData();
  body.append("file", file);
  return api<{
    valid: boolean;
    rows: number;
    customers: Customer[];
    synthetic_data: boolean;
    analysis_allowed: boolean;
    message: string;
  }>("/api/upload/validate", { method: "POST", body });
};
export const startAnalysis = (mode: "mock" | "live" = "live") =>
  api<{ task_id: string }>("/api/analysis?mode=" + mode, { method: "POST" });
export const startUploadAnalysis = (
  file: File,
  mode: "mock" | "live" = "live",
) => {
  const body = new FormData();
  body.append("file", file);
  return api<{ task_id: string }>("/api/analysis/upload?mode=" + mode, {
    method: "POST",
    body,
  });
};
export const getTask = (id: string) => api<Task>(`/api/analysis/${id}`);
export const getLatestTask = () =>
  api<{ task: Task | null }>("/api/analysis/latest");
export const retryTask = (id: string) =>
  api(`/api/analysis/${id}/retry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ failed_only: true }),
  });
export const downloadUrl = (id: string) => `/api/analysis/${id}/download`;
