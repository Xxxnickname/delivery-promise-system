import { fetchMasterData, setDemoState } from '../api.js';
import { escapeHtml, formatNumber, icon, stateView, showToast } from '../components.js';

const PAGE_SIZE = 8;

function aliasRows(items) {
  return items.map((item) => `
    <tr>
      <td>${escapeHtml(item.alias)}</td>
      <td class="mono primary-cell">${escapeHtml(item.standard_code)}</td>
      <td>${escapeHtml(item.standard_name)}</td>
      <td>${escapeHtml(item.source)}</td>
      <td><span class="badge ${item.status === '已归一' ? 'badge-success' : 'badge-warning'}">${escapeHtml(item.status)}</span></td>
      <td class="hide-mobile">${escapeHtml(item.updated_at)}</td>
    </tr>`).join('');
}

function masterContent(master) {
  return `
    <div class="stack">
      <div class="toolbar" style="justify-content:space-between">
        <div class="tabs" role="tablist" aria-label="基础数据分类">
          <button class="tab-btn active" type="button" role="tab" aria-selected="true" data-tab="alias">物料别名 <span class="badge badge-neutral">20</span></button>
          <button class="tab-btn" type="button" role="tab" aria-selected="false" data-tab="substitute">替代料组 <span class="badge badge-neutral">3</span></button>
          <button class="tab-btn" type="button" role="tab" aria-selected="false" data-tab="config">口径配置</button>
        </div>
        <div class="inline-meta"><span>当前版本</span><span class="badge badge-primary version-badge">${escapeHtml(master.data_version)}</span><span>更新于 ${escapeHtml(master.updated_at)}</span></div>
      </div>

      <section data-panel="alias" class="stack">
        <div class="card">
          <div class="card-header"><div><h2 class="section-title">物料别名</h2><div class="section-note">料号 / 物料编码 / 图号统一归一到标准料号</div></div><div class="toolbar"><div class="search-field" style="flex-basis:260px">${icon('search', 'icon icon-sm')}<input class="input" id="alias-search" placeholder="搜索别名或标准料号" /></div><button class="button button-secondary button-sm" type="button" id="add-alias">${icon('plus', 'icon icon-sm')}新增别名</button></div></div>
          <div id="alias-table"></div>
          <div id="alias-footer"></div>
        </div>
      </section>

      <section data-panel="substitute" class="stack" hidden>
        <div class="card card-pad">
          <div class="section-head"><div><h2 class="section-title">替代料组</h2><div class="section-note">一对一替代与用量折算；多对多替代留待二期</div></div><button class="button button-secondary button-sm" type="button" id="add-substitute">${icon('plus', 'icon icon-sm')}新增替代组</button></div>
          <div class="substitute-list">
            ${master.substitutes.map((item) => `
              <div class="substitute-item">
                <span class="badge badge-info">${escapeHtml(item.group_code)}</span>
                <div><div class="substitute-flow"><span class="substitute-code">${escapeHtml(item.primary)}</span><span class="arrow-mark">${icon('arrow', 'icon icon-sm')}</span><span class="substitute-code">${escapeHtml(item.substitute)}</span><span class="badge badge-neutral">折算 ${escapeHtml(item.ratio)}</span></div><div class="small muted" style="margin-top:4px">${escapeHtml(item.note)}</div></div>
                <span class="badge badge-success">已启用</span>
              </div>`).join('')}
          </div>
        </div>
      </section>

      <section data-panel="config" class="stack" hidden>
        <form class="card card-pad" id="config-form">
          <div class="section-head"><div><h2 class="section-title">口径配置</h2><div class="section-note">保存即生成新版本，不覆盖历史口径</div></div><span class="badge badge-warning">待发布 v3.3</span></div>
          <div class="form-grid">
            <label class="field"><span class="field-label">损耗率</span><input class="input" name="scrap_rate" value="${escapeHtml(master.config.scrap_rate)}" inputmode="decimal" /><span class="field-hint">单位：%</span></label>
            <label class="field"><span class="field-label">安全库存天数</span><input class="input" name="safety_stock_days" value="${escapeHtml(master.config.safety_stock_days)}" inputmode="numeric" /><span class="field-hint">工作日口径</span></label>
            <label class="field"><span class="field-label">工作日历</span><select class="select" name="work_calendar"><option>${escapeHtml(master.config.work_calendar)}</option><option>周一至周五</option><option>自然日</option></select></label>
            <label class="field"><span class="field-label">上班时间</span><input class="input" name="workday_start" value="${escapeHtml(master.config.workday_start)}" /></label>
            <label class="field"><span class="field-label">下班时间</span><input class="input" name="workday_end" value="${escapeHtml(master.config.workday_end)}" /></label>
            <label class="field"><span class="field-label">时区</span><input class="input" name="timezone" value="${escapeHtml(master.config.timezone)}" readonly /></label>
            <label class="field form-span"><span class="field-label">舍入规则</span><input class="input" name="rounding_rule" value="${escapeHtml(master.config.rounding_rule)}" readonly /><span class="field-hint">数量 2 位 / 中间量 3 位；由宪法冻结，不在页面修改。</span></label>
          </div>
          <div class="card-footer" style="margin:var(--space-5) calc(var(--space-5) * -1) calc(var(--space-5) * -1);padding-left:var(--space-5);padding-right:var(--space-5)"><span class="small muted">新版本会进入发布记录，历史快照仍引用原版本。</span><button class="button button-primary" type="submit">保存并生成新版本</button></div>
        </form>
      </section>
    </div>`;
}

