import { downloadFile, fetchShortageSummary, setDemoState } from '../api.js';
import { escapeHtml, formatNumber, icon, orderListModalMarkup, riskBadge, stateView, showToast, timeline } from '../components.js';

function shortageRow(item) {
  return `
    <tr class="clickable-row" data-open-gap="${escapeHtml(item.item_code)}" tabindex="0">
      <td><div class="item-link"><span class="mono primary-cell">${escapeHtml(item.item_code)}</span><span class="item-link-name">${escapeHtml(item.item_name)}</span></div></td>
      <td class="numeric">${formatNumber(item.total_need)}</td>
      <td class="numeric">${formatNumber(item.available)}</td>
      <td class="numeric danger-cell">${formatNumber(item.gap)}</td>
      <td class="nowrap">${escapeHtml(item.earliest_required_date)}</td>
      <td><div class="supply-cell"><span>${formatNumber(item.in_transit_qty)}</span><small>ETA ${escapeHtml(item.earliest_eta)}</small></div></td>
      <td class="numeric"><a class="impact-count" href="#/shortages/${encodeURIComponent(item.item_code)}">${formatNumber(item.affected_orders_count, 0)} 张 ${icon('chevron', 'icon icon-sm')}</a></td>
      <td><div class="stack-sm">${riskBadge(item.risk)}<span class="badge badge-neutral">${escapeHtml(item.status)}</span></div></td>
    </tr>`;
}

function ledgerContent(data) {
  const affectedOrders = [...new Map(data.items.flatMap((item) => item.affected_orders.map((order) => ({ ...order, can_commit: order.status !== '已延期' }))).map((order) => [order.order_no, order])).values()];
  return `
    <div class="grid-4">
      <button class="metric-card metric-card-button" type="button" data-shortage-quick="all"><div class="metric-label"><span>缺料物料</span>${icon('shortage', 'icon icon-sm')}</div><div class="metric-value">${formatNumber(data.summary.shortage_items, 0)} 项</div><div class="metric-foot">点击查看全部</div></button>
      <button class="metric-card metric-card-button" type="button" data-shortage-quick="high"><div class="metric-label"><span>高风险物料</span>${icon('alert', 'icon icon-sm')}</div><div class="metric-value danger">${formatNumber(data.summary.critical_items, 0)} 项</div><div class="metric-foot">点击只看高风险</div></button>
      <button class="metric-card metric-card-button" type="button" data-open-shortage-orders><div class="metric-label"><span>受影响订单</span>${icon('orders', 'icon icon-sm')}</div><div class="metric-value">${formatNumber(data.summary.affected_orders, 0)} 张</div><div class="metric-foot">点击查看订单清单</div></button>
      <button class="metric-card metric-card-button" type="button" data-shortage-quick="week"><div class="metric-label"><span>本周关键缺料</span>${icon('calendar', 'icon icon-sm')}</div><div class="metric-value">${formatNumber(data.summary.need_this_week, 0)} 项</div><div class="metric-foot">点击只看本周关键</div></button>
    </div>

    <section class="card" style="margin-top:var(--space-4)">
      <div class="card-header"><div><h2 class="section-title">物料缺口汇总</h2><div class="section-note">点击一行打开影响订单与 BOM 追溯 · 数据更新 ${escapeHtml(data.updated_at)}</div></div><span class="badge badge-primary">${escapeHtml(data.calc_version)}</span></div>
      <div class="card-body" style="padding-bottom:var(--space-3)">
        <div class="toolbar" style="justify-content:space-between">
          <div class="toolbar" style="flex:1 1 480px">
            <div class="search-field" style="flex-basis:300px">${icon('search', 'icon icon-sm')}<input class="input" id="shortage-search" placeholder="搜索料号 / 名称 / 订单号" /></div>
            <select class="select" id="shortage-risk" style="width:126px" aria-label="按风险筛选"><option value="">全部风险</option><option value="高">高风险</option><option value="中">中风险</option></select>
            <label class="check-row" style="min-height:40px"><input type="checkbox" id="shortage-delay-only" /><span>仅看已影响延期</span></label>
          </div>
          <span class="small muted" id="shortage-count">共 ${formatNumber(data.items.length, 0)} 项</span>
        </div>
      </div>
      <div class="table-wrap flush" id="shortage-table"></div>
      <div class="card-footer"><span class="small muted">缺口 = 需求 - 可用；数字由计算服务提供，前端不推导</span><button class="button button-secondary button-sm" type="button" id="shortage-export-all">${icon('download', 'icon icon-sm')}导出缺料台账</button></div>
    </section>
    ${orderListModalMarkup({ id: 'shortage-orders-modal', title: '受影响订单清单', subtitle: '来自当前缺料台账涉及的全部订单', orders: affectedOrders })}`;
}

