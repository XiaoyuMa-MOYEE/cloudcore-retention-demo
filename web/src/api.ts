import type { Customer, Task } from "./types";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail;
    const issues = Array.isArray(detail?.errors)
      ? "\n" +
        detail.errors
          .map(
            (x: { row_number?: number; customer_id?: string; field?: string; problem?: string }) =>
              `${x.customer_id ? `${x.customer_id} · ` : ""}Row ${x.row_number ?? "?"} · ${x.field ?? ""}: ${x.problem}`,
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

export const getDemo = () =>
  api<{ customers: Customer[]; synthetic_data: boolean; human_approval_required: boolean }>("/api/demo");

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

export const analyze = (file?: File) => {
  const body = new FormData();
  if (file) body.append("file", file);
  return api<Task>("/api/analyze", { method: "POST", body });
};

export function downloadCsv(csv: string) {
  const url = URL.createObjectURL(new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "offers.csv";
  link.click();
  URL.revokeObjectURL(url);
}
