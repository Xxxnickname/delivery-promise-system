import { fetchOrders, downloadFile, setDemoState } from '../api.js';
import { conclusionCard, escapeHtml, formatNumber, icon, orderListModalMarkup, roleLabel, stateView } from '../components.js';
import { lineChart } from '../charts.js';

const QUERY_TREND = [
  { label: '10/26', value: 12 }, { label: '10/27', value: 18 }, { label: '10/28', value: 15 },
  { label: '10/29', value: 21 }, { label: '10/30', value: 19 }, { label: '10/31', value: 26 }, { label: '11/01', value: 24 }
];

function loadingSkeleton() {
  return `
    <div class="result-strip">
      ${[1, 2, 3].map(() => '<div class="metric-card"><div class="skeleton skeleton-line short"></div><div class="skeleton skeleton-line"></div></div>').join('')}
    </div>
    <div class="split-main">
      <div class="card card-pad"><div class="skeleton skeleton-table"></div></div>
      <div class="card card-pad"><div class="skeleton skeleton-card"></div></div>
    </div>`;
}

function resultMarkup(orders, user) {
  if (!orders.length) {
    return stateView('empty', {
      emptyTitle: '没有匹配的订单',
      emptyText: '订单号、客户或产品名称都可以搜索。销售角色只显示授权客户范围内的订单。',
      emptyAction: '<button class="button button-secondary button-sm" type="button" data-clear-search>清空搜索</button>'
    });
  }

  const latest = orders[0];
  const commitOrders = orders.filter((order) => order.can_commit);
  const delayOrders = orders.filter((order) => !order.can_commit);
  const commitCount = commitOrders.length;
  const delayCount = delayOrders.length;
  const tableRows = orders.slice(0, 5).map((order) => `
    <tr>
      <td class="mono primary-cell"><a class="order-link" href="#/order/${encodeURIComponent(order.order_no)}">${escapeHtml(order.order_no)}</a></td>
      <td>${escapeHtml(order.customer)}</td>
      <td class="hide-mobile">${escapeHtml(order.product_name)}</td>
      <td>${escapeHtml(order.due_date)}</td>
      <td><span class="badge ${order.can_commit ? 'badge-success' : 'badge-danger'}"><span class="dot"></span>${order.can_commit ? `可承诺 ${escapeHtml(order.due_date)}` : `延期 ${escapeHtml(order.delay_days)} 天`}</span></td>
      <td class="actions-cell"><a class="link-button" href="#/order/${encodeURIComponent(order.order_no)}">查看 ${icon('chevron', 'icon icon-sm')}</a></td>
    </tr>`).join('');

  return `
    <div class="result-strip">
      <button class="metric-card metric-card-button" type="button" data-open-order-modal="query-all-modal">
        <div class="metric-label"><span>当前可见订单</span>${icon('orders', 'icon icon-sm')}</div>
        <div class="metric-value">${formatNumber(orders.length, 0)}</div>
        <div class="metric-foot">${escapeHtml(user?.role === 'sales' ? '按授权客户范围过滤' : '全部客户 · mock 数据')} · 点击查看</div>
      </button>
      <button class="metric-card metric-card-button" type="button" data-open-order-modal="query-commit-modal">
        <div class="metric-label"><span>可按期交付</span>${icon('check', 'icon icon-sm')}</div>
        <div class="metric-value success">${formatNumber(commitCount, 0)}</div>
        <div class="metric-foot">点击查看可承诺订单</div>
      </button>
      <button class="metric-card metric-card-button" type="button" data-open-order-modal="query-delay-modal">
        <div class="metric-label"><span>需关注延期</span>${icon('alert', 'icon icon-sm')}</div>
        <div class="metric-value danger">${formatNumber(delayCount, 0)}</div>
        <div class="metric-foot">点击查看延期订单</div>
      </button>
    </div>

    <div class="split-main">
      <section class="card" aria-labelledby="recent-title">
        <div class="card-header">
          <div><h2 class="section-title" id="recent-title">最近查询</h2><div class="section-note">最多展示 5 条 · 点击表头可排序</div></div>
          <a class="button button-ghost button-sm" href="#/simulate">去模拟 ${icon('arrow', 'icon icon-sm')}</a>
        </div>
        <div class="table-wrap flush">
          <table class="data-table recent-table" aria-label="最近查询订单">
            <thead><tr>
              <th><button class="link-button" type="button" data-sort="order_no">订单号</button></th>
              <th>客户</th>
              <th class="hide-mobile">产品</th>
              <th><button class="link-button" type="button" data-sort="due_date">客户交期</button></th>
              <th>结论</th><th></th>
            </tr></thead>
            <tbody>${tableRows}</tbody>
          </table>
        </div>
        <div class="card-footer"><span class="small muted">数据版本 gen-1.0 · 更新于 2026-11-01 14:32</span><span class="badge badge-primary">MOCK</span></div>
      </section>

      <aside class="stack">
        <div class="section-head"><h2 class="section-title">最新结论</h2><span class="section-note">${escapeHtml(roleLabel(user?.role))}视角</span></div>
        ${conclusionCard(latest)}
        <div class="chart-figure">
          <div class="chart-head"><div><div class="chart-title">近 7 天订单查询</div><div class="small muted">演示趋势，不参与业务计算</div></div><div class="chart-legend"><span class="legend-dot" style="background:var(--color-primary)"></span>查询次数</div></div>
          ${lineChart(QUERY_TREND, { width: 480, height: 160, ariaLabel: '近七天订单查询趋势' })}
        </div>
      </aside>
    </div>
    ${orderListModalMarkup({ id: 'query-all-modal', title: '当前可见订单', subtitle: '按当前搜索条件', orders })}
    ${orderListModalMarkup({ id: 'query-commit-modal', title: '可按期交付订单', subtitle: '可承诺日期已满足客户交期', orders: commitOrders })}
    ${orderListModalMarkup({ id: 'query-delay-modal', title: '延期订单明细', subtitle: '按延期天数查看影响', orders: delayOrders })}`;
}

