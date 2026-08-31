import { session } from './stores.js';

const BASE = import.meta.env.VITE_API_BASE ?? '/api';

export class ApiError extends Error {
  /** @param {number} status @param {string} detail @param {any} [data] */
  constructor(status, detail, data) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.data = data;
  }
}

/**
 * Thin fetch wrapper. Auth rides on an httpOnly cookie, so every call just needs
 * credentials:'include'. Nothing is cached client-side (spec 11.2) — no storage,
 * and the API already sends Cache-Control: no-store.
 * @param {string} path
 * @param {{ method?: string, body?: any, query?: Record<string, any> }} [opts]
 */
export async function api(path, opts = {}) {
  const { method = 'GET', body, query } = opts;
  let url = BASE + path;
  if (query) {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null && v !== '') q.set(k, v);
    const s = q.toString();
    if (s) url += '?' + s;
  }

  const init = { method, credentials: 'include', headers: {} };
  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(url, init);
  } catch {
    throw new ApiError(0, 'network');
  }

  if (res.status === 401) {
    session.set(null);
    throw new ApiError(401, 'unauthorized');
  }
  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty / non-json */
  }
  if (!res.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : res.statusText;
    throw new ApiError(res.status, detail, data);
  }
  return data;
}
