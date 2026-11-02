import { clearCurrentUser, getCurrentUser, getDemoState, setDemoState } from './api.js';
import { escapeHtml, icon, roleLabel } from './components.js';
import {
  activeNavKey, canAccess, getNavItems, navigate, parseRoute, roleHome, ROUTE_META
} from './router.js';
import { renderLoginPage } from './pages/login.js';
import { renderDashboardPage } from './pages/dashboard.js';
import { renderShortagesPage } from './pages/shortages.js';
import { renderInventoryPage } from './pages/inventory.js';
import { renderQueryPage } from './pages/query.js';
import { renderDetailPage } from './pages/detail.js';
import { renderSimulatePage } from './pages/simulate.js';
import { renderImportPage } from './pages/import.js';
import { renderComparePage } from './pages/compare.js';
import { renderMasterPage } from './pages/master.js';
import { renderUsersPage } from './pages/users.js';

const app = document.querySelector('#app');
const PAGE_RENDERERS = {
  login: renderLoginPage,
  dashboard: renderDashboardPage,
  query: renderQueryPage,
  shortages: renderShortagesPage,
  inventory: renderInventoryPage,
  detail: renderDetailPage,
  simulate: renderSimulatePage,
  import: renderImportPage,
  compare: renderComparePage,
  master: renderMasterPage,
  users: renderUsersPage
};
const STATE_LABELS = {
  ready: 'ready · 正常数据',
  loading: 'loading · 加载中',
  empty: 'empty · 空数据',
  error: 'error · 可重试错误'
};

function sidebar(user, route) {
  const active = activeNavKey(route);
  const groups = getNavItems(user.role);
  return `
    <aside class="sidebar" id="sidebar" aria-label="主导航">
      <div class="sidebar-inner">
        <a class="brand" href="${roleHome(user.role)}" aria-label="交期领航首页">
          <div class="brand-mark">${icon('logo', 'icon icon-lg')}</div>
          <div><div class="brand-name">交期领航</div><div class="brand-sub">DELIVERY PROMISE</div></div>
        </a>
        ${groups.map((group) => `
          <nav class="nav-section" aria-label="${escapeHtml(group.label)}">
            <div class="nav-label">${escapeHtml(group.label)}</div>
            ${group.items.map((item) => `
              <a class="nav-link ${active === item.key ? 'active' : ''}" href="${item.href}" ${active === item.key ? 'aria-current="page"' : ''}>
                ${icon(item.icon)}<span class="nav-text">${escapeHtml(item.label)}</span>
              </a>`).join('')}
          </nav>`).join('')}
        <div class="sidebar-footer">
          <div class="sidebar-panel">
            <div class="sidebar-panel-title"><span>演示状态</span><span class="badge badge-neutral">?state=</span></div>
            <div class="sidebar-panel-note">切换后当前页立即重载，用于 G1 四态走查。</div>
            <select class="state-select" id="demo-state" aria-label="切换四态演示">
              ${Object.entries(STATE_LABELS).map(([value, label]) => `<option value="${value}" ${getDemoState() === value ? 'selected' : ''}>${label}</option>`).join('')}
            </select>
          </div>
          <div class="user-mini">
            <span class="avatar">${escapeHtml(user.name.slice(0, 1))}</span>
            <div style="min-width:0;flex:1"><div class="user-mini-name">${escapeHtml(user.name)}</div><div class="user-mini-meta">${escapeHtml(roleLabel(user.role))} · ${escapeHtml(user.department)}</div></div>
            <button class="button button-ghost button-icon button-sm" type="button" id="logout" aria-label="退出登录" title="退出登录">${icon('logout', 'icon icon-sm')}</button>
          </div>
          <div class="small" style="color:var(--color-on-sidebar-muted);padding:0 var(--space-2);font-size:10px">G1 MOCK · PORT 8003</div>
        </div>
      </div>
    </aside>`;
}

