/**
 * Tasks Page
 */
const TasksPage = (() => {
  let currentPage = 1;
  let currentFilters = {};
  let totalPages = 1;
  let editingTaskId = null;

  // ── Render ──────────────────────────────────────────────────────────────────
  async function render() {
    showPage('page-tasks');
    currentPage = 1;
    currentFilters = {};
    await fetchAndRender();
    bindEvents();
  }

  async function fetchAndRender() {
    const container = document.getElementById('task-list-container');
    container.innerHTML = skeletonTasks(5);
    try {
      const params = { page: currentPage, per_page: 20, ...currentFilters };
      const res = await api.getTasks(params);
      totalPages = res.meta.total_pages;
      renderTaskList(res.data);
      renderPagination(res.meta);
    } catch (e) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-title">${e.message}</div></div>`;
    }
  }

  function renderTaskList(tasks) {
    const container = document.getElementById('task-list-container');
    if (!tasks.length) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">✅</div>
          <div class="empty-state-title">No tasks found</div>
          <div class="empty-state-desc">Create your first task to get started</div>
        </div>`;
      return;
    }
    container.innerHTML = `<div class="task-list">${tasks.map(taskCard).join('')}</div>`;
  }

  function taskCard(t) {
    const due = t.due_date;
    const overdueClass = isOverdue(due) ? 'overdue' : isDueSoon(due) ? 'soon' : '';
    const pinClass = t.is_pinned ? 'pinned' : '';
    const doneClass = t.status === 'completed' ? 'completed' : '';
    return `
    <div class="glass-card task-card ${pinClass} ${doneClass}" data-id="${t.id}" onclick="TasksPage.openDetail(${t.id})">
      <div class="task-card-header">
        <div class="task-checkbox ${t.status === 'completed' ? 'checked' : ''}"
             onclick="event.stopPropagation(); TasksPage.toggleComplete(${t.id}, '${t.status}')"></div>
        <div class="task-title ${t.status === 'completed' ? 'done' : ''}">${escapeHtml(t.title)}</div>
        ${t.is_pinned ? '<span class="task-pin">📌</span>' : ''}
      </div>
      <div class="task-meta">
        ${statusBadge(t.status)}
        ${priorityBadge(t.priority)}
        <span class="badge" style="background:var(--obsidian-600);color:var(--text-muted)">${categoryIcon(t.category)} ${t.category}</span>
        ${due ? `<span class="task-due ${overdueClass}">📅 ${formatDate(due)}</span>` : ''}
      </div>
      ${t.progress_percentage > 0 ? `
      <div class="progress-track">
        <div class="progress-fill ${t.status==='completed'?'complete':''}" style="width:${t.progress_percentage}%"></div>
      </div>` : ''}
      <div class="task-footer">
        <span class="task-subtask-count">
          ${t.subtask_count > 0 ? `☑ ${t.completed_subtask_count}/${t.subtask_count} subtasks` : ''}
        </span>
        <div class="task-actions">
          <button class="task-action-btn" onclick="event.stopPropagation(); TasksPage.openEdit(${t.id})" data-tooltip="Edit">✏️</button>
          <button class="task-action-btn" onclick="event.stopPropagation(); TasksPage.pin(${t.id}, ${!t.is_pinned})" data-tooltip="${t.is_pinned ? 'Unpin' : 'Pin'}">📌</button>
          <button class="task-action-btn danger" onclick="event.stopPropagation(); TasksPage.confirmDelete(${t.id})" data-tooltip="Delete">🗑</button>
        </div>
      </div>
    </div>`;
  }

  function renderPagination(meta) {
    const el = document.getElementById('task-pagination');
    if (!el) return;
    if (meta.total_pages <= 1) { el.innerHTML = ''; return; }
    el.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;justify-content:center;margin-top:20px">
        <button class="btn btn-ghost btn-sm" ${!meta.has_prev ? 'disabled' : ''} onclick="TasksPage.goPage(${meta.page - 1})">← Prev</button>
        <span class="text-sm text-muted">Page ${meta.page} of ${meta.total_pages}</span>
        <button class="btn btn-ghost btn-sm" ${!meta.has_next ? 'disabled' : ''} onclick="TasksPage.goPage(${meta.page + 1})">Next →</button>
      </div>`;
  }

  // ── Events ──────────────────────────────────────────────────────────────────
  function bindEvents() {
    // Filter chips
    document.querySelectorAll('#page-tasks .filter-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const key = chip.dataset.filter;
        const val = chip.dataset.value;
        document.querySelectorAll(`#page-tasks .filter-chip[data-filter="${key}"]`).forEach(c => c.classList.remove('active'));
        if (currentFilters[key] === val) {
          delete currentFilters[key];
        } else {
          chip.classList.add('active');
          currentFilters[key] = val;
        }
        currentPage = 1;
        fetchAndRender();
      });
    });

    // Search
    const searchEl = document.getElementById('task-search');
    if (searchEl) {
      searchEl.addEventListener('input', debounce(e => {
        currentFilters.search = e.target.value.trim() || undefined;
        currentPage = 1;
        fetchAndRender();
      }));
    }

    // Sort
    const sortEl = document.getElementById('task-sort');
    if (sortEl) {
      sortEl.addEventListener('change', () => {
        const [sort_by, sort_order] = sortEl.value.split(':');
        currentFilters.sort_by = sort_by;
        currentFilters.sort_order = sort_order;
        fetchAndRender();
      });
    }
  }

  // ── Actions ─────────────────────────────────────────────────────────────────
  async function toggleComplete(id, currentStatus) {
    const newStatus = currentStatus === 'completed' ? 'todo' : 'completed';
    try {
      await api.updateTaskStatus(id, newStatus);
      await fetchAndRender();
    } catch (e) { Toast.error('Update failed', e.message); }
  }

  async function pin(id, pinned) {
    try {
      await api.updateTask(id, { is_pinned: pinned });
      await fetchAndRender();
    } catch (e) { Toast.error('Update failed', e.message); }
  }

  async function openDetail(id) {
    try {
      const task = await api.getTask(id);
      renderDetailModal(task);
      Modal.open('modal-task-detail');
    } catch (e) { Toast.error('Failed to load task', e.message); }
  }

  async function openEdit(id) {
    editingTaskId = id;
    try {
      const task = await api.getTask(id);
      fillTaskForm(task);
      document.getElementById('task-form-title').textContent = 'Edit Task';
      Modal.open('modal-task-form');
    } catch (e) { Toast.error('Failed to load task', e.message); }
  }

  function openCreate() {
    editingTaskId = null;
    resetTaskForm();
    document.getElementById('task-form-title').textContent = 'New Task';
    Modal.open('modal-task-form');
  }

  async function confirmDelete(id) {
    if (!confirm('Delete this task? This cannot be undone.')) return;
    try {
      await api.deleteTask(id);
      Toast.success('Task deleted');
      await fetchAndRender();
    } catch (e) { Toast.error('Delete failed', e.message); }
  }

  async function saveTask() {
    const btn = document.getElementById('task-save-btn');
    const data = getTaskFormData();
    if (!data.title.trim()) { Toast.warning('Title required'); return; }
    await withLoading(btn, async () => {
      try {
        if (editingTaskId) {
          await api.updateTask(editingTaskId, data);
          Toast.success('Task updated');
        } else {
          await api.createTask(data);
          Toast.success('Task created');
        }
        Modal.close('modal-task-form');
        await fetchAndRender();
      } catch (e) { Toast.error('Save failed', e.message); }
    });
  }

  async function goPage(page) {
    currentPage = page;
    await fetchAndRender();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ── Task Detail Modal ────────────────────────────────────────────────────────
  function renderDetailModal(task) {
    const body = document.getElementById('task-detail-body');
    body.innerHTML = `
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">
        ${statusBadge(task.status)} ${priorityBadge(task.priority)}
        <span class="badge" style="background:var(--obsidian-600);color:var(--text-muted)">${categoryIcon(task.category)} ${task.category}</span>
      </div>
      ${task.description ? `<p style="color:var(--text-secondary);font-size:0.9rem;margin-bottom:16px;line-height:1.6">${escapeHtml(task.description)}</p>` : ''}
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px">
        ${task.due_date ? `<div><div class="form-label">Due Date</div><div>${formatDate(task.due_date)}</div></div>` : ''}
        ${task.estimated_hours ? `<div><div class="form-label">Estimated</div><div>${task.estimated_hours}h</div></div>` : ''}
        ${task.actual_hours ? `<div><div class="form-label">Actual</div><div>${task.actual_hours}h</div></div>` : ''}
        ${task.completed_at ? `<div><div class="form-label">Completed</div><div>${new Date(task.completed_at).toLocaleDateString()}</div></div>` : ''}
      </div>
      <div style="margin-bottom:16px">
        <div class="form-label" style="margin-bottom:8px">Progress</div>
        <div class="progress-track"><div class="progress-fill ${task.status==='completed'?'complete':''}" style="width:${task.progress_percentage}%"></div></div>
        <div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px">${task.progress_percentage}% complete</div>
      </div>
      ${task.subtasks?.length ? `
        <div>
          <div class="form-label" style="margin-bottom:8px">Subtasks (${task.subtasks.filter(s=>s.status==='completed').length}/${task.subtasks.length})</div>
          <div style="display:flex;flex-direction:column;gap:6px">
            ${task.subtasks.map(s => `
              <div style="display:flex;align-items:center;gap:8px;padding:8px 10px;background:var(--obsidian-700);border-radius:8px">
                <div class="task-checkbox ${s.status==='completed'?'checked':''}" style="width:16px;height:16px;border-radius:4px"
                     onclick="SubtaskManager.toggle(${task.id}, ${s.id}, '${s.status}', this)"></div>
                <span style="font-size:0.85rem;${s.status==='completed'?'text-decoration:line-through;color:var(--text-muted)':''}">${escapeHtml(s.title)}</span>
              </div>`).join('')}
          </div>
        </div>` : ''}
      <div style="display:flex;gap:8px;margin-top:20px">
        <button class="btn btn-ghost btn-sm" onclick="Modal.close('modal-task-detail'); TasksPage.openEdit(${task.id})">✏️ Edit</button>
        <button class="btn btn-danger btn-sm" onclick="Modal.close('modal-task-detail'); TasksPage.confirmDelete(${task.id})">🗑 Delete</button>
      </div>
    `;
    document.getElementById('task-detail-title').textContent = task.title;
  }

  // ── Form helpers ─────────────────────────────────────────────────────────────
  function getTaskFormData() {
    return {
      title: document.getElementById('tf-title')?.value || '',
      description: document.getElementById('tf-description')?.value || '',
      priority: document.getElementById('tf-priority')?.value || 'medium',
      category: document.getElementById('tf-category')?.value || 'other',
      status: document.getElementById('tf-status')?.value || 'todo',
      due_date: document.getElementById('tf-due-date')?.value || null,
      estimated_hours: parseFloat(document.getElementById('tf-hours')?.value) || null,
      is_pinned: document.getElementById('tf-pinned')?.checked || false,
      tags: document.getElementById('tf-tags')?.value || null,
    };
  }

  function fillTaskForm(task) {
    document.getElementById('tf-title').value = task.title || '';
    document.getElementById('tf-description').value = task.description || '';
    document.getElementById('tf-priority').value = task.priority || 'medium';
    document.getElementById('tf-category').value = task.category || 'other';
    document.getElementById('tf-status').value = task.status || 'todo';
    document.getElementById('tf-due-date').value = task.due_date ? task.due_date.slice(0, 16) : '';
    document.getElementById('tf-hours').value = task.estimated_hours || '';
    document.getElementById('tf-pinned').checked = task.is_pinned || false;
    document.getElementById('tf-tags').value = task.tags || '';
  }

  function resetTaskForm() {
    ['tf-title','tf-description','tf-due-date','tf-hours','tf-tags'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    const prio = document.getElementById('tf-priority');
    if (prio) prio.value = 'medium';
    const cat = document.getElementById('tf-category');
    if (cat) cat.value = 'other';
    const stat = document.getElementById('tf-status');
    if (stat) stat.value = 'todo';
    const pinned = document.getElementById('tf-pinned');
    if (pinned) pinned.checked = false;
  }

  function skeletonTasks(n) {
    return Array(n).fill(0).map(() => `
      <div class="glass-card" style="padding:18px 20px;margin-bottom:10px">
        <div style="display:flex;gap:12px;align-items:center">
          <div class="skeleton" style="width:20px;height:20px;border-radius:6px"></div>
          <div class="skeleton" style="height:16px;flex:1;border-radius:4px"></div>
        </div>
        <div style="display:flex;gap:8px;margin-top:10px">
          <div class="skeleton" style="height:20px;width:60px;border-radius:99px"></div>
          <div class="skeleton" style="height:20px;width:60px;border-radius:99px"></div>
        </div>
      </div>`).join('');
  }

  return { render, fetchAndRender, toggleComplete, pin, openDetail, openEdit, openCreate, confirmDelete, saveTask, goPage };
})();

// ── SubtaskManager ────────────────────────────────────────────────────────────
const SubtaskManager = {
  async toggle(taskId, subtaskId, currentStatus, checkboxEl) {
    const newStatus = currentStatus === 'completed' ? 'todo' : 'completed';
    try {
      await api.updateSubtask(taskId, subtaskId, { status: newStatus });
      checkboxEl.classList.toggle('checked', newStatus === 'completed');
      const title = checkboxEl.nextElementSibling;
      if (title) {
        title.style.textDecoration = newStatus === 'completed' ? 'line-through' : '';
        title.style.color = newStatus === 'completed' ? 'var(--text-muted)' : '';
      }
      checkboxEl.setAttribute('onclick', `SubtaskManager.toggle(${taskId}, ${subtaskId}, '${newStatus}', this)`);
    } catch (e) { Toast.error('Update failed', e.message); }
  },
};

Router.register('#/tasks', TasksPage.render);
