/**
 * 轻量 Hash 路由与角色权限定义。
 * 路由约定：#/login、#/dashboard、#/query、#/shortages/:item?、
 * #/inventory、#/order/:no、#/simulate、#/import、#/compare、#/master、#/users。
 */

const NAV_BY_ROLE = {
  sales: [
    {
      label: '我的交付',
      items: [
        { key: 'query', href: '#/query', label: '我的订单', icon: 'search' },
        { key: 'simulate', href: '#/simulate', label: '场景模拟', icon: 'sliders' }
      ]
    }
  ],
  planner: [
    {
      label: '数据工作台',
      items: [
        { key: 'import', href: '#/import', label: '数据导入', icon: 'upload' },
        { key: 'inventory', href: '#/inventory', label: '库存总览', icon: 'warehouse' },
        { key: 'shortages', href: '#/shortages', label: '缺料台账', icon: 'shortage' }
      ]
    },
    { label: '主数据', items: [{ key: 'master', href: '#/master', label: '基础数据', icon: 'database' }] },
    {
      label: '业务查看',
      items: [
        { key: 'query', href: '#/query', label: '订单查询', icon: 'search' },
        { key: 'simulate', href: '#/simulate', label: '场景模拟', icon: 'sliders' }
      ]
    }
  ],
  supervisor: [
    {
      label: '决策中心',
      items: [
        { key: 'dashboard', href: '#/dashboard', label: '交付驾驶舱', icon: 'dashboard' },
        { key: 'shortages', href: '#/shortages', label: '缺料台账', icon: 'shortage' },
        { key: 'inventory', href: '#/inventory', label: '库存总览', icon: 'warehouse' }
      ]
    },
    {
      label: '业务分析',
      items: [
        { key: 'query', href: '#/query', label: '订单查询', icon: 'search' },
        { key: 'simulate', href: '#/simulate', label: '场景模拟', icon: 'sliders' },
        { key: 'compare', href: '#/compare', label: '快照对比', icon: 'compare' }
      ]
    }
  ],
  admin: [
    {
      label: '全局视图',
      items: [
        { key: 'dashboard', href: '#/dashboard', label: '交付驾驶舱', icon: 'dashboard' },
        { key: 'shortages', href: '#/shortages', label: '缺料台账', icon: 'shortage' },
        { key: 'inventory', href: '#/inventory', label: '库存总览', icon: 'warehouse' }
      ]
    },
    {
      label: '业务与数据',
      items: [
        { key: 'query', href: '#/query', label: '订单查询', icon: 'search' },
        { key: 'simulate', href: '#/simulate', label: '场景模拟', icon: 'sliders' },
        { key: 'compare', href: '#/compare', label: '快照对比', icon: 'compare' },
        { key: 'import', href: '#/import', label: '数据导入', icon: 'upload' },
        { key: 'master', href: '#/master', label: '基础数据', icon: 'database' }
      ]
    },
    { label: '系统设置', items: [{ key: 'users', href: '#/users', label: '用户管理', icon: 'users' }] }
  ]
};

export const ROUTE_META = {
  login: { title: '登录', kicker: 'DELIVERY CONTROL' },
  dashboard: { title: '交付驾驶舱', kicker: 'DELIVERY COCKPIT' },
  query: { title: '订单查询', kicker: 'PROMISE DESK' },
  detail: { title: '订单详情', kicker: 'ORDER INSPECTION' },
  shortages: { title: '缺料台账', kicker: 'SHORTAGE LEDGER' },
  inventory: { title: '库存总览', kicker: 'INVENTORY OVERVIEW' },
  simulate: { title: '场景模拟', kicker: 'WHAT IF' },
  import: { title: '数据导入', kicker: 'DATA INTAKE' },
  compare: { title: '快照对比', kicker: 'SNAPSHOT DIFF' },
  master: { title: '基础数据', kicker: 'MASTER DATA' },
  users: { title: '用户管理', kicker: 'ACCESS CONTROL' }
};

export function parseRoute(hash = window.location.hash) {
  const raw = String(hash || '#/query').replace(/^#/, '') || '/query';
  const segments = raw.split('/').filter(Boolean);
  if (!segments.length) return { name: 'query', params: {} };
  if (segments[0] === 'order' && segments[1]) {
    return { name: 'detail', params: { no: decodeURIComponent(segments[1]) } };
  }
  if (segments[0] === 'shortages' && segments[1]) {
    if (segments[1] === 'week') return { name: 'shortages', params: { scope: 'week' } };
    return { name: 'shortages', params: { item: decodeURIComponent(segments[1]) } };
  }
  if (segments[0] === 'inventory') {
    return { name: 'inventory', params: { tab: segments[1] || 'raw' } };
  }
  const name = ROUTE_META[segments[0]] ? segments[0] : 'query';
  return { name, params: {} };
}

export function navigate(path, { replace = false } = {}) {
  const hash = path.startsWith('#') ? path : `#${path}`;
  if (replace) {
    window.history.replaceState({}, '', `${window.location.pathname}${window.location.search}${hash}`);
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  } else if (window.location.hash === hash) {
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  } else {
    window.location.hash = hash;
  }
}

export function getNavItems(role) {
  return NAV_BY_ROLE[role] || [];
}

export function canAccess(routeName, user) {
  if (routeName === 'login') return true;
  if (!user) return false;
  const required = {
    dashboard: ['supervisor', 'admin'],
    query: ['sales', 'planner', 'supervisor', 'admin'],
    detail: ['sales', 'planner', 'supervisor', 'admin'],
    shortages: ['planner', 'supervisor', 'admin'],
    inventory: ['planner', 'supervisor', 'admin'],
    simulate: ['sales', 'planner', 'supervisor', 'admin'],
    import: ['planner', 'admin'],
    compare: ['supervisor', 'admin'],
    master: ['planner', 'admin'],
    users: ['admin']
  }[routeName];
  return Boolean(required?.includes(user.role));
}

export function roleHome(role) {
  return {
    sales: '#/query',
    planner: '#/import',
    supervisor: '#/dashboard',
    admin: '#/users'
  }[role] || '#/query';
}

export function activeNavKey(route) {
  if (route.name === 'detail') return 'query';
  return route.name;
}