export function renderQueryPage({ user, state }) {
  const isSales = user?.role === 'sales';
  const pageTitle = isSales ? '我的订单' : '订单查询';
  const html = `
    <div class="page">
      <header class="page-header">
        <div>
          <div class="page-kicker">${icon('search', 'icon icon-sm')} ${isSales ? 'My orders' : 'Promise desk'}</div>
          <h1 class="page-title">${pageTitle}</h1>
          <p class="page-subtitle">${isSales ? '只看授权客户范围内的订单：可承诺日期、齐套日与风险标签首屏可见。' : '输入订单号或客户名称，首屏直接看到可承诺日期、齐套日与风险标签。明细可下钻，不在前端推导业务数字。'}</p>
        </div>
        <div class="page-actions">
          <button class="button button-secondary button-sm" type="button" id="query-refresh">${icon('refresh', 'icon icon-sm')}刷新</button>
          <button class="button button-primary button-sm" type="button" id="query-export">${icon('download', 'icon icon-sm')}导出结果</button>
        </div>
      </header>

      <section class="query-hero" aria-labelledby="query-form-title">
        <div class="query-hero-row">
          <form class="search-field" id="query-form" role="search">
            <label class="sr-only" for="query-input" id="query-form-title">搜索订单</label>
            ${icon('search')}
            <input class="input" id="query-input" name="q" placeholder="搜索订单号 / 客户 / 产品，例如 SO202601004" autocomplete="off" />
          </form>
          <button class="button button-primary" type="submit" form="query-form">查询结论</button>
          <span class="role-chip">${icon('shield', 'icon icon-sm')}${escapeHtml(user?.role === 'sales' ? '仅授权客户' : '全量客户')}</span>
        </div>
        <div class="quick-queries"><span>快速查看</span>
          <button class="quick-chip" type="button" data-query="SO202601004">延期订单 SO202601004</button>
          <button class="quick-chip" type="button" data-query="SO202601001">可承诺 SO202601001</button>
          <button class="quick-chip" type="button" data-query="华东智造">客户 华东智造</button>
        </div>
      </section>

      <div id="query-results" class="stack" aria-live="polite">
        ${state === 'ready' ? loadingSkeleton() : stateView(state, { emptyTitle: '查询结果为空', errorTitle: '订单结论加载失败' })}
      </div>
    </div>`;

  function mount(root) {
    const form = root.querySelector('#query-form');
    const input = root.querySelector('#query-input');
    const results = root.querySelector('#query-results');
    const refresh = root.querySelector('#query-refresh');
    const exportButton = root.querySelector('#query-export');
    let currentOrders = [];
    let sort = { key: 'due_date', direction: 1 };
    let lastModalTrigger = null;
    const closeModals = () => {
      results.querySelectorAll('.modal-backdrop').forEach((modal) => { modal.hidden = true; });
      document.body.style.overflow = '';
      lastModalTrigger?.focus();
    };

    async function search(query = input.value) {
      if (state !== 'ready') return;
      results.innerHTML = loadingSkeleton();
      try {
        currentOrders = await fetchOrders({ query });
        const sorted = [...currentOrders].sort((a, b) => String(a[sort.key]).localeCompare(String(b[sort.key])) * sort.direction);
        results.innerHTML = resultMarkup(sorted, user);
        bindLocal();
      } catch (reason) {
        results.innerHTML = stateView('error', { errorTitle: '订单结论加载失败', errorText: reason.message });
        bindLocal();
      }
    }

    function bindLocal() {
      root.querySelector('[data-clear-search]')?.addEventListener('click', () => {
        input.value = '';
        search('');
      });
      root.querySelectorAll('[data-sort]').forEach((button) => {
        button.addEventListener('click', () => {
          sort = { key: button.dataset.sort, direction: sort.key === button.dataset.sort ? sort.direction * -1 : 1 };
          const sorted = [...currentOrders].sort((a, b) => String(a[sort.key]).localeCompare(String(b[sort.key])) * sort.direction);
          results.innerHTML = resultMarkup(sorted, user);
          bindLocal();
        });
      });
      root.querySelector('[data-retry]')?.addEventListener('click', () => {
        setDemoState('ready');
        window.dispatchEvent(new HashChangeEvent('hashchange'));
      });
    }

    results.addEventListener('click', (event) => {
      const opener = event.target.closest('[data-open-order-modal]');
      if (opener) {
        lastModalTrigger = opener;
        const modal = results.querySelector(`#${opener.dataset.openOrderModal}`);
        if (modal) {
          modal.hidden = false;
          document.body.style.overflow = 'hidden';
          modal.querySelector('[data-close-modal]')?.focus();
        }
        return;
      }
      if (event.target.closest('[data-close-modal]') || event.target.classList.contains('modal-backdrop')) closeModals();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeModals();
    });
    window.addEventListener('hashchange', () => {
      document.body.style.overflow = '';
    }, { once: true });

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      search();
    });
    refresh.addEventListener('click', () => search(input.value));
    root.querySelectorAll('[data-query]').forEach((button) => {
      button.addEventListener('click', () => {
        input.value = button.dataset.query;
        search(input.value);
      });
    });
    exportButton.addEventListener('click', () => {
      const lines = ['order_no,customer,due_date,kit_date,can_commit,delay_days'];
      currentOrders.forEach((order) => lines.push([order.order_no, order.customer, order.due_date, order.kit_date, order.can_commit, order.delay_days].join(',')));
      downloadFile('order-query-result.csv', `\uFEFF${lines.join('\n')}`, 'text/csv;charset=utf-8');
    });

    if (state !== 'ready') bindLocal();
    search('');
  }

  return { html, mount, title: pageTitle };
}




