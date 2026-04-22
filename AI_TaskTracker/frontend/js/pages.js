/**
 * Pages  —  AI Task Tracker v3
 * Home · Login · Register · Dashboard (+ onboarding) · Tasks · Calendar · Settings
 */

// ════════════════════════════════════════════════════════
// AUTH HELPERS
// ════════════════════════════════════════════════════════
function showHome() {
  document.getElementById('auth-section').classList.remove('hidden');
  document.getElementById('app-section').classList.add('hidden');
  document.getElementById('home-box').classList.remove('hidden');
  document.getElementById('login-box').classList.add('hidden');
  document.getElementById('register-box').classList.add('hidden');
}

function showLogin() {
  document.getElementById('auth-section').classList.remove('hidden');
  document.getElementById('app-section').classList.add('hidden');
  document.getElementById('home-box').classList.add('hidden');
  document.getElementById('login-box').classList.remove('hidden');
  document.getElementById('register-box').classList.add('hidden');
}

function showRegister() {
  document.getElementById('home-box').classList.add('hidden');
  document.getElementById('login-box').classList.add('hidden');
  document.getElementById('register-box').classList.remove('hidden');
}

async function doLogin() {
  const btn      = document.getElementById('login-btn');
  const email    = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  if (!email || !password) { Toast.warning('Please fill in all fields'); return; }

  await withBtn(btn, async () => {
    try {
      const res = await API.auth.login({ email, password });
      API.tokens.set(res.access_token, res.refresh_token);
      State.save(res.user);
      Theme.set(res.user.theme || 'dark');
      afterLogin();
    } catch (e) {
      Toast.error(e.message);
    }
  });
}

async function doRegister() {
  const btn      = document.getElementById('register-btn');
  const username = document.getElementById('reg-username').value.trim();
  const email    = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  const fullName = document.getElementById('reg-fullname').value.trim();

  if (!username || !email || !password) {
    Toast.warning('Username, email and password are required');
    return;
  }

  await withBtn(btn, async () => {
    try {
      await API.auth.register({ username, email, password, full_name: fullName || null });
      Toast.success('Account created! Signing you in…');
      // Auto-login after register
      const res = await API.auth.login({ email, password });
      API.tokens.set(res.access_token, res.refresh_token);
      State.save(res.user);
      Theme.set(res.user.theme || 'dark');
      afterLogin(true); // true = first login, show onboarding
    } catch (e) {
      Toast.error(e.message);
    }
  });
}

function afterLogin(isNewUser = false) {
  document.getElementById('auth-section').classList.add('hidden');
  document.getElementById('app-section').classList.remove('hidden');
  _updateSidebarUser(State.user);
  Router.navigate('#dashboard');
  PushManager.init();
  if (isNewUser) {
    // Show onboarding after tasks load
    setTimeout(() => Onboarding.show(), 800);
  }
}

async function doLogout() {
  try { await API.auth.logout(); } catch { /* ignore */ }
  API.tokens.clear();
  State.clear();
  document.getElementById('app-section').classList.add('hidden');
  showHome();
}

function _updateSidebarUser(user) {
  if (!user) return;
  const name  = document.querySelector('.user-name');
  const email = document.querySelector('.user-email');
  const av    = document.querySelector('.sidebar .user-avatar');
  if (name)  name.textContent  = user.full_name || user.username;
  if (email) email.textContent = user.email;
  if (av)    av.textContent    = (user.full_name || user.username)[0].toUpperCase();
}

function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById(id)?.classList.add('active');
  if (API.tokens.isLoggedIn()) {
    document.getElementById('auth-section').classList.add('hidden');
    document.getElementById('app-section').classList.remove('hidden');
  }
}

// ════════════════════════════════════════════════════════
// ONBOARDING
// ════════════════════════════════════════════════════════
const Onboarding = {
  _key: 'ait_onboarding_dismissed',

  show() {
    if (localStorage.getItem(this._key)) return;
    const banner = document.getElementById('onboarding-banner');
    if (banner) banner.classList.remove('hidden');
  },

  dismiss() {
    localStorage.setItem(this._key, '1');
    const banner = document.getElementById('onboarding-banner');
    if (banner) banner.classList.add('hidden');
  },

  // Called after dashboard loads — hide if user has real tasks
  checkAuto(taskCount) {
    if (taskCount > 3) {
      // They have tasks beyond the 3 seed tasks — dismiss silently
      this.dismiss();
      return;
    }
    this.show();
  },
};

