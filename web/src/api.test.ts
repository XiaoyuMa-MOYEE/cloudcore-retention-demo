import { afterEach, describe, expect, it, vi } from "vitest";
import { login } from "./api";

afterEach(() => vi.restoreAllMocks());

describe("authenticated API transport", () => {
  it("sends the access code only in the login request and includes cookies on API calls", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response('{"authenticated":true}', { status: 200 }),
      );
    await login("group-secret");
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/login");
    expect(options?.credentials).toBe("include");
    expect(options?.body).toBe('{"access_code":"group-secret"}');
  });
});
