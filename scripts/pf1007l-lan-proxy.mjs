#!/usr/bin/env node
// Restricted LAN bridge with optional HTTPS; upstream HTTPS is always verified.
// No access log, dashboard key in a client response, arbitrary upstream or XFF trust.
import http from 'node:http';
import https from 'node:https';
import net from 'node:net';
import { X509Certificate, createPrivateKey } from 'node:crypto';
import { readFileSync, statSync, lstatSync, unlinkSync, chmodSync } from 'node:fs';
import { createSecureContext } from 'node:tls';

const upstream = new URL('https://pf1007l-desk-dashboard.pages.dev');
const config = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const { bindAddress, port = 8788, allowedClients, healthClients = [] } = config;
const keyFile = config.keyFile || (process.env.CREDENTIALS_DIRECTORY && `${process.env.CREDENTIALS_DIRECTORY}/dashboard-key`);
const privateIPv4 = ip => net.isIPv4(ip) && (
  ip.startsWith('10.') || ip.startsWith('192.168.') ||
  (ip.startsWith('172.') && Number(ip.split('.')[1]) >= 16 && Number(ip.split('.')[1]) <= 31)
);
if (!privateIPv4(bindAddress) || !Number.isInteger(port) || port < 1024 || port > 65535 ||
    !Array.isArray(allowedClients) || !allowedClients.length ||
    allowedClients.some(ip => !privateIPv4(ip)) || !Array.isArray(healthClients) ||
    healthClients.some(ip => !privateIPv4(ip))) throw Error('Explicit private IPv4 bind/client configuration required');
const keyStat = statSync(keyFile);
// systemd uses a read-only per-unit credential mount and may use ACLs or
// namespace mappings that cannot be inferred from owner/group mode bits alone.
function isProtectedSystemdCredential(directory, file, mountInfo) {
  if (!/^\/run\/credentials\/[^/]+$/.test(directory) || (file.mode & 0o222)) return false;
  return mountInfo.split('\n').some(line => {
    const fields = line.split(' '), separator = fields.indexOf('-');
    return fields[4] === directory && separator > 0 &&
      fields[5].split(',').includes('ro') &&
      ['ramfs', 'tmpfs'].includes(fields[separator + 1]);
  });
}

// Ordinary key files require owner-only permissions. systemd credential files
// are protected by a read-only, per-unit RAM mount; ACL/namespace protection
// cannot reliably be inferred from UID/GID mode bits alone.
let protectedCredential = false;
if (!config.keyFile && process.platform === 'linux' && process.env.CREDENTIALS_DIRECTORY) {
  const directory = process.env.CREDENTIALS_DIRECTORY;
  protectedCredential = isProtectedSystemdCredential(directory, keyStat, readFileSync('/proc/self/mountinfo', 'utf8'));
}
if ((keyStat.mode & 0o077) !== 0 && !protectedCredential) throw Error('Key file must be private or on the read-only systemd credential mount');
const key = readFileSync(keyFile, 'utf8').trim();
if (key.length < 32) throw Error('Strong dashboard key required');
function checkedTls(privateKey, chain) {
  const leaf = new X509Certificate(chain);
  if (!leaf.checkHost(config.tls.hostname, { wildcards: false }) || !leaf.checkPrivateKey(createPrivateKey(privateKey)) ||
      Date.parse(leaf.validFrom) > Date.now() || Date.parse(leaf.validTo) <= Date.now()) {
    throw Error('TLS certificate hostname, validity or key mismatch');
  }
  const options = { key: privateKey, cert: chain, minVersion: 'TLSv1.2' };
  createSecureContext(options); // reject malformed chain/key before publication
  return options;
}
const secure = config.tls !== undefined;
let tlsOptions;
if (secure) {
  const { hostname } = config.tls;
  if (typeof hostname !== 'string' || hostname.length > 253 || !hostname.includes('.') ||
      !hostname.split('.').every(label => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(label)) || net.isIP(hostname)) {
    throw Error('A canonical DNS hostname is required for HTTPS');
  }
  const directory = process.env.CREDENTIALS_DIRECTORY;
  const privateKeyFile = config.tls.keyFile || (directory && `${directory}/tls-key`);
  const chainFile = config.tls.chainFile || (directory && `${directory}/tls-chain`);
  const privateStat = statSync(privateKeyFile);
  const protectedMount = !config.tls.keyFile && process.platform === 'linux' && directory &&
    isProtectedSystemdCredential(directory, privateStat, readFileSync('/proc/self/mountinfo', 'utf8'));
  if ((privateStat.mode & 0o077) && !protectedMount) throw Error('TLS private key must be private to the service');
  const privateKey = readFileSync(privateKeyFile);
  const chain = readFileSync(chainFile);
  tlsOptions = checkedTls(privateKey, chain);

}
if (process.argv.includes('--check-config')) {
  console.log('Proxy configuration and private credential access verified; no listener started.');
  process.exit(0);
}
const authority = `${secure ? config.tls.hostname : bindAddress}:${port}`;
const origin = `${secure ? 'https' : 'http'}://${authority}`;
const contentSecurityPolicy = `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' ${secure ? 'wss' : 'ws'}://${authority}; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`;
const stats = { requests: 0, denied: 0, upstreamResponses: 0, tlsVerified: 0, upgrades: 0, upstreamErrors: 0 };
const sockets = new Set();
const tunneledClients = new Map();
const agent = new https.Agent({ keepAlive: true, maxSockets: 8, maxFreeSockets: 2 });
const hopHeaders = new Set(['connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
  'te', 'trailer', 'transfer-encoding', 'upgrade', 'alt-svc', 'set-cookie', 'strict-transport-security']);