export function renderMasterPage({ state }) {
  const html = `
    <div class="page">
      <header class="page-header">
        <div>
          <div class="page-kicker">${icon('database', 'icon icon-sm')} Master data</div>
          <h1 class="page-title">基础数据</h1>
          <p class="page-subtitle">物料别名、替代料组与计算口径统一维护。保存配置后生成新版本，历史版本可追溯。</p>
        </div>
        <div class="page-actions"><span class="badge badge-primary version-badge">${icon('shield', 'icon icon-sm')}版本化配置</span></div>
      </header>
      <div id="master-root">
        ${state === 'ready' ? '<div class="card card-pad"><div class="skeleton skeleton-table"></div></div>' : stateView(state, { emptyTitle: '暂无基础数据', errorTitle: '基础数据加载失败' })}
      </div>
    </div>`;

  function mount(root) {
    const target = root.querySelector('#master-root');
    let master = null;
    let filtered = [];
    let page = 1;

    function renderAliases() {
      const start = (page - 1) * PAGE_SIZE;
      const slice = filtered.slice(start, start + PAGE_SIZE);
      const table = target.querySelector('#alias-table');
      const footer = target.querySelector('#alias-footer');
      if (!table || !footer) return;
      table.innerHTML = `
        <div class="table-wrap flush"><table class="data-table"><thead><tr><th>别名</th><th>标准料号</th><th>标准名称</th><th>来源</th><th>状态</th><th class="hide-mobile">更新</th></tr></thead><tbody>${aliasRows(slice) || '<tr><td colspan="6" class="table-empty">没有匹配的别名</td></tr>'}</tbody></table></div>`;
      const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
      footer.innerHTML = `
        <div class="table-footer"><span>共 ${formatNumber(filtered.length, 0)} 条 · 第 ${page} / ${pages} 页</span><div class="pagination">
          <button class="page-btn" type="button" data-page="${page - 1}" ${page === 1 ? 'disabled' : ''}>上一页</button>
          ${Array.from({ length: pages }, (_, index) => `<button class="page-btn ${page === index + 1 ? 'active' : ''}" type="button" data-page="${index + 1}">${index + 1}</button>`).join('')}
          <button class="page-btn" type="button" data-page="${page + 1}" ${page === pages ? 'disabled' : ''}>下一页</button>
        </div></div>`;
      footer.querySelectorAll('[data-page]').forEach((button) => button.addEventListener('click', () => {
        page = Number(button.dataset.page);
        renderAliases();
      }));
    }

    function bindTabs() {
      target.querySelectorAll('[data-tab]').forEach((button) => {
        button.addEventListener('click', () => {
          target.querySelectorAll('[data-tab]').forEach((item) => {
            item.classList.toggle('active', item === button);
            item.setAttribute('aria-selected', item === button ? 'true' : 'false');
          });
          target.querySelectorAll('[data-panel]').forEach((panel) => {
            panel.hidden = panel.dataset.panel !== button.dataset.tab;
          });
        });
      });
      target.querySelector('#alias-search')?.addEventListener('input', (event) => {
        const query = event.target.value.trim().toLowerCase();
        filtered = master.aliases.filter((item) => [item.alias, item.standard_code, item.standard_name].some((field) => String(field).toLowerCase().includes(query)));
        page = 1;
        renderAliases();
      });
      target.querySelector('#add-alias')?.addEventListener('click', () => showToast('G1 仅展示弹窗入口，新增写入待 G2 接入'));
      target.querySelector('#add-substitute')?.addEventListener('click', () => showToast('G1 仅展示替代组编辑入口'));
      target.querySelector('#config-form')?.addEventListener('submit', (event) => {
        event.preventDefault();
        showToast('已生成待发布版本 master-3.3（mock，不落盘）');
      });
    }

    async function load() {
      if (state !== 'ready') return;
      try {
        master = await fetchMasterData();
        filtered = [...master.aliases];
        target.innerHTML = masterContent(master);
        bindTabs();
        renderAliases();
      } catch (reason) {
        target.innerHTML = stateView('error', { errorTitle: '基础数据加载失败', errorText: reason.message });
      }
    }

    target.addEventListener('click', (event) => {
      if (event.target.closest('[data-retry]')) {
        setDemoState('ready');
        window.dispatchEvent(new HashChangeEvent('hashchange'));
      }
    });
    load();
  }

  return { html, mount, title: '基础数据' };
}

