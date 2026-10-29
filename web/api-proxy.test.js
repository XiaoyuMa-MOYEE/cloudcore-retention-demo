import { afterEach, describe, expect, it, vi } from "vitest";
import worker from "./api-proxy.js";

afterEach(() => vi.unstubAllGlobals());

describe("Cloudflare API proxy", () => {
  it("forwards same-origin API requests to the configured HTTPS backend", async () => {
    const upstream = new Response("ok", { status: 200 });
    const fetchMock = vi.fn(async () => upstream);
    vi.stubGlobal("fetch", fetchMock);
    const assets = { fetch: vi.fn() };
    const request = new Request("https://cloudcore.moyee.uk/api/health?check=1");

    const response = await worker.fetch(
      request,
      { BACKEND_ORIGIN: "https://api.example.test", ASSETS: assets },
    );

    expect(response).toBe(upstream);
    expect(fetchMock).toHaveBeenCalledOnce();
    const forwarded = fetchMock.mock.calls[0][0];
    expect(forwarded.url).toBe("https://api.example.test/api/health?check=1");
    expect(forwarded.headers.get("X-Forwarded-Host")).toBe("cloudcore.moyee.uk");
    expect(forwarded.headers.get("X-Forwarded-Proto")).toBe("https");
    expect(assets.fetch).not.toHaveBeenCalled();
  });

  it("serves non-API requests from the static asset binding", async () => {
    const assetResponse = new Response("index");
    const assets = { fetch: vi.fn(async () => assetResponse) };
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const request = new Request("https://cloudcore.moyee.uk/customers");

    const response = await worker.fetch(request, { ASSETS: assets });

    expect(response).toBe(assetResponse);
    expect(assets.fetch).toHaveBeenCalledWith(request);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("fails closed when the backend origin is still a placeholder", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const request = new Request("https://cloudcore.moyee.uk/api/health");

    const response = await worker.fetch(request, {
      BACKEND_ORIGIN: "https://REPLACE_WITH_PRIVATE_BACKEND_HOST",
    });

    expect(response.status).toBe(503);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
