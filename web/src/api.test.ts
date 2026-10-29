import { afterEach, describe, expect, it, vi } from "vitest";
import { analyze, validateCsv } from "./api";

afterEach(() => vi.restoreAllMocks());

describe("stateless demo API", () => {
  it("sends a selected CSV to the analysis API without a login step", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ status: "completed", total: 1, succeeded: 1, failed: 0 }), { status: 200 }),
    );
    const file = new File(["synthetic"], "demo.csv", { type: "text/csv" });
    await analyze(file);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/analyze");
    expect(options?.method).toBe("POST");
    expect(options?.body).toBeInstanceOf(FormData);
    expect((options?.body as FormData).get("file")).toBe(file);
    expect(options).not.toHaveProperty("credentials", "include");
  });

  it("validates uploads without persisting or changing the file", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ valid: true, rows: 1, customers: [], synthetic_data: true, analysis_allowed: true, message: "ok" }), { status: 200 }),
    );
    const file = new File(["original,csv"], "source.csv", { type: "text/csv" });
    await validateCsv(file);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/upload/validate");
    expect((options?.body as FormData).get("file")).toBe(file);
  });
});