// ════════════════════════════════════════════════════════
// DASHBOARD
// ════════════════════════════════════════════════════════
const Dashboard = {
  async render() {
    showPage('page-dashboard');
    try {
      const res   = await API.tasks.list({ per_page: 100 });
      const tasks = res.items || [];

      const total   = tasks.length;
      const done    = tasks.filter(t => t.status === 'done').length;
      const inProg  = tasks.filter(t => t.status === 'in_progress').length;
      const overdue = tasks.filter(t => isOverdue(t.due_date) && t.status !== 'done').length;

      _setText('stat-total',   total);
      _setText('stat-done',    done);
      _setText('stat-inprog',  inProg);
      _setText('stat-overdue', overdue);

      const pct   = total ? Math.round((done / total) * 100) : 0;
      const bar   = document.getElementById('progress-bar');
      const pctEl = document.getElementById('progress-pct');
      if (bar)   bar.style.width = `${pct}%`;
      if (pctEl) pctEl.textContent = `${pct}%`;

      // Recent tasks (newest 5)
      const container = document.getElementById('recent-tasks');
      const recent    = tasks.slice(0, 5);
      if (!recent.length) {
        container.innerHTML = `
          <div class="empty">
            <div class="empty-icon">✅</div>
            <div class="empty-title">No tasks yet</div>
            <div class="empty-desc">Press <kbd>N</kbd> or click + New Task to get started</div>
          </div>`;
      } else {
        container.innerHTML = recent.map(t => _miniCard(t)).join('');
      }

      // Due soon
      const urgent = tasks.filter(t =>
        t.status !== 'done' && t.due_date &&
        new Date(t.due_date) <= new Date(Date.now() + 48 * 3600000)
      );
      const urgEl = document.getElementById('urgent-tasks');
      if (urgEl) {
        urgEl.innerHTML = urgent.length
          ? urgent.map(t => _miniCard(t)).join('')
          : `<p class="text-sm text-muted">Nothing due in the next 48 hours 🎉</p>`;
      }

      // Onboarding
      Onboarding.checkAuto(total);

    } catch (e) {
      Toast.error('Dashboard error: ' + e.message);
    }
  },
};

function _setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function _miniCard(t) {
  const overdueCls = isOverdue(t.due_date) && t.status !== 'done' ? 'overdue'
                   : isSoon(t.due_date) ? 'soon' : '';
  const subCount   = (t.subtasks || []).length;
  const subDone    = (t.subtasks || []).filter(s => s.is_done).length;
  const tagsHtml   = _renderTags(t.tags);

  return `
  <div class="card task-card" onclick="Tasks.openDetail(${t.id})">
    <div class="task-check ${t.status === 'done' ? 'done' : ''}"
         onclick="event.stopPropagation(); Tasks.quickComplete(${t.id}, '${t.status}')"></div>
    <div class="task-body">
      <div class="task-title ${t.status === 'done' ? 'done' : ''}">${esc(t.title)}</div>
      <div class="task-meta">
        <span class="badge badge-${t.priority}">${t.priority}</span>
        <span class="badge badge-${t.status.replace('_', '-')}">${t.status.replace('_', ' ')}</span>
        ${t.due_date ? `<span class="task-due ${overdueCls}">📅 ${fmtDate(t.due_date)}</span>` : ''}
        ${subCount ? `<span class="task-sub-count">☑ ${subDone}/${subCount}</span>` : ''}
        ${tagsHtml}
      </div>
    </div>
    <div class="task-actions">
      <button class="task-action" onclick="event.stopPropagation(); Tasks.openEdit(${t.id})" title="Edit">✏️</button>
      <button class="task-action del" onclick="event.stopPropagation(); Tasks.delete(${t.id})" title="Delete">🗑</button>
    </div>
  </div>`;
}

function _renderTags(tags) {
  if (!tags) return '';
  return tags.split(',')
    .map(t => t.trim()).filter(Boolean)
    .map(t => `<span class="tag-chip">${esc(t)}</span>`)
    .join('');
}

Router.register('dashboard', () => Dashboard.render());

