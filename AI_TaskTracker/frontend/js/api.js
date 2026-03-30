/**
 * API Client  —  AI Task Tracker v3
 * All HTTP calls to the FastAPI backend.
 * Auto-attaches JWT, handles 401 → token refresh.
 */
const API = (() => {
  const BASE = '/api/v1';

  // ── Token storage ─────────────────────────────────────────
  const tokens = {
    get access()  { return localStorage.getItem('access_token'); },
    get refresh() { return localStorage.getItem('refresh_token'); },
    set(access, refresh) {
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
    },
    clear() {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
    },
    isLoggedIn() { return !!this.access; },
  };

  let _refreshing = null; // prevent concurrent refreshes

  // ── Core fetch ────────────────────────────────────────────
  async function request(method, path, body = null, retry = true) {
    const headers = { 'Content-Type': 'application/json' };
    if (tokens.access) headers['Authorization'] = `Bearer ${tokens.access}`;

    let res;
    try {
      res = await fetch(`${BASE}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch {
      throw new Error('Cannot connect to server. Is the backend running?');
    }

    if (res.status === 401 && retry && tokens.refresh) {
      await _doRefresh();
      return request(method, path, body, false);
    }

    if (res.status === 204) return null;

    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.detail || data?.message || `Error ${res.status}`);
    return data;
  }

  async function _doRefresh() {
    if (_refreshing) return _refreshing;
    _refreshing = (async () => {
      try {
        const data = await request('POST', '/auth/refresh',
          { refresh_token: tokens.refresh }, false);
        tokens.set(data.access_token, data.refresh_token);
      } catch {
        tokens.clear();
        window.location.hash = '#login';
      } finally {
        _refreshing = null;
      }
    })();
    return _refreshing;
  }

  const get   = p       => request('GET',    p);
  const post  = (p, b)  => request('POST',   p, b);
  const patch = (p, b)  => request('PATCH',  p, b);
  const del   = p       => request('DELETE', p);
  const getQ  = (p, params) => {
    const q = new URLSearchParams(
      Object.fromEntries(
        Object.entries(params).filter(([, v]) => v != null && v !== '')
      )
    ).toString();
    return get(q ? `${p}?${q}` : p);
  };

  // ── Auth ──────────────────────────────────────────────────
  const auth = {
    register: d  => post('/auth/register', d),
    login:    d  => post('/auth/login', d),
    logout:   () => post('/auth/logout', {}),
    me:       () => get('/auth/me'),
    refresh:  rt => post('/auth/refresh', { refresh_token: rt }),
  };

  // ── Users ─────────────────────────────────────────────────
  const users = {
    updateMe:       d => patch('/users/me', d),
    changePassword: d => post('/users/me/change-password', d),
    deleteMe:       () => del('/users/me'),
  };

  // ── Tasks ─────────────────────────────────────────────────
  const tasks = {
    list:    p      => getQ('/tasks', p || {}),
    get:     id     => get(`/tasks/${id}`),
    create:  d      => post('/tasks', d),
    update:  (id,d) => patch(`/tasks/${id}`, d),
    archive: id     => post(`/tasks/${id}/archive`, {}),
    delete:  id     => del(`/tasks/${id}`),
  };

  // ── Subtasks ──────────────────────────────────────────────
  const subtasks = {
    list:   taskId          => get(`/tasks/${taskId}/subtasks`),
    create: (taskId, d)     => post(`/tasks/${taskId}/subtasks`, d),
    update: (taskId, id, d) => patch(`/tasks/${taskId}/subtasks/${id}`, d),
    delete: (taskId, id)    => del(`/tasks/${taskId}/subtasks/${id}`),
  };

  // ── Push ──────────────────────────────────────────────────
  const push = {
    vapidKey:    () => get('/push/vapid-key'),
    subscribe:   d  => post('/push/subscribe', d),
    unsubscribe: d  => post('/push/unsubscribe', d),
    test:        () => post('/push/test', {}),
  };

  return { tokens, auth, users, tasks, subtasks, push };
})();

window.API = API;
