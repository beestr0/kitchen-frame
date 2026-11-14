import worker from './index.js';
import { cachedWeather } from './weather-cache.js';
export { MessageRoom } from './messages.js';

// Production entry point: a missing secret must never open the private API.
// The public static shell contains no personal data or embedded credentials.
export default {
  async scheduled(controller, env, ctx) {
    // This desk schedule must not activate the original calendar cron.
    if (env.WEATHER_ENABLED === 'true') ctx.waitUntil(cachedWeather(env).catch(() => {}));
  },
  async fetch(req, env, ctx) {
    if (new URL(req.url).pathname.startsWith('/api/') && !env.DASHBOARD_KEY) {
      return Response.json({ error: 'Dashboard access is not configured' }, {
        status: 503,
        headers: { 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer' },
      });
    }
    let response;
    if (new URL(req.url).pathname === '/api/weather') {
      const headers = { 'Cache-Control': 'no-store' };
      if (req.headers.get('Authorization') !== 'Bearer ' + env.DASHBOARD_KEY) response = Response.json({ error: 'unauthorized' }, { status: 401, headers });
      else if (req.method !== 'GET') response = Response.json({ error: 'method not allowed' }, { status: 405, headers });
      else if (env.WEATHER_ENABLED !== 'true') response = Response.json({ error: 'Weather is not enabled' }, { status: 503, headers });
      else {
        try { response = Response.json(await cachedWeather(env), { headers }); }
        catch { response = Response.json({ error: 'Weather temporarily unavailable' }, { status: 503, headers }); }
      }
    } else response = await worker.fetch(req, env, ctx);
    // A WebSocket upgrade response must be returned intact.
    if (response.status === 101) return response;
    const secured = new Response(response.body, response);
    secured.headers.set('Referrer-Policy', 'no-referrer');
    secured.headers.set('X-Content-Type-Options', 'nosniff');
    return secured;
  },
};
