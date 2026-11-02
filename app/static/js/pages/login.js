import { login, setCurrentUser } from '../api.js';
import { icon } from '../components.js';
import { navigate, roleHome } from '../router.js';

const DEMO_ROLES = [
  { account: 'sales01', name: '销售演示', role: '销售', note: '只看授权客户' },
  { account: 'planner01', name: '计划演示', role: '计划', note: '导入、库存与主数据' },
  { account: 'supervisor01', name: '主管演示', role: '主管', note: '驾驶舱与缺料决策' },
  { account: 'admin', name: '管理员', role: '管理员', note: '账号与权限' }
];

export function renderLoginPage() {
  const html = `
    <div class="login-page">
      <section class="login-story" aria-label="产品介绍">
        <div class="login-brand">
          <div class="brand-mark">${icon('logo', 'icon icon-lg')}</div>
          <div><div class="brand-name">交期领航</div><div class="brand-sub">DELIVERY PROMISE</div></div>
        </div>
        <div class="login-story-body">
          <div class="login-story-kicker">G1 · Static Mock Review</div>
          <h1 class="login-story-title">把交期风险，<br>提前算清楚。</h1>
          <p class="login-story-copy">从订单结论、缺口明细到插单影响，计划与销售在同一张工作台上对齐判断。当前阶段仅使用 mock 数据，不触发计算与写入。</p>
          <div class="login-proof">
            <div class="login-proof-item"><strong>11 屏</strong><span>完整可点路径</span></div>
            <div class="login-proof-item"><strong>4 态</strong><span>ready / loading / empty / error</span></div>
            <div class="login-proof-item"><strong>0 依赖</strong><span>原生 HTML / CSS / JS</span></div>
          </div>
        </div>
        <div class="login-story-foot">演示环境 · 不连接数据库 · 所有结果来自 static/mock</div>
      </section>

      <section class="login-panel">
        <div class="login-card">
          <div class="page-kicker">${icon('shield', 'icon icon-sm')} Secure workspace</div>
          <h2 class="login-title">登录交付工作台</h2>
          <p class="login-sub">使用演示账号查看不同角色的菜单与可见范围。</p>

          <form class="login-form" id="login-form" novalidate>
            <label class="field">
              <span class="field-label">账号</span>
              <input class="input" id="login-account" name="account" value="sales01" autocomplete="username" aria-describedby="login-hint" />
            </label>
            <label class="field">
              <span class="field-label">密码</span>
              <input class="input" id="login-password" name="password" type="password" value="demo123" autocomplete="current-password" aria-describedby="login-hint" />
            </label>
            <p class="field-hint" id="login-hint">演示环境任意非空密码均可，账号状态会按 mock 用户表校验。</p>
            <p class="login-error" id="login-error" role="alert" hidden></p>
            <button class="button button-primary button-lg" type="submit" id="login-submit">${icon('lock', 'icon icon-sm')}进入工作台</button>
          </form>

          <div class="demo-roles">
            <div class="demo-roles-title">快速切换角色 · 一键登录</div>
            <div class="demo-role-grid">
              ${DEMO_ROLES.map((item) => `
                <button class="demo-role" type="button" data-demo-account="${item.account}">
                  <span class="avatar">${item.role.slice(0, 1)}</span>
                  <span><strong>${item.name}</strong> · ${item.role}<br><span class="muted">${item.note}</span></span>
                </button>`).join('')}
            </div>
          </div>
          <p class="login-footnote">当前 G1 门禁：11 屏可点、mock 自洽、四态可演示。评审通过前不进入后端算法阶段。</p>
        </div>
      </section>
    </div>`;

  function mount(root) {
    const form = root.querySelector('#login-form');
    const account = root.querySelector('#login-account');
    const password = root.querySelector('#login-password');
    const error = root.querySelector('#login-error');
    const submit = root.querySelector('#login-submit');

    async function doLogin(nextAccount = account.value, nextPassword = password.value) {
      error.hidden = true;
      submit.disabled = true;
      submit.innerHTML = '<span class="spinner"></span>正在校验身份';
      try {
        const user = await login(nextAccount, nextPassword);
        setCurrentUser(user);
        navigate(roleHome(user.role), { replace: true });
      } catch (reason) {
        error.textContent = reason.message || '登录失败，请重试';
        error.hidden = false;
      } finally {
        submit.disabled = false;
        submit.innerHTML = `${icon('lock', 'icon icon-sm')}进入工作台`;
      }
    }

    root.querySelectorAll('[data-demo-account]').forEach((button) => {
      button.addEventListener('click', () => {
        account.value = button.dataset.demoAccount;
        password.value = 'demo123';
        doLogin(account.value, password.value);
      });
    });

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      doLogin();
    });
  }

  return { html, mount, fullPage: true, title: '登录' };
}




