import { fetchOrderDetail, fetchOrders, downloadFile, setDemoState } from '../api.js';
import { escapeHtml, formatNumber, gapTable, icon, riskBadge, stateView, timeline } from '../components.js';

function hero(order) {
  return `
    <section class="detail-hero ${order.can_commit ? '' : 'is-delay'}" aria-label="订单结论摘要">
      <div>
        <div class="detail-order-no">${escapeHtml(order.order_no)}</div>
        <div class="detail-product">${escapeHtml(order.product_name)}</div>
        <div class="detail-customer">${escapeHtml(order.customer)} · ${formatNumber(order.qty, 0)} 台 · 负责人 ${escapeHtml(order.owner)}</div>
      </div>
      <div class="detail-dates">
        <div class="detail-date-item"><span>客户交期</span><strong>${escapeHtml(order.due_date)}</strong></div>
        <div class="detail-date-item"><span>最早可齐套</span><strong class="${order.can_commit ? '' : 'danger'}">${escapeHtml(order.kit_date)}</strong></div>
        <div class="detail-date-item"><span>交付偏差</span><strong class="${order.can_commit ? '' : 'danger'}">${order.can_commit ? '可按期' : `+${escapeHtml(order.delay_days)} 天`}</strong></div>
      </div>
      <div class="toolbar">${riskBadge(order.risk)}<span class="badge ${order.can_commit ? 'badge-success' : 'badge-danger'}"><span class="dot"></span>${escapeHtml(order.order_state)}</span></div>
    </section>`;
}

function detailContent(order, detail) {
  const gaps = detail?.gaps || [];
  const events = detail?.timeline || [];
  const isFullMock = Boolean(detail);
  const summary = detail?.summary || (order.can_commit
    ? '该订单在当前计算版本下可按期交付，mock 未提供额外缺口明细。'
    : `该订单有 ${order.gaps_count} 项缺口；当前 G1 mock 只为 SO202601004 提供 6 项完整明细。`);

  const left = `
    <aside class="stack">
      <section class="card card-pad">
        <div class="section-head"><h2 class="section-title">订单信息</h2><span class="badge badge-primary">${escapeHtml(order.calc_version || 'gen-1.0')}</span></div>
        <div class="detail-facts">
          <div class="detail-fact"><span>产品编码</span><strong class="mono">${escapeHtml(order.product_code)}</strong></div>
          <div class="detail-fact"><span>订单数量</span><strong>${formatNumber(order.qty, 0)} 台</strong></div>
          <div class="detail-fact"><span>缺口项数</span><strong class="${gaps.length ? 'risk-high' : ''}">${formatNumber(order.gaps_count || 0, 0)} 项</strong></div>
          <div class="detail-fact"><span>数据版本</span><strong class="mono">${escapeHtml(order.calc_version || 'gen-1.0')}</strong></div>
          <div class="detail-fact"><span>最后计算</span><strong>${escapeHtml(order.last_calculated || '2026-11-01 14:28')}</strong></div>
        </div>
      </section>
      <div class="detail-summary">${escapeHtml(summary)}</div>
      ${isFullMock ? '' : '<div class="card card-pad"><div class="inline-meta">' + icon('info', 'icon icon-sm') + '<span>本页仅展示该订单的结论字段；完整 6 项缺口表请走查 SO202601004。</span></div></div>'}
    </aside>`;

  const center = `
    <section class="card" aria-labelledby="gap-title">
      <div class="card-header">
        <div>
          <h2 class="section-title" id="gap-title">缺口明细</h2>
          <div class="section-note">按影响面排序 · 缺口 = 需求 - 可用（由 mock 直接提供）</div>
        </div>
        <span class="badge ${gaps.length ? 'badge-danger' : 'badge-success'}">${gaps.length ? `${gaps.length} 项缺口` : '无缺口'}</span>
      </div>
      <div class="card-body" style="padding:0">
        ${gaps.length ? gapTable(gaps) : `<div class="table-empty">${order.can_commit ? '库存与在途满足本次订单，无缺口。' : '该订单的缺口明细尚未加入 G1 mock。'}</div>`}
      </div>
    </section>`;

  const right = `
    <aside class="card card-pad detail-side">
      <div class="section-head"><h2 class="section-title">到货时间轴</h2>${icon('clock', 'icon icon-sm')}</div>
      ${events.length ? timeline(events) : '<div class="state-panel empty" style="min-height:180px;padding:var(--space-4)"><div class="state-icon">' + icon('calendar', 'icon icon-lg') + '</div><div class="state-title">暂无到货事件</div><p class="state-text">当前 mock 未为该订单提供时间轴。</p></div>'}
    </aside>`;

  return `${hero(order)}<div class="detail-grid" style="margin-top:var(--space-4)">${left}${center}${right}</div>`;
}

export function renderDetailPage({ user, state, params }) {
  const html = `
    <div class="page">
      <header class="page-header">
        <div>
          <div class="page-kicker">${icon('orders', 'icon icon-sm')} Order inspection</div>
          <h1 class="page-title">订单详情</h1>
          <p class="page-subtitle">结论、缺口与到货时间轴同屏呈现。缺口表 6 列齐全，数值右对齐，缺口标红。</p>
        </div>
        <div class="page-actions">
          <a class="button button-secondary button-sm" href="#/query">${icon('arrow', 'icon icon-sm')}返回查询</a>
          <button class="button button-primary button-sm" type="button" id="detail-export">${icon('download', 'icon icon-sm')}导出齐套报告</button>
        </div>
      </header>
      <div id="detail-root">
        ${state === 'ready' ? '<div class="card card-pad"><div class="skeleton skeleton-card"></div></div>' : stateView(state, { emptyTitle: '订单不存在或无权查看', errorTitle: '订单详情加载失败' })}
      </div>
    </div>`;

  function mount(root) {
    const target = root.querySelector('#detail-root');
    const exportButton = root.querySelector('#detail-export');
    let current = null;

    async function load() {
      if (state !== 'ready') return;
      try {
        const orders = await fetchOrders({ query: params.no });
        const order = orders.find((item) => item.order_no === params.no);
        if (!order) {
          target.innerHTML = stateView('empty', { emptyTitle: '订单不存在或无权查看', emptyText: '请返回订单查询换一个订单号，或使用具备全量客户权限的角色。' });
          current = null;
          return;
        }
        const detail = await fetchOrderDetail(params.no);
        current = { order, detail };
        target.innerHTML = detailContent(order, detail);
      } catch (reason) {
        target.innerHTML = stateView('error', { errorTitle: '订单详情加载失败', errorText: reason.message });
      }
    }

    target.addEventListener('click', (event) => {
      if (event.target.closest('[data-retry]')) {
        setDemoState('ready');
        window.dispatchEvent(new HashChangeEvent('hashchange'));
      }
    });

    exportButton.addEventListener('click', () => {
      if (!current) return;
      const gaps = current.detail?.gaps || [];
      const lines = ['order_no,item_code,item_name,need,available,gap,ready_date,impact_orders'];
      gaps.forEach((gap) => lines.push([current.order.order_no, gap.item_code, gap.item_name, gap.need, gap.available, gap.gap, gap.ready_date, gap.impact_orders.join('|')].join(',')));
      if (!gaps.length) lines.push([current.order.order_no, '', '', '', '', '', current.order.kit_date, ''].join(','));
      downloadFile(`${current.order.order_no}-kit-report.csv`, `\uFEFF${lines.join('\n')}`, 'text/csv;charset=utf-8');
    });

    load();
  }

  return { html, mount, title: `订单 ${params.no}` };
}


