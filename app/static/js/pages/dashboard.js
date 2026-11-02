import { downloadFile, fetchInventorySummary, fetchOrders, fetchShortageSummary, setDemoState } from '../api.js';
import { escapeHtml, formatNumber, icon, orderListModalMarkup, riskBadge, stateView, showToast } from '../components.js';

function dashboardContent(data) {
  const { orders, shortages, inventory } = data;
  const critical = [...shortages.items].sort((a, b) => a.earliest_required_date.localeCompare(b.earliest_required_date)).slice(0, 5);
  const highRisk = orders.filter((order) => !order.can_commit).sort((a, b) => Number(b.delay_days) - Number(a.delay_days));
  const returns = inventory.returns.filter((item) => item.inspection_status === '待检');
  return `
    <div class="grid-4">
      <button class="metric-card metric-card-button" type="button" data-open-delayed><div class="metric-label"><span>延期订单</span>${icon('alert', 'icon icon-sm')}</div><div class="metric-value danger">${formatNumber(shortages.summary.at_risk_orders, 0)} 张</div><div class="metric-foot">点击查看订单明细</div></button>
      <a class="metric-card metric-card-link" href="#/shortages"><div class="metric-label"><span>缺料物料</span>${icon('shortage', 'icon icon-sm')}</div><div class="metric-value">${formatNumber(shortages.summary.shortage_items, 0)} 项</div><div class="metric-foot">${escapeHtml(shortages.summary.critical_items)} 项高风险</div></a>
      <a class="metric-card metric-card-link" href="#/shortages/week"><div class="metric-label"><span>本周关键缺料</span>${icon('calendar', 'icon icon-sm')}</div><div class="metric-value">${formatNumber(shortages.summary.need_this_week, 0)} 项</div><div class="metric-foot">点击查看缺料台账</div></a>
      <button class="metric-card metric-card-button" type="button" data-open-delayed><div class="metric-label"><span>最大延期</span>${icon('clock', 'icon icon-sm')}</div><div class="metric-value danger">${formatNumber(shortages.summary.max_delay_days, 0)} 天</div><div class="metric-foot">点击查看影响订单</div></button>
    </div>

    <div class="dashboard-layout" style="margin-top:var(--space-4)">
      <div class="stack">
        <section class="card" aria-labelledby="critical-shortage-title">
          <div class="card-header"><div><h2 class="section-title" id="critical-shortage-title">紧急缺料</h2><div class="section-note">按最晚需到料日排序 · 点击料号追溯影响订单</div></div><a class="button button-ghost button-sm" href="#/shortages">查看全部 ${icon('arrow', 'icon icon-sm')}</a></div>
          <div class="table-wrap flush">
            <table class="data-table dashboard-table" aria-label="紧急缺料">
              <thead><tr><th>料号 / 名称</th><th class="numeric">缺口</th><th>最晚需到料</th><th>最早 ETA</th><th class="numeric">影响单</th><th>风险</th></tr></thead>
              <tbody>${critical.map((item) => `
                <tr>
                  <td><a class="item-link" href="#/shortages/${encodeURIComponent(item.item_code)}"><span class="mono primary-cell">${escapeHtml(item.item_code)}</span><span class="item-link-name">${escapeHtml(item.item_name)}</span></a></td>
                  <td class="numeric danger-cell">${formatNumber(item.gap)}</td>
                  <td class="nowrap">${escapeHtml(item.earliest_required_date)}</td>
                  <td class="nowrap">${escapeHtml(item.earliest_eta)}</td>
                  <td class="numeric"><a class="impact-count" href="#/shortages/${encodeURIComponent(item.item_code)}">${formatNumber(item.affected_orders_count, 0)} 张</a></td>
                  <td>${riskBadge(item.risk)}</td>
                </tr>`).join('')}</tbody>
            </table>
          </div>
          <div class="card-footer"><span class="small muted">数据更新 ${escapeHtml(shortages.updated_at)}</span><span class="badge badge-primary">${escapeHtml(shortages.calc_version)}</span></div>
        </section>

        <section class="card card-pad">
          <div class="section-head"><div><h2 class="section-title">风险订单</h2><div class="section-note">按延期天数排序</div></div><a class="link-button" href="#/query">订单查询 ${icon('chevron', 'icon icon-sm')}</a></div>
          <div class="risk-order-list">
            ${highRisk.map((order) => `
              <a class="risk-order-item" href="#/order/${encodeURIComponent(order.order_no)}">
                <div><div class="mono primary-cell">${escapeHtml(order.order_no)}</div><div class="small muted">${escapeHtml(order.customer)} · ${escapeHtml(order.product_name)}</div></div>
                <div class="risk-order-dates"><span>齐套 ${escapeHtml(order.kit_date)}</span><strong class="risk-high">+${escapeHtml(order.delay_days)} 天</strong></div>
              </a>`).join('')}
          </div>
        </section>
      </div>

      <aside class="stack">
        <section class="card card-pad">
          <div class="section-head"><h2 class="section-title">可用成品与退货</h2>${icon('warehouse', 'icon icon-sm')}</div>
          <div class="mini-stat-row">
            <a class="mini-stat-link" href="#/inventory/finished"><span>可承诺成品</span><strong>${formatNumber(inventory.summary.available_finished, 0)} 台</strong></a>
            <a class="mini-stat-link" href="#/inventory/returns"><span>退货待检</span><strong class="risk-medium">${formatNumber(inventory.summary.pending_returns, 0)} 单</strong></a>
          </div>
          <div class="return-list">
            ${returns.map((item) => `<a class="return-item" href="#/inventory/returns"><div><div class="small primary-cell">${escapeHtml(item.item_code)} · ${escapeHtml(item.item_name)}</div><div class="small muted">${escapeHtml(item.source_order)} · ${escapeHtml(item.reason)}</div></div><span class="badge badge-warning">待检 ${formatNumber(item.qty, 0)}</span></a>`).join('')}
          </div>
          <a class="button button-secondary button-sm" href="#/inventory" style="width:100%;margin-top:var(--space-3)">查看库存总览 ${icon('arrow', 'icon icon-sm')}</a>
        </section>

        <section class="card card-pad">
          <div class="section-head"><h2 class="section-title">数据状态</h2><span class="badge badge-success">可用</span></div>
          <div class="data-health-list">
            <div><span>缺料数据</span><strong>${escapeHtml(shortages.updated_at)}</strong></div>
            <div><span>库存数据</span><strong>${escapeHtml(inventory.updated_at)}</strong></div>
            <div><span>ETA 未确认</span><a class="link-button" href="#/inventory/transit">${formatNumber(inventory.summary.eta_unconfirmed, 0)} 条</a></div>
            <div><span>计算版本</span><strong class="mono">${escapeHtml(shortages.calc_version)}</strong></div>
          </div>
        </section>
      </aside>
    </div>
    ${orderListModalMarkup({ id: 'delayed-orders-modal', title: '延期订单明细', subtitle: '按延期天数排序 · 点击订单进入详情', orders: highRisk })}`;
}

