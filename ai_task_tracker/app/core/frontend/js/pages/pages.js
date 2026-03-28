/**
 * Dashboard Page
 */
const DashboardPage = (() => {
  async function render() {
    showPage('page-dashboard');
    await fetchStats();
  }

  async function fetchStats() {
    try {
      const [stats, productivity] = await Promise.all([
        api.getDashboardStats(),
        api.getProductivitySummary(30),
      ]);
      renderStats(stats);
      renderProductivityChart(productivity.daily_scores || []);
      renderActivitySummary(productivity);
    } catch (e) { Toast.error('Dashboard error', e.message); }
  }

  function renderStats(s) {
    const items = [
      { label: 'Total Tasks', value: s.total_tasks, icon: '✅', color: 'var(--gold-500)', change: '' },
      { label: 'Completed Today', value: s.completed_today, icon: '🏆', color: 'var(--emerald)', change: '' },
      { label: 'Overdue', value: s.tasks_overdue, icon: '⚠️', color: 'var(--rose)', change: s.tasks_overdue > 0 ? 'down' : '' },
      { label: 'Due Soon', value: s.tasks_due_soon, icon: '⏰', color: 'var(--amber)', change: '' },
      { label: 'Active Milestones', value: s.active_milestones, icon: '🎯', color: 'var(--violet)', change: '' },
      { label: 'Streak Days', value: s.streak_days, icon: '🔥', color: 'var(--gold-400)', change: s.streak_days > 0 ? 'up' : '' },
      { label: "Today's Score", value: `${Math.round(s.productivity_score_today)}`, icon: '📊', color: 'var(--sapphire)', change: '' },
      { label: '7-Day Rate', value: `${Math.round(s.completion_rate_7d * 100)}%`, icon: '📈', color: 'var(--emerald)', change: 'up' },
    ];
    const grid = document.getElementById('dashboard-stats');
    if (!grid) return;
    grid.innerHTML = items.map(item => `
      <div class="glass-card stat-card animate-slide-up" style="--accent-color:${item.color}">
        <div class="stat-label">${item.label}</div>
        <div class="stat-value" style="color:${item.color}">${item.value}</div>
        <div class="stat-icon">${item.icon}</div>
      </div>`).join('');
  }

  function renderProductivityChart(scores) {
    const canvas = document.getElementById('productivity-chart');
    if (!canvas || !scores.length) return;
    const ctx = canvas.getContext('2d');
    const labels = scores.slice(-14).map(s => s.date.slice(5));
    const data = scores.slice(-14).map(s => s.score);
    canvas.width = canvas.offsetWidth;
    canvas.height = 160;
    const W = canvas.width, H = canvas.height;
    const maxVal = Math.max(...data, 100);
    ctx.clearRect(0, 0, W, H);
    // Gradient fill
    const grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, 'rgba(212,168,67,0.3)');
    grad.addColorStop(1, 'rgba(212,168,67,0)');
    const pts = data.map((v, i) => ({ x: (i / (data.length - 1)) * (W - 40) + 20, y: H - 20 - (v / maxVal) * (H - 30) }));
    ctx.beginPath();
    ctx.moveTo(pts[0].x, H - 20);
    pts.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.lineTo(pts[pts.length - 1].x, H - 20);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();
    // Line
    ctx.beginPath();
    pts.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
    ctx.strokeStyle = 'rgba(212,168,67,0.8)';
    ctx.lineWidth = 2;
    ctx.stroke();
    // Dots
    pts.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
      ctx.fillStyle = '#d4a843';
      ctx.fill();
    });
  }

  function renderActivitySummary(p) {
    const el = document.getElementById('activity-summary');
    if (!el) return;
    el.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:16px">
        <div class="glass-card" style="padding:16px">
          <div class="stat-label">Tasks Created (30d)</div>
          <div style="font-size:1.6rem;font-family:var(--font-display);font-weight:700;color:var(--sapphire)">${p.total_tasks_created}</div>
        </div>
        <div class="glass-card" style="padding:16px">
          <div class="stat-label">Tasks Completed (30d)</div>
          <div style="font-size:1.6rem;font-family:var(--font-display);font-weight:700;color:var(--emerald)">${p.total_tasks_completed}</div>
        </div>
        <div class="glass-card" style="padding:16px">
          <div class="stat-label">Avg Completion Rate</div>
          <div style="font-size:1.6rem;font-family:var(--font-display);font-weight:700;color:var(--gold-400)">${Math.round(p.average_completion_rate * 100)}%</div>
        </div>
        <div class="glass-card" style="padding:16px">
          <div class="stat-label">Avg Productivity Score</div>
          <div style="font-size:1.6rem;font-family:var(--font-display);font-weight:700;color:var(--violet)">${Math.round(p.average_productivity_score)}/100</div>
        </div>
      </div>`;
  }

  return { render };
})();
Router.register('#/dashboard', DashboardPage.render);

/* ── Milestones Page ──────────────────────────────────────────────────────── */
const MilestonesPage = (() => {
  let editingId = null;

  async function render() {
    showPage('page-milestones');
    await fetchAndRender();
  }

  async function fetchAndRender() {
    const container = document.getElementById('milestones-container');
    container.innerHTML = '<div style="display:flex;justify-content:center;padding:40px"><span class="spinner"></span></div>';
    try {
      const res = await api.getMilestones({ per_page: 50 });
      if (!res.data.length) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🎯</div><div class="empty-state-title">No milestones yet</div><div class="empty-state-desc">Create a milestone to group related tasks</div></div>`;
        return;
      }
      container.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px">${res.data.map(milestoneCard).join('')}</div>`;
    } catch (e) { Toast.error('Failed to load milestones', e.message); }
  }

  function milestoneCard(m) {
    const statusColors = { planned: 'var(--sapphire)', in_progress: 'var(--gold-400)', completed: 'var(--emerald)', overdue: 'var(--rose)', cancelled: 'var(--text-muted)' };
    return `
    <div class="glass-card milestone-card">
      <div class="milestone-color-bar" style="background:${m.color}"></div>
      <div class="milestone-header">
        <div>
          <div class="milestone-title">${escapeHtml(m.title)}</div>
          ${m.description ? `<div class="milestone-meta">${escapeHtml(m.description.slice(0, 80))}${m.description.length > 80 ? '…' : ''}</div>` : ''}
        </div>
        <span class="badge" style="background:${statusColors[m.status]}22;color:${statusColors[m.status]};border-radius:99px">${m.status.replace('_',' ')}</span>
      </div>
      <div class="milestone-progress-label">
        <span>Progress</span><span>${m.progress_percentage}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill ${m.status==='completed'?'complete':''}" style="width:${m.progress_percentage}%;background:${m.color}"></div>
      </div>
      <div class="milestone-footer">
        <span class="milestone-task-count">${m.completed_tasks}/${m.total_tasks} tasks</span>
        <div style="display:flex;gap:6px">
          ${m.due_date ? `<span class="task-due ${isOverdue(m.due_date)?'overdue':''}">📅 ${formatDate(m.due_date)}</span>` : ''}
          <button class="task-action-btn" onclick="MilestonesPage.openEdit(${m.id})">✏️</button>
          <button class="task-action-btn danger" onclick="MilestonesPage.confirmDelete(${m.id})">🗑</button>
        </div>
      </div>
    </div>`;
  }

  function openCreate() { editingId = null; resetForm(); document.getElementById('milestone-form-title').textContent = 'New Milestone'; Modal.open('modal-milestone-form'); }

  async function openEdit(id) {
    editingId = id;
    try { const m = await api.getMilestone(id); fillForm(m); document.getElementById('milestone-form-title').textContent = 'Edit Milestone'; Modal.open('modal-milestone-form'); }
    catch (e) { Toast.error('Failed to load milestone', e.message); }
  }

  async function confirmDelete(id) {
    if (!confirm('Delete this milestone? Tasks will not be deleted.')) return;
    try { await api.deleteMilestone(id); Toast.success('Milestone deleted'); fetchAndRender(); }
    catch (e) { Toast.error('Delete failed', e.message); }
  }

  async function save() {
    const btn = document.getElementById('milestone-save-btn');
    const data = {
      title: document.getElementById('mf-title')?.value || '',
      description: document.getElementById('mf-description')?.value || '',
      color: document.getElementById('mf-color')?.value || '#6366f1',
      due_date: document.getElementById('mf-due-date')?.value || null,
    };
    if (!data.title.trim()) { Toast.warning('Title required'); return; }
    await withLoading(btn, async () => {
      try {
        if (editingId) { await api.updateMilestone(editingId, data); Toast.success('Milestone updated'); }
        else { await api.createMilestone(data); Toast.success('Milestone created'); }
        Modal.close('modal-milestone-form');
        fetchAndRender();
      } catch (e) { Toast.error('Save failed', e.message); }
    });
  }

  function fillForm(m) {
    document.getElementById('mf-title').value = m.title || '';
    document.getElementById('mf-description').value = m.description || '';
    document.getElementById('mf-color').value = m.color || '#6366f1';
    document.getElementById('mf-due-date').value = m.due_date ? m.due_date.slice(0, 10) : '';
  }
  function resetForm() { ['mf-title','mf-description','mf-due-date'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; }); document.getElementById('mf-color').value = '#6366f1'; }

  return { render, openCreate, openEdit, confirmDelete, save };
})();
Router.register('#/milestones', MilestonesPage.render);

