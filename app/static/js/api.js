/**
 * Mock API 适配层。
 * - MOCK=true 时只读 static/mock/*.json，不触发任何后端业务逻辑。
 * - 所有真实接口路径已在注释中列明，G1 通过后可由 A2 接管。
 * - 前端不计算缺口/齐套日，只回显服务或 mock 给定的数字。
 */

export const MOCK = true;
const USER_KEY = 'plan-demo-current-user';
const DEMO_STATES = ['ready', 'loading', 'empty', 'error'];

const wait = (ms = 240) => new Promise((resolve) => window.setTimeout(resolve, ms));

export function getDemoState() {
  const state = new URLSearchParams(window.location.search).get('state');
  return DEMO_STATES.includes(state) ? state : 'ready';
}

export function setDemoState(state) {
  if (!DEMO_STATES.includes(state)) return;
  const url = new URL(window.location.href);
  url.searchParams.set('state', state);
  window.history.replaceState({}, '', url);
}

export function getCurrentUser() {
  try {
    return JSON.parse(window.localStorage.getItem(USER_KEY) || 'null');
  } catch {
    return null;
  }
}

export function setCurrentUser(user) {
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearCurrentUser() {
  window.localStorage.removeItem(USER_KEY);
}

async function loadMock(fileName) {
  if (!MOCK) {
    throw new Error('G1 静态预览未连接真实接口');
  }
  const response = await fetch(`./mock/${fileName}?t=${Date.now()}`, { cache: 'no-store' });
  if (!response.ok) throw new Error(`mock 文件加载失败：${fileName}`);
  return response.json();
}

/**
 * 读取用户可访问的订单。销售只返回授权客户范围内的订单。
 * 真实接口：GET /api/orders?q=...
 */
export async function fetchOrders({ query = '' } = {}) {
  const [payload, user] = await Promise.all([loadMock('order_promise.json'), Promise.resolve(getCurrentUser())]);
  await wait();
  const normalized = query.trim().toLowerCase();
  const scopes = user?.customer_scopes || [];
  const canSeeAll = !user || user.role !== 'sales' || scopes.includes('全部客户');
  return payload.orders.filter((order) => {
    const roleAllowed = canSeeAll || scopes.includes(order.customer);
    const queryAllowed = !normalized || [order.order_no, order.customer, order.product_name, order.owner]
      .some((field) => String(field).toLowerCase().includes(normalized));
    return roleAllowed && queryAllowed;
  });
}

/**
 * 读取订单详情。mock 只为 SO202601004 准备了完整 6 项缺口；
 * 其他订单返回 null，由详情页使用承诺结论降级展示，不生成虚构缺口。
 * 真实接口：GET /api/orders/{order_no}/promise
 */
export async function fetchOrderDetail(orderNo) {
  const detail = await loadMock('order_detail.json');
  await wait(180);
  if (detail.order_no !== orderNo) return null;
  return detail;
}

/**
 * 模拟插单/加急。结果来自 simulate_result.json，not_persisted 固定为 true。
 * 真实接口：POST /api/simulate
 */
export async function runSimulation(payload) {
  const result = await loadMock('simulate_result.json');
  await wait(650);
  return {
    ...result,
    request: { ...result.request, ...payload },
    inserted_order: { ...result.inserted_order, qty: payload.qty || result.inserted_order.qty }
  };
}

/**
 * 导入四类 CSV。mock 固定返回 120 成功 / 3 失败，便于演示错误 CSV。
 * 真实接口：POST /api/imports（multipart）
 */
export async function importCsv(files, mode = 'ALL_OR_NOTHING') {
  const result = await loadMock('import_result.json');
  await wait(260);
  return {
    ...result,
    mode,
    tables: result.tables.map((table) => ({ ...table, file_name: files[table.type]?.name || table.file_name }))
  };
}

/** 真实接口：GET /api/snapshots/compare?from=...&to=... */
export async function fetchSnapshotDiff() {
  const result = await loadMock('snapshot_diff.json');
  await wait(220);
  return result;
}

/**
 * 主管缺料台账：按物料汇总，并携带受影响订单与 BOM 路径。
 * 真实接口：GET /api/shortages
 */
export async function fetchShortageSummary() {
  const result = await loadMock('shortage_summary.json');
  await wait(220);
  return result;
}

/**
 * 库存总览：原材料、成品、在途、退货四类数据一次性返回。
 * 真实接口：GET /api/inventory?view=summary
 */
export async function fetchInventorySummary() {
  const result = await loadMock('inventory_summary.json');
  await wait(220);
  return result;
}

/** 真实接口：GET /api/master-data */
export async function fetchMasterData() {
  const result = await loadMock('master_data.json');
  await wait(200);
  return result;
}

/** 真实接口：GET /api/users */
export async function fetchUsers() {
  const result = await loadMock('users.json');
  await wait(180);
  return result;
}

/**
 * 登录只做演示身份切换：演示账号存在、状态启用、密码非空即可。
 * 真实接口：POST /api/auth/login
 */
export async function login(account, password) {
  const payload = await loadMock('users.json');
  await wait(320);
  const user = payload.users.find((item) => item.account === account.trim());
  if (!user) throw new Error('账号不存在，请从下方演示角色选择');
  if (user.status !== '启用') throw new Error('该账号已停用，请联系管理员');
  if (!password.trim()) throw new Error('请输入密码（演示环境任意非空密码均可）');
  return user;
}

/**
 * 长任务轮询封装（mock 版）。
 * 真实环境下替换为 GET /api/export/{task_id} 或 GET /api/imports/{batch_id}。
 */
export function createTaskPoller({ duration = 2200, onProgress, onComplete, onCancel } = {}) {
  let elapsed = 0;
  let timer = null;
  let canceled = false;
  const tick = 120;

  const promise = new Promise((resolve, reject) => {
    const run = () => {
      if (canceled) return;
      elapsed += tick;
      const percent = Math.min(100, Math.round((elapsed / duration) * 100));
      onProgress?.(percent);
      if (percent >= 100) {
        onComplete?.();
        resolve({ canceled: false });
        return;
      }
      timer = window.setTimeout(run, tick);
    };
    timer = window.setTimeout(run, tick);
  });

  return {
    promise,
    cancel() {
      if (canceled) return;
      canceled = true;
      window.clearTimeout(timer);
      onCancel?.();
    }
  };
}

export function buildErrorCsv(errors) {
  const header = 'row_no,column,value,reason';
  const rows = errors.map((error) => [error.row_no, error.column, error.value, error.reason]
    .map((value) => `"${String(value ?? '').replaceAll('"', '""')}"`)
    .join(','));
  return `\uFEFF${[header, ...rows].join('\n')}`;
}

export function downloadFile(fileName, content, type = 'text/plain;charset=utf-8') {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 500);
}