// ════════════════════════════════════════════════════════
// TASKS PAGE
// ════════════════════════════════════════════════════════
const Tasks = {
  _editId:   null,
  _filters:  {},
  _page:     1,
  _archived: false,

  async render() {
    showPage('page-tasks');
    this._page     = 1;
    this._filters  = {};
    this._archived = false;
    document.querySelectorAll('#page-tasks .filter-chip').forEach(c => c.classList.remove('active'));
    const s = document.getElementById('task-search');
    if (s) s.value = '';
    await this._load();
    this._bindFilters();
  },

  async _load() {
    const container = document.getElementById('task-list');
    container.innerHTML = [1, 2, 3].map(() => `
      <div class="card" style="padding:14px 18px;margin-bottom:8px">
        <div class="skel" style="height:14px;width:60%;margin-bottom:8px"></div>
        <div class="skel" style="height:10px;width:40%"></div>
      </div>`).join('');

    try {
      const params = {
        page: this._page,
        per_page: 20,
        include_archived: this._archived || undefined,
        ...this._filters,
      };
      const res = await API.tasks.list(params);
      this._renderList(res.items || []);
      this._renderPager(res);
    } catch (e) {
      Toast.error('Failed to load tasks: ' + e.message);
      document.getElementById('task-list').innerHTML =
        `<div class="empty"><div class="empty-title">Error loading tasks</div>
         <div class="empty-desc">${esc(e.message)}</div></div>`;
    }
  },

  _renderList(tasks) {
    const el = document.getElementById('task-list');
    if (!tasks.length) {
      el.innerHTML = `
        <div class="empty">
          <div class="empty-icon">📋</div>
          <div class="empty-title">No tasks found</div>
          <div class="empty-desc">
            ${this._archived ? 'No archived tasks.' : 'Create one with <strong>+ New Task</strong> or press <kbd>N</kbd>'}
          </div>
        </div>`;
      return;
    }
    el.innerHTML = `<div class="task-list">${tasks.map(t => _miniCard(t)).join('')}</div>`;
  },

  _renderPager(meta) {
    const el = document.getElementById('task-pager');
    if (!el || meta.total_pages <= 1) { if (el) el.innerHTML = ''; return; }
    el.innerHTML = `
      <div class="pager">
        <button class="btn btn-ghost btn-sm" ${meta.page <= 1 ? 'disabled' : ''}
          onclick="Tasks._page=${meta.page - 1};Tasks._load()">← Prev</button>
        <span class="text-sm text-muted">Page ${meta.page} of ${meta.total_pages}</span>
        <button class="btn btn-ghost btn-sm" ${meta.page >= meta.total_pages ? 'disabled' : ''}
          onclick="Tasks._page=${meta.page + 1};Tasks._load()">Next →</button>
      </div>`;
  },

  _bindFilters() {
    document.querySelectorAll('#page-tasks .filter-chip').forEach(chip => {
      chip.replaceWith(chip.cloneNode(true));
    });
    document.querySelectorAll('#page-tasks .filter-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const key = chip.dataset.filter;
        const val = chip.dataset.value;
        if (key === 'archived') {
          this._archived = !this._archived;
          chip.classList.toggle('active', this._archived);
          this._page = 1; this._load(); return;
        }
        document.querySelectorAll(`#page-tasks .filter-chip[data-filter="${key}"]`)
          .forEach(c => c.classList.remove('active'));
        if (this._filters[key] === val) {
          delete this._filters[key];
        } else {
          chip.classList.add('active');
          this._filters[key] = val;
        }
        this._page = 1; this._load();
      });
    });

    const search = document.getElementById('task-search');
    if (search) {
      const cloned = search.cloneNode(true);
      search.replaceWith(cloned);
      let t;
      cloned.addEventListener('input', e => {
        clearTimeout(t);
        t = setTimeout(() => {
          const v = e.target.value.trim();
          if (v) this._filters.search = v;
          else   delete this._filters.search;
          this._page = 1; this._load();
        }, 350);
      });
    }
  },

  openCreate() {
    this._editId = null;
    this._resetForm();
    document.getElementById('task-modal-title').textContent = 'New Task';
    document.getElementById('subtasks-section').classList.add('hidden');
    Modal.open('modal-task');
    setTimeout(() => document.getElementById('tf-title')?.focus(), 80);
  },

  async openEdit(id) {
    this._editId = id;
    try {
      const t = await API.tasks.get(id);
      document.getElementById('tf-title').value    = t.title || '';
      document.getElementById('tf-desc').value     = t.description || '';
      document.getElementById('tf-priority').value = t.priority || 'medium';
      document.getElementById('tf-status').value   = t.status || 'todo';
      document.getElementById('tf-due').value      = t.due_date ? t.due_date.slice(0, 16) : '';
      document.getElementById('tf-tags').value     = t.tags || '';
      document.getElementById('task-modal-title').textContent = 'Edit Task';
      document.getElementById('subtasks-section').classList.remove('hidden');
      Modal.open('modal-task');
      this._loadSubtasks(id, t.subtasks || []);
    } catch (e) { Toast.error(e.message); }
  },

  async openDetail(id) {
    try {
      const t = await API.tasks.get(id);
      const overdueCls = isOverdue(t.due_date) && t.status !== 'done' ? 'overdue'
                       : isSoon(t.due_date) ? 'soon' : '';
      document.getElementById('detail-title').textContent = t.title;
      document.getElementById('detail-body').innerHTML = `
        <div class="flex gap-2 flex-wrap" style="margin-bottom:14px">
          <span class="badge badge-${t.priority}">${t.priority}</span>
          <span class="badge badge-${t.status.replace('_', '-')}">${t.status.replace('_', ' ')}</span>
          ${t.due_date ? `<span class="task-due ${overdueCls}">📅 ${fmtDate(t.due_date)}</span>` : ''}
          ${_renderTags(t.tags)}
        </div>
        ${t.description
          ? `<p class="detail-desc">${esc(t.description)}</p>`
          : `<p class="text-muted text-sm" style="margin-bottom:14px">No description</p>`}
        ${(t.subtasks || []).length ? `
          <div class="subtask-list" style="margin-bottom:16px">
            <div class="sub-label">Subtasks</div>
            ${t.subtasks.map(s => `
              <div class="subtask-item readonly">
                <span class="sub-check ${s.is_done ? 'done' : ''}"></span>
                <span class="${s.is_done ? 'done' : ''}">${esc(s.title)}</span>
              </div>`).join('')}
          </div>` : ''}
        <p class="text-xs text-muted" style="margin-bottom:14px">
          Created ${fmtDateTime(t.created_at)}
          ${t.updated_at !== t.created_at ? ` · Updated ${fmtDateTime(t.updated_at)}` : ''}
        </p>
        <div class="flex gap-2 flex-wrap">
          <button class="btn btn-secondary btn-sm"
            onclick="Modal.close('modal-detail'); Tasks.openEdit(${t.id})">✏️ Edit</button>
          <button class="btn btn-ghost btn-sm"
            onclick="Modal.close('modal-detail'); Tasks.archiveTask(${t.id}, ${t.is_archived})">
            ${t.is_archived ? '📤 Unarchive' : '📥 Archive'}
          </button>
          <button class="btn btn-danger btn-sm"
            onclick="Modal.close('modal-detail'); Tasks.delete(${t.id})">🗑 Delete</button>
        </div>`;
      Modal.open('modal-detail');
    } catch (e) { Toast.error(e.message); }
  },

  _loadSubtasks(taskId, subtasks) {
    const container = document.getElementById('subtask-list');
    if (!container) return;
    container.innerHTML = subtasks.map(s => this._subtaskRow(taskId, s)).join('');
  },

  _subtaskRow(taskId, s) {
    return `
    <div class="subtask-item" id="sub-${s.id}">
      <input type="checkbox" class="sub-checkbox" ${s.is_done ? 'checked' : ''}
        onchange="Tasks.toggleSubtask(${taskId}, ${s.id}, this.checked)">
      <span class="sub-title ${s.is_done ? 'done' : ''}">${esc(s.title)}</span>
      <button class="sub-del" onclick="Tasks.deleteSubtask(${taskId}, ${s.id})" title="Remove">✕</button>
    </div>`;
  },

  async addSubtask(taskId) {
    const input = document.getElementById('new-subtask-input');
    const title = input?.value.trim();
    if (!title) return;
    try {
      const sub = await API.subtasks.create(taskId, { title });
      input.value = '';
      const container = document.getElementById('subtask-list');
      if (container) container.insertAdjacentHTML('beforeend', this._subtaskRow(taskId, sub));
    } catch (e) { Toast.error(e.message); }
  },

  async toggleSubtask(taskId, subId, isDone) {
    try {
      await API.subtasks.update(taskId, subId, { is_done: isDone });
      const row = document.getElementById(`sub-${subId}`);
      if (row) row.querySelector('.sub-title')?.classList.toggle('done', isDone);
    } catch (e) { Toast.error(e.message); }
  },

  async deleteSubtask(taskId, subId) {
    try {
      await API.subtasks.delete(taskId, subId);
      document.getElementById(`sub-${subId}`)?.remove();
    } catch (e) { Toast.error(e.message); }
  },

  async save() {
    const btn  = document.getElementById('task-save-btn');
    const data = {
      title:       document.getElementById('tf-title').value.trim(),
      description: document.getElementById('tf-desc').value.trim() || null,
      priority:    document.getElementById('tf-priority').value,
      status:      document.getElementById('tf-status').value,
      due_date: (() => {
        const v = document.getElementById('tf-due').value;
        if (!v) return null;
        return new Date(v).toISOString();
      })(),
      tags: document.getElementById('tf-tags').value.trim() || null,
    };
    if (!data.title) { Toast.warning('Title is required'); return; }

    await withBtn(btn, async () => {
      try {
        if (this._editId) {
          await API.tasks.update(this._editId, data);
          Toast.success('Task updated');
        } else {
          await API.tasks.create(data);
          Toast.success('Task created');
        }
        Modal.close('modal-task');
        await this._load();
        if (document.getElementById('page-dashboard')?.classList.contains('active')) {
          Dashboard.render();
        }
        if (document.getElementById('page-calendar')?.classList.contains('active')) {
          Calendar.render();
        }
      } catch (e) { Toast.error(e.message); }
    });
  },

  async quickComplete(id, currentStatus) {
    const newStatus = currentStatus === 'done' ? 'todo' : 'done';
    try {
      await API.tasks.update(id, { status: newStatus });
      await this._load();
      if (document.getElementById('page-dashboard')?.classList.contains('active')) Dashboard.render();
      if (document.getElementById('page-calendar')?.classList.contains('active'))  Calendar.render();
    } catch (e) { Toast.error(e.message); }
  },

  async archiveTask(id, isArchived) {
    try {
      if (isArchived) {
        await API.tasks.update(id, { is_archived: false });
        Toast.success('Task unarchived');
      } else {
        await API.tasks.archive(id);
        Toast.success('Task archived');
      }
      await this._load();
      if (document.getElementById('page-dashboard')?.classList.contains('active')) Dashboard.render();
    } catch (e) { Toast.error(e.message); }
  },

  async delete(id) {
    if (!confirm('Permanently delete this task and all its subtasks?')) return;
    try {
      await API.tasks.delete(id);
      Toast.success('Task deleted');
      await this._load();
      if (document.getElementById('page-dashboard')?.classList.contains('active')) Dashboard.render();
      if (document.getElementById('page-calendar')?.classList.contains('active'))  Calendar.render();
    } catch (e) { Toast.error(e.message); }
  },

  _resetForm() {
    ['tf-title', 'tf-desc', 'tf-due', 'tf-tags'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    const p = document.getElementById('tf-priority');
    const s = document.getElementById('tf-status');
    if (p) p.value = 'medium';
    if (s) s.value = 'todo';
    const sc = document.getElementById('subtask-list');
    if (sc) sc.innerHTML = '';
  },
};

