/**
 * AI Task Tracker — App Core
 * Router, global state, toast notifications, modal manager
 */

// ── Global State ──────────────────────────────────────────────────────────────
const Store = {
  user: null,
  dashboardStats: null,
  notifications: [],
  unreadCount: 0,

  set(key, val) { this[key] = val; },
  get(key) { return this[key]; },
};

// ── Toast ─────────────────────────────────────────────────────────────────────
const Toast = {
  _container: null,

  init() {
    this._container = document.getElementById('toast-container');
  },

  show(type, title, message = '', duration = 4000) {
    const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `
      <span class="toast-icon">${icons[type] || 'ℹ'}</span>
      <div class="toast-body">
        <div class="toast-title">${title}</div>
        ${message ? `<div class="toast-msg">${message}</div>` : ''}
      </div>
      <button class="toast-close" onclick="Toast.remove(this.closest('.toast'))">✕</button>
    `;
    this._container.appendChild(el);
    if (duration > 0) setTimeout(() => this.remove(el), duration);
    return el;
  },

  remove(el) {
    if (!el || el.classList.contains('removing')) return;
    el.classList.add('removing');
    setTimeout(() => el.remove(), 300);
  },

  success(title, msg) { return this.show('success', title, msg); },
  error(title, msg)   { return this.show('error', title, msg); },
  warning(title, msg) { return this.show('warning', title, msg); },
  info(title, msg)    { return this.show('info', title, msg); },
};

// ── Modal Manager ─────────────────────────────────────────────────────────────
const Modal = {
  _stack: [],

  open(id) {
    const overlay = document.getElementById(id);
    if (!overlay) return;
    overlay.classList.add('active');
    this._stack.push(id);
    document.body.style.overflow = 'hidden';
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) this.close(id);
    }, { once: true });
  },

  close(id) {
    const overlay = document.getElementById(id);
    if (!overlay) return;
    overlay.classList.remove('active');
    this._stack = this._stack.filter(i => i !== id);
    if (this._stack.length === 0) document.body.style.overflow = '';
  },

  closeTop() {
    if (this._stack.length) this.close(this._stack[this._stack.length - 1]);
  },
};

// ── Router ────────────────────────────────────────────────────────────────────
const Router = {
  routes: {},
  currentPage: null,

  register(hash, handler) {
    this.routes[hash] = handler;
  },

  navigate(hash) {
    window.location.hash = hash;
  },

  init() {
    window.addEventListener('hashchange', () => this._resolve());
    this._resolve();
  },

  async _resolve() {
    const hash = window.location.hash || '#/dashboard';

    // Auth guard
    if (!api.isAuthenticated() && hash !== '#/login' && hash !== '#/register') {
      window.location.hash = '#/login';
      return;
    }
    if (api.isAuthenticated() && (hash === '#/login' || hash === '#/register')) {
      window.location.hash = '#/dashboard';
      return;
    }

    const handler = this.routes[hash];
    if (handler) {
      await handler();
      this._setActiveNav(hash);
    } else {
      // Default to dashboard
      window.location.hash = '#/dashboard';
    }
  },

  _setActiveNav(hash) {
    document.querySelectorAll('.nav-item').forEach(el => {
      el.classList.toggle('active', el.dataset.route === hash);
    });
    // Update header title
    const titles = {
      '#/dashboard': ['Dashboard', 'Your productivity overview'],
      '#/tasks': ['Tasks', 'Manage your tasks'],
      '#/milestones': ['Milestones', 'Track your goals'],
      '#/ai-suggestions': ['AI Suggestions', 'Smart recommendations'],
      '#/notifications': ['Notifications', 'Stay informed'],
      '#/analytics': ['Analytics', 'Productivity insights'],
      '#/settings': ['Settings', 'Preferences & account'],
      '#/admin': ['Admin Panel', 'User & system management'],
    };
    const [title, subtitle] = titles[hash] || ['Dashboard', ''];
    const titleEl = document.querySelector('.header-page-title');
    const subtitleEl = document.querySelector('.header-page-subtitle');
    if (titleEl) titleEl.textContent = title;
    if (subtitleEl) subtitleEl.textContent = subtitle;
  },
};

