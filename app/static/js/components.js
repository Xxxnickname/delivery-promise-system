/**
 * 共享 UI 组件。
 * 说明：本文件只负责展示 mock 字段，不计算缺口、齐套日或任何业务结论。
 * 每个组件都输出可转义的 HTML 字符串，页面挂载后再绑定交互事件。
 */

const ICONS = {
  logo: '<path d="M4 7.5 12 3l8 4.5v9L12 21l-8-4.5z"/><path d="M4 7.5 12 12l8-4.5M12 12v9"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  orders: '<path d="M5 3h14v18H5z"/><path d="M8 7h8M8 11h8M8 15h5"/>',
  sliders: '<path d="M4 6h10M18 6h2M4 12h2M10 12h10M4 18h7M15 18h5"/><circle cx="16" cy="6" r="2"/><circle cx="8" cy="12" r="2"/><circle cx="13" cy="18" r="2"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M5 16v4h14v-4"/>',
  compare: '<rect x="4" y="5" width="6" height="14" rx="1"/><rect x="14" y="5" width="6" height="14" rx="1"/><path d="M7 9h0M17 15h0"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
  users: '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6M16 5a3 3 0 0 1 0 6M18 14c2.2.7 3.7 2.5 3.7 5"/>',
  dashboard: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  shortage: '<path d="M12 3 2.8 20h18.4z"/><path d="M12 9v4M12 17h.01"/><path d="M5 12h4M15 12h4"/>',
  warehouse: '<path d="m3 10 9-6 9 6v10H3z"/><path d="M7 20v-6h10v6M3 10h18"/>',
  return: '<path d="M9 5H5v4M5.5 9A8 8 0 1 1 4 15M13 9l-3 3 3 3M10 12h6"/>',
  truck: '<path d="M3 7h11v10H3zM14 10h4l3 3v4h-7z"/><circle cx="7" cy="19" r="2"/><circle cx="18" cy="19" r="2"/>',
  logout: '<path d="M10 4H5v16h5M14 8l4 4-4 4M18 12H9"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  arrow: '<path d="M5 12h14M14 7l5 5-5 5"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  alert: '<path d="M12 3 2.6 20h18.8z"/><path d="M12 9v4M12 17h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  download: '<path d="M12 4v12M7 11l5 5 5-5M5 20h14"/>',
  refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  file: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5"/>',
  shield: '<path d="M12 3 5 6v5c0 4.8 2.9 8.1 7 10 4.1-1.9 7-5.2 7-10V6z"/><path d="m9 12 2 2 4-4"/>',
  box: '<path d="m3 8 9-5 9 5-9 5z"/><path d="M3 8v8l9 5 9-5V8M12 13v8"/>',
  spark: '<path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6z"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  filter: '<path d="M4 5h16l-6 7v6l-4 2v-8z"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  lock: '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6M14 11v6"/>'
};

export function icon(name, className = 'icon') {
  const path = ICONS[name] || ICONS.info;
  return `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`;
}

export const escapeHtml = (value = '') => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;');

export function formatNumber(value, digits = 2) {
  const number = Number(value);
  if (!Number.isFinite(number)) return escapeHtml(value ?? '—');
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  }).format(number);
}

export const roleLabel = (role) => ({
  sales: '销售',
  planner: '计划',
  supervisor: '主管',
  admin: '管理员'
}[role] || '访客');

export function roleBadge(role) {
  const tone = role === 'admin' ? 'badge-info' : role === 'supervisor' ? 'badge-warning' : role === 'planner' ? 'badge-primary' : 'badge-neutral';
  return `<span class="badge ${tone}">${roleLabel(role)}</span>`;
}

export function riskBadge(level = '低') {
  const tone = level === '高' ? 'badge-danger' : level === '中' ? 'badge-warning' : 'badge-success';
  return `<span class="badge ${tone}"><span class="dot"></span>${escapeHtml(level)}风险</span>`;
}

