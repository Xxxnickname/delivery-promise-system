import { downloadFile, fetchInventorySummary, setDemoState } from '../api.js';
import { escapeHtml, formatNumber, icon, stateView, showToast } from '../components.js';

const TAB_LABELS = [
  { key: 'raw', label: '原材料库存', icon: 'database' },
  { key: 'finished', label: '成品库存', icon: 'box' },
  { key: 'transit', label: '在途库存', icon: 'truck' },
  { key: 'returns', label: '退货库存', icon: 'return' }
];

function statusBadge(status) {
  const tone = status.includes('紧急') || status.includes('不合格') || status.includes('待确认')
    ? 'badge-danger'
    : status.includes('紧张') || status.includes('待检') || status.includes('部分预留') || status.includes('即将')
      ? 'badge-warning'
      : status.includes('正常') || status.includes('可用') || status.includes('合格') || status.includes('放行')
        ? 'badge-success'
        : 'badge-info';
  return `<span class="badge ${tone}">${escapeHtml(status)}</span>`;
}

function rawRows(rows) {
  return rows.map((row) => `
    <tr>
      <td>${row.shortage_item ? `<a class="link-button mono" href="#/shortages/${encodeURIComponent(row.item_code)}">${escapeHtml(row.item_code)}</a>` : `<div class="mono primary-cell">${escapeHtml(row.item_code)}</div>`}<div class="small muted">${escapeHtml(row.item_name)} · ${escapeHtml(row.spec)}</div></td>
      <td class="mono">${escapeHtml(row.warehouse)}</td>
      <td class="numeric">${formatNumber(row.on_hand)}</td>
      <td class="numeric">${formatNumber(row.allocated)}</td>
      <td class="numeric success-cell">${formatNumber(row.available)}</td>
      <td class="numeric">${formatNumber(row.safety_stock)}</td>
      <td class="numeric">${formatNumber(row.in_transit)}</td>
      <td class="nowrap">${escapeHtml(row.earliest_eta || '—')}</td>
      <td class="numeric">${formatNumber(row.stock_days, 0)} 天</td>
      <td>${statusBadge(row.status)}</td>
    </tr>`).join('');
}

function finishedRows(rows) {
  return rows.map((row) => `
    <tr>
      <td><div class="mono primary-cell">${escapeHtml(row.item_code)}</div><div class="small muted">${escapeHtml(row.item_name)} · ${escapeHtml(row.warehouse)}</div></td>
      <td>${escapeHtml(row.customer)}</td>
      <td class="numeric">${formatNumber(row.on_hand)}</td>
      <td class="numeric">${formatNumber(row.allocated)}</td>
      <td class="numeric success-cell">${formatNumber(row.available)}</td>
      <td class="numeric">${formatNumber(row.qualified_return_qty)}</td>
      <td class="numeric ${Number(row.pending_return_qty) ? 'risk-medium' : ''}">${formatNumber(row.pending_return_qty)}</td>
      <td class="numeric">${formatNumber(row.age_days, 0)} 天</td>
      <td>${statusBadge(row.status)}</td>
    </tr>`).join('');
}

function transitRows(rows) {
  return rows.map((row) => `
    <tr>
      <td><div class="mono primary-cell">${escapeHtml(row.po_no)}</div><div class="small muted">${escapeHtml(row.supplier)}</div></td>
      <td><div class="mono">${escapeHtml(row.item_code)}</div><div class="small muted">${escapeHtml(row.item_name)}</div></td>
      <td class="numeric">${formatNumber(row.qty)}</td>
      <td class="nowrap">${escapeHtml(row.eta_date)}</td>
      <td>${statusBadge(row.eta_confirmed === '是' ? '已确认' : '待确认 ETA')}</td>
      <td><div class="toolbar">${row.linked_orders.map((order) => `<a class="badge badge-info mono" href="#/order/${encodeURIComponent(order)}">${escapeHtml(order)}</a>`).join('')}</div></td>
      <td>${statusBadge(row.status)}</td>
    </tr>`).join('');
}

function returnRows(rows) {
  return rows.map((row) => `
    <tr class="${row.inspection_status === '待检' ? 'row-attention' : ''}">
      <td><div class="mono primary-cell">${escapeHtml(row.return_no)}</div><div class="small muted">来源 ${escapeHtml(row.source_order)}</div></td>
      <td>${escapeHtml(row.customer)}</td>
      <td><div class="mono">${escapeHtml(row.item_code)}</div><div class="small muted">${escapeHtml(row.item_name)}</div></td>
      <td class="numeric">${formatNumber(row.qty)}</td>
      <td>${escapeHtml(row.reason)}</td>
      <td>${statusBadge(row.inspection_status)}</td>
      <td class="numeric ${Number(row.available_qty) ? 'success-cell' : 'muted'}">${formatNumber(row.available_qty)}</td>
      <td class="numeric">${formatNumber(row.age_days, 0)} 天</td>
      <td>${statusBadge(row.disposition)}</td>
    </tr>`).join('');
}