function deny(res, code = 403) {
  stats.denied++;
  res.writeHead(code, { 'Content-Type': 'text/plain', 'Cache-Control': 'no-store', 'Connection': 'close' });
  res.end('Request denied\n');
}
function unavailable(req, res) {
  const document = req.url === '/' || req.url?.startsWith('/?') || req.url?.startsWith('/index.html');
  res.writeHead(502, { 'Content-Type': document ? 'text/html; charset=utf-8' : 'application/json', 'Cache-Control': 'no-store' });
  res.end(document
    ? '<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="10"><title>Reconnecting</title><body style="background:#111;color:#ddd;font:24px sans-serif;padding:40px">Dashboard upstream unavailable. Retrying in 10 seconds.</body>'
    : JSON.stringify({ error: 'Upstream temporarily unavailable' }));
}
function parseAllowed(req) {
  const peer = req.socket.remoteAddress?.replace(/^::ffff:/, '');
  const remote = peer === bindAddress ? (tunneledClients.get(req.socket.remotePort)?.ip || peer) : peer;
  if (req.headers.host !== authority) return null;
  if (req.headers.origin && req.headers.origin !== origin) return null;
  if (req.headers['sec-fetch-site'] === 'cross-site') return null;
  if (!req.url?.startsWith('/') || req.url.startsWith('//') || req.url.includes('\\')) return null;
  let url;
  try { url = new URL(req.url, upstream); } catch { return null; }
  if (url.origin !== upstream.origin || url.searchParams.get('key')) return null;
  // Monitoring on the server must not grant other local services access to private APIs.
  const healthOnly = req.method === 'GET' && url.pathname === '/__proxy_health' && healthClients.includes(remote);
  if (!allowedClients.includes(remote) && !healthOnly) return null;
  url.searchParams.delete('key'); // frontend may send an empty ?key=; never propagate it
  if (!['GET', 'HEAD', 'POST'].includes(req.method)) return null;
  // Demo edits are local to the browser. Real cloud writes require a separate opt-in.
  if (req.method === 'POST' && config.allowApiWrites !== true) return null;
  if (req.method === 'POST' && !/^\/api\/(lists\/(todo|groceries)(\/[^/]+\/done)?|messages\/[^/]+\/dismiss)$/.test(url.pathname)) return null;
  return url;
}
function headersFor(req, url, upgrade = false) {
  const headers = { host: upstream.host, 'user-agent': 'Mozilla/5.0 PF1007L-LAN-Proxy/1.0', 'accept-encoding': 'identity' };
  for (const name of ['accept', 'content-type', 'content-length', 'range', 'if-none-match', 'if-modified-since']) {
    if (req.headers[name]) headers[name] = req.headers[name];
  }
  if (url.pathname.startsWith('/api/')) headers.authorization = 'Bearer ' + key;
  if (upgrade) {
    headers.connection = 'Upgrade'; headers.upgrade = 'websocket'; headers.origin = upstream.origin;
    for (const name of ['sec-websocket-key', 'sec-websocket-version', 'sec-websocket-protocol']) {
      if (req.headers[name]) headers[name] = req.headers[name];
    }
  }
  return headers;
}
function requestUpstream(req, url, upgrade = false) {
  const request = https.request({
    hostname: upstream.hostname, port: 443, servername: upstream.hostname,
    path: url.pathname + url.search, method: req.method,
    headers: headersFor(req, url, upgrade), agent,
    rejectUnauthorized: true, minVersion: 'TLSv1.2',
  });
  // Include DNS/connect/TLS in the deadline; socket inactivity alone misses DNS stalls.
  const deadline = setTimeout(() => request.destroy(), 15000);
  const clear = () => clearTimeout(deadline);
  request.once('response', clear); request.once('upgrade', clear);
  request.once('error', clear); request.once('close', clear);
  return request;
}
function responseHeaders(response) {
  const headers = {};
  for (const [name, value] of Object.entries(response.headers)) {
    if (!hopHeaders.has(name)) headers[name] = value;
  }
  if (headers.location) {
    const location = new URL(headers.location, upstream);
    if (location.origin !== upstream.origin) return null;
    headers.location = origin + location.pathname + location.search;
  }
  headers['referrer-policy'] = 'no-referrer';
  headers['x-content-type-options'] = 'nosniff';
  headers['cross-origin-resource-policy'] = 'same-origin';
  headers['content-security-policy'] = contentSecurityPolicy;
  return headers;
}
const handleRequest = (req, res) => {
  res.setHeader('Content-Security-Policy', contentSecurityPolicy);
  res.setHeader('X-Content-Type-Options', 'nosniff');
  stats.requests++;
  const url = parseAllowed(req);
  if (!url) return deny(res);
  if (url.pathname === '/__proxy_health') {
    res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
    return res.end(JSON.stringify({ ...stats, uptimeSeconds: process.uptime(), memory: process.memoryUsage(), cpu: process.cpuUsage() }));
  }
  // Permanent-host POC: even if live integrations are added upstream later, this
  // explicitly demo-only endpoint must never deliver their private data over HTTP.
  const liveWeather = secure && config.liveWeather === true && req.method === 'GET' && url.pathname === '/api/weather' && !url.search;
  if (config.demoOnly === true && url.pathname.startsWith('/api/') && !liveWeather) {
    const fixtures = {
      '/api/calendar': { events: [], calendars: 0, errors: [], updated: new Date().toISOString(), demo: true },
      '/api/photos': { photos: [], demo: true },
      '/api/messages': { messages: [], demo: true },
      '/api/weather': { error: 'Weather is not configured in this demo-only proxy', demo: true },
      '/api/lists/todo': { items: [], sections: [], people: {}, demo: true },
      '/api/lists/groceries': { items: [], sections: [], people: {}, demo: true },
    };
    const body = fixtures[url.pathname];
    res.writeHead(body ? 200 : 403, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
    return res.end(JSON.stringify(body || { error: 'API unavailable in demo-only mode' }));
  }
  let size = 0;
  req.on('data', chunk => { size += chunk.length; if (size > 65536) { req.destroy(); upstreamReq.destroy(); } });
  const upstreamReq = requestUpstream(req, url);
  upstreamReq.setTimeout(15000, () => upstreamReq.destroy());
  upstreamReq.on('response', response => {
    if (!response.socket.authorized) { response.destroy(); return deny(res, 502); }
    stats.tlsVerified++; stats.upstreamResponses++;
    const headers = responseHeaders(response);
    if (!headers) { response.destroy(); return deny(res, 502); }
    res.writeHead(response.statusCode, headers); response.pipe(res);
  });
  upstreamReq.on('error', () => {
    stats.upstreamErrors++;
    if (!res.headersSent) unavailable(req, res);
    else res.destroy();
  });
  req.on('aborted', () => upstreamReq.destroy());
  res.on('close', () => upstreamReq.destroy());
  req.pipe(upstreamReq);
};
const server = secure ? https.createServer(tlsOptions, handleRequest) : http.createServer(handleRequest);
// Optional single-target CONNECT bridge for this kiosk's app-only proxy. The
// browser performs normal end-to-end TLS; this listener cannot serve plaintext
// dashboard content or connect to arbitrary destinations. No X-Forwarded-For trust.
let connectServer;
if (secure && config.tls.connectProxyPort !== undefined) {
  const bridgePort = config.tls.connectProxyPort;
  if (!Number.isInteger(bridgePort) || bridgePort < 1024 || bridgePort > 65535 || bridgePort === port) throw Error('Invalid CONNECT bridge port');
  connectServer = http.createServer((_req, res) => { res.writeHead(403); res.end('CONNECT only'); });
  connectServer.headersTimeout = 5000;
  connectServer.on('connect', (req, client, head) => {
    const peer = client.remoteAddress?.replace(/^::ffff:/, '');
    if (!allowedClients.includes(peer) || req.url !== authority || req.headers.host !== authority) {
      client.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n'); return;
    }
    const remote = net.createConnection({ host: bindAddress, port, localAddress: bindAddress });
    sockets.add(remote); let remotePort;
    const identity = { ip: peer };
    remote.setTimeout(5000, () => remote.destroy());
    remote.on('connect', () => {
      remote.setTimeout(0); remotePort = remote.localPort;
      tunneledClients.set(remotePort, identity);
      client.write('HTTP/1.1 200 Connection Established\r\n\r\n');
      if (head.length) remote.write(head);
      client.pipe(remote); remote.pipe(client);
    });
    remote.on('error', () => client.destroy()); client.on('error', () => remote.destroy());
    client.on('close', () => remote.destroy());
    remote.on('close', () => {
      if (tunneledClients.get(remotePort) === identity) tunneledClients.delete(remotePort);
      sockets.delete(remote); client.destroy();
    });
  });
  connectServer.on('connection', socket => { sockets.add(socket); socket.on('close', () => sockets.delete(socket)); });
  connectServer.listen(bridgePort, bindAddress);
}
// Root certificate automation can reload only through this service-private Unix
// socket. It is never exposed on TCP; the 0700 runtime directory is the boundary.
let reloadServer;
if (secure && process.env.RUNTIME_DIRECTORY) {
  const runtime = process.env.RUNTIME_DIRECTORY;
  const directory = lstatSync(runtime);
  if (!directory.isDirectory() || directory.isSymbolicLink() || directory.uid !== process.getuid() || (directory.mode & 0o077)) {
    throw Error('Private service runtime directory required');
  }
  const socketPath = `${runtime}/reload.sock`;
  try { if (!lstatSync(socketPath).isSocket()) throw Error('Unexpected reload path'); unlinkSync(socketPath); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  reloadServer = http.createServer((req, res) => {
    if (req.method !== 'POST' || req.url !== '/reload') { res.writeHead(403); return res.end(); }
    let size = 0; const chunks = [];
    req.on('data', chunk => { size += chunk.length; if (size > 65536) req.destroy(); else chunks.push(chunk); });
    req.on('end', () => {
      try {
        const material = JSON.parse(Buffer.concat(chunks).toString('utf8'));
        const next = checkedTls(material.key, material.chain);
        server.setSecureContext(next); tlsOptions = next;
        res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('{"reloaded":true}');
      } catch { res.writeHead(400); res.end('Certificate reload rejected'); }
    });
  });
  reloadServer.requestTimeout = 5000;
  reloadServer.listen(socketPath, () => chmodSync(socketPath, 0o600));
}
server.on('connection', socket => { sockets.add(socket); socket.on('close', () => sockets.delete(socket)); });
// Diagnostic WSS traverses the actual authenticated cloud relay but exposes only
// its literal heartbeat response. Initial/live message payloads are discarded.
function pongOnly(write, close) {
  let buffer = Buffer.alloc(0);
  return chunk => {
    buffer = Buffer.concat([buffer, chunk]);
    while (buffer.length >= 2) {
      const first = buffer[0], second = buffer[1]; let offset = 2, size = second & 127;
      if ((second & 128) || (first & 112)) { close(); return; }
      if (size === 127) { close(); return; } // diagnostic has no large frames
      if (size === 126) { if (buffer.length < 4) return; size = buffer.readUInt16BE(2); offset = 4; }
      if (size > 65535 || buffer.length > 131072) { close(); return; }
      if (buffer.length < offset + size) return;
      const frame = buffer.subarray(0, offset + size), payload = frame.subarray(offset);
      if (first === 129 && payload.equals(Buffer.from('pong'))) write(frame);
      if ((first & 15) === 8) { close(); return; }
      buffer = buffer.subarray(offset + size);
    }
  };
}
server.on('upgrade', (req, socket, head) => {
  const url = parseAllowed(req);
  const reject = code => { stats.denied++; socket.end(`HTTP/1.1 ${code} Rejected\r\nConnection: close\r\n\r\n`); };
  const diagnostic = secure && config.demoOnly === true && url?.pathname === '/__proxy_ws_check';
  if (diagnostic) url.pathname = '/api/messages/live';
  if ((config.demoOnly === true && !diagnostic) || !url || url.pathname !== '/api/messages/live' || req.headers.origin !== origin || req.headers.upgrade?.toLowerCase() !== 'websocket') return reject(403);
  const upstreamReq = requestUpstream(req, url, true);
  upstreamReq.setTimeout(15000, () => upstreamReq.destroy());
  upstreamReq.on('upgrade', (response, remote, upstreamHead) => {
    if (!remote.authorized) { remote.destroy(); return reject(502); }
    stats.tlsVerified++; stats.upgrades++;
    remote.setTimeout(0); socket.setTimeout(0);
    const headers = { ...response.headers, connection: 'Upgrade', upgrade: 'websocket' };
    delete headers['set-cookie']; delete headers['alt-svc'];
    socket.write('HTTP/1.1 101 Switching Protocols\r\n' + Object.entries(headers).map(([k, v]) => `${k}: ${v}`).join('\r\n') + '\r\n\r\n');
    if (diagnostic) {
      const filter = pongOnly(frame => socket.write(frame), () => { socket.destroy(); remote.destroy(); });
      remote.on('data', filter);
      if (upstreamHead.length) filter(upstreamHead);
    } else {
      if (upstreamHead.length) socket.write(upstreamHead);
      remote.pipe(socket);
    }
    if (head.length) remote.write(head);
    socket.pipe(remote);
    remote.on('error', () => socket.destroy()); socket.on('error', () => remote.destroy());
    socket.on('close', () => remote.destroy()); remote.on('close', () => socket.destroy());
  });
  upstreamReq.on('response', response => { response.resume(); reject(response.statusCode || 502); });
  upstreamReq.on('error', () => { stats.upstreamErrors++; if (!socket.destroyed) reject(502); });
  upstreamReq.end();
});
server.requestTimeout = 20000;
server.headersTimeout = 10000;
server.maxHeadersCount = 40;
server.listen(port, bindAddress, () => console.log(`LAN proof-of-concept listening on ${origin}; explicit IP/Host/Origin checks; no access log.`));
function shutdown() { connectServer?.close(); reloadServer?.close(); server.close(); for (const socket of sockets) socket.destroy(); agent.destroy(); }
process.on('SIGTERM', shutdown); process.on('SIGINT', shutdown);