export function conclusionCard(order, options = {}) {
  const delayed = !order.can_commit;
  const compact = options.compact ? ' conclusion-mini' : '';
  const date = delayed ? order.kit_date : order.due_date;
  const dateLabel = delayed ? '最早可齐套日' : '可承诺日期';
  const orderHref = `#/order/${encodeURIComponent(order.order_no)}`;
  return `
    <article class="conclusion-card ${delayed ? 'is-delay' : ''}${compact}" aria-label="${escapeHtml(order.order_no)} ${dateLabel}">
      <div class="conclusion-top">
        <div>
          <div class="conclusion-order mono">${escapeHtml(order.order_no)}</div>
          <div class="conclusion-customer">${escapeHtml(order.customer)} · ${escapeHtml(order.product_name)}</div>
        </div>
        <span class="badge ${delayed ? 'badge-danger' : 'badge-success'}"><span class="dot"></span>${delayed ? `延期 ${escapeHtml(order.delay_days)} 天` : '可按期交付'}</span>
      </div>
      <div class="conclusion-date-label">${dateLabel}</div>
      <div class="conclusion-date ${delayed ? 'danger' : ''}">${escapeHtml(date)}</div>
      <div class="conclusion-meta">
        <div class="conclusion-meta-item"><span>客户交期</span><strong>${escapeHtml(order.due_date)}</strong></div>
        <div class="conclusion-meta-item"><span>${delayed ? '缺口物料' : '齐套状态'}</span><strong>${delayed ? `${escapeHtml(order.gaps_count)} 项` : '已齐套'}</strong></div>
        <div class="conclusion-meta-item"><span>数量</span><strong>${formatNumber(order.qty, 0)} 台</strong></div>
        <div class="conclusion-meta-item"><span>负责人</span><strong>${escapeHtml(order.owner)}</strong></div>
      </div>
      ${options.showAction === false ? '' : `<a class="button button-secondary button-sm conclusion-action" href="${orderHref}">查看结论与缺口 ${icon('arrow', 'icon icon-sm')}</a>`}
    </article>`;
}

export function gapTable(gaps) {
  const rows = gaps.map((gap) => {
    const impacts = Array.isArray(gap.impact_orders) ? gap.impact_orders : [];
    return `
      <tr>
        <td class="mono primary-cell"><a class="link-button mono" href="#/shortages/${encodeURIComponent(gap.item_code)}">${escapeHtml(gap.item_code)}</a></td>
        <td class="item-name" title="${escapeHtml(gap.item_name)}">${escapeHtml(gap.item_name)}</td>
        <td class="numeric">${formatNumber(gap.need)}</td>
        <td class="numeric">${formatNumber(gap.available)}</td>
        <td class="numeric danger-cell">${formatNumber(gap.gap)}</td>
        <td class="nowrap">${escapeHtml(gap.ready_date)}</td>
        <td><span class="impact-count" title="${escapeHtml(impacts.join('、'))}">${icon('alert', 'icon icon-sm')}${impacts.length} 张</span></td>
      </tr>`;
  }).join('');
  return `
    <div class="table-wrap">
      <table class="data-table gap-table" aria-label="缺口明细">
        <thead><tr>
          <th class="col-code">料号</th>
          <th class="col-name">名称</th>
          <th class="col-number numeric">需求</th>
          <th class="col-number numeric">可用</th>
          <th class="col-number numeric">缺口</th>
          <th class="col-date">最早到货</th>
          <th class="col-impact">影响单</th>
        </tr></thead>
        <tbody>${rows || '<tr><td colspan="7" class="table-empty">暂无缺口</td></tr>'}</tbody>
      </table>
    </div>`;
}

export function timeline(items) {
  const rows = items.map((item) => `
    <li class="timeline-item ${escapeHtml(item.tone || 'normal')}">
      <div class="timeline-date">${escapeHtml(item.date)}</div>
      <div class="timeline-label">${escapeHtml(item.label)}</div>
      <div class="timeline-detail">${escapeHtml(item.detail)}</div>
    </li>`).join('');
  return `<ol class="timeline" aria-label="到货时间轴">${rows}</ol>`;
}

export function progressBar(value, options = {}) {
  const safe = Math.max(0, Math.min(100, Number(value) || 0));
  return `
    <div class="progress-block" aria-live="polite">
      <div class="progress-head">
        <div>
          <strong class="small">${escapeHtml(options.label || '处理中')}</strong>
          <div class="muted small">${escapeHtml(options.note || '')}</div>
        </div>
        <div class="toolbar">
          <span class="mono small">${safe}%</span>
          ${options.cancelable ? `<button class="button button-ghost button-sm" type="button" data-cancel-task>取消</button>` : ''}
        </div>
      </div>
      <div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${safe}">
        <div class="progress-fill" style="width:${safe}%"></div>
      </div>
    </div>`;
}

