import {
  buildErrorCsv, createTaskPoller, downloadFile, importCsv, setDemoState
} from '../api.js';
import { escapeHtml, formatNumber, icon, progressBar, stateView, showToast } from '../components.js';

const TABLES = [
  { type: 'orders', label: '订单表', icon: 'orders', accept: '.csv', hint: 'order_no · item_code · qty · due_date' },
  { type: 'bom', label: 'BOM 表', icon: 'database', accept: '.csv', hint: 'parent_code · child_code · qty_per · level' },
  { type: 'inventory', label: '库存表', icon: 'box', accept: '.csv', hint: 'item_code · on_hand · allocated' },
  { type: 'in_transit', label: '在途表', icon: 'calendar', accept: '.csv', hint: 'item_code · qty · eta_date' }
];

const TEMPLATE_HEADERS = {
  orders: 'order_no,item_code,qty,due_date,customer\nSO202601001,FG-500,120,2026-11-12,华东智造',
  bom: 'parent_code,child_code,qty_per,scrap_rate,substitute_group\nFG-500,RM-033,1.00,0.02,SG-001',
  inventory: 'item_code,on_hand,allocated,warehouse\nRM-033,1200.00,0.00,WH-01',
  in_transit: 'item_code,qty,eta_date,batch_no\nRM-033,29312.92,2026-11-16,PO-20261101'
};

function importResultMarkup(result) {
  const modeResult = result.mode_results[result.mode];
  const rolledBack = Boolean(modeResult?.rolled_back);
  const statusText = rolledBack ? '已全部回滚' : '部分导入已留痕';
  const statusClass = rolledBack ? 'badge-danger' : 'badge-warning';
  const tableRows = result.tables.map((table) => `
    <tr><td class="primary-cell">${escapeHtml(table.label)}</td><td class="mono">${escapeHtml(table.file_name)}</td><td class="numeric">${formatNumber(table.rows, 0)}</td><td class="numeric success-cell">${formatNumber(table.ok_rows, 0)}</td><td class="numeric ${table.failed_rows ? 'danger-cell' : ''}">${formatNumber(table.failed_rows, 0)}</td></tr>`).join('');
  const errorRows = result.errors.map((error) => `
    <tr><td class="mono">${formatNumber(error.row_no, 0)}</td><td class="mono">${escapeHtml(error.column)}</td><td class="mono">${escapeHtml(error.value || '（空）')}</td><td>${escapeHtml(error.reason)}</td></tr>`).join('');
  return `
    <div class="stack">
      <section class="card card-pad">
        <div class="section-head"><div><div class="page-kicker">${icon('check', 'icon icon-sm')} Import finished</div><h2 class="section-title">批量 ${escapeHtml(result.batch_id)}</h2></div><span class="badge ${statusClass}">${escapeHtml(statusText)}</span></div>
        <div class="import-summary">
          <div class="metric-card"><div class="metric-label">校验通过</div><div class="metric-value success">${formatNumber(result.ok_rows, 0)} 行</div><div class="metric-foot">四张表合计</div></div>
          <div class="metric-card"><div class="metric-label">失败行</div><div class="metric-value danger">${formatNumber(result.failed_rows, 0)} 行</div><div class="metric-foot">可定位行号 / 列 / 原值</div></div>
          <div class="metric-card"><div class="metric-label">实际入库</div><div class="metric-value">${formatNumber(modeResult?.imported_rows || 0, 0)} 行</div><div class="metric-foot">${rolledBack ? '默认全或无：整批回滚' : '显式部分导入：保留成功行'}</div></div>
        </div>
        ${rolledBack ? '<div class="inline-meta" style="margin-top:var(--space-3);padding:var(--space-3);border-radius:var(--radius-md);background:var(--color-danger-soft);color:var(--color-danger)">' + icon('shield', 'icon icon-sm') + '检测到 3 行失败，系统按默认策略回滚全部 120 行，未产生静默丢行。</div>' : ''}
      </section>

      <section class="card">
        <div class="card-header"><div><h2 class="section-title">四表结果</h2><div class="section-note">文件行数与错误统计</div></div><span class="badge badge-primary">${escapeHtml(result.mode === 'ALL_OR_NOTHING' ? '全部回滚' : '部分导入')}</span></div>
        <div class="table-wrap flush"><table class="data-table"><thead><tr><th>类型</th><th>文件</th><th class="numeric">总行</th><th class="numeric">成功</th><th class="numeric">失败</th></tr></thead><tbody>${tableRows}</tbody></table></div>
      </section>

      <section class="card">
        <div class="card-header"><div><h2 class="section-title">错误明细</h2><div class="section-note">行号 / 列 / 原值 / 原因</div></div><button class="button button-secondary button-sm" type="button" id="download-errors">${icon('download', 'icon icon-sm')}下载错误 CSV</button></div>
        <div class="table-wrap flush"><table class="data-table error-table"><thead><tr><th>行号</th><th>列</th><th>原值</th><th>原因</th></tr></thead><tbody>${errorRows}</tbody></table></div>
      </section>
    </div>`;
}

