export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Health endpoint
    if (url.pathname === "/api/health") {
      return Response.json({
        status: "online",
        application: "AttendX",
        platform: "Cloudflare Workers"
      });
    }

    // Serve AttendX frontend and all static assets
    return env.ASSETS.fetch(request);
  }
};