// ── Auth helpers ──────────────────────────────────────────────────────────────
async function loadCurrentUser() {
  try {
    const cached = localStorage.getItem('current_user');
    if (cached) { Store.set('user', JSON.parse(cached)); return; }
    const user = await api.getMe();
    Store.set('user', user);
    localStorage.setItem('current_user', JSON.stringify(user));
    updateSidebarUser(user);
  } catch { /* handled by auth guard */ }
}

function updateSidebarUser(user) {
  const nameEl = document.querySelector('.user-name');
  const roleEl = document.querySelector('.user-role');
  const avatarEl = document.querySelector('.user-avatar');
  if (nameEl) nameEl.textContent = user.full_name || user.username;
  if (roleEl) roleEl.textContent = user.is_admin ? 'Administrator' : 'Member';
  if (avatarEl) avatarEl.textContent = (user.full_name || user.username)[0].toUpperCase();
  // Show admin nav
  if (user.is_admin) {
    document.querySelectorAll('[data-admin-only]').forEach(el => el.classList.remove('hidden'));
  }
}

async function loadUnreadCount() {
  try {
    const res = await api.getUnreadCount();
    const count = res?.data?.count || 0;
    Store.set('unreadCount', count);
    const badge = document.querySelector('.nav-badge[data-for="notifications"]');
    const dot = document.querySelector('.header-btn .notif-dot');
    if (badge) { badge.textContent = count; badge.style.display = count > 0 ? 'flex' : 'none'; }
    if (dot) dot.style.display = count > 0 ? 'block' : 'none';
  } catch {}
}

// ── Utility helpers ───────────────────────────────────────────────────────────
function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = d - now;
  const days = Math.ceil(diff / 86400000);
  if (days === 0) return 'Today';
  if (days === 1) return 'Tomorrow';
  if (days === -1) return 'Yesterday';
  if (days < 0) return `${Math.abs(days)}d overdue`;
  if (days < 7) return `In ${days}d`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatRelative(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const sec = Math.floor((now - d) / 1000);
  if (sec < 60)   return 'just now';
  if (sec < 3600) return `${Math.floor(sec/60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec/3600)}h ago`;
  return `${Math.floor(sec/86400)}d ago`;
}

function priorityBadge(p) {
  const map = { low: 'badge-low', medium: 'badge-medium', high: 'badge-high', urgent: 'badge-urgent' };
  return `<span class="badge ${map[p] || 'badge-low'}">${p}</span>`;
}

function statusBadge(s) {
  const map = {
    todo: 'badge-todo', in_progress: 'badge-progress', completed: 'badge-done',
    on_hold: 'badge-hold', cancelled: 'badge-cancelled', overdue: 'badge-overdue',
  };
  const labels = { todo: 'To Do', in_progress: 'In Progress', completed: 'Done', on_hold: 'On Hold', cancelled: 'Cancelled' };
  return `<span class="badge ${map[s] || 'badge-todo'}">${labels[s] || s}</span>`;
}

function categoryIcon(c) {
  const map = { work: '💼', personal: '🏠', health: '💪', learning: '📚', finance: '💰', other: '📌' };
  return map[c] || '📌';
}

function isOverdue(dueDate) {
  return dueDate && new Date(dueDate) < new Date();
}

function isDueSoon(dueDate) {
  if (!dueDate) return false;
  const d = new Date(dueDate);
  const now = new Date();
  return d > now && (d - now) < 86400000 * 3;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}

async function withLoading(btn, fn) {
  const original = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>';
  try { await fn(); }
  finally { btn.disabled = false; btn.innerHTML = original; }
}

function debounce(fn, ms = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ── Keyboard shortcuts ────────────────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') Modal.closeTop();
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    document.querySelector('.header-search input')?.focus();
  }
});

// ── Mobile sidebar ────────────────────────────────────────────────────────────
function initMobileSidebar() {
  const btn = document.querySelector('.mobile-menu-btn');
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');
  const close = () => { sidebar?.classList.remove('open'); overlay?.classList.remove('active'); };
  btn?.addEventListener('click', () => { sidebar?.classList.toggle('open'); overlay?.classList.toggle('active'); });
  overlay?.addEventListener('click', close);
  document.querySelectorAll('.nav-item').forEach(el => el.addEventListener('click', close));
}

// ── App Boot ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  Toast.init();
  initMobileSidebar();

  if (api.isAuthenticated()) {
    await loadCurrentUser();
    loadUnreadCount();
    // Refresh unread count every 60s
    setInterval(loadUnreadCount, 60000);
  }

  Router.init();
});