Router.register('tasks', () => Tasks.render());

// ════════════════════════════════════════════════════════
// CALENDAR VIEW
// ════════════════════════════════════════════════════════
const Calendar = {
  _weekOffset: 0,  // 0 = this week, -1 = last week, +1 = next week

  async render() {
    showPage('page-calendar');
    const grid = document.getElementById('cal-grid');
    grid.innerHTML = `<div class="cal-loading"><span class="spin"></span> Loading…</div>`;

    try {
      const res   = await API.tasks.list({ per_page: 200 });
      const tasks = (res.items || []).filter(t => !t.is_archived && t.status !== 'done');
      this._renderWeek(tasks);
    } catch (e) {
      Toast.error('Calendar error: ' + e.message);
    }
  },

  _weekStart() {
    const now    = new Date();
    const day    = now.getDay(); // 0=Sun
    const monday = new Date(now);
    monday.setDate(now.getDate() - ((day + 6) % 7) + this._weekOffset * 7);
    monday.setHours(0, 0, 0, 0);
    return monday;
  },

  _renderWeek(tasks) {
    const start  = this._weekStart();
    const days   = Array.from({ length: 7 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });

    // Update label
    const fmt = d => d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
    document.getElementById('cal-week-label').textContent =
      `${fmt(days[0])} – ${fmt(days[6])}`;

    // Group tasks by calendar date
    const byDay = {};
    const unscheduled = [];
    tasks.forEach(t => {
      if (!t.due_date) { unscheduled.push(t); return; }
      const key = new Date(t.due_date).toDateString();
      byDay[key] = byDay[key] || [];
      byDay[key].push(t);
    });

    const today = new Date().toDateString();
    const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    const grid = document.getElementById('cal-grid');
    grid.innerHTML = days.map((day, i) => {
      const key      = day.toDateString();
      const isToday  = key === today;
      const dayTasks = byDay[key] || [];
      const dateNum  = day.getDate();
      const month    = day.toLocaleDateString('en-GB', { month: 'short' });

      return `
      <div class="cal-day ${isToday ? 'cal-today' : ''} ${i >= 5 ? 'cal-weekend' : ''}">
        <div class="cal-day-header">
          <span class="cal-day-name">${dayNames[i]}</span>
          <span class="cal-day-num ${isToday ? 'cal-today-num' : ''}">${dateNum} ${month}</span>
        </div>
        <div class="cal-day-tasks">
          ${dayTasks.length === 0
            ? `<div class="cal-empty">—</div>`
            : dayTasks.map(t => this._calTaskChip(t)).join('')
          }
        </div>
      </div>`;
    }).join('');

    // Unscheduled
    const unsEl = document.getElementById('cal-unscheduled');
    if (unsEl) {
      unsEl.innerHTML = unscheduled.length
        ? `<div class="task-list">${unscheduled.map(t => _miniCard(t)).join('')}</div>`
        : `<p class="text-sm text-muted">All active tasks have a due date 🎉</p>`;
    }
  },

  _calTaskChip(t) {
    const overdue = isOverdue(t.due_date) && t.status !== 'done';
    return `
    <div class="cal-chip badge-${t.priority} ${overdue ? 'cal-chip-overdue' : ''}"
         onclick="Tasks.openDetail(${t.id})" title="${esc(t.title)}">
      <span class="cal-chip-dot"></span>
      <span class="cal-chip-title">${esc(t.title)}</span>
    </div>`;
  },

  prevWeek() { this._weekOffset--; this.render(); },
  nextWeek() { this._weekOffset++; this.render(); },
  goToday()  { this._weekOffset = 0; this.render(); },
};

