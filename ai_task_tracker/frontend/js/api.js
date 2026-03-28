/**
 * AI Task Tracker — API Client
 * Handles all communication with the FastAPI backend.
 */

const API_BASE = '/api/v1';

class ApiClient {
  constructor() {
    this._accessToken = localStorage.getItem('access_token');
    this._refreshToken = localStorage.getItem('refresh_token');
    this._refreshing = null;
  }

  // ── Token management ────────────────────────────────────────────────────────

  setTokens({ access_token, refresh_token }) {
    this._accessToken = access_token;
    this._refreshToken = refresh_token;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
  }

  clearTokens() {
    this._accessToken = null;
    this._refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('current_user');
  }

  isAuthenticated() {
    return !!this._accessToken;
  }

  // ── Core fetch wrapper ───────────────────────────────────────────────────────

  async _fetch(path, options = {}, retry = true) {
    const url = `${API_BASE}${path}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(this._accessToken ? { Authorization: `Bearer ${this._accessToken}` } : {}),
      ...(options.headers || {}),
    };

    let resp;
    try {
      resp = await fetch(url, { ...options, headers });
    } catch (err) {
      throw new Error('Network error — is the backend running?');
    }

    // Token expired → try refresh once
    if (resp.status === 401 && retry && this._refreshToken) {
      await this._doRefresh();
      return this._fetch(path, options, false);
    }

    const data = await resp.json().catch(() => ({}));

    if (!resp.ok) {
      const msg = data?.error?.message || data?.detail || `HTTP ${resp.status}`;
      throw new ApiError(msg, resp.status, data?.error?.code);
    }

    return data;
  }

  async _doRefresh() {
    // Prevent concurrent refreshes
    if (this._refreshing) return this._refreshing;
    this._refreshing = (async () => {
      try {
        const data = await this._fetch(
          '/auth/refresh',
          { method: 'POST', body: JSON.stringify({ refresh_token: this._refreshToken }) },
          false
        );
        this.setTokens(data);
      } catch {
        this.clearTokens();
        window.location.hash = '#/login';
      } finally {
        this._refreshing = null;
      }
    })();
    return this._refreshing;
  }

  get(path, params) {
    const url = params ? `${path}?${new URLSearchParams(params)}` : path;
    return this._fetch(url, { method: 'GET' });
  }
  post(path, body)   { return this._fetch(path, { method: 'POST',   body: JSON.stringify(body) }); }
  patch(path, body)  { return this._fetch(path, { method: 'PATCH',  body: JSON.stringify(body) }); }
  delete(path)       { return this._fetch(path, { method: 'DELETE' }); }

  // ── Auth ─────────────────────────────────────────────────────────────────────
  login(email, password, device_info = null)    { return this.post('/auth/login', { email, password, device_info }); }
  register(username, email, password, full_name) { return this.post('/auth/register', { username, email, password, full_name }); }
  logout()                                        { return this.post('/auth/logout', { refresh_token: this._refreshToken }); }
  getMe()                                         { return this.get('/auth/me'); }

  // ── Users ─────────────────────────────────────────────────────────────────────
  updateProfile(data)         { return this.patch('/users/me', data); }
  changePassword(cp, np)      { return this.post('/users/me/change-password', { current_password: cp, new_password: np }); }

  // ── Tasks ─────────────────────────────────────────────────────────────────────
  getTasks(params)             { return this.get('/tasks', params); }
  getTask(id)                  { return this.get(`/tasks/${id}`); }
  createTask(data)             { return this.post('/tasks', data); }
  updateTask(id, data)         { return this.patch(`/tasks/${id}`, data); }
  updateTaskStatus(id, status) { return this.patch(`/tasks/${id}/status`, { status }); }
  deleteTask(id)               { return this.delete(`/tasks/${id}`); }
  bulkDeleteTasks(ids)         { return this.post('/tasks/bulk-delete', { task_ids: ids }); }

  // ── Subtasks ──────────────────────────────────────────────────────────────────
  getSubtasks(taskId)               { return this.get(`/tasks/${taskId}/subtasks`); }
  createSubtask(taskId, data)        { return this.post(`/tasks/${taskId}/subtasks`, data); }
  updateSubtask(taskId, id, data)    { return this.patch(`/tasks/${taskId}/subtasks/${id}`, data); }
  deleteSubtask(taskId, id)          { return this.delete(`/tasks/${taskId}/subtasks/${id}`); }

  // ── Milestones ────────────────────────────────────────────────────────────────
  getMilestones(params)     { return this.get('/milestones', params); }
  getMilestone(id)          { return this.get(`/milestones/${id}`); }
  createMilestone(data)     { return this.post('/milestones', data); }
  updateMilestone(id, data) { return this.patch(`/milestones/${id}`, data); }
  deleteMilestone(id)       { return this.delete(`/milestones/${id}`); }

  // ── Notifications ─────────────────────────────────────────────────────────────
  getNotifications(params)   { return this.get('/notifications', params); }
  getUnreadCount()           { return this.get('/notifications/unread-count'); }
  markNotifRead(id)          { return this.patch(`/notifications/${id}/read`, {}); }
  markAllNotifsRead()        { return this.post('/notifications/mark-all-read', {}); }
  deleteNotif(id)            { return this.delete(`/notifications/${id}`); }

  // ── AI Suggestions ────────────────────────────────────────────────────────────
  getSuggestions(params)     { return this.get('/ai-suggestions', params); }
  generateSuggestions()      { return this.post('/ai-suggestions/generate', {}); }
  feedbackSuggestion(id, st) { return this.patch(`/ai-suggestions/${id}/feedback`, { status: st }); }
  markSuggestionRead(id)     { return this.patch(`/ai-suggestions/${id}/read`, {}); }

  // ── Dashboard ─────────────────────────────────────────────────────────────────
  getDashboardStats()            { return this.get('/dashboard/stats'); }
  getProductivitySummary(days)   { return this.get('/dashboard/productivity', { days }); }

  // ── Admin ─────────────────────────────────────────────────────────────────────
  adminListUsers(params)       { return this.get('/admin/users', params); }
  adminGetUser(id)             { return this.get(`/admin/users/${id}`); }
  adminUpdateUser(id, data)    { return this.patch(`/admin/users/${id}`, data); }
  adminDeleteUser(id)          { return this.delete(`/admin/users/${id}`); }
  adminGetStats()              { return this.get('/admin/stats'); }
}

class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const api = new ApiClient();
window.api = api;
