// Pages is the HTTPS front door. APIs stay same-origin and reach a private Worker
// through a service binding, without a public workers.dev TLS connection.
export default {
  async fetch(req, env) {
    if (!new URL(req.url).pathname.startsWith('/api/')) return env.ASSETS.fetch(req);
    if (!env.DESK_API) return Response.json({ error: 'Dashboard API unavailable' }, {
      status: 503, headers: { 'Cache-Control': 'no-store' },
    });
    // Preserve Authorization, method/body and WebSocket upgrades. Authentication
    // belongs to the fail-closed desk Worker; the relay embeds no credentials.
    return env.DESK_API.fetch(req);
  },
};