/* ── Notifications Page ───────────────────────────────────────────────────── */
const NotificationsPage = (() => {
  async function render() {
    showPage('page-notifications');
    await fetchAndRender();
  }

  async function fetchAndRender() {
    const container = document.getElementById('notifications-container');
    container.innerHTML = '<div style="display:flex;justify-content:center;padding:40px"><span class="spinner"></span></div>';
    try {
      const res = await api.getNotifications({ per_page: 50 });
      if (!res.data.length) { container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🔔</div><div class="empty-state-title">All caught up!</div><div class="empty-state-desc">No notifications to show</div></div>`; return; }
      container.innerHTML = `<div class="glass-card" style="padding:0;overflow:hidden">${res.data.map(notifItem).join('')}</div>`;
    } catch (e) { Toast.error('Failed to load notifications', e.message); }
  }

  function notifItem(n) {
    const icons = { task_due:'⏰', task_overdue:'⚠️', task_completed:'✅', milestone_due:'🎯', milestone_completed:'🏆', ai_suggestion:'🤖', streak_achievement:'🔥', system:'📢', productivity_report:'📊' };
    return `
    <div class="notif-item ${!n.is_read ? 'unread' : ''}" onclick="NotificationsPage.markRead(${n.id}, this)">
      <span class="notif-icon">${icons[n.notification_type] || '📢'}</span>
      <div class="notif-content">
        <div class="notif-title">${escapeHtml(n.title)}</div>
        <div class="notif-msg">${escapeHtml(n.message)}</div>
        <div class="notif-time">${formatRelative(n.created_at)}</div>
      </div>
      ${!n.is_read ? '<div class="notif-unread-dot"></div>' : ''}
    </div>`;
  }

  async function markRead(id, el) {
    try { await api.markNotifRead(id); el.classList.remove('unread'); el.querySelector('.notif-unread-dot')?.remove(); loadUnreadCount(); }
    catch {}
  }

  async function markAllRead() {
    try { await api.markAllNotifsRead(); Toast.success('All notifications marked read'); fetchAndRender(); loadUnreadCount(); }
    catch (e) { Toast.error('Failed', e.message); }
  }

  return { render, markRead, markAllRead };
})();
Router.register('#/notifications', NotificationsPage.render);

/* ── AI Suggestions Page ──────────────────────────────────────────────────── */
const AISuggestionsPage = (() => {
  async function render() {
    showPage('page-ai-suggestions');
    await fetchAndRender();
  }

  async function fetchAndRender() {
    const container = document.getElementById('suggestions-container');
    container.innerHTML = '<div style="display:flex;justify-content:center;padding:40px"><span class="spinner"></span></div>';
    try {
      const res = await api.getSuggestions({ per_page: 20 });
      if (!res.data.length) { container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🤖</div><div class="empty-state-title">No suggestions right now</div><div class="empty-state-desc">Click "Generate" to analyse your productivity</div></div>`; return; }
      container.innerHTML = `<div style="display:flex;flex-direction:column;gap:12px">${res.data.map(suggCard).join('')}</div>`;
    } catch (e) { Toast.error('Failed to load suggestions', e.message); }
  }

  function suggCard(s) {
    const types = { prioritization:'🔴', time_management:'⏱️', workload_balance:'📊', overdue_alert:'⚠️', break_reminder:'☕', productivity_boost:'📈', streak_motivation:'🔥', task_breakdown:'📝', deadline_warning:'⏰', focus_mode:'🎯' };
    return `
    <div class="glass-card suggestion-card">
      <span class="suggestion-icon">${types[s.suggestion_type] || '💡'}</span>
      <div class="suggestion-body">
        <div class="suggestion-type">${s.suggestion_type.replace(/_/g,' ')}</div>
        <div class="suggestion-title">${escapeHtml(s.title)}</div>
        <div class="suggestion-msg">${escapeHtml(s.message)}</div>
        <div class="suggestion-actions">
          <button class="btn btn-primary btn-sm" onclick="AISuggestionsPage.accept(${s.id})">✓ Accept</button>
          <button class="btn btn-ghost btn-sm" onclick="AISuggestionsPage.dismiss(${s.id})">Dismiss</button>
        </div>
      </div>
    </div>`;
  }

  async function generate() {
    const btn = document.getElementById('generate-suggestions-btn');
    await withLoading(btn, async () => {
      try { await api.generateSuggestions(); Toast.success('Suggestions refreshed'); fetchAndRender(); }
      catch (e) { Toast.error('Generation failed', e.message); }
    });
  }

  async function accept(id) {
    try { await api.feedbackSuggestion(id, 'accepted'); Toast.success('Suggestion accepted'); fetchAndRender(); }
    catch (e) { Toast.error('Failed', e.message); }
  }

  async function dismiss(id) {
    try { await api.feedbackSuggestion(id, 'dismissed'); fetchAndRender(); }
    catch (e) { Toast.error('Failed', e.message); }
  }

  return { render, generate, accept, dismiss };
})();
Router.register('#/ai-suggestions', AISuggestionsPage.render);

