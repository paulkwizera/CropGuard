import { escapeHtml } from "./format.js";
import { t } from "../i18n.js";

/** 24-hour forecast chart: rain as bars, temperature as a line. Built from real readings only. */
export function weatherChart(readings) {
  if (!readings?.length) return "";
  const W = 640, H = 250, m = { t: 20, r: 44, b: 38, l: 44 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const step = iw / readings.length;
  const temps = readings.map((r) => r.temp_c);
  const tMin = Math.floor(Math.min(...temps) - 1), tMax = Math.ceil(Math.max(...temps) + 1);
  const rainMax = Math.max(2, ...readings.map((r) => r.rain_mm));
  const y = (t) => m.t + ih - ((t - tMin) / (tMax - tMin || 1)) * ih;
  const yr = (mm) => m.t + ih - (mm / rainMax) * ih;
  const x = (i) => m.l + step * i + step / 2;

  const bars = readings.map((r, i) => {
    const h = Math.max(0, m.t + ih - yr(r.rain_mm));
    return r.rain_mm > 0 ? `<rect x="${x(i) - step * 0.28}" y="${yr(r.rain_mm)}" width="${step * 0.56}" height="${h}" rx="3" fill="var(--rain)" opacity=".85"/>` : "";
  }).join("");
  const line = readings.map((r, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(r.temp_c).toFixed(1)}`).join(" ");
  const dots = readings.map((r, i) => `<circle cx="${x(i)}" cy="${y(r.temp_c)}" r="4" fill="#fff" stroke="var(--forest-900)" stroke-width="2.5"/>`).join("");
  const labels = readings.map((r, i) => `<text x="${x(i)}" y="${H - 14}" text-anchor="middle">${escapeHtml(r.datetime.slice(11, 16))}</text>`).join("");
  const grid = [0, 0.5, 1].map((f) => {
    const gy = m.t + ih * f;
    return `<line x1="${m.l}" x2="${W - m.r}" y1="${gy}" y2="${gy}" stroke="var(--line)" stroke-dasharray="3 5"/>`;
  }).join("");
  const axisL = [0, 0.5, 1].map((f) => `<text x="${m.l - 10}" y="${m.t + ih * f + 4}" text-anchor="end">${Math.round(tMax - (tMax - tMin) * f)}°</text>`).join("");
  const axisR = [0, 0.5, 1].map((f) => `<text x="${W - m.r + 10}" y="${m.t + ih * f + 4}" text-anchor="start">${+(rainMax * (1 - f)).toFixed(1)}</text>`).join("");
  const summary = t("Temperature from {min} to {max} degrees Celsius and {rain} millimetres of rain over the next 24 hours.", { min: Math.min(...temps), max: Math.max(...temps), rain: readings.reduce((s, r) => s + r.rain_mm, 0).toFixed(1) });

  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${escapeHtml(summary)}" style="width:100%;height:auto;font:600 12px var(--font-body);fill:var(--ink-faint)">
    ${grid}${bars}
    <path d="${line}" fill="none" stroke="var(--forest-900)" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>
    ${dots}${labels}${axisL}${axisR}
    <text x="${m.l - 10}" y="10" text-anchor="end" style="fill:var(--forest-900)">°C</text>
    <text x="${W - m.r + 10}" y="10" text-anchor="start" style="fill:var(--rain)">mm</text>
  </svg>`;
}