export function renderInventoryPage({ state, params }) {
  const html = `
    <div class="page">
      <header class="page-header">
        <div>
          <div class="page-kicker">${icon('warehouse', 'icon icon-sm')} Inventory overview</div>
          <h1 class="page-title">库存总览</h1>
          <p class="page-subtitle">原材料、成品、在途和退货分开看。待检或不合格退货不进入可承诺库存。</p>
        </div>
        <div class="page-actions"><button class="button button-primary button-sm" type="button" id="inventory-export">${icon('download', 'icon icon-sm')}导出当前页</button></div>
      </header>
      <div id="inventory-root">
        ${state === 'ready' ? '<div class="card card-pad"><div class="skeleton skeleton-table"></div></div>' : stateView(state, { emptyTitle: '暂无库存数据', errorTitle: '库存数据加载失败' })}
      </div>
    </div>`;

  function mount(root) {
    const target = root.querySelector('#inventory-root');
    const exportButton = root.querySelector('#inventory-export');
    let data = null;
    const requestedTab = TAB_LABELS.some((tab) => tab.key === params?.tab) ? params.tab : 'raw';
    let activeTab = requestedTab;
    let filtered = [];

    const getRows = () => ({
      raw: data.raw_materials,
      finished: data.finished_goods,
      transit: data.in_transit,
      returns: data.returns
    }[activeTab]);

    function statusOptions() {
      const options = [...new Set(getRows().map((row) => row.status || row.inspection_status).filter(Boolean))];
      return `<option value="">全部状态</option>${options.map((option) => `<option>${escapeHtml(option)}</option>`).join('')}`;
    }

    function tableForRows(rows) {
      if (activeTab === 'raw') return `<table class="data-table inventory-table"><thead><tr><th>料号 / 规格</th><th>仓库</th><th class="numeric">现有</th><th class="numeric">已分配</th><th class="numeric">可用</th><th class="numeric">安全库存</th><th class="numeric">在途</th><th>最早 ETA</th><th class="numeric">库存天数</th><th>状态</th></tr></thead><tbody>${rawRows(rows) || '<tr><td colspan="10" class="table-empty">没有匹配的原材料</td></tr>'}</tbody></table>`;
      if (activeTab === 'finished') return `<table class="data-table inventory-table"><thead><tr><th>成品 / 仓库</th><th>客户</th><th class="numeric">现有</th><th class="numeric">已分配</th><th class="numeric">可承诺</th><th class="numeric">合格退货</th><th class="numeric">待检退货</th><th class="numeric">库龄</th><th>状态</th></tr></thead><tbody>${finishedRows(rows) || '<tr><td colspan="9" class="table-empty">没有匹配的成品</td></tr>'}</tbody></table>`;
      if (activeTab === 'transit') return `<table class="data-table inventory-table"><thead><tr><th>PO / 供应商</th><th>料号 / 名称</th><th class="numeric">数量</th><th>预计到货</th><th>ETA 确认</th><th>关联订单</th><th>状态</th></tr></thead><tbody>${transitRows(rows) || '<tr><td colspan="7" class="table-empty">没有匹配的在途批次</td></tr>'}</tbody></table>`;
      return `<table class="data-table inventory-table"><thead><tr><th>退货单 / 来源</th><th>客户</th><th>成品</th><th class="numeric">数量</th><th>退货原因</th><th>检验状态</th><th class="numeric">可计入可用</th><th class="numeric">库龄</th><th>处置</th></tr></thead><tbody>${returnRows(rows) || '<tr><td colspan="9" class="table-empty">没有匹配的退货</td></tr>'}</tbody></table>`;
    }

    function renderTable() {
      const query = target.querySelector('#inventory-search')?.value.trim().toLowerCase() || '';
      const status = target.querySelector('#inventory-status')?.value || '';
      filtered = getRows().filter((row) => {
        const fields = Object.values(row).flatMap((value) => Array.isArray(value) ? value : [value]);
        const queryHit = !query || fields.some((field) => String(field ?? '').toLowerCase().includes(query));
        const statusValue = row.status || row.inspection_status || '';
        return queryHit && (!status || statusValue === status);
      });
      target.querySelector('#inventory-table').innerHTML = tableForRows(filtered);
      target.querySelector('#inventory-result-count').textContent = `共 ${filtered.length} 条`;
    }

    function renderContent() {
      const s = data.summary;
      target.innerHTML = `
        <div class="stack">
          <div class="grid-4">
            <button class="metric-card metric-card-button" type="button" data-inv-goto="raw"><div class="metric-label">原材料 SKU ${icon('database', 'icon icon-sm')}</div><div class="metric-value">${formatNumber(s.raw_sku, 0)}</div><div class="metric-foot">当前展示 ${formatNumber(data.raw_materials.length, 0)} 条样例</div></button>
            <button class="metric-card metric-card-button" type="button" data-inv-goto="finished"><div class="metric-label">成品 SKU ${icon('box', 'icon icon-sm')}</div><div class="metric-value">${formatNumber(s.finished_sku, 0)}</div><div class="metric-foot">可承诺 ${formatNumber(s.available_finished, 0)} 台</div></button>
            <button class="metric-card metric-card-button" type="button" data-inv-goto="transit"><div class="metric-label">在途 PO ${icon('truck', 'icon icon-sm')}</div><div class="metric-value">${formatNumber(s.in_transit_po, 0)}</div><div class="metric-foot">${formatNumber(s.eta_unconfirmed, 0)} 条 ETA 未确认</div></button>
            <button class="metric-card metric-card-button" type="button" data-inv-goto="returns"><div class="metric-label">退货待检 ${icon('return', 'icon icon-sm')}</div><div class="metric-value danger">${formatNumber(s.pending_returns, 0)}</div><div class="metric-foot">待检退货不计入可用</div></button>
          </div>

          <section class="card">
            <div class="card-header"><div><h2 class="section-title">库存明细</h2><div class="section-note">数据更新 ${escapeHtml(data.updated_at)} · 可用库存由服务端提供</div></div><span class="badge badge-primary">MOCK INVENTORY</span></div>
            <div class="tabs inventory-tabs" role="tablist" aria-label="库存分类">${TAB_LABELS.map((tab) => `<button class="tab-btn ${tab.key === activeTab ? 'active' : ''}" type="button" role="tab" aria-selected="${tab.key === activeTab}" data-inv-tab="${tab.key}">${icon(tab.icon, 'icon icon-sm')}${tab.label}</button>`).join('')}</div>
            <div class="card-body" style="padding-bottom:var(--space-3)">
              <div class="toolbar" style="justify-content:space-between">
                <div class="toolbar" style="flex:1 1 440px"><div class="search-field" style="flex-basis:300px">${icon('search', 'icon icon-sm')}<input class="input" id="inventory-search" placeholder="搜索料号 / 名称 / 仓库 / 订单" /></div><select class="select" id="inventory-status" style="width:150px">${statusOptions()}</select></div>
                <span class="small muted" id="inventory-result-count"></span>
              </div>
            </div>
            <div class="table-wrap flush" id="inventory-table"></div>
            <div class="card-footer"><span class="small muted">退货需质检放行后才进入可承诺库存</span><button class="button button-secondary button-sm" type="button" id="inventory-export-current">${icon('download', 'icon icon-sm')}导出当前列表</button></div>
          </section>
        </div>`;

      target.querySelectorAll('[data-inv-tab]').forEach((button) => button.addEventListener('click', () => {
        activeTab = button.dataset.invTab;
        target.querySelectorAll('[data-inv-tab]').forEach((item) => {
          item.classList.toggle('active', item === button);
          item.setAttribute('aria-selected', item === button ? 'true' : 'false');
        });
        target.querySelector('#inventory-status').innerHTML = statusOptions();
        renderTable();
      }));
      target.querySelectorAll('[data-inv-goto]').forEach((button) => button.addEventListener('click', () => {
        target.querySelector(`[data-inv-tab="${button.dataset.invGoto}"]`)?.click();
      }));
      target.querySelector('#inventory-search').addEventListener('input', renderTable);
      target.querySelector('#inventory-status').addEventListener('change', renderTable);
      target.querySelector('#inventory-export-current').addEventListener('click', exportCurrent);
      renderTable();
    }

    function exportCurrent() {
      if (!filtered.length) return showToast('当前列表没有可导出的数据', 'danger');
      const headers = Object.keys(filtered[0]).filter((key) => !Array.isArray(filtered[0][key]));
      const lines = [headers.join(',')];
      filtered.forEach((row) => lines.push(headers.map((key) => `"${String(row[key] ?? '').replaceAll('"', '""')}"`).join(',')));
      downloadFile(`inventory-${activeTab}.csv`, `\uFEFF${lines.join('\n')}`, 'text/csv;charset=utf-8');
      showToast('库存列表已导出');
    }

    async function load() {
      if (state !== 'ready') return;
      try {
        data = await fetchInventorySummary();
        renderContent();
      } catch (reason) {
        target.innerHTML = stateView('error', { errorTitle: '库存数据加载失败', errorText: reason.message });
      }
    }

    exportButton.addEventListener('click', () => target.querySelector('#inventory-export-current')?.click());
    target.addEventListener('click', (event) => {
      if (event.target.closest('[data-retry]')) {
        setDemoState('ready');
        window.dispatchEvent(new HashChangeEvent('hashchange'));
      }
    });
    load();
  }

  return { html, mount, title: '库存总览' };
}