/* ── Analytics Page ───────────────────────────────────────────────────────── */
const AnalyticsPage = (() => {
  async function render() {
    showPage('page-analytics');
    await fetchAndRender(30);
  }

  async function fetchAndRender(days) {
    const container = document.getElementById('analytics-container');
    container.innerHTML = '<div style="display:flex;justify-content:center;padding:60px"><span class="spinner"></span></div>';
    try {
      const p = await api.getProductivitySummary(days);
      container.innerHTML = buildAnalyticsHTML(p);
      drawChart(p.daily_scores || []);
    } catch (e) { Toast.error('Failed to load analytics', e.message); }
  }

  function buildAnalyticsHTML(p) {
    const catIcons = { work:'💼', personal:'🏠', health:'💪', learning:'📚', finance:'💰', other:'📌' };
    const cats = Object.entries(p.category_breakdown || {});
    return `
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px;margin-bottom:24px">
      ${[
        ['Tasks Created',p.total_tasks_created,'var(--sapphire)'],
        ['Tasks Completed',p.total_tasks_completed,'var(--emerald)'],
        ['Overdue Tasks',p.total_tasks_overdue,'var(--rose)'],
        ['Avg Score',`${Math.round(p.average_productivity_score)}/100`,'var(--gold-400)'],
        ['Completion Rate',`${Math.round(p.average_completion_rate*100)}%`,'var(--emerald)'],
        ['On-Time Rate',`${Math.round(p.average_on_time_rate*100)}%`,'var(--violet)'],
        ['Streak Days',p.current_streak,'var(--amber)'],
        ['Hours Logged',`${p.total_hours_logged}h`,'var(--sapphire)'],
      ].map(([l,v,c]) => `<div class="glass-card stat-card" style="--accent-color:${c}"><div class="stat-label">${l}</div><div class="stat-value" style="color:${c};font-size:1.7rem">${v}</div></div>`).join('')}
    </div>
    <div class="glass-card" style="padding:24px;margin-bottom:20px">
      <h3 style="font-family:var(--font-display);margin-bottom:16px">Daily Productivity Score</h3>
      <canvas id="analytics-chart" style="width:100%;height:220px"></canvas>
    </div>
    ${cats.length ? `
    <div class="glass-card" style="padding:24px">
      <h3 style="font-family:var(--font-display);margin-bottom:16px">Completed by Category</h3>
      <div style="display:flex;flex-direction:column;gap:10px">
        ${cats.sort((a,b)=>b[1]-a[1]).map(([cat, count]) => {
          const max = Math.max(...cats.map(c=>c[1]));
          return `<div>
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:0.85rem">
              <span>${catIcons[cat]||'📌'} ${cat}</span><span style="color:var(--gold-400);font-weight:600">${count}</span>
            </div>
            <div class="progress-track" style="height:6px"><div class="progress-fill" style="width:${(count/max)*100}%"></div></div>
          </div>`;
        }).join('')}
      </div>
    </div>` : ''}`;
  }

  function drawChart(scores) {
    const canvas = document.getElementById('analytics-chart');
    if (!canvas || !scores.length) return;
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth || 600;
    canvas.height = 220;
    const W = canvas.width, H = canvas.height, pad = 30;
    const data = scores.slice(-30).map(s => s.score);
    const maxVal = 100;
    ctx.clearRect(0, 0, W, H);
    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.05)'; ctx.lineWidth = 1;
    [25,50,75,100].forEach(v => {
      const y = H - pad - (v/maxVal)*(H-pad*2);
      ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(W-pad, y); ctx.stroke();
      ctx.fillStyle = 'rgba(255,255,255,0.2)'; ctx.font = '10px DM Sans,sans-serif'; ctx.fillText(v, 4, y+3);
    });
    if (data.length < 2) return;
    const pts = data.map((v,i) => ({ x: pad + (i/(data.length-1))*(W-pad*2), y: H-pad-(v/maxVal)*(H-pad*2) }));
    const grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, 'rgba(212,168,67,0.35)');
    grad.addColorStop(1, 'rgba(212,168,67,0)');
    ctx.beginPath(); ctx.moveTo(pts[0].x, H-pad);
    pts.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.lineTo(pts[pts.length-1].x, H-pad); ctx.closePath();
    ctx.fillStyle = grad; ctx.fill();
    ctx.beginPath();
    pts.forEach((p,i) => i===0 ? ctx.moveTo(p.x,p.y) : ctx.lineTo(p.x,p.y));
    ctx.strokeStyle='rgba(212,168,67,0.9)'; ctx.lineWidth=2.5; ctx.stroke();
    pts.forEach(p => { ctx.beginPath(); ctx.arc(p.x,p.y,3,0,Math.PI*2); ctx.fillStyle='#d4a843'; ctx.fill(); });
  }

  return { render, fetchAndRender };
})();
Router.register('#/analytics', AnalyticsPage.render);

