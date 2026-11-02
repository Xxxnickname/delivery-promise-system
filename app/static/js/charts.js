/**
 * 内联 SVG 图表，不依赖第三方库。
 * 仅负责将传入的序列映射为图形坐标；不推导订单交期或物料数量。
 */
import { escapeHtml, formatNumber } from './components.js';

const WIDTH = 520;
const HEIGHT = 190;
const PAD = { left: 34, right: 12, top: 16, bottom: 28 };

function scale(values, min, max, size) {
  const span = max - min || 1;
  return values.map((value) => PAD.top + ((max - value) / span) * (size - PAD.top - PAD.bottom));
}

export function lineChart(series, options = {}) {
  const width = Number(options.width) || WIDTH;
  const height = Number(options.height) || HEIGHT;
  const values = series.map((item) => Number(item.value));
  const max = Math.max(...values, 1) * 1.12;
  const min = 0;
  const ys = scale(values, min, max, height);
  const innerWidth = width - PAD.left - PAD.right;
  const xs = values.map((_, index) => PAD.left + (values.length === 1 ? innerWidth / 2 : (index / (values.length - 1)) * innerWidth));
  const points = xs.map((x, index) => `${x.toFixed(1)},${ys[index].toFixed(1)}`).join(' ');
  const area = `${PAD.left},${height - PAD.bottom} ${points} ${width - PAD.right},${height - PAD.bottom}`;
  const grid = [0, .25, .5, .75, 1].map((tick) => {
    const y = PAD.top + tick * (height - PAD.top - PAD.bottom);
    return `<line class="chart-grid" x1="${PAD.left}" x2="${width - PAD.right}" y1="${y}" y2="${y}"/>`;
  }).join('');
  const labels = series.map((item, index) => `<text class="chart-axis" x="${xs[index]}" y="${height - 8}" text-anchor="middle">${escapeHtml(item.label)}</text>`).join('');
  const dots = series.map((item, index) => `<circle cx="${xs[index]}" cy="${ys[index]}" r="3.5" fill="var(--color-primary)" stroke="var(--color-surface)" stroke-width="2"><title>${escapeHtml(item.label)} ${formatNumber(item.value, 0)}</title></circle>`).join('');
  return `
    <div class="chart-shell">
      <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(options.ariaLabel || '趋势折线图')}">
        ${grid}
        <polygon class="chart-area" points="${area}"/>
        <polyline class="chart-line" points="${points}"/>
        ${dots}
        ${labels}
      </svg>
    </div>`;
}

export function barChart(items, options = {}) {
  const width = Number(options.width) || WIDTH;
  const height = Number(options.height) || HEIGHT;
  const max = Math.max(...items.map((item) => Number(item.value)), 1);
  const innerWidth = width - PAD.left - PAD.right;
  const barWidth = Math.min(54, innerWidth / items.length * .54);
  const gap = innerWidth / items.length;
  const bars = items.map((item, index) => {
    const value = Number(item.value);
    const barHeight = (value / max) * (height - PAD.top - PAD.bottom);
    const x = PAD.left + gap * index + (gap - barWidth) / 2;
    const y = height - PAD.bottom - barHeight;
    return `
      <rect class="chart-bar ${item.tone === 'danger' ? 'danger' : ''}" x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="5"><title>${escapeHtml(item.label)} ${formatNumber(value, 0)}</title></rect>
      <text class="chart-label" x="${x + barWidth / 2}" y="${height - 10}" text-anchor="middle">${escapeHtml(item.label)}</text>
      <text class="chart-axis" x="${x + barWidth / 2}" y="${y - 7}" text-anchor="middle">${formatNumber(value, 0)}</text>`;
  }).join('');
  return `
    <div class="chart-shell">
      <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(options.ariaLabel || '柱状图')}">
        <line class="chart-grid" x1="${PAD.left}" x2="${width - PAD.right}" y1="${height - PAD.bottom}" y2="${height - PAD.bottom}"/>
        ${bars}
      </svg>
    </div>`;
}
