import { downloadFile, fetchUsers, setDemoState } from '../api.js';
import { escapeHtml, formatNumber, icon, roleBadge, roleLabel, stateView, showToast } from '../components.js';

function userRows(users) {
  return users.map((user) => `
    <tr>
      <td class="mono primary-cell">${escapeHtml(user.account)}</td>
      <td>${escapeHtml(user.name)}</td>
      <td>${roleBadge(user.role)}</td>
      <td class="hide-mobile">${escapeHtml(user.department)}</td>
      <td><div class="toolbar">${user.customer_scopes.map((scope) => `<span class="badge badge-neutral">${escapeHtml(scope)}</span>`).join('')}</div></td>
      <td><span class="badge ${user.status === '启用' ? 'badge-success' : 'badge-neutral'}"><span class="dot"></span>${escapeHtml(user.status)}</span></td>
      <td class="hide-mobile">${escapeHtml(user.last_login)}</td>
      <td class="actions-cell"><button class="link-button" type="button" data-edit-user="${escapeHtml(user.account)}">编辑授权</button></td>
    </tr>`).join('');
}

export function renderUsersPage({ state }) {
  const html = `
    <div class="page">
      <header class="page-header">
        <div>
          <div class="page-kicker">${icon('users', 'icon icon-sm')} Access control</div>
          <h1 class="page-title">用户管理</h1>
          <p class="page-subtitle">维护账号、角色与授权客户范围。销售只能看到自己客户范围内的订单，计划/主管默认全量。</p>
        </div>
        <div class="page-actions">
          <button class="button button-secondary button-sm" type="button" id="export-users">${icon('download', 'icon icon-sm')}导出清单</button>
          <button class="button button-primary button-sm" type="button" id="add-user">${icon('plus', 'icon icon-sm')}新增账号</button>
        </div>
      </header>
      <div id="users-root">
        ${state === 'ready' ? '<div class="card card-pad"><div class="skeleton skeleton-table"></div></div>' : stateView(state, { emptyTitle: '暂无用户', errorTitle: '用户列表加载失败' })}
      </div>
      <div class="modal-backdrop" id="user-modal" hidden>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="user-modal-title">
          <div class="modal-header"><div><h2 class="modal-title" id="user-modal-title">编辑账号</h2><div class="small muted">G1 仅演示结构，不写回 mock 文件</div></div><button class="button button-ghost button-icon button-sm" type="button" data-close-modal aria-label="关闭">${icon('close', 'icon icon-sm')}</button></div>
          <form class="modal-body stack" id="user-form">
            <div class="form-grid">
              <label class="field"><span class="field-label">账号</span><input class="input" name="account" id="user-account" required /></label>
              <label class="field"><span class="field-label">姓名</span><input class="input" name="name" id="user-name" required /></label>
              <label class="field"><span class="field-label">角色</span><select class="select" name="role" id="user-role"><option value="sales">销售</option><option value="planner">计划</option><option value="supervisor">主管</option><option value="admin">管理员</option></select></label>
              <label class="field"><span class="field-label">状态</span><select class="select" name="status" id="user-status"><option value="启用">启用</option><option value="停用">停用</option></select></label>
              <label class="field form-span"><span class="field-label">授权客户范围</span><input class="input" name="scopes" id="user-scopes" placeholder="多个客户用逗号分隔；管理员/计划可填“全部客户”" /><span class="field-hint">销售角色必须填写具体客户范围。</span></label>
            </div>
            <div class="inline-meta" style="padding:var(--space-3);border-radius:var(--radius-md);background:var(--color-primary-soft);color:var(--color-primary-ink)">${icon('shield', 'icon icon-sm')}权限变更会记录审计日志（后端阶段接入）。</div>
          </form>
          <div class="modal-footer"><button class="button button-secondary" type="button" data-close-modal>取消</button><button class="button button-primary" type="submit" form="user-form">保存授权</button></div>
        </div>
      </div>
    </div>`;

  function mount(root) {
    const target = root.querySelector('#users-root');
    const modal = root.querySelector('#user-modal');
    const form = root.querySelector('#user-form');
    let users = [];
    let filtered = [];
    let lastTrigger = null;

    function openModal(user = null) {
      lastTrigger = document.activeElement;
      root.querySelector('#user-account').value = user?.account || '';
      root.querySelector('#user-account').readOnly = Boolean(user);
      root.querySelector('#user-name').value = user?.name || '';
      root.querySelector('#user-role').value = user?.role || 'sales';
      root.querySelector('#user-status').value = user?.status || '启用';
      root.querySelector('#user-scopes').value = user?.customer_scopes?.join('，') || '';
      modal.hidden = false;
      root.querySelector('#user-account').focus();
    }

    function closeModal() {
      modal.hidden = true;
      lastTrigger?.focus();
    }

    function renderList() {
      if (!target.querySelector('#users-table')) return;
      const rows = filtered.length ? userRows(filtered) : '<tr><td colspan="8" class="table-empty">没有匹配的账号</td></tr>';
      target.querySelector('#users-table').innerHTML = `<div class="table-wrap flush"><table class="data-table"><thead><tr><th>账号</th><th>姓名</th><th>角色</th><th class="hide-mobile">部门</th><th>授权客户范围</th><th>状态</th><th class="hide-mobile">最近登录</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`;
      target.querySelectorAll('[data-edit-user]').forEach((button) => button.addEventListener('click', () => {
        openModal(users.find((item) => item.account === button.dataset.editUser));
      }));
    }

    function renderContent(payload) {
      const enabled = payload.users.filter((user) => user.status === '启用').length;
      const sales = payload.users.filter((user) => user.role === 'sales').length;
      target.innerHTML = `
        <div class="stack">
          <div class="grid-3">
            <div class="metric-card"><div class="metric-label">账号总数</div><div class="metric-value">${formatNumber(payload.users.length, 0)}</div><div class="metric-foot">销售 / 计划 / 主管 / 管理员</div></div>
            <div class="metric-card"><div class="metric-label">启用账号</div><div class="metric-value success">${formatNumber(enabled, 0)}</div><div class="metric-foot">停用账号不能登录</div></div>
            <div class="metric-card"><div class="metric-label">销售账号</div><div class="metric-value">${formatNumber(sales, 0)}</div><div class="metric-foot">按客户范围隔离订单</div></div>
          </div>
          <section class="card">
            <div class="card-header"><div><h2 class="section-title">账号与授权</h2><div class="section-note">角色决定菜单；客户范围决定订单可见性</div></div><div class="toolbar"><div class="search-field" style="flex-basis:240px">${icon('search', 'icon icon-sm')}<input class="input" id="user-search" placeholder="搜索账号 / 姓名 / 客户" /></div><select class="select" id="role-filter" style="width:126px"><option value="">全部角色</option><option value="sales">销售</option><option value="planner">计划</option><option value="supervisor">主管</option><option value="admin">管理员</option></select></div></div>
            <div id="users-table"></div>
            <div class="card-footer"><span class="small muted">最近更新 ${escapeHtml(payload.updated_at)}</span><span class="badge badge-info">ADMIN ONLY</span></div>
          </section>
        </div>`;
      renderList();

      target.querySelector('#user-search').addEventListener('input', applyFilters);
      target.querySelector('#role-filter').addEventListener('change', applyFilters);
    }

    function applyFilters() {
      const query = target.querySelector('#user-search')?.value.trim().toLowerCase() || '';
      const role = target.querySelector('#role-filter')?.value || '';
      filtered = users.filter((user) => {
        const matchQuery = !query || [user.account, user.name, user.department, ...user.customer_scopes].some((field) => String(field).toLowerCase().includes(query));
        return matchQuery && (!role || user.role === role);
      });
      renderList();
    }

    async function load() {
      if (state !== 'ready') return;
      try {
        const payload = await fetchUsers();
        users = payload.users;
        filtered = [...users];
        renderContent(payload);
      } catch (reason) {
        target.innerHTML = stateView('error', { errorTitle: '用户列表加载失败', errorText: reason.message });
      }
    }

    root.querySelector('#add-user').addEventListener('click', () => openModal());
    root.querySelectorAll('[data-close-modal]').forEach((button) => button.addEventListener('click', closeModal));
    modal.addEventListener('click', (event) => { if (event.target === modal) closeModal(); });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !modal.hidden) closeModal();
      if (event.key === 'Tab' && !modal.hidden) {
        const focusable = [...modal.querySelectorAll('button, input, select, [href]')].filter((item) => !item.disabled && !item.hidden);
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      closeModal();
      showToast('授权已保存（mock 演示，不写回文件）');
    });

    root.querySelector('#export-users').addEventListener('click', () => {
      const lines = ['account,name,role,department,status,customer_scopes'];
      filtered.forEach((user) => lines.push([user.account, user.name, roleLabel(user.role), user.department, user.status, user.customer_scopes.join('|')].join(',')));
      downloadFile('users.csv', `\uFEFF${lines.join('\n')}`, 'text/csv;charset=utf-8');
    });

    target.addEventListener('click', (event) => {
      if (event.target.closest('[data-retry]')) {
        setDemoState('ready');
        window.dispatchEvent(new HashChangeEvent('hashchange'));
      }
    });
    load();
  }

  return { html, mount, title: '用户管理' };
}