/* ── Settings Page ────────────────────────────────────────────────────────── */
const SettingsPage = (() => {
  async function render() {
    showPage('page-settings');
    const user = Store.get('user') || await api.getMe();
    fillForm(user);
  }

  function fillForm(user) {
    ['full_name','bio','timezone','theme'].forEach(k => {
      const el = document.getElementById(`setting-${k}`);
      if (el) el.value = user[k] || '';
    });
    document.getElementById('setting-email').textContent = user.email;
    document.getElementById('setting-username').textContent = '@' + user.username;
    const avatar = document.getElementById('settings-avatar');
    if (avatar) avatar.textContent = (user.full_name || user.username)[0].toUpperCase();
  }

  async function saveProfile() {
    const btn = document.getElementById('save-profile-btn');
    const data = {};
    ['full_name','bio','timezone','theme'].forEach(k => {
      const el = document.getElementById(`setting-${k}`);
      if (el) data[k] = el.value.trim() || null;
    });
    await withLoading(btn, async () => {
      try {
        const updated = await api.updateProfile(data);
        Store.set('user', updated);
        localStorage.setItem('current_user', JSON.stringify(updated));
        updateSidebarUser(updated);
        Toast.success('Profile updated');
      } catch (e) { Toast.error('Update failed', e.message); }
    });
  }

  async function changePassword() {
    const btn = document.getElementById('change-pwd-btn');
    const cp = document.getElementById('current-password')?.value;
    const np = document.getElementById('new-password')?.value;
    const cnp = document.getElementById('confirm-password')?.value;
    if (!cp || !np) { Toast.warning('Fill in all fields'); return; }
    if (np !== cnp) { Toast.warning('Passwords do not match'); return; }
    if (np.length < 8) { Toast.warning('Password must be at least 8 characters'); return; }
    await withLoading(btn, async () => {
      try { await api.changePassword(cp, np); Toast.success('Password changed'); ['current-password','new-password','confirm-password'].forEach(id => { const el = document.getElementById(id); if(el) el.value=''; }); }
      catch (e) { Toast.error('Change failed', e.message); }
    });
  }

  async function logout() {
    try { await api.logout(); } catch {}
    api.clearTokens();
    Store.set('user', null);
    window.location.hash = '#/login';
  }

  return { render, saveProfile, changePassword, logout };
})();
Router.register('#/settings', SettingsPage.render);