export function renderImportPage({ state }) {
  const html = `
    <div class="page">
      <header class="page-header">
        <div>
          <div class="page-kicker">${icon('upload', 'icon icon-sm')} Data intake</div>
          <h1 class="page-title">数据导入</h1>
          <p class="page-subtitle">四张 ERP 导出表按模板校验。默认全部回滚；部分导入必须显式勾选并留痕，错误行可下载定位。</p>
        </div>
        <div class="page-actions"><button class="button button-secondary button-sm" type="button" id="demo-files">${icon('file', 'icon icon-sm')}载入示例文件</button></div>
      </header>

      <div class="split-main">
        <div class="stack">
          <section class="card card-pad">
            <div class="section-head"><div><h2 class="section-title">四类 CSV</h2><div class="section-note">拖拽或点击选择文件；G1 使用固定 120 / 3 结果</div></div><span class="badge badge-info">UTF-8 BOM · CSV</span></div>
            <div class="import-grid">
              ${TABLES.map((table) => `
                <div class="dropzone" data-dropzone="${table.type}">
                  <input type="file" class="sr-only" accept="${table.accept}" data-file-input="${table.type}" aria-label="选择${table.label}" />
                  <div class="dropzone-icon">${icon(table.icon, 'icon icon-sm')}</div>
                  <div><div class="dropzone-title">${table.label}</div><div class="dropzone-note">拖拽或点击选择</div><div class="dropzone-file" data-file-label="${table.type}">未选择</div></div>
                  <button class="button button-ghost button-sm" type="button" data-template="${table.type}">${icon('download', 'icon icon-sm')}模板</button>
                </div>`).join('')}
            </div>
          </section>

          <section class="card card-pad">
            <div class="section-head"><h2 class="section-title">导入策略</h2><span class="badge badge-warning">默认全部回滚</span></div>
            <div class="import-mode">
              <label class="radio-card"><input type="radio" name="import-mode" value="ALL_OR_NOTHING" checked><span><strong>全部回滚（默认）</strong><span>任一行失败即整批回滚，推荐生产使用</span></span></label>
              <label class="radio-card"><input type="radio" name="import-mode" value="PARTIAL_WITH_AUDIT" id="partial-mode" disabled><span><strong>部分导入</strong><span>仅保留成功行，并记录审计痕迹</span></span></label>
            </div>
            <label class="check-row" style="margin-top:var(--space-3)"><input type="checkbox" id="partial-confirm"><span>我确认允许部分导入；失败行仍会进入错误报告，不做静默丢弃。</span></label>
          </section>

          <div class="toolbar">
            <button class="button button-primary" type="button" id="start-import">${icon('upload', 'icon icon-sm')}开始导入</button>
            <button class="button button-secondary" type="button" id="clear-files">清除选择</button>
            <span class="small muted">未选择文件时也会使用示例文件名演示。</span>
          </div>
        </div>

        <section id="import-result" class="stack" aria-live="polite">
          ${state === 'ready' ? '<div class="state-panel empty"><div class="state-icon">' + icon('file', 'icon icon-lg') + '</div><h2 class="state-title">等待导入</h2><p class="state-text">选择四张表或点击“载入示例文件”，然后开始导入。进度条可取消。</p></div>' : stateView(state, { emptyTitle: '暂无导入记录', errorTitle: '导入结果加载失败' })}
        </section>
      </div>
    </div>`;

  function mount(root) {
    const selected = {};
    const result = root.querySelector('#import-result');
    const start = root.querySelector('#start-import');
    const partialConfirm = root.querySelector('#partial-confirm');
    const partialMode = root.querySelector('#partial-mode');
    let poller = null;

    function setFileLabel(type, name) {
      root.querySelector(`[data-file-label="${type}"]`).textContent = name || '未选择';
      root.querySelector(`[data-dropzone="${type}"]`).classList.toggle('has-file', Boolean(name));
    }

    function assignFile(type, file) {
      selected[type] = file;
      setFileLabel(type, file?.name || '');
    }

    root.querySelectorAll('[data-dropzone]').forEach((zone) => {
      const type = zone.dataset.dropzone;
      const input = zone.querySelector(`[data-file-input="${type}"]`);
      zone.addEventListener('click', (event) => {
        if (!event.target.closest('button')) input.click();
      });
      input.addEventListener('change', () => assignFile(type, input.files?.[0]));
      zone.addEventListener('dragover', (event) => { event.preventDefault(); zone.classList.add('dragging'); });
      zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
      zone.addEventListener('drop', (event) => {
        event.preventDefault();
        zone.classList.remove('dragging');
        const file = event.dataTransfer?.files?.[0];
        if (file) assignFile(type, file);
      });
    });

    root.querySelectorAll('[data-template]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        const type = button.dataset.template;
        downloadFile(`${type}-template.csv`, `\uFEFF${TEMPLATE_HEADERS[type]}`, 'text/csv;charset=utf-8');
      });
    });

    root.querySelector('#demo-files').addEventListener('click', () => {
      TABLES.forEach((table, index) => assignFile(table.type, { name: `demo_${table.label}_20261101.csv`, size: 3200 + index * 740 }));
      showToast('已载入 4 个示例文件名');
    });

    root.querySelector('#clear-files').addEventListener('click', () => {
      TABLES.forEach((table) => assignFile(table.type, null));
    });

    partialConfirm.addEventListener('change', () => {
      partialMode.disabled = !partialConfirm.checked;
      if (!partialConfirm.checked) root.querySelector('input[name="import-mode"][value="ALL_OR_NOTHING"]').checked = true;
    });

    result.addEventListener('click', (event) => {
      if (event.target.closest('[data-cancel-task]')) {
        poller?.cancel();
        return;
      }
      if (event.target.closest('#download-errors')) {
        const errors = result._errors || [];
        downloadFile('import-errors.csv', buildErrorCsv(errors), 'text/csv;charset=utf-8');
      }
      if (event.target.closest('[data-retry]')) {
        setDemoState('ready');
        window.dispatchEvent(new HashChangeEvent('hashchange'));
      }
    });

    async function startImport() {
      if (poller) return;
      const mode = root.querySelector('input[name="import-mode"]:checked')?.value || 'ALL_OR_NOTHING';
      start.disabled = true;
      result.innerHTML = progressBar(0, { label: '正在校验四张表', note: '即将开始解析表头与行数据', cancelable: true });
      try {
        const payload = await importCsv(selected, mode);
        poller = createTaskPoller({
          duration: 1800,
          onProgress: (percent) => {
            const box = result.querySelector('.progress-block');
            if (!box) return;
            box.querySelector('.progress-head .mono').textContent = `${percent}%`;
            box.querySelector('.progress-track').setAttribute('aria-valuenow', percent);
            box.querySelector('.progress-fill').style.width = `${percent}%`;
            box.querySelector('.progress-head .muted').textContent = percent < 55 ? '校验表头、类型与日期…' : '汇总错误行并准备回滚…';
          },
          onComplete: () => {
            result._errors = payload.errors;
            result.innerHTML = importResultMarkup(payload);
            start.disabled = false;
            poller = null;
            showToast(payload.mode === 'ALL_OR_NOTHING' ? '导入完成：3 行失败，整批已回滚' : '导入完成：成功行已保留并留痕', payload.mode === 'ALL_OR_NOTHING' ? 'danger' : 'success');
          },
          onCancel: () => {
            poller = null;
            start.disabled = false;
            result.innerHTML = stateView('empty', { emptyTitle: '导入已取消', emptyText: '没有写入任何数据；可重新选择文件后开始。' });
          }
        });
      } catch (reason) {
        poller = null;
        start.disabled = false;
        result.innerHTML = stateView('error', { errorTitle: '导入失败', errorText: reason.message });
      }
    }

    start.addEventListener('click', startImport);

  }

  return { html, mount, title: '数据导入' };
}