Router.register('calendar', () => Calendar.render());

// ════════════════════════════════════════════════════════
// SETTINGS PAGE
// ════════════════════════════════════════════════════════
const Settings = {
  render() {
    showPage('page-settings');
    const user = State.user;
    if (!user) return;

    document.getElementById('s-fullname').value      = user.full_name || '';
    document.getElementById('s-username').textContent = '@' + user.username;
    document.getElementById('s-email').textContent    = user.email;
    document.getElementById('s-theme').value          = user.theme || 'dark';

    const av = document.getElementById('settings-avatar');
    if (av) av.textContent = (user.full_name || user.username)[0].toUpperCase();

    PushManager._updateUI();
  },

  async saveProfile() {
    const btn = document.getElementById('save-profile-btn');
    await withBtn(btn, async () => {
      try {
        const updated = await API.users.updateMe({
          full_name: document.getElementById('s-fullname').value.trim() || null,
          theme:     document.getElementById('s-theme').value,
        });
        State.save(updated);
        Theme.set(updated.theme);
        _updateSidebarUser(updated);
        Toast.success('Profile saved');
      } catch (e) { Toast.error(e.message); }
    });
  },

  async changePassword() {
    const btn  = document.getElementById('change-pwd-btn');
    const curr = document.getElementById('s-curr-pwd').value;
    const next = document.getElementById('s-new-pwd').value;
    const conf = document.getElementById('s-conf-pwd').value;

    if (!curr || !next)  { Toast.warning('Fill in all password fields'); return; }
    if (next !== conf)   { Toast.warning('Passwords do not match'); return; }
    if (next.length < 8) { Toast.warning('Password must be at least 8 characters'); return; }

    await withBtn(btn, async () => {
      try {
        await API.users.changePassword({ current_password: curr, new_password: next });
        Toast.success('Password updated');
        ['s-curr-pwd', 's-new-pwd', 's-conf-pwd'].forEach(id => {
          document.getElementById(id).value = '';
        });
      } catch (e) { Toast.error(e.message); }
    });
  },
};