function drawerMarkup(item) {
  return `
    <div class="drawer-header">
      <div><div class="eyebrow">${escapeHtml(item.item_type)} · ${escapeHtml(item.unit)}</div><div class="drawer-title-row"><h2 class="drawer-title" id="drawer-title">${escapeHtml(item.item_code)} · ${escapeHtml(item.item_name)}</h2>${riskBadge(item.risk)}</div><div class="small muted">${escapeHtml(item.status)} · 最晚需到料 ${escapeHtml(item.earliest_required_date)}</div></div>
      <button class="button button-ghost button-icon button-sm" type="button" data-close-drawer aria-label="关闭缺口详情">${icon('close', 'icon icon-sm')}</button>
    </div>
    <div class="drawer-body">
      <div class="drawer-metrics">
        <div><span>总需求</span><strong>${formatNumber(item.total_need)}</strong></div>
        <div><span>可用</span><strong>${formatNumber(item.available)}</strong></div>
        <div><span>缺口</span><strong class="risk-high">${formatNumber(item.gap)}</strong></div>
        <div><span>在途</span><strong>${formatNumber(item.in_transit_qty)}</strong></div>
      </div>
      <div class="drawer-meta"><span>最早 ETA <strong>${escapeHtml(item.earliest_eta)}</strong></span><span>影响订单 <strong>${formatNumber(item.affected_orders_count, 0)} 张</strong></span></div>

      <section class="drawer-section">
        <div class="section-head"><h3 class="section-title">受影响订单</h3><span class="section-note">需求与 BOM 路径均来自 mock</span></div>
        <div class="table-wrap drawer-table-wrap">
          <table class="data-table compact drawer-table" aria-label="受影响订单">
            <thead><tr><th>订单</th><th>客户 / 产品</th><th class="numeric">需求</th><th class="numeric">缺口</th><th>交期 / 齐套</th><th>BOM</th><th>状态</th></tr></thead>
            <tbody>${item.affected_orders.map((order) => `
              <tr>
                <td><a class="link-button mono" href="#/order/${encodeURIComponent(order.order_no)}">${escapeHtml(order.order_no)}</a></td>
                <td><div class="primary-cell">${escapeHtml(order.customer)}</div><div class="small muted">${escapeHtml(order.product_name)}</div></td>
                <td class="numeric">${formatNumber(order.need)}</td>
                <td class="numeric danger-cell">${formatNumber(order.gap)}</td>
                <td><div class="nowrap">${escapeHtml(order.due_date)}</div><div class="small ${order.delay_days ? 'risk-high' : 'muted'}">齐套 ${escapeHtml(order.kit_date)}${order.delay_days ? ` · +${escapeHtml(order.delay_days)} 天` : ''}</div></td>
                <td><span class="badge badge-info">L${formatNumber(order.bom_level, 0)}</span><div class="small muted mono" style="margin-top:3px">${escapeHtml(order.bom_path)}</div></td>
                <td><span class="badge ${order.status === '已延期' ? 'badge-danger' : 'badge-success'}">${escapeHtml(order.status)}</span></td>
              </tr>`).join('')}</tbody>
          </table>
        </div>
      </section>

      <section class="drawer-section"><div class="section-head"><h3 class="section-title">供给时间轴</h3></div>${timeline(item.timeline)}</section>
    </div>
    <div class="drawer-footer"><span class="small muted">导出只包含当前物料的受影响订单</span><button class="button button-primary button-sm" type="button" data-export-item="${escapeHtml(item.item_code)}">${icon('download', 'icon icon-sm')}导出采购需求</button></div>`;
}

