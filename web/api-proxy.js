export default {
  async fetch(request, env) {
    const incoming = new URL(request.url);

    if (!incoming.pathname.startsWith("/api/")) {
      return env.ASSETS.fetch(request);
    }

    const configuredOrigin = env.BACKEND_ORIGIN;
    if (!configuredOrigin || configuredOrigin.includes("REPLACE_WITH")) {
      return new Response("The API backend has not been configured.", {
        status: 503,
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      });
    }

    let backend;
    try {
      backend = new URL(configuredOrigin);
    } catch {
      return new Response("The API backend configuration is invalid.", {
        status: 503,
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      });
    }
    if (backend.protocol !== "https:" || backend.username || backend.password) {
      return new Response("The API backend must use a credential-free HTTPS origin.", {
        status: 503,
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      });
    }

    backend.pathname = incoming.pathname;
    backend.search = incoming.search;
    const headers = new Headers(request.headers);
    headers.set("X-Forwarded-Host", incoming.host);
    headers.set("X-Forwarded-Proto", incoming.protocol.slice(0, -1));

    return fetch(
      new Request(backend, {
        method: request.method,
        headers,
        body: request.body,
        redirect: "manual",
      }),
    );
  },
};