Router.register('settings', () => Settings.render());

// ════════════════════════════════════════════════════════
// AI MILESTONE PLANNER
// ════════════════════════════════════════════════════════
const MilestonePlanner = {
  _plan: null,  // current generated plan

  async render() {
    showPage('page-planner');
    this._plan = null;
    document.getElementById('mp-preview').classList.add('hidden');
    document.getElementById('mp-title').value = '';
    document.getElementById('mp-desc').value  = '';
    document.getElementById('mp-days').value  = '';
  },

  async generate() {
    const btn   = document.getElementById('mp-generate-btn');
    const title = document.getElementById('mp-title').value.trim();
    const desc  = document.getElementById('mp-desc').value.trim();
    const days  = parseInt(document.getElementById('mp-days').value, 10);

    if (!title)          { Toast.warning('Please enter a goal title');            return; }
    if (!days || days < 1) { Toast.warning('Please enter a valid number of days'); return; }

    const prompt = `You are an AI planner generator.
User Input:
Title: ${title}
Description: ${desc || 'Not provided'}
Deadline: ${days} days
Your job:
Generate a day-wise actionable plan so the user can achieve the goal within the deadline.
STRICT RULES:
- Output ONLY valid JSON
- NO explanation text
- NO markdown
- FOLLOW schema EXACTLY
- Generate exactly ${days} entries (1 per day)
- Each day must have:
  - "day" number
  - "task" (short main task)
  - "subtasks" (2-4 actionable steps)
SCHEMA:
{
  "title": "",
  "description": "",
  "deadline_days": 0,
  "plan": [
    {
      "day": 1,
      "task": "",
      "subtasks": []
    }
  ]
}
IMPORTANT:
- Tasks must be progressive (gradually increasing difficulty)
- Tasks must be realistic and achievable
- Adapt based on the goal type (fitness, learning, skill, etc.)
- Ensure consistency and logical progression`;

    await withBtn(btn, async () => {
      try {
        // Show skeleton loader
        document.getElementById('mp-preview').classList.remove('hidden');
        document.getElementById('mp-day-cards').innerHTML = this._skeleton(Math.min(days, 5));

        const res = await fetch('http://localhost:11434/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: 'gpt-oss:20b',
            prompt: prompt,
            stream: false,
          }),
        });

        if (!res.ok) throw new Error(`Ollama error ${res.status}: ${await res.text()}`);

        const data = await res.json();
        const raw  = (data.response || '').trim();

        let plan;
        try {
          // Strip possible markdown fences just in case
          const clean = raw.replace(/^```json\s*/i, '').replace(/```\s*$/, '').trim();
          plan = JSON.parse(clean);
        } catch {
          throw new Error('AI returned invalid JSON. Try again or simplify your description.');
        }

        if (!plan.plan || !Array.isArray(plan.plan)) {
          throw new Error('Unexpected plan format from AI. Please try again.');
        }

        this._plan = plan;
        this._renderPreview(plan);
        Toast.success('Plan generated! Review and save when ready.');
      } catch (e) {
        document.getElementById('mp-preview').classList.add('hidden');
        Toast.error('Generation failed: ' + e.message);
      }
    });
  },

  _skeleton(n) {
    return Array.from({ length: n }, () => `
      <div class="card" style="padding:14px 18px;margin-bottom:10px">
        <div class="skel" style="height:13px;width:30%;margin-bottom:10px"></div>
        <div class="skel" style="height:11px;width:70%;margin-bottom:6px"></div>
        <div class="skel" style="height:11px;width:55%;margin-bottom:6px"></div>
        <div class="skel" style="height:11px;width:62%"></div>
      </div>`).join('');
  },

  _renderPreview(plan) {
    document.getElementById('mp-preview-title').textContent = plan.title || 'Your Plan';
    document.getElementById('mp-preview-desc').textContent  = plan.description || '';
    document.getElementById('mp-preview-days').textContent  = plan.deadline_days || plan.plan.length;

    const container = document.getElementById('mp-day-cards');
    container.innerHTML = plan.plan.map((entry, idx) => this._dayCard(entry, idx)).join('');
  },

  _dayCard(entry, idx) {
    const subtasksHtml = (entry.subtasks || []).map((s, si) => `
      <div class="subtask-item" style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border)">
        <span style="font-size:0.75rem;color:var(--text-3);min-width:20px">${si + 1}.</span>
        <input type="text" class="input mp-sub-input" style="flex:1;padding:4px 8px;font-size:0.82rem"
               value="${esc(s)}" data-day="${idx}" data-sub="${si}">
        <button class="btn btn-ghost btn-sm" style="padding:2px 6px;font-size:0.7rem"
                onclick="MilestonePlanner._removeSub(${idx},${si})">✕</button>
      </div>`).join('');

    return `
    <div class="card card-p mp-day-card" id="mp-day-${idx}" style="margin-bottom:12px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
        <span class="badge badge-medium" style="min-width:54px;text-align:center;font-size:0.7rem">Day ${entry.day}</span>
        <input type="text" class="input mp-task-input" style="flex:1;font-weight:600"
               value="${esc(entry.task)}" data-day="${idx}" placeholder="Main task for this day">
      </div>
      <div class="mp-subtasks-wrap" id="mp-subs-${idx}">
        ${subtasksHtml}
      </div>
      <button class="btn btn-ghost btn-sm" style="margin-top:10px;font-size:0.78rem"
              onclick="MilestonePlanner._addSub(${idx})">+ Add subtask</button>
    </div>`;
  },

  _removeSub(dayIdx, subIdx) {
    const entry = this._plan.plan[dayIdx];
    if (!entry) return;
    entry.subtasks.splice(subIdx, 1);
    document.getElementById(`mp-subs-${dayIdx}`).outerHTML =
      document.createElement('div').innerHTML; // re-render just subs
    // Re-render whole card for simplicity
    const cardEl = document.getElementById(`mp-day-${dayIdx}`);
    if (cardEl) cardEl.outerHTML = this._dayCard(entry, dayIdx);
  },

  _addSub(dayIdx) {
    const entry = this._plan.plan[dayIdx];
    if (!entry) return;
    entry.subtasks = entry.subtasks || [];
    entry.subtasks.push('New subtask');
    const cardEl = document.getElementById(`mp-day-${dayIdx}`);
    if (cardEl) cardEl.outerHTML = this._dayCard(entry, dayIdx);
  },

  _collectEdits() {
    if (!this._plan) return;
    this._plan.plan.forEach((entry, idx) => {
      const taskEl = document.querySelector(`.mp-task-input[data-day="${idx}"]`);
      if (taskEl) entry.task = taskEl.value.trim();
      const subEls = document.querySelectorAll(`.mp-sub-input[data-day="${idx}"]`);
      entry.subtasks = Array.from(subEls).map(el => el.value.trim()).filter(Boolean);
    });
  },

  async saveAll() {
    if (!this._plan) return;
    this._collectEdits();

    const btn  = document.getElementById('mp-save-btn');
    const plan = this._plan;
    const today = new Date();
    today.setHours(9, 0, 0, 0); // 9 AM default

    let saved = 0;
    let failed = 0;

    await withBtn(btn, async () => {
      for (const entry of plan.plan) {
        try {
          const due = new Date(today);
          due.setDate(today.getDate() + (entry.day - 1));

          // Create the parent task
          const task = await API.tasks.create({
            title:       `Day ${entry.day} – ${entry.task}`,
            description: `Part of AI Milestone Plan: "${plan.title}"`,
            priority:    'medium',
            status:      'todo',
            due_date:    due.toISOString(),
            tags:        'ai-plan,' + (plan.title || 'milestone').toLowerCase().replace(/\s+/g,'-').slice(0,20),
          });

          // Create subtasks
          for (const sub of (entry.subtasks || [])) {
            if (sub.trim()) {
              await API.subtasks.create(task.id, { title: sub.trim() });
            }
          }
          saved++;
        } catch {
          failed++;
        }
      }

      if (saved > 0) {
        Toast.success(`✅ ${saved} task${saved > 1 ? 's' : ''} saved to My Tasks!`);
        if (failed > 0) Toast.warning(`⚠ ${failed} task${failed > 1 ? 's' : ''} failed to save.`);
        // Navigate to tasks page
        setTimeout(() => Router.navigate('#tasks'), 1200);
      } else {
        Toast.error('Could not save tasks. Please try again.');
      }
    });
  },

  reset() {
    this._plan = null;
    document.getElementById('mp-preview').classList.add('hidden');
    document.getElementById('mp-day-cards').innerHTML = '';
    document.getElementById('mp-title').value = '';
    document.getElementById('mp-desc').value  = '';
    document.getElementById('mp-days').value  = '';
  },
};

Router.register('planner', () => MilestonePlanner.render());

// ════════════════════════════════════════════════════════
// BOOT — restore session on page reload
// ════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  if (API.tokens.isLoggedIn() && State.user) {
    document.getElementById('auth-section').classList.add('hidden');
    document.getElementById('app-section').classList.remove('hidden');
    _updateSidebarUser(State.user);
    PushManager.init();
  } else {
    // Show landing home page by default
    showHome();
  }

  Router.init();
});
