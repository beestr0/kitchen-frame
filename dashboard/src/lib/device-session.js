// Native credentials never enter JS: the native bridge installs an HttpOnly cookie.
export function requestNativeSession(channel = globalThis.FrameDeviceAuth, timeoutMs = 35000) {
  if (!channel || typeof channel.postMessage !== 'function') return Promise.reject(new Error('Device enrollment is required'));
  return new Promise((resolve, reject) => {
    const previous = channel.onmessage;
    const finish = (error) => {
      clearTimeout(timer); channel.onmessage = previous;
      error ? reject(error) : resolve();
    };
    const timer = setTimeout(() => finish(new Error('Device authentication timed out')), timeoutMs);
    channel.onmessage = (event) => {
      if (event.data === 'ready') finish();
      else if (event.data === 'unavailable') finish(new Error('Device authentication unavailable'));
    };
    try { channel.postMessage('renew'); } catch { finish(new Error('Device authentication unavailable')); }
  });
}

export function createDeviceSession({ request, authenticate = requestNativeSession,
  clock = () => globalThis.performance?.now?.() ?? Date.now() }) {
  let session = null, renewAt = 0, pending = null, retryAt = 0;
  async function ensure(force = false) {
    if (pending) return pending;
    if (!force && session && clock() < renewAt) return session;
    if (clock() < retryAt) throw new Error('Device authentication is recovering; retry shortly');
    pending = (async () => {
      await Promise.resolve(); // install pending before even a synchronous transport failure
      let next;
      try {
        try { next = await request('session'); }
        catch (error) {
          if (error.status !== 401 || error.mode !== 'device-v1') throw error;
          await authenticate();
          next = await request('session');
        }
        if (next.mode === 'device-v1' && Number(next.expiresIn) <= 180) {
          await authenticate();
          next = await request('session');
        }
        if (typeof next.csrf !== 'string' || !next.csrf || !['device-v1', 'legacy-demo', undefined].includes(next.mode)) throw new Error('Invalid session response');
        const ttl = next.expiresIn === undefined ? 300 : Number(next.expiresIn);
        if (!Number.isFinite(ttl) || ttl <= 0 || ttl > 86400) throw new Error('Invalid session expiry');
        session = next;
        // Use relative server lifetime, not the Android wall-clock for proof validation.
        renewAt = clock() + Math.max(1, Math.min(ttl * 0.8, ttl - 120)) * 1000;
        retryAt = 0;
        return session;
      } catch (error) {
        session = null; renewAt = 0; retryAt = clock() + 15000;
        throw error;
      } finally { pending = null; }
    })();
    return pending;
  }
  async function perform(route, init = {}) {
    const invoke = async () => {
      const value = await ensure();
      return request(route, { ...init, headers: { ...(init.headers || {}),
        ...(init.method === 'POST' ? { 'X-Pilot-CSRF': value.csrf } : {}) } });
    };
    try { return await invoke(); }
    catch (error) {
      // A server middleware 401 means no task handler/write ran. Retry exactly
      // once after renewal, preserving the original operation ID/body. Never
      // replay a timeout, 409, 429 or 5xx whose write outcome may be uncertain.
      if (error.status !== 401 || error.mode !== 'device-v1' || error.code !== 'device_auth_required') throw error;
      session = null; renewAt = 0;
      await ensure(true);
      return invoke();
    }
  }
  return { ensure, request: perform, invalidate() { session = null; renewAt = 0; } };
}
