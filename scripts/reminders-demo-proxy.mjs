import http from 'node:http';
import { readFileSync, statSync } from 'node:fs';
import { resolve, extname } from 'node:path';

const prefix = '/__reminders-demo/';
export function remindersDemoHandler(config, secure) {
  if (!secure || config.remindersDemo?.enabled !== true) return null;
  const root = config.remindersDemo.uiDirectory;
  if (root !== '/opt/pf1007l-reminders-bridge/ui') throw Error('Unexpected demo UI directory');
  const token = readFileSync(`${process.env.CREDENTIALS_DIRECTORY}/reminders-demo-key`, 'utf8').trim();
  if (token.length < 40) throw Error('Demo bridge credential required');
  return (req, res, url) => {
    if (!url.pathname.startsWith(prefix)) return false;
    const route = url.pathname.slice(prefix.length);
    const reply = (status, value) => {
      res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      res.end(JSON.stringify(value));
    };
    if (url.search) { reply(400, { error: 'Demo query strings unavailable' }); return true; }
    if (['session', 'snapshot', 'complete'].includes(route)) {
      if ((route === 'complete' ? req.method !== 'POST' : req.method !== 'GET')) {
        reply(405, { error: 'Method unavailable' }); return true;
      }
      let size = 0;
      const headers = { 'X-Pilot-Key': token, 'X-Pilot-Client': req.pilotRemote };
      for (const name of ['origin', 'cookie', 'content-type', 'content-length', 'x-pilot-csrf']) {
        if (req.headers[name]) headers[name] = req.headers[name];
      }
      const upstream = http.request({ hostname: '127.0.0.1', port: 5240, path: url.pathname,
        method: req.method, headers, timeout: 12000 }, response => {
        const fields = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };
        if (response.headers['set-cookie']) fields['Set-Cookie'] = response.headers['set-cookie'];
        res.writeHead(response.statusCode, fields); response.pipe(res);
      });
      upstream.on('timeout', () => upstream.destroy());
      upstream.on('error', () => { if (!res.headersSent) reply(503, { error: 'Demo tasks temporarily unavailable' }); else res.destroy(); });
      req.on('data', chunk => { size += chunk.length; if (size > 2048) { upstream.destroy(); req.destroy(); } });
      req.on('aborted', () => upstream.destroy()); req.pipe(upstream);
      return true;
    }
    if (!['GET', 'HEAD'].includes(req.method)) { reply(405, { error: 'Method unavailable' }); return true; }
    try {
      const file = resolve(root, route || 'index.html');
      if (!file.startsWith(root + '/') || !statSync(file).isFile()) throw Error();
      const type = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml',
        '.woff2': 'font/woff2', '.png': 'image/png', '.webp': 'image/webp' }[extname(file)];
      if (!type) throw Error();
      res.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'no-store' });
      res.end(req.method === 'HEAD' ? undefined : readFileSync(file));
    } catch { reply(404, { error: 'Demo asset unavailable' }); }
    return true;
  };
}
