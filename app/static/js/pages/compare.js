import { createTaskPoller, downloadFile, fetchSnapshotDiff, setDemoState } from '../api.js';
import { diffTable, escapeHtml, formatNumber, icon, progressBar, stateView, showToast } from '../components.js';
import { barChart } from '../charts.js';

function compareContent(data) {
  return `
    <div class="stack">
      <section class="grid-4">
        <div class="metric-card"><div class="metric-label">变化订单 <span class="badge badge-neutral">两次快照</span></div><div class="metric-value">${formatNumber(data.summary.changed, 0)} 张</div><div class="metric-foot">${escapeHtml(data.from_snapshot.label)} → ${escapeHtml(data.to_snapshot.label)}</div></div>
        <div class="metric-card"><div class="metric-label">齐套日延后 <span class="badge badge-danger">需关注</span></div><div class="metric-value danger">${formatNumber(data.summary.delayed, 0)} 张</div><div class="metric-foot">红色标记 · 影响面优先</div></div>
        <div class="metric-card"><div class="metric-label">齐套日提前 <span class="badge badge-success">改善</span></div><div class="metric-value success">${formatNumber(data.summary.advanced, 0)} 张</div><div class="metric-foot">绿色标记 · 可提前承诺</div></div>
        <div class="metric-card"><div class="metric-label">最大顺延</div><div class="metric-value danger">${formatNumber(data.summary.max_delay_days, 0)} 天</div><div class="metric-foot">按订单对齐计算差异</div></div>
      </section>

      <div class="diff-grid">
        <section class="card" aria-labelledby="diff-title">
          <div class="card-header"><div><h2 class="section-title" id="diff-title">按订单对齐</h2><div class="section-note">左列上次齐套日，右列本次齐套日</div></div><div class="diff-legend"><span><span class="legend-dot" style="background:var(--color-danger)"></span>延后</span><span><span class="legend-dot" style="background:var(--color-success)"></span>提前</span></div></div>
          <div class="table-wrap flush">${diffTable(data.items)}</div>
          <div class="card-footer"><span class="small muted">calc_version：${escapeHtml(data.from_snapshot.calc_version)} → ${escapeHtml(data.to_snapshot.calc_version)}</span><span class="badge badge-info">SNAPSHOT</span></div>
        </section>
        <aside class="stack">
          <div class="chart-figure">
            <div class="chart-head"><div><div class="chart-title">变化分布</div><div class="small muted">按齐套日变化方向</div></div>${icon('compare', 'icon icon-sm')}</div>
            ${barChart([{ label: '延后', value: data.summary.delayed, tone: 'danger' }, { label: '提前', value: data.summary.advanced }], { width: 400, height: 180, ariaLabel: '快照变化分布柱状图' })}
          </div>
          <div class="card card-pad">
            <div class="section-head"><h2 class="section-title">对比口径</h2><span class="badge badge-primary">gen-1.0</span></div>
            <div class="detail-facts">
              <div class="detail-fact"><span>对比方式</span><strong>按 order_no 对齐</strong></div>
              <div class="detail-fact"><span>日期单位</span><strong>YYYY-MM-DD</strong></div>
              <div class="detail-fact"><span>变化判定</span><strong>齐套日不同</strong></div>
              <div class="detail-fact"><span>导出</span><strong>服务端 xlsx（待接）</strong></div>
            </div>
            <p class="small muted" style="margin-top:var(--space-3)">G1 阶段导出按钮仅生成 CSV 演示文件，不调用后端任务。</p>
          </div>
        </aside>
      </div>
    </div>`;
}

export function renderComparePage({ state }) {
  const html = `
    <div class="page">
      <header class="page-header">
        <div>
          <div class="page-kicker">${icon('compare', 'icon icon-sm')} Snapshot diff</div>
          <h1 class="page-title">快照对比</h1>
          <p class="page-subtitle">将两次计算的齐套日按订单号对齐。延后标红、提前标绿，主管可先看变化再决定是否重排。</p>
        </div>
        <div class="page-actions"><button class="button button-primary button-sm" type="button" id="compare-export">${icon('download', 'icon icon-sm')}导出对比</button></div>
      </header>

      <section class="card card-pad" style="margin-bottom:var(--space-4)">
        <div class="toolbar">
          <label class="inline-meta"><span>基准快照</span><select class="select" id="from-snapshot" style="width:210px"><option>10-31 18:00 计算 · snap_20261031_02</option></select></label>
          <span class="arrow-mark">${icon('arrow', 'icon icon-sm')}</span>
          <label class="inline-meta"><span>对比快照</span><select class="select" id="to-snapshot" style="width:210px"><option>11-01 14:28 计算 · snap_20261101_03</option></select></label>
          <span class="badge badge-primary">按订单对齐</span>
          <span class="small muted">当前展示 12 张变化，其中 3 张延后</span>
        </div>
      </section>

      <div id="compare-progress"></div>
      <div id="compare-root">
        ${state === 'ready' ? '<div class="card card-pad"><div class="skeleton skeleton-table"></div></div>' : stateView(state, { emptyTitle: '两次快照没有差异', errorTitle: '快照对比加载失败' })}
      </div>
    </div>`;

  function mount(root) {
    const target = root.querySelector('#compare-root');
    const progress = root.querySelector('#compare-progress');
    const exportButton = root.querySelector('#compare-export');
    let data = null;
    let poller = null;

    async function load() {
      if (state !== 'ready') return;
      try {
        data = await fetchSnapshotDiff();
        target.innerHTML = compareContent(data);
      } catch (reason) {
        target.innerHTML = stateView('error', { errorTitle: '快照对比加载失败', errorText: reason.message });
      }
    }

    function exportCompare() {
      if (!data || poller) return;
      exportButton.disabled = true;
      progress.innerHTML = progressBar(0, { label: '正在生成对比文件', note: '模拟服务端导出任务', cancelable: true });
      poller = createTaskPoller({
        duration: 1500,
        onProgress: (percent) => {
          const track = progress.querySelector('.progress-track');
          if (!track) return;
          track.setAttribute('aria-valuenow', percent);
          progress.querySelector('.progress-fill').style.width = `${percent}%`;
          progress.querySelector('.progress-head .mono').textContent = `${percent}%`;
        },
        onComplete: () => {
          const lines = ['order_no,customer,from_kit_date,to_kit_date,delta_days'];
          data.items.forEach((item) => lines.push([item.order_no, item.customer, item.from, item.to, item.delta_days].join(',')));
          downloadFile('snapshot-diff.csv', `\uFEFF${lines.join('\n')}`, 'text/csv;charset=utf-8');
          progress.innerHTML = '<div class="inline-meta" style="padding:var(--space-3);border-radius:var(--radius-md);background:var(--color-success-soft);color:var(--color-success)">' + icon('check', 'icon icon-sm') + '导出完成：snapshot-diff.csv（G1 演示文件）</div>';
          exportButton.disabled = false;
          poller = null;
          showToast('快照对比已导出');
        }
      });
    }

    progress.addEventListener('click', (event) => {
      if (event.target.closest('[data-cancel-task]')) {
        poller?.cancel();
        poller = null;
        exportButton.disabled = false;
        progress.innerHTML = stateView('empty', { emptyTitle: '导出已取消', emptyText: '没有生成文件，可重新导出。' });
      }
    });

    target.addEventListener('click', (event) => {
      if (event.target.closest('[data-retry]')) {
        setDemoState('ready');
        window.dispatchEvent(new HashChangeEvent('hashchange'));
      }
    });

    exportButton.addEventListener('click', exportCompare);
    load();
  }

  return { html, mount, title: '快照对比' };
}

