export default {
  async fetch(request, env) {
    const incoming = new URL(request.url);
    const backend = new URL(env.BACKEND_ORIGIN);
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
