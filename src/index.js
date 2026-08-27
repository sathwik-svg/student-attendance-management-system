export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // API requests → Flask backend
    if (url.pathname.startsWith("/api/")) {
      const backend = env.BACKEND_URL;

      if (!backend) {
        return Response.json(
          { error: "BACKEND_URL is not configured" },
          { status: 503 }
        );
      }

      const target = new URL(url.pathname + url.search, backend);

      const proxyRequest = new Request(target.toString(), request);

      return fetch(proxyRequest);
    }

    // Everything else → Cloudflare static assets
    return env.ASSETS.fetch(request);
  }
};
