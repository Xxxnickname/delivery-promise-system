import { downloadFile, fetchOrders, runSimulation, setDemoState } from '../api.js';
import { escapeHtml, formatNumber, icon, stateView, showToast } from '../components.js';

function emptyResult() {
  return `
    <div class="state-panel empty">
      <div class="state-icon">${icon('sliders', 'icon icon-lg')}</div>
      <h2 class="state-title">设置一次模拟</h2>
      <p class="state-text">选择插单或加急参数后运行。结果只用于评估影响清单，不会写入订单主表。</p>
    </div>`;
}

function resultMarkup(result) {
  const rows = result.affected.map((item) => {
    const delayed = Number(item.delay_days) > 0;
    return `
      <tr>
        <td class="mono primary-cell">${escapeHtml(item.order_no)}</td>
        <td>${escapeHtml(item.customer)}</td>
        <td>${escapeHtml(item.before_kit_date)}</td>
        <td class="${delayed ? 'danger-cell' : ''}">${escapeHtml(item.after_kit_date)}</td>
        <td class="numeric ${delayed ? 'danger-cell' : 'success-cell'}">${delayed ? `+${escapeHtml(item.delay_days)} 天` : '0 天'}</td>
        <td>${escapeHtml(item.reason)}</td>
      </tr>`;
  }).join('');
  return `
    <div class="stack">
      <section class="card card-pad">
        <div class="section-head">
          <div><div class="page-kicker">${icon('spark', 'icon icon-sm')} Simulation result</div><h2 class="section-title">${escapeHtml(result.summary.headline)}</h2></div>
          <span class="badge badge-warning">${icon('shield', 'icon icon-sm')}不落库</span>
        </div>
        <p class="muted small">模拟版本 ${escapeHtml(result.summary.simulation_calc_version)} · 基线版本 ${escapeHtml(result.summary.baseline_calc_version)} · ${escapeHtml(result.simulation_id)}</p>
        <div class="grid-3" style="margin-top:var(--space-4)">
          <div class="metric-card"><div class="metric-label">受影响订单</div><div class="metric-value">${formatNumber(result.summary.affected_count, 0)}</div><div class="metric-foot">按影响清单去重</div></div>
          <div class="metric-card"><div class="metric-label">最大顺延</div><div class="metric-value danger">${formatNumber(result.summary.max_delay_days, 0)} 天</div><div class="metric-foot">用于谈判与优先级判断</div></div>
          <div class="metric-card"><div class="metric-label">插单可齐套</div><div class="metric-value success">${escapeHtml(result.inserted_order.kit_date)}</div><div class="metric-foot">期望交期 ${escapeHtml(result.inserted_order.expect_date)}</div></div>
        </div>
      </section>

      <section class="card">
        <div class="card-header"><div><h2 class="section-title">影响清单</h2><div class="section-note">主表保持不变 · 仅用于本次模拟</div></div><button class="button button-secondary button-sm" type="button" id="simulate-export">${icon('download', 'icon icon-sm')}导出影响清单</button></div>
        <div class="table-wrap flush">
          <table class="data-table" aria-label="模拟影响清单">
            <thead><tr><th>订单号</th><th>客户</th><th>原齐套日</th><th>模拟齐套日</th><th class="numeric">变化</th><th>原因</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </section>
      <p class="small muted">演示说明：当前 mock 固定返回一次插单结果；切换参数不会重新计算数字，后端接入后由算法服务返回。</p>
    </div>`;
}

