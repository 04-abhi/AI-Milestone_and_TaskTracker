/**
 * App Core  —  AI Task Tracker v3
 * Theme · Toast · Modal · Router · State · Helpers
 *
 * ⚠  IMPORTANT: Router.init() is called at the BOTTOM of pages.js,
 *    AFTER all route handlers are registered. Do NOT call it here.
 */

// ── Global state ──────────────────────────────────────────
const State = {
  user: null,
  load() {
    const u = localStorage.getItem('user');
    this.user = u ? JSON.parse(u) : null;
  },
  save(user) {
    this.user = user;
    localStorage.setItem('user', JSON.stringify(user));
  },
  clear() {
    this.user = null;
    localStorage.removeItem('user');
  },
};

// ── Theme ─────────────────────────────────────────────────
const Theme = {
  get() { return localStorage.getItem('theme') || 'dark'; },
  set(t) {
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem('theme', t);
    const btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = t === 'dark' ? '☀️' : '🌙';
    // sync settings dropdown if open
    const sel = document.getElementById('s-theme');
    if (sel) sel.value = t;
  },
  toggle() {
    const next = this.get() === 'dark' ? 'light' : 'dark';
    this.set(next);
    if (API.tokens.isLoggedIn()) {
      API.users.updateMe({ theme: next }).catch(() => {});
    }
  },
  init() {
    this.set(State.user?.theme || this.get());
  },
};

// ── Toast ─────────────────────────────────────────────────
const Toast = {
  show(type, message, duration = 3500) {
    const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `
      <span class="toast-icon">${icons[type] || 'ℹ'}</span>
      <span class="toast-msg">${message}</span>
    `;
    document.getElementById('toasts').appendChild(el);
    setTimeout(() => {
      el.classList.add('out');
      setTimeout(() => el.remove(), 300);
    }, duration);
  },
  success: m => Toast.show('success', m),
  error:   m => Toast.show('error',   m),
  info:    m => Toast.show('info',    m),
  warning: m => Toast.show('warning', m),
};

// ── Modal ─────────────────────────────────────────────────
const Modal = {
  open(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.add('open');
    document.body.style.overflow = 'hidden';
    // close on backdrop click
    const handler = e => { if (e.target === el) this.close(id); };
    el.addEventListener('click', handler, { once: true });
  },
  close(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('open');
    document.body.style.overflow = '';
  },
  closeAll() {
    document.querySelectorAll('.modal-bg.open').forEach(m => {
      m.classList.remove('open');
    });
    document.body.style.overflow = '';
  },
};

// ── Loading button helper ─────────────────────────────────
async function withBtn(btn, fn) {
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span>';
  try { await fn(); }
  finally { btn.disabled = false; btn.innerHTML = orig; }
}

// ── Date helpers ──────────────────────────────────────────
function fmtDate(d) {
  if (!d) return '';
  const dt  = new Date(d);
  const now = new Date();
  // Compare calendar dates only (strip time) so "Today at 5 PM" shows Today not Tomorrow
  const dtDay  = new Date(dt.getFullYear(),  dt.getMonth(),  dt.getDate());
  const nowDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diff   = Math.round((dtDay - nowDay) / 86400000);
  if (diff === 0)  return 'Today';
  if (diff === 1)  return 'Tomorrow';
  if (diff === -1) return 'Yesterday';
  if (diff < 0)    return `${Math.abs(diff)}d overdue`;
  if (diff < 7)    return `In ${diff}d`;
  return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

function fmtDateTime(d) {
  if (!d) return '';
  return new Date(d).toLocaleString('en-GB', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

function isOverdue(d) { return d && new Date(d) < new Date(); }
function isSoon(d) {
  if (!d) return false;
  const dt = new Date(d), now = new Date();
  return dt > now && (dt - now) < 3 * 86400000; // within 3 days
}

// XSS-safe escape
function esc(s) {
  const d = document.createElement('div');
  d.textContent = s || '';
  return d.innerHTML;
}

// ── Router ────────────────────────────────────────────────
const Router = {
  routes: {},
  register(hash, fn) { this.routes[hash] = fn; },

  init() {
    window.addEventListener('hashchange', () => this._go());
    this._go(); // handle current hash on page load
  },

  navigate(hash) {
    // Ensure hash starts with #
    window.location.hash = hash.startsWith('#') ? hash : `#${hash}`;
  },

  _go() {
    const raw  = window.location.hash; // e.g. "#dashboard"
    const hash = (raw.startsWith('#') ? raw.slice(1) : raw) || 'dashboard';

    // Guard: not logged in
    if (!API.tokens.isLoggedIn() && hash !== 'login' && hash !== 'register') {
      this.navigate('#login');
      return;
    }
    // Guard: already logged in, skip auth pages
    if (API.tokens.isLoggedIn() && (hash === 'login' || hash === 'register')) {
      this.navigate('#dashboard');
      return;
    }

    const fn = this.routes[hash];
    if (fn) {
      fn();
    } else if (API.tokens.isLoggedIn()) {
      this.navigate('#dashboard');
    } else {
      this.navigate('#login');
    }

    // Update active nav link
    document.querySelectorAll('.nav-link[data-route]').forEach(el => {
      el.classList.toggle('active', el.dataset.route === hash);
    });

    // Update header title
    const titles = { dashboard: 'Dashboard', tasks: 'My Tasks', settings: 'Settings' };
    const titleEl = document.querySelector('.header-title');
    if (titleEl) titleEl.textContent = titles[hash] || '';
  },
};

// ── Mobile sidebar ────────────────────────────────────────
function initMobile() {
  const btn     = document.getElementById('mob-btn');
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');
  const close   = () => {
    sidebar?.classList.remove('open');
    if (overlay) overlay.style.display = 'none';
  };

  btn?.addEventListener('click', () => {
    const open = sidebar?.classList.toggle('open');
    if (overlay) overlay.style.display = open ? 'block' : 'none';
  });
  overlay?.addEventListener('click', close);
  document.querySelectorAll('.nav-link').forEach(l => l.addEventListener('click', close));
}

// ── Keyboard shortcuts ────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') Modal.closeAll();

  // 'N' anywhere in the app → new task (when not typing in an input)
  const tag = document.activeElement?.tagName;
  if (e.key === 'n' && tag !== 'INPUT' && tag !== 'TEXTAREA' && tag !== 'SELECT') {
    if (API.tokens.isLoggedIn()) {
      Tasks.openCreate();
    }
  }
});

// ── Boot ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  State.load();
  Theme.init();
  initMobile();
  // Router.init() is called at the bottom of pages.js after all routes are registered
});