/* ── Admin Page ───────────────────────────────────────────────────────────── */
const AdminPage = (() => {
  let currentPage = 1;

  async function render() {
    showPage('page-admin');
    await Promise.all([fetchStats(), fetchUsers()]);
  }

  async function fetchStats() {
    try {
      const res = await api.adminGetStats();
      const d = res.data;
      const el = document.getElementById('admin-stats');
      if (!el) return;
      el.innerHTML = `
        <div class="glass-card stat-card" style="--accent-color:var(--gold-400)"><div class="stat-label">Total Users</div><div class="stat-value" style="color:var(--gold-400)">${d.users.total}</div></div>
        <div class="glass-card stat-card" style="--accent-color:var(--emerald)"><div class="stat-label">Active Users</div><div class="stat-value" style="color:var(--emerald)">${d.users.active}</div></div>
        <div class="glass-card stat-card" style="--accent-color:var(--sapphire)"><div class="stat-label">Total Tasks</div><div class="stat-value" style="color:var(--sapphire)">${d.tasks.total}</div></div>
        <div class="glass-card stat-card" style="--accent-color:var(--violet)"><div class="stat-label">Completion Rate</div><div class="stat-value" style="color:var(--violet)">${Math.round(d.tasks.completion_rate*100)}%</div></div>
      `;
    } catch {}
  }

  async function fetchUsers() {
    const tbody = document.getElementById('admin-users-tbody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:20px"><span class="spinner"></span></td></tr>`;
    try {
      const res = await api.adminListUsers({ page: currentPage, per_page: 20 });
      tbody.innerHTML = res.data.map(u => `
        <tr style="border-bottom:1px solid var(--glass-border)">
          <td style="padding:12px 16px"><div style="display:flex;align-items:center;gap:10px"><div class="user-avatar" style="width:28px;height:28px;font-size:0.7rem">${(u.full_name||u.username)[0].toUpperCase()}</div><div><div style="font-weight:500">${escapeHtml(u.full_name||u.username)}</div><div style="font-size:0.75rem;color:var(--text-muted)">@${u.username}</div></div></div></td>
          <td style="padding:12px 16px;font-size:0.85rem;color:var(--text-secondary)">${escapeHtml(u.email)}</td>
          <td style="padding:12px 16px">${u.is_admin ? '<span class="badge badge-urgent">Admin</span>' : '<span class="badge badge-todo">User</span>'}</td>
          <td style="padding:12px 16px">${u.is_active ? '<span class="badge badge-done">Active</span>' : '<span class="badge badge-cancelled">Disabled</span>'}</td>
          <td style="padding:12px 16px;font-size:0.8rem;color:var(--text-muted)">${u.total_tasks} tasks</td>
          <td style="padding:12px 16px">
            <div style="display:flex;gap:6px">
              <button class="btn btn-ghost btn-sm" onclick="AdminPage.toggleActive(${u.id}, ${!u.is_active})">${u.is_active ? 'Disable' : 'Enable'}</button>
              <button class="btn btn-danger btn-sm" onclick="AdminPage.deleteUser(${u.id})">Delete</button>
            </div>
          </td>
        </tr>`).join('');
    } catch (e) { tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--rose)">${e.message}</td></tr>`; }
  }

  async function toggleActive(id, active) {
    try { await api.adminUpdateUser(id, { is_active: active }); Toast.success(`User ${active ? 'enabled' : 'disabled'}`); fetchUsers(); }
    catch (e) { Toast.error('Failed', e.message); }
  }

  async function deleteUser(id) {
    if (!confirm('Delete this user? This cannot be undone.')) return;
    try { await api.adminDeleteUser(id); Toast.success('User deleted'); fetchUsers(); }
    catch (e) { Toast.error('Delete failed', e.message); }
  }

  return { render, toggleActive, deleteUser };
})();
Router.register('#/admin', AdminPage.render);

/* ── Auth Pages ───────────────────────────────────────────────────────────── */
const AuthPage = (() => {
  function renderLogin() {
    document.getElementById('auth-section').classList.remove('hidden');
    document.getElementById('app-section').classList.add('hidden');
    document.getElementById('auth-login').classList.remove('hidden');
    document.getElementById('auth-register').classList.add('hidden');
  }

  function renderRegister() {
    document.getElementById('auth-section').classList.remove('hidden');
    document.getElementById('app-section').classList.add('hidden');
    document.getElementById('auth-login').classList.add('hidden');
    document.getElementById('auth-register').classList.remove('hidden');
  }

  async function login() {
    const btn = document.getElementById('login-btn');
    const email = document.getElementById('login-email')?.value;
    const password = document.getElementById('login-password')?.value;
    if (!email || !password) { Toast.warning('Fill in all fields'); return; }
    await withLoading(btn, async () => {
      try {
        const res = await api.login(email, password, navigator.userAgent.slice(0,50));
        api.setTokens(res);
        Store.set('user', res.user);
        localStorage.setItem('current_user', JSON.stringify(res.user));
        document.getElementById('auth-section').classList.add('hidden');
        document.getElementById('app-section').classList.remove('hidden');
        updateSidebarUser(res.user);
        loadUnreadCount();
        window.location.hash = '#/dashboard';
        Toast.success(`Welcome back, ${res.user.full_name || res.user.username}!`);
      } catch (e) { Toast.error('Login failed', e.message); }
    });
  }

  async function register() {
    const btn = document.getElementById('register-btn');
    const username = document.getElementById('reg-username')?.value;
    const email = document.getElementById('reg-email')?.value;
    const password = document.getElementById('reg-password')?.value;
    const fullName = document.getElementById('reg-fullname')?.value;
    if (!username || !email || !password) { Toast.warning('Fill in all required fields'); return; }
    await withLoading(btn, async () => {
      try {
        await api.register(username, email, password, fullName);
        Toast.success('Account created! Please log in.');
        renderLogin();
        window.location.hash = '#/login';
      } catch (e) { Toast.error('Registration failed', e.message); }
    });
  }

  return { renderLogin, renderRegister, login, register };
})();

Router.register('#/login', AuthPage.renderLogin);
Router.register('#/register', AuthPage.renderRegister);

/* ── Helper: show page ───────────────────────────────────────────────────── */
function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const target = document.getElementById(id);
  if (target) target.classList.add('active');
  if (api.isAuthenticated()) {
    document.getElementById('auth-section')?.classList.add('hidden');
    document.getElementById('app-section')?.classList.remove('hidden');
  }
}