function shell(user, route, pageHtml, pageTitle) {
  const meta = ROUTE_META[route.name] || ROUTE_META.query;
  return `
    <div class="app-shell">
      ${sidebar(user, route)}
      <div class="main-shell">
        <header class="topbar">
          <div class="topbar-left">
            <button class="button button-ghost button-icon button-sm mobile-menu" type="button" id="mobile-menu" aria-label="打开导航" aria-controls="sidebar">${icon('menu', 'icon icon-sm')}</button>
            <div class="breadcrumb"><span>交付工作台</span><span>/</span><strong>${escapeHtml(pageTitle || meta.title)}</strong></div>
            <div class="topbar-context"><span class="status-dot"></span><span>${escapeHtml(getDemoState() === 'ready' ? 'mock 数据已载入' : `演示状态：${getDemoState()}`)}</span></div>
          </div>
          <div class="topbar-actions">
            <span class="role-chip">${icon('shield', 'icon icon-sm')}${escapeHtml(roleLabel(user.role))}视角</span>
          </div>
        </header>
        <main class="content" id="main-content">${pageHtml}</main>
      </div>
    </div>`;
}

function accessDenied(user) {
  const html = `
    <div class="page">
      <header class="page-header"><div><div class="page-kicker">${icon('lock', 'icon icon-sm')} Access denied</div><h1 class="page-title">当前角色无权访问</h1><p class="page-subtitle">${escapeHtml(roleLabel(user.role))}角色的菜单与可见范围已按权限收紧。可切换到主管或管理员演示完整能力。</p></div></header>
      <div class="state-panel empty">
        <div class="state-icon">${icon('lock', 'icon icon-lg')}</div>
        <h2 class="state-title">没有该页面的访问权限</h2>
        <p class="state-text">直接输入 URL 也不会绕过角色授权。请返回订单查询，或从登录页切换演示角色。</p>
        <div class="state-actions"><a class="button button-primary" href="${roleHome(user.role)}">返回工作台</a><a class="button button-secondary" href="#/login">切换角色</a></div>
      </div>
    </div>`;
  return { html, mount() {}, title: '无权访问' };
}

function render() {
  document.querySelector('#toast-root')?.replaceChildren();
  const route = parseRoute();
  const user = getCurrentUser();
  const state = getDemoState();

  if (!user && route.name !== 'login') {
    navigate('#/login', { replace: true });
    return;
  }

  const page = PAGE_RENDERERS[route.name] || renderQueryPage;
  let rendered;
  if (route.name !== 'login' && !canAccess(route.name, user)) {
    rendered = accessDenied(user);
  } else {
    rendered = page({ user, state, params: route.params });
  }

  document.title = `${rendered.title || '交期领航'} · 交期领航`;
  if (rendered.fullPage) {
    app.innerHTML = rendered.html;
  } else {
    app.innerHTML = shell(user, route, rendered.html, rendered.title);
  }
  rendered.mount?.(app);

  app.querySelector('#demo-state')?.addEventListener('change', (event) => {
    setDemoState(event.target.value);
    render();
  });
  app.querySelector('#logout')?.addEventListener('click', () => {
    clearCurrentUser();
    navigate('#/login', { replace: true });
  });
  app.querySelector('#mobile-menu')?.addEventListener('click', () => {
    app.querySelector('#sidebar')?.classList.toggle('open');
  });
  app.querySelectorAll('.sidebar .nav-link, .brand').forEach((link) => link.addEventListener('click', () => {
    app.querySelector('#sidebar')?.classList.remove('open');
  }));
  app.querySelector('#main-content')?.addEventListener('click', () => {
    app.querySelector('#sidebar')?.classList.remove('open');
  });
}

window.addEventListener('hashchange', render);
window.addEventListener('DOMContentLoaded', () => {
  if (!window.location.hash) {
    const current = getCurrentUser();
    const target = current ? roleHome(current.role) : '#/login';
    navigate(target, { replace: true });
    return;
  }
  render();
});