export function renderSimulatePage({ state }) {
  const html = `
    <div class="page">
      <header class="page-header">
        <div>
          <div class="page-kicker">${icon('sliders', 'icon icon-sm')} What if</div>
          <h1 class="page-title">场景模拟</h1>
          <p class="page-subtitle">模拟插单、加急或交期变更对现有订单的影响，先看清单再做承诺。模拟结果不写入主表。</p>
        </div>
        <span class="badge badge-warning"><span class="dot"></span>模拟不落库</span>
      </header>
      <div class="simulate-layout">
        <section class="card" aria-labelledby="simulate-form-title">
          <div class="card-header"><div><h2 class="section-title" id="simulate-form-title">模拟参数</h2><div class="section-note">输入业务假设，不修改真实订单</div></div>${icon('sliders', 'icon icon-sm')}</div>
          <form class="card-body stack" id="simulate-form">
            <label class="field">
              <span class="field-label">基准订单</span>
              <select class="select" id="simulate-order" required><option value="">正在载入订单…</option></select>
            </label>
            <fieldset class="field" style="border:0;padding:0">
              <legend class="field-label">模拟类型</legend>
              <div class="radio-group">
                <label class="radio-card"><input type="radio" name="mode" value="insert" checked><span><strong>插单</strong><span>在现有排产中插入新的交付需求</span></span></label>
                <label class="radio-card"><input type="radio" name="mode" value="rush"><span><strong>加急</strong><span>压缩现有订单的齐套时间</span></span></label>
              </div>
            </fieldset>
            <div class="form-grid">
              <label class="field"><span class="field-label">数量</span><input class="input" id="simulate-qty" type="number" min="1" value="50" required /><span class="field-hint">台</span></label>
              <label class="field"><span class="field-label">期望交期</span><input class="input" id="simulate-date" type="date" value="2026-11-15" required /></label>
            </div>
            <div class="inline-meta" style="padding:var(--space-3);border-radius:var(--radius-md);background:var(--color-warning-soft)">${icon('shield', 'icon icon-sm')}模拟不会修改订单、库存或在途数据。</div>
            <button class="button button-primary" type="submit" id="simulate-submit">${icon('spark', 'icon icon-sm')}运行模拟</button>
          </form>
        </section>
        <section id="simulate-result" aria-live="polite" class="stack">
          ${state === 'ready' ? emptyResult() : stateView(state, { emptyTitle: '还没有模拟结果', errorTitle: '模拟失败' })}
        </section>
      </div>
    </div>`;

  function mount(root) {
    const form = root.querySelector('#simulate-form');
    const select = root.querySelector('#simulate-order');
    const result = root.querySelector('#simulate-result');
    const submit = root.querySelector('#simulate-submit');
    let latest = null;

    fetchOrders({ query: '' }).then((orders) => {
      select.innerHTML = orders.map((order) => `<option value="${escapeHtml(order.order_no)}">${escapeHtml(order.order_no)} · ${escapeHtml(order.product_name)}</option>`).join('') || '<option value="">无可访问订单</option>';
      if (orders[0]) select.value = orders[0].order_no;
    }).catch((reason) => {
      select.innerHTML = '<option value="">订单加载失败</option>';
      showToast(reason.message, 'danger');
    });

    async function submitSimulation() {
      if (!select.value) return showToast('请选择基准订单', 'danger');
      submit.disabled = true;
      submit.innerHTML = '<span class="spinner"></span>正在模拟影响';
      try {
        latest = await runSimulation({
          order_no: select.value,
          mode: form.querySelector('input[name="mode"]:checked')?.value || 'insert',
          qty: root.querySelector('#simulate-qty').value,
          expect_date: root.querySelector('#simulate-date').value
        });
        result.innerHTML = resultMarkup(latest);
        root.querySelector('#simulate-export')?.addEventListener('click', exportResult);
        showToast('模拟完成，主表未发生变更');
      } catch (reason) {
        result.innerHTML = stateView('error', { errorTitle: '模拟失败', errorText: reason.message });
      } finally {
        submit.disabled = false;
        submit.innerHTML = `${icon('spark', 'icon icon-sm')}运行模拟`;
      }
    }

    function exportResult() {
      if (!latest) return;
      const lines = ['order_no,customer,before_kit_date,after_kit_date,delay_days,reason'];
      latest.affected.forEach((item) => lines.push([item.order_no, item.customer, item.before_kit_date, item.after_kit_date, item.delay_days, item.reason].join(',')));
      downloadFile('simulation-impact.csv', `\uFEFF${lines.join('\n')}`, 'text/csv;charset=utf-8');
    }

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      submitSimulation();
    });
    result.addEventListener('click', (event) => {
      if (event.target.closest('[data-retry]')) {
        setDemoState('ready');
        window.dispatchEvent(new HashChangeEvent('hashchange'));
      }
    });
    if (state === 'ready') result.querySelector('[data-retry]')?.remove();
  }

  return { html, mount, title: '场景模拟' };
}