export function renderShortagesPage({ state, params }) {
  const html = `
    <div class="page">
      <header class="page-header">
        <div>
          <div class="page-kicker">${icon('shortage', 'icon icon-sm')} Shortage ledger</div>
          <h1 class="page-title">缺料台账</h1>
          <p class="page-subtitle">从物料看风险：一行一个原材料，点开即可追溯影响订单、BOM 路径、在途 ETA 与齐套时间。</p>
        </div>
        <div class="page-actions"><a class="button button-secondary button-sm" href="#/inventory">${icon('warehouse', 'icon icon-sm')}库存总览</a></div>
      </header>
      <div id="shortage-root">
        ${state === 'ready' ? '<div class="card card-pad"><div class="skeleton skeleton-table"></div></div>' : stateView(state, { emptyTitle: '暂无缺料数据', errorTitle: '缺料台账加载失败' })}
      </div>
    </div>
    <div class="drawer-backdrop" id="gap-drawer" hidden><aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title"><div id="drawer-content"></div></aside></div>`;

  function mount(root) {
    const target = root.querySelector('#shortage-root');
    const drawer = root.querySelector('#gap-drawer');
    const drawerContent = root.querySelector('#drawer-content');
    let data = null;
    let lastTrigger = null;
    let weeklyOnly = params.scope === 'week';

    function closeDrawer() {
      drawer.hidden = true;
      document.body.style.overflow = '';
      lastTrigger?.focus();
    }

    function openDrawer(item, trigger = null) {
      lastTrigger = trigger || document.activeElement;
      drawerContent.innerHTML = drawerMarkup(item);
      drawer.hidden = false;
      document.body.style.overflow = 'hidden';
      drawer.querySelector('[data-close-drawer]')?.focus();
      drawer.querySelector('[data-export-item]')?.addEventListener('click', () => exportItem(item));
      drawer.querySelectorAll('a[href^="#/order/"]').forEach((link) => link.addEventListener('click', closeDrawer));
    }

    function exportItem(item) {
      const lines = ['order_no,customer,product,need,gap,due_date,kit_date,delay_days,bom_level,bom_path,status'];
      item.affected_orders.forEach((order) => lines.push([order.order_no, order.customer, order.product_name, order.need, order.gap, order.due_date, order.kit_date, order.delay_days, order.bom_level, order.bom_path, order.status].join(',')));
      downloadFile(`${item.item_code}-purchase-request.csv`, `\uFEFF${lines.join('\n')}`, 'text/csv;charset=utf-8');
      showToast(`${item.item_code} 采购需求已导出`);
    }

    function renderTable(items) {
      const holder = target.querySelector('#shortage-table');
      const count = target.querySelector('#shortage-count');
      if (!holder) return;
      holder.innerHTML = `<table class="data-table shortage-table"><thead><tr><th>料号 / 名称</th><th class="numeric">总需求</th><th class="numeric">可用</th><th class="numeric">缺口</th><th>最晚需到料</th><th>在途 / ETA</th><th class="numeric">影响单</th><th>风险 / 状态</th></tr></thead><tbody>${items.map(shortageRow).join('') || '<tr><td colspan="8" class="table-empty">没有匹配的缺料物料</td></tr>'}</tbody></table>`;
      count.textContent = `共 ${items.length} 项`;
      holder.querySelectorAll('[data-open-gap]').forEach((row) => {
        row.addEventListener('click', (event) => {
          if (event.target.closest('a')) return;
          openDrawer(data.items.find((item) => item.item_code === row.dataset.openGap), row);
        });
        row.addEventListener('keydown', (event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            openDrawer(data.items.find((item) => item.item_code === row.dataset.openGap), row);
          }
        });
      });
    }

    function applyFilters() {
      const query = target.querySelector('#shortage-search')?.value.trim().toLowerCase() || '';
      const risk = target.querySelector('#shortage-risk')?.value || '';
      const delayOnly = target.querySelector('#shortage-delay-only')?.checked;
      const items = data.items.filter((item) => {
        const hit = !query || [item.item_code, item.item_name, ...item.affected_orders.map((order) => order.order_no)].some((field) => String(field).toLowerCase().includes(query));
        const delayHit = !delayOnly || item.affected_orders.some((order) => Number(order.delay_days) > 0);
        const weeklyHit = !weeklyOnly || item.weekly_focus;
        return hit && (!risk || item.risk === risk) && delayHit && weeklyHit;
      });
      renderTable(items);
    }

    async function load() {
      if (state !== 'ready') return;
      try {
        data = await fetchShortageSummary();
        target.innerHTML = ledgerContent(data);
        target.querySelector('#shortage-search').addEventListener('input', applyFilters);
        target.querySelector('#shortage-risk').addEventListener('change', applyFilters);
        target.querySelector('#shortage-delay-only').addEventListener('change', applyFilters);
        target.querySelectorAll('[data-shortage-quick]').forEach((button) => button.addEventListener('click', () => {
          const mode = button.dataset.shortageQuick;
          target.querySelector('#shortage-search').value = '';
          target.querySelector('#shortage-risk').value = mode === 'high' ? '高' : '';
          target.querySelector('#shortage-delay-only').checked = false;
          weeklyOnly = mode === 'week';
          applyFilters();
        }));
        const ordersModal = target.querySelector('#shortage-orders-modal');
        let ordersTrigger = null;
        const closeOrdersModal = () => {
          ordersModal.hidden = true;
          document.body.style.overflow = '';
          ordersTrigger?.focus();
        };
        target.querySelector('[data-open-shortage-orders]').addEventListener('click', (event) => {
          ordersTrigger = event.currentTarget;
          ordersModal.hidden = false;
          document.body.style.overflow = 'hidden';
          ordersModal.querySelector('[data-close-modal]')?.focus();
        });
        ordersModal.addEventListener('click', (event) => {
          if (event.target === ordersModal || event.target.closest('[data-close-modal]')) closeOrdersModal();
        });
        ordersModal.querySelectorAll('a[href^="#/order/"]').forEach((link) => link.addEventListener('click', closeOrdersModal));
        window.addEventListener('hashchange', () => {
          document.body.style.overflow = '';
          ordersModal.hidden = true;
        }, { once: true });
        applyFilters();
        target.querySelector('#shortage-export-all').addEventListener('click', () => {
          const lines = ['item_code,item_name,total_need,available,gap,earliest_required_date,in_transit,earliest_eta,affected_orders,risk,status'];
          data.items.forEach((item) => lines.push([item.item_code, item.item_name, item.total_need, item.available, item.gap, item.earliest_required_date, item.in_transit_qty, item.earliest_eta, item.affected_orders_count, item.risk, item.status].join(',')));
          downloadFile('shortage-ledger.csv', `\uFEFF${lines.join('\n')}`, 'text/csv;charset=utf-8');
        });
        if (params.item) {
          const item = data.items.find((row) => row.item_code === params.item);
          if (item) openDrawer(item);
        }
      } catch (reason) {
        target.innerHTML = stateView('error', { errorTitle: '缺料台账加载失败', errorText: reason.message });
      }
    }

    window.addEventListener('hashchange', () => {
      document.body.style.overflow = '';
      drawer.hidden = true;
    }, { once: true });
    drawer.addEventListener('click', (event) => {
      if (event.target === drawer || event.target.closest('[data-close-drawer]')) closeDrawer();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !drawer.hidden) closeDrawer();
      const ordersModal = target.querySelector('#shortage-orders-modal');
      if (event.key === 'Escape' && ordersModal && !ordersModal.hidden) { ordersModal.hidden = true; document.body.style.overflow = ''; }
      if (event.key === 'Tab' && !drawer.hidden) {
        const focusable = [...drawer.querySelectorAll('button, a[href], input, select')].filter((element) => !element.disabled);
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });
    target.addEventListener('click', (event) => {
      if (event.target.closest('[data-retry]')) {
        setDemoState('ready');
        window.dispatchEvent(new HashChangeEvent('hashchange'));
      }
    });
    load();
  }

  return { html, mount, title: '缺料台账' };
}