export function diffTable(items) {
  const rows = items.map((item) => {
    const delayed = Number(item.delta_days) > 0;
    const changed = Number(item.delta_days) !== 0;
    const deltaText = delayed ? `+${item.delta_days} 天` : changed ? `${item.delta_days} 天` : '0 天';
    return `
      <tr>
        <td class="mono primary-cell">${escapeHtml(item.order_no)}</td>
        <td>${escapeHtml(item.customer)}</td>
        <td class="${delayed ? 'delta-positive' : changed ? 'delta-negative' : ''}">${escapeHtml(item.from)}</td>
        <td class="${delayed ? 'delta-positive' : changed ? 'delta-negative' : ''}">${escapeHtml(item.to)}</td>
        <td class="numeric delta-pill ${delayed ? 'delta-positive' : changed ? 'delta-negative' : ''}">${deltaText}</td>
      </tr>`;
  }).join('');
  return `
    <div class="table-wrap">
      <table class="data-table diff-table" aria-label="快照差异">
        <thead><tr><th>订单号</th><th>客户</th><th>上次齐套日</th><th>本次齐套日</th><th class="numeric">变化</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="5" class="table-empty">两次快照之间没有变化</td></tr>'}</tbody>
      </table>
    </div>`;
}

export function stateView(state, options = {}) {
  if (state === 'loading') {
    return `
      <div class="state-panel" aria-busy="true">
        <div class="state-icon"><span class="spinner" style="border-color:var(--color-line);border-top-color:var(--color-primary);width:24px;height:24px"></span></div>
        <h2 class="state-title">正在读取 mock 数据</h2>
        <p class="state-text">这是四态演示中的加载态，可通过左侧“演示状态”切回 ready。</p>
      </div>`;
  }
  if (state === 'empty') {
    return `
      <div class="state-panel empty">
        <div class="state-icon">${icon('search', 'icon icon-lg')}</div>
        <h2 class="state-title">${escapeHtml(options.emptyTitle || '没有匹配结果')}</h2>
        <p class="state-text">${escapeHtml(options.emptyText || '换一个订单号或客户名称再试。')}</p>
        ${options.emptyAction ? `<div class="state-actions">${options.emptyAction}</div>` : ''}
      </div>`;
  }
  if (state === 'error') {
    return `
      <div class="state-panel error">
        <div class="state-icon">${icon('alert', 'icon icon-lg')}</div>
        <h2 class="state-title">${escapeHtml(options.errorTitle || '暂时无法加载')}</h2>
        <p class="state-text">${escapeHtml(options.errorText || 'mock 接口返回了可重试错误。检查网络或切回 ready 继续走查。')}</p>
        <div class="state-actions"><button class="button button-secondary" type="button" data-retry>${icon('refresh', 'icon icon-sm')}重新加载</button></div>
      </div>`;
  }
  return '';
}

/**
 * 通用订单列表弹窗：用于驾驶舱、订单查询等汇总卡片的下钻。
 * 只展示传入订单，不计算交期或缺口。
 */
export function orderListModalMarkup({ id, title, subtitle = '', orders = [] }) {
  return `
    <div class="modal-backdrop" id="${escapeHtml(id)}" hidden>
      <div class="modal order-modal" role="dialog" aria-modal="true" aria-labelledby="${escapeHtml(id)}-title">
        <div class="modal-header">
          <div><h2 class="modal-title" id="${escapeHtml(id)}-title">${escapeHtml(title)}</h2><div class="small muted">${escapeHtml(subtitle)}</div></div>
          <button class="button button-ghost button-icon button-sm" type="button" data-close-modal aria-label="关闭订单列表">${icon('close', 'icon icon-sm')}</button>
        </div>
        <div class="modal-body order-modal-list">
          ${orders.map((order) => `
            <a class="order-modal-item" href="#/order/${encodeURIComponent(order.order_no)}">
              <div><div class="mono primary-cell">${escapeHtml(order.order_no)}</div><div class="small muted">${escapeHtml(order.customer)} · ${escapeHtml(order.product_name)}</div></div>
              <div class="order-modal-values"><span>客户交期 <strong>${escapeHtml(order.due_date)}</strong></span><span>齐套 <strong class="${order.can_commit ? '' : 'risk-high'}">${escapeHtml(order.kit_date)}</strong></span></div>
              <span class="badge ${order.can_commit ? 'badge-success' : 'badge-danger'}">${order.can_commit ? '可承诺' : `延期 ${escapeHtml(order.delay_days)} 天`}</span>
            </a>`).join('') || '<div class="table-empty">暂无订单</div>'}
        </div>
        <div class="modal-footer"><a class="button button-secondary button-sm" href="#/query">去订单查询</a><button class="button button-primary button-sm" type="button" data-close-modal>知道了</button></div>
      </div>
    </div>`;
}

export function showToast(message, tone = 'success') {
  const root = document.querySelector('#toast-root');
  if (!root) return;
  const item = document.createElement('div');
  item.className = `toast ${tone}`;
  item.innerHTML = `${icon(tone === 'danger' ? 'alert' : 'check', 'icon icon-sm')}<span>${escapeHtml(message)}</span>`;
  root.appendChild(item);
  window.setTimeout(() => item.remove(), 3200);
}