export function renderDashboardPage({ state }) {
  const html = `
    <div class="page">
      <header class="page-header">
        <div>
          <div class="page-kicker">${icon('dashboard', 'icon icon-sm')} Delivery cockpit</div>
          <h1 class="page-title">交付驾驶舱</h1>
          <p class="page-subtitle">先看风险，再看物料和订单。缺口、库存、退货与数据状态集中在一屏，点击指标或料号即可下钻。</p>
        </div>
        <div class="page-actions">
          <a class="button button-secondary button-sm" href="#/simulate">${icon('sliders', 'icon icon-sm')}插单模拟</a>
          <button class="button button-primary button-sm" type="button" id="dashboard-export">${icon('download', 'icon icon-sm')}导出主管简报</button>
        </div>
      </header>
      <div id="dashboard-root">
        ${state === 'ready' ? '<div class="grid-4">' + [1,2,3,4].map(()=>'<div class="metric-card"><div class="skeleton skeleton-line short"></div><div class="skeleton skeleton-line"></div></div>').join('') + '</div>' : stateView(state, { emptyTitle: '暂无可展示的风险数据', errorTitle: '驾驶舱数据加载失败' })}
      </div>
    </div>`;

  function mount(root) {
    const target = root.querySelector('#dashboard-root');
    const exportButton = root.querySelector('#dashboard-export');
    let data = null;
    let lastTrigger = null;

    function closeModal() {
      const modal = target.querySelector('#delayed-orders-modal');
      if (!modal) return;
      modal.hidden = true;
      document.body.style.overflow = '';
      lastTrigger?.focus();
    }

    function openModal(trigger) {
      const modal = target.querySelector('#delayed-orders-modal');
      if (!modal) return;
      lastTrigger = trigger;
      modal.hidden = false;
      document.body.style.overflow = 'hidden';
      modal.querySelector('[data-close-modal]')?.focus();
    }

    async function load() {
      if (state !== 'ready') return;
      try {
        const [orders, shortages, inventory] = await Promise.all([fetchOrders(), fetchShortageSummary(), fetchInventorySummary()]);
        data = { orders, shortages, inventory };
        target.innerHTML = dashboardContent(data);
        target.querySelectorAll('[data-open-delayed]').forEach((button) => button.addEventListener('click', () => openModal(button)));
        const modal = target.querySelector('#delayed-orders-modal');
        modal.addEventListener('click', (event) => {
          if (event.target === modal || event.target.closest('[data-close-modal]')) closeModal();
        });
        modal.querySelectorAll('a[href^="#/order/"]').forEach((link) => link.addEventListener('click', closeModal));
        window.addEventListener('hashchange', () => {
          document.body.style.overflow = '';
          modal.hidden = true;
        }, { once: true });
        document.addEventListener('keydown', (event) => {
          if (event.key === 'Escape' && !modal.hidden) closeModal();
        });
      } catch (reason) {
        target.innerHTML = stateView('error', { errorTitle: '驾驶舱数据加载失败', errorText: reason.message });
      }
    }

    exportButton.addEventListener('click', () => {
      if (!data) return;
      const lines = ['type,key,value,date,risk'];
      lines.push(`metrics,delayed_orders,${data.shortages.summary.at_risk_orders},2026-11-02,`);
      data.shortages.items.forEach((item) => lines.push(['shortage', item.item_code, item.gap, item.earliest_required_date, item.risk].join(',')));
      data.orders.filter((order) => !order.can_commit).forEach((order) => lines.push(['order', order.order_no, order.delay_days, order.kit_date, order.risk].join(',')));
      downloadFile('supervisor-brief.csv', `\uFEFF${lines.join('\n')}`, 'text/csv;charset=utf-8');
      showToast('主管简报已导出');
    });

    target.addEventListener('click', (event) => {
      if (event.target.closest('[data-retry]')) {
        setDemoState('ready');
        window.dispatchEvent(new HashChangeEvent('hashchange'));
      }
    });
    load();
  }

  return { html, mount, title: '交付驾驶舱' };
}

